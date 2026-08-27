import pytest
from django.core.exceptions import ValidationError

from techpourtoutes.models import School


@pytest.mark.django_db
def test_school_str_shows_name_and_postal_code():
    school = School(onisep_id="14008", name="Lycée Voltaire", postal_code="75011")
    school.save()

    assert str(school) == "Lycée Voltaire (75011)"


@pytest.mark.django_db
def test_school_onisep_id_is_unique():
    School(onisep_id="14008", name="Lycée Voltaire").save()

    with pytest.raises(ValidationError):
        School(onisep_id="14008", name="Autre lycée").save()


@pytest.mark.django_db
def test_school_shares_a_uai_with_another_school():
    """The Onisep referential holds 562 duplicated UAI: only `onisep_id` identifies a school."""
    School(onisep_id="14008", uai="0750001A", name="Lycée Voltaire").save()
    School(onisep_id="14009", uai="0750001A", name="Lycée Voltaire - section pro").save()

    assert School.objects.filter(uai="0750001A").count() == 2


@pytest.mark.django_db
def test_school_save_populates_normalized_fields():
    school = School(onisep_id="14008", name="Lycée Privée", acronym="ENSÉA")
    school.save()

    assert school.name_normalized == "Lycee Privee"
    assert school.acronym_normalized == "ENSEA"


@pytest.mark.django_db
def test_school_display_label_prefers_the_acronym():
    with_acronym = School(onisep_id="1", name="Université de Technologie de Troyes", acronym="UTT")
    without_acronym = School(onisep_id="2", name="Lycée Voltaire")

    assert with_acronym.display_label == "UTT (Université de Technologie de Troyes)"
    assert without_acronym.display_label == "Lycée Voltaire"


@pytest.mark.django_db
def test_school_display_label_shows_the_locality_for_a_homonym():
    school = School(
        onisep_id="1",
        name="ESSCA School of Management",
        acronym="ESSCA",
        postal_code="49000",
        city="Angers",
    )
    school.has_homonym = True

    assert school.display_label == "ESSCA (ESSCA School of Management) - 49000 Angers"


@pytest.mark.django_db
def test_school_display_label_of_a_homonym_without_a_locality_stays_bare():
    school = School(onisep_id="1", name="ESSCA School of Management")
    school.has_homonym = True

    assert school.display_label == "ESSCA School of Management"


@pytest.mark.django_db
def test_school_locality_joins_the_postal_code_and_the_city():
    assert School(onisep_id="1", postal_code="49000", city="Angers").locality == "49000 Angers"
    assert School(onisep_id="2", city="Angers").locality == "Angers"
    assert School(onisep_id="3").locality == ""


@pytest.mark.django_db
def test_school_location_label_falls_back_to_the_name_without_a_postal_code():
    assert School(onisep_id="1", name="Lycée Voltaire").location_label == "Lycée Voltaire"


@pytest.mark.django_db
def test_school_queryset_scopes():
    secondary = School(onisep_id="1", name="Lycée Voltaire", secondary=True)
    higher_ed = School(onisep_id="2", name="Université de Brest", higher_ed=True)
    both = School(onisep_id="3", name="Lycée Jean Zay", secondary=True, higher_ed=True)
    ambassador = School(
        onisep_id="4", name="Télécom Nancy", higher_ed=True, training_ambassador_eligible=True
    )
    for school in (secondary, higher_ed, both, ambassador):
        school.save()

    assert set(School.objects.secondary()) == {secondary, both}
    assert set(School.objects.higher_ed()) == {higher_ed, both, ambassador}
    assert set(School.objects.training_ambassador()) == {ambassador}


@pytest.mark.django_db
def test_school_find_answers_none_to_anything_but_a_known_id(school, higher_ed_school):
    """The id travels through a hidden field, so it can be absent, unknown or malformed."""
    assert School.objects.find(school.pk) == school
    assert School.objects.secondary().find(higher_ed_school.pk) is None
    assert School.objects.find("2b7f4f4a-0000-0000-0000-000000000000") is None
    assert School.objects.find("pas-un-uuid") is None
    assert School.objects.find("") is None


@pytest.mark.django_db
def test_school_search_ignores_accents_and_matches_every_token():
    voltaire = School(onisep_id="1", name="Lycée Voltaire", postal_code="75011")
    zay = School(onisep_id="2", name="Lycée Jean Zay", postal_code="75012")
    for school in (voltaire, zay):
        school.save()

    assert set(School.objects.search("lycee")) == {voltaire, zay}
    assert set(School.objects.search("lycee voltaire")) == {voltaire}
    assert set(School.objects.search("inconnu")) == set()


@pytest.mark.django_db
def test_school_search_matches_the_acronym():
    school = School(onisep_id="1", name="Université de Technologie de Troyes", acronym="UTT")
    school.save()

    assert set(School.objects.search("utt")) == {school}


@pytest.mark.django_db
def test_school_search_matches_the_postal_code_only_when_asked():
    school = School(onisep_id="1", name="Lycée Voltaire", postal_code="75011")
    school.save()

    assert set(School.objects.search("750", match_postal_code=True)) == {school}
    assert set(School.objects.search("750")) == set()
