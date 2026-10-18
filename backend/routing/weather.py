"""Weather value object + Open-Meteo parsing (pure, testable without network)."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

MM_PER_INCH = 25.4
CM_PER_INCH = 2.54


class ForecastRangeError(ValueError):
    """The requested time is outside the forecast window."""


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


def extract_weather(hourly: dict, eta: datetime) -> Weather:
    """Pick the hourly forecast slot nearest to `eta` (UTC-aware).

    Open-Meteo is asked for wind in mph, rain/showers in mm, snowfall in cm,
    all per hour, with timezone=GMT. Convert to the spec's inch units.
    """
    times = hourly["time"]
    start = datetime.fromisoformat(times[0]).replace(tzinfo=timezone.utc)
    idx = round((eta - start).total_seconds() / 3600)
    if idx < 0 or idx >= len(times):
        raise ForecastRangeError(f"{eta.isoformat()} is outside the forecast window")
    g = lambda key: hourly[key][idx] or 0.0   # API returns null for missing hours
    return Weather(
        wind_mph=g("wind_speed_10m"),
        rain_in_hr=(g("rain") + g("showers")) / MM_PER_INCH,
        snow_in_hr=g("snowfall") / CM_PER_INCH,
    )


def hourly_window(hourly: dict, start: datetime, hours: int) -> list:
    """Weather for `start`, `start`+1h, ... Stops early if the forecast runs
    out (so a late departure gets a shorter slider, not an error). Raises only
    if not even the first hour is available."""
    out = []
    for h in range(hours):
        try:
            out.append(extract_weather(hourly, start + timedelta(hours=h)))
        except ForecastRangeError:
            if not out:
                raise
            break
    return out
