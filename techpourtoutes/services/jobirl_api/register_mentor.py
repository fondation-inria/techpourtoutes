from techpourtoutes.models import Mentor
from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService

SITUATION_PRO_MAPPING = {
    Mentor.ProfessionalSituation.WORKING: "actif",
    Mentor.ProfessionalSituation.STUDENT: "actif",
    Mentor.ProfessionalSituation.RETIRED: "retraite",
    Mentor.ProfessionalSituation.JOBLESS: "chomeur",
}


class RegisterMentorOnJobirl(JobirlApiBaseService):
    def perform(self, *, mentor) -> None:
        field_of_study = (
            f"En étude - {mentor.job_title}" if mentor.professional_situation == "student" else ""
        )
        payload = {
            "jobirl_profil": "pro",
            "mentorat_profil": "mentor",
            "choix": "projet",
            "secteurs_activites": "75851",
            "civilite": mentor.civility,
            "prenom": mentor.first_name,
            "nom": mentor.last_name,
            "email": mentor.email,
            "mobile": f"0{mentor.phone.national_number}" if mentor.phone else "",
            "cp": mentor.postal_code,
            "ville": mentor.city,
            "situation_pro": SITUATION_PRO_MAPPING[mentor.professional_situation],
            "poste": field_of_study if field_of_study else mentor.job_title,
        }
        if mentor.professional_situation in ["student", "working"]:
            payload.update(
                {
                    "nom_structure": mentor.structure_name,
                }
            )

        self.request(
            method="post",
            path="user_register",
            payload=payload,
        )

        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]
