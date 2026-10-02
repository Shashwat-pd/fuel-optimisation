import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

from planner.errors import PlanError


def decode_polyline6(text):
    coordinates = []
    lat = lon = index = 0
    while index < len(text):
        deltas = []
        for _ in range(2):
            result = shift = 0
            while True:
                byte = ord(text[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        coordinates.append([lon / 1e6, lat / 1e6])
    return coordinates


def fetch_osrm(url, params):
    try:
        response = requests.get(url, params=params, headers={"User-Agent": "SpotterFuelPlanner/1.0"}, timeout=(3, 15))
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        raise PlanError("Routing provider unavailable. Try again later.", "upstream_unavailable", 502)


def get_route(start, finish):
    coords = f"{start['longitude']:.6f},{start['latitude']:.6f};{finish['longitude']:.6f},{finish['latitude']:.6f}"
    key = "route:" + hashlib.sha256(coords.encode()).hexdigest()
    route = cache.get(key)

    if route is None:
        data = fetch_osrm(
            f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{coords}",
            {"overview": "full", "geometries": "polyline6", "steps": "false", "alternatives": "false"},
        )
        try:
            if data["code"] != "Ok":
                raise PlanError("No drivable route found.", "no_route", 422)
            found = data["routes"][0]
            route = {"distance": found["distance"], "duration": found["duration"], "polyline": found["geometry"]}
            coordinates = decode_polyline6(route["polyline"])
        except (KeyError, IndexError, TypeError):
            raise PlanError("Malformed routing response.", "upstream_unavailable", 502)
        cache.set(key, route, settings.ROUTE_CACHE_SECONDS)
    else:
        coordinates = decode_polyline6(route["polyline"])

    geometry = {"type": "LineString", "coordinates": coordinates}
    if route["distance"] <= 0 or len(coordinates) < 2:
        raise PlanError("Start and finish must produce a nonzero route.")
    return {"distance": route["distance"], "duration": route["duration"], "geometry": geometry}
