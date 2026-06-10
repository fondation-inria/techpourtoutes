import functools

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def client_ip(request):
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key_value(request, dimension):
    if dimension == "ip":
        return client_ip(request)
    if dimension == "email":
        return request.POST.get("email", "").strip().lower()
    return ""


def _parse_rate(rate):
    max_requests, window = rate.split("/")
    return int(max_requests), int(window)


def rate_limit(setting_name, *, keys=("ip",)):
    """Throttle POST requests per client IP and/or submitted email.

    `setting_name` points at a settings value of the form "<max>/<seconds>", read at request
    time so it can be tuned per environment (and overridden in tests). The limit is enforced
    independently on each dimension in `keys`; a request is blocked (HTTP 429) as soon as one
    of them exceeds the limit within the window. No-op in local development (DEBUG).
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "POST" and not settings.DEBUG:
                max_requests, window = _parse_rate(getattr(settings, setting_name))
                for dimension in keys:
                    value = _key_value(request, dimension)
                    if not value:
                        continue
                    cache_key = f"ratelimit:{view.__name__}:{dimension}:{value}"
                    cache.add(cache_key, 0, window)
                    try:
                        count = cache.incr(cache_key)
                    except ValueError:
                        cache.set(cache_key, 1, window)
                        count = 1
                    if count > max_requests:
                        return HttpResponse(
                            "Trop de tentatives. Veuillez réessayer plus tard.", status=429
                        )
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
