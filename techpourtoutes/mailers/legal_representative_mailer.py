from .base_mailer import BaseMailer


class LegalRepresentativeMailer(BaseMailer):
    from_email = "TechPourToutes <bonjour@techpourtoutes.io>"

    @classmethod
    def authorization_requested(cls, *, authorization):
        beneficiary = authorization.beneficiary
        cls.send_mail(
            subject=(
                f"{beneficiary.first_name} {beneficiary.last_name} souhaite obtenir votre "
                "autorisation pour rejoindre le programme TechPourToutes"
            ),
            recipient_list=[authorization.legal_representative_email],
            context={"beneficiary": beneficiary, "authorization_url": authorization.url},
            tags=["utilisateur", "responsable légal", "demande d'autorisation"],
        )

    @classmethod
    def authorization_signed(cls, *, authorization):
        beneficiary = authorization.beneficiary
        with authorization.proof_pdf.open("rb") as proof_pdf:
            attachment = ("autorisation-techpourtoutes.pdf", proof_pdf.read(), "application/pdf")
        cls.send_mail(
            subject=(
                f"Votre autorisation signée pour {beneficiary.first_name} {beneficiary.last_name}"
            ),
            recipient_list=[authorization.legal_representative_email],
            context={"beneficiary": beneficiary},
            tags=["utilisateur", "responsable légal", "autorisation signée"],
            attachments=[attachment],
        )
