from corrector.engines import kk_stem


def test_stems_inflected_forms():
    stemmer = kk_stem.default()
    assert stemmer.stem("мектептерімізде") == "мектеп"
    assert stemmer.stem("Соттың") == "сот"
    assert stemmer.stem("талапкердің") == "талапкер"
    assert stemmer.stem("жауапкерлерге") == "жауапкер"


def test_stems_of_text_keep_tokens():
    stemmer = kk_stem.default()
    pairs = stemmer.stems("Соттың шешімімен талапкер келісті")
    assert [t.text for t, _ in pairs] == ["Соттың", "шешімімен", "талапкер", "келісті"]
    assert [s for _, s in pairs][:3] == ["сот", "шешім", "талапкер"]
