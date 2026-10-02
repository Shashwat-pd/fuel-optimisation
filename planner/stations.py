from decimal import Decimal

import numpy as np
from django.conf import settings
from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from planner.models import Station

METERS_PER_MILE = 1609.344


def stations_along_route(geometry, distance_miles):
    coords = geometry["coordinates"]
    lons, lats = np.array(coords, dtype=float).T
    geodesic = Geod(ellps="WGS84").inv(lons[:-1], lats[:-1], lons[1:], lats[1:])[2]
    along = np.r_[0.0, np.cumsum(geodesic)]
    if along[-1] <= 0:
        return []
    route_miles = along / along[-1] * distance_miles

    to_meters = Transformer.from_crs(4326, 2163, always_xy=True).transform
    xy = np.column_stack(to_meters(lons, lats))
    line = LineString(xy)
    flat = np.r_[0.0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]

    rows = list(
        Station.objects.filter(
            latitude__gte=lats.min() - 0.1,
            latitude__lte=lats.max() + 0.1,
            longitude__gte=lons.min() - 0.5,
            longitude__lte=lons.max() + 0.5,
        ).values("external_id", "name", "address", "latitude", "longitude", "price")
    )
    if not rows:
        return []

    points = [Point(*to_meters(r["longitude"], r["latitude"])) for r in rows]
    near = STRtree(points).query(line, predicate="dwithin", distance=settings.STATION_CORRIDOR_MILES * METERS_PER_MILE)

    result = []
    for i in near:
        row, point = rows[i], points[i]
        price = Decimal(row.pop("price"))
        row["distance_from_route_miles"] = round(line.distance(point) / METERS_PER_MILE, 3)
        result.append({"mile": float(np.interp(line.project(point), flat, route_miles)), "price": price, "station": row})
    return result
