from corrector.core import paths
from corrector.core.userdict import UserDictionary
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.spell import SpellEngine


def test_names_list_accepts_exact_case(tmp_path):
    ru = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    engine = SpellEngine("ru_spell", ru, set(), UserDictionary(tmp_path / "с.txt"), names={"Кызылординской"})
    assert engine.check([(0, "Суд Кызылординской области")]) == []
    assert len(engine.check([(0, "Суд кызылординской области")])) == 1


def test_unknown_capitalized_word_policy(tmp_path):
    from corrector.core.issue import Level
    ru = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    engine = SpellEngine("ru_spell", ru, set(), UserDictionary(tmp_path / "с.txt"))
    twice = engine.check([(0, "Истец Турматова подала иск."), (1, "Представитель Турматова явился.")])
    assert twice == []
    once = engine.check([(0, "Истец Турматова подала иск.")])
    assert len(once) == 1 and once[0].level is Level.HINT and once[0].suggestions == [] and "имя или название" in once[0].message
    start = engine.check([(0, "Турматова подала иск.")])
    assert len(start) == 1 and start[0].level is Level.ERROR
