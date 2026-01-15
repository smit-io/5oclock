from pathlib import Path

DATA_DIR = Path("data")
DB_DIR = Path("databases")

GEONAMES_URLS = {
    "cities": "https://download.geonames.org/export/dump/cities500.zip",
    "admin1": "https://download.geonames.org/export/dump/admin1CodesASCII.txt",
    "countries": "https://download.geonames.org/export/dump/countryInfo.txt",
}

FORCE_REBUILD = False

GEONAMES_DB_PATH = DB_DIR / "geonames.db"
CITIES_DB_PATH = DB_DIR / "cities.db"

CITIES_ZIP = DATA_DIR / "cities500.zip"
ADMIN1_FILE = DATA_DIR / "admin1CodesASCII.txt"
COUNTRY_FILE = DATA_DIR / "countryInfo.txt"
CITIES_FILE = DATA_DIR / "cities500.txt"