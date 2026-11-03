import base64

import paramiko
from django.conf import settings

HOST = "sftp.apec.fr"
PORT = 22
HOST_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIBzNwV4Q9rT2R8dQ/wmSTOZ76FJpAfFpncRYgWHm/+WN"
# Overwritten every morning but Sundays and Mondays, with every offer of the day.
EXPORT_PATH = "Export_offres_TECHPOURTOUTES.xml"
TIMEOUT = 60


class ApecSftpClient:
    """Apec hands its offers over as a single file on its SFTP server, not through an API."""

    def download_export(self, file) -> None:
        with paramiko.SSHClient() as ssh:
            ssh.get_host_keys().add(
                HOST, "ssh-ed25519", paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY))
            )
            ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
            ssh.connect(
                HOST,
                port=PORT,
                username=settings.APEC_SFTP_LOGIN,
                password=settings.APEC_SFTP_PASSWORD,
                timeout=TIMEOUT,
                allow_agent=False,
                look_for_keys=False,
            )
            with ssh.open_sftp() as sftp:
                sftp.get_channel().settimeout(TIMEOUT)
                sftp.getfo(EXPORT_PATH, file)
