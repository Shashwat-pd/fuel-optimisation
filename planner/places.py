import csv
from functools import lru_cache
from pathlib import Path

PLACES_FILE = Path(__file__).resolve().parent.parent / "data" / "places.csv"


def make_key(city, state):
    return state.strip().upper(), " ".join(city.replace(".", "").lower().split())


@lru_cache(maxsize=1)
def load_places():
    places = {}
    with open(PLACES_FILE, newline="") as f:
        for row in csv.DictReader(f):
            places[make_key(row["name"], row["state"])] = {
                "name": f"{row['name']}, {row['state']}",
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }
    return places


def find_place(text):
    city, _, state = text.rpartition(",")
    return load_places().get(make_key(city, state))
