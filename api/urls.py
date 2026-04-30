from django.conf import settings
from django.urls import path

urlpatterns = []

if settings.MOCK_JOBIRL_API:
    from .views import mock_jobirl_register

    urlpatterns += [path("techpourtoutes/api/user_register", mock_jobirl_register)]
