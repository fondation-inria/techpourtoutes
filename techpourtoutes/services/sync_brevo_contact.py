from techpourtoutes.services.base import BaseService
from techpourtoutes.services.brevo_api.mappings import brevo_attributes_for, brevo_list_id_for
from techpourtoutes.services.brevo_api.upsert_contact import UpsertBrevoContact


class SyncBrevoContact(BaseService):
    def perform(self, *, instance) -> None:
        list_id = brevo_list_id_for(instance)
        attributes = brevo_attributes_for(instance)
        if list_id is None or attributes is None:
            return
        result = self._sync_contact(str(instance.pk), list_id, attributes)
        if result.failure:
            self.status_code = getattr(result, "status_code", None)
            self.fail(result.errors[0])

    def _sync_contact(self, ext_id, list_id, attributes):
        result = UpsertBrevoContact(ext_id=ext_id, list_id=list_id, attributes=attributes)
        if self._is_sms_conflict(result):
            return UpsertBrevoContact(
                ext_id=ext_id,
                list_id=list_id,
                attributes={k: v for k, v in attributes.items() if k != "SMS"},
            )
        return result

    @staticmethod
    def _is_sms_conflict(result) -> bool:
        if not result.errors:
            return False
        return "SMS" in result.errors[0] and "already associated" in result.errors[0]
