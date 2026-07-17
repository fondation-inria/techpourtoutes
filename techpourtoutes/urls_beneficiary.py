from django.urls import path

from . import views

urlpatterns = [
    path("", views.beneficiary_home, name="home"),
]
