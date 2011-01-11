from dateutil.parser import parse
import formencode
import formencode.validators
import formencode.national
import sqlalchemy as sa
from _internal import ValidationHandler, ClassMutator, is_iterable, \
    SA_FORMENCODE_MAPPING

class DateTimeConverter(formencode.validators.FancyValidator):
    def _to_python(self, value, state):
        try:
            return parse(value)
        except ValueError, e:
            if 'unknown string format' not in str(e):
                raise
            raise formencode.Invalid('Unknown date/time string "%s"' % value, value, state)

class _ValidatesPresenceOf(ValidationHandler):
    fe_validator = formencode.FancyValidator
    type = 'field'
    default_kwargs = dict(not_empty=True)

class _ValidatesOneOf(ValidationHandler):
    fe_validator = formencode.validators.OneOf
    type = 'field'
    def should_break(self, unknown_arg):
        return is_iterable(unknown_arg)

class _MinLength(formencode.validators.MinLength):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesMinLength(ValidationHandler):
    fe_validator = _MinLength
    type = 'field'
    def should_break(self, unknown_arg):
        if isinstance(unknown_arg, int):
            return True
        return False

class _IPAddress(formencode.validators.IPAddress):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesIPAddress(ValidationHandler):
    fe_validator = _IPAddress
    type = 'field'

class _URL(formencode.validators.URL):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesURL(ValidationHandler):
    fe_validator = _URL
    type = 'field'

class _ValidatesChoices(_ValidatesOneOf):
    def add_validation_to_extension(self, field_names, fe_args, **kwargs):
        fe_args[0] = [k for k,v in fe_args[0]]
        ValidationHandler.add_validation_to_extension(self, field_names, fe_args, **kwargs)

class _ValidatesConstraints(ValidationHandler):
    type = 'notfield'
    def add_validation_to_extension(self, field_names, validation_types, **kwargs):
        validate_length = bool(kwargs.get('length', True))
        validate_nullable = bool(kwargs.get('nullable', True))
        validate_type = bool(kwargs.get('type', True))
        excludes = kwargs.get('exclude', [])
        colnames = self.entitycls.sa_column_names()
        for colname in colnames:
            col = self.entitycls.__mapper__.get_property(colname).columns[0]
            if colname in excludes or col.primary_key:
                continue
            if validate_length and isinstance(col.type, sa.types.String):
                self.validator_ext.add_validation(formencode.validators.MaxLength(col.type.length), colname)
            if validate_nullable and not col.nullable:
                validator = formencode.FancyValidator(not_empty=True)
                # some values only get populated after a flush, we tag these
                # validators here
                if col.default or col.foreign_keys or col.server_default:
                    validator._sa_defer_on_none = True
                self.validator_ext.add_validation(validator, colname)
            if validate_type:
                for sa_type, fe_validator in SA_FORMENCODE_MAPPING.iteritems():
                    if isinstance(col.type, sa_type):
                        self.validator_ext.add_validation(fe_validator, colname)
                        break

def _formencode_validator_factory(fevalidator, **kwargs):
    class _ValidatesFeValidator(ValidationHandler):
        fe_validator = fevalidator
        type = 'field'
        default_kwargs = kwargs
    return ClassMutator(_ValidatesFeValidator)


validates_choices = ClassMutator(_ValidatesChoices)
validates_constraints = ClassMutator(_ValidatesConstraints)
validates_ipaddr= ClassMutator(_ValidatesIPAddress)
validates_minlen= ClassMutator(_ValidatesMinLength)
validates_one_of = ClassMutator(_ValidatesOneOf)
validates_presence_of = ClassMutator(_ValidatesPresenceOf)
validates_url = ClassMutator(_ValidatesURL)
validates_email = _formencode_validator_factory(formencode.validators.Email)
validates_usphone = _formencode_validator_factory(formencode.national.USPhoneNumber)

converts_date = _formencode_validator_factory(formencode.validators.DateConverter, sv_convert=True)
converts_time = _formencode_validator_factory(formencode.validators.TimeConverter, use_datetime=True, sv_convert=True)
converts_datetime = _formencode_validator_factory(DateTimeConverter, sv_convert=True)
