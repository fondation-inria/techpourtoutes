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
]
