import re

from planner.errors import PlanError
from planner.models import Place

SHORT_WORDS = {"SAINT": "ST", "SAINTE": "STE", "FORT": "FT", "MOUNT": "MT"}


def make_key(city, state):
    words = re.sub(r"[^A-Z0-9 ]", " ", city.upper().replace("'", "")).split()
    return state.strip().upper(), "".join(SHORT_WORDS.get(w, w) for w in words)


def as_dict(place):
    return {"name": place.name, "latitude": place.latitude, "longitude": place.longitude}


def find_city(city, state):
    state_key, city_key = make_key(city, state)
    place = Place.objects.filter(state=state_key, key=city_key).first()
    if place is not None:
        return as_dict(place)
    if not Place.objects.exists():
        raise PlanError("City list is not loaded", "places_not_loaded", 503)
    return None


def find_place(text):
    city, _, state = text.rpartition(",")
    return find_city(city, state)


def all_places():
    return {(p.state, p.key): as_dict(p) for p in Place.objects.all()}
