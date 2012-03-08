import inspect
import sys

from dateutil.parser import parse
import formencode
import formencode.validators as fev
import formencode.national
import sqlalchemy as sa

from savalidation._internal import is_iterable

_ELV = '_sav_entity_linkers'

# map a SA field type to a formencode validator for use in _ValidatesConstraints
SA_FORMENCODE_MAPPING = {
    sa.types.Integer: formencode.validators.Int,
    sa.types.Numeric: formencode.validators.Number,
}

class EntityLinker(object):
    """
        Wraps a Validator, storing the validator class and subsequent arguments
        on the entity class for later use by the entity instances.

        validates_something = EntityLinker(SomethingValidator)

        class Car(Base, ValidationMixin):

            make = sa.Column(String(50))
            validates_something(make)
    """

    def __init__(self, validator_cls):
        self.validator_cls = validator_cls

    def __call__(self, *args, **kwargs):
        class_locals = sys._getframe(1).f_locals
        elvs = class_locals.setdefault(_ELV, [])
        elvs.append((self.validator_cls, args, kwargs))
entity_linker = EntityLinker

class ValidatorBase(object):
    fe_validator = None
    default_kwargs = dict()

    def __init__(self, entity_cls, *args, **kwargs):
        self.entitycls = entity_cls
        self.args = args
        self.kwargs = kwargs
        self.fe_field_validators = []
        self.fe_entity_validators = []
        self.field_names = []
        self.fe_args = []

        self.split_field_names_from_fe_args()
        self.create_fe_validators()

    def add_field_validator(self, field_name, fe_val):
        if not hasattr(fe_val, '_sav_defer_on_none'):
            fe_val._sav_defer_on_none = False
        if not hasattr(fe_val, '_sav_convert_flag'):
            fe_val._sav_convert_flag = False
        self.fe_field_validators.append((field_name, fe_val))

    def add_entity_validator(self, fe_val):
        self.fe_entity_validators.append(fe_val)

    def split_field_names_from_fe_args(self):
        """
            Some validators may want to take position arguments and field
            names.  This method handles putting the args in the correct
            internal variable.
        """
        index = 0
        for index, unknown_arg in enumerate(self.args):
            if self.arg_for_fe_validator(index, unknown_arg):
                self.fe_args.append(unknown_arg)
                break
            self.field_names.append(unknown_arg)
        self.fe_args.extend(self.args[index+1:])

    def create_fe_validators(self):
        defer_flag = self.kwargs.pop('deferred', False)
        kwargs = self.default_kwargs.copy()
        kwargs.update(self.kwargs)
        convert_flag = kwargs.pop('sv_convert', False)

        for field_to_validate in self.field_names:
            validator = self.fe_validator(*self.fe_args, **kwargs)
            validator._sav_defer_on_none = defer_flag
            validator._sav_convert_flag = convert_flag
            self.add_field_validator(field_to_validate, validator)

    def arg_for_fe_validator(self, index, unknown_arg):
        return False

class DateTimeConverter(fev.FancyValidator):
    def _to_python(self, value, state):
        try:
            return parse(value)
        except ValueError, e:
            if 'unknown string format' not in str(e):
                raise
            raise formencode.Invalid('Unknown date/time string "%s"' % value, value, state)

@entity_linker
class _ValidatesPresenceOf(ValidatorBase):
    fe_validator = formencode.FancyValidator
    default_kwargs = dict(not_empty=True)

class _ValidatesOneOf(ValidatorBase):
    fe_validator = fev.OneOf
    def arg_for_fe_validator(self, index, unknown_arg):
        return is_iterable(unknown_arg)

class _MinLength(fev.MinLength):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesMinLength(ValidatorBase):
    fe_validator = _MinLength
    def arg_for_fe_validator(self, index, unknown_arg):
        if isinstance(unknown_arg, int):
            return True
        return False

class _IPAddress(fev.IPAddress):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesIPAddress(ValidatorBase):
    fe_validator = _IPAddress

class _URL(fev.URL):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesURL(ValidatorBase):
    fe_validator = _URL

class _ValidatesChoices(_ValidatesOneOf):
    def create_fe_validators(self):
        # the first formencode parameter should be a sequence of pairs.  However,
        # the FE validator needs just the list of keys that are valid, so we
        # strip those off here.
        self.fe_args[0] = [k for k,v in self.fe_args[0]]
        ValidatorBase.create_fe_validators(self)

@entity_linker
class _ValidatesConstraints(ValidatorBase):
    def create_fe_validators(self):
        # grab some values from the kwargs that apply to this validator
        validate_length = bool(self.kwargs.get('length', True))
        validate_nullable = bool(self.kwargs.get('nullable', True))
        validate_type = bool(self.kwargs.get('type', True))
        excludes = self.kwargs.get('exclude', [])

        fe_validators = []
        for colname in self.entitycls._sav_column_names():
            # get the SA column instance
            col = self.entitycls.__mapper__.get_property(colname).columns[0]

            # ignore primary keys
            if colname in excludes or col.primary_key:
                continue

            # validate lengths on String and Unicode types
            if validate_length and isinstance(col.type, sa.types.String):
                self.add_field_validator(colname, fev.MaxLength(col.type.length))

            # handle fields that are not nullable
            if validate_nullable and not col.nullable:
                validator = formencode.FancyValidator(not_empty=True)
                # some values only get populated after a flush, we tag these
                # validators here
                if col.default or col.foreign_keys or col.server_default:
                    validator._sav_defer_on_none = True
                self.add_field_validator(colname, validator)

            # data-type validation
            if validate_type:
                for sa_type, fe_validator in SA_FORMENCODE_MAPPING.iteritems():
                    if isinstance(col.type, sa_type):
                        self.add_field_validator(colname, fe_validator)
                        break

def formencode_factory(fevalidator, **kwargs):
    """
        Converts a formencode validator into an object that can be used in
        an entity object for validation:

        validates_int = formencode_factory(formencode.validators.Int)

        class MyCar(Base):
            year = Column(Int)
            validates_int('year')
    """
    class _ValidatesFeValidator(ValidatorBase):
        fe_validator = fevalidator
        type = 'field'
        default_kwargs = kwargs
    return EntityLinker(_ValidatesFeValidator)


validates_choices = EntityLinker(_ValidatesChoices)
validates_constraints = _ValidatesConstraints
validates_ipaddr= EntityLinker(_ValidatesIPAddress)
validates_minlen= EntityLinker(_ValidatesMinLength)
validates_one_of = EntityLinker(_ValidatesOneOf)
validates_presence_of = _ValidatesPresenceOf
validates_required = _ValidatesPresenceOf
validates_url = EntityLinker(_ValidatesURL)
validates_email = formencode_factory(fev.Email)
validates_usphone = formencode_factory(formencode.national.USPhoneNumber)

converts_date = formencode_factory(fev.DateConverter, sv_convert=True)
converts_time = formencode_factory(fev.TimeConverter, use_datetime=True, sv_convert=True)
converts_datetime = formencode_factory(DateTimeConverter, sv_convert=True)
