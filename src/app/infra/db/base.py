"""
SQLAlchemy declarative base.

All ORM mapped classes import Base from here.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
