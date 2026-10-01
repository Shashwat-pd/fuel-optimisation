import requests
from django.core.cache import cache

OSRM_URL = "https://router.project-osrm.org"
METERS_PER_MILE = 1609.344
CACHE_SECONDS = 60 * 60 * 24


class RouteNotFound(Exception):
    pass


def get_route(start, finish):
    coords = f"{start['longitude']},{start['latitude']};{finish['longitude']},{finish['latitude']}"
    cache_key = f"osrm:{coords}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        f"{OSRM_URL}/route/v1/driving/{coords}",
        params={"overview": "full", "geometries": "geojson"},
        timeout=15,
    )
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteNotFound(data.get("message", "No route found"))
    route = data["routes"][0]
    result = {
        "geometry": route["geometry"],
        "distance_miles": route["distance"] / METERS_PER_MILE,
        "duration_seconds": route["duration"],
    }
    cache.set(cache_key, result, CACHE_SECONDS)
    return result
