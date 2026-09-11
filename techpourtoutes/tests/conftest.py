from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture
def mock_geocoding(httpx_mock):
    """The address search asks one Géoplateforme index at a time, so each needs its own
    payload — matched on the `index` parameter rather than on call order."""

    def register(*, addresses=(), pois=()):
        def respond(request):
            wanted = pois if request.url.params["index"] == "poi" else addresses
            return httpx.Response(200, json={"features": list(wanted)})

        httpx_mock.add_callback(respond, is_reusable=True)

    return register


@pytest.fixture
def pro(db):
    from techpourtoutes.models import Pro

    pro = Pro(
        username="alice@example.com",
        civility=Pro.Civility.MADAME,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        phone="+33612345678",
        postal_code="75001",
        professional_situation=Pro.ProfessionalSituation.WORKING,
        job_title="Chercheuse",
        structure_name="Inria",
        brevo_sync_enabled=True,
    )
    pro.save()
    return pro


@pytest.fixture
def higher_ed_school(db):
    from techpourtoutes.models import School

    school = School(
        onisep_id="490",
        name="Université Paris-Saclay",
        acronym="UPSaclay",
        siret="13002602400054",
        uai="0911101X",
        higher_ed=True,
        training_ambassador_eligible=True,
    )
    school.save()
    return school


@pytest.fixture
def school(db):
    from techpourtoutes.models import School

    school = School(
        onisep_id="14008",
        uai="0750001A",
        name="Lycée Voltaire",
        postal_code="75011",
        secondary=True,
    )
    school.save()
    return school


@pytest.fixture
def beneficiary(db):
    from datetime import date

    from techpourtoutes.models import Beneficiary

    beneficiary = Beneficiary(
        username="jade@example.com",
        first_name="Jade",
        last_name="Petit",
        email="jade@example.com",
        phone="+33612345678",
        birth_date=date(2008, 3, 15),
    )
    beneficiary.save()
    return beneficiary


@pytest.fixture
def formation(school):
    from techpourtoutes.models import Formation, FormationAction

    formation = Formation(onisep_id="7118", name="Spécialité mathématiques", secondary=True)
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=school).save()
    return formation


@pytest.fixture
def higher_ed_formation(higher_ed_school):
    from techpourtoutes.models import Formation, FormationAction

    formation = Formation(onisep_id="9701", name="Master Informatique", higher_ed=True)
    formation.save()
    FormationAction(onisep_id="69396", formation=formation, school=higher_ed_school).save()
    return formation


@pytest.fixture
def experience(pro, higher_ed_school, higher_ed_formation):
    from datetime import date

    from techpourtoutes.models import Level, TrainingExperience

    return TrainingExperience.objects.create(
        user=pro,
        school=higher_ed_school,
        formation=higher_ed_formation,
        level=Level.BAC_3,
        start_date=date(2019, 9, 1),
        end_date=date(2020, 8, 31),
    )


@pytest.fixture
def beneficiary_experience(beneficiary, school, formation):
    from datetime import date

    from techpourtoutes.models import Level, TrainingExperience

    return TrainingExperience.objects.create(
        user=beneficiary,
        school=school,
        formation=formation,
        level=Level.TERMINALE,
        start_date=date(2023, 9, 1),
        end_date=date(2024, 8, 31),
    )


@pytest.fixture
def event(pro):
    """A geocoded, upcoming event — the nominal case the autocomplete produces."""
    from datetime import time, timedelta
    from decimal import Decimal

    from django.utils import timezone

    from techpourtoutes.models import Event

    start = timezone.localdate() + timedelta(days=30)
    event = Event(
        created_by=pro,
        title="Salon des métiers du numérique",
        organizer="Numeum",
        subcategory=Event.Subcategory.SALON,
        start_date=start,
        end_date=start + timedelta(days=1),
        start_time=time(9, 0),
        end_time=time(18, 0),
        location_type=Event.LocationType.PHYSICAL,
        address="8 Boulevard du Port",
        postal_code="80000",
        city="Amiens",
        cog_code="80021",
        longitude=2.29009,
        latitude=49.897443,
        ban_id="80021_6590_00008",
        access_type=Event.AccessType.OPEN,
        price=Decimal("0"),
    )
    event.save()
    return event


ONISEP = "https://www.onisep.fr/http/redirection"


