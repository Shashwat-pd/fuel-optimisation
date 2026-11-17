# fuel-optimisation

A Django REST Framework API that plans where to buy fuel on a road trip inside the United States. You give it a start city and a finish city ("City, ST"), and optionally how much fuel is in the tank. It gets a driving route from OSRM, finds the fuel stations within 5 miles of that route, and picks where to stop and how many gallons to buy at each stop so the trip costs as little as possible. The vehicle is fixed in code at 10 MPG with a 50-gallon tank (500 miles of range). The response contains the route geometry as GeoJSON, the distance and driving time, the list of fuel stops (station, route mile, price, gallons, cost), the total fuel cost, and the fuel in the tank at the start and end.

## How it works

A request goes through four steps, in `planner/trip.py`:

1. **Resolve the cities.** `"Austin, TX"` is split on the last comma and normalised to a key (upper case, punctuation removed, `SAINT` to `ST`, `FORT` to `FT`, and so on). The key is looked up in the `Place` table, which is loaded from `data/places.csv`.

2. **Get the route.** `planner/routing.py` calls the OSRM `route/v1/driving` endpoint (default `https://router.project-osrm.org`, configurable with `OSRM_URL`) with full overview geometry in polyline6 format. The compact polyline, distance and duration are stored in Django's file-based cache for 24 hours, keyed by a SHA-256 hash of the start and finish coordinates, and decoded into a GeoJSON `LineString` on every request. OSRM errors, timeouts and malformed responses become a `502 upstream_unavailable` error.

3. **Find stations along the route** (`planner/stations.py`).
   - A bounding box around the route (with a small margin) is used as a database filter on the indexed `latitude`/`longitude` columns, so only nearby stations are loaded.
   - The route and the candidate stations are projected to a metric CRS (EPSG:2163). A Shapely `STRtree` query with `dwithin` keeps stations within `STATION_CORRIDOR_MILES` (5) of the route line.
   - Each kept station is projected onto the line to get its position along the route. That position is converted to a route mile by interpolating against cumulative WGS84 geodesic distance along the route, scaled to OSRM's reported distance.

4. **Plan the fuel stops** (`planner/fuel.py`, `plan_fuel`).
   - Stations are sorted by route mile. A virtual zero-cost station is placed behind the start, at the distance that makes the starting tank equal to `initial_fuel_gallons`. This lets a partly full starting tank be handled like any other stop.
   - **Break stations.** `find_breaks` marks every station that has nothing cheaper within the 500 miles behind it (the virtual start station is always one). Since no cheaper fuel could have been carried into a break, the plan treats each break as the start of an independent stretch: it arrives there with an empty tank, and the stretch ends at the next break or at the destination.
   - **Within a stretch.** If the end of the stretch is within range, the plan buys just enough at the break to reach it. If not, it fills the tank and hops to the cheapest station within range ahead (`find_next_cheapest`, ties go to the furthest one), then repeats from there until the end is reachable. If no station is in range, the API returns `422 insufficient_coverage`.
   - A second pass replays the plan from the real starting tank to work out the fuel on arrival and departure at each stop and the cost of each purchase. Prices and costs use `Decimal`, and costs are rounded to cents.

**Complexity.** With `n` stations on the route, sorting is O(n log n). `find_breaks` and `find_next_cheapest` each scan, for every station, only the stations within 500 miles behind or ahead of it, so they are O(n·k), where `k` is the largest number of stations in any 500-mile window. In the worst case (every station within 500 miles of every other) that is O(n²). The planning loop itself only moves forward along the route, so it is O(n).

## API

### `POST /api/route/`

Request body (JSON; unknown fields are rejected):

| Field | Type | Required | Notes |
|---|---|---|---|
| `start` | string, max 200 chars | yes | `"City, ST"`, e.g. `"Chicago, IL"` |
| `finish` | string, max 200 chars | yes | `"City, ST"` |
| `initial_fuel_gallons` | number, 0 to 50 | no | Defaults to 50 (a full tank) |

Example response shape. The field names are real; the values are illustrative, not output from a real run:

```json
{
  "start":  {"name": "Chicago, IL", "latitude": 41.85, "longitude": -87.65},
  "finish": {"name": "Denver, CO",  "latitude": 39.74, "longitude": -104.98},
  "distance_miles": 1003.4,
  "duration_minutes": 905,
  "total_money_spent": "151.98",
  "fuel": {
    "start_gallons": 50.0,
    "used_gallons": 100.34,
    "end_gallons": 0.0
  },
  "fuel_stops": [
    {
      "name": "EXAMPLE TRUCK STOP",
      "address": "I-80, Exit 123, Some City, NE",
      "latitude": 40.81,
      "longitude": -96.70,
      "mile": 480.2,
      "price_per_gallon": "3.0190",
      "gallons": 50.34,
      "cost": "151.98"
    }
  ],
  "route": {"type": "LineString", "coordinates": [[-87.65, 41.85], "..."]},
  "attribution": "Routing: OSRM, map data © OpenStreetMap contributors; places: US Census Bureau, GeoNames"
}
```

