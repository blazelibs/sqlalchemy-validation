import mock
from nose.plugins.skip import SkipTest
from nose.tools import eq_, raises
import sqlalchemy.exc as saexc

import savalidation.tests.examples as ex
from savalidation import ValidationError

class TestFamily(object):

    def tearDown(self):
        # need this to clear the session after the exception catching below
        ex.sess.rollback()
        ex.sess.query(ex.Family).delete()
        ex.sess.commit()

    def test_id_is_auto_increment(self):
        f1 = ex.Family(name=u'f1', reg_num=1)
        ex.sess.add(f1)
        ex.sess.commit()
        f2 = ex.Family(name=u'f2', reg_num=2)
        ex.sess.add(f2)
        ex.sess.commit()
        eq_(f1.id, f2.id - 1)

    def test_edit(self):
        f1 = ex.Family(name=u'test_edit', reg_num=1)
        ex.sess.add(f1)
        ex.sess.commit()
        fid = f1.id
        ex.sess.remove()
        f1 = ex.sess.query(ex.Family).get(fid)
        assert f1.name == 'test_edit'
        f1.status = 'foobar'
        try:
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'status': [u"Value must be one of: active; inactive; moved (not 'foobar')"]}
            eq_(f1.validation_errors, expect)
            eq_(str(e), 'validation error(s): <Family id=1, name=test_edit> [status: "Value must be one of: active; inactive; moved (not \'foobar\')"]')
        f1.status = u'inactive'
        ex.sess.commit()

    @raises(saexc.IntegrityError)
    def test_name_is_unique(self):
        f1 = ex.Family(name=u'f', reg_num=1)
        f2 = ex.Family(name=u'f', reg_num=2)
        ex.sess.add(f1)
        ex.sess.add(f2)
        ex.sess.commit()

    @raises(saexc.IntegrityError)
    def test_reg_num_is_unique(self):
        f1 = ex.Family(name=u'f1', reg_num=1)
        ex.sess.add(f1)
        f2 = ex.Family(name=u'f2', reg_num=1)
        ex.sess.add(f2)
        ex.sess.commit()

    def test_status_default(self):
        f1 = ex.Family(name=u'f1', reg_num=1)
        ex.sess.add(f1)
        ex.sess.commit()
        eq_(f1.status, u'active')
        ex.sess.commit()

    def test_invalid_status(self):
        try:
            f1 = ex.Family(name=u'f1', reg_num=1, status='foobar')
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'status': [u"Value must be one of: active; inactive; moved (not 'foobar')"]}
            eq_(f1.validation_errors, expect)
            eq_(str(e), 'validation error(s): <Family id=None, name=f1> [status: "Value must be one of: active; inactive; moved (not \'foobar\')"]')

    def test_missing_regnum(self):
        try:
            f1 = ex.Family(name=u'f1', status=u'active')
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'reg_num': [u"Please enter a value"]}
            eq_(f1.validation_errors, expect)

    def test_missing_name(self):
        try:
            f1 = ex.Family(reg_num=1, status=u'active')
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'name': [u"Please enter a value"]}
            eq_(f1.validation_errors, expect)

    def test_multiple_invalid_instances(self):
        try:
            f1 = ex.Family(name='f1', status=u'active')
            f2 = ex.Family(name='f2', status=u'active')
            ex.sess.add(f1)
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            eq_(len(e.invalid_instances), 2)
            expect = {'reg_num': [u"Please enter a value"]}
            eq_(f1.validation_errors, expect)
            eq_(f2.validation_errors, expect)

    def test_missing_both(self):
        try:
            f1 = ex.Family()
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'reg_num': [u'Please enter a value'], 'name': [u'Please enter a value']}
            eq_(len(e.invalid_instances), 1)
            eq_(f1.validation_errors, expect)

    def test_name_too_long(self):
        try:
            f1 = ex.Family(name=u'f1'*100, reg_num=1)
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'name': [u'Enter a value less than 75 characters long']}
            eq_(f1.validation_errors, expect)

