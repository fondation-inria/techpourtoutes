import hashlib

import pytest

from techpourtoutes.services.legal_representative_authorization.build_proof import (
    BuildLegalRepresentativeAuthorizationProof,
)


@pytest.mark.django_db
def test_build_proof_stores_the_pdf_in_the_private_bucket(signed_authorization, s3_storages):
    BuildLegalRepresentativeAuthorizationProof(authorization=signed_authorization)

    signed_authorization.refresh_from_db()
    keys = [
        item["Key"] for item in s3_storages.list_objects_v2(Bucket="tpt-test-private")["Contents"]
    ]
    assert keys == [signed_authorization.proof_pdf.name]
    assert signed_authorization.proof_pdf.name.endswith(".pdf")
    assert signed_authorization.proof_pdf.read().startswith(b"%PDF")


@pytest.mark.django_db
def test_build_proof_keeps_the_hash_of_the_pdf_so_an_altered_copy_shows(signed_authorization):
    BuildLegalRepresentativeAuthorizationProof(authorization=signed_authorization)

    signed_authorization.refresh_from_db()
    assert signed_authorization.proof_pdf_hash == (
        hashlib.sha256(signed_authorization.proof_pdf.read()).hexdigest()
    )
