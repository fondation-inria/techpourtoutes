from .email_form import BeneficiaryEmailForm
from .high_school_training_experience_form import BeneficiaryHighSchoolTrainingExperienceForm
from .higher_education_training_experience_form import (
    BeneficiaryHigherEducationTrainingExperienceForm,
)
from .identity_form import BeneficiaryIdentityForm
from .last_diploma_training_experience_form import (
    BeneficiaryLastDiplomaTrainingExperienceForm,
)
from .mentoring_signup_form import BeneficiaryMentoringSignUpForm
from .study_status_form import BeneficiaryStudyStatusForm, StudyStatus

__all__ = [
    "BeneficiaryEmailForm",
    "BeneficiaryHigherEducationTrainingExperienceForm",
    "BeneficiaryHighSchoolTrainingExperienceForm",
    "BeneficiaryIdentityForm",
    "BeneficiaryLastDiplomaTrainingExperienceForm",
    "BeneficiaryMentoringSignUpForm",
    "BeneficiaryStudyStatusForm",
    "StudyStatus",
]
