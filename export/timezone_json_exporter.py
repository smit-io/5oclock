import json
from pathlib import Path
from typing import List
from sqlalchemy import select
from collections import defaultdict

from cities_db.models import City, IANATimezone

from config import FORCE_REBUILD, TIMEZONE_INDEX_FILE_NAME


def safe_tz_filename(tz_name: str) -> str:
    """Convert IANA timezone to filename-safe string."""
    return tz_name.replace("/", "_")

def write_timezone_file(output_dir: Path, tz_name: str, data: dict):
    filename = safe_tz_filename(tz_name) + ".json"
    path = output_dir / filename

    # Skip if file exists and no rebuild requested
    if path.exists() and not FORCE_REBUILD:
        # logger.debug("Skipping %s (already exists)", path.name)
        return

    # Convert defaultdict → dict (JSON-safe)
    data["countries"] = dict(data["countries"])

    tmp_path = path.with_suffix(".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    # Atomic replace
    tmp_path.replace(path)


def export_cities_by_timezone(session, output_dir: Path):
    """
    Create one JSON file per timezone.
    Each file groups cities by country.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    stmt = (
        select(
            IANATimezone.name,
            City.name,
            City.state,
            City.population,
            City.latitude,
            City.longitude,
            City.country,
        )
        .join(City.timezone)
        .order_by(
            IANATimezone.name,
            City.country,
            City.population.desc(),
        )
    )

    result = session.execute(stmt)

    current_tz = None
    data = None

    for (
        tz_name,
        city_name,
        state_name,
        population,
        lat,
        lng,
        country_code,
    ) in result:

        if tz_name != current_tz:
            # Flush previous timezone file
            if data is not None:
                write_timezone_file(output_dir, current_tz, data)

            current_tz = tz_name
            data = {
                "timezone": tz_name,
                "countries": defaultdict(list),
            }

        data["countries"][country_code].append({
            "city": city_name,
            "state": state_name,
            "population": population,
            "lat": lat,
            "lng": lng,
        })

    # Flush last file
    if data is not None:
        write_timezone_file(output_dir, current_tz, data)

def tz_name_from_filename(filename: str) -> str:
    """
    Convert safe filename back to IANA timezone name.
    Example: America_New_York.json → America/New_York
    """
    return filename.replace(".json", "").replace("_", "/")


def generate_timezone_index(output_dir: Path):
    """
    Generates _timezone.index containing all timezones
    for which JSON files exist.
    """

    index_path = output_dir / TIMEZONE_INDEX_FILE_NAME

    # Skip if already exists and no rebuild requested
    if index_path.exists() and not FORCE_REBUILD:
        return

    timezones: List[str] = []

    for path in sorted(output_dir.glob("*.json")):
        if path.name == TIMEZONE_INDEX_FILE_NAME:
            continue

        timezones.append(tz_name_from_filename(path.name))

    data = {
        "timezones": timezones
    }

    tmp_path = index_path.with_suffix(".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    tmp_path.replace(index_path)