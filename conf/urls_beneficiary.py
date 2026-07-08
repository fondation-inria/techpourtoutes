from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from techpourtoutes import views
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
    path("", views.beneficiary_home, name="home"),
    path("coalition/", views.coalition_home, name="coalition_home"),
    path("coalition/", include("techpourtoutes.urls_coalition")),
    path("", include("techpourtoutes.urls_common")),
]
