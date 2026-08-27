from techpourtoutes.models import School
from techpourtoutes.utils.onisep import read_onisep_csv

from ..base import BaseService


class FlagTrainingAmbassadorSchools(BaseService):
    """Mark the schools the training ambassador form offers, from the curated id list.
    The list is the source of truth: a school dropped from it loses the flag, and an id
    with no row — most of them, when only the samples are imported — is simply inert."""

    FILENAME = "training_ambassador_school_onisep_ids.csv"

    def perform(self) -> None:
        onisep_ids = [row["onisep_id"].strip() for row in read_onisep_csv(self.FILENAME)]
        School.objects.training_ambassador().exclude(onisep_id__in=onisep_ids).update(
            training_ambassador_eligible=False
        )
        School.objects.filter(onisep_id__in=onisep_ids).update(training_ambassador_eligible=True)
