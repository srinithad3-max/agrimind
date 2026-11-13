"""
Weather Monitoring Agent
- Pulls a live 7-day forecast from Open-Meteo (free, no API key)
- Computes FAO reference evapotranspiration (ET0) (falls back to Hargreaves)
- Flags agronomic risks: heavy rain, heat stress at the current growth stage,
  fungal-disease weather (leaf wetness), dry spells, strong wind for spraying
- Caches the last good forecast so the demo still works if venue Wi-Fi dies
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from app.agents.base import Agent
from app.core.crops import crop, STAGE_HEAT_WEIGHT

DATA = Path(__file__).resolve().parents[2] / "data"
API = "https://api.open-meteo.com/v1/forecast"


def hargreaves_et0(tmax, tmin, lat_deg, doy):
    """FAO-56 Hargreaves equation, mm/day."""
    lat = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    dec = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    ws = math.acos(max(-1, min(1, -math.tan(lat) * math.tan(dec))))
    ra = (24 * 60 / math.pi) * 0.082 * dr * (ws * math.sin(lat) * math.sin(dec)
                                             + math.cos(lat) * math.cos(dec) * math.sin(ws))
    tmean = (tmax + tmin) / 2
    return max(0.0, 0.0023 * (tmean + 17.8) * math.sqrt(max(0.1, tmax - tmin)) * ra * 0.408)


def demo_forecast(scenario: str, lat: float) -> dict:
    """Scripted weather for a repeatable pitch demo (clearly labelled in the UI)."""
    today = date.today()
    if scenario == "heat":
        rows = [(39, 26, 0, 5, 38, 12, 0), (41, 27, 0, 5, 32, 14, 0), (42, 28, 0, 10, 30, 15, 1),
                (40, 27, 0, 10, 35, 12, 1), (38, 26, 1, 25, 45, 10, 2), (37, 25, 0, 15, 42, 9, 1),
                (38, 25, 0, 10, 40, 11, 0)]
    else:  # "blight": humid week with rain arriving on day 2
        rows = [(30, 21, 0, 15, 78, 8, 2), (28, 21, 18, 85, 92, 14, 63), (27, 20, 9, 70, 90, 12, 61),
                (29, 20, 2, 40, 86, 9, 3), (30, 20, 0, 20, 80, 8, 2), (31, 21, 0, 10, 74, 10, 1),
                (31, 21, 0, 10, 70, 9, 0)]
    daily = []
    for i, (tx, tn, rain, prob, rh, wind, code) in enumerate(rows):
        d = today + timedelta(days=i)
        daily.append(dict(date=d.isoformat(), tmax=tx, tmin=tn, rain=rain, rain_prob=prob, rh=rh,
                          wind=wind, code=code,
                          et0=round(hargreaves_et0(tx, tn, lat, d.timetuple().tm_yday), 2)))
    return dict(daily=daily, current=dict(temp=daily[0]["tmax"] - 3, rh=daily[0]["rh"],
                                          wind=daily[0]["wind"], code=daily[0]["code"]))


class WeatherAgent(Agent):
    id, name, icon = "weather", "Weather Agent", "🌦"
    reads = ["farm.location", "crop.stage"]
    publishes = ["weather.forecast", "weather.risks"]

    def fetch_live(self, lat, lon) -> dict:
        params = dict(
            latitude=lat, longitude=lon, timezone="auto", forecast_days=7,
            daily="temperature_2m_max,temperature_2m_min,precipitation_sum,"
                  "precipitation_probability_max,et0_fao_evapotranspiration,"
                  "wind_speed_10m_max,weather_code",
            hourly="relative_humidity_2m",
            current="temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        )
        r = requests.get(API, params=params, timeout=8)
        r.raise_for_status()
        j = r.json()
        d, h = j["daily"], j["hourly"]
        rh_by_day: dict[str, list] = {}
        for t, v in zip(h["time"], h["relative_humidity_2m"]):
            if v is not None:
                rh_by_day.setdefault(t[:10], []).append(v)
        daily = []
        for i, day in enumerate(d["time"]):
            tx, tn = d["temperature_2m_max"][i], d["temperature_2m_min"][i]
            et0 = d["et0_fao_evapotranspiration"][i]
            if et0 is None:
                et0 = hargreaves_et0(tx, tn, lat, datetime.fromisoformat(day).timetuple().tm_yday)
            rhs = rh_by_day.get(day, [70])
            daily.append(dict(date=day, tmax=tx, tmin=tn, rain=d["precipitation_sum"][i] or 0,
                              rain_prob=d["precipitation_probability_max"][i] or 0,
                              rh=round(sum(rhs) / len(rhs)), wind=d["wind_speed_10m_max"][i] or 0,
                              code=d["weather_code"][i] or 0, et0=round(et0, 2)))
        c = j.get("current", {})
        return dict(daily=daily, current=dict(temp=c.get("temperature_2m"), rh=c.get("relative_humidity_2m"),
                                              wind=c.get("wind_speed_10m"), code=c.get("weather_code", 0)))

    def run(self) -> dict:
        ctx = self.bb.context
        lat, lon, place = ctx["lat"], ctx["lon"], ctx["place"]
        stage = self.bb.get("crop.stage")
        c = crop(ctx["crop"])
        cache = DATA / f"weather_cache_{round(lat, 2)}_{round(lon, 2)}.json"
        source = "Open-Meteo live forecast"

        if ctx.get("scenario") in ("blight", "heat"):
            fc = demo_forecast(ctx["scenario"], lat)
            source = "Demo scenario weather (scripted)"
            self.say(f"Loaded demo-scenario weather for {place}.")
        else:
            self.say(f"Fetching 7-day forecast for {place} ({lat:.2f}, {lon:.2f}) from Open-Meteo…")
            try:
                fc = self.fetch_live(lat, lon)
                cache.write_text(json.dumps(fc))
            except Exception as e:  # offline: use cache, then bundled sample
                if cache.exists():
                    fc, source = json.loads(cache.read_text()), "Cached forecast (offline)"
                else:
                    fc, source = demo_forecast("blight", lat), "Sample forecast (offline)"
                self.say(f"Live API unreachable ({type(e).__name__}); using {source.lower()}.", level="warn")

        days = fc["daily"]
        for d in days:
            d["tmean"] = round((d["tmax"] + d["tmin"]) / 2, 1)
            d["day"] = datetime.fromisoformat(d["date"]).strftime("%a %d")
            d["fungal"] = bool((d["rh"] >= 80 or d["rain"] >= 2) and 15 <= d["tmean"] <= 30)
            d["heat"] = d["tmax"] >= c["t_max"]

        total_rain = round(sum(d["rain"] for d in days), 1)
        fungal_days = sum(d["fungal"] for d in days)
        heat_days = sum(d["heat"] for d in days)
        rain_days = [i for i, d in enumerate(days) if d["rain"] >= 5 and d["rain_prob"] >= 50]
        dry_window = next((i for i, d in enumerate(days)
                           if d["rain"] < 2 and d["rain_prob"] < 40 and d["wind"] < 15), None)

        risks = []
        for i, d in enumerate(days):
            if d["rain"] >= 15:
                risks.append(dict(type="heavy_rain", level="high", day=i,
                                  text=f"Heavy rain {d['rain']:.0f} mm on {d['day']} ({d['rain_prob']}% chance)"))
        if heat_days:
            hot = max(days, key=lambda d: d["tmax"])
            w = STAGE_HEAT_WEIGHT[stage["index"]] if stage else 0.5
            risks.append(dict(type="heat", level="high" if w >= 0.9 else "medium", day=days.index(hot),
                              text=f"Heat stress: {hot['tmax']:.0f}°C on {hot['day']} (crop limit {c['t_max']}°C)"
                                   + (" during the sensitive flowering stage" if w >= 0.9 else "")))
        if fungal_days >= 2:
            risks.append(dict(type="fungal", level="high" if fungal_days >= 4 else "medium", day=None,
                              text=f"{fungal_days} of 7 days have leaf-wetness weather that favours fungal spread"))
        if total_rain < 3 and sum(d["et0"] for d in days) > 25:
            risks.append(dict(type="dry_spell", level="medium", day=None,
                              text=f"Dry spell: only {total_rain} mm rain against "
                                   f"{sum(d['et0'] for d in days):.0f} mm evaporative demand"))
        windy = [d for d in days if d["wind"] >= 20]
        if windy:
            risks.append(dict(type="wind", level="low", day=days.index(windy[0]),
                              text=f"Strong wind {windy[0]['wind']:.0f} km/h on {windy[0]['day']} - avoid spraying"))

        summary = dict(total_rain=total_rain, fungal_days=fungal_days, heat_days=heat_days,
                       avg_et0=round(sum(d["et0"] for d in days) / len(days), 2),
                       max_temp=max(d["tmax"] for d in days), mean_temp=round(sum(d["tmean"] for d in days) / len(days), 1),
                       mean_rh=round(sum(d["rh"] for d in days) / len(days)),
                       rain_days=rain_days, dry_window=dry_window, source=source)
        out = dict(daily=days, current=fc["current"], summary=summary, risks=risks)

        self.bb.publish("weather.forecast", out, self.id)
        self.bb.publish("weather.risks", risks, self.id)
        self.say(f"7-day outlook: {total_rain} mm rain, max {summary['max_temp']:.0f}°C, "
                 f"ET₀ avg {summary['avg_et0']} mm/day, {fungal_days} fungal-risk days.")
        if rain_days:
            d = days[rain_days[0]]
            self.say(f"Rain alert: {d['rain']:.0f} mm expected {d['day']}. Factor this into irrigation.",
                     to="irrigation", level="warn")
        if fungal_days >= 2:
            self.say(f"Humid spell ({fungal_days} days ≥80% RH). Disease spread risk is elevated.",
                     to="disease", level="warn")
        if heat_days:
            self.say(f"{heat_days} day(s) above {c['t_max']}°C. Expect heat-stress yield penalty.",
                     to="yield", level="warn")
        return out
