from app.formatter import G5_MISS_HINT, OF_MISS_HINT, ONLINEFIX_PAGE_GUIDE, format_report
from app.result import Candidate, DownloadLink
from app.service import SearchReport


def _of_candidate(title="Cyberpunk 2077 по сети"):
    return Candidate(
        source="online-fix.me",
        title=title,
        page_url="https://online-fix.me/x.html",
        kind="full",
        links=[DownloadLink("直链 (.rar)", "https://uploads.online-fix.me/x.rar")],
        password="online-fix.me",
    )


def _g5_candidate(title="死亡搁浅 导演剪辑版"):
    return Candidate(
        source="gamer520.com",
        title=title,
        page_url="https://www.gamer520.com/43694.html",
        kind="body",
        links=[DownloadLink("网盘", "https://pan.xunlei.com/s/abc?pwd=1234", "提取码: 1234")],
    )


def test_not_found_appends_bilingual_retry_hint():
    report = SearchReport(query="渔力全开", onlinefix_ok=True, gamer520_ok=True)
    text = format_report(report)
    assert text.startswith("未找到《渔力全开》的下载信息。")
    assert "中英文各搜一遍" in text
    assert "/game <游戏中文名>" in text
    assert "/game <游戏英文名>" in text


def test_both_unavailable_no_retry_hint():
    report = SearchReport(query="xxx", onlinefix_ok=False, gamer520_ok=False)
    text = format_report(report)
    assert text == "暂时无法查询《xxx》的下载信息，请稍后再试。"
    assert "中英文各搜一遍" not in text


def test_full_game_only_hints_chinese_retry():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(_of_candidate())
    text = format_report(report)
    assert "全量游戏" in text
    assert "解压密码: online-fix.me" in text
    assert G5_MISS_HINT in text
    assert OF_MISS_HINT not in text


def test_onlinefix_section_has_page_click_guide():
    report = SearchReport(query="Cyberpunk 2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(_of_candidate())
    text = format_report(report)
    assert ONLINEFIX_PAGE_GUIDE in text
    assert "uploads.online-fix.me/x.rar" not in text


def test_body_only_hints_english_retry_when_onlinefix_ok():
    report = SearchReport(query="死亡搁浅", onlinefix_ok=True, gamer520_ok=True)
    report.gamer520_candidates.append(_g5_candidate())
    text = format_report(report)
    assert OF_MISS_HINT in text
    assert "未找到对应的联机补丁" in text
    assert G5_MISS_HINT not in text


def test_no_language_hint_when_onlinefix_down():
    report = SearchReport(query="死亡搁浅", onlinefix_ok=False, gamer520_ok=True)
    report.gamer520_candidates.append(_g5_candidate())
    text = format_report(report)
    assert "online-fix.me 暂时无法访问" in text
    assert OF_MISS_HINT not in text
    assert "未找到对应的联机补丁" not in text


def test_single_full_result_no_numbering():
    report = SearchReport(query="渔力全开", onlinefix_ok=True, gamer520_ok=False)
    report.onlinefix_candidates.append(_of_candidate(title="How to Fish"))
    text = format_report(report)
    assert "\nHow to Fish\n" in text
    assert "1. How to Fish" not in text


def test_single_body_result_no_numbering():
    report = SearchReport(query="死亡搁浅", onlinefix_ok=False, gamer520_ok=True)
    report.gamer520_candidates.append(_g5_candidate())
    text = format_report(report)
    assert "\n死亡搁浅 导演剪辑版\n" in text
    assert "1. 死亡搁浅 导演剪辑版" not in text


def test_multiple_results_keep_numbering():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(_of_candidate(title="Cyberpunk 2077 по сети"))
    report.gamer520_candidates.append(_g5_candidate(title="赛博朋克2077"))
    text = format_report(report)
    assert "1. Cyberpunk 2077 по сети" in text
    assert "2. 赛博朋克2077" in text


def test_both_sources_are_separated_by_an_extra_blank_line():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(_of_candidate())
    report.gamer520_candidates.append(_g5_candidate(title="赛博朋克2077"))
    text = format_report(report)
    assert "【全量游戏（含联机补丁）· online-fix.me】" in text
    assert "\n\n\n【游戏本体 · gamer520.com】" in text



def test_cached_onlinefix_guarded_links_are_filtered():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    cand = Candidate(
        source="online-fix.me",
        title="Cyberpunk 2077 по сети",
        page_url="https://online-fix.me/x.html",
        kind="full",
        links=[
            DownloadLink("直链 (.rar)", "https://uploads.online-fix.me:2053/x.rar"),
            DownloadLink("网盘", "https://mega.nz/file/abc"),
        ],
        password="online-fix.me",
    )
    report.onlinefix_candidates.append(cand)
    text = format_report(report)
    assert "uploads.online-fix.me" not in text
    assert "详情页: https://online-fix.me/x.html" in text
    assert "mega.nz/file/abc" in text
