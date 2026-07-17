from django.http import HttpResponse
from django.urls import reverse


def robots_txt(request):
    lines = [
        "User-agent: *",
        f"Disallow: {reverse('account')}",
        f"Disallow: {reverse('login_to_jobirl')}",
        f"Disallow: {reverse('coalition_welcome')}",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
