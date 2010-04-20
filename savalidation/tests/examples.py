from datetime import datetime
import sqlalchemy as sa
import sqlalchemy.ext.declarative as sadec
import sqlalchemy.sql as sasql
import sqlalchemy.orm as saorm

from savalidation import declarative_base, ValidatingSessionExtension, ValidationError
import savalidation.validators as val

engine = sa.create_engine('sqlite://')
#engine.echo = True
meta = sa.MetaData()
Base = declarative_base(metadata=meta)

Session = saorm.sessionmaker(
    bind=engine,
    autoflush=False,
    extension=ValidatingSessionExtension()
)

sess = Session()

class Family(Base):
    __tablename__ = 'families'
    
    id = sa.Column(sa.Integer, primary_key=True)
    createdts = sa.Column(sa.DateTime, nullable=False, default=datetime.now, server_default=sasql.text('CURRENT_TIMESTAMP'))
    updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
    name =  sa.Column(sa.Unicode(75), nullable=False, unique=True)
    reg_num = sa.Column(sa.Integer, nullable=False, unique=True)
    status =  sa.Column(sa.Unicode(15), nullable=False, default=u'active', server_default=u'active')
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('moved', 'Moved'),
    )
    val.validates_constraints()
    val.validates_one_of('status', [k for k, v in STATUS_CHOICES])

class Person(Base):
    __tablename__ = 'people'
    
    id = sa.Column(sa.Integer, primary_key=True)
    createdts = sa.Column(sa.DateTime, nullable=False, server_default=sasql.text('CURRENT_TIMESTAMP'))
    updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
    name_first = sa.Column(sa.Unicode(75), nullable=False)
    name_last = sa.Column(sa.Unicode(75), nullable=False)
    family_role = sa.Column(sa.Unicode(20), nullable=False)
    nullable_but_required = sa.Column(sa.Unicode(5))
    
    ROLE_CHOICES = (
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('child', 'Child'),
    )
    val.validates_constraints(exclude='createdts')
    val.validates_presence_of('nullable_but_required')
    val.validates_choices('family_role', ROLE_CHOICES)

class IntegerType(Base):
    __tablename__ = 'IntegerType'
    id = sa.Column(sa.Integer, primary_key=True)
    fld = sa.Column(sa.Integer)
    fld2 = sa.Column(sa.SmallInteger)
    fld3 = sa.Column(sa.BigInteger)
    val.validates_constraints()
    
class NumericType(Base):
    __tablename__ = 'NumericType'
    id = sa.Column(sa.Integer, primary_key=True)
    fld = sa.Column(sa.Numeric)
    fld2 = sa.Column(sa.Float)
    val.validates_constraints()

meta.create_all(bind=engine)