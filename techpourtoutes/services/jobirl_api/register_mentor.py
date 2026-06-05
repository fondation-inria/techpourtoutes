from techpourtoutes.models import Pro
from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService

SITUATION_PRO_MAPPING = {
    Pro.ProfessionalSituation.WORKING: "actif",
    Pro.ProfessionalSituation.RETIRED: "retraite",
    Pro.ProfessionalSituation.JOBLESS: "chomeur",
}


class RegisterMentorOnJobirl(JobirlApiBaseService):
    def perform(self, *, pro) -> None:
        mobile = "".join(c for c in pro.phone.as_national if c.isdigit()) if pro.phone else ""
        data = {
            "jobirl_profil": "pro",
            "mentorat_profil": "mentor",
            "choix": "projet",
            "secteurs_activites": "75851",
            "civilite": pro.civility,
            "prenom": pro.first_name,
            "nom": pro.last_name,
            "email": pro.email,
            "mobile": mobile,
            "cp": pro.postal_code,
            "situation_pro": SITUATION_PRO_MAPPING[pro.professional_situation],
            "poste": pro.job_title,
        }
        if pro.professional_situation == "working":
            data.update(
                {
                    "nom_structure": pro.structure_name,
                }
            )

        self.request(
            method="post",
            path="user_register",
            data=data,
        )

        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]
