from techpourtoutes.utils.environment import email_subject_prefix, review_app_name


def test_email_subject_prefix_names_a_review_app_after_its_pull_request():
    assert email_subject_prefix("techpourtoutes-staging-pr320") == "[pr-320] "


def test_email_subject_prefix_names_staging():
    assert email_subject_prefix("techpourtoutes-staging") == "[staging] "


def test_email_subject_prefix_is_empty_in_production():
    assert email_subject_prefix("techpourtoutes") == ""


def test_email_subject_prefix_is_empty_outside_scalingo():
    assert email_subject_prefix("") == ""


def test_review_app_name_is_the_app_name_of_a_review_app():
    assert review_app_name("techpourtoutes-staging-pr320") == "techpourtoutes-staging-pr320"


def test_review_app_name_is_empty_outside_a_review_app():
    assert review_app_name("techpourtoutes-staging") == ""
    assert review_app_name("") == ""
