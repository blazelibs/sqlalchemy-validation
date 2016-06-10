from __future__ import absolute_import

from decimal import Decimal, DecimalException
import sys

from dateutil.parser import parse
import formencode
import formencode.validators as fev
import formencode.national
import sqlalchemy as sa

from savalidation._internal import is_iterable
import six

_ELV = '_sav_entity_linkers'


class BaseValidator(fev.FancyValidator):
    def __classinit__(cls, new_attrs):
        depricated_methods = getattr(cls, '_deprecated_methods', None) or \
            new_attrs.get('_deprecated_methods')
        if depricated_methods is not None:
            for old, new in depricated_methods:
                if old in new_attrs:
                    method = new_attrs.pop(old)
                    setattr(cls, new, method)
                    new_attrs[new] = method
        return fev.FancyValidator.__classinit__(cls, new_attrs)


class NumericValidator(BaseValidator):
    def __init__(self, places, prec):
        self.places = places
        self.prec = prec
        super(NumericValidator, self).__init__()

    def _to_python(self, value, state):
        try:
            return Decimal(value)
        except DecimalException:
            raise formencode.Invalid('Please enter a number', value, state)

    def validate_python(self, value, state):
        super(BaseValidator, self)._validate_python(value, state)
        if value is None or self.places is None or self.prec is None:
            return
        max_before_point = self.places - self.prec
        if value.adjusted() + 1 > max_before_point:
            max_val = '{}.{}'.format('9' * max_before_point, '9' * self.prec)
            if value >= 0:
                raise formencode.Invalid(
                    'Please enter a number that is {} or smaller'.format(max_val), state, value
                )
            else:
                raise formencode.Invalid(
                    'Please enter a number that is -{} or greater'.format(max_val), state, value
                )

        quant = Decimal('1') / (Decimal('10') ** self.prec) if self.prec else Decimal('0')
        if value.quantize(quant) != value:
            raise formencode.Invalid(
                'Please enter a number with {} or fewer decimal places'.format(self.prec),
                state, value
            )


