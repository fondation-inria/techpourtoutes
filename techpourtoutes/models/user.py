from django.contrib.auth.models import AbstractUser

from .base import BaseModel


class User(BaseModel, AbstractUser):
    class Meta(AbstractUser.Meta):
        abstract = False
        swappable = "AUTH_USER_MODEL"
