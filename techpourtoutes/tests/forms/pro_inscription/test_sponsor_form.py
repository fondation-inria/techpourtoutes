from techpourtoutes.forms import ProSponsorForm
from techpourtoutes.models import Pro


def test_sponsor_form_asks_what_her_profile_lacks_and_a_message(pro):
    pro.structure_type = Pro.StructureType.COMPANY
    pro.phone = ""
    assert set(ProSponsorForm(pro=pro).fields) == {"phone", "message"}


def test_sponsor_form_requires_what_her_profile_lacks(pro):
    pro.structure_name = ""
    form = ProSponsorForm(data={"structure_type": "company"}, pro=pro)
    assert not form.is_valid()
    assert "structure_name" in form.errors


def test_sponsor_form_requires_a_message(pro):
    form = ProSponsorForm(data={"structure_type": "company"}, pro=pro)
    assert not form.is_valid()
    assert "message" in form.errors
