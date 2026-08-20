"""Fetch bicycle theft data from data.police.uk.

Locations are anonymised, with every crime snapped to the nearest point, so coordinates are approximate."""

import json
import os
import time

import pandas as pd
import requests

from pipeline.config import CITIES, RAW

BASE = "https://data.police.uk/api"
CATEGORY = "bicycle-theft"

def available_months():
    """Months the API has data for."""
    r = requests.get(f"{BASE}/crimes-street-dates", timeout=30)
    r.raise_for_status()
    return[entry["date"] for entry in r.json()]

def _poly(bbox):
    """Format a bounding box as the API's lat,lng:latlng poly parameter"""
    corners = [
        (bbox["south"], bbox["west"]),
        (bbox["north"], bbox["west"]),
        (bbox["north"], bbox["east"]),
        (bbox["south"], bbox["east"]),
    ]
    return ":".join(f"{lat},{lng}" for lat, lng in corners)

def fetch_city_month(city, bbox, month):
    url = f"{BASE}/crimes-street/{CATEGORY}"
    r = requests.get(url, params={"poly": _poly(bbox), "date": month}, timeout=60)

    if r.status_code == 503:
        raise RuntimeError(f"503 for {city} {month}: area too large")

    r.raise_for_status()
    rows = []
    for crime in r.json():
        loc = crime.get("location")
        if not loc:
            continue
        rows.append({
            "city": city,
            "month": crime["month"],
            "lat": float(loc["latitude"]),
            "lng": float(loc["longitude"]),
            "street": loc["street"]["name"],
            "persistent_id": crime.get("persistent_id", ""),
        })
    return rows

def main():
    os.makedirs(RAW, exist_ok=True)
    months = available_months()
    for city, bbox in CITIES.items():
        for month in months:
            rows = fetch_city_month(city, bbox, month)
            all_rows.extend(rows)
            print(f" {city} {month}: {len(rows)}")
            time.sleep(0.3)

    df = pd.DataFrame(all_rows)
    out = f"{RAW}/thefts.csv"
    df.to_csv(out, index=False)

    meta = {"months": months, "fetched_rows": len(df)}
    with open(f"{RAW}/thefts_meta.json",  "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved {len(df)} thefts to {out}")

if __name__ == "__main__":
    main()