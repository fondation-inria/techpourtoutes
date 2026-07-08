from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("se-connecter/", views.login_request, name="login_request"),
    path("se-connecter/email-envoye/", views.login_email_sent, name="login_email_sent"),
    path("se-connecter/token/<str:token>/", views.login_verify, name="login_verify"),
    path("mon-compte/", views.account, name="account"),
    path("mon-compte/infos/", views.account_info, name="account_info"),
    path("mon-compte/modifier/", views.account_edit, name="account_edit"),
    path(
        "mon-compte/communication/",
        views.account_communication,
        name="account_communication",
    ),
    path(
        "mon-compte/formations/<uuid:pk>/",
        views.training_experience_info,
        name="training_experience_info",
    ),
    path(
        "mon-compte/formations/<uuid:pk>/modifier/",
        views.training_experience_edit,
        name="training_experience_edit",
    ),
    path("se-deconnecter/", views.logout_view, name="logout"),
    path("mon-compte-mentor/", views.login_to_jobirl, name="login_to_jobirl"),
    path(
        "mon-compte/supprimer/confirmation",
        views.delete_account_modal,
        name="delete_account_modal",
    ),
    path("mon-compte/supprimer", views.delete_account, name="delete_account"),
    # Static
    path("donnees-personnelles/", views.donnees_personnelles, name="donnees_personnelles"),
    path("conditions-generales/", views.conditions_generales, name="conditions_generales"),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("accessibilite/", views.accessibilite, name="accessibilite"),
    path("schema-pluriannuel-accessibilite/", views.schema_pluriannuel, name="schema_pluriannuel"),
    path("a-propos/", views.a_propos, name="a_propos"),
    path("notre-manifeste/", views.notre_manifeste, name="notre_manifeste"),
    path("qui-sommes-nous/", views.qui_sommes_nous, name="qui_sommes_nous"),
    path(
        "pourquoi-nous-ecrivons-au-feminin/",
        views.pourquoi_nous_ecrivons_au_feminin,
        name="pourquoi_nous_ecrivons_au_feminin",
    ),
    path("contact/", views.contact, name="contact"),
]
