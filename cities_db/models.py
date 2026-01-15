from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base

class IANATimezone(Base):
    __tablename__ = "iana_timezones"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    state = Column(String)
    state_code = Column(String)
    country = Column(String)
    country_code = Column(String(2), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    population = Column(Integer)
    timezone_id = Column(Integer, ForeignKey("iana_timezones.id"), nullable=False)

    timezone = relationship("IANATimezone")
