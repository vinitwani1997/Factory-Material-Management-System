"""
Models for: suppliers, customers
"""

from sqlalchemy import Column, Integer, String, Text
from app.database.connection import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_number = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    gst_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_number = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    gst_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
