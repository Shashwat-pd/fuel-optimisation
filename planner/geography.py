import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape

US_FILE = Path(__file__).resolve().parent.parent / "data" / "us.geojson"


@lru_cache(maxsize=1)
def us_shape():
    return shape(json.loads(US_FILE.read_text())["geometry"])


def in_us(latitude, longitude):
    return us_shape().covers(Point(longitude, latitude))
