"""One team per type of structure: it is told about what the pros of that type ask for or
propose, and moderates their events. Each team is a list of addresses from the environment."""

from django.conf import settings

from ..models.structure_type import StructureType


def recipients_for(structure_type):
    """The team following `structure_type`; a type never given still reaches the coalition's
    general address rather than nobody."""
    return _teams().get(structure_type, ["agir@techpourtoutes.io"])


def structure_types_followed_by(email):
    """The types of structure whose team lists `email`. A pro who never gave hers is left to
    the superusers."""
    return [structure_type for structure_type, team in _teams().items() if _lists(team, email)]


def _teams():
    return {
        StructureType.ASSOCIATION: settings.COALITION_ASSOCIATION_RECIPIENTS,
        StructureType.HIGHER_ED: settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS,
        StructureType.SCHOOL: settings.COALITION_SCHOOL_RECIPIENTS,
        StructureType.COMPANY: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
        StructureType.PUBLIC_INSTITUTION: settings.COALITION_PUBLIC_INSTITUTION_RECIPIENTS,
        StructureType.RETIRED: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
        StructureType.JOBLESS: settings.COALITION_WORK_AMBASSADOR_RECIPIENTS,
    }


def _lists(team, email):
    return email.lower() in (address.lower() for address in team)
