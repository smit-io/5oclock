import os

TARGET_24H = int(os.getenv("TARGET_24H", 17))
POP_LIMIT = int(os.getenv("POP_LIMIT", 500))

# Directories
DATA_DIR = "./geonames"
OUTPUT_DIR = "./cities"

# Files
CITIES_FILE = os.path.join(DATA_DIR, "cities500.txt")
ADMIN_FILE = os.path.join(DATA_DIR, "admin1CodesASCII.txt")
DB_PATH = os.path.join(OUTPUT_DIR, "world_cities.json")

# URLs
CITIES_URL = "https://download.geonames.org/export/dump/cities500.zip"
ADMIN_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"