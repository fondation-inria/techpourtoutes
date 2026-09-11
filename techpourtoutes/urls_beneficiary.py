from django.urls import path

from . import views

urlpatterns = [
    path("", views.beneficiary_home, name="home"),
    path("inscription/", views.inscription_funnel, name="inscription_funnel"),
    path("trouver-une-mentore/", views.new_mentoree, name="new_mentoree"),
    path("devenir-mentoree/", views.mentoring_funnel, name="mentoring_funnel"),
    path(
        "inscription/passer-mentorat/",
        views.show_skip_mentoring_signup_modal,
        name="show_skip_mentoring_signup_modal",
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
    path(
        "evenements/rejoindre-le-club/",
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
        "evenements/<uuid:pk>/",
        views.show_event,
        name="show_event",
    ),
]
