from techpourtoutes.models import LegalRepresentativeAuthorization

from ..read_only import ReadOnlyTabularInline


class LegalRepresentativeAuthorizationInline(ReadOnlyTabularInline):
    """On a beneficiary: the request sent to her legal representative, and its proof once
    signed."""

    model = LegalRepresentativeAuthorization
    fields = (
        "legal_representative_name",
        "legal_representative_email",
        "status",
        "created_at",
        "signed_at",
        "relationship",
        "proof_pdf",
    )
    readonly_fields = fields
