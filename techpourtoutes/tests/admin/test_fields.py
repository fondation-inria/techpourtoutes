import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.admin.fields import SubcategoryField
from techpourtoutes.models import Event


def test_decompress_selects_a_listed_subcategory():
    assert SubcategoryField().widget.decompress(Event.Subcategory.HACKATHON) == [
        Event.Subcategory.HACKATHON,
        "",
    ]


def test_decompress_routes_free_text_through_other():
    assert SubcategoryField().widget.decompress("Rencontre d'anciennes") == [
        Event.Subcategory.OTHER,
        "Rencontre d'anciennes",
    ]


def test_decompress_handles_a_blank_value():
    assert SubcategoryField().widget.decompress("") == [None, None]


def test_compress_keeps_a_listed_subcategorys_key():
    assert SubcategoryField().compress([Event.Subcategory.HACKATHON, ""]) == "hackathon"


def test_compress_ignores_a_stale_free_text_left_in_the_box():
    """Whatever free text is left in the box is ignored unless "Autre" is selected."""
    result = SubcategoryField().compress([Event.Subcategory.HACKATHON, "texte périmé"])
    assert result == "hackathon"


def test_compress_returns_the_free_text_for_other():
    result = SubcategoryField().compress([Event.Subcategory.OTHER, "Rencontre d'anciennes"])
    assert result == "Rencontre d'anciennes"


def test_compress_demands_the_free_text_for_other():
    with pytest.raises(ValidationError) as excinfo:
        SubcategoryField().compress([Event.Subcategory.OTHER, ""])

    assert "Précisez le type d'événement." in excinfo.value.messages


def test_compress_of_nothing_is_blank():
    assert SubcategoryField().compress([]) == ""
