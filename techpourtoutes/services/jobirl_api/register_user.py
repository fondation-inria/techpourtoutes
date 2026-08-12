from techpourtoutes.models import Pro, TrainingExperience
from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService

SITUATION_PRO_MAPPING = {
    Pro.ProfessionalSituation.WORKING: "actif",
    Pro.ProfessionalSituation.RETIRED: "retraite",
    Pro.ProfessionalSituation.JOBLESS: "chomeur",
}

# Jobirl "secteurs_activites" identifier sent for every mentor registration.
JOBIRL_SECTOR_ID = "75851"

# Every beneficiary's "filière" is registered as "Générale" until Jobirl needs otherwise.
BENEFICIARY_FILIERE = "Générale"


class RegisterMentorOnJobirl(JobirlApiBaseService):
    def perform(self, *, user) -> None:
        is_pro = hasattr(user, "pro")
        data = self._common_data(user)
        data.update(self._pro_data(user) if is_pro else self._beneficiary_data(user))

        self.request(
            method="post",
            path="user_register",
            data=data,
        )

        self.user_id = self.jobirl_response_body["id"]
        self.token = self.jobirl_response_body["token"]

    def _common_data(self, user) -> dict:
        mobile = "".join(c for c in user.phone.as_national if c.isdigit()) if user.phone else ""
        return {
            "choix": "projet",
            "secteurs_activites": JOBIRL_SECTOR_ID,
            "civilite": user.civility,
            "prenom": user.first_name,
            "nom": user.last_name,
            "email": user.email,
            "mobile": mobile,
            "cp": user.postal_code,
        }

    def _pro_data(self, user) -> dict:
        data = {
            "jobirl_profil": "pro",
            "mentorat_profil": "mentor",
            "situation_pro": SITUATION_PRO_MAPPING[user.professional_situation],
            "poste": user.job_title,
        }
        if user.professional_situation == "working":
            data["nom_structure"] = user.structure_name
        return data

    def _beneficiary_data(self, user) -> dict:
        experience = user.training_experiences.first()
        is_secondary = experience.level in TrainingExperience.SECONDARY_LEVELS
        level_field = "classe" if is_secondary else "niveau_etudes"
        data = {
            "jobirl_profil": "jeune",
            "mentorat_profil": "aide",
            "bdate": user.birth_date.isoformat(),
            "profil_jeune": "lyceenne" if is_secondary else "etudiante",
            # We never ask a beneficiary for her own postal code, so we use her school's instead
            "cp": experience.school.postal_code,
            "filiere": BENEFICIARY_FILIERE,
            "etablissement": experience.school.name,
            "etablissement_code_uai_onisep": experience.school.uai,
            "formation": experience.formation.name,
            "formation_code_onisep": experience.formation.onisep_id,
            level_field: experience.get_level_display(),
        }
        if user.legal_representative_email:
            data["email_tuteur"] = user.legal_representative_email
        return data
