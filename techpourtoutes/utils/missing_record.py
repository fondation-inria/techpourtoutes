from ..mailers import PerfectibleMailer


def report_missing_record(form, user, origin):
    """Sends to the team what a user could not find, so they can create it by hand.

    Every form offering the free-text fallback calls this right after saving: what resolved is
    already persisted, what did not is only ever recoverable from this mail.
    """
    if form.has_missing_record:
        PerfectibleMailer.missing_record(user=user, origin=origin, **form.missing_record_report())
