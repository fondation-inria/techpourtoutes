import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .base import BaseModel, BaseQuerySet
from .beneficiary import Beneficiary


def _new_token():
    return secrets.token_urlsafe(32)


class LegalRepresentativeAuthorizationQuerySet(BaseQuerySet):
    def pending(self):
        return self.filter(status=LegalRepresentativeAuthorization.Status.PENDING)


class LegalRepresentativeAuthorization(BaseModel):
    """A minor's legal representative, asked to sign her authorization through a personal link.

    Until signed, the beneficiary may correct the name and email she gave: the request is then
    replaced, link included. Once signed, it is never touched again and keeps the proof: the
    identity declared, IP, the exact text signed, and the PDF mailed to the signatory with its
    hash, so an altered copy shows.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("en attente")
        SIGNED = "signed", _("signée")

    class Relationship(models.TextChoices):
        MOTHER = "mother", _("Mère")
        FATHER = "father", _("Père")
        GUARDIAN = "guardian", _("Tuteur ou tutrice légale")
        OTHER = "other", _("Autre représentant légal")

    beneficiary = models.OneToOneField(
        Beneficiary,
        on_delete=models.CASCADE,
        related_name="legal_representative_authorization",
        verbose_name=_("bénéficiaire"),
    )
    token = models.CharField(max_length=64, unique=True, default=_new_token, editable=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("statut")
    )
    legal_representative_name = models.CharField(
        max_length=150, verbose_name=_("nom de la personne responsable légale")
    )
    legal_representative_email = models.EmailField(
        verbose_name=_("email de la personne responsable légale")
    )
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, blank=True, verbose_name=_("qualité")
    )
    newsletter_consent = models.BooleanField(
        default=False, verbose_name=_("souhaite recevoir les actus")
    )
    signed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("signée le"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("adresse IP"))
    document = models.TextField(blank=True, verbose_name=_("document signé"))
    proof_pdf_hash = models.CharField(
        max_length=64, blank=True, verbose_name=_("empreinte SHA-256 du PDF")
    )
    proof_pdf = models.FileField(
        max_length=255,
        blank=True,
        upload_to="legal_representative_authorizations/",
        verbose_name=_("preuve PDF"),
    )

    objects = LegalRepresentativeAuthorizationQuerySet.as_manager()

    class Meta:
        verbose_name = _("autorisation de la personne responsable légale")
        verbose_name_plural = _("autorisations des personnes responsables légales")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.beneficiary.full_name} – {self.legal_representative_name}"

    @property
    def url(self):
        return settings.SITE_URL + reverse(
            "edit_legal_representative_authorization", args=[self.token]
        )
