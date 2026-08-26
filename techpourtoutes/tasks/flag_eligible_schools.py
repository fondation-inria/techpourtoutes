from celery import shared_task

from techpourtoutes.services.school.flag_eligible_schools import FlagEligibleSchools


@shared_task
def flag_eligible_schools_task():
    result = FlagEligibleSchools()
    if result.failure:
        raise RuntimeError(", ".join(result.errors))
