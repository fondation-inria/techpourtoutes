import pytest


@pytest.mark.django_db
def test_training_experience_links_pro_and_higher_ed_school(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience(
        pro=pro, higher_ed_school=higher_ed_school, course="Master Informatique"
    )
    experience.save()

    assert experience in pro.training_experiences.all()
    assert experience in higher_ed_school.training_experiences.all()
