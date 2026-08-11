from techpourtoutes.models import Pro
from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService

SITUATION_PRO_MAPPING = {
    Pro.ProfessionalSituation.WORKING: "actif",
    Pro.ProfessionalSituation.RETIRED: "retraite",
    Pro.ProfessionalSituation.JOBLESS: "chomeur",
}

# Jobirl "secteurs_activites" identifier sent for every mentor registration.
JOBIRL_SECTOR_ID = "75851"


class RegisterMentorOnJobirl(JobirlApiBaseService):
    def perform(self, *, user) -> None:
        mobile = "".join(c for c in user.phone.as_national if c.isdigit()) if user.phone else ""
        is_pro = hasattr(user, "pro")
        data = {
            "jobirl_profil": "pro" if is_pro else "jeune",
            "mentorat_profil": "mentor" if is_pro else "aide",
            "choix": "projet",
            "secteurs_activites": JOBIRL_SECTOR_ID,
            "civilite": user.civility,
            "prenom": user.first_name,
            "nom": user.last_name,
            "email": user.email,
            "mobile": mobile,
            "cp": user.postal_code,
        }
        if is_pro:
            data.update(
                {
                    "situation_pro": SITUATION_PRO_MAPPING[user.professional_situation],
                    "poste": user.job_title,
                }
            )
            if user.professional_situation == "working":
                data.update(
                    {
                        "nom_structure": user.structure_name,
                    }
                )

        self.request(
            method="post",
            path="user_register",
            data=data,
        )

        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]
