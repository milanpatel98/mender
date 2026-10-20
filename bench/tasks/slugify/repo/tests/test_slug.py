from slug import slugify


def test_accents_are_transliterated():
    assert slugify("Café Déjà Vu") == "cafe-deja-vu"


def test_basic():
    assert slugify("Hello World") == "hello-world"
