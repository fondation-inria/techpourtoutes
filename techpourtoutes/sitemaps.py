from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from waffle import switch_is_active

COMMON_PAGE_NAMES = [
    "notre_manifeste",
    "qui_sommes_nous",
    "pourquoi_nous_ecrivons_au_feminin",
    "contact",
]

COALITION_PAGE_NAMES = [
    "coalition_home",
    "mentor_landing",
    "work_ambassador_landing",
    "training_ambassador_landing",
    "internships_landing",
    "sponsor_landing",
    "workshops_landing",
    "signer_manifeste",
]

BENEFICIARY_PAGE_NAMES = [
    "home",
]


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        if switch_is_active("beneficiary_mode"):
            return BENEFICIARY_PAGE_NAMES + COALITION_PAGE_NAMES + COMMON_PAGE_NAMES
        return COALITION_PAGE_NAMES + COMMON_PAGE_NAMES

    def location(self, item):
        return reverse(item)
