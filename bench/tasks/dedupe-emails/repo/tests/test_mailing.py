from mailing import unique_emails


def test_order_and_spelling_kept():
    emails = ["Zoe@Example.com", "amy@example.com", "zoe@example.com", "Bob@x.org"]
    assert unique_emails(emails) == ["Zoe@Example.com", "amy@example.com", "Bob@x.org"]
