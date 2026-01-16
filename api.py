from fastapi import FastAPI, Query, HTTPException, Request
from typing import List, Optional
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pytz
from datetime import datetime
import sqlite3

# Import your existing logic
from src.processor import (
    get_cities_from_tz_table,
    get_round_robin_cities,
    get_top_populated_cities,
    get_cities_by_population_range,
    get_cities_by_timezone,
    get_cities_from_best_hour_match
)

# app = FastAPI(title="GeoNames City API")

# from fastapi.responses import HTMLResponse

# @app.get("/", response_class=HTMLResponse)
# async def read_root():
#     with open("index.html") as f:
#         return f.read()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request, target_hour: int = Query(17)):
    # Get the interleaved city list
    cities_list = get_round_robin_cities(target_hour)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "cities": cities_list,
        "target_hour": target_hour
    })

# --- Optimized Endpoints ---

@app.get("/cities/top")
async def top_cities(limit: int = 100):
    """Returns the most populated cities globally."""
    return get_top_populated_cities(limit=limit)

# Uses cities table containing lot of records
# @app.get("/cities/timezone/{tz_name:path}")
# async def cities_by_tz(tz_name: str, limit: Optional[int] = None):
#     """Returns cities in a specific timezone (e.g., /cities/timezone/America/New_York)."""
#     # Using :path allows slashes in the URL parameter
#     data = get_cities_by_timezone(tz_name, limit=limit)
#     if not data:
#         raise HTTPException(status_code=404, detail="Timezone not found or no cities available")
#     return data

@app.get("/cities/timezone/{tz_name:path}")
async def cities_by_tz(tz_name: str, limit: Optional[int] = None):
    """Returns cities in a specific timezone (e.g., /cities/timezone/America/New_York)."""
    # Using :path allows slashes in the URL parameter
    data = get_cities_from_tz_table(tz_name, limit=limit)
    if not data:
        raise HTTPException(status_code=404, detail="Timezone not found or no cities available")
    return data

@app.get("/cities/population")
async def cities_by_pop(min_pop: int = 0, max_pop: int = 200_000_000, limit: int = 100):
    """Returns cities within a population range."""
    return get_cities_by_population_range(min_pop, max_pop, limit=limit)

@app.get("/cities/hour/{target_hour}")
async def cities_by_hour(target_hour: int, limit: Optional[int] = None):
    """Returns cities where the current time is closest to HH:00."""
    if not (0 <= target_hour <= 23):
        raise HTTPException(status_code=400, detail="Hour must be between 0 and 23")
    return get_cities_from_best_hour_match(target_hour, city_limit=limit)

@app.get("/timezones")
async def list_timezones():
    """Returns all IANA timezones and their current local time."""
    now_utc = datetime.now(pytz.utc)
    return [
        {
            "tz": tz, 
            "time": now_utc.astimezone(pytz.timezone(tz)).strftime("%H:%M"),
            "minute_offset": now_utc.astimezone(pytz.timezone(tz)).minute
        } 
        for tz in pytz.common_timezones
    ]

@app.get("/current-cities")
async def get_active_cities(target_hour: int = Query(17, ge=0, le=23), limit: int = Query(3, ge=1, le=100)):
    """Returns cities where the current time is closest to 5 PM (17:00) by default."""
    # Force check for the 5 PM (17:00) window
    return get_cities_from_best_hour_match(target_hour, limit)