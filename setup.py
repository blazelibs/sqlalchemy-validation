import os
from setuptools import setup, find_packages

version = '0.1-dev'

doc_dir = os.path.join(os.path.dirname(__file__), 'docs')
index_filename = os.path.join(doc_dir, 'index.txt')
long_description = open(index_filename).read()

setup(name='savalidation',
      version=version,
      description="Active Record like validation on SQLAlchemy declarative model objects",
      long_description=long_description,
      classifiers=[
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        ], 
      author='Randy Syring',
      author_email='rsyring@gmail.com',
      url='http://bitbucket.org/rsyring/sqlalchemy-validation',
      license='BSD',
      packages=['savalidation'],
      zip_safe=False,
      )
