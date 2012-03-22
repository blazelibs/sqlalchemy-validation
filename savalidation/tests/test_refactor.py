from datetime import datetime
import formencode
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

import mock
from nose.plugins.skip import SkipTest
from nose.tools import eq_, raises
import sqlalchemy.exc as saexc

from savalidation import ValidationError, ValidationMixin
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

    id = sa.Column(sa.Integer, primary_key=True)
    name =  sa.Column(sa.Unicode(75), nullable=False, unique=True)
    reg_num = sa.Column(sa.Integer, nullable=False, unique=True)

    val.validates_required('name')
    val.validates_constraints()

class Customer(Base, ValidationMixin):
    __tablename__ = 'customer'

    # SA COLUMNS
    id = sa.Column(sa.Integer, primary_key=True)
    name =  sa.Column(sa.String(75), nullable=False)

    orders = saorm.relationship('Order', backref='customer', lazy=False)

    #OTHER
    def __str__(self):
        return '<Customer id=%s, name=%s>' % (self.id, self.name)

class Order(Base, ValidationMixin):
    __tablename__ = 'orders'

    id = sa.Column(sa.Integer, primary_key=True)
    customer_id = sa.Column(sa.Integer, sa.ForeignKey(Customer.id), nullable=False)

    val.validates_required('customer_id', sav_event='before_exec')

class IPAddress(Base, ValidationMixin):
    __tablename__ = 'ipaddresses'

    id = sa.Column(sa.Integer, primary_key=True)
    ip1 =  sa.Column(sa.String(75), nullable=False)
    ip2 =  sa.Column(sa.String(75))

    val.validates_ipaddr('ip1', 'ip2')

meta.create_all(bind=engine)

class TestStuff(object):

    def tearDown(self):
        # need this to clear the session after the exception catching below
        sess.rollback()
        sess.query(Family).delete()
        sess.commit()
        sess.remove()

    def test_id_is_auto_increment(self):
        f1 = Family(name=u'f1', reg_num=3)
        sess.add(f1)
        sess.commit()
        f2 = Family(name=u'f2', reg_num=2)
        sess.add(f2)
        sess.commit()
        eq_(f1.id, f2.id - 1)

    def test_edit(self):
        f1 = Family(name=u'test_edit', reg_num=1)
        sess.add(f1)
        sess.commit()
        fid = f1.id
        sess.remove()
        f1 = sess.query(Family).get(fid)
        assert f1.name == 'test_edit'
        f1.name = None
        try:
            sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            sess.rollback()
            expect = {'name': [u"Please enter a value"]}
            eq_(f1.validation_errors, expect)

    def test_fk_required(self):
        o = Order(customer_id=None)
        sess.add(o)
        try:
            sess.commit()
            assert False
        except ValidationError, e:
            sess.rollback()
            expect = {'customer_id': [u'Please enter a value']}
            eq_(o.validation_errors, expect)

    def test_auto_not_empty_validation(self):
        o = IPAddress(ip1='foo', ip2='bar')
        sess.add(o)
        try:
            sess.commit()
            assert False
        except ValidationError, e:
            sess.rollback()
            expect = {'ip1': ['Please enter a valid IP address (a.b.c.d)'],
                'ip2': ['Please enter a valid IP address (a.b.c.d)']
            }
            eq_(o.validation_errors, expect)

    def test_auto_not_empty_validation2(self):
        o = IPAddress(ip1='192.168.200.1', ip2=None)
        sess.add(o)
        sess.commit()

    def test_only_one_validation_error(self):
        o = IPAddress(ip1='192.168.200.1', ip2='')
        sess.add(o)
        try:
            sess.commit()
            assert False
        except ValidationError, e:
            sess.rollback()
            expect = {'ip1': ['Please enter a valid IP address (a.b.c.d)'],
                'ip2': ['Please enter a valid IP address (a.b.c.d)']
            }
            eq_(len(e.invalid_instances), 1)
