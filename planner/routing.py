import requests
from django.core.cache import cache

OSRM_URL = "https://router.project-osrm.org"
METERS_PER_MILE = 1609.344
CACHE_SECONDS = 60 * 60 * 24


class RouteNotFound(Exception):
    pass


def get_route(start, finish):
    coords = f"{start['longitude']:.6f},{start['latitude']:.6f};{finish['longitude']:.6f},{finish['latitude']:.6f}"
    cache_key = f"osrm:{coords}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        f"{OSRM_URL}/route/v1/driving/{coords}",
        params={"overview": "full", "geometries": "geojson", "steps": "false", "alternatives": "false"},
        headers={"User-Agent": "SpotterFuelPlanner/1.0"},
        timeout=(3, 15),
    )
    if response.status_code >= 500:
        response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteNotFound(data.get("message", "No route found"))
    route = data["routes"][0]
    if route["distance"] <= 0:
        raise RouteNotFound("Start and finish are the same place")
    result = {
        "geometry": route["geometry"],
        "distance_miles": route["distance"] / METERS_PER_MILE,
        "duration_seconds": route["duration"],
    }
    cache.set(cache_key, result, CACHE_SECONDS)
    return result
