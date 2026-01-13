import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from datetime import datetime
import pytz
import sqlite3
import os

from src.constants import DB_NAME
from src.downloader import sync_data
from src.database import build_db

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    sync_data()
    build_db()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('index.html')

@app.get("/api/cities")
async def get_cities(target_hour: int = 17):
    if not os.path.exists(DB_NAME):
        return {"error": "Database not ready"}

    now_utc = datetime.now(pytz.utc)
    matching_tz_names = []

    # 1. Identify all IANA timezones where it is currently the target hour
    for tz_name in pytz.all_timezones:
        try:
            tz_obj = pytz.timezone(tz_name)
            local_dt = now_utc.astimezone(tz_obj)
            if local_dt.hour == target_hour:
                matching_tz_names.append(tz_name)
        except Exception:
            continue

    if not matching_tz_names:
        return []

    # 2. Query database for cities in those specific timezones
    results = []
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    curr = conn.cursor()
    
    # Using 'IN' clause for a single efficient fetch
    placeholders = ', '.join(['?'] * len(matching_tz_names))
    query = f"""
        SELECT c.name, c.country, c.lat, c.lon, t.tz 
        FROM cities c
        JOIN iana_timezones t ON c.tz_id = t.id 
        WHERE t.tz IN ({placeholders})
    """
    
    curr.execute(query, matching_tz_names)
    rows = curr.fetchall()

    # 3. Format results with local time details
    for row in rows:
        tz_name = row['tz']
        tz_obj = pytz.timezone(tz_name)
        local_dt = now_utc.astimezone(tz_obj)
        
        results.append({
            "name": row['name'],
            "country": row['country'],
            "lat": row['lat'],
            "lon": row['lon'],
            "timezone": tz_name,
            "local_date": local_dt.strftime("%Y-%m-%d"),
            "local_time": local_dt.strftime("%H:%M:%S"),
            "tz_abbr": local_dt.strftime("%Z")
        })

    conn.close()
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)