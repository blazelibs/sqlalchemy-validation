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
        self.before_flush_methods = []

        self.init_fe_validators()
        self.init_before_flush_methods()

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

    def init_fe_validators(self):
        for val_class, args, kwargs in self.entity_linkers:
            # val_class should be a subclass of ValidatorBase
            sav_val = val_class(self.entity.__class__, *args, **kwargs)

            # chained FE validators from entity SAV validators
            self.chained_validators.extend(sav_val.fe_entity_validators)

            # field FE validators from field SAV validators
            for field_name, fe_val in sav_val.fe_field_validators:
                #print field_name, fe_val
                self.field_validators[field_name].append(fe_val)

    def init_before_flush_methods(self):
        for attr_name, attr_obj in self.entity.__class__.__dict__.iteritems():
            # test for a value, not just the presence of the attribute to avoid
            # collecting methods that have been mocked and will therefore
            # have all attributes.
            if getattr(attr_obj, '_sav_before_flush', False) == 'yes':
                # don't want to get into trouble w/ strong references, so only
                # keep a copy of the name of the attribute
                self.before_flush_methods.append(attr_name)

    def trigger_before_flush_methods(self):
        for mname in self.before_flush_methods:
            method_obj = getattr(self.entity, mname)
            method_obj()

    def clear_errors(self):
        self.errors = defaultdict(list)

    def add_error(self, field_name, msg):
        self.errors[field_name].append(msg)

    def validate(self, type):
        if type == 'before_flush':
            self.clear_errors()
            self.trigger_before_flush_methods()

        # if there were no validators setup, then just return
        if not self.entity_linkers:
            # make sure we return errors here since a before_flush() method
            # could have added validation errors
            return self.errors

        fe_val_schema, fe_conv_schema = self.create_fe_schemas(type)
        self.validate_fe_schema(fe_val_schema, False)
        self.validate_fe_schema(fe_conv_schema, True)
        return self.errors

    def does_validator_apply(self, fieldname, fe_val, type):
        def_on_none = fe_val._sav_defer_on_none
        if not def_on_none:
            return type == 'before_flush'
        fvalue = self.entity.__dict__.get(fieldname, None)
        if fvalue is not None:
            return type == 'before_flush'
        return type != 'before_flush'

    def create_fe_schemas(self, type):
        fe_val_schema = formencode.Schema(allow_extra_fields = True)
        fe_conv_schema = formencode.Schema(allow_extra_fields = True)
        for field, validators in self.field_validators.iteritems():
            validators_to_apply = []
            converters_to_apply = []
            for v in validators:
                if self.does_validator_apply(field, v, type):
                    if v._sav_convert_flag:
                        converters_to_apply.append(v)
                    else:
                        validators_to_apply.append(v)
            if validators_to_apply:
                fe_val_schema.add_field(field, formencode.compound.All(*validators_to_apply))
            if converters_to_apply:
                fe_conv_schema.add_field(field, formencode.compound.All(*converters_to_apply))
        for fe_validator in self.chained_validators:
            fe_schema.add_chained_validator(fe_validator)
        return fe_val_schema, fe_conv_schema

    def validate_fe_schema(self, schema, flag_convert):
        idict = {}
        for colname in self.entity._sav_column_names():
            if schema.fields.has_key(colname):
                idict[colname] = getattr(self.entity, colname, None)
        try:
            #print '-------------', idict, schema, flag_convert, self.entity
            processed = schema.to_python(idict, _FEState(self.entity))
            if flag_convert:
                self.entity.__dict__.update(processed)
            #print '----valid', processed
        except formencode.Invalid, e:
            for field_name, msg in e.unpack_errors().iteritems():
                self.add_error(field_name, msg)

class ValidationMixin(object):
    _sav_entity_linkers = ()

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

    @classmethod
    def do_validation(cls, insts_to_val, insts_with_err, type):
        for instance in insts_to_val:
            if instance in insts_with_err:
                continue

            errors = instance._sav.validate(type)
            if errors:
                insts_with_err.append(instance)

    @classmethod
    def restore_and_raise(cls, session, iwe, expunged):
        # add the instances back in that got expunged
        for instance in expunged:
            session.add(instance)
        if iwe:
            raise ValidationError(iwe)

    @classmethod
    def before_flush(cls, session, flush_context, instances):
        iwe = session._sav_insts_with_err = []
        itv = session._sav_insts_to_val = []

        for inst in session.new:
            if not isinstance(inst, ValidationMixin):
                continue
            itv.append(inst)

        for inst in session.dirty:
            if not isinstance(inst, ValidationMixin):
                continue

            if session.is_modified(inst):
                itv.append(inst)

        cls.do_validation(itv, iwe, 'before_flush')

        # expunge all instances with an error from the session so that they
        # don't get flushed.  They will get added back into the session later
        # so that the state is consistent.  We just want to prevent DB errors
        # as much as possible.
        for instance in iwe:
            session.expunge(instance)

        # if we have expunged all the instances
        if not session.new and not session.dirty and not session.deleted:
            cls.restore_and_raise(session, iwe, iwe)

    @classmethod
    def after_flush(cls, session, flush_context):
        iwe = session._sav_insts_with_err
        expunged = list(iwe)
        itv = session._sav_insts_to_val
        cls.do_validation(itv, iwe, 'after_flush')
        cls.restore_and_raise(session, iwe, expunged)

# until this bug gets fixed & released:
#   http://www.sqlalchemy.org/trac/ticket/2424
# these events will only work if this module is instantiated BEFORE your session
# is created.  If that is not the case, then call watch_session() with your
# session object and the events will be registered correctly.
sa.event.listen(saorm.Session, 'before_flush', _EventHandler.before_flush)
sa.event.listen(saorm.Session, 'after_flush', _EventHandler.after_flush)

def watch_session(sess):
    sa.event.listen(sess, 'before_flush', _EventHandler.before_flush)
    sa.event.listen(sess, 'after_flush', _EventHandler.after_flush)
