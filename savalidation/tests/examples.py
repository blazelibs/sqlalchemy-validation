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
#engine.echo = True
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

class IntegerType(Base, ValidationMixin):
    __tablename__ = 'IntegerType'
    id = sa.Column(sa.Integer, primary_key=True)
    fld = sa.Column(sa.Integer)
    fld2 = sa.Column(sa.SmallInteger)
    fld3 = sa.Column(sa.BigInteger)

    val.validates_constraints()

class NumericType(Base, ValidationMixin):
    __tablename__ = 'NumericType'
    id = sa.Column(sa.Integer, primary_key=True)
    fld = sa.Column(sa.Numeric)
    fld2 = sa.Column(sa.Float)

    val.validates_constraints()

class DateTimeType(Base, ValidationMixin):
    __tablename__ = 'DateTimeType'
    id = sa.Column(sa.Integer, primary_key=True)
    fld = sa.Column(sa.Date)
    fld2 = sa.Column(sa.DateTime)
    fld3 = sa.Column(sa.Time)

    val.converts_date('fld')
    val.converts_datetime('fld2')
    val.converts_time('fld3')

class Customer(Base, ValidationMixin):
    __tablename__ = 'customer'

    # SA COLUMNS
    id = sa.Column(sa.Integer, primary_key=True)
    name =  sa.Column(sa.String(75), nullable=False)

    orders = saorm.relationship('Order', backref='customer', lazy=False)
    orders2 = saorm.relationship('Order2', backref='customer', lazy=False)

    #OTHER
    def __str__(self):
        return '<Customer id=%s, name=%s>' % (self.id, self.name)

class Order(Base, ValidationMixin):
    __tablename__ = 'orders'

    id = sa.Column(sa.Integer, primary_key=True)
    customer_id = sa.Column(sa.Integer, sa.ForeignKey(Customer.id), nullable=False)
    createdts = sa.Column(sa.DateTime, nullable=False, default=datetime.now, server_default=sasql.text('CURRENT_TIMESTAMP'))

    val.validates_constraints()

class Order2(Base, ValidationMixin):
    __tablename__ = 'orders2'

    id = sa.Column(sa.Integer, primary_key=True)
    customer_id = sa.Column(sa.Integer, sa.ForeignKey(Customer.id))
    createdts = sa.Column(sa.DateTime, nullable=False, server_default=sasql.text('CURRENT_TIMESTAMP'))

    val.validates_constraints()
    # if the value is None, the validation will be deferred until after a
    # flush() is executed on the session.  Useful for default values and
    # relations where the value doesn't show up as an attribute until a flush()
    # is issues. NOTE: This only works when the DB doesn't issue exceptions
    # for the value sent.  If you try to send NULL, to a non-nullable column,
    # then you will get an IntegrityError.
    val.validates_presence_of('customer_id', deferred=True)


class NoMixin(Base):
    __tablename__ = 'nomixin'

    id = sa.Column(sa.Integer, primary_key=True)
    name =  sa.Column(sa.String(75), nullable=False)

class SomeObj(Base, ValidationMixin):
    __tablename__ = 'some_objs'

    id = sa.Column(sa.Integer, primary_key=True)
    minlen = sa.Column(sa.String(25))
    ipaddr = sa.Column(sa.String(15))
    url = sa.Column(sa.String(50))

    val.validates_constraints()
    val.validates_minlen('minlen', 20)
    val.validates_ipaddr('ipaddr')
    val.validates_url('url')

class ReverseConverter(formencode.api.FancyValidator):
    def _to_python(self, value, state):
        if not isinstance(value, basestring):
            raise formencode.Invalid('Must be a string type', value, state)
        # this reverse a string or list...yah, I know, it looks funny
        return value[::-1]

validates_reverse = val._formencode_validator_factory(ReverseConverter)
converts_reverse = val._formencode_validator_factory(ReverseConverter, sv_convert=True)

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

meta.create_all(bind=engine)
