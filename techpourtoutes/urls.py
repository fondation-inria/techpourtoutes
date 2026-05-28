from django.urls import path

from . import views

urlpatterns = [
    # Coallition
    path("", views.coallition_index, name="coallition_index"),
    path("je-deviens-mentor/", views.mentor_landing, name="mentor_landing"),
    path("bienvenue-dans-la-coallition/", views.mentor_success, name="mentor_success"),
    # Auth
    path("se-connecter/", views.login_request, name="login_request"),
    path("se-connecter/email-envoye/", views.login_email_sent, name="login_email_sent"),
    path("se-connecter/token/<str:token>/", views.login_verify, name="login_verify"),
    path("mon-compte/", views.account, name="account"),
    path("mon-compte/infos/", views.account_info, name="account_info"),
    path("mon-compte/modifier/", views.account_edit, name="account_edit"),
    path("se-deconnecter/", views.logout_view, name="logout"),
    path("mon-compte-mentor/", views.login_to_jobirl, name="login_to_jobirl"),
    # Legals
    path("donnees-personnelles/", views.donnees_personnelles, name="donnees_personnelles"),
    path("conditions-generales/", views.conditions_generales, name="conditions_generales"),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("accessibilite/", views.accessibilite, name="accessibilite"),
    path("schema-pluriannuel-accessibilite", views.schema_pluriannuel, name="schema_pluriannuel"),
]
