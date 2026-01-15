from collections import defaultdict

from cities_db.models import IANATimezone, City
from geonames_db.models import GeoNamesCity, Admin1Code, CountryInfo
import pytz


def build_timezones(geo_session, city_session):
    """
    Populate iana_timezones table using GeoNames as source of truth.
    """

    timezones = (
        geo_session.query(GeoNamesCity.timezone)
        .distinct()
        .all()
    )

    for (tz_name,) in timezones:
        if tz_name:
            city_session.add(IANATimezone(name=tz_name))

    city_session.commit()


def build_cities(geo_session, city_session):
    """
    Populate cities table:
    - Grouped by timezone
    - Within each timezone, sorted by population DESC
    """

    # -------------------------------------------------
    # Build lookup maps
    # -------------------------------------------------

    admin_map = {
        a.code: a.name
        for a in geo_session.query(Admin1Code)
    }

    country_map = {
        c.iso: c.country
        for c in geo_session.query(CountryInfo)
    }

    tz_map = {
        t.name: t.id
        for t in city_session.query(IANATimezone)
    }

    # -------------------------------------------------
    # Group cities by timezone_id
    # -------------------------------------------------

    cities_by_timezone: dict[int, list[City]] = defaultdict(list)

    for c in geo_session.query(GeoNamesCity).yield_per(1000):
        tz_id = tz_map.get(c.timezone)
        if not tz_id:
            continue

        admin_key = f"{c.country_code}.{c.admin1_code}"

        city = City(
            name=c.name,
            state=admin_map.get(admin_key),
            state_code=c.admin1_code,
            country=country_map.get(c.country_code),
            country_code=c.country_code,
            latitude=c.latitude,
            longitude=c.longitude,
            population=c.population or 0,
            timezone_id=tz_id,
        )

        cities_by_timezone[tz_id].append(city)

    # -------------------------------------------------
    # Insert grouped + sorted
    # -------------------------------------------------

    for tz_id, cities in cities_by_timezone.items():
        # Sort by population DESC within timezone
        cities.sort(key=lambda c: c.population, reverse=True)

        city_session.bulk_save_objects(cities)

    city_session.commit()

def create_indexes(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_iana_timezones_name
        ON iana_timezones (name);
        """)

        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_cities_tz_population
        ON cities (timezone_id, population DESC);
        """)
        
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_cities_tz_pop_desc
        ON cities (timezone_id, population DESC);
        """)
        
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_cities_tz_pop_asc
        ON cities (timezone_id, population ASC);
        """)
        
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_cities_country
        ON cities (country_code);
        """)
        
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_cities_country_pop_desc
        ON cities (country_code, population DESC);
        """)

