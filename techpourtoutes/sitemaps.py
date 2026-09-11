from django.contrib.sitemaps import Sitemap
from django.urls import reverse

COMMON_PAGE_NAMES = [
    "notre_manifeste",
    "qui_sommes_nous",
    "pourquoi_nous_ecrivons_au_feminin",
    "contact",
]

COALITION_PAGE_NAMES = [
    "coalition_home",
    "new_mentor",
    "new_work_ambassador",
    "new_training_ambassador",
    "new_internship",
    "new_sponsor",
    "new_workshop_request",
    "new_manifeste_signature",
]

BENEFICIARY_PAGE_NAMES = ["home", "new_mentoree", "index_events"]


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return BENEFICIARY_PAGE_NAMES + COALITION_PAGE_NAMES + COMMON_PAGE_NAMES

    def location(self, item):
        return reverse(item)
