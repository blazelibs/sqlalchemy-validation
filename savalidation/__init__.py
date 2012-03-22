from collections import defaultdict
import types
import weakref

import formencode
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.orm as saorm

from savalidation._internal import getversion
from savalidation.validators import _ELV

VERSION = getversion()

class ValidationError(Exception):
    """ issued when models are flushed but have validation errors """
    def __init__(self, invalid_instances):
        self.invalid_instances = invalid_instances
        instance_errors = []
        for instance in invalid_instances:
            fields_with_errors = []
            fields = instance._sav.errors
            model = str(instance)
            field_errors = {}
            for fname, errors in fields.iteritems():
                fields_with_errors.append('[%s: "%s"]' % (fname, '"; "'.join(errors)))
            instance_errors.append('%s %s' % (model, '; '.join(fields_with_errors)))
        msg = 'validation error(s): %s' % '; '.join(instance_errors)
        Exception.__init__(self, msg)

class EntityRefMissing(Exception):
    """
        _ValidationHelper uses a weak reference to the entity instance to make
        sure SA's identity map doesn't stay populated b/c of a strong reference
        to the entity.

        If a request for the entity reference is made, but the weak reference
        has lots its link to the entity instance, this exception is raised.

        This shouldn't happen normally, because the only time an entity
        reference should be needed is during validation and the only time
        validation should be triggered is when the Session has a reference
        to the entity and is in the before_flush or after_flush state.
    """

class _FEState(object):
    def __init__(self, entity):
        self.entity = entity

class _ValidationHelper(object):
    """
        This class exists to "back-up" the ValidationMixin so that we can set
        variables and use methods without concerning ourselves with clashing
        with the Entity's variables and methods.
    """
    def __init__(self, entity):
        self.clear_errors()
        self.entref = weakref.ref(entity)
        self.field_validators = defaultdict(list)
        self.chained_validators = []

    @property
    def entity(self):
        entity = self.entref()
        if entity is None:
            raise EntityRefMissing('A request for the entity occured, but that'
                ' object is no longer available through its weak reference.')
        return entity

    def __getstate__(self):
        """
            need to do some hoop jumping so that this object can be pickled
            without the weakref getting in the way
        """
        state = dict(self.__dict__)
        state['entity'] = self.entity
        del state['entref']
        return state

    def __setstate__(self, state):
        """
            complement's __getstate__ so that we can re-enstantiate the object
        """
        entity = state['entity']

        del state['entity']
        self.__dict__ = state
        self.entref = weakref.ref(entity)

    @property
    def entity_linkers(self):
        return self.entity._sav_entity_linkers

    @property
    def before_flush_methods(self):
        return self.entity._sav_before_flush_methods

    def trigger_before_flush_methods(self):
        for mname in self.before_flush_methods:
            method_obj = getattr(self.entity, mname)
            method_obj()

    def clear_errors(self):
        self.errors = defaultdict(list)

    def add_error(self, field_name, msg):
        self.errors[field_name].append(msg)

    def validate_fe_schema(self, schema, flag_convert):
        if not schema.fields:
            # print 'return b/c schema has no fields'
            return
        idict = {}
        for colname in self.entity._sav_column_names():
            if schema.fields.has_key(colname):
                idict[colname] = getattr(self.entity, colname, None)
        try:
            # print '-------------', idict, schema, flag_convert, self.entity
            processed = schema.to_python(idict, _FEState(self.entity))
            if flag_convert:
                self.entity.__dict__.update(processed)
            #print '----valid', processed
        except formencode.Invalid, e:
            for field_name, msg in e.unpack_errors().iteritems():
                self.add_error(field_name, msg)
            return True
        return False

    def run_event_schemas(self, event):
        has_error = False
        if self.entity._sav_fe_schemas:
            val_schema, conv_schema = self.entity._sav_fe_schemas[event]
            if self.validate_fe_schema(val_schema, False):
                has_error = True
            if self.validate_fe_schema(conv_schema, True):
                has_error = True
        return has_error

