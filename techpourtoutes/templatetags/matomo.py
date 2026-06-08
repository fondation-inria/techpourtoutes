from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

SNIPPET = """<!-- Matomo -->
<script>
  var _paq = window._paq = window._paq || [];
  _paq.push(['disableCookies']);
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u="%(url)s/";
    _paq.push(['setTrackerUrl', u+'matomo.php']);
    _paq.push(['setSiteId', '%(site_id)s']);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
  })();
</script>
<!-- End Matomo Code -->"""


@register.simple_tag
def matomo_tracking():
    if not (settings.MATOMO_URL and settings.MATOMO_SITE_ID):
        return ""
    return mark_safe(SNIPPET % {"url": settings.MATOMO_URL, "site_id": settings.MATOMO_SITE_ID})
