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

class TestPerson(object):
    def tearDown(self):
        ex.sess.rollback()
    
    def test_id_is_auto_increment(self):
        f1 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father')
        ex.sess.add(f1)
        ex.sess.commit()
        f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'father')
        f2.name_first = u'foobar'
        ex.sess.add(f2)
        ex.sess.commit()
        eq_(f1.id, f2.id - 1)
    
    def test_family_role_when_invalid(self):
        try:
            f2 = ex.Person(name_first=u'f1', name_last=u'l1', family_role=u'foobar')
            ex.sess.add(f2)
            ex.sess.commit()
            assert False, 'should have been an exception'
        except ValidationError, e:
            assert e.errors['Person']['family_role'][0].startswith('Value must be one of: father; mother; child')

    def test_first_name_is_too_long(self):
        try:
            f2 = ex.Person(name_first=u'f1'*50, name_last=u'l1', family_role=u'father')
            ex.sess.add(f2)
            ex.sess.commit()
        except ValidationError, e:
            assert e.errors['Person']['name_first'][0] == 'Enter a value less than 75 characters long'