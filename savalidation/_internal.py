from __future__ import absolute_import
import os
import six


def getversion():
    cdir = os.path.abspath(os.path.dirname(__file__))
    return open(os.path.join(cdir, 'version.txt')).read().strip()


def is_iterable(possible_iterable):
    if isinstance(possible_iterable, six.string_types):
        return False
    try:
        iter(possible_iterable)
        return True
    except TypeError:
        return False
