from pathlib import Path

from config import (
    DATA_DIR,
    DB_DIR,
    GEONAMES_URLS,
    FORCE_REBUILD,
    GEONAMES_DB_PATH,
    CITIES_DB_PATH,
    CITIES_ZIP,
    CITIES_FILE,
    COUNTRY_FILE,
    ADMIN1_FILE
)

from export.timezone_json_exporter import export_cities_by_timezone, generate_timezone_index
from utils.files import ensure_dir
from downloader.geonames import download_if_needed

from db.session import create_session
from db.base import Base

# GeoNames DB
from geonames_db.models import GeoNamesCity, Admin1Code, CountryInfo
from geonames_db.importer import (
    import_cities500,
    import_admin1,
    import_countries,
)

# Cities DB
from cities_db.models import City, IANATimezone
from cities_db.importer import build_timezones, build_cities, create_indexes
from cities_db.queries import bottom_cities_by_population_in_timezone, cities_at_hour, top_cities_by_population_at_hour, top_cities_by_population_in_timezone


# ---------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------

def rebuild_db_if_needed(db_path: Path):
    if FORCE_REBUILD and db_path.exists():
        db_path.unlink()


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

def create_directories():
    print("Making sure directories exist")
    ensure_dir(DATA_DIR)
    ensure_dir(DB_DIR)
    print("Directories are now setup")

def download_data():
    print("⬇️  Downloading GeoNames data if needed")

    download_if_needed(
        GEONAMES_URLS["cities"],
        CITIES_ZIP,
        FORCE_REBUILD,
    )

    download_if_needed(
        GEONAMES_URLS["admin1"],
        ADMIN1_FILE,
        FORCE_REBUILD,
    )

    download_if_needed(
        GEONAMES_URLS["countries"],
        COUNTRY_FILE,
        FORCE_REBUILD,
    )
    
    print("✅ GeoNames data download complete")
    
def build_geonames_db():
    print("🗄️  Building geonames.db")

    rebuild_db_if_needed(GEONAMES_DB_PATH)

    geo_session, geo_engine = create_session(GEONAMES_DB_PATH)

    # Create tables
    Base.metadata.create_all(
        geo_engine,
        tables=[
            GeoNamesCity.__table__,
            Admin1Code.__table__,
            CountryInfo.__table__,
        ],
    )

    # Import raw data
    if FORCE_REBUILD or not geo_session.query(GeoNamesCity).first():
        print("📥 Importing cities500")
        import_cities500(geo_session, CITIES_FILE)

        print("📥 Importing admin1 codes")
        import_admin1(geo_session, ADMIN1_FILE)

        print("📥 Importing country info")
        import_countries(geo_session, COUNTRY_FILE)
    else:
        print("✅ geonames.db already populated")

    geo_session.close()
    
def build_cities_db():
    print("🏙️  Building cities.db")

    rebuild_db_if_needed(CITIES_DB_PATH)

    geo_session, geo_engine = create_session(GEONAMES_DB_PATH)
    city_session, city_engine = create_session(CITIES_DB_PATH)

    # Create tables
    Base.metadata.create_all(
        city_engine,
        tables=[
            IANATimezone.__table__,
            City.__table__,
        ],
    )

    # Populate iana_timezones
    if FORCE_REBUILD or not city_session.query(IANATimezone).first():
        print("🌍 Populating IANA timezones")
        build_timezones(geo_session, city_session)
    else:
        print("✅ iana_timezones already populated")

    # Populate cities
    if FORCE_REBUILD or not city_session.query(City).first():
        print("🏗️  Populating cities table")

        # Re-open GeoNames session for reading
        geo_session, _ = create_session(GEONAMES_DB_PATH)

        build_cities(geo_session, city_session)

        geo_session.close()
    else:
        print("✅ cities table already populated")
        
    create_indexes(city_engine)
    
    city_session.close()
    
def export_json():
    city_session, _ = create_session(CITIES_DB_PATH)
    export_cities_by_timezone(
        session=city_session,
        output_dir=Path("json/timezones"),
    )
    
    generate_timezone_index(Path("json/timezones"))
    
    city_session.close()

def init():
    create_directories()
    download_data()
    build_geonames_db()
    build_cities_db()
    export_json()
    
def some_data():
    
    city_session, city_engine = create_session(CITIES_DB_PATH)
    
    print("🕔 Querying cities at hour 17")

    cities = cities_at_hour(city_session, 17)

    print(f"✅ Found {len(cities)} cities currently between 17:00–17:59")

    # Print a few examples
    for city in cities[:10]:
        print(
            f"{city.name}, {city.state}, {city.country}, {city.population}"
            f"({city.timezone.name})"
        )

    print("🎉 Done")
    
    print("Top 5 cities by population in America/New_York:")
    top_cities_in_ny = top_cities_by_population_in_timezone(city_session, "America/New_York", 5)
    for city in top_cities_in_ny:
        print(f"- {city.name}, Population: {city.population}")
        
    print("Botton 5 cities by population in America/New_York:")
    bottom_cities_in_ny = bottom_cities_by_population_in_timezone(city_session, "America/New_York", 25)
    for city in bottom_cities_in_ny:
        print(f"- {city.name}, Population: {city.population}")
        
    print("Top 15 cities at hour 10:")
    hour_10_cities = top_cities_by_population_at_hour(city_session, hour=10, limit=15)
    for city in hour_10_cities:
        print(f"- {city.name}, Population: {city.population}, Timezone: {city.timezone.name}")
    
    city_session.close()
    
    cities = cities_at_hour(
        city_session,
        12,
        limit=20,
        round_robin_by="country"
    )
    
    print(f"Roundrobin cities")
    for city in cities:
        print(f"- {city.name},  {city.state}, {city.country} Population: {city.population}, Timezone: {city.timezone.name}")
        


def main():
    print("🚀 Starting TimeFinder build pipeline")
    init()
    print("🤘 Build pipeline complete")
    some_data()



# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
