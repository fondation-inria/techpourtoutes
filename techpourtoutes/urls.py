from django.urls import path

from . import views

urlpatterns = [
    # Coallition
    path("", views.coallition_index, name="coallition_index"),
    path("je-deviens-mentor/", views.mentor_landing, name="mentor_landing"),
    path("bienvenue-dans-la-coallition/", views.mentor_success, name="mentor_success"),
    # Legals
    path("donnees-personnelles/", views.donnees_personnelles, name="donnees_personnelles"),
    path("conditions-generales/", views.conditions_generales, name="conditions_generales"),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("accessibilite/", views.accessibilite, name="accessibilite"),
    path("schema-pluriannuel-accessibilite", views.schema_pluriannuel, name="schema_pluriannuel"),
]
