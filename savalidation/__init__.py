import sqlalchemy.ext.declarative as sadec
import sqlalchemy.orm as saorm
from _internal import process_mutators, Validator

class ValidationError(Exception):
    """ issued when models are flushed but have validation errors """
    def __init__(self, invalid_instances):
        self.invalid_instances = invalid_instances
        fields_with_errors = []
        for instance in invalid_instances:
            fields = instance._get_validation_errors()
            model = str(instance)
            fields_with_errors.append('%s[%s]' % (model, ','.join(fields.keys())))
        msg = 'validation error(s) on: %s' % '; '.join(fields_with_errors)
        Exception.__init__(self, msg)

class ValidationMixin(object):

    @saorm.reconstructor
    def init_on_load(self):
        process_mutators(self.__class__)
        self.clear_validation_errors()

    @classmethod
    def sa_column_names(self):
        return [p.key for p in self.__mapper__.iterate_properties \
                                      if isinstance(p, saorm.ColumnProperty)]

    def to_dict(self, exclude=[]):
        data = dict([(name, getattr(self, name))
                     for name in self.sa_column_names() if name not in exclude])
        return data

    def _validation_error(self, field_name, msg):
        errors = self.__validation_errors__.setdefault(field_name, [])
        errors.append(msg)

    def _get_validation_errors(self):
        return self.__validation_errors__
    validation_errors = property(_get_validation_errors)

    def clear_validation_errors(self):
        self.__validation_errors__ = {}

    @classmethod
    def _find_validator_extension(cls):
        for extension in cls.__mapper__.extension:
            if isinstance(extension, Validator):
                break
        else:
            extension = None

        return extension

def custom_constructor(self, **kwargs):
    sadec._declarative_constructor(self, **kwargs)
    if hasattr(self, 'init_on_load'):
        self.init_on_load()

def declarative_base(*args, **kwargs):
    kwargs.setdefault('constructor', custom_constructor)
    return sadec.declarative_base(*args, **kwargs)

class ValidatingSessionExtension(saorm.interfaces.SessionExtension):

    def _sv_do_validation(self, itv, iwe, type):
        for instance in itv:
            if instance in iwe:
                continue
            try:
                if hasattr(instance, '_find_validator_extension'):
                    validator_extension = instance._find_validator_extension()
                    if validator_extension:
                        validator_extension.validate(instance, type)
                    errors = instance._get_validation_errors()
                    #print instance, errors
                    if errors:
                        iwe.append(instance)
            except AttributeError, e:
                if '_get_validation_errors' not in str(e):
                    raise

    def _sv_restore_and_raise(self, session, iwe, expunged):
        # add the instances back in that got expunged
        for instance in expunged:
            session.add(instance)
        if iwe:
            raise ValidationError(iwe)

    def before_flush(self, session, flush_context, instances):
        iwe = session._sv_instances_with_error = []
        itv = session._sv_instances_to_validate = list(session.new) + list(session.dirty)
        self._sv_do_validation(itv, iwe, 'before_flush')

        # expunge all instances with an error from the session so that they
        # don't get flushed.  They will get added back into the session later
        # so that the state is consistent.  We just want to prevent DB errors
        # as much as possible.
        for instance in iwe:
            session.expunge(instance)

        # if we have expunged all the instances
        if not session.new and not session.dirty and not session.deleted:
            self._sv_restore_and_raise(session, iwe, iwe)

    def after_flush(self, session, flush_context):
        iwe = session._sv_instances_with_error
        expunged = list(iwe)
        itv = session._sv_instances_to_validate
        self._sv_do_validation(itv, iwe, 'after_flush')
        self._sv_restore_and_raise(session, iwe, expunged)
