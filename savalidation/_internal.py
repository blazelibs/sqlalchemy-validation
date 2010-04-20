import sys
from datetime import datetime
from dateutil.parser import parse
import formencode
from formencode import Invalid
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

class DateTimeValidator(formencode.validators.FancyValidator):
    
    def validate_python(self, value, state):
        try:
            parse(value)
        except ValueError, e:
            if 'unknown string format' not in str(e):
                raise
            raise Invalid('Unknown date/time string "%s"' % value)

SA_FORMENCODE_MAPPING = {
    sa.types.Integer: formencode.validators.Int,
    sa.types.Numeric: formencode.validators.Number,
    sa.types.DateTime: DateTimeValidator,
    sa.types.Date: DateTimeValidator,
    sa.types.Time: DateTimeValidator,
}

MUTATORS = '__savalidation_mutators__'

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

    def process(self, entity, *args, **kwargs):
        '''
        Process one mutator. This version simply calls the handler callable,
        but another mutator (sub)class could do more processing.
        '''
        self.handler(entity, *args, **kwargs)

def process_mutators(instance):
    '''
    Apply all mutators of the given instance. That is, loop over all mutators
    in the class's mutator list and process them.
    '''
    # we don't use getattr here to not inherit from the parent mutators
    # inadvertantly if the current entity hasn't defined any mutator.
    mutators = instance.__class__.__dict__.get(MUTATORS, [])
    for mutator, args, kwargs in mutators:
        mutator.process(instance, *args, **kwargs)

class ValidationError(Exception):
    """ issued when models are flushed but have validation errors """
    def __init__(self, errors):
        self.errors = errors
        fields_with_errors = []
        for model, fields in errors.iteritems():
            for fname, errors in fields.iteritems():
                fields_with_errors.append('%s.%s' % (model, fname))
        msg = 'validation error(s) on: %s' % ','.join(fields_with_errors)
        Exception.__init__(self, msg)

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
    
    def create_fe_schema(self, instance):
        defaulting_columns = self.get_defaulting_columns(instance)
        fe_schema = formencode.Schema(allow_extra_fields = True)
        #print self.field_validators
        for field, validators in self.field_validators.iteritems():
            if field not in defaulting_columns:
                fe_schema.add_field(field, formencode.compound.All(*validators))
        for fe_validator in self.chained_validators:
            fe_schema.add_chained_validator(fe_validator)
        return fe_schema
    
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
        for colname in instance._column_names:
            value = idict.get(colname, None)
            if value is None:
                col = instance.__mapper__.get_property(colname).columns[0]
                if col.default:
                    retval.append(colname)
        return retval
    
    def validate(self, instance):
        try:
            fe_schema = self.create_fe_schema(instance)
            colnames = instance._column_names
            idict = {}
            for colname in colnames:
                if fe_schema.fields.has_key(colname):
                    idict[colname] = instance.__dict__.get(colname, None)
            #print fe_schema, instance.__dict__
            fe_schema.to_python(idict)
        except Invalid, e:
            for k,v in e.unpack_errors().iteritems():
                instance._validation_error(k, v)
    
    #def before_insert(self, mapper, connection, instance):
    #    try:
    #        validator_extension = instance._find_validator_extension()
    #        if validator_extension:
    #            validator_extension.validate(instance)
    #        errors = instance._get_validation_errors()
    #        if errors:
    #            raise ValidationError({instance.__class__.__name__: errors})
    #    except AttributeError, e:
    #        if '_find_validator_extension' not in str(e):
    #            raise
    #    return saorm.interfaces.EXT_CONTINUE
    #before_update = before_insert

class ValidationHandler(object):
    default_kwargs = dict()
    
    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        self.validator_ext = instance._find_validator_extension()
        
        # add the Validator mapper extension if needed
        if not self.validator_ext:
            self.validator_ext = Validator()
            instance.__mapper__.extension.append(self.validator_ext)
        
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
        new_kwargs = self.default_kwargs.copy()
        new_kwargs.update(kwargs)
        kwargs = new_kwargs
        if field_names is not None:
            for field_to_validate in field_names:
                self.validator_ext.add_validation(self.fe_validator(*fe_args, **kwargs), field_to_validate)
        else:
           self.validator_ext.add_validation(self.fe_validator(*fe_args, **kwargs), None) 
    
    def should_break(self, unknown_arg):
        return False
    