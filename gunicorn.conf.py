import os

worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_WORKERS", 1))
threads = int(os.environ.get("GUNICORN_THREADS", 1))
preload_app = True
max_requests = 1000
max_requests_jitter = 100