class TestPerson(object):
    def tearDown(self):
        ex.sess.rollback()

    def test_id_is_auto_increment(self):
        f1 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father', nullable_but_required=u'f')
        ex.sess.add(f1)
        ex.sess.commit()
        f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father', nullable_but_required=u'f')
        f2.name_first = u'foobar'
        ex.sess.add(f2)
        ex.sess.commit()
        eq_(f1.id, f2.id - 1)

    def test_family_role_when_invalid(self):
        try:
            f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'foobar', nullable_but_required=u'f')
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'should have been an exception'
        except ValidationError, e:
            assert f2.validation_errors['family_role'][0].startswith('Value must be one of: father; mother; child')

    def test_first_name_is_too_long(self):
        try:
            f2 = ex.Person(name_first=u'f1'*50, name_last=u'l1', family_role=u'father', nullable_but_required=u'f')
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'should have been an exception'
        except ValidationError, e:
            assert f2.validation_errors['name_first'][0] == 'Enter a value less than 75 characters long'

    def test_nullable_but_required(self):
        # set to None
        try:
            f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father', nullable_but_required=None)
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'should have been an exception'
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'nullable_but_required': [u'Please enter a value']}
            eq_(f2.validation_errors, expect)
        # not given
        try:
            f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father')
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'should have been an exception'
        except ValidationError, e:
            expect = {'nullable_but_required': [u'Please enter a value']}
            eq_(f2.validation_errors, expect)

    @mock.patch('savalidation.tests.examples.Person.get')
    def test_before_flush_decorator_and_mocked_methods(self, m_get):
        p = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father', nullable_but_required=u'a')
        ex.sess.add(p)
        ex.sess.commit()
        eq_(m_get.call_count, 0)

class TestTypes(object):

    def tearDown(self):
        # need this to clear the session after the exception catching below
        ex.sess.rollback()

    def test_integer(self):
        inst = ex.IntegerType(fld=10)
        # this None helps test "missing" verse "value not entered"
        inst.fld2 = None
        ex.sess.add(inst)
        ex.sess.commit()
        inst = ex.IntegerType(fld='5')
        ex.sess.add(inst)
        ex.sess.commit()
        try:
            inst = ex.IntegerType(fld='ten', fld2='ten', fld3='ten')
            ex.sess.add(inst)
            ex.sess.commit()
            assert False, 'expected exception'
        except ValidationError, e:
            expect = {'fld': [u'Please enter an integer value'], 'fld2': [u'Please enter an integer value'], 'fld3': [u'Please enter an integer value']}
            eq_(inst.validation_errors, expect)

    def test_numeric(self):
        inst = ex.NumericType(fld=10.5)
        ex.sess.add(inst)
        ex.sess.commit()
        inst = ex.NumericType(fld='10.5')
        ex.sess.add(inst)
        ex.sess.commit()
        try:
            inst = ex.NumericType(fld='ten dot five', fld2='ten dot five')
            ex.sess.add(inst)
            ex.sess.commit()
            assert False, 'expected exception'
        except ValidationError, e:
            expect = {'fld': [u'Please enter a number'], 'fld2': [u'Please enter a number']}
            eq_(inst.validation_errors, expect)

    def test_date_time(self):
        inst = ex.DateTimeType(fld='9/23/2010', fld3='10:25:33 am', fld2='2010-09-26 10:47:35 pm')
        ex.sess.add(inst)
        ex.sess.commit()
        try:
            inst = ex.DateTimeType(fld='foo', fld3='bar', fld2='baz')
            ex.sess.add(inst)
            ex.sess.commit()
            assert False, 'expected exception'
        except ValidationError, e:
            expect = {'fld2': ['Unknown date/time string "baz"'], 'fld': [u'Please enter the date in the form mm/dd/yyyy'], 'fld3': [u'You must enter minutes (after a :)']}
            eq_(inst.validation_errors, expect)

