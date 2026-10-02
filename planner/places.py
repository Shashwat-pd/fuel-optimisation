import csv
import re
from functools import lru_cache
from pathlib import Path

PLACES_FILE = Path(__file__).resolve().parent.parent / "data" / "places.csv"
SHORT_WORDS = {"SAINT": "ST", "SAINTE": "STE", "FORT": "FT", "MOUNT": "MT"}


def make_key(city, state):
    words = re.sub(r"[^A-Z0-9 ]", " ", city.upper().replace("'", "")).split()
    return state.strip().upper(), "".join(SHORT_WORDS.get(w, w) for w in words)


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


def find_city(city, state):
    return load_places().get(make_key(city, state))
