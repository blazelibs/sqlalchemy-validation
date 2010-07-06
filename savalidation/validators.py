from dateutil.parser import parse
import formencode
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
                self.validator_ext.add_validation(formencode.FancyValidator(not_empty=True), colname)
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


validates_presence_of = ClassMutator(_ValidatesPresenceOf)
validates_one_of = ClassMutator(_ValidatesOneOf)
validates_choices = ClassMutator(_ValidatesChoices)
validates_constraints = ClassMutator(_ValidatesConstraints)
converts_date = _formencode_validator_factory(formencode.validators.DateConverter)
converts_time = _formencode_validator_factory(formencode.validators.TimeConverter, use_datetime=True)
converts_datetime = _formencode_validator_factory(DateTimeConverter)
