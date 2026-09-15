from corrector.rules.alphabets import LOOKALIKES, fix_lookalikes, is_mixed


def test_is_mixed():
    assert is_mixed("Кazakhstan") and is_mixed("иcтец") and is_mixed("ИнтерснабGas")
    assert not is_mixed("Windows") and not is_mixed("истец") and not is_mixed("ҚР")


def test_fix_lookalikes_only_when_every_latin_letter_has_pair():
    assert fix_lookalikes("иcтец") == "истец"
    assert fix_lookalikes("Кazakhstan") is None
    assert LOOKALIKES["c"] == "с" and LOOKALIKES["H"] == "Н"
