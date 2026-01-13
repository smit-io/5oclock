import sqlite3
import csv
import os
from src.constants import DB_NAME, FILES, FORCE_REBUILD

def build_db():
    if FORCE_REBUILD and os.path.exists(DB_NAME):
        print("FORCE_REBUILD is True. Deleting old database...")
        os.remove(DB_NAME)
    
    if os.path.exists(DB_NAME):
        return

    print("Building database from GeoNames files...")
    conn = sqlite3.connect(DB_NAME)
    curr = conn.cursor()

    curr.executescript("""
        CREATE TABLE iana_timezones (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            tz TEXT UNIQUE
        );
        CREATE TABLE cities (
            name TEXT, 
            state TEXT, 
            country TEXT, 
            lat REAL, 
            lon REAL, 
            state_abbr TEXT, 
            country_abbr TEXT, 
            tz_id INTEGER,
            FOREIGN KEY(tz_id) REFERENCES iana_timezones(id)
        );
        CREATE INDEX idx_city_tz_id ON cities(tz_id);
    """)

    # Load Country Names Mapping
    countries = {}
    if os.path.exists(FILES["countries"]):
        with open(FILES["countries"], 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'): continue
                row = line.split('\t')
                countries[row[0]] = row[4]

    # Load State Names Mapping
    states = {}
    if os.path.exists(FILES["admin1"]):
        with open(FILES["admin1"], 'r', encoding='utf-8') as f:
            for line in f:
                row = line.split('\t')
                states[row[0]] = row[1]

    # Process Cities and insert into DB
    tz_map = {}
    if os.path.exists(FILES["cities_txt"]):
        with open(FILES["cities_txt"], 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                # GeoNames schema: 1:name, 4:lat, 5:lon, 8:country, 10:admin1, 17:timezone
                city_name = row[1]
                lat, lon = row[4], row[5]
                country_code = row[8]
                admin1 = row[10]
                tz_name = row[17]
                
                if not tz_name: continue

                if tz_name not in tz_map:
                    curr.execute("INSERT OR IGNORE INTO iana_timezones (tz) VALUES (?)", (tz_name,))
                    curr.execute("SELECT id FROM iana_timezones WHERE tz=?", (tz_name,))
                    tz_map[tz_name] = curr.fetchone()[0]

                state_key = f"{country_code}.{admin1}"
                curr.execute("""
                    INSERT INTO cities VALUES (?,?,?,?,?,?,?,?)
                """, (city_name, states.get(state_key, ""), countries.get(country_code, ""), 
                     lat, lon, admin1, country_code, tz_map[tz_name]))

    conn.commit()
    conn.close()
    print("Database build complete.")