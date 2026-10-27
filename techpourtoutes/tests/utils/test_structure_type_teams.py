import pytest
from django.test import override_settings

from techpourtoutes.models import Pro
from techpourtoutes.utils.structure_type_teams import recipients_for, structure_types_followed_by

teams = override_settings(
    COALITION_ASSOCIATION_RECIPIENTS=["association@example.com"],
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
    COALITION_SCHOOL_RECIPIENTS=["school@example.com", "both@example.com"],
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
    COALITION_PUBLIC_INSTITUTION_RECIPIENTS=["public@example.com", "both@example.com"],
)


@teams
@pytest.mark.parametrize(
    "structure_type,recipients",
    [
        (Pro.StructureType.ASSOCIATION, ["association@example.com"]),
        (Pro.StructureType.HIGHER_ED, ["training@example.com"]),
        (Pro.StructureType.SCHOOL, ["school@example.com", "both@example.com"]),
        (Pro.StructureType.COMPANY, ["ambassador@example.com"]),
        (Pro.StructureType.PUBLIC_INSTITUTION, ["public@example.com", "both@example.com"]),
        (Pro.StructureType.RETIRED, ["ambassador@example.com"]),
        (Pro.StructureType.JOBLESS, ["ambassador@example.com"]),
        ("", ["agir@techpourtoutes.io"]),
    ],
)
def test_recipients_for_names_the_team_following_the_structure_type(structure_type, recipients):
    assert recipients_for(structure_type) == recipients


@teams
def test_structure_types_followed_by_lists_every_team_she_belongs_to():
    assert structure_types_followed_by("both@example.com") == [
        Pro.StructureType.SCHOOL,
        Pro.StructureType.PUBLIC_INSTITUTION,
    ]


@teams
def test_structure_types_followed_by_gives_the_types_of_a_shared_team():
    """Retired and jobless pros are followed by the company team."""
    assert structure_types_followed_by("ambassador@example.com") == [
        Pro.StructureType.COMPANY,
        Pro.StructureType.RETIRED,
        Pro.StructureType.JOBLESS,
    ]


@teams
def test_structure_types_followed_by_ignores_the_case_of_the_address():
    assert structure_types_followed_by("School@Example.com") == [Pro.StructureType.SCHOOL]


@teams
def test_structure_types_followed_by_gives_nothing_to_who_is_in_no_team():
    assert structure_types_followed_by("nobody@example.com") == []
