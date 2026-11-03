import tempfile
from datetime import timedelta
from xml.etree.ElementTree import ParseError

import paramiko
from defusedxml import DefusedXmlException
from django.utils import timezone

from techpourtoutes.clients.apec import ApecSftpClient
from techpourtoutes.services.base_api import BaseApiService
from techpourtoutes.utils.apec import read_apec_xml

AUTHENTICATION_ERROR_MESSAGE = "Le serveur SFTP de l'Apec a refusé nos identifiants."
HOST_KEY_ERROR_MESSAGE = (
    "Le serveur SFTP de l'Apec ne présente plus la clé attendue : connexion refusée."
)
MISSING_EXPORT_MESSAGE = "L'export des offres est introuvable sur le serveur SFTP de l'Apec."
NETWORK_ERROR_MESSAGE = "Impossible de joindre le serveur SFTP de l'Apec."
PAYLOAD_ERROR_MESSAGE = "L'export Apec n'est pas un XML exploitable."
STALE_EXPORT_MESSAGE = "L'export Apec n'a pas été mis à jour depuis le {date}."

# Apec writes no export on Sundays and Mondays: past that, it has stopped writing it.
MAX_EXPORT_AGE = timedelta(days=3)


class FetchApecJobPostings(BaseApiService):
    """Download the export and read its offers, failing once Apec has stopped writing it.

    It is downloaded every morning, written or not that day: the upsert only touches what
    changed. The file weighs some 60 MB: it is streamed to disk rather than held in memory.
    """

    def perform(self) -> None:
        with tempfile.TemporaryFile() as export:
            self._download(export)
            export.seek(0)
            exported_on, self._records = self._read(export)
        if timezone.localdate() - exported_on > MAX_EXPORT_AGE:
            self.fail(STALE_EXPORT_MESSAGE.format(date=exported_on.strftime("%d/%m/%Y")))

    def _read(self, export):
        try:
            return read_apec_xml(export)
        except ParseError, DefusedXmlException:
            self.fail(PAYLOAD_ERROR_MESSAGE)

    def _download(self, export) -> None:
        try:
            ApecSftpClient().download_export(export)
        except paramiko.AuthenticationException:
            self.fail(AUTHENTICATION_ERROR_MESSAGE)
        except paramiko.BadHostKeyException:
            self.fail(HOST_KEY_ERROR_MESSAGE)
        except FileNotFoundError:
            self.fail(MISSING_EXPORT_MESSAGE)
        except paramiko.SSHException, OSError:
            self.network_error = True
            self.fail(NETWORK_ERROR_MESSAGE)

    @property
    def apec_records(self) -> list:
        return getattr(self, "_records", [])
