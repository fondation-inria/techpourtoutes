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
]
