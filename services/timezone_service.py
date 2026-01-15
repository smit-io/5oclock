import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from sqlalchemy import select
from cities_db.models import IANATimezone

logger = logging.getLogger(__name__)


def timezones_at_hour(session, target_hour: int) -> list[str]:
    """
    Returns IANA timezone names that currently have the given local hour,
    filtered to only those present in cities.db.
    """

    now_utc = datetime.now(timezone.utc)

    # 1. Compute matching timezones using zoneinfo
    computed_matches: set[str] = set()

    for tz_name in available_timezones():
        try:
            local_time = now_utc.astimezone(ZoneInfo(tz_name))
            if local_time.hour == target_hour:
                computed_matches.add(tz_name)
        except Exception:
            # Defensive: skip any broken zone
            continue

    if not computed_matches:
        return []

    # 2. Fetch timezones that actually exist in cities.db
    existing_tz_rows = session.execute(
        select(IANATimezone.name).where(IANATimezone.name.in_(computed_matches))
    ).all()

    existing_timezones = {row[0] for row in existing_tz_rows}

    # 3. Log missing timezones
    missing_timezones = computed_matches - existing_timezones
    if missing_timezones:
        logger.warning(
            "❔ Timezones missing in cities.db (hour=%d): %s",
            target_hour,
            sorted(missing_timezones),
        )

    print(f"✅ Found {existing_timezones} timezones at hour {target_hour}")

    # 4. Return only valid timezones
    return sorted(existing_timezones)
