import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import demo, providers
from .analysis import analyze_routes
from .corridor import sample_corridor
from .serializers import (ValidationError, parse_heatmap_request, parse_request,
                          serialize_heatmap, serialize_results)
from .weather import ForecastRangeError

log = logging.getLogger(__name__)

HEATMAP_HOURS = 49          # forecast slider: +0h .. +48h from departure


def _error(status, message, **extra):
    return JsonResponse({"error": message, **extra}, status=status)


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "demo_enabled": settings.DEMO_WEATHER_ENABLED})


def _demo_refused(params):
    if params["demo"] and not settings.DEMO_WEATHER_ENABLED:
        return _error(400, "Invalid input.",
                      fields={"demo": "Demo mode is disabled on this server."})
    return None


def _read_body(request):
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


@require_POST
def analyze(request):
    body = _read_body(request)
    if body is None:
        return _error(400, "Request body must be a JSON object.")

    try:
        params = parse_request(body)
    except ValidationError as e:
        return _error(400, "Invalid input.", fields=e.errors)

    refused = _demo_refused(params)
    if refused:
        return refused

    fetch_weather = demo.fetch_weather if params["demo"] else providers.fetch_weather
    try:
        origin = providers.geocode(params["origin"])
        dest = providers.geocode(params["destination"])
        routes = providers.fetch_routes(origin, dest)
        results, best = analyze_routes(
            routes, params["departure"], params["load_lb"],
            fetch_weather, params["interval"])
    except LookupError as e:
        return _error(422, str(e))
    except ForecastRangeError as e:
        return _error(422, f"Weather forecast unavailable for that time: {e}")
    except requests.RequestException:
        log.exception("Upstream API failure")
        return _error(502, "A routing or weather service is unavailable. Try again shortly.")

    payload = serialize_results(results, best, origin, dest)
    payload["demo"] = params["demo"]
    return JsonResponse(payload)


@require_POST
def heatmap(request):
    body = _read_body(request)
    if body is None:
        return _error(400, "Request body must be a JSON object.")
    try:
        params = parse_heatmap_request(body)
    except ValidationError as e:
        return _error(400, "Invalid input.", fields=e.errors)

    refused = _demo_refused(params)
    if refused:
        return refused

    fetch_window = demo.fetch_weather_window if params["demo"] else providers.fetch_weather_window
    points = sample_corridor(params["routes"])
    try:
        windows = fetch_window(
            points, params["departure"], HEATMAP_HOURS)
    except ForecastRangeError as e:
        return _error(422, f"Weather forecast unavailable for that time: {e}")
    except requests.RequestException:
        log.exception("Upstream API failure")
        return _error(502, "The weather service is unavailable. Try again shortly.")

    payload = serialize_heatmap(points, windows, params["departure"], params["load_lb"])
    payload["demo"] = params["demo"]
    return JsonResponse(payload)
