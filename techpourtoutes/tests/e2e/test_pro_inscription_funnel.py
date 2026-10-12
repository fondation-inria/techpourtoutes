import re

import pytest
from django.core import mail
from playwright.sync_api import expect
from waffle.models import Switch

from techpourtoutes.models import Pro

from .helpers import select_option

# These tests drive a real browser to cover what the view tests cannot: the Alpine state of the
# fields — the message shown with Autre, the structure name hidden without a structure — and a
# complete sign-up through HTMX.


@pytest.fixture
def new_funnel_url(live_server, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    Switch.objects.update_or_create(name="new_pro_features", defaults={"active": True})
    return f"{live_server.url}/coalition/inscription/new/"


def _current_step(page):
    return page.locator('input[name="action"]:not([value="back"])')


def _complete_email_and_identity(page):
    page.fill('input[name="email"]', "hedy@example.com")
    page.get_by_role("button", name="Continuer").click()
    expect(_current_step(page)).to_have_value("identity")
    select_option(page, "Civilité*", "Madame")
    page.fill('input[name="first_name"]', "Hedy")
    page.fill('input[name="last_name"]', "Lamarr")
    page.locator('input[name="manifeste_accepted"]').check(force=True)
    page.locator('input[name="terms_accepted"]').check(force=True)
    page.get_by_role("button", name="Continuer").click()
    expect(_current_step(page)).to_have_value("engagements")


def test_retired_sponsor_joins_with_a_message_for_the_team(page, new_funnel_url):
    page.goto(f"{new_funnel_url}?engagement=sponsor")
    _complete_email_and_identity(page)

    expect(page.locator('input[value="sponsor"]')).to_be_checked()
    message = page.locator('textarea[name="message"]')
    expect(message).to_be_hidden()
    page.get_by_text("Autre", exact=True).click()
    message.fill("Je peux aussi relire des CV.")
    page.get_by_role("button", name="Continuer").click()
    expect(_current_step(page)).to_have_value("last_information")

    structure_name = page.locator('input[name="structure_name"]')
    expect(structure_name).to_be_hidden()
    select_option(page, "Dans quel type de structure travaillez-vous ?*", "Entreprise")
    expect(structure_name).to_be_visible()
    select_option(page, "Dans quel type de structure travaillez-vous ?*", "Je suis à la retraite")
    expect(structure_name).to_be_hidden()
    page.fill('input[name="job_title"]', "Ingénieure")
    page.fill('input[name="phone"]', "0612345678")
    page.fill('input[name="postal_code"]', "75011")
    page.get_by_role("button", name="Rejoindre la coalition").click()

    expect(page.get_by_text("Saisissez le code reçu par mail")).to_be_visible()
    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.engagements == ["sponsor"]
    assert pro.professional_situation == "retired"
    assert any("Je peux aussi relire des CV." in m.body for m in mail.outbox)

    welcome = next(m for m in mail.outbox if m.to == ["hedy@example.com"])
    page.fill('input[name="code"]', re.search(r"\b(\d{6})\b", welcome.body).group(1))
    page.get_by_role("button", name="Continuer").click()

    expect(page.get_by_text("Bienvenue dans la coalition !")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/mon-compte/$"))


def test_a_training_ambassador_learns_why_her_school_may_be_missing(page, new_funnel_url):
    page.goto(f"{new_funnel_url}?engagement=training_ambassador")
    _complete_email_and_identity(page)
    page.get_by_role("button", name="Continuer").click()
    expect(_current_step(page)).to_have_value("training_ambassador")

    notice = page.get_by_text("n'est disponible que dans une liste d'établissements partenaires")
    expect(notice).to_be_hidden()
    page.get_by_role("button", name="Je ne trouve pas mon établissement").click()
    expect(notice).to_be_visible()
    expect(page.get_by_role("button", name="Je ne trouve pas ma formation")).to_be_visible()
