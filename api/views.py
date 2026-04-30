import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

_mock_status = {"code": 200}


@csrf_exempt
@require_POST
def mock_jobirl_register(request):
    code = _mock_status["code"]
    logger.info("Mock Jobirl user_register called (status=%s): %s", code, dict(request.POST))
    if code != 200:
        return JsonResponse({"status": "error", "message": "mock error"}, status=code)
    return JsonResponse({"status": "ok", "message": "mock: utilisateur créé"})
