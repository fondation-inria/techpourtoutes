from django.urls import path

from . import views

urlpatterns = [
    path("", views.beneficiary_home, name="home"),
    path("inscription/", views.inscription_funnel, name="inscription_funnel"),
    path("trouver-une-mentore/", views.find_mentor_landing, name="find_mentor_landing"),
    path("devenir-mentoree/", views.add_mentoring, name="add_mentoring"),
    path(
        "inscription/passer-mentorat/",
        views.mentoring_signup_skip_modal,
        name="mentoring_signup_skip_modal",
    ),
    path("bientot-disponible/", views.bientot_disponible, name="bientot_disponible"),
    path("evenements/", views.events, name="events"),
    path("evenements/suite/", views.more_events, name="more_events"),
    path(
        "evenements/rejoindre-le-club/",
        views.saved_event_signup_modal,
        name="saved_event_signup_modal",
    ),
    path(
        "evenements/<uuid:pk>/enregistrer/",
        views.toggle_saved_event,
        name="toggle_saved_event",
    ),
]
