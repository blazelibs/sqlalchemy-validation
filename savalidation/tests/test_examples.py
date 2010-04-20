from nose.tools import eq_, raises
import sqlalchemy.exc as saexc
import examples as ex
from savalidation import ValidationError

class TestFamily(object):
    
    def tearDown(self):
        # need this to clear the session after the exception catching below
        ex.sess.rollback()
        ex.sess.execute('DELETE FROM %s' % ex.Family.__table__)
        ex.sess.commit()
        
    def test_id_is_auto_increment(self):
        f1 = ex.Family(name=u'f1', reg_num=1)
        ex.sess.add(f1)
        ex.sess.commit()
        f2 = ex.Family(name=u'f2', reg_num=2)
        ex.sess.add(f2)
        ex.sess.commit()
        eq_(f1.id, f2.id - 1)
    
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
            expect = {'Family': {'status': [u"Value must be one of: active; inactive; moved (not 'foobar')"]}}
            eq_(e.errors, expect)
            
    def test_missing_regnum(self):
        try:
            f1 = ex.Family(name=u'f1', status=u'active')
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'Family': {'reg_num': [u"Missing value"]}}
            eq_(e.errors, expect)
            
    def test_missing_name(self):
        try:
            f1 = ex.Family(reg_num=1, status=u'active')
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'Family': {'name': [u"Missing value"]}}
            eq_(e.errors, expect)
            
    def test_missing_both(self):
        try:
            f1 = ex.Family()
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'Family': {'reg_num': [u'Missing value'], 'name': [u'Missing value']}}
            eq_(e.errors, expect)
    
    def test_name_too_long(self):
        try:
            f1 = ex.Family(name=u'f1'*100, reg_num=1)
            ex.sess.add(f1)
            ex.sess.commit()
            assert False, 'exception expected'
        except ValidationError, e:
            expect = {'Family': {'name': [u'Enter a value less than 75 characters long']}}
            eq_(e.errors, expect)

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
            assert e.errors['Person']['family_role'][0].startswith('Value must be one of: father; mother; child')

    def test_first_name_is_too_long(self):
        try:
            f2 = ex.Person(name_first=u'f1'*50, name_last=u'l1', family_role=u'father', nullable_but_required=u'f')
            ex.sess.add(f2)
            ex.sess.commit()
        except ValidationError, e:
            assert e.errors['Person']['name_first'][0] == 'Enter a value less than 75 characters long'
    
    def test_nullable_but_required(self):
        try:
            f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father')
            ex.sess.add(f2)
            ex.sess.commit()
        except ValidationError, e:
            expect = {'Person': {'nullable_but_required': [u'Missing value']}}
            eq_(e.errors, expect)