from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from piccolo.config import DATABASE

Base = declarative_base()

sqlite_db = create_engine('sqlite:///' +  DATABASE)
Session = scoped_session(sessionmaker(bind=sqlite_db))