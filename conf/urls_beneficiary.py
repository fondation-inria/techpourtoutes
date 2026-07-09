from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from techpourtoutes.sitemaps import StaticViewSitemap
from techpourtoutes.views.robots_views import robots_txt

sitemaps = {"static": StaticViewSitemap}

urlpatterns = [
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("robots.txt", robots_txt),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("techpourtoutes.urls_common")),
    path("", include("techpourtoutes.urls_beneficiary")),
    path("coalition/", include("techpourtoutes.urls_coalition")),
]
