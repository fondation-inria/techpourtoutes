class TransientError(Exception):
    """Raised by tasks when an external call fails with a retryable error ( (5xx, 429)."""


def raise_failure(result) -> None:
    """Turn a failed service's errors into the exception that matches its kind."""
    message = ", ".join(result.errors)
    if result.failed_with_transient_error:
        raise TransientError(message)
    raise RuntimeError(message)


RETRY_KWARGS = {
    "autoretry_for": (TransientError,),
    "retry_backoff": True,
    "retry_backoff_max": 3600,
    "retry_jitter": True,
    "max_retries": 48,
}
