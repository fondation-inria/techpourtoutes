from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("techpourtoutes", "0006_user_brevo_sync_enabled")]

    operations = [migrations.RenameModel("Mentor", "Pro")]
