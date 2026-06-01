from django.urls import path

from . import views

urlpatterns = [
    # Coalition
    path("", views.coalition_index, name="coalition_index"),
    path("mentorer/", views.mentor_landing, name="mentor_landing"),
    path("pitcher-mon-metier/", views.work_ambassador_landing, name="work_ambassador_landing"),
    path("accueillir-une-stagiaire/", views.internships_landing, name="internships_landing"),
    path("bienvenue-dans-la-coalition/", views.coalition_welcome, name="coalition_welcome"),
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