@pytest.fixture
def school_record():
    """One row of an Onisep "structures d'enseignement" file, with its real keys."""

    def build(onisep_id="14008", **overrides):
        return {
            "code_uai": "0383399N",
            "n_siret": "19381912500231",
            "type_detablissement": "école d'ingénieurs",
            "nom": "École nationale supérieure d'informatique",
            "sigle": "Ensimag",
            "statut": "public",
            "universite_de_rattachement_libelle_et_uai": "",
            "universite_de_rattachement_id_et_url_onisep": "",
            "boite_postale": "BP 72",
            "adresse": "681 rue de la Passerelle",
            "cp": "38402",
            "commune": "Saint-Martin-d'Hères",
            "commune_cog": "38421",
            "cedex": "Cedex",
            "telephone": "04 76 82 72 00",
            "arrondissement": "",
            "departement": "38 - Isère",
            "academie": "Grenoble",
            "region": "Auvergne-Rhône-Alpes",
            "region_cog": "84",
            "longitude_x": 5.76804,
            "latitude_y": 45.1935,
            "url_et_id_onisep": f"{ONISEP}/etablissement/slug/ENS.{onisep_id}",
            **overrides,
        }

    return build


@pytest.fixture
def formation_record():
    """One row of the Onisep "formations initiales" file, with its real keys."""

    def build(onisep_id="9701", **overrides):
        return {
            "code_nsf": "314",
            "code_scolarite": "46E31401",
            "sigle_type_formation": "",
            "libelle_type_formation": "formation d'école spécialisée",
            "libelle_formation_principal": "assistant de comptabilité",
            "sigle_formation": "",
            "duree": "1 an",
            "niveau_de_sortie_indicatif": "bac ou équivalent",
            "code_rncp": "38506",
            "niveau_de_certification": "4",
            "libelle_niveau_de_certification": "niveau 4",
            "url_et_id_onisep": f"{ONISEP}/formation/slug/FOR.{onisep_id}",
            **overrides,
        }

    return build


@pytest.fixture
def formation_action_record():
    """One row of an Onisep "actions de formation" file, with its real keys."""

    def build(onisep_id="69395", formation_id="9701", school_id="14008", **overrides):
        return {
            "action_de_formation_af_identifiant_onisep": f"AF.{onisep_id}",
            "formation_for_libelle": "classe de 1re générale",
            "for_url_et_id_onisep": f"{ONISEP}/formation/slug/FOR.{formation_id}",
            "lieu_denseignement_ens_libelle": "Lycée privé polyvalent Saint-Joseph",
            "ens_url_et_id_onisep": f"{ONISEP}/etablissement/slug/ENS.{school_id}",
            "ens_code_uai": "0341523W",
            **overrides,
        }

    return build


@pytest.fixture
def carif_oref_record():
    """One record of the Carif-Oref apprenticeship catalogue, as the projection returns it."""

    def build(onisep_id="5978", **overrides):
        return {
            "onisep_url": f"{ONISEP}/formation/slug/FOR.{onisep_id}",
            "niveau": "5 (BTS, DEUST...)",
            "duree": "2",
            "intitule_rco": "BTS conception des processus de réalisation de produits",
            "rncp_details": {
                "nsf_code": "254",
                "type_certif": "Brevet de technicien supérieur",
                "code_type_certif": "BTS",
            },
            "etablissement_formateur_siret": "38855948600070",
            "etablissement_formateur_uai": "0681832X",
            "etablissement_gestionnaire_siret": "38855948600070",
            "etablissement_gestionnaire_uai": "0681832X",
            **overrides,
        }

    return build


@pytest.fixture
def mock_create_mentor():
    instance = MagicMock(success=True, failure=False, errors=[])
    with patch(
        "techpourtoutes.views.coalition_views.CreateMentor",
        return_value=instance,
    ) as mock:
        yield mock


@pytest.fixture
def valid_pro_model_data():
    return {
        "civility": "Madame",
        "first_name": "Marie",
        "last_name": "Dupont",
        "email": "marie.dupont@example.com",
        "phone": "0612345678",
        "postal_code": "75011",
        "professional_situation": "working",
        "job_title": "Développeuse backend",
        "structure_name": "Grande entreprise",
    }


@pytest.fixture
def valid_pro_data(valid_pro_model_data):
    return {**valid_pro_model_data, "terms_accepted": True, "manifeste_accepted": True}


@pytest.fixture
def inactive_user(db):
    from techpourtoutes.models import User

    user = User.objects.create_user(
        username="inactive@example.com",
        email="inactive@example.com",
        first_name="Inactive",
        last_name="User",
        is_active=False,
    )
    return user
