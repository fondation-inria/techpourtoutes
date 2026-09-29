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
    try:
        storage = storages[storage_alias]
    except InvalidStorageError:
        raise Http404
    if isinstance(storage, S3Storage):
        raise Http404
    try:
        policy = read_local_upload_policy(request.POST.get("policy", ""))
    except signing.BadSignature:
        return HttpResponseForbidden()
    if policy["storage_alias"] != storage_alias:
        return HttpResponseForbidden()
    file = request.FILES.get("file")
    if file is None or not 1 <= file.size <= policy["max_size"]:
        return HttpResponseBadRequest()
    storage.save(policy["key"], file)
    return HttpResponse(status=204)
