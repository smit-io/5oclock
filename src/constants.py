import os

FORCE_REBUILD = False
DATA_DIR = "data"
DB_NAME = "cities.db"

GEONAMES_URLS = {
    "cities": "https://download.geonames.org/export/dump/cities500.zip",
    "countries": "https://download.geonames.org/export/dump/countryInfo.txt",
    "admin1": "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
}

FILES = {
    "cities_zip": os.path.join(DATA_DIR, "cities500.zip"),
    "cities_txt": os.path.join(DATA_DIR, "cities500.txt"),
    "countries": os.path.join(DATA_DIR, "countryInfo.txt"),
    "admin1": os.path.join(DATA_DIR, "admin1CodesASCII.txt")
}