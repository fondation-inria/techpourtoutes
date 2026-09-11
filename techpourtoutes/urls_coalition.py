from django.urls import path

from . import views

urlpatterns = [
    path("", views.coalition_home, name="coalition_home"),
    path("mentorer/", views.new_mentor, name="new_mentor"),
    path("mentorer/inscription/", views.create_mentor, name="create_mentor"),
    path("pitcher-mon-metier/", views.new_work_ambassador, name="new_work_ambassador"),
    path(
        "pitcher-mon-metier/inscription/",
        views.create_work_ambassador,
        name="create_work_ambassador",
    ),
    path(
        "devenir-ambassadrice-etudiante/",
        views.new_training_ambassador,
        name="new_training_ambassador",
    ),
    path(
        "devenir-ambassadrice-etudiante/inscription/",
        views.create_training_ambassador,
        name="create_training_ambassador",
    ),
    path("accueillir-une-stagiaire/", views.new_internship, name="new_internship"),
    path("devenir-mecene/", views.new_sponsor, name="new_sponsor"),
    path("devenir-mecene/inscription/", views.create_sponsor, name="create_sponsor"),
    path("organiser-un-atelier/", views.new_workshop_request, name="new_workshop_request"),
    path(
        "organiser-un-atelier/demande/",
        views.create_workshop_request,
        name="create_workshop_request",
    ),
    path("bienvenue-dans-la-coalition/", views.coalition_welcome, name="coalition_welcome"),
    path("signer-le-manifeste/", views.new_manifeste_signature, name="new_manifeste_signature"),
    path(
        "signer-le-manifeste/signature/",
        views.create_manifeste_signature,
        name="create_manifeste_signature",
    ),
    path(
        "signer-le-manifeste/merci/",
        views.show_manifeste_signature,
        name="show_manifeste_signature",
    ),
]
