from api.clients.jobirl import JobirlAPIError, JobirlClient

__all__ = ["JobirlAPIError"]


def register_mentor_on_jobirl(mentor) -> None:
    phone = str(mentor.phone.national_number) if mentor.phone else ""
    payload = {
        "jobirl_profil": "pro",
        "mentorat_profil": "mentor",
        "email": mentor.email,
        "prenom": mentor.first_name,
        "nom": mentor.last_name,
        "mobile": phone,
        "situation_pro": mentor.professional_situation,
        "poste": mentor.job_title,
        "nom_structure": mentor.structure_name,
        "cp": mentor.postal_code,
    }
    JobirlClient().post("user_register", data=payload, debug_context=mentor.email)
