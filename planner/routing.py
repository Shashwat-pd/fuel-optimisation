import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

from planner.errors import PlanError


def fetch_osrm(url, params):
    key = "osrm:" + hashlib.sha256(f"{url}?{sorted(params.items())}".encode()).hexdigest()
    data = cache.get(key)
    if data is not None:
        return data
    try:
        response = requests.get(url, params=params, headers={"User-Agent": "SpotterFuelPlanner/1.0"}, timeout=(3, 15))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        raise PlanError("Routing provider unavailable. Try again later.", "upstream_unavailable", 502)
    cache.set(key, data, settings.ROUTE_CACHE_SECONDS)
    return data


def get_route(start, finish):
    coords = f"{start['longitude']:.6f},{start['latitude']:.6f};{finish['longitude']:.6f},{finish['latitude']:.6f}"
    data = fetch_osrm(
        f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{coords}",
        {"overview": "full", "geometries": "geojson", "steps": "false", "alternatives": "false"},
    )
    try:
        if data["code"] != "Ok":
            raise PlanError("No drivable route found.", "no_route", 422)
        route = data["routes"][0]
        if route["distance"] <= 0 or len(route["geometry"]["coordinates"]) < 2:
            raise PlanError("Start and finish must produce a nonzero route.")
        return route
    except (KeyError, IndexError, TypeError):
        raise PlanError("Malformed routing response.", "upstream_unavailable", 502)
