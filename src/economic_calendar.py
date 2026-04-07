"""Fetch today's US economic calendar events from Forex Factory."""

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List, NamedTuple

_FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Impact display order (High first)
_IMPACT_ORDER = {"High": 0, "Medium": 1, "Low": 2}

# Country code → Forex Factory currency code
_COUNTRY_TO_FF = {
    "US": "USD",
    "GB": "GBP",
    "JP": "JPY",
    "CA": "CAD",
    "AU": "AUD",
    "FR": "EUR",
    "DE": "EUR",
    "CN": "CNY",
}


class EconomicEvent(NamedTuple):
    title: str
    country: str   # FF currency code e.g. "USD", "EUR"
    time_et: str   # e.g. "8:30am" or "All Day"
    time_jst: str  # e.g. "21:30 JST" or "終日"
    impact: str    # "High" | "Medium" | "Low"
    forecast: str
    previous: str


def _to_jst(dt: datetime) -> str:
    """Convert datetime to JST time string."""
    jst = timezone(timedelta(hours=9))
    jst_dt = dt.astimezone(jst)
    return jst_dt.strftime("%H:%M JST")


def fetch_today_us_events(min_impact: str = "Medium", countries: List[str] = None) -> List[EconomicEvent]:
    """Fetch today's USD economic events.

    Args:
        min_impact: Minimum impact level to include. "High" returns only high-impact.
                    "Medium" returns High + Medium. "Low" returns all.
        countries: List of country codes (e.g. ["US", "JP"]). Defaults to ["US"].
    Returns:
        List of EconomicEvent sorted by time, then impact.
    """
    try:
        req = urllib.request.Request(
            _FF_CALENDAR_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; news-filter/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logging.warning("[EconCalendar] Failed to fetch calendar: %s", exc)
        return []

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    # Window: today 08:00 JST → tomorrow 08:00 JST
    today_start = now_jst.replace(hour=8, minute=0, second=0, microsecond=0)
    window_start = today_start
    window_end = today_start + timedelta(hours=24)

    # Build set of FF currency codes to include
    target_countries = set(countries or ["US"])
    target_ff_codes = {_COUNTRY_TO_FF.get(c, c) for c in target_countries}

    min_order = _IMPACT_ORDER.get(min_impact, 1)
    events = []

    for item in data:
        if item.get("country") not in target_ff_codes:
            continue
        impact = item.get("impact", "")
        if impact == "Non-Economic" or impact not in _IMPACT_ORDER:
            continue
        if _IMPACT_ORDER[impact] > min_order:
            continue

        # Parse the date field - Forex Factory returns ISO 8601 with offset
        date_str = item.get("date", "")
        event_dt = None
        try:
            event_dt = datetime.fromisoformat(date_str)
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            # Keep events within [today 08:00 JST, tomorrow 08:00 JST]
            if not (window_start <= event_dt <= window_end):
                continue
        except (ValueError, TypeError):
            # No parseable datetime: skip
            continue

        # Extract ET and JST times from the parsed datetime
        try:
            et_tz = timezone(timedelta(hours=-4))  # EDT (UTC-4)
            time_et = event_dt.astimezone(et_tz).strftime("%-I:%M%p").lower()  # e.g. "10:00am"
            time_jst = _to_jst(event_dt)
        except Exception:
            time_et = "All Day"
            time_jst = "終日"

        events.append(EconomicEvent(
            title=item.get("title", ""),
            country=item.get("country", ""),
            time_et=time_et,
            time_jst=time_jst,
            impact=impact,
            forecast=str(item.get("forecast", "") or ""),
            previous=str(item.get("previous", "") or ""),
        ))

    # Sort by time (JST), then impact
    events.sort(key=lambda e: (e.time_jst, _IMPACT_ORDER.get(e.impact, 9)))
    return events
