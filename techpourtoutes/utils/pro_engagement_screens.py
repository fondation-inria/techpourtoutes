from ..forms import ProAdditionalInformationForm
from ..models import Pro

# The screen each engagement calls for; every other one only completes her profile, if needed.
_INDEPENDANT_SCREEN = {
    Pro.Engagement.TRAINING_AMBASSADOR: "training_ambassador",
    Pro.Engagement.WORKSHOPS: "workshop_request",
}


def screen_for(pro, engagement):
    """The screen `pro` still has to answer to take on `engagement`, or None when she has
    nothing left to give."""
    if engagement in _INDEPENDANT_SCREEN:
        return _INDEPENDANT_SCREEN[engagement]
    if ProAdditionalInformationForm(pro=pro).asks_anything:
        return "additional_information"
    return None
