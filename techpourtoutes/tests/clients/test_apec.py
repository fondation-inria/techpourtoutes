from io import BytesIO
from unittest.mock import patch

import paramiko
import pytest
from django.test import override_settings

from techpourtoutes.clients.apec import ApecSftpClient


@pytest.fixture
def ssh():
    with patch("techpourtoutes.clients.apec.paramiko.SSHClient") as ssh_client:
        yield ssh_client.return_value.__enter__.return_value


@override_settings(APEC_SFTP_LOGIN="techpourtoutes", APEC_SFTP_PASSWORD="secret")
def test_the_client_signs_in_with_our_credentials(ssh):
    ApecSftpClient().download_export(BytesIO())

    host, kwargs = ssh.connect.call_args
    assert host == ("sftp.apec.fr",)
    assert kwargs["port"] == 22
    assert kwargs["username"] == "techpourtoutes"
    assert kwargs["password"] == "secret"


def test_the_client_only_trusts_the_host_key_of_apec(ssh):
    ApecSftpClient().download_export(BytesIO())

    hostname, key_type, key = ssh.get_host_keys.return_value.add.call_args.args
    assert (hostname, key_type) == ("sftp.apec.fr", "ssh-ed25519")
    assert key.fingerprint == "SHA256:DHEYbYKhBX4uyI4XL3iODnfAVcDyODSh1W9YiNSLozg"
    (policy,) = ssh.set_missing_host_key_policy.call_args.args
    assert isinstance(policy, paramiko.RejectPolicy)


def test_the_client_downloads_the_export(ssh):
    export = BytesIO()

    ApecSftpClient().download_export(export)

    sftp = ssh.open_sftp.return_value.__enter__.return_value
    sftp.getfo.assert_called_once_with("Export_offres_TECHPOURTOUTES.xml", export)
