from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


TURKISH_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")


def clamp_days(days: int) -> int:
 
    return max(1, min(days, 3))


def parse_iso_datetime(value: str | None) -> datetime | None:
   
    if not value:
        return None

    value = value.strip()

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def parse_turkish_date_text(value: str | None) -> datetime | None:
   
    if not value:
        return None

    text = value.strip().lower()

    match = re.search(
        r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?",
        text,
    )
    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))
    hour = int(match.group(4)) if match.group(4) else 0
    minute = int(match.group(5)) if match.group(5) else 0

    month = TURKISH_MONTHS.get(month_name)
    if not month:
        return None

    local_dt = datetime(year, month, day, hour, minute, tzinfo=ISTANBUL_TZ)
    return local_dt.astimezone(timezone.utc)


def parse_published_at_raw(value: str | None) -> datetime | None:
  
    iso_dt = parse_iso_datetime(value)
    if iso_dt:
        return iso_dt

    tr_dt = parse_turkish_date_text(value)
    if tr_dt:
        return tr_dt

    return None


def is_within_last_n_days(value: str | None, days: int = 3) -> bool:
  
    parsed = parse_published_at_raw(value)
    if not parsed:
        return False

    safe_days = clamp_days(days)

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=safe_days)

    return threshold <= parsed <= now