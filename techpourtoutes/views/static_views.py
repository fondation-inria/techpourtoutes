from django.conf import settings
from django.shortcuts import redirect, render


def donnees_personnelles(request):
    return render(request, "static/donnees_personnelles.html", {"site_url": settings.SITE_URL})


def conditions_generales(request):
    return render(request, "static/conditions_generales.html", {"site_url": settings.SITE_URL})


def mentions_legales(request):
    return render(request, "static/mentions_legales.html", {"site_url": settings.SITE_URL})


def accessibilite(request):
    return render(request, "static/accessibilite.html", {"site_url": settings.SITE_URL})


def schema_pluriannuel(request):
    return render(request, "static/schema_pluriannuel.html", {"site_url": settings.SITE_URL})


def a_propos(request):
    return redirect("notre_manifeste")


def notre_manifeste(request):
    return render(request, "static/notre_manifeste.html", {"site_url": settings.SITE_URL})


def signature_manifeste(request):
    manifeste_url = f"{settings.SITE_URL}/notre-manifeste/"
    return render(
        request,
        "static/signature_manifeste.html",
        {
            "site_url": settings.SITE_URL,
            "linkedin_share_url": f"https://www.linkedin.com/sharing/share-offsite/?url={manifeste_url}",
        },
    )


def qui_sommes_nous(request):
    return render(request, "static/qui_sommes_nous.html", {"site_url": settings.SITE_URL})


def pourquoi_nous_ecrivons_au_feminin(request):
    return render(
        request, "static/pourquoi_nous_ecrivons_au_feminin.html", {"site_url": settings.SITE_URL}
    )


def contact(request):
    return render(request, "static/contact.html", {"site_url": settings.SITE_URL})
