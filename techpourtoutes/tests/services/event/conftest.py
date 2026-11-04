import pytest

from techpourtoutes.models import Pro


@pytest.fixture
def pro(pro):
    """An event's author has always said what type of structure she works in: the team told
    about it follows it."""
    pro.structure_type = Pro.StructureType.PUBLIC_INSTITUTION
    pro.save()
    return pro
