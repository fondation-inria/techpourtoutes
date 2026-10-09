from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.beneficiary_home, name="home"),
    path(
        "page-d-accueil-techpourtoutes-992956/",
        RedirectView.as_view(pattern_name="home", permanent=True),
    ),
    path("inscription/", views.inscription_funnel, name="inscription_funnel"),
    path("inscription/new/", views.new_inscription_funnel, name="new_inscription_funnel"),
    path("trouver-une-mentore/", views.new_mentoree, name="new_mentoree"),
    path("devenir-mentoree/", views.mentoring_funnel, name="mentoring_funnel"),
    path(
        "echanger-avec-une-etudiante/",
        views.new_training_ambassador_beneficiary,
        name="new_training_ambassador_beneficiary",
    ),
    path(
        "echanger-avec-une-etudiante/demande/",
        views.new_training_ambassador_request,
        name="new_training_ambassador_request",
    ),
    path(
        "echanger-avec-une-etudiante/demande/envoyer/",
        views.create_training_ambassador_request,
        name="create_training_ambassador_request",
    ),
    path(
        "inscription/passer/<str:step>/",
        views.show_skip_inscription_step_modal,
        name="show_skip_inscription_step_modal",
    ),
    path(
        "bientot-disponible/",
        views.new_upcoming_feature_notification,
        name="new_upcoming_feature_notification",
    ),
    path(
        "bientot-disponible/inscription/",
        views.create_upcoming_feature_notification,
        name="create_upcoming_feature_notification",
    ),
    path("evenements/", views.index_events, name="index_events"),
    path("mes-evenements/", views.index_beneficiary_events, name="index_beneficiary_events"),
    path(
        "evenements/<uuid:pk>/rejoindre-le-club/",
        views.create_saved_event_modal,
        name="create_saved_event_modal",
    ),
    path(
        "evenements/<uuid:pk>/enregistrer/",
        views.update_saved_event,
        name="update_saved_event",
    ),
    path(
        "evenements/<uuid:pk>/participer/",
        views.show_participation_modal,
        name="show_participation_modal",
    ),
    path(
        "evenements/<slug:slug>/",
        views.show_event,
        name="show_event",
    ),
]
