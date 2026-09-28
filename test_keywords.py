from koltool.keywords import dedupe_keywords, parse_bulk_keywords


def test_keyword_deduplication_normalizes_spaces_and_case():
    assert dedupe_keywords(["Pokemon PSA", " pokemon   psa ", "盲盒", "盲盒"]) == ["Pokemon PSA", "盲盒"]
    assert parse_bulk_keywords("一番赏，盲盒\n一番赏；GK") == ["一番赏", "盲盒", "GK"]
