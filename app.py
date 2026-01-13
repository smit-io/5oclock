import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import pytz
import sqlite3
import os

from src.constants import DB_NAME
from src.downloader import sync_data
from src.database import build_db

app = FastAPI()

# Sync data and build DB on startup
@app.on_event("startup")
async def startup_event():
    sync_data()
    build_db()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('index.html')

@app.get("/api/cities")
async def get_cities(target_hour: int = 17):
    results = []
    now = datetime.now(pytz.utc)
    
    if not os.path.exists(DB_NAME):
        return {"error": "Database not ready"}

    conn = sqlite3.connect(DB_NAME)
    curr = conn.cursor()
    
    # 1. Get all timezones
    curr.execute("SELECT id, tz FROM iana_timezones")
    all_tzs = curr.fetchall()
    
    for tz_id, tz_name in all_tzs:
        try:
            # 2. Check if the timezone currently matches the target hour
            tz_obj = pytz.timezone(tz_name)
            local_dt = now.astimezone(tz_obj)
            
            if local_dt.hour == target_hour:
                # 3. Fetch cities for this matching timezone
                city_curr = conn.cursor()
                city_curr.execute("""
                    SELECT name, country, lat, lon, tz 
                    FROM cities 
                    JOIN iana_timezones ON cities.tz_id = iana_timezones.id 
                    WHERE tz_id = ?
                """, (tz_id,))
                
                for city in city_curr.fetchall():
                    results.append({
                        "name": city[0],
                        "country": city[1],
                        "lat": city[2],
                        "lon": city[3],
                        "timezone": city[4],
                        "local_date": local_dt.strftime("%Y-%m-%d"),
                        "local_time": local_dt.strftime("%H:%M:%S"),
                        "tz_abbr": local_dt.strftime("%Z")
                    })
        except Exception:
            continue
            
    conn.close()
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)