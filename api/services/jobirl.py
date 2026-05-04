from api.clients.jobirl import JobirlAPIError, JobirlClient

__all__ = ["JobirlAPIError"]


def register_mentor_on_jobirl(mentor) -> None:
    phone = f"0{mentor.phone.national_number}" if mentor.phone else ""
    payload = {
        "jobirl_profil": "pro",
        "mentorat_profil": "mentor",
        "choix": "projet",
        "civilite": "Madame",
        "prenom": mentor.first_name,
        "nom": mentor.last_name,
        "email": mentor.email,
        "mobile": phone,
        "bdate": "2000-08-08",
        "cp": mentor.postal_code,
        "adresse": "10 rue Deguerry",
        "ville": "Paris",
        "situation_pro": "retraite",
        "secteurs_activites": "",
        "poste": mentor.job_title,
        "nom_structure": mentor.structure_name,
        "adresse_structure": "",
        "cp_structure": "",
        "ville_structure": "",
    }
    JobirlClient().post("user_register", data=payload)


# implement :
# - civilite
# - situation_pro (actif, retraite, chomeur)
# - bdate YYYY-MM-DD
# - adresse
# - ville
# - secteurs_activites
# - choix ? (parcousup,stage,projet)

# infos structures required if actif ; else, do not ask
