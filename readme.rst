Introduction
------------

SAValidation facilitates Active Record like validation on SQLAlchemy declarative model
objects.

You can install the `in-development version
<http://bitbucket.org/blazelibs/sqlalchemy-validation/get/tip.gz#egg=savalidation-dev>`_
of savalidation with ``easy_install savalidation==dev``.

The home page is currently the `bitbucket repository
<http://bitbucket.org/blazelibs/sqlalchemy-validation/>`_.

Usage Example
-------------

The following is a snippet from the examples.py file:

.. code-block:: python

    from datetime import datetime
    import formencode
    import sqlalchemy as sa
    import sqlalchemy.ext.declarative as sadec
    import sqlalchemy.sql as sasql
    import sqlalchemy.orm as saorm

    from savalidation import ValidationMixin, watch_session
    import savalidation.validators as val

    engine = sa.create_engine('sqlite://')
    #engine.echo = True
    meta = sa.MetaData()
    Base = sadec.declarative_base(metadata=meta)

    Session = saorm.scoped_session(
        saorm.sessionmaker(
            bind=engine,
            autoflush=False
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
        # will validate nullability and string types
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

        ROLE_CHOICES = (
            ('father', 'Father'),
            ('mother', 'Mother'),
            ('child', 'Child'),
        )
        val.validates_constraints(exclude='createdts')
        val.validates_presence_of('nullable_but_required')
        val.validates_choices('family_role', ROLE_CHOICES)

    class ReverseConverter(formencode.api.FancyValidator):
        def _to_python(self, value, state):
            if not isinstance(value, basestring):
                raise formencode.Invalid('Must be a string type', value, state)
            # this reverse a string or list...yah, I know, it looks funny
            return value[::-1]

    validates_reverse = val.formencode_factory(ReverseConverter)
    converts_reverse = val.formencode_factory(ReverseConverter, sv_convert=True)

    class ConversionTester(Base, ValidationMixin):
        __tablename__ = 'conversion_testers'

        id = sa.Column(sa.Integer, primary_key=True)
        val1 = sa.Column(sa.String(25))
        val2 = sa.Column(sa.String(25))
        val3 = sa.Column(sa.String(25))
        val4 = sa.Column(sa.String(25))

        validates_reverse('val1')
        validates_reverse('val2', sv_convert=True)
        converts_reverse('val3')
        converts_reverse('val4', sv_convert=False)

See more examples in the tests directory of the distribution.

Installing & Testing Source
---------------------------

(this is one way, there are others)

.. code-block:: bash

    # create a virtualenv
    # activate the virtualenv

    $ pip install -e "hg+http://bitbucket.org/blazlibs/sqlalchemy-validation#egg=savlidation-dev"
    $ pip install nose
    $ cd src/savalidation/savalidation
    $ nosetests

Questions & Comments
--------------------

Please visit: http://groups.google.com/group/blazelibs

Known Issues
------------

Final values that get set on an ORM mapped object attributes through
relationships, the default or onupdate column parameters, and possibly others
are not availble at the time validation is done.

In some cases, this can be caught after the flush (before commit) when those
values become available on the ORM object.

Unfortunately, that is of limited value in the case where the the value that
slipped through violates a DB constraint.  In that case, a true DB exception
will be raised.

Dependencies
------------

* SQLAlchemy > 0.7.6
* FormEncode
* python-dateutil (for date/time converters)
* Nose (if you want to run the tests)

Credits
-------

This project borrows code and ideas from:

* `Sqlalchemy Validations <http://code.google.com/p/sqlalchemy-validations/>`_
* `Elixir <http://elixir.ematia.de/>`_

Current Status
--------------

The code itself seems stable, but the API may change in the future.
