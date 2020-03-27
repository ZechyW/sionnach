"""
Utility functions
"""
from sqlalchemy.orm.exc import NoResultFound

from sionnach.db import Help


def get_helpfile(db, name):
    """
    Retrieve the helpfile/static text from the given DB with the given name
    :param db: SQLAlchemy database session
    :param name: Helpfile/text file name
    :return:
    """
    try:
        return db.query(Help).filter(Help.name == name).one().text
    except NoResultFound:
        return f"'{name}' not found."