class ValidationMixin(object):
    _sav_do_validation = True

    def _sav_initialize(self):
        self._sav = _ValidationHelper(self)

    @property
    def validation_errors(self):
        return self._sav.errors

    def add_validation_error(self, field_name, msg):
        return self._sav.add_error(field_name, msg)

    @classmethod
    def _sav_column_names(self):
        return [p.key for p in self.__mapper__.iterate_properties \
                                      if isinstance(p, saorm.ColumnProperty)]

    def to_dict(self, exclude=[]):
        data = dict([(name, getattr(self, name))
                     for name in self.sa_column_names() if name not in exclude])
        return data

    @staticmethod
    @sa.event.listens_for(saorm.mapper, 'mapper_configured')
    def _sav_init_validation_class(mapper, cls):
        """
            This method is called when the class is finished initializing to
            take all the validation info that was associated with the class
            and turn it into formencode schemas that can be used later by the
            instances to do validation.
        """

        # dont run for classes that aren't validators
        if not getattr(cls, '_sav_do_validation', False):
            return

        # only want this to run once per class
        if getattr(cls, '_sav_class_init_already_ran', False):
            return

        # make sure the attribute is there for classes which use the mixin
        # but don't actually use any validators
        cls._sav_class_init_already_ran = True
        if not hasattr(cls, '_sav_entity_linkers'):
            cls._sav_entity_linkers = ()
        cls._sav_fe_schemas = {}
        cls._sav_before_flush_methods = []

        # gather all the fev_metas from all entity linkers into one place
        all_fev_metas = []
        for val_class, args, kwargs in cls._sav_entity_linkers:
            # val_class should be a subclass of ValidatorBase
            sav_val = val_class(cls, *args, **kwargs)
            all_fev_metas.extend(sav_val.fev_metas)

        # create the formencode schemas to validate with
        cls._sav_fe_schemas['before_flush'] = \
            cls._sav_create_fe_schema(all_fev_metas, 'before_flush', False), \
            cls._sav_create_fe_schema(all_fev_metas, 'before_flush', True)

        cls._sav_fe_schemas['before_exec'] = \
            cls._sav_create_fe_schema(all_fev_metas, 'before_exec', False), \
            cls._sav_create_fe_schema(all_fev_metas, 'before_exec', True)

        # setup methods that have been decorated with the before_flush event
        for attr_name, attr_obj in cls.__dict__.iteritems():
            # test for a value, not just the presence of the attribute to avoid
            # collecting methods that have been mocked and will therefore
            # have all attributes.
            if getattr(attr_obj, '_sav_before_flush', False) == 'yes':
                # don't want to get into trouble w/ strong references, so only
                # keep a copy of the name of the attribute
                cls._sav_before_flush_methods.append(attr_name)

    @classmethod
    def _sav_create_fe_schema(cls, fev_metas, for_event, for_conversion):
        schema = formencode.Schema(allow_extra_fields = True)
        field_validators = defaultdict(list)
        for fevm in fev_metas:
            if fevm.event == for_event and fevm.is_converter == for_conversion:
                field_validators[fevm.field_name].append(fevm.fev)
        for fieldname, validators in field_validators.iteritems():
            schema.add_field(fieldname, formencode.compound.All(*validators))
        return schema

    @classmethod
    def _sav_validate(cls, instance, type):
        if type == 'before_flush':
            instance._sav.clear_errors()
            instance._sav.trigger_before_flush_methods()

        return instance._sav.run_event_schemas(type)

class _EventHandler(object):

    @staticmethod
    @sa.event.listens_for(saorm.mapper, 'init')
    def initialize_validators_for_init(target, args, kwargs):
        if hasattr(target, '_sav_initialize'):
            target._sav_initialize()

    @staticmethod
    @sa.event.listens_for(saorm.mapper, 'load')
    def initialize_validators_for_load(target, context):
        if hasattr(target, '_sav_initialize'):
            target._sav_initialize()

    @staticmethod
    def handle_insert(mapper, connection, target):
        if hasattr(target, '_sav_validate'):
            errors = target._sav_validate(target, 'before_exec')

    @staticmethod
    @sa.event.listens_for(saorm.mapper, 'before_insert')
    @sa.event.listens_for(saorm.mapper, 'before_update')
    def handle_before_exec(mapper, connection, target):
        if not hasattr(target, '_sav_validate'):
            return
        sess = saorm.session.Session.object_session(target)
        sess._sav_ent_exec_count -= 1

        target._sav_validate(target, 'before_exec')

        if sess._sav_ent_exec_count == 0:
            ents_with_error = []
            for ent in sess._sav_ents_to_validate:
                if ent.validation_errors:
                    ents_with_error.append(ent)
            # print ents_with_error
            if ents_with_error:
                raise ValidationError(ents_with_error)

    @classmethod
    def before_flush(cls, session, flush_context, instances):
        ents_to_validate = session._sav_ents_to_validate = []

        for ent in session.new:
            if not hasattr(ent, '_sav_validate'):
                continue
            ents_to_validate.append(ent)

        for ent in session.dirty:
            if not hasattr(ent, '_sav_validate'):
                continue
            if session.is_modified(ent):
                ents_to_validate.append(ent)

        # save the number of instances so we know when to raise in the
        # handle_before_exec() method above
        session._sav_ent_exec_count = len(ents_to_validate)

        for ent in ents_to_validate:
            ent._sav_validate(ent, 'before_flush')

# until this bug gets fixed & released:
#   http://www.sqlalchemy.org/trac/ticket/2424
# these events will only work if this module is instantiated BEFORE your session
# is created.  If that is not the case, then call watch_session() with your
# session object and the events will be registered correctly.
sa.event.listen(saorm.Session, 'before_flush', _EventHandler.before_flush)

def watch_session(sess):
    sa.event.listen(sess, 'before_flush', _EventHandler.before_flush)
