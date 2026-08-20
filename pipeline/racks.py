"""Fetch and parse bike racks and parking from OpenStreetMap"""

import json
import os

import pandas as pd
import requests

from pipeline.config import CITIES, RAW

OVERPASS = "https://overpass-api.de/api/interpreter"

QUERY = """
[out:json][timeout:180];
(
    node["amenity"="bicycle_parking"]({south}, {west}, {north}, {east});
    way["amenity"="bicycle_parking"]({south}, {west}, {north}, {east});
);
out center tags;
"""

def fetch_raw(city, bbox):
    path = f"{RAW}/osm_{city}.json"
    if os.path.exists(path):
        print(f" {city}: using cached {path}")
        with open(path) as f:
            return json.load(f)

    print(f" {city}: querying Overpass")
    r = requests.post(OVERPASS, data={"data":  QUERY.format(**bbox)}, timeout=300)
    r.raise_for_status()
    data = r.json()
    with open(path, "w") as f:
        json.dump(data, f)
    return data

def parse(data, city):
    rows = []
    for el in data["elements"]:
        if el["type"] == "node":
            lat, lng = el["lat"], el["lon"]
        elif "center" in el:
            lat, lng = el["center"]["lat"], el["center"]["lon"]
        else:
            continue

        tags = el.get("tags", {})
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "city": city,
            "lat": lat,
            "lng": lng,
            "capacity_raw": tags.get("capacity"),
            "parking_type": tags.get("bicycle_parking"),
            "covered": tags.get("covered"),
            "access": tags.get("access"),
            "surveillance": tags.get("surveillance"),
            "operator": tags.get("operator"),
            "name": tags.get("name"),
        })
    return rows

def clean_capacity(value):
    if value is None:
        return None
    text = str(value).strip().split(";")[0].replalce("~", "").replace("+", "")
    try:
        n = float(text)
    except ValueError:
        return  None
    if n <= 0 or n > 2000:
        return None
    return n

def main():
    os.makedirs(RAW, exist_ok=True)
    rows = []
    for city, bbox in CITIES.items():
        rows.extend(parse(fetch_raw(city, bbox), city))

    df = pd.DataFrame(rows)
    df["capacity"] = df["capacity_raw"].map(clean_capacity)

    before = len(df)
    df["_k"] = df["lat"].round(5).astype(str) + "_" + df["lng"].round(5).astype(str)
    df = df.drop_duplicates("_k").drop(columns="_k")

    df.to_csv(f"{RAW}/racks.csv", index = False)

    tagged = df["capacity"].notna().sum()
    print(f"\n{len(df)} racks ({before - len(df)} duplicates removed)")
    print(f"{tagged} have a capacity tag ({100 * tagged / len(df):.0f}%)")
    print("\nTop parking types:")
    print(df["parking_type"].value_counts().head(10))

if __name__ == "__main__":
    main()