import re

REVIEW_APP = re.compile(r"-pr(\d+)$")


def email_subject_prefix(app_name: str) -> str:
    """Tag the subjects of every mail sent from outside production, after Scalingo's `$APP`.

    A review app is named after its pull request (`techpourtoutes-staging-pr320`), staging after
    itself. Production — and local dev, where `$APP` is unset — sends its subjects untouched.
    """
    if review_app := REVIEW_APP.search(app_name):
        return f"[pr-{review_app[1]}] "
    return "[staging] " if app_name.endswith("-staging") else ""


def review_app_name(app_name: str) -> str:
    """Scalingo's `$APP` on a review app, empty anywhere else."""
    return app_name if REVIEW_APP.search(app_name) else ""
