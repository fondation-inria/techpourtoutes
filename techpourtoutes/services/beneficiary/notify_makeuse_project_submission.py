from ...mailers import BeneficiaryMailer, ConsortiumMailer
from ..base import BaseService


class NotifyMakeuseProjectSubmission(BaseService):
    def perform(self, *, beneficiary, project_name, project_link, project_description):
        ConsortiumMailer.makeuse_project_submitted(
            beneficiary=beneficiary,
            project_name=project_name,
            project_link=project_link,
            project_description=project_description,
        )
        BeneficiaryMailer.makeuse_project_submitted(beneficiary=beneficiary)
