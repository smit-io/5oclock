import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from datetime import datetime, timezone
import zoneinfo
import sqlite3
import os

from src.constants import DB_NAME
from src.downloader import sync_data
from src.database import build_db

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Only sync and build if needed or FORCE_REBUILD is handled inside these funcs
    sync_data()
    build_db()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('index.html')

@app.get("/api/cities")
async def get_cities(target_hour: int = 17):
    if not os.path.exists(DB_NAME):
        return {"error": "Database not ready"}

    now_utc = datetime.now(timezone.utc)
    matching_tz_names = []

    # Get all available IANA timezone names
    all_zones = zoneinfo.available_timezones()

    # Find which zones currently match the target hour
    for tz_name in all_zones:
        try:
            # Create ZoneInfo object
            tz = zoneinfo.ZoneInfo(tz_name)
            # Convert UTC now to this local timezone
            local_dt = now_utc.astimezone(tz)
            
            if local_dt.hour == target_hour:
                matching_tz_names.append(tz_name)
        except Exception:
            continue

    if not matching_tz_names:
        return []

    results = []
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    curr = conn.cursor()

    # Optimized indexed query using the matching IANA strings
    placeholders = ', '.join(['?'] * len(matching_tz_names))
    query = f"""
        SELECT c.name, c.country, t.tz 
        FROM cities c
        JOIN iana_timezones t ON c.tz_id = t.id 
        WHERE t.tz IN ({placeholders})
        ORDER BY RANDOM()
        LIMIT 200
    """
    
    curr.execute(query, matching_tz_names)
    rows = curr.fetchall()

    for row in rows:
        tz_name = row['tz']
        tz = zoneinfo.ZoneInfo(tz_name)
        local_dt = now_utc.astimezone(tz)
        
        results.append({
            "name": row['name'],
            "country": row['country'],
            "timezone": tz_name,
            "local_date": local_dt.strftime("%Y-%m-%d"),
            "local_time": local_dt.strftime("%H:%M:%S"),
            "tz_abbr": local_dt.tzname()  # Fixed: No arguments needed here
        })

    conn.close()
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)