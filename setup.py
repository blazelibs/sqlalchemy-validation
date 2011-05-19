"""
Introduction
---------------------

SAValidation Facilitates Active Record like validation on SQLAlchemy declarative model
objects.

You can install the `in-development version
<http://bitbucket.org/rsyring/sqlalchemy-validation/get/tip.gz#egg=savlidation-dev>`_
of savalidation with ``easy_install savalidation==dev``.

The home page is currently the `bitbucket repository
<http://bitbucket.org/rsyring/sqlalchemy-validation/>`_.

Usage Example
---------------------

The following is a snippet from the examples.py file::

    from datetime import datetime
    import formencode
    import sqlalchemy as sa
    import sqlalchemy.ext.declarative as sadec
    import sqlalchemy.sql as sasql
    import sqlalchemy.orm as saorm

    from savalidation import declarative_base, ValidatingSessionExtension, \
        ValidationError, ValidationMixin
    import savalidation.validators as val

    engine = sa.create_engine('sqlite://')
    meta = sa.MetaData()
    Base = declarative_base(metadata=meta)

    Session = saorm.scoped_session(
        saorm.sessionmaker(
            bind=engine,
            autoflush=False,
            extension=ValidatingSessionExtension()
        )
    )

    sess = Session

    class Family(Base, ValidationMixin):
        __tablename__ = 'families'

        # SA COLUMNS
        id = sa.Column(sa.Integer, primary_key=True)
        createdts = sa.Column(sa.DateTime, nullable=False, default=datetime.now, server_default=sasql.text('CURRENT_TIMESTAMP'))
        updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
        name =  sa.Column(sa.Unicode(75), nullable=False, unique=True)
        reg_num = sa.Column(sa.Integer, nullable=False, unique=True)
        status =  sa.Column(sa.Unicode(15), nullable=False, default=u'active', server_default=u'active')

        # VALIDATION
        STATUS_CHOICES = (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('moved', 'Moved'),
        )
        # will validate nullability & length of string types
        val.validates_constraints()
        val.validates_one_of('status', [k for k, v in STATUS_CHOICES])

        #OTHER
        def __str__(self):
            return '<Family id=%s, name=%s>' % (self.id, self.name)

    class Person(Base, ValidationMixin):
        __tablename__ = 'people'

        id = sa.Column(sa.Integer, primary_key=True)
        createdts = sa.Column(sa.DateTime, nullable=False, server_default=sasql.text('CURRENT_TIMESTAMP'))
        updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
        name_first = sa.Column(sa.Unicode(75), nullable=False)
        name_last = sa.Column(sa.Unicode(75), nullable=False)
        family_role = sa.Column(sa.Unicode(20), nullable=False)
        nullable_but_required = sa.Column(sa.Unicode(5))
        birthdate = sa.Column(sa.Date)

        ROLE_CHOICES = (
            ('father', 'Father'),
            ('mother', 'Mother'),
            ('child', 'Child'),
        )
        val.validates_constraints(exclude='createdts')
        val.validates_presence_of('nullable_but_required')
        val.validates_choices('family_role', ROLE_CHOICES)
        # will automatically convert the string to a python datetime.date object
        val.converts_date('birthdate')

See more examples in the tests directory of the distribution.

Installing & Testing Source
-----------------------------

(this is one way, there are others)

#. create a virtualenv
#. activate the virtualenv
#. ``pip install -e "hg+http://bitbucket.org/rsyring/sqlalchemy-validation#egg=savlidation-dev"``
#. ``pip install nose``
#. ``cd src/savalidation/savalidation``
#. ``nosetests``

Questions & Comments
---------------------

Please visit: http://groups.google.com/group/blazelibs

Dependencies
--------------
 * SQLAlchemy
 * FormEncode
 * python-dateutil (for date/time converters)
 * Nose (if you want to run the tests)

Credits
---------

This project borrows code and ideas from:

* `Sqlalchemy Validations <http://code.google.com/p/sqlalchemy-validations/>`_
* `Elixir <http://elixir.ematia.de/>`_

Current Status
---------------

The code itself seems stable, but the API is likely to change in the future.

"""

import os
from setuptools import setup, find_packages

# this is here b/c we get import failures if trying to import VERSION from
# savalidation and the venv isn't setup
VERSION = '0.1.3'

setup(
    name='SAValidation',
    version=VERSION,
    description="Active Record like validation on SQLAlchemy declarative model objects",
    long_description=__doc__,
    classifiers=[
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        ],
    author='Randy Syring',
    author_email='rsyring@gmail.com',
    url='http://bitbucket.org/rsyring/sqlalchemy-validation/',
    license='BSD',
    packages=['savalidation'],
    zip_safe=False,
    install_requires=[
        'SQLAlchemy<=0.6.999',
        'python-dateutil>=1.5',
        'FormEncode>=1.2'
    ],
)
