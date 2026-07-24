import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import AbstractUser, UserManager
from django.core import signing
from django.core.validators import EmailValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .base import BaseModel

LOGIN_TOKEN_TTL = timedelta(hours=1)
VERIFICATION_CODE_TTL = timedelta(minutes=15)
VERIFICATION_CODE_MAX_ATTEMPTS = 5
EMAIL_CHANGE_TOKEN_SALT = "email-change"


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class User(BaseModel, AbstractUser):
    objects = ActiveUserManager()
    all_objects = models.Manager()
    email = models.EmailField(
        _("adresse mail"),
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
    login_code_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("hash du code de connexion envoyé par mail à l'utilisateur"),
    )
    login_code_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("datetime d'expiration du code de connexion envoyé par mail au user"),
    )
    login_code_attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("nombre de tentatives de saisie du code de connexion"),
    )
    email_change_code_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("hash du code de changement d'adresse mail"),
    )
    email_change_code_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("datetime d'expiration du code de changement d'adresse mail"),
    )
    email_change_attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("nombre de tentatives de saisie du code de changement d'adresse mail"),
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
        self.login_token_hash = _hash_token(plaintext)
        self.login_token_expires_at = timezone.now() + LOGIN_TOKEN_TTL
        self.save()
        return plaintext

    @classmethod
    def consume_login_token(cls, *, plaintext: str) -> User | None:
        h = _hash_token(plaintext)
        user = cls.objects.filter(
            login_token_hash=h, login_token_expires_at__gt=timezone.now()
        ).first()
        if user is None:
            return None
        updated = cls.objects.filter(pk=user.pk, login_token_hash=h).update(
            login_token_hash="", login_token_expires_at=None
        )
        if not updated:
            return None
        return user

    _LOGIN_CODE_FIELDS = {
        "hash_field": "login_code_hash",
        "expires_field": "login_code_expires_at",
        "attempts_field": "login_code_attempts",
    }
    _EMAIL_CHANGE_CODE_FIELDS = {
        "hash_field": "email_change_code_hash",
        "expires_field": "email_change_code_expires_at",
        "attempts_field": "email_change_attempts",
    }

    def issue_login_code(self) -> str:
        return self._issue_verification_code(**self._LOGIN_CODE_FIELDS)

    def consume_login_code(self, plaintext: str) -> bool:
        return self._consume_verification_code(plaintext, **self._LOGIN_CODE_FIELDS)

    def set_email_change_code(self) -> str:
        return self._issue_verification_code(**self._EMAIL_CHANGE_CODE_FIELDS)

    def consume_email_change_code(self, plaintext: str) -> bool:
        return self._consume_verification_code(plaintext, **self._EMAIL_CHANGE_CODE_FIELDS)

    def apply_email_change(self, new_email: str) -> None:
        self.email = new_email
        self.username = new_email
        self._reset_code_state(**self._EMAIL_CHANGE_CODE_FIELDS)
        self.save()

    def _issue_verification_code(
        self, *, hash_field: str, expires_field: str, attempts_field: str
    ) -> str:
        code = generate_numeric_code()
        setattr(self, hash_field, _hash_token(code))
        setattr(self, expires_field, timezone.now() + VERIFICATION_CODE_TTL)
        setattr(self, attempts_field, 0)
        self.save()
        return code

    def _consume_verification_code(
        self, plaintext: str, *, hash_field: str, expires_field: str, attempts_field: str
    ) -> bool:
        stored_hash = getattr(self, hash_field)
        expires_at = getattr(self, expires_field)
        if (
            not stored_hash
            or expires_at is None
            or expires_at < timezone.now()
            or getattr(self, attempts_field) >= VERIFICATION_CODE_MAX_ATTEMPTS
        ):
            return False
        if _hash_token(plaintext) != stored_hash:
            self._register_failed_attempt(
                hash_field=hash_field, expires_field=expires_field, attempts_field=attempts_field
            )
            return False
        # Conditional UPDATE — atomic at the DB level, blocks a double-submit race.
        consumed = User.objects.filter(pk=self.pk, **{hash_field: stored_hash}).update(
            **{hash_field: "", expires_field: None, attempts_field: 0}
        )
        return bool(consumed)

    def _register_failed_attempt(
        self, *, hash_field: str, expires_field: str, attempts_field: str
    ) -> None:
        setattr(self, attempts_field, getattr(self, attempts_field) + 1)
        if getattr(self, attempts_field) >= VERIFICATION_CODE_MAX_ATTEMPTS:
            self._reset_code_state(
                hash_field=hash_field, expires_field=expires_field, attempts_field=attempts_field
            )
        self.save()

    def _reset_code_state(
        self, *, hash_field: str, expires_field: str, attempts_field: str
    ) -> None:
        setattr(self, hash_field, "")
        setattr(self, expires_field, None)
        setattr(self, attempts_field, 0)

    def issue_email_change_token(self, new_email: str, stage: str) -> str:
        return signing.dumps(
            {"user_pk": str(self.pk), "new_email": new_email, "stage": stage},
            salt=EMAIL_CHANGE_TOKEN_SALT,
        )

    def read_email_change_token(self, token: str) -> dict | None:
        try:
            payload = signing.loads(token, salt=EMAIL_CHANGE_TOKEN_SALT)
        except signing.BadSignature:
            return None
        if payload.get("user_pk") != str(self.pk):
            return None
        return payload

    def email_change_verify_url(self, token: str) -> str:
        return f"{reverse('email_change_verify')}?{urlencode({'token': token})}"

    def soft_delete(self):
        self.is_active = False
        self.set_unusable_password()
        self.first_name = ""
        self.last_name = ""
        self.username = f"deleted_{self.pk}"
        self.email = f"deleted_{self.pk}@deleted.local"
        self.login_token_hash = ""
        self.login_token_expires_at = None
        self.login_code_hash = ""
        self.login_code_expires_at = None
        self.login_code_attempts = 0
        self.brevo_sync_enabled = False
        self.save()


def _hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def generate_numeric_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
