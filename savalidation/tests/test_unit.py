try:
    import cPickle as pickle
except ImportError:
    import pickle
import gc
import weakref

from nose.plugins.skip import SkipTest
from nose.tools import eq_, raises
import sqlalchemy.exc as saexc

from savalidation import EntityRefMissing, ValidationError
import savalidation.tests.examples as ex

class TestWeakReferences(object):

    @classmethod
    def setup_class(self):
        ex.sess.expunge_all()

    def test_weak_ref(self):
        assert not ex.sess.identity_map

        # add an object
        ex.sess.add(ex.SomeObj())
        ex.sess.commit()
        ex.sess.expunge_all()

        # make sure its in the db
        assert ex.sess.query(ex.SomeObj).count() == 1

        # since we expunged above, we still shouldn't have anything in the
        # session's identity map
        assert not ex.sess.identity_map

        so = ex.sess.query(ex.SomeObj).first()
        assert len(ex.sess.identity_map) == 1

        # delete our reference, which should make the the weakly referenced
        # object drop out of the identity map
        del so

        # nothing left
        assert not ex.sess.identity_map

    def test_reference_lost_exception(self):
        vh = ex.SomeObj()._sav
        try:
            vh.entity
            assert False, 'expected exception'
        except EntityRefMissing:
            pass

    def test_pickling(self):
        so = ex.SomeObj(minlen=5)
        assert so._sav.entity.minlen == 5
        pstr = pickle.dumps(so)
        del so

        so2 = pickle.loads(pstr)
        assert so2._sav.entity.minlen == 5

        # make sure it's a weakref
        vh = so2._sav
        del so2
        gc.collect()

        try:
            vh.entity
            assert False, 'expected exception'
        except EntityRefMissing:
            pass

class TestBeforeFlushHelper(object):
    def setUp(self):
        ex.sess.query(ex.Person).delete()

    def test_before_flush(self):
        p = ex.Person(
            name_first = u'randy',
            name_last = u'foo',
            family_role = u'father',
            nullable_but_required = u'ab',
        )
        ex.sess.add(p)
        ex.sess.commit()
        ex.sess.remove()
        eq_(ex.sess.query(ex.Person).first().name_first, 'randall')

    def test_with_validation(self):
        p = ex.Person(
            name_first = u'ughhh',
            name_last = u'Obama',
            family_role = u'father',
            nullable_but_required = u'ab',
        )
        ex.sess.add(p)
        try:
            ex.sess.commit()
            assert False, 'exepcted exception'
        except ValidationError, e:
            ex.sess.rollback()
            eq_(len(e.invalid_instances), 1)
            expect = {'name_first': [u'must be "President"']}
            eq_(p.validation_errors, expect)

    def test_only_called_for_before_flush(self):
        p = ex.Person(
            name_first = u'f',
            name_last = u'l',
            family_role = u'father',
            nullable_but_required = u'ab',
        )
        ex.sess.add(p)
        ex.sess.commit()
        # make sure the validator only fired once.  This makes sure we don't
        # fire before_flush methods for after_flush too
        eq_(p.enforce_president_call_count, 1)

    def test_with_no_entity_linkers(self):
        c = ex.Customer(
            name = u'Sam',
        )
        ex.sess.add(c)
        try:
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            eq_(len(e.invalid_instances), 1)
            expect = {'name': [u'Sam not allowed']}
            eq_(c.validation_errors, expect)


class TestFESchemas(object):

    def test_convert_flag(self):
        ex.ConversionTester()
        schemas = ex.ConversionTester._sav_fe_schemas
        # validation
        eq_(set(schemas['before_flush'][0].fields.keys()), set(['val1', 'val4']))
        # conversion
        eq_(set(schemas['before_flush'][1].fields.keys()), set(['val2', 'val3']))
