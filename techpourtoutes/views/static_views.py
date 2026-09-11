from django.shortcuts import redirect, render


def donnees_personnelles(request):
    return render(request, "static/donnees_personnelles.html", {})


def conditions_generales(request):
    return render(request, "static/conditions_generales.html", {})


def mentions_legales(request):
    return render(request, "static/mentions_legales.html", {})


def accessibilite(request):
    return render(request, "static/accessibilite.html", {})


def schema_pluriannuel(request):
    return render(request, "static/schema_pluriannuel.html", {})


def a_propos(request):
    return redirect("notre_manifeste")


def notre_manifeste(request):
    return render(request, "static/notre_manifeste.html", {})


def qui_sommes_nous(request):
    return render(request, "static/qui_sommes_nous.html", {})


def pourquoi_nous_ecrivons_au_feminin(request):
    return render(request, "static/pourquoi_nous_ecrivons_au_feminin.html", {})


def contact(request):
    return render(request, "static/contact.html", {})
