import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Folder Structures
DATA_DIR = BASE_DIR  / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "db"
JSON_DIR = DATA_DIR / "json"
GEONAMES_DB_PATH = OUTPUT_DIR / "geonames.db"
CITIES_DB_PATH = OUTPUT_DIR / "cities.db"

FORCE_UPDATE = os.getenv("GEONAMES_FORCE_UPDATE", "False").lower() in ("true", "1", "t")

# GeoNames URLs
BASE_URL = "https://download.geonames.org/export/dump/"
FILES_TO_DOWNLOAD = {
    "cities": "cities500.zip",
    "admin_codes": "admin1CodesASCII.txt",
    "country_info": "countryInfo.txt"
}

# Column definitions based on GeoNames readme.txt
SCHEMAS = {
    "cities": [
        "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
        "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
        "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
        "dem", "timezone", "modification_date"
    ],
    "admin_codes": ["code", "name", "name_ascii", "geonameid"],
    "country_info": [
        "iso", "iso3", "iso_numeric", "fips", "country", "capital", "area",
        "population", "continent", "tld", "currency_code", "currency_name",
        "phone", "postal_code_format", "postal_code_regex", "languages",
        "geonameid", "neighbours", "equivalent_fips_code"
    ]
}

# Schema for the refined database
REFINED_SCHEMAS = {
    "iana_timezones": ["id", "timezone_name"],
    "cities": [
        "name", "state", "country", "population", 
        "latitude", "longitude", "state_abbr", 
        "country_abbr", "timezone_id"
    ]
}

# Ensure directories exist
for folder in [INPUT_DIR, OUTPUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

