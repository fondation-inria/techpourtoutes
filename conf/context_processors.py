from django.conf import settings
from waffle import switch_is_active


def global_settings(request):
    return {
        "SITE_URL": settings.SITE_URL,
        "FAVICON_NAMEFILE": settings.FAVICON_NAMEFILE,
        "DEFAULT_SITE_MODE": "student" if switch_is_active("student_home") else "coalition",
    }
