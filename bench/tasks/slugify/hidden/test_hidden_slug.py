from slug import slugify


def test_more_accents():
    assert slugify("Crème Brûlée") == "creme-brulee"
    assert slugify("naïve résumé") == "naive-resume"
    assert slugify("Ångström") == "angstrom"


def test_punctuation_and_spacing():
    assert slugify("  Hello,   World!  ") == "hello-world"
    assert slugify("--rooms & suites--") == "rooms-suites"


def test_empty():
    assert slugify("") == ""
    assert slugify("!!!") == ""
