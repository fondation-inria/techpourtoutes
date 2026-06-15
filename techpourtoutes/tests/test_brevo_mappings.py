from datetime import date

import pytest
from django.test import override_settings
from phonenumber_field.phonenumber import PhoneNumber

from techpourtoutes.services.brevo_api.mappings import (
    _serialize,
    brevo_attributes_for,
    brevo_list_id_for,
)


@pytest.mark.django_db
def test_brevo_attributes_for_pro_returns_mapped_attributes(pro):
    assert brevo_attributes_for(pro) == {
        "EMAIL": "alice@example.com",
        "PRENOM": "Alice",
        "NOM": "Martin",
        "SMS": "+33612345678",
        "TELEPHONE_RAW_NUMBER": "0033612345678",
        "CIVILITE": ["Madame"],
        "JOB_TITLE": "Chercheuse",
        "SITUATION_PRO": ["En emploi"],
        "NOM_DE_LA_STRUCTURE": "Inria",
        "CODE_POSTAL": "75001",
        "ENGAGEMENTS": [],
        "TYPES_DE_CONTACT": ["Coalition TPT"],
    }


@pytest.mark.django_db
def test_brevo_attributes_for_bare_user_returns_none(db):
    from techpourtoutes.models import User

    user = User.objects.create_user(username="bare@example.com", email="bare@example.com")

    assert brevo_attributes_for(user) is None


@pytest.mark.django_db
@override_settings(BREVO_PRO_LIST_ID=42)
def test_brevo_list_id_for_pro_returns_pro_list_id(pro):
    assert brevo_list_id_for(pro) == 42


@pytest.mark.django_db
def test_brevo_list_id_for_bare_user_returns_none(db):
    from techpourtoutes.models import User

    user = User.objects.create_user(username="bare@example.com", email="bare@example.com")

    assert brevo_list_id_for(user) is None


@pytest.mark.django_db
def test_brevo_attributes_engagements_are_translated_to_labels(pro):
    from techpourtoutes.models import Pro

    pro.engagements = [Pro.Engagement.MENTOR, Pro.Engagement.WORKSHOPS]
    pro.save()

    assert brevo_attributes_for(pro)["ENGAGEMENTS"] == ["mentorer", "organiser un atelier"]


def test_serialize_phone_returns_e164():
    phone = PhoneNumber.from_string("0612345678", region="FR")

    assert _serialize(phone) == "+33612345678"


def test_serialize_date_returns_iso():
    assert _serialize(date(2026, 5, 26)) == "2026-05-26"


def test_serialize_none_returns_none():
    assert _serialize(None) is None


def test_serialize_passthrough_for_str_int_bool():
    assert _serialize("hello") == "hello"
    assert _serialize(42) == 42
    assert _serialize(True) is True
