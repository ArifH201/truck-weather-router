"""Sampling points along the trip corridor for the weather heatmap."""
from .geo import checkpoint_distances, cumulative_miles, haversine_mi, point_at

MAX_POINTS = 150      # total across all routes: keeps API calls and payload small
MIN_SPACING_MI = 10


def polyline_miles(coords):
    return sum(haversine_mi(p, q) for p, q in zip(coords, coords[1:]))


def sample_corridor(routes, max_points=MAX_POINTS):
    """Evenly spaced (lat, lon) points along every route, rounded to 2 dp
    (~1 km, matching the weather cache) and de-duplicated, so stretches shared
    by several routes are only fetched once. Spacing widens on long trips so
    the total stays within the cap."""
    per_route = max(2, max_points // max(len(routes), 1))
    seen, points = set(), []
    for coords in routes:
        total = polyline_miles(coords)
        spacing = max(MIN_SPACING_MI, total / (per_route - 1))
        cum = cumulative_miles(coords, total)
        for d in checkpoint_distances(total, spacing):
            lat, lon = point_at(coords, cum, d)
            key = (round(lat, 2), round(lon, 2))
            if key not in seen:
                seen.add(key)
                points.append(key)
    return points
