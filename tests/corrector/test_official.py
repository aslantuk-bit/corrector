from corrector.rules.official import find_candidates, similar


def test_find_candidates_matches_by_first_and_last_word():
    text = "постановление Верховного суда Республики Казахстан от 1 января"
    found = find_candidates(text, "Верховный Суд Республики Казахстан")
    assert [text[s:e] for s, e in found] == ["Верховного суда Республики Казахстан"]


def test_similarity_threshold():
    assert similar("Верховного суда Республики Казахстан", "Верховный Суд Республики Казахстан")
    assert not similar("Верховный Суд Российской Федерации", "Верховный Суд Республики Казахстан")
