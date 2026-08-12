from .base_mailer import BaseMailer

# Internal dev-team address: it handles what the Onisep catalogue is missing.
RECIPIENTS = ["perfectible@techpourtoutes.io"]


class PerfectibleMailer(BaseMailer):
    from_email = "TechPourToutes <noreply@techpourtoutes.io>"

    @classmethod
    def missing_record(
        cls, *, user, origin, level, school_label, formation_label, school, formation
    ):
        cls.send_mail(
            subject="Établissement ou formation absent du catalogue",
            recipient_list=RECIPIENTS,
            context={
                "user": user,
                "origin": origin,
                "level": level,
                "school_label": school_label,
                "formation_label": formation_label,
                "school": school,
                "formation": formation,
            },
            tags=["interne", "perfectible", "donnée manquante"],
        )
