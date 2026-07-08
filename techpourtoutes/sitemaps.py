from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "mentor_landing",
            "work_ambassador_landing",
            "training_ambassador_landing",
            "internships_landing",
            "sponsor_landing",
            "workshops_landing",
            "notre_manifeste",
            "qui_sommes_nous",
            "pourquoi_nous_ecrivons_au_feminin",
            "contact",
        ]

    def location(self, item):
        return reverse(item)
