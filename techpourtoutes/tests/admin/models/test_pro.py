import pytest
from django import forms
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_pro_changelist"


@pytest.mark.django_db
def test_admin_pro_hides_jobirl_token_and_locks_id(verified_admin_client, admin_pro):
    admin_pro.jobirl_user_id = 8675309
    admin_pro.jobirl_user_token = "jobirl-token-do-not-show"
    admin_pro.save()
    url = reverse("admin:techpourtoutes_pro_change", args=[admin_pro.pk])
    content = verified_admin_client.get(url).content.decode()
    # The Jobirl token is a credential — never exposed.
    assert 'name="jobirl_user_token"' not in content
    assert "jobirl-token-do-not-show" not in content
    # The Jobirl id is set by the API, not by hand — shown read-only (visible, not editable).
    assert 'name="jobirl_user_id"' not in content
    assert "8675309" in content


@pytest.mark.django_db
def test_admin_pro_lists_training_experiences(verified_admin_client, admin_pro, experience):
    url = reverse("admin:techpourtoutes_pro_change", args=[admin_pro.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Master Informatique" in content
    assert "Université Paris-Saclay" in content


@pytest.mark.django_db
def test_admin_pro_grants_admin_access_through_the_role_alone(
    verified_admin_client, pro, event_moderator_group
):
    """Handing out the role is the whole gesture: `is_staff` follows from it, so the page
    never offers it — see `_on_user_groups_changed`."""
    url = reverse("admin:techpourtoutes_pro_change", args=[pro.pk])
    form = verified_admin_client.get(url).context["adminform"].form

    assert "is_staff" not in form.fields
    assert list(form.fields["groups"].queryset) == [event_moderator_group]


@pytest.mark.django_db
def test_admin_pro_offers_the_groups_as_checkboxes_only(verified_admin_client, pro):
    """A role is ticked, not typed: a checked box reads as selected where a highlighted line
    did not, and the group list is this project's to define, not this page's to extend."""
    url = reverse("admin:techpourtoutes_pro_change", args=[pro.pk])
    response = verified_admin_client.get(url)

    widget = response.context["adminform"].form.fields["groups"].widget
    assert isinstance(widget.widget, forms.CheckboxSelectMultiple)
    assert not widget.can_add_related
    assert not widget.can_change_related
    assert not widget.can_delete_related
    assert 'id="add_id_groups"' not in response.content.decode()


@pytest.mark.django_db
def test_admin_pro_appoints_a_chargee_de_mission(
    verified_admin_client, valid_pro_model_data, event_moderator_group
):
    """The round trip, not just the widget: ticking the role alone brings the pro back staff,
    in the group, and holding exactly what the group carries."""
    from techpourtoutes.models import Pro

    chargee = Pro(
        username="chargee@example.com", **{**valid_pro_model_data, "email": "chargee@example.com"}
    )
    chargee.save()
    url = reverse("admin:techpourtoutes_pro_change", args=[chargee.pk])
    form = verified_admin_client.get(url).context["adminform"].form

    response = verified_admin_client.post(
        url,
        {
            **{name: form[name].value() or "" for name in form.fields},
            "groups": str(event_moderator_group.pk),
            "training_experiences-TOTAL_FORMS": "0",
            "training_experiences-INITIAL_FORMS": "0",
            "workshop_requests-TOTAL_FORMS": "0",
            "workshop_requests-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == 302
    chargee.refresh_from_db()
    assert chargee.is_staff
    assert list(chargee.groups.all()) == [event_moderator_group]
    assert chargee.has_perm("techpourtoutes.change_event")
    assert not chargee.has_perm("techpourtoutes.delete_event")


@pytest.mark.django_db
def test_pro_changelist_stats_keep_their_delta(verified_admin_client, pros):
    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()
    assert "sur 30 derniers jours" in content


@pytest.mark.django_db
def test_changelist_date_filter_renders(verified_admin_client, pros):
    response = verified_admin_client.get(
        reverse(CHANGELIST), {"created_at__gte": "2000-01-01 00:00:00+00:00"}
    )
    assert response.status_code == 200
