from datetime import timedelta

from django.db import migrations
from django.utils import timezone

# Beyond the three weeks of reminders, a request is dropped: should she still want a mentor, the
# beneficiary signs up for mentoring anew rather than correcting a form long filled in.
STALE_AFTER = timedelta(weeks=3)


# A beneficiary already on Jobirl had her attestation handled by hand, off the platform.
def move_legal_representative_to_authorization(apps, schema_editor):
    Beneficiary = apps.get_model("techpourtoutes", "Beneficiary")
    LegalRepresentativeAuthorization = apps.get_model(
        "techpourtoutes", "LegalRepresentativeAuthorization"
    )
    recent = timezone.now() - STALE_AFTER
    for beneficiary in Beneficiary.objects.exclude(legal_representative_email=""):
        signed = beneficiary.jobirl_user_id is not None
        if not signed and beneficiary.created_at < recent:
            continue
        LegalRepresentativeAuthorization.objects.create(
            beneficiary=beneficiary,
            legal_representative_name=beneficiary.legal_representative_name,
            legal_representative_email=beneficiary.legal_representative_email,
            status="signed" if signed else "pending",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("techpourtoutes", "0065_legal_representative_authorization"),
    ]

    operations = [
        migrations.RunPython(move_legal_representative_to_authorization, migrations.RunPython.noop),
        migrations.RemoveField(model_name="beneficiary", name="legal_representative_email"),
        migrations.RemoveField(model_name="beneficiary", name="legal_representative_name"),
    ]
