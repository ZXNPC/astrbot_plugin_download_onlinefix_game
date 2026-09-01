from app.name_lookup import (
    contains_cjk,
    extract_appdetails_name,
    extract_search_hit,
    has_cjk_overlap,
)

STORE_PAYLOAD = {
    "total": 1,
    "items": [
        {"id": 4001890, "name": "渔力全开", "type": "app"},
    ],
}


def test_contains_cjk():
    assert contains_cjk("黑神话悟空")
    assert contains_cjk("赛博朋克2077")
    assert not contains_cjk("cyberpunk 2077")


def test_has_cjk_overlap():
    assert has_cjk_overlap("渔力全开", "渔力全开")
    assert has_cjk_overlap("黑神话悟空", "黑神话：悟空 豪华版")
    assert has_cjk_overlap("赛博朋克2077", "赛博朋克2077 终极典藏版")
    assert not has_cjk_overlap("渔力全开", "How to Fish")
    assert not has_cjk_overlap("死亡搁浅", "赛博朋克2077")


def test_extract_search_hit_zh_name():
    hit = extract_search_hit(STORE_PAYLOAD, "渔力全开")
    assert hit == {"id": 4001890, "name": "渔力全开"}


def test_extract_search_hit_english_name_used_directly():
    payload = {
        "total": 1,
        "items": [{"id": 2073850, "name": "How to Fish", "type": "app"}],
    }
    hit = extract_search_hit(payload, "渔力全开")
    assert hit == {"id": 2073850, "name": "How to Fish"}


def test_extract_search_hit_skips_non_app_and_no_overlap():
    payload = {
        "items": [
            {"id": 2, "name": "渔力全开 DLC", "type": "dlc"},
            {"id": 3, "name": "无关游戏", "type": "app"},
        ]
    }
    assert extract_search_hit(payload, "渔力全开") is None


def test_extract_search_hit_empty():
    assert extract_search_hit({"total": 0, "items": []}, "渔力全开") is None
    assert extract_search_hit(None, "渔力全开") is None


def test_extract_appdetails_name():
    payload = {"4001890": {"success": True, "data": {"name": "How to Fish"}}}
    assert extract_appdetails_name(payload, 4001890) == "How to Fish"


def test_extract_appdetails_name_failures():
    assert extract_appdetails_name({"4001890": {"success": False}}, 4001890) is None
    assert extract_appdetails_name({}, 4001890) is None
    assert extract_appdetails_name(None, 4001890) is None