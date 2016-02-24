import mock
from nose.tools import eq_
import sqlalchemy.exc as saexc
import examples as ex
from savalidation import ValidationError
import savalidation.validators as sav

class TestValidators(object):

    def test_min_length(self):
        so = ex.SomeObj(minlen='a'*20)
        ex.sess.add(so)
        ex.sess.commit()

        try:
            so = ex.SomeObj(minlen='a'*19)
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'minlen': [u'Enter a value at least 20 characters long']}
            eq_(e.invalid_instances[0].validation_errors, expect)

        # None works b/c its a nullable field
        so = ex.SomeObj(minlen=None)
        ex.sess.add(so)
        ex.sess.commit()

        # empty string should not work
        try:
            so = ex.SomeObj(minlen='')
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'minlen': [u'Enter a value at least 20 characters long']}
            eq_(e.invalid_instances[0].validation_errors, expect)

    def test_ip_addr(self):
        so = ex.SomeObj(ipaddr='127.0.0.1')
        ex.sess.add(so)
        ex.sess.commit()

        try:
            so = ex.SomeObj(ipaddr='127.0.0')
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'ipaddr': [u'Please enter a valid IP address (a.b.c.d)']}
            eq_(e.invalid_instances[0].validation_errors, expect)

        # None works b/c its a nullable field
        so = ex.SomeObj(ipaddr=None)
        ex.sess.add(so)
        ex.sess.commit()

        # empty string should not work
        try:
            so = ex.SomeObj(ipaddr='')
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'ipaddr': [u'Please enter a valid IP address (a.b.c.d)']}
            eq_(e.invalid_instances[0].validation_errors, expect)


    def test_url(self):
        so = ex.SomeObj(url='http://www.example.com/')
        ex.sess.add(so)
        ex.sess.commit()

        try:
            so = ex.SomeObj(url='foobar')
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'url': [u'You must provide a full domain name (like foobar.com)']}
            eq_(e.invalid_instances[0].validation_errors, expect)

        # None works b/c its a nullable field
        so = ex.SomeObj(url=None)
        ex.sess.add(so)
        ex.sess.commit()

        # empty string should not work
        try:
            so = ex.SomeObj(url='')
            ex.sess.add(so)
            ex.sess.commit()
            assert False
        except ValidationError, e:
            ex.sess.rollback()
            expect = {'url': [u'That is not a valid URL']}
            eq_(e.invalid_instances[0].validation_errors, expect)

class TestValidatorBase(object):

    @mock.patch('savalidation.validators.ValidatorBase.fe_validator')
    def test_convert_flag_from_entity_linker_arg(self, m_fe_validator):
        vb = sav.ValidatorBase(ex.ConversionTester, 'val2', sv_convert=True)
        m_fe_validator.assert_called_once_with()
        eq_(len(vb.fev_metas), 1)
        eq_(vb.fev_metas[0].is_converter, True)

    @mock.patch('savalidation.validators.ValidatorBase.fe_validator')
    @mock.patch('savalidation.validators.ValidatorBase.default_kwargs', wraps={'sv_convert': True})
    def test_convert_flag_from_formencode_factory(self, m_default_kwargs, m_fe_validator):
        vb = sav.ValidatorBase(ex.ConversionTester, 'val3')
        m_fe_validator.assert_called_once_with()
        eq_(len(vb.fev_metas), 1)
        eq_(vb.fev_metas[0].is_converter, True)

