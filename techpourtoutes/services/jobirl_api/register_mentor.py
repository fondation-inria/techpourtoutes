from techpourtoutes.models import Pro
from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService

SITUATION_PRO_MAPPING = {
    Pro.ProfessionalSituation.WORKING: "actif",
    Pro.ProfessionalSituation.STUDENT: "actif",
    Pro.ProfessionalSituation.RETIRED: "retraite",
    Pro.ProfessionalSituation.JOBLESS: "chomeur",
}


class RegisterMentorOnJobirl(JobirlApiBaseService):
    def perform(self, *, pro) -> None:
        field_of_study = (
            f"En étude - {pro.job_title}" if pro.professional_situation == "student" else ""
        )
        payload = {
            "jobirl_profil": "pro",
            "mentorat_profil": "mentor",
            "choix": "projet",
            "secteurs_activites": "75851",
            "civilite": pro.civility,
            "prenom": pro.first_name,
            "nom": pro.last_name,
            "email": pro.email,
            "mobile": f"0{pro.phone.national_number}" if pro.phone else "",
            "cp": pro.postal_code,
            "situation_pro": SITUATION_PRO_MAPPING[pro.professional_situation],
            "poste": field_of_study if field_of_study else pro.job_title,
        }
        if pro.professional_situation in ["student", "working"]:
            payload.update(
                {
                    "nom_structure": pro.structure_name,
                }
            )

        self.request(
            method="post",
            path="user_register",
            payload=payload,
        )

        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]
