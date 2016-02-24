Change Log
----------


0.3.1 released 2016-02-23
=========================

* fix formencode compatibility, supports formencode 1.2 and 1.3

0.3.0 released 2014-09-30
=========================

* fix bug with .validates_constraints() and Text column types
* watch_session() is no longer needed, SQLAlchemy >= 0.7.6 required
* now beta quality: been used in production a long time, but not used widely

0.2.1 released 2013-05-15
=========================

* fixed issue #6 - adjustment to the version of python-dateutil required.

0.2.0 released 2012-10-24
=========================

This release contains some **BC BREAKS**.

* internal API cleaned up
* refactored to use SQLAlchemy (SA) events, we are now compatable with & require
  SA >= 0.7
* CHANGE: if using SA < 0.7.6, savalidation.watch_session() must be called with each
  instance of your session IF the savalidation module is being instantiated
  before your session is created.
* CHANGE: the validator API has changed.  If you have created custom validators
  you will need to look at the changes in validators.py.
* the Formencode state object sent to a validator's method has changed the
  "instance" attribute to be "entity."
* add before_flush() helper to decorate entity instance methods
* got rid of after_flush validation.  Instead, before_insert/before_update events
    can now be used to validate non-nullable foreign keys.
* got rid of validation support for a column's default and server_default
    values (b/c it required after_flush validation)
* formencode schemas are now only created once per class, not per instance,
    boosting performance.

0.1.5 released 2011-06-11
=========================

* fix 0.1.4 release which didn't include version file

0.1.4 released 2011-06-11
=========================

* change python-dateutil dependence to < 2.0, 2.x is for python 3

0.1.3 released 2011-05-19
=========================

* change SQLAlchemy requirement so the latest package < 0.7 is installed
