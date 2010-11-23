"""
Introduction
---------------------

SAValidation Facilitates Active Record like validation on SQLAlchemy declarative model
objects.

You can install the `in-development version
<http://bitbucket.org/rsyring/sqlalchemy-validation/get/tip.gz#egg=savlidation-dev>`_
of savalidation with ``easy_install savalidation==dev``.

The home page is currently the `bitbucket repository
<http://bitbucket.org/rsyring/sqlalchemy-validation/>`_.

Questions & Comments
---------------------

Please visit: http://groups.google.com/group/blazelibs

Dependencies
--------------
 * SQLAlchemy
 * FormEncode
 * Nose (if you want to run the tests)

Credits
---------

This project borrows code and ideas from:

* `Sqlalchemy Validations <http://code.google.com/p/sqlalchemy-validations/>`_
* `Elixir <http://elixir.ematia.de/>`_

Current Status
---------------

The code itself seems stable, but the API is likely to change in the future.

"""

import os
from setuptools import setup, find_packages

# this is here b/c we get import failures if trying to import VERSION from
# savalidation and the venv isn't setup
VERSION = '0.1'

setup(name='SAValidation',
      version=VERSION,
      description="Active Record like validation on SQLAlchemy declarative model objects",
      long_description=__doc__,
      classifiers=[
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        ],
      author='Randy Syring',
      author_email='rsyring@gmail.com',
      url='http://bitbucket.org/rsyring/sqlalchemy-validation/',
      license='BSD',
      packages=['savalidation'],
      zip_safe=False,
      install_requires=[
          'SQLAlchemy>=0.6.2',
          'python-dateutil>=1.5'
      ],
      )
