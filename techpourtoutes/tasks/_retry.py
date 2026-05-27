class TransientError(Exception):
    """Raised by tasks when an external call fails with a retryable error ( (5xx, 429)."""


RETRY_KWARGS = {
    "autoretry_for": (TransientError,),
    "retry_backoff": True,
    "retry_backoff_max": 3600,
    "retry_jitter": True,
    "max_retries": 48,
}
