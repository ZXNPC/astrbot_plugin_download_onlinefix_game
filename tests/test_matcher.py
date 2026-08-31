from app.matcher import normalize, rank_hits, score


def test_normalize():
    assert normalize("黑神话：悟空") == normalize("黑神话悟空")
    assert normalize("Cyberpunk 2077") == normalize("cyberpunk2077")
    assert normalize("赛博朋克 2077") == normalize("赛博朋克2077")


def test_score_partial_match():
    assert score("赛博朋克2077", "赛博朋克2077 终极典藏版|解压即撸") > 0.8
    assert score("黑神话悟空", "黑神话：悟空 豪华版") > 0.8
    assert score("cyberpunk 2077", "CyberCorp по сети") < 0.5


def test_rank_hits():
    hits = [
        {"title": "Cyberpunk 2077 по сети", "page_url": "a"},
        {"title": "CyberCorp по сети", "page_url": "b"},
        {"title": "Call of Duty", "page_url": "c"},
    ]
    ranked = rank_hits(hits, "cyberpunk 2077", 2)
    assert ranked[0]["page_url"] == "a"
    assert len(ranked) == 2
