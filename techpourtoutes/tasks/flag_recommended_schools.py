from celery import shared_task

from techpourtoutes.services.school.flag_recommended_schools import FlagRecommendedSchools


@shared_task
def flag_recommended_schools_task():
    result = FlagRecommendedSchools()
    if result.failure:
        raise RuntimeError(", ".join(result.errors))
