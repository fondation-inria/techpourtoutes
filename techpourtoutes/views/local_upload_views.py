from django.core import signing
from django.core.files.storage import InvalidStorageError, storages
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from storages.backends.s3 import S3Storage

from techpourtoutes.utils.local_upload import read_local_upload_policy


@csrf_exempt
@require_POST
def create_local_upload(request, storage_alias):
    """Stands in for the bucket when no object storage is configured: it receives the very form
    `CreatePresignedUpload` signed, and refuses what the bucket would refuse. Like a bucket, it
    trusts the signed policy, not a CSRF token."""
    storage = _disk_storage_or_404(storage_alias)
    policy = _policy_signed_for(storage_alias, request.POST.get("policy", ""))
    if policy is None or request.POST.get("Content-Type") != policy["content_type"]:
        return HttpResponseForbidden()
    file = request.FILES.get("file")
    if not _fits_in(file, policy):
        return HttpResponseBadRequest()
    storage.save(policy["key"], file)
    return HttpResponse(status=204)


def _disk_storage_or_404(storage_alias):
    """Once a bucket is configured, it receives the uploads itself: this route no longer exists."""
    try:
        storage = storages[storage_alias]
    except InvalidStorageError:
        raise Http404
    if isinstance(storage, S3Storage):
        raise Http404
    return storage


def _policy_signed_for(storage_alias, signed_policy):
    """The policy the app signed for this very storage, or None if it is forged, expired, or
    signed for another one."""
    try:
        policy = read_local_upload_policy(signed_policy)
    except signing.BadSignature:
        return None
    return policy if policy["storage_alias"] == storage_alias else None


def _fits_in(file, policy):
    return file is not None and 1 <= file.size <= policy["max_size"]
