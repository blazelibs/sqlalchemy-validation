import formencode
import sqlalchemy as sa
from _internal import ValidationHandler, ClassMutator, is_iterable

class _ValidatesPresenceOf(ValidationHandler):
    fe_validator = formencode.FancyValidator
    type = 'field'
    
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
        colnames = self.instance._column_names
        for colname in colnames:
            col = self.instance.__mapper__.get_property(colname).columns[0]
            if colname in excludes or col.primary_key:
                continue
            if validate_length and isinstance(col.type, sa.types.String):
                self.validator_ext.add_validation(formencode.validators.MaxLength(col.type.length), colname)
            if validate_nullable and not col.nullable:
                self.validator_ext.add_validation(formencode.FancyValidator, colname)
        

validates_presence_of = ClassMutator(_ValidatesPresenceOf)
validates_one_of = ClassMutator(_ValidatesOneOf)
validates_choices = ClassMutator(_ValidatesChoices)
validates_constraints = ClassMutator(_ValidatesConstraints)