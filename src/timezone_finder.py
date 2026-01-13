from datetime import datetime, timezone
from functools import lru_cache
import sqlite3
import zoneinfo
import pytz
from datetime import datetime, timezone

from src.constants import CITIES_DB_PATH

def get_current_time_in_tz(tz_name: str) -> datetime:
    """Helper to get current time for a specific IANA zone."""
    return datetime.now(zoneinfo.ZoneInfo(tz_name))

def find_best_matching_timezones_with_meta(target_hour: int) -> dict:
    """
    Finds best matching timezones and returns a dict with metadata:
    { "America/Chicago": {"date": "2026-01-12", "time": "17:05", "abbr": "CST"}, ... }
    """
    now_utc = datetime.now(timezone.utc)
    matching_tzs = []
    
    for tz_name in pytz.common_timezones:
        try:
            tz = pytz.timezone(tz_name)
            local_now = now_utc.astimezone(tz)
            
            if local_now.hour == target_hour:
                matching_tzs.append({
                    "name": tz_name,
                    "minute": local_now.minute,
                    "date": local_now.strftime("%Y-%m-%d"),
                    "time": local_now.strftime("%H:%M:%S"),
                    "abbr": local_now.strftime("%Z") # Gets PST, CST, etc.
                })
        except Exception:
            continue

    if not matching_tzs:
        return {}

    # Winner takes all (closest to :00)
    min_minute = min(tz['minute'] for tz in matching_tzs)
    
    # Return a mapping of timezone name to its metadata
    return {
        tz['name']: {
            "date": tz['date'], 
            "time": tz['time'], 
            "abbr": tz['abbr']
        } 
        for tz in matching_tzs if tz['minute'] == min_minute
    }


# @lru_cache(maxsize=24)
# def find_best_matching_timezones(target_hour: int) -> list:
#     utc_now = datetime.now(zoneinfo.ZoneInfo('UTC'))
#     matching_zones = []

#     for tz_name in zoneinfo.available_timezones():
#         tz = zoneinfo.ZoneInfo(tz_name)
#         local_now = utc_now.astimezone(tz)
#         # if target_hour <= local_now.hour < target_hour + 1:
#         #     matching_zones.append(tz_name)
#         if local_now.hour == target_hour:
#             matching_zones.append(tz_name)

#     return matching_zones

# def find_best_matching_timezones(target_hour: int) -> list:
#     """
#     1. Finds all timezones where local hour == target_hour.
#     2. Among those, finds the ones closest to the :00 minute mark.
#     """
#     conn = sqlite3.connect(CITIES_DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("SELECT timezone_name FROM iana_timezones")
#     all_tzs = [row[0] for row in cursor.fetchall()]
#     conn.close()

#     # Step 1: Filter zones currently in the target hour
#     active_in_hour = []
#     now_utc = datetime.now(zoneinfo.ZoneInfo("UTC"))

#     for tz_name in all_tzs:
#         try:
#             local_now = now_utc.astimezone(zoneinfo.ZoneInfo(tz_name))
#             if local_now.hour == target_hour:
#                 active_in_hour.append({
#                     "name": tz_name,
#                     "minute": local_now.minute
#                 })
#         except Exception:
#             continue

#     if not active_in_hour:
#         return []

#     # Step 2: Find the minimum minute value (closest to :00)
#     min_minute = min(tz['minute'] for tz in active_in_hour)

#     # Step 3: Return all zones that share that minimum minute
#     return [tz['name'] for tz in active_in_hour if tz['minute'] == min_minute]

# Use pytz instead of database for timezone calculations

# def find_best_matching_timezones(target_hour: int) -> list:
#     """
#     Finds the IANA timezone(s) closest to the start of target_hour 
#     using the pytz library for timezone definitions.
#     """
#     active_in_hour = []
#     now_utc = datetime.now(pytz.utc)

#     # Use pytz's internal list of all IANA timezones
#     for tz_name in pytz.all_timezones:
#         try:
#             tz = pytz.timezone(tz_name)
#             local_now = now_utc.astimezone(tz)
            
#             if local_now.hour == target_hour:
#                 active_in_hour.append({
#                     "name": tz_name,
#                     "minute": local_now.minute
#                 })
#         except Exception:
#             continue

#     if not active_in_hour:
#         return []

#     # Find the minimum minute (closest to :00)
#     min_minute = min(tz['minute'] for tz in active_in_hour)

#     # Return names of all zones that share that minimum minute
#     return [tz['name'] for tz in active_in_hour if tz['minute'] == min_minute]