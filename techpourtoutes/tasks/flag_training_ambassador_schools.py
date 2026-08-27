from celery import shared_task

from techpourtoutes.services.school.flag_training_ambassador_schools import (
    FlagTrainingAmbassadorSchools,
)


@shared_task
def flag_training_ambassador_schools_task():
    result = FlagTrainingAmbassadorSchools()
    if result.failure:
        raise RuntimeError(", ".join(result.errors))
