"""Browser-driving helpers shared by the two beneficiary funnels.

Both funnels render the same field partials, so the steps they have in common are driven the
same way: pick a study status, pick a level, pick a school and its formation.
"""

from techpourtoutes.models import Formation, FormationAction, School

HIGH_SCHOOL_LABEL = "Dans quel établissement étudies-tu ?*"
HIGH_SCHOOL_FORMATION_LABEL = "Quelle est ta formation ?*"


def voltaire_teaching(formation_name):
    """A lycée and the one formation it delivers, as the imports would have linked them."""
    school = School(
        onisep_id="14008",
        uai="0750001A",
        name="Lycée Voltaire",
        postal_code="75011",
        secondary=True,
    )
    school.save()
    formation = Formation(onisep_id="7118", name=formation_name, secondary=True)
    formation.save()
    FormationAction(onisep_id="69395", formation=formation, school=school).save()
    return school, formation


def choose_study_status(page, label):
    page.get_by_text(label).click()
    page.get_by_role("button", name="Continuer").click()


def select_option(page, label, option):
    page.get_by_role("button", name=label).click()
    page.get_by_role("button", name=option, exact=True).click()


def search_field(page, label):
    """Both comboboxes post under `q`: only their label tells them apart."""
    return page.get_by_label(label)


def pick(page, label, query, option):
    search_field(page, label).fill(query)
    page.get_by_role("option", name=option, exact=True).click()
