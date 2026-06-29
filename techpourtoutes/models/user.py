import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .base import BaseModel

LOGIN_TOKEN_TTL = timedelta(hours=1)


def _hash_login_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


class User(BaseModel, AbstractUser):
    email = models.EmailField(
        _("adresse email"),
        validators=[EmailValidator(message=_("Saisissez une adresse mail valide."))],
    )
    login_token_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("hash du token de connexion envoyé par mail à l'utilisateur"),
    )
    login_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("datetime d'expiration du token de connexion envoyé par mail au user"),
    )
    brevo_sync_enabled = models.BooleanField(
        default=False,
        verbose_name=_("synchroniser avec Brevo"),
        help_text=_("Si décoché, ce compte n'est pas synchronisé vers Brevo."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("est un compte activé"),
        help_text=_("Si décoché, ce compte est désactivé"),
    )

    class Meta(AbstractUser.Meta):
        abstract = False
        swappable = "AUTH_USER_MODEL"

    @classmethod
    def from_db(cls, db, field_names, values):
        # Remember the stored Brevo sync state so the post_save signal can tell a genuine
        # opt-out (True -> False) from a contact that was never synced.
        instance = super().from_db(db, field_names, values)
        instance._loaded_brevo_sync_enabled = instance.brevo_sync_enabled
        return instance

    def issue_login_token(self) -> str:
        plaintext = secrets.token_urlsafe(32)
        self.login_token_hash = _hash_login_token(plaintext)
        self.login_token_expires_at = timezone.now() + LOGIN_TOKEN_TTL
        self.save()
        return plaintext

    @classmethod
    def consume_login_token(cls, *, plaintext: str) -> User | None:
        h = _hash_login_token(plaintext)
        user = cls.objects.filter(
            login_token_hash=h, login_token_expires_at__gt=timezone.now()
        ).first()
        if user is None:
            return None
        # Conditional UPDATE — atomic at the DB level, blocks a double-click race.
        updated = cls.objects.filter(pk=user.pk, login_token_hash=h).update(
            login_token_hash="", login_token_expires_at=None
        )
        if not updated:
            return None
        return user

    def deactivate_user(self):
        self.is_active = False
        self.set_unusable_password()
        self.first_name = ""
        self.last_name = ""
        self.email = f"deleted_{self.pk}@deleted.local"
        self.login_token_hash = ""
        self.login_token_expires_at = None
        self.brevo_sync_enabled = False
        self.deactivate_specific_fields()

    def deactivate_specific_fields(self):
        pass
