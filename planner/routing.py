import requests

OSRM_URL = "https://router.project-osrm.org"
METERS_PER_MILE = 1609.344


class RouteNotFound(Exception):
    pass


def get_route(start, finish):
    coords = f"{start['longitude']},{start['latitude']};{finish['longitude']},{finish['latitude']}"
    response = requests.get(
        f"{OSRM_URL}/route/v1/driving/{coords}",
        params={"overview": "full", "geometries": "geojson"},
        timeout=15,
    )
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteNotFound(data.get("message", "No route found"))
    route = data["routes"][0]
    return {
        "geometry": route["geometry"],
        "distance_miles": route["distance"] / METERS_PER_MILE,
        "duration_seconds": route["duration"],
    }
