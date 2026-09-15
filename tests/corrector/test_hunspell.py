from corrector.core import paths
from corrector.engines.hunspell import SpellDictionary


def test_kazakh_dictionary_knows_legal_words():
    d = SpellDictionary(paths.data_dir() / "kk" / "kk_KZ")
    for word in ["сот", "соттың", "талапкер", "қаулы", "шешімі", "қанағаттандырылсын", "апелляциялық", "Астана"]:
        assert d.known(word), word
    assert not d.known("соттын")
    assert d.suggest("соттын")[0] == "соттың"


def test_russian_dictionary_and_suggestions_cached():
    d = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    assert d.known("ходатайство") and d.known("Верховный")
    assert not d.known("ходатайтсво")
    first = d.suggest("ходатайтсво")
    assert first[0] == "ходатайство"
    assert d.suggest("ходатайтсво") is first
