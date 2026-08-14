from django.urls import path

from . import views

urlpatterns = [
    path("", views.coalition_home, name="coalition_home"),
    path("mentorer/", views.mentor_landing, name="mentor_landing"),
    path("pitcher-mon-metier/", views.work_ambassador_landing, name="work_ambassador_landing"),
    path(
        "devenir-ambassadrice-etudiante/",
        views.training_ambassador_landing,
        name="training_ambassador_landing",
    ),
    path("accueillir-une-stagiaire/", views.internships_landing, name="internships_landing"),
    path("devenir-mecene", views.sponsor_landing, name="sponsor_landing"),
    path("organiser-un-atelier", views.workshops_landing, name="workshops_landing"),
    path("signer-le-manifeste/", views.signer_manifeste, name="signer_manifeste"),
    path("bienvenue-dans-la-coalition/", views.coalition_welcome, name="coalition_welcome"),
    path("signature-manifeste/", views.signature_manifeste, name="signature_manifeste"),
]
