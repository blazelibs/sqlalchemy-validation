import sys
from datetime import datetime
import formencode
from formencode import Invalid
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

SA_FORMENCODE_MAPPING = {
    sa.types.Integer: formencode.validators.Int,
    sa.types.Numeric: formencode.validators.Number,
}

MUTATORS = '__savalidation_mutators__'
MUTATORS_FLAG = '__savalidation_mutators_flag__'

def is_iterable(possible_iterable):
    if isinstance(possible_iterable, basestring):
        return False
    try:
        iter(possible_iterable)
        return True
    except TypeError:
        return False

class ClassMutator(object):
    '''
    DSL-style syntax

    A ``ClassMutator`` object represents a DSL term.
    '''

    def __init__(self, handler):
        '''
        Create a new ClassMutator, using the `handler` callable to process it
        when the time will come.
        '''
        self.handler = handler

    # called when a mutator (eg. "has_field(...)") is parsed
    def __call__(self, *args, **kwargs):
        # self in this case is the "generic" mutator (eg "has_field")
        # jam this mutator into the class's mutator list
        class_locals = sys._getframe(1).f_locals
        mutators = class_locals.setdefault(MUTATORS, [])
        mutators.append((self, args, kwargs))

    def process(self, cls, *args, **kwargs):
        '''
        Process one mutator. This version simply calls the handler callable,
        but another mutator (sub)class could do more processing.
        '''
        self.handler(cls, *args, **kwargs)

def process_mutators(cls):
    '''
    Loop over all mutators in the class's mutator list and process them.  This
    function can be called multiple times, but will only process mutators for
    a class once.
    '''
    #print '--- process mutators'
    # we don't use getattr here to not inherit from the parent mutators
    # inadvertantly if the current entity hasn't defined any mutator.
    if getattr(cls, MUTATORS_FLAG, False):
        return
    setattr(cls, MUTATORS_FLAG, True)
    mutators = cls.__dict__.get(MUTATORS, [])
    for mutator, args, kwargs in mutators:
        mutator.process(cls, *args, **kwargs)

class FEState(object):
    def __init__(self, instance):
        self.instance = instance

def should_apply(fieldname, instance, validator, type):
    def_on_none = getattr(validator, '_sa_defer_on_none', False)
    if not def_on_none:
        return type == 'before_flush'
    fvalue = instance.__dict__.get(fieldname, None)
    if fvalue is not None:
        return type == 'before_flush'
    return type != 'before_flush'

class Validator(saorm.interfaces.MapperExtension):
    def __init__(self, *args):
        saorm.interfaces.MapperExtension.__init__(self)
        self.field_validators = {}
        self.chained_validators = []
        #print 'validator init'

    def add_validation(self, fe_validator, field):
        #print 'add validation', field, fe_validator
        if field:
            self.field_validators.setdefault(field, [])
            self.field_validators[field].append(fe_validator)
        else:
            self.chained_validators.append(fe_validator)

    def create_fe_schema(self, instance, type):
        fe_val_schema = formencode.Schema(allow_extra_fields = True)
        fe_conv_schema = formencode.Schema(allow_extra_fields = True)
        for field, validators in self.field_validators.iteritems():
            validators_to_apply = []
            converters_to_apply = []
            for v in validators:
                if should_apply(field, instance, v, type):
                    if getattr(v, '_sv_convert_flag', False):
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

    def get_defaulting_columns(self, instance):
        """
            if we have columns wich are currently None but which have a default
            value on the column, we skip validating them.  A default column,
            since it is set by the programmer, should be valid.

            The real reason we have to do this is that defaults don't get applied
            early enough in the process for us to see what the values are and
            validate them.  The SA DefaultExecutionContext has get_insert_default()
            and get_update_default(), but not sure what kind of issues would
            be involved to have to create an execution context just to get
            default values.

            So, it seems that no validation is better than false positives, so
            we skip it.
        """
        idict = instance.__dict__
        retval = []
        for colname in instance.sa_column_names():
            value = idict.get(colname, None)
            if value is None:
                col = instance.__mapper__.get_property(colname).columns[0]
                if col.default:
                    retval.append(colname)
        return retval

    def validate(self, instance, type):
        if type == 'before_flush':
            instance.clear_validation_errors()
        colnames = instance.sa_column_names()
        fe_val_schema, fe_conv_schema = self.create_fe_schema(instance, type)
        self._validate_schema(instance, colnames, fe_val_schema, False)
        self._validate_schema(instance, colnames, fe_conv_schema, True)

    def _validate_schema(self, instance, colnames, schema, flag_convert):
        idict = {}
        for colname in colnames:
            if schema.fields.has_key(colname):
                idict[colname] = getattr(instance, colname, None)
        try:
            #print '-------------', idict, schema, flag_convert
            processed = schema.to_python(idict, FEState(instance))
            if flag_convert:
                instance.__dict__.update(processed)
            #print '----valid', processed
        except Invalid, e:
            for k,v in e.unpack_errors().iteritems():
                instance._validation_error(k, v)

    #def after_insert(self, mapper, connection, instance):
    #    print 'customer_id', instance, instance.customer_id
    #    return saorm.interfaces.EXT_CONTINUE
    #before_update = before_insert
    #after_insert = before_insert

class ValidationHandler(object):
    default_kwargs = dict()

    def __init__(self, entitycls, *args, **kwargs):
        #print '--- init validation handler'
        self.entitycls = entitycls
        self.validator_ext = entitycls._find_validator_extension()

        # add the Validator mapper extension if needed
        if not self.validator_ext:
            self.validator_ext = Validator()
            entitycls.__mapper__.extension.append(self.validator_ext)
        #print '--- mapper is', object.__repr__(entitycls.__mapper__)
        if self.type == 'field':
            field_names = []
            fe_args = []
            for index, unknown_arg in enumerate(args):
                if self.should_break(unknown_arg):
                    fe_args.append(unknown_arg)
                    break
                field_names.append(unknown_arg)
            fe_args.extend(args[index+1:])
        else:
            field_names = None
            fe_args = args
        self.add_validation_to_extension(field_names, fe_args, **kwargs)

    def add_validation_to_extension(self, field_names, fe_args, **kwargs):
        defer_flag = kwargs.pop('deferred', False)
        new_kwargs = self.default_kwargs.copy()
        new_kwargs.update(kwargs)
        kwargs = new_kwargs
        convert_flag = kwargs.pop('sv_convert', False)
        if field_names is not None:
            for field_to_validate in field_names:
                validator = self.fe_validator(*fe_args, **kwargs)
                # some values only get populated after a flush, we tag these
                # validators here
                if defer_flag:
                    validator._sa_defer_on_none = True
                validator._sv_convert_flag = convert_flag
                self.validator_ext.add_validation(validator, field_to_validate)
        else:
            fe_validator = self.fe_validator(*fe_args, **kwargs)
            self.validator_ext.add_validation(fe_validator, None)

    def should_break(self, unknown_arg):
        return False
