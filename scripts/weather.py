#!/usr/bin/env python3
"""Writes the weather as plain text, so a Meshtastic auto-responder can quote it with %url(...)%.

GitHub Pages cannot run server code, so this script runs in GitHub Actions every 15 minutes,
rebuilds the .txt files and commits them. The browser page (index.html) keeps using JavaScript;
the .txt is for anything that cannot run it.
"""

import json
import math
import urllib.request
from pathlib import Path

# One file per city: <slug>.txt next to index.html, so Pages serves /weather/<slug>.txt.
CITIES = {
    "pyatigorsk": {"place": "Пятигорске", "lat": 44.0486, "lon": 43.0594},
}

# Primary host first; the ensemble host answers the same shape where the main one is unreachable.
FORECAST_URLS = [
    "https://api.open-meteo.com/v1/forecast?{query}",
    "https://ensemble-api.open-meteo.com/v1/ensemble?{query}&models=icon_seamless",
]

WMO = {
    0: "Ясно",
    1: "Малооблачно",
    2: "Переменная облачность",
    3: "Облачно",
    45: "Туман",
    48: "Изморозь",
    51: "Слабая морось",
    53: "Морось",
    55: "Сильная морось",
    56: "Ледяная морось",
    57: "Сильная ледяная морось",
    61: "Небольшой дождь",
    63: "Дождь",
    65: "Сильный дождь",
    66: "Ледяной дождь",
    67: "Сильный ледяной дождь",
    71: "Небольшой снег",
    73: "Снег",
    75: "Сильный снег",
    77: "Снежная крупа",
    80: "Ливень",
    81: "Сильный ливень",
    82: "Очень сильный ливень",
    85: "Снегопад",
    86: "Сильный снегопад",
    95: "Гроза",
    96: "Гроза с градом",
    99: "Сильная гроза с градом",
}


# JavaScript's Math.round, which the page used: .5 always goes up.
def round_half(value):
    return math.floor(float(value) + 0.5)


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "cocofielddlc-weather/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_weather(lat, lon):
    query = (
        "latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code,cloud_cover"
        "&hourly=precipitation&forecast_days=1&timezone=auto"
    ).format(lat=lat, lon=lon)

    last_error = None
    for template in FORECAST_URLS:
        try:
            return fetch_json(template.format(query=query))
        except Exception as error:  # noqa: BLE001 - the next host is the point
            last_error = error
    raise last_error if last_error else RuntimeError("no forecast host answered")


def precipitation_next_hours(data, hours=6):
    current = data.get("current", {}).get("time", "")
    hour = current[:13] + ":00" if len(current) >= 13 else ""
    times = data.get("hourly", {}).get("time", [])
    values = data.get("hourly", {}).get("precipitation", [])
    if hour not in times:
        return 0.0
    start = times.index(hour)
    window = values[start : start + hours]
    return sum(value for value in window if isinstance(value, (int, float)))


def describe(code):
    return WMO.get(int(code or 0), "Погода без описания")


def build_line(city, data):
    current = data["current"]
    temperature = round_half(current["temperature_2m"])
    cloudiness = round_half(current.get("cloud_cover", 0))
    code = int(current.get("weather_code", 0))
    amount = precipitation_next_hours(data)

    if amount > 0.1:
        tail = "в ближайшее время ожидаются осадки"
    else:
        tail = "в ближайшее время осадков не ожидается"

    return "Погода в {place}: {desc}, {temp}°C, облачность {cloud}%, {tail}".format(
        place=city["place"], desc=describe(code), temp=temperature, cloud=cloudiness, tail=tail
    )


def main():
    root = Path(__file__).resolve().parent.parent
    for slug, city in CITIES.items():
        data = fetch_weather(city["lat"], city["lon"])
        line = build_line(city, data)
        (root / (slug + ".txt")).write_text(line + "\n", encoding="utf-8")
        print(slug + ": " + line)


if __name__ == "__main__":
    main()
