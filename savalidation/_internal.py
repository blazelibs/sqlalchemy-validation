import sys
from datetime import datetime
import formencode
from formencode import Invalid
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

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

### SQLAlchemy mapper extension
class Validator(saorm.interfaces.MapperExtension):
    def __init__(self, *args):
        saorm.interfaces.MapperExtension.__init__(self)
        self.fe_schema = formencode.Schema(allow_extra_fields = True)
    
    def add_validation(self, fe_validator, field):
        if field:
            self.fe_schema.add_field(field, fe_validator)
        else:
            self.fe_schema.add_chained_validator(fe_validator)
    
    def validate(self, instance):
        try:
            self.fe_schema.to_python(instance.__dict__)
        except Invalid, e:
            for k,v in e.unpack_errors().iteritems():
                instance._validation_error(k, v)

class ValidationHandler(object):
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
        if field_names is not None:
            for field_to_validate in field_names:
                self.validator_ext.add_validation(self.fe_validator(*fe_args, **kwargs), field_to_validate)
        else:
           self.validator_ext.add_validation(self.fe_validator(*fe_args, **kwargs), None) 
    
    def should_break(self, unknown_arg):
        return False
    