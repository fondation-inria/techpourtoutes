from django.urls import path

from . import views

urlpatterns = [
    path("", views.coallition_index, name="coallition_index"),
    path("je-deviens-mentor/", views.mentor_landing, name="mentor_landing"),
    path("bienvenue-dans-la-coallition/", views.mentor_success, name="mentor_success"),
]
