from django.conf import settings
from django.shortcuts import render


def donnees_personnelles(request):
    return render(request, "legals/donnees_personnelles.html", {"site_url": settings.SITE_URL})


def conditions_generales(request):
    return render(request, "legals/conditions_generales.html", {"site_url": settings.SITE_URL})


def mentions_legales(request):
    return render(request, "legals/mentions_legales.html", {"site_url": settings.SITE_URL})


def accessibilite(request):
    return render(request, "legals/accessibilite.html", {"site_url": settings.SITE_URL})


def schema_pluriannuel(request):
    return render(request, "legals/schema_pluriannuel.html", {"site_url": settings.SITE_URL})
