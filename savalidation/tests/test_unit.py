from nose.plugins.skip import SkipTest
from nose.tools import eq_, raises
import sqlalchemy.exc as saexc

from savalidation import EntityRefMissing
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
        except EntityRefMissing:
            pass
