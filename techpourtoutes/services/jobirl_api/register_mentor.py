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
        self.request(
            method="post",
            path="user_register",
            payload={
                "jobirl_profil": "pro",
                "mentorat_profil": "mentor",
                "choix": "projet",
                "civilite": mentor.civility,
                "prenom": mentor.first_name,
                "nom": mentor.last_name,
                "email": mentor.email,
                "mobile": f"0{mentor.phone.national_number}" if mentor.phone else "",
                "bdate": mentor.birth_date.strftime("%Y-%m-%d"),
                "cp": mentor.postal_code,
                "adresse": mentor.address,
                "ville": mentor.city,
                "situation_pro": SITUATION_PRO_MAPPING[mentor.professional_situation],
                "secteurs_activites": "75851",
                "poste": mentor.job_title,
                "nom_structure": mentor.structure_name,
                "adresse_structure": "",
                "cp_structure": "",
                "ville_structure": "",
            },
        )
        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]
