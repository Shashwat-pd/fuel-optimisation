import shapely
from pyproj import Transformer
from shapely.geometry import LineString

from planner.models import Station

CORRIDOR_MILES = 5
METERS_PER_MILE = 1609.344

to_meters = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)


def stations_along_route(geometry, distance_miles):
    coords = geometry["coordinates"]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    pad = 0.2
    stations = list(Station.objects.filter(
        latitude__gte=min(lats) - pad,
        latitude__lte=max(lats) + pad,
        longitude__gte=min(lons) - pad,
        longitude__lte=max(lons) + pad,
    ))
    if not stations:
        return []

    line = LineString(zip(*to_meters.transform(lons, lats)))
    xs, ys = to_meters.transform([s.longitude for s in stations], [s.latitude for s in stations])
    points = shapely.points(xs, ys)
    shapely.prepare(line)
    near = shapely.dwithin(line, points, CORRIDOR_MILES * METERS_PER_MILE)

    result = []
    for station, point, is_near in zip(stations, points, near):
        if not is_near:
            continue
        mile = line.project(point) / line.length * distance_miles
        result.append({
            "id": station.external_id,
            "name": station.name,
            "address": station.address,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "price": station.price,
            "mile": mile,
            "distance_from_route_miles": round(line.distance(point) / METERS_PER_MILE, 2),
        })
    result.sort(key=lambda s: s["mile"])
    return result
