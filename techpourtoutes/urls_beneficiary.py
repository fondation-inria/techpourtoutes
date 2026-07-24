from django.urls import path

from . import views

urlpatterns = [
    path("", views.beneficiary_home, name="home"),
    path("inscription/", views.inscription_funnel, name="inscription_funnel"),
]
