from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from storages.backends.s3 import S3Storage


class Command(BaseCommand):
    help = (
        "Supprimer de l'object storage tous les fichiers de la review app, avant de la détruire. "
        "Refuse de tourner ailleurs que sur une review app."
    )

    def handle(self, *args, **options):
        for alias in ("default", "public"):
            storage = storages[alias]
            if not isinstance(storage, S3Storage) or not storage.location:
                raise CommandError("  Réservé à une review app : ses fichiers ont leur préfixe.")
            batches = storage.bucket.objects.filter(Prefix=f"{storage.location}/").delete()
            deleted = sum(len(batch.get("Deleted", [])) for batch in batches)
            self.stdout.write(f"  {alias} : {deleted} fichier(s) supprimé(s).")
