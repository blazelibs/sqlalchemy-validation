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

class DeclarativeBase(object):

    def __init__(self, **kwargs):
        process_mutators(self)
        sadec._declarative_constructor(self, **kwargs)
        self.__validation_errors__ = {}
    
    @property
    def _column_names(self):
        return [p.key for p in self.__mapper__.iterate_properties \
                                      if isinstance(p, saorm.ColumnProperty)]
        
    def to_dict(self, exclude=[]):
        data = dict([(name, getattr(self, name))
                     for name in self._column_names if name not in exclude])
        return data
    
    def _validation_error(self, field_name, msg):
        errors = self.__validation_errors__.setdefault(field_name, [])
        errors.append(msg)
        
    def _get_validation_errors(self):
        return self.__validation_errors__
    validation_errors = property(_get_validation_errors)
    
    def _find_validator_extension(self):
        for extension in self.__mapper__.extension:
            if isinstance(extension, Validator):
                break
        else:
            extension = None
            
        return extension

def declarative_base(*args, **kwargs):
    kwargs.setdefault('cls', DeclarativeBase)
    kwargs.setdefault('constructor', None)
    return sadec.declarative_base(*args, **kwargs)

class ValidatingSessionExtension(saorm.interfaces.SessionExtension):
    
    def before_flush(self, session, flush_context, instances):
        instances_with_error = []
        instances_to_validate = list(session.new) + list(session.dirty)
        for instance in instances_to_validate:
            try:
                if hasattr(instance, '_find_validator_extension'):
                    validator_extension = instance._find_validator_extension()
                    if validator_extension:
                        validator_extension.validate(instance)
                    errors = instance._get_validation_errors()
                    if errors:
                        instances_with_error.append(instance)
            except AttributeError, e:
                if '_get_validation_errors' not in str(e):
                    raise
        if instances_with_error:
            raise ValidationError(instances_with_error)