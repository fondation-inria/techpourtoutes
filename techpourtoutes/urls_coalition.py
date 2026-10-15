from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.coalition_home, name="coalition_home"),
    path("inscription/", views.pro_inscription_funnel, name="pro_inscription_funnel"),
    path(
        "inscription/new/",
        views.new_pro_inscription_funnel,
        name="new_pro_inscription_funnel",
    ),
    path("engagements/<str:engagement>/", views.new_pro_engagement, name="new_pro_engagement"),
    path(
        "engagements/<str:engagement>/ajouter/",
        views.create_pro_engagement,
        name="create_pro_engagement",
    ),
    path("mentorer/", views.new_mentor, name="new_mentor"),
    path("pitcher-mon-metier/", views.new_work_ambassador, name="new_work_ambassador"),
    path(
        "devenir-ambassadrice-etudiante/",
        views.new_training_ambassador,
        name="new_training_ambassador",
    ),
    path("accueillir-une-stagiaire/", views.new_internship, name="new_internship"),
    path(
        "devenir-mecene/",
        RedirectView.as_view(pattern_name="new_structure_engagement", permanent=True),
    ),
    path(
        "engager-ma-structure/",
        views.new_structure_engagement,
        name="new_structure_engagement",
    ),
    path("organiser-un-atelier/", views.new_workshop_request, name="new_workshop_request"),
    path("proposer-un-evenement/", views.new_event, name="new_event"),
    path("evenements/<uuid:pk>/modifier/", views.edit_event, name="edit_event"),
    path("evenements/creer/", views.create_event, name="create_event"),
    path(
        "evenements/importer-un-visuel/",
        views.create_event_image_upload,
        name="create_event_image_upload",
    ),
    path("evenements/enregistrer/", views.update_event, name="update_event"),
    path("mes-evenements/", views.index_pro_events, name="index_pro_events"),
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