# map a SA field type to a formencode validator for use in _ValidatesConstraints
SA_FORMENCODE_MAPPING = {
    sa.types.Integer: formencode.validators.Int,
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


class FEVMeta(object):
    """
        Wraps a formencode validator along with other meta information that
        indicates how & when that validator is to be used.
    """
    ALL_EVENTS = 'before_flush', 'before_exec'

    def __init__(self, fev, field_name=None, event='before_flush', is_converter=False):
        if event not in self.ALL_EVENTS:
            raise ValueError('got "{0}" for event, should be one of: {1}'.format(event,
                                                                                 self.ALL_EVENTS))
        self.fev = fev
        self.field_name = field_name
        self.event = event
        self.is_converter = is_converter

    def __repr__(self):
        return '<FEVMeta: field_name={0}; event={1}; is_conv={2}; fev={3}'.format(
            self.field_name, self.event, self.is_converter, self.fev
        )


class ValidatorBase(object):
    fe_validator = None
    default_kwargs = dict()

    def __init__(self, entity_cls, *args, **kwargs):
        self.entitycls = entity_cls
        self.args = args
        self.kwargs = kwargs
        self.field_names = []
        self.fe_args = []
        self.fev_metas = []

        self.split_field_names_from_fe_args()
        self.create_fe_validators()

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
        kwargs = self.default_kwargs.copy()
        kwargs.update(self.kwargs)
        convert_flag = kwargs.pop('sav_convert', kwargs.pop('sv_convert', False))
        sav_event = kwargs.pop('sav_event', 'before_flush')

        for field_to_validate in self.field_names:
            self.create_fev_meta(self.fe_validator, field_to_validate, kwargs, sav_event,
                                 convert_flag)

    def create_fev_meta(self, fev_cls, colname, fe_kwargs={}, sav_event='before_flush',
                        convert_flag=False, auto_not_empty=True):
        fe_kwargs = fe_kwargs.copy()
        if auto_not_empty and self.sa_column_needs_not_empty(colname):
            fe_kwargs['not_empty'] = True
        fev = fev_cls(*self.fe_args, **fe_kwargs)
        fev_meta = FEVMeta(fev, colname, sav_event, convert_flag)
        self.fev_metas.append(fev_meta)

    def sa_column_needs_not_empty(self, colname):
        col = self.fetch_sa_column(colname)
        if not col.nullable and not col.default and not col.server_default:
            return True
        return False

    def fetch_sa_column(self, colname):
        return self.entitycls.__mapper__.get_property(colname).columns[0]

    def arg_for_fe_validator(self, index, unknown_arg):
        return False


class DateTimeConverter(BaseValidator):
    def _to_python(self, value, state):
        try:
            return parse(value)
        except ValueError as e:
            if 'unknown string format' not in str(e).lower():
                raise
            raise formencode.Invalid('Unknown date/time string "%s"' % value, value, state)
        except TypeError as e:
            # can probably be removed if this ever gets fixed:
            # https://bugs.launchpad.net/dateutil/+bug/1257985
            if "'NoneType' object is not iterable" not in str(e):
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
        self.fe_args[0] = [k for k, v in self.fe_args[0]]
        ValidatorBase.create_fe_validators(self)


@entity_linker
class _ValidatesConstraints(ValidatorBase):
    def create_fe_validators(self):
        # grab some values from the kwargs that apply to this validator
        validate_length = bool(self.kwargs.get('length', True))
        validate_nullable = bool(self.kwargs.get('nullable', True))
        validate_type = bool(self.kwargs.get('type', True))
        excludes = self.kwargs.get('exclude', [])

        for colname in self.entitycls._sav_column_names():
            # get the SA column instance
            col = self.entitycls.__mapper__.get_property(colname).columns[0]

            # ignore primary keys
            if colname in excludes or col.primary_key:
                continue

            # validate lengths on String and Unicode types, but not Text b/c it shouldn't have a
            # length
            if validate_length and isinstance(col.type, sa.types.String) \
                    and not isinstance(col.type, sa.types.Text):
                fmeta = FEVMeta(fev.MaxLength(col.type.length), colname)
                self.fev_metas.append(fmeta)

            if validate_type and isinstance(col.type, sa.types.Numeric):
                fmeta = FEVMeta(NumericValidator(col.type.precision, col.type.scale), colname)
                self.fev_metas.append(fmeta)

            # handle fields that are not nullable
            if validate_nullable and not col.nullable:
                if not col.default and not col.server_default:
                    validator = formencode.FancyValidator(not_empty=True)
                    event = 'before_flush'
                    if col.foreign_keys:
                        event = 'before_exec'
                    fmeta = FEVMeta(validator, colname, event)
                    self.fev_metas.append(fmeta)

            # data-type validation
            if validate_type:
                for sa_type, fe_validator in six.iteritems(SA_FORMENCODE_MAPPING):
                    if isinstance(col.type, sa_type):
                        self.create_fev_meta(fe_validator, colname, auto_not_empty=False)
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
validates_ipaddr = EntityLinker(_ValidatesIPAddress)
validates_minlen = EntityLinker(_ValidatesMinLength)
validates_one_of = EntityLinker(_ValidatesOneOf)
validates_presence_of = _ValidatesPresenceOf
validates_required = _ValidatesPresenceOf
validates_url = EntityLinker(_ValidatesURL)
validates_email = formencode_factory(fev.Email)
validates_usphone = formencode_factory(formencode.national.USPhoneNumber)

converts_date = formencode_factory(fev.DateConverter, sv_convert=True)
converts_time = formencode_factory(fev.TimeConverter, use_datetime=True, sv_convert=True)
converts_datetime = formencode_factory(DateTimeConverter, sv_convert=True)
