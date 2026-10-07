from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def sentry_browser():
    """Loads the browser SDK, in the same Sentry project as the app. `defer` keeps the order:
    the SDK runs before the script that initialises it."""
    if not settings.SENTRY_DSN:
        return ""
    return format_html(
        '<script defer src="{}"></script>\n<script defer src="{}" data-dsn="{}"></script>',
        static("js/sentry.min.js"),
        static("js/sentry_init.js"),
        settings.SENTRY_DSN,
    )
