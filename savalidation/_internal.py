import os
import sys
from datetime import datetime
import formencode
from formencode import Invalid
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

def getversion():
    cdir = os.path.abspath(os.path.dirname(__file__))
    return open(os.path.join(cdir, 'version.txt')).read().strip()

def is_iterable(possible_iterable):
    if isinstance(possible_iterable, basestring):
        return False
    try:
        iter(possible_iterable)
        return True
    except TypeError:
        return False
