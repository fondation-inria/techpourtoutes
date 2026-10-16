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
    BeneficiaryMakeuseProjectSubmissionForm,
    BeneficiaryMentoringSignUpForm,
    BeneficiaryStudyStatusForm,
    BeneficiaryTrainingAmbassadorRequestForm,
    StudyStatus,
)
from .event import EventDetailsForm, EventLocationForm, EventSubcategoryForm
from .manifeste_signature_form import ManifesteSignatureForm
from .pro_inscription import (
    ProAdditionalInformationForm,
    ProEmailForm,
    ProEngagementsForm,
    ProIdentityForm,
    ProTrainingAmbassadorForm,
    ProWorkshopRequestForm,
)
from .upcoming_feature_notification_form import UpcomingFeatureNotificationForm

__all__ = [
    "BeneficiaryEmailForm",
    "BeneficiaryHigherEducationTrainingExperienceForm",
    "BeneficiaryHighSchoolTrainingExperienceForm",
    "BeneficiaryIdentityForm",
    "BeneficiaryLastDiplomaTrainingExperienceForm",
    "BeneficiaryMakeuseProjectSubmissionForm",
    "BeneficiaryMentoringSignUpForm",
    "BeneficiaryStudyStatusForm",
    "BeneficiaryTrainingAmbassadorRequestForm",
    "BeneficiaryLegalRepEditForm",
    "BeneficiaryEditUserForm",
    "BeneficiaryTrainingExperienceForm",
    "UserCommunicationForm",
    "StudyStatus",
    "DestroyUserForm",
    "UserEmailChangeForm",
    "UpcomingFeatureNotificationForm",
    "EventSubcategoryForm",
    "EventDetailsForm",
    "EventLocationForm",
    "LoginRequestForm",
    "ManifesteSignatureForm",
    "ProEditUserForm",
    "ProEmailForm",
    "ProEngagementsForm",
    "ProIdentityForm",
    "ProAdditionalInformationForm",
    "ProTrainingAmbassadorForm",
    "ProWorkshopRequestForm",
    "ProTrainingExperienceForm",
    "VerificationCodeForm",
]
