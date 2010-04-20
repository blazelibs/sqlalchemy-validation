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

def blow_up(*args, **kwargs):
    assert False, 'blow_up called'
    
class Family(Base):
    __tablename__ = 'families'
    
    id = sa.Column(sa.Integer, primary_key=True)
    createdts = sa.Column(sa.DateTime, nullable=False, server_default=sasql.text('CURRENT_TIMESTAMP'))
    updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
    name =  sa.Column(sa.Unicode(75), nullable=False, unique=True)
    reg_num = sa.Column(sa.Integer, nullable=False, unique=True)
    status =  sa.Column(sa.Unicode(15), nullable=False, default=u'active', server_default=u'active')
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('moved', 'Moved'),
    )

    val.validates_auto('length')
    val.validates_presence_of('name', 'reg_num')
    val.validates_one_of('status', [k for k, v in STATUS_CHOICES])

class Person(Base):
    __tablename__ = 'people'
    
    id = sa.Column(sa.Integer, primary_key=True)
    createdts = sa.Column(sa.DateTime, nullable=False, server_default=sasql.text('CURRENT_TIMESTAMP'))
    updatedts = sa.Column(sa.DateTime, onupdate=datetime.now)
    name_first = sa.Column(sa.Unicode(75), nullable=False)
    name_last = sa.Column(sa.Unicode(75), nullable=False)
    family_role = sa.Column(sa.Unicode(20), nullable=False)
    
    ROLE_CHOICES = (
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('child', 'Child'),
    )
    val.validates_auto('length', 'nullable')
    val.validates_presence_of('family_role', 'name_last')
    val.validates_choices('family_role', ROLE_CHOICES)

meta.create_all(bind=engine)