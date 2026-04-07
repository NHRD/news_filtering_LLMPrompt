"""Fetch today's US economic calendar events from Forex Factory + TradingView."""

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List, NamedTuple

_FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_TV_CALENDAR_URL = "https://economic-calendar.tradingview.com/events"

_TV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/economic-calendar/",
    "Content-Type": "application/x-www-form-urlencoded",
}

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

# TradingView importance value → label
_TV_IMPACT_MAP = {2: "High", 1: "Medium", 0: "Low", -1: "Low"}


class EconomicEvent(NamedTuple):
    title: str
    country: str   # FF currency code e.g. "USD", "EUR"
    time_et: str   # e.g. "8:30am" or "All Day"
    time_jst: str  # e.g. "21:30 JST" or "終日"
    impact: str    # "High" | "Medium" | "Low"
    forecast: str
    previous: str


def _to_jst(dt: datetime) -> str:
    """Convert datetime to JST date+time string."""
    jst = timezone(timedelta(hours=9))
    jst_dt = dt.astimezone(jst)
    return jst_dt.strftime("%m/%d %H:%M JST")


def _to_et(dt: datetime) -> str:
    et_tz = timezone(timedelta(hours=-4))  # EDT (UTC-4)
    try:
        return dt.astimezone(et_tz).strftime("%-I:%M%p").lower()
    except Exception:
        return "All Day"


def _get_window() -> tuple:
    """Return (window_start, window_end) as JST 08:00 today → JST 08:00 tomorrow."""
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    today_start = now_jst.replace(hour=8, minute=0, second=0, microsecond=0)
    return today_start, today_start + timedelta(hours=24)


def _fetch_ff(window_start: datetime, window_end: datetime,
              target_ff_codes: set, min_order: int) -> List[EconomicEvent]:
    """Fetch from Forex Factory."""
    try:
        req = urllib.request.Request(
            _FF_CALENDAR_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; news-filter/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logging.warning("[EconCalendar] FF fetch failed: %s", exc)
        return []

    events = []
    for item in data:
        if item.get("country") not in target_ff_codes:
            continue
        impact = item.get("impact", "")
        if impact == "Non-Economic" or impact not in _IMPACT_ORDER:
            continue
        if _IMPACT_ORDER[impact] > min_order:
            continue
        date_str = item.get("date", "")
        try:
            event_dt = datetime.fromisoformat(date_str)
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            if not (window_start <= event_dt <= window_end):
                continue
        except (ValueError, TypeError):
            continue

        events.append(EconomicEvent(
            title=item.get("title", ""),
            country=item.get("country", ""),
            time_et=_to_et(event_dt),
            time_jst=_to_jst(event_dt),
            impact=impact,
            forecast=str(item.get("forecast", "") or ""),
            previous=str(item.get("previous", "") or ""),
        ))
    return events


def _fetch_tv(window_start: datetime, window_end: datetime,
              target_ff_codes: set, min_order: int) -> List[EconomicEvent]:
    """Fetch from TradingView economic calendar."""
    # TradingView uses ISO 8601 UTC
    from_str = window_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_str = window_end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    post_data = f"from={urllib.parse.quote(from_str)}&to={urllib.parse.quote(to_str)}&countries=US,GB,JP,CA,AU,DE,FR,CN&importanceList=high,medium,low"

    try:
        req = urllib.request.Request(
            _TV_CALENDAR_URL,
            data=post_data.encode(),
            headers=_TV_HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logging.warning("[EconCalendar] TradingView fetch failed: %s", exc)
        return []

    # TradingView country code → FF currency code mapping
    tv_country_to_ff = {
        "US": "USD", "GB": "GBP", "JP": "JPY", "CA": "CAD",
        "AU": "AUD", "FR": "EUR", "DE": "EUR", "CN": "CNY",
    }

    events = []
    for item in data.get("result", []):
        ff_code = tv_country_to_ff.get(item.get("country", ""), "")
        if ff_code not in target_ff_codes:
            continue
        imp_val = item.get("importance", -1)
        impact = _TV_IMPACT_MAP.get(imp_val, "Low")
        if _IMPACT_ORDER[impact] > min_order:
            continue
        date_str = item.get("date", "")
        try:
            event_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if not (window_start <= event_dt <= window_end):
                continue
        except (ValueError, TypeError):
            continue

        events.append(EconomicEvent(
            title=item.get("title", ""),
            country=ff_code,
            time_et=_to_et(event_dt),
            time_jst=_to_jst(event_dt),
            impact=impact,
            forecast=str(item.get("forecast") or ""),
            previous=str(item.get("previous") or ""),
        ))
    return events


def fetch_today_us_events(min_impact: str = "Medium", countries: List[str] = None) -> List[EconomicEvent]:
    """Fetch today's economic events from Forex Factory + TradingView, deduplicated.

    Args:
        min_impact: Minimum impact level. "High" = High only, "Medium" = High+Medium, "Low" = all.
        countries: List of country codes (e.g. ["US", "JP"]). Defaults to ["US"].
    Returns:
        Deduplicated list of EconomicEvent sorted by time, then impact.
    """
    import urllib.parse  # noqa: ensure available

    window_start, window_end = _get_window()
    target_countries = set(countries or ["US"])
    target_ff_codes = {_COUNTRY_TO_FF.get(c, c) for c in target_countries}
    min_order = _IMPACT_ORDER.get(min_impact, 1)

    ff_events = _fetch_ff(window_start, window_end, target_ff_codes, min_order)
    tv_events = _fetch_tv(window_start, window_end, target_ff_codes, min_order)

    logging.info("[EconCalendar] FF: %d events, TradingView: %d events", len(ff_events), len(tv_events))

    # Deduplicate: key = (time_jst, normalized_title)
    # FF takes priority (higher impact data); TV fills in missing events
    seen = {}
    for e in ff_events:
        key = (e.time_jst, e.title.lower().strip())
        seen[key] = e

    for e in tv_events:
        key = (e.time_jst, e.title.lower().strip())
        if key not in seen:
            seen[key] = e

    events = list(seen.values())
    events.sort(key=lambda e: (e.time_jst, _IMPACT_ORDER.get(e.impact, 9)))
    return events
