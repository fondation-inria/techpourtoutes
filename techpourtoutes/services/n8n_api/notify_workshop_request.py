from django.utils import timezone

from .base_service import N8nApiBaseService


class NotifyWorkshopRequest(N8nApiBaseService):
    def perform(self, *, pro, ateliers, remark):
        self.request(
            method="notify_workshop_request",
            payload={
                "type_atelier": ateliers,
                "civilite": pro.civility,
                "prenom": pro.first_name,
                "nom": pro.last_name,
                "email": pro.email,
                "etablissement": pro.structure_name,
                "code_postal": pro.postal_code,
                "identifiant_etablissement": pro.structure_id,
                "fonction": pro.job_title,
                "remarque": remark,
                "timestamp": timezone.now().isoformat(),
            },
        )
