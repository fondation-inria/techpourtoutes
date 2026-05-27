RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 3600,
    "retry_jitter": True,
    "max_retries": 48,
}