Money values are strings. Stops where less than 0.005 gallons would be bought are left out.

Errors share one shape, set in `planner/errors.py`:

```json
{"error": {"code": "invalid_input", "message": "Request validation failed.",
           "details": [{"loc": ["finish"], "type": "required", "msg": "This field is required."}]}}
```

Error codes the code can return:

| Status | Code | When |
|---|---|---|
| 400 | `invalid_input` | Validation failed, or the route has zero length |
| 413 | `request_too_large` | Body over 16 KB |
| 422 | `location_not_found` | City not in the places table |
| 422 | `no_route` | OSRM found no drivable route |
| 422 | `insufficient_coverage` | A gap between stations is longer than the vehicle's range |
| 502 | `upstream_unavailable` | OSRM unreachable or returned something unexpected |
| 503 | `places_not_loaded` | `import_places` has not been run |

## Running locally

Requirements: Python 3.12 or newer (Django 6.x requires it) and the packages in `requirements.txt` (Django, Django REST Framework, requests, Shapely, pyproj, NumPy). The database is SQLite (`db.sqlite3` in the project root), and the route cache is written to `.cache/`.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Environment variables (all optional for local use):

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `1` | Set to anything other than `1` to turn debug off |
| `DJANGO_SECRET_KEY` | a development key | Must be set when debug is off, or startup fails |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Comma-separated |
| `OSRM_URL` | `https://router.project-osrm.org` | OSRM server to route with |

### Load data

Load the city list first. Station import uses it to place stations, and the API uses it to resolve start and finish cities.

```sh
python manage.py import_places                 # defaults to data/places.csv
python manage.py import_places path/to/places.csv
```

`places.csv` has the columns `state,name,latitude,longitude`. The import replaces all existing places in one transaction.

Then load fuel stations. A fuel price file is not included in the repository; supply your own.

```sh
python manage.py import_fuel path/to/fuel.csv
python manage.py import_fuel path/to/fuel.csv --replace   # delete existing stations first
```

`import_fuel` accepts two CSV formats:

- **Basic:** `id,name,latitude,longitude,price`, plus an optional `address` column. Coordinates must fall on US land (checked against `data/us.geojson`). Price must be positive, below 10000, with at most four decimal places.
- **OPIS truck-stop export:** columns `OPIS Truckstop ID, Truckstop Name, Address, City, State, Retail Price`. The file has no coordinates, so each station is placed at its city's coordinates from the places table. Rows whose city is not found are skipped and counted. If one station ID appears more than once, the lowest price is kept.

The import is atomic: one bad row aborts it and leaves the existing data unchanged. Without `--replace` it upserts on station ID.

### Call the API

```sh
python manage.py runserver

curl -s -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Chicago, IL", "finish": "Denver, CO", "initial_fuel_gallons": 20}'
```

## Project layout

```
config/                    Django settings and root URLconf (mounts planner at /api/)
data/
  places.csv               US place names with coordinates
  us.geojson               US land outline, used to validate station coordinates
planner/
  views.py                 RouteView: validates the request and calls plan_trip
  urls.py                  route/ endpoint
  serializers.py           Request validation (strict numbers, no unknown fields, US-only coordinates)
  trip.py                  Orchestrates city lookup, routing, station search and fuel planning; shapes the response
  places.py                City name normalisation and lookup against the Place table
  routing.py               OSRM client, polyline6 decoder, route caching
  stations.py              Finds stations within the route corridor and their route mile
  fuel.py                  Cost-minimising fuel-stop algorithm
  geography.py             Point-in-US check using data/us.geojson
  errors.py                PlanError and the API's uniform error format
  models.py                Station and Place models
  management/commands/
    import_places.py       Loads the city list
    import_fuel.py         Loads fuel stations from a basic or OPIS CSV
  migrations/              Schema migrations
  tests.py                 Empty test stub
```

## Limitations

- **Fixed vehicle.** MPG (10) and tank size (50 gallons) are constants in `planner/fuel.py`, not request parameters. The plan assumes constant consumption and lets the tank run to empty.
- **No tests.** `planner/tests.py` is the default empty stub.
- **External routing dependency.** Every uncached route calls OSRM. The default is the public demo server at `router.project-osrm.org`, which is not meant for production traffic. If it is down, uncached requests fail with 502.
- **Approximate station locations for OPIS data.** OPIS rows are placed at their city's coordinates, not the station's real location. The 5-mile corridor check and the route mile are therefore approximate, and a station on an interstate exit can be included or left out based on where its city's point is.
- **City-level input only.** Start and finish must be `"City, ST"` names in the places table; addresses and coordinates are not accepted.
- **Single source of prices.** Prices are whatever was last imported. There is no refresh schedule and no record of when a price was observed.
- **Local-only setup.** SQLite and a file-based cache. There is no deployment configuration, authentication or rate limiting (all requests are allowed).
- **Route only, no detours.** The planner only considers stations within 5 miles of the route, and it does not count the extra distance to drive off the route to a station.
