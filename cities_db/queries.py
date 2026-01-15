from typing import Optional
from sqlalchemy import select
from cities_db.models import City, IANATimezone
from services.timezone_service import timezones_at_hour
from utils.round_robin import round_robin

def cities_at_hour(
    session,
    hour: int,
    limit: Optional[int] = None,
    round_robin_by: Optional[str] = None,
):
    tz_names = timezones_at_hour(session, hour)

    tz_ids_stmt = (
        select(IANATimezone.id)
        .where(IANATimezone.name.in_(tz_names))
    )

    query = (
        session.query(City)
        .filter(City.timezone_id.in_(tz_ids_stmt))
    )

    if limit is not None:
        query = query.limit(limit)

    cities = query.all()

    if round_robin_by:
        cities = round_robin(cities, round_robin_by)

    return cities


def cities_in_timezone(
    session,
    tz_name: str,
    limit: Optional[int] = None,
    round_robin_by: Optional[str] = None,
):
    tz_id_subq = (
        select(IANATimezone.id)
        .where(IANATimezone.name == tz_name)
        .scalar_subquery()
    )

    query = (
        session.query(City)
        .filter(City.timezone_id == tz_id_subq)
    )

    if limit is not None:
        query = query.limit(limit)

    cities = query.all()

    if round_robin_by:
        cities = round_robin(cities, round_robin_by)

    return cities



def top_cities_by_population_in_timezone(session, tz_name: str, limit: Optional[int] = None):
    query = (
        session.query(City)
        .join(City.timezone)
        .filter(IANATimezone.name == tz_name)
        .order_by(City.population.desc())
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def bottom_cities_by_population_in_timezone(session, tz_name: str, limit: Optional[int] = None):
    query = (
        session.query(City)
        .join(City.timezone)
        .filter(IANATimezone.name == tz_name)
        .order_by(City.population.asc())
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def top_cities_by_population_at_hour(session, hour: int, limit: Optional[int] = None):
    tz_names = timezones_at_hour(session, hour)

    tz_ids_stmt = (
        select(IANATimezone.id)
        .where(IANATimezone.name.in_(tz_names))
    )

    query = (
        session.query(City)
        .filter(City.timezone_id.in_(tz_ids_stmt))
        .order_by(City.population.desc())
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def bottom_cities_by_population_at_hour(session, hour: int, limit: Optional[int] = None):
    tz_names = timezones_at_hour(session, hour)

    tz_ids_stmt = (
        select(IANATimezone.id)
        .where(IANATimezone.name.in_(tz_names))
    )

    query = (
        session.query(City)
        .filter(City.timezone_id.in_(tz_ids_stmt))
        .order_by(City.population.asc())
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def cities_by_country(session, country_code: str):
    return (
        session.query(City)
        .filter(City.country_code == country_code)
        .all()
    )
