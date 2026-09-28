from .account import (
    BeneficiaryEditUserForm,
    BeneficiaryLegalRepEditForm,
    BeneficiaryTrainingExperienceForm,
    DestroyUserForm,
    ProEditUserForm,
    ProTrainingExperienceForm,
    UserCommunicationForm,
    UserEmailChangeForm,
)
from .auth import LoginRequestForm, VerificationCodeForm
from .beneficiary_inscription import (
    BeneficiaryEmailForm,
    BeneficiaryHigherEducationTrainingExperienceForm,
    BeneficiaryHighSchoolTrainingExperienceForm,
    BeneficiaryIdentityForm,
    BeneficiaryLastDiplomaTrainingExperienceForm,
    BeneficiaryMentoringSignUpForm,
    BeneficiaryStudyStatusForm,
    StudyStatus,
)
from .engagement import EngagementForm, TrainingAmbassadorForm, WorkshopRequestForm
from .event import EventDetailsForm, EventLocationForm, EventSubcategoryForm
from .manifeste_signature_form import ManifesteSignatureForm
from .upcoming_feature_notification_form import UpcomingFeatureNotificationForm

__all__ = [
    "BeneficiaryEmailForm",
    "BeneficiaryHigherEducationTrainingExperienceForm",
    "BeneficiaryHighSchoolTrainingExperienceForm",
    "BeneficiaryIdentityForm",
    "BeneficiaryLastDiplomaTrainingExperienceForm",
    "BeneficiaryMentoringSignUpForm",
    "BeneficiaryStudyStatusForm",
    "BeneficiaryLegalRepEditForm",
    "BeneficiaryEditUserForm",
    "BeneficiaryTrainingExperienceForm",
    "UserCommunicationForm",
    "StudyStatus",
    "DestroyUserForm",
    "UserEmailChangeForm",
    "UpcomingFeatureNotificationForm",
    "EngagementForm",
    "EventSubcategoryForm",
    "EventDetailsForm",
    "EventLocationForm",
    "LoginRequestForm",
    "ManifesteSignatureForm",
    "ProEditUserForm",
    "ProTrainingExperienceForm",
    "TrainingAmbassadorForm",
    "VerificationCodeForm",
    "WorkshopRequestForm",
]
