from techpourtoutes.text import mask_email


def test_mask_email_hides_middle_of_local_part():
    assert mask_email("quentin@yahoo.fr") == "q***n@yahoo.fr"


def test_mask_email_short_local_part():
    assert mask_email("qb@yahoo.fr") == "q***@yahoo.fr"
