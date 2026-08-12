import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import PerfectibleMailer

locmem = override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")


@pytest.mark.django_db
@locmem
def test_missing_record_reports_both_free_text_names(beneficiary):
    PerfectibleMailer.missing_record(
        user=beneficiary,
        origin="Funnel d'inscription",
        level="Terminale",
        school_label="Lycée du bout du monde",
        formation_label="Bac pro maréchalerie",
        school=None,
        formation=None,
    )

    message = mail.outbox[0]
    assert message.to == ["perfectible@techpourtoutes.io"]
    assert "Lycée du bout du monde" in message.body
    assert "Bac pro maréchalerie" in message.body
    assert "Funnel d'inscription" in message.body
    assert beneficiary.email in message.body


@pytest.mark.django_db
@locmem
def test_missing_record_names_the_record_that_did_resolve(beneficiary, school):
    PerfectibleMailer.missing_record(
        user=beneficiary,
        origin="Compte bénéficiaire",
        level="Terminale",
        school_label=school.location_label,
        formation_label="Bac pro maréchalerie",
        school=school,
        formation=None,
    )

    body = mail.outbox[0].body
    assert school.name in body
    assert "Bac pro maréchalerie" in body


@pytest.mark.django_db
@locmem
def test_missing_record_attaches_its_brevo_tags(beneficiary):
    PerfectibleMailer.missing_record(
        user=beneficiary,
        origin="Atelier",
        level="",
        school_label="Lycée du bout du monde",
        formation_label="",
        school=None,
        formation=None,
    )

    assert mail.outbox[0].tags == ["interne", "perfectible", "donnée manquante"]
