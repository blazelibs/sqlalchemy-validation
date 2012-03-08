Change Log
----------

0.2.0 released ???
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

0.1.5 released 2011-06-11
=========================

* fix 0.1.4 release which didn't include version file

0.1.4 released 2011-06-11
=========================

* change python-dateutil dependence to < 2.0, 2.x is for python 3

0.1.3 released 2011-05-19
=========================

* change SQLAlchemy requirement so the latest package < 0.7 is installed
