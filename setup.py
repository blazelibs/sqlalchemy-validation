import os
from setuptools import setup, find_packages

cdir = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(cdir, 'readme.rst')).read()
CHANGELOG = open(os.path.join(cdir, 'changelog.rst')).read()
VERSION = open(os.path.join(cdir, 'savalidation', 'version.txt')).read().strip()

setup(
    name='SAValidation',
    version=VERSION,
    description="Active Record like validation on SQLAlchemy declarative model objects",
    long_description=README + '\n\n' + CHANGELOG,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Database',
        ],
    author='Randy Syring',
    author_email='rsyring@gmail.com',
    url='http://bitbucket.org/rsyring/sqlalchemy-validation/',
    license='BSD',
    packages=['savalidation'],
    zip_safe=False,
    install_requires=[
        # SA 0.7 breaks us :(
        'SQLAlchemy<=0.6.999',
        # version 2 is out for PY 3, but the notes say to use 1.x for PY 2.x
        'python-dateutil<=1.9.999',
        'FormEncode>=1.2'
    ],
)
