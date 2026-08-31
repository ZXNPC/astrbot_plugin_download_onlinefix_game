from app.translate import contains_cjk, extract_translation


def test_contains_cjk():
    assert contains_cjk("黑神话悟空")
    assert not contains_cjk("cyberpunk 2077")


def test_extract_translation():
    payload = [[["Cyberpunk 2077", "赛博朋克2077", None, None, 1]], None, "en"]
    assert extract_translation(payload) == "Cyberpunk 2077"
