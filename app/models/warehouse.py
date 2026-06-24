"""
Model for: warehouses (plants / godowns / locations)
"""

from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g. "Plant A - MIDC Nashik"
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    user_locations = relationship("UserLocation", back_populates="warehouse")