class TestOrders(object):

    def tearDown(self):
        ex.sess.remove()
        ex.sess.execute('DELETE FROM %s' % ex.Order.__table__)
        ex.sess.execute('DELETE FROM %s' % ex.Order2.__table__)
        ex.sess.execute('DELETE FROM %s' % ex.Customer.__table__)
        ex.sess.commit()

    def test_with_id(self):
        c = ex.Customer(name='ts1')
        ex.sess.add(c)
        ex.sess.flush()
        o = ex.Order(customer_id = c.id)
        ex.sess.add(o)
        ex.sess.commit()
        assert o.customer is c

    def test_with_reference(self):
        c1 = ex.Customer(name='ts1')
        o = ex.Order(customer = c1)
        ex.sess.add(o)
        ex.sess.add(c1)
        ex.sess.commit()
        #assert o.customer is c1

    def test_fk_type_checking(self):
        o = ex.Order(customer_id = 'foobar')
        ex.sess.add(o)
        try:
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'customer_id': [u'Please enter an integer value']}
            eq_(o.validation_errors, expect)

    def test_fk_not_null_checking(self):
        o = ex.Order()
        ex.sess.add(o)
        try:
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'customer_id': [u'Please enter a value']}
            eq_(o.validation_errors, expect)

    def test_order2_with_reference(self):
        c1 = ex.Customer(name='ts1')
        o = ex.Order2(customer = c1)
        ex.sess.add(o)
        ex.sess.add(c1)
        ex.sess.commit()
        assert o.customer is c1

    def test_order2_with_none(self):
        o = ex.Order2()
        ex.sess.add(o)
        try:
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'customer_id': [u'Please enter a value']}
            eq_(o.validation_errors, expect)

class TestUnit(object):

    def tearDown(self):
        # need this to clear the session after the exception catching below
        ex.sess.rollback()
        ex.sess.execute('DELETE FROM %s' % ex.Family.__table__)
        ex.sess.commit()

    def test_inst_col_names(self):
        f1 = ex.Family(name=u'f1', reg_num=1)
        eq_(f1._sav_column_names(), ['id', 'createdts', 'updatedts', 'name', 'reg_num', 'status'])

    def test_class_col_names(self):
        eq_(ex.Family._sav_column_names(), ['id', 'createdts', 'updatedts', 'name', 'reg_num', 'status'])

class TestMixin(object):

    def tearDown(self):
        ex.sess.rollback()
        ex.sess.execute('DELETE FROM %s' % ex.NoMixin.__table__)
        ex.sess.commit()

    def test_no_constructor(self):
        nm = ex.NoMixin()
        nm.name = 'tnc'
        ex.sess.add(nm)
        ex.sess.commit()
        ex.sess.remove()
        nm = ex.sess.query(ex.NoMixin).first()
        assert nm.name == 'tnc', nm.name

    def test_with_constructor(self):
        nm = ex.NoMixin(name='tnc')
        ex.sess.add(nm)
        ex.sess.commit()
        ex.sess.remove()
        nm = ex.sess.query(ex.NoMixin).first()
        assert nm.name == 'tnc', nm.name

class TestConversions(object):
    @classmethod
    def teardown_class(self):
        ex.sess.rollback()
        ex.sess.remove()

    def setUp(self):
        # need this to clear the session after the exception catching below
        ex.sess.rollback()
        ex.sess.execute('DELETE FROM %s' % ex.ConversionTester.__table__)
        ex.sess.commit()

    def test_ok(self):
        e1 = ex.ConversionTester(val1='foo')
        ex.sess.add(e1)
        ex.sess.commit()
        ex.sess.remove()
        e1 = ex.sess.query(ex.ConversionTester).first()
        eq_(e1.val1, 'foo')

    def test_conversion_from_factory(self):
        e1 = ex.ConversionTester(val3='foo')
        ex.sess.add(e1)
        ex.sess.commit()
        ex.sess.remove()
        e1 = ex.sess.query(ex.ConversionTester).first()
        eq_(e1.val3, 'oof')

    def test_conversion_from_factory_with_override(self):
        e1 = ex.ConversionTester(val4='foo')
        ex.sess.add(e1)
        ex.sess.commit()
        ex.sess.remove()
        e1 = ex.sess.query(ex.ConversionTester).first()
        eq_(e1.val4, 'foo')

    def test_conversion_from_kwarg(self):
        e1 = ex.ConversionTester(val2='foo')
        ex.sess.add(e1)
        ex.sess.commit()
        ex.sess.remove()
        e1 = ex.sess.query(ex.ConversionTester).first()
        eq_(e1.val2, 'oof')

    def test_validation_failure(self):
        try:
            e1 = ex.ConversionTester(val3=2)
            ex.sess.add(e1)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            eq_(len(e.invalid_instances), 1)
            expect = {'val3': [u"Must be a string type"]}
            eq_(e1.validation_errors, expect)
