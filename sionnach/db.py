"""
SQLAlchemy ORM bindings for DB objects
"""
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Help(Base):
    """
    Holds helpfile text (including various static fixtures, like the MOTD)
    """

    __tablename__ = "help"
    id = Column(Integer, primary_key=True)

    # Main helpfile name
    name = Column(String)

    # Optional other keywords for this file
    keywords = Column(String)

    # Helpfile text
    text = Column(Text)


class User(Base):
    """
    Holds user info
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    password = Column(String)
