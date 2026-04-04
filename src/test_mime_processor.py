from mime_processor import fuzzy_match_mimetype_category


def test_fuzzy_match():
    assert fuzzy_match_mimetype_category("get") == None
    assert fuzzy_match_mimetype_category("all") == None
    assert fuzzy_match_mimetype_category("python") == "text/x-python"
