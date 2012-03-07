import sys
from dateutil.parser import parse
import formencode
import formencode.validators
import formencode.national
import sqlalchemy as sa
from savalidation._internal import is_iterable, SA_FORMENCODE_MAPPING

_ELV = '_sav_entity_linkers'

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
    type = 'field'
    default_kwargs = dict()

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        ##print '--- init validation handler'
        #self.entitycls = entitycls
        #self.validator_ext = entitycls._find_validator_extension()
        #
        ## add the Validator mapper extension if needed
        #if not self.validator_ext:
        #    self.validator_ext = Validator()
        #    entitycls.__mapper__.extension.append(self.validator_ext)
        #print '--- mapper is', object.__repr__(entitycls.__mapper__)

        if self.type == 'field':
            self.split_field_names_from_args()
        else:
            self.field_names = None
            self.fe_args = args

    def split_field_names_from_args(self):
        self.field_names = []
        self.fe_args = []
        for index, unknown_arg in enumerate(self.args):
            if self.should_break(unknown_arg):
                self.fe_args.append(unknown_arg)
                break
            self.field_names.append(unknown_arg)
        self.fe_args.extend(self.args[index+1:])

    def entity_fe_validators(self):
        if self.type != 'entity' or self.fe_validator is None:
            return ()
        fe_validator = self.fe_validator(*self.args, **self.kwargs)
        return (fe_validator,)

    def field_fe_validators(self):
        if self.type != 'field':
            return ()

        defer_flag = self.kwargs.pop('deferred', False)
        kwargs = self.default_kwargs.copy()
        kwargs.update(self.kwargs)
        convert_flag = kwargs.pop('sv_convert', False)

        validators = []
        for field_to_validate in self.field_names:
            validator = self.fe_validator(*self.fe_args, **kwargs)
            validator._sav_defer_on_none = defer_flag
            validator._sav_convert_flag = convert_flag
            validators.append((field_to_validate, validator))
        return validators

    def should_break(self, unknown_arg):
        return False

class DateTimeConverter(formencode.validators.FancyValidator):
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
    type = 'field'
    default_kwargs = dict(not_empty=True)

class _ValidatesOneOf(ValidatorBase):
    fe_validator = formencode.validators.OneOf
    type = 'field'
    def should_break(self, unknown_arg):
        return is_iterable(unknown_arg)

class _MinLength(formencode.validators.MinLength):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesMinLength(ValidatorBase):
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

class _ValidatesIPAddress(ValidatorBase):
    fe_validator = _IPAddress
    type = 'field'

class _URL(formencode.validators.URL):
    """ need a special class that will allow None through but not '' """
    def is_empty(self, value):
        # only consider None empty, not an empty string
        return value is None

class _ValidatesURL(ValidatorBase):
    fe_validator = _URL
    type = 'field'

class _ValidatesChoices(_ValidatesOneOf):
    def add_validation_to_extension(self, field_names, fe_args, **kwargs):
        fe_args[0] = [k for k,v in fe_args[0]]
        ValidatorBase.add_validation_to_extension(self, field_names, fe_args, **kwargs)

class _ValidatesConstraints(ValidatorBase):
    type = 'entity'
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
    class _ValidatesFeValidator(ValidatorBase):
        fe_validator = fevalidator
        type = 'field'
        default_kwargs = kwargs
    return EntityLinker(_ValidatesFeValidator)


validates_choices = EntityLinker(_ValidatesChoices)
validates_constraints = EntityLinker(_ValidatesConstraints)
validates_ipaddr= EntityLinker(_ValidatesIPAddress)
validates_minlen= EntityLinker(_ValidatesMinLength)
validates_one_of = EntityLinker(_ValidatesOneOf)
validates_presence_of = _ValidatesPresenceOf
validates_required = _ValidatesPresenceOf
validates_url = EntityLinker(_ValidatesURL)
validates_email = _formencode_validator_factory(formencode.validators.Email)
validates_usphone = _formencode_validator_factory(formencode.national.USPhoneNumber)

converts_date = _formencode_validator_factory(formencode.validators.DateConverter, sv_convert=True)
converts_time = _formencode_validator_factory(formencode.validators.TimeConverter, use_datetime=True, sv_convert=True)
converts_datetime = _formencode_validator_factory(DateTimeConverter, sv_convert=True)
