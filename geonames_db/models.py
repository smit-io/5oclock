from sqlalchemy import Column, Integer, String, Float
from db.base import Base

class GeoNamesCity(Base):
    __tablename__ = "cities500"

    geonameid = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    asciiname = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country_code = Column(String(2), nullable=False)
    admin1_code = Column(String)
    population = Column(Integer)
    timezone = Column(String, nullable=False)


class Admin1Code(Base):
    __tablename__ = "admin1_codes"

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ascii_name = Column(String)


class CountryInfo(Base):
    __tablename__ = "country_info"

    iso = Column(String(2), primary_key=True)
    country = Column(String, nullable=False)