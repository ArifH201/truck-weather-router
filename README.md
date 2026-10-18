# Weather-Aware Truck Routing

A React + Django app that helps a truck driver pick the safest of three routes
based on **weather, load weight, and travel time**.

Enter an origin, destination, departure time, and load weight. The app fetches
three route options, samples the forecast at the truck's *estimated arrival time*
at each checkpoint, scores the risk, recommends a route, and shows everything on a
map with a 0-48 hour corridor weather heatmap.

**Live app:** _add URL_ · **Walkthrough:** _add Loom link_

## How it works

```
Browser (React + Leaflet)                      Django API                       Third parties
  TripForm ── POST /api/analyze ─────────►  geocode ───────────────────────►  Nominatim
                                            fetch 3 routes ─────────────────►  OSRM
                                            checkpoints + ETAs
                                            one batched forecast ───────────►  Open-Meteo
                                            classify risk (load rules)
                                            rank routes, explain winner
  routes, cards, markers ◄─────────────────  JSON
  slider ── POST /api/heatmap ───────────►  sample corridor, 49h forecast ──►  Open-Meteo (cached)
  heatmap ◄────────────────────────────────  compact per-hour arrays
```

The backend is stateless: no database, no sessions. Weather responses are cached
in memory for 30 minutes.

## Risk rules

Each checkpoint is classified by its worst condition (wind, rain, snow), then the
load rules can only *escalate* it.

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | <25 | 25-34 | 35-44 | 45-54 | ≥55 |
| Rain (in/hr) | <0.10 | 0.10-0.25 | 0.25-0.50 | 0.50-1.00 | >1.00 |
| Snow (in/hr) | <0.5 | 0.5-1.0 | 1.0-2.0 | 2.0-3.0 | >3.0 |

Load rules: wind ≥55 is No Travel for any load; wind 45-54 with a load over
30,000 lb is No Travel; wind 35-44 with a load over 40,000 lb is Severe.

**Boundary conventions** (the spec's ranges overlap or leave gaps):
- Each level's lower bound is inclusive: 35.0 mph is High, 0.25 in/hr rain is High.
- No Travel follows the spec's operators literally: `>=` for wind, `>` for rain and
  snow, so exactly 1.00 in/hr rain is still Severe.
- Values between published ranges (e.g. 34.5 mph) fall into the lower level.
- Load thresholds are strict: exactly 30,000 lb is *not* over 30,000 lb.

## Route recommendation

Routes are ranked, in this order, by: fewest Severe miles, fewest High miles,
lowest average risk, shortest travel time. A route containing any No Travel
segment ranks after every route without one.

"Miles" are real distances. Each checkpoint owns the road halfway to its
neighbours, so segments tile the route exactly; average risk is weighted by those
distances (0 = Low … 4 = No Travel). The API returns a one-sentence reason naming
the first criterion on which the winner beats the runner-up.

## Heatmap

`/api/heatmap` samples up to 150 points along the routes (de-duplicated, spacing
widens on long trips) and returns one array per metric with an entry for each
forecast hour (+0h to +48h from departure). The slider indexes into data the
browser already holds, so scrubbing causes no network calls. If the departure is
near the end of the 16-day forecast window the slider is shortened rather than
failing.

## API

`POST /api/analyze`

```json
{ "origin": "Chicago, IL", "destination": "Denver, CO",
  "departure": "2026-10-12T14:00:00Z", "load_lb": 42000, "interval_miles": 25 }
```
`interval_miles` is optional (10, 25, or 50); by default it is 10 mi for routes up
to 200 mi, 25 mi up to 600 mi, otherwise 50 mi. `departure` needs a timezone offset.
Returns `routes[]` (geometry, metrics, checkpoints with ETA and weather, rank),
`recommended_index`, and `recommendation_reason`.

`POST /api/heatmap` takes `{ geometries: [[[lat, lon], ...], ...], departure, load_lb }`
and returns `{ start, hours, points: [{ lat, lon, wind[], rain[], snow[], risk[] }] }`.

`GET /api/health` returns `{"status": "ok"}`.

Errors: 400 invalid input (with per-field messages), 422 unknown place or forecast
unavailable, 502 upstream service down.

## Demo mode (simulated storm)

Real forecasts are often calm, which makes the heatmap hard to demonstrate. For
testing and walkthroughs there is an optional **demo mode**: a deterministic storm
band sweeps across the corridor over ~32 hours, passing through every risk level.
Routes and geocoding stay real; only the forecast is simulated (`routing/demo.py`).

- A "Demo mode" checkbox appears in the form only when the server enables it.
- It is on by default when `DJANGO_DEBUG=1` and off in production unless you set
  `DEMO_WEATHER_ENABLED=1`.
- When active, the UI shows a "DEMO MODE: simulated weather" banner and a
  SIMULATED tag on the heatmap, and the API responses carry `"demo": true`.

## Assumptions and limitations

- **Truck speed:** OSRM models cars, so durations are multiplied by 1.15
  (`TRUCK_TIME_FACTOR` in `providers.py`). This is an assumption, not data.
- **ETAs** assume constant average speed along each route.
- **Wind** uses 10 m sustained speed; gusts would be more conservative.
- **Forecast resolution** is hourly on a grid of roughly 10 km, and the nearest hour
  to each ETA is used.
- **Routing alternatives:** the OSRM public demo server sometimes returns fewer
  than three routes and is rate-limited. `fetch_routes` is the only function to
  change to use OpenRouteService or Mapbox instead.
- **Nominatim** requires roughly 1 request/second; geocoding is throttled and cached.
- Forecasts reach about 15 days ahead.
- Heatmap and route checkpoints use different samples: the heatmap shows the
  corridor at a chosen hour, the route scores use each checkpoint's own ETA.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver          # http://localhost:8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxies /api)
```

## Tests

```bash
cd backend && pytest        # 46 tests: risk boundaries, load rules, ranking, ETAs, API, heatmap
cd frontend && npm test     # formatting and map helper functions
```

External APIs are mocked in the tests, so run one real trip before deploying.

## Layout

```
backend/routing/
  risk.py        classification + load rules
  recommend.py   metrics, ranking, explanation
  geo.py         distances, checkpoint placement, segment ownership
  weather.py     Open-Meteo parsing and unit conversion
  analysis.py    routes + weather -> scored results
  corridor.py    heatmap sampling
  providers.py   Nominatim / OSRM / Open-Meteo clients, caching
  serializers.py request validation and JSON shaping
  views.py       endpoints
frontend/src/
  components/    TripForm, RouteCards, MapView, HeatmapLayer, HeatmapControls
  lib/           api, risk colours and helpers, formatting
```

## Possible improvements

Per-segment speed from the router for more accurate ETAs, gust-based wind, a
persistent cache (Redis) shared between workers, risk-coloured route segments on
the map, and a commercial routing API with real truck profiles.
