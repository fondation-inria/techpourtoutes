import json
import logging
from datetime import datetime
from pathlib import Path

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class JobirlAPIError(Exception):
    pass


def _save_response(mentor, url, payload: dict, response: httpx.Response) -> None:
    if not settings.DEBUG:
        return
    folder = Path(settings.BASE_DIR) / "var" / "jobirl_responses"
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = folder / f"{timestamp}_{mentor.email}.json"
    try:
        body = response.json()
    except Exception:
        body = response.text
    filepath.write_text(
        json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "url": url,
                "request": payload,
                "response": body,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


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
    url = f"{settings.JOBIRL_URL}/techpourtoutes/api/user_register"
    try:
        headers = {"Authorization": f"Bearer {settings.JOBIRL_API_TOKEN}"}
        response = httpx.post(url, data=payload, headers=headers)
        _save_response(mentor, url, payload, response)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Jobirl API returned %s for mentor %s", exc.response.status_code, mentor.pk)
        code = exc.response.status_code
        raise JobirlAPIError(
            f"L'inscription sur la plateforme partenaire a échoué (code {code}). "
            "Veuillez réessayer ou contacter le support."
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Jobirl API network error for mentor %s: %s", mentor.pk, exc)
        raise JobirlAPIError(
            "Impossible de joindre la plateforme partenaire. Veuillez réessayer ultérieurement."
        ) from exc
