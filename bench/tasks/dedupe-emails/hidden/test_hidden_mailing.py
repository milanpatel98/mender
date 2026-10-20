from mailing import unique_emails


def test_empty():
    assert unique_emails([]) == []


def test_large_list_keeps_order():
    emails = [f"user{i % 50}@site.com" if i % 2 else f"USER{i % 50}@SITE.COM" for i in range(1000)]
    out = unique_emails(emails)
    assert len(out) == 50
    assert out[0] == "USER0@SITE.COM"
    assert [e.lower() for e in out] == [f"user{i}@site.com" for i in range(50)]


def test_accepts_any_iterable():
    assert unique_emails(iter(["a@b.c", "A@B.C"])) == ["a@b.c"]
