"""Pure geometry helpers: distances, checkpoint placement, segment ownership."""
import bisect
import math

EARTH_RADIUS_MI = 3958.8
METERS_PER_MILE = 1609.344


def haversine_mi(a, b):
    """a, b are (lat, lon) in degrees."""
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(coords, total_miles):
    """Distance along the polyline at each vertex, rescaled so the last value
    equals the routing API's own distance (haversine sums run slightly short)."""
    cum = [0.0]
    for p, q in zip(coords, coords[1:]):
        cum.append(cum[-1] + haversine_mi(p, q))
    raw = cum[-1]
    scale = total_miles / raw if raw else 0.0
    return [c * scale for c in cum]


def point_at(coords, cum, d):
    """(lat, lon) at distance d miles along the polyline (linear interpolation)."""
    if d <= 0:
        return coords[0]
    if d >= cum[-1]:
        return coords[-1]
    i = bisect.bisect_right(cum, d) - 1
    span = cum[i + 1] - cum[i]
    t = (d - cum[i]) / span if span else 0.0
    (la1, lo1), (la2, lo2) = coords[i], coords[i + 1]
    return (la1 + (la2 - la1) * t, lo1 + (lo2 - lo1) * t)


def auto_interval(total_miles):
    """Default sampling interval: finer on short trips, coarser on long ones."""
    if total_miles <= 200:
        return 10
    if total_miles <= 600:
        return 25
    return 50


def checkpoint_distances(total_miles, interval):
    """0, interval, 2*interval ... plus the destination."""
    ds = []
    d = 0.0
    while d < total_miles:
        ds.append(d)
        d += interval
    ds.append(total_miles)
    return ds


def segment_miles(dists, total_miles):
    """Each checkpoint owns the road halfway to its neighbours, so the segments
    tile the route exactly and sum to total_miles."""
    bounds = [0.0] + [(a + b) / 2 for a, b in zip(dists, dists[1:])] + [total_miles]
    return [bounds[i + 1] - bounds[i] for i in range(len(dists))]
