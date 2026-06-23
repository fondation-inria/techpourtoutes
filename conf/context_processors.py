from django.conf import settings


def global_settings(request):
    return {
        "SITE_URL": settings.SITE_URL,
        "FAVICON_NAMEFILE": settings.FAVICON_NAMEFILE,
    }
