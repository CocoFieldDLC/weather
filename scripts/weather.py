#!/usr/bin/env python3
"""Writes the weather as plain text, so a Meshtastic auto-responder can quote it with %url(...)%.

GitHub Pages cannot run server code, so this script runs in GitHub Actions every 15 minutes,
rebuilds the .txt files and commits them. The browser page (index.html) keeps using JavaScript;
the .txt is for anything that cannot run it.
"""

import json
import math
import urllib.parse
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

# The whole line must stay readable in one Meshtastic message.
MAX_LENGTH = 180

WMO = {
    0: "ясно",
    1: "малооблачно",
    2: "переменная облачность",
    3: "облачно",
    45: "туман",
    48: "изморозь",
    51: "слабая морось",
    53: "морось",
    55: "сильная морось",
    56: "ледяная морось",
    57: "сильная ледяная морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "ледяной дождь",
    67: "сильный ледяной дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    77: "снежная крупа",
    80: "ливень",
    81: "сильный ливень",
    82: "очень сильный ливень",
    85: "снегопад",
    86: "сильный снегопад",
    95: "гроза",
    96: "гроза с градом",
    99: "сильная гроза с градом",
}


# JavaScript's Math.round, which the page used: .5 always goes up.
def round_half(value):
    return int(math.floor(float(value) + 0.5))


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "cocofielddlc-weather/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_weather(lat, lon):
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,cloud_cover",
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,weather_code",
            "forecast_days": 2,
            "timezone": "auto",
        },
        safe=",",
    )

    last_error = None
    for template in FORECAST_URLS:
        try:
            return fetch_json(template.format(query=query))
        except Exception as error:  # noqa: BLE001 - the next host is the point
            last_error = error
    raise last_error if last_error else RuntimeError("no forecast host answered")


def describe(code):
    try:
        number = int(code or 0)
    except (TypeError, ValueError):
        number = 0
    return WMO.get(number, "погода без описания")


def sentence(text):
    return text[:1].upper() + text[1:] if text else text


def signed(value):
    number = round_half(value)
    return ("+" if number >= 0 else "-") + str(abs(number))


def plain(value):
    return str(round_half(value))


def millimetres(value):
    text = ("%.1f" % round(float(value), 1)).rstrip("0").rstrip(".")
    return text.replace(".", ",")


def current_part(city, data):
    current = data.get("current") or {}
    return "Погода в {place}: {desc}, {temp}°C, облачность {cloud}%".format(
        place=city["place"],
        desc=sentence(describe(current.get("weather_code"))),
        temp=plain(current.get("temperature_2m", 0)),
        cloud=round_half(current.get("cloud_cover", 0)),
    )


def tomorrow_part(data):
    daily = data.get("daily") or {}
    codes = daily.get("weather_code") or []
    lows = daily.get("temperature_2m_min") or []
    highs = daily.get("temperature_2m_max") or []
    sums = daily.get("precipitation_sum") or []

    if len(codes) < 2 or len(lows) < 2 or len(highs) < 2:
        return ""
    if lows[1] is None or highs[1] is None:
        return ""

    pieces = [
        "Завтра: " + describe(codes[1]),
        signed(lows[1]) + "…" + signed(highs[1]) + "°C",
    ]

    amount = sums[1] if len(sums) >= 2 else None
    if isinstance(amount, (int, float)):
        pieces.append("без осадков" if amount < 0.05 else "осадки до " + millimetres(amount) + " мм")

    return ", ".join(pieces)


def build_line(city, data):
    head = current_part(city, data)
    tail = tomorrow_part(data)

    variants = ([head + ". " + tail] if tail else []) + [head]
    for line in variants:
        if len(line) <= MAX_LENGTH:
            return line
    return variants[-1][:MAX_LENGTH].rstrip()


def main():
    root = Path(__file__).resolve().parent.parent
    for slug, city in CITIES.items():
        data = fetch_weather(city["lat"], city["lon"])
        line = build_line(city, data)
        (root / (slug + ".txt")).write_text(line + "\n", encoding="utf-8")
        print(slug + ": " + line)


if __name__ == "__main__":
    main()
