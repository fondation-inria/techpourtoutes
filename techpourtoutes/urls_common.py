from django.urls import path

from . import views

urlpatterns = [
    # Account
    path("se-connecter/", views.login_request, name="login_request"),
    path("se-connecter/code/", views.login_code, name="login_code"),
    path("se-connecter/token/<str:token>/", views.login_verify, name="login_verify"),
    path("mon-compte/", views.show_account, name="show_account"),
    path("mon-compte/profil/", views.show_user, name="show_user"),
    path("mon-compte/profil/infos/", views.show_user_info, name="show_user_info"),
    path("mon-compte/profil/modifier/", views.edit_user, name="edit_user"),
    path("mon-compte/profil/update/", views.update_user, name="update_user"),
    path(
        "mon-compte/profil/communication/update",
        views.update_user_communication,
        name="update_user_communication",
    ),
    path("mon-compte/mail/", views.show_user_email, name="show_user_email"),
    path("mon-compte/mail/changer/", views.edit_user_email, name="edit_user_email"),
    path(
        "mon-compte/mail/changer/demande/",
        views.create_user_email_change,
        name="create_user_email_change",
    ),
    path(
        "mon-compte/mail/verifier/",
        views.show_user_email_verification,
        name="show_user_email_verification",
    ),
    path("mon-compte/mail/valider/", views.update_user_email, name="update_user_email"),
    path(
        "mon-compte/mail/code/renvoyer/",
        views.create_user_email_code,
        name="create_user_email_code",
    ),
    path(
        "mon-compte/formations/pro/<uuid:pk>/",
        views.show_pro_training_experience,
        name="show_pro_training_experience",
    ),
    path(
        "mon-compte/formations/pro/<uuid:pk>/modifier/",
        views.edit_pro_training_experience,
        name="edit_pro_training_experience",
    ),
    path(
        "mon-compte/formations/pro/<uuid:pk>/update/",
        views.update_pro_training_experience,
        name="update_pro_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/ajouter/",
        views.new_beneficiary_training_experience,
        name="new_beneficiary_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/create/",
        views.create_beneficiary_training_experience,
        name="create_beneficiary_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/<uuid:pk>/",
        views.show_beneficiary_training_experience,
        name="show_beneficiary_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/<uuid:pk>/modifier/",
        views.edit_beneficiary_training_experience,
        name="edit_beneficiary_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/<uuid:pk>/update/",
        views.update_beneficiary_training_experience,
        name="update_beneficiary_training_experience",
    ),
    path(
        "mon-compte/formations/beneficiaire/<uuid:pk>/supprimer/",
        views.destroy_beneficiary_training_experience,
        name="destroy_beneficiary_training_experience",
    ),
    path("se-deconnecter/", views.destroy_session, name="destroy_session"),
    path("mon-compte-mentorat/", views.login_to_jobirl, name="login_to_jobirl"),
    path(
        "mon-compte/profil/supprimer/confirmation",
        views.destroy_user_modal,
        name="destroy_user_modal",
    ),
    path("mon-compte/profil/supprimer", views.destroy_user, name="destroy_user"),
    path("recherche-etablissements/", views.search_schools, name="search_schools"),
    path("recherche-formations/", views.search_formations, name="search_formations"),
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
