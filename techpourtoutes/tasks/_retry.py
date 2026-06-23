class TransientError(Exception):
    """Raised by tasks when an external call fails with a retryable error ( (5xx, 429)."""


def is_transient_status(code: int | None) -> bool:
    return code is not None and (code == 429 or code >= 500)


def retry_task_later(message):
    raise TransientError(message)


RETRY_KWARGS = {
    "autoretry_for": (TransientError,),
    "retry_backoff": True,
    "retry_backoff_max": 3600,
    "retry_jitter": True,
    "max_retries": 48,
}
