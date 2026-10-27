import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_send_legal_representative_authorization_reminders_says_how_many_it_sent(capsys):
    call_command("send_legal_representative_authorization_reminders")

    out = capsys.readouterr().out
    assert "0 relance(s) envoyée(s) aux personnes responsables légales" in out
    assert "0 relance(s) envoyée(s) aux bénéficiaires" in out
