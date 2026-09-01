from app.formatter import format_report
from app.result import Candidate, DownloadLink
from app.service import SearchReport


def test_not_found_without_hints():
    report = SearchReport(query="xxx", onlinefix_ok=True, gamer520_ok=True)
    text = format_report(report)
    assert text == "未找到《xxx》的下载信息。"


def test_both_unavailable():
    report = SearchReport(query="xxx", onlinefix_ok=False, gamer520_ok=False)
    assert "暂时无法查询" in format_report(report)


def test_full_game_section():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(
        Candidate(
            source="online-fix.me",
            title="Cyberpunk 2077 по сети",
            page_url="https://online-fix.me/games/adventures/1-cyberpunk-2077-po-seti.html",
            kind="full",
            links=[DownloadLink("直链 (.rar)", "https://uploads.online-fix.me/CyberPunk_2077/Fix Repair/x.rar")],
            password="online-fix.me",
        )
    )
    text = format_report(report)
    assert "全量游戏" in text
    assert "解压密码: online-fix.me" in text


def test_body_only_note():
    report = SearchReport(query="死亡搁浅", onlinefix_ok=True, gamer520_ok=True)
    report.gamer520_candidates.append(
        Candidate(
            source="gamer520.com",
            title="死亡搁浅 导演剪辑版",
            page_url="https://www.gamer520.com/43694.html",
            kind="body",
            links=[DownloadLink("网盘", "https://pan.xunlei.com/s/abc?pwd=1234", "提取码: 1234")],
        )
    )
    text = format_report(report)
    assert "未找到对应的联机补丁" in text


def test_single_full_result_no_numbering():
    report = SearchReport(query="渔力全开", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(
        Candidate(
            source="online-fix.me",
            title="How to Fish",
            page_url="https://online-fix.me/x.html",
            kind="full",
            links=[DownloadLink("直链 (.rar)", "https://uploads.online-fix.me/x.rar")],
            password="online-fix.me",
        )
    )
    text = format_report(report)
    assert "\nHow to Fish\n" in text
    assert "1. How to Fish" not in text


def test_single_body_result_no_numbering():
    report = SearchReport(query="死亡搁浅", onlinefix_ok=True, gamer520_ok=True)
    report.gamer520_candidates.append(
        Candidate(
            source="gamer520.com",
            title="死亡搁浅 导演剪辑版",
            page_url="https://www.gamer520.com/43694.html",
            kind="body",
            links=[DownloadLink("网盘", "https://pan.xunlei.com/s/abc?pwd=1234", "提取码: 1234")],
        )
    )
    text = format_report(report)
    assert "\n死亡搁浅 导演剪辑版\n" in text
    assert "1. 死亡搁浅 导演剪辑版" not in text


def test_multiple_results_keep_numbering():
    report = SearchReport(query="赛博朋克2077", onlinefix_ok=True, gamer520_ok=True)
    report.onlinefix_candidates.append(
        Candidate(source="online-fix.me", title="Cyberpunk 2077 по сети", page_url="a", kind="full")
    )
    report.gamer520_candidates.append(
        Candidate(source="gamer520.com", title="赛博朋克2077", page_url="b", kind="body")
    )
    text = format_report(report)
    assert "1. Cyberpunk 2077 по сети" in text
    assert "2. 赛博朋克2077" in text


def test_name_resolution_failed_hint_appended():
    report = SearchReport(
        query="渔力全开",
        onlinefix_ok=True,
        gamer520_ok=True,
        name_resolution_failed=True,
    )
    report.gamer520_candidates.append(
        Candidate(source="gamer520.com", title="渔力全开", page_url="b", kind="body")
    )
    text = format_report(report)
    assert "未能自动获取该游戏的英文名" in text
    assert "/game <游戏英文名>" in text


def test_name_resolution_failed_hint_on_not_found():
    report = SearchReport(
        query="渔力全开",
        onlinefix_ok=True,
        gamer520_ok=True,
        name_resolution_failed=True,
    )
    text = format_report(report)
    assert text.startswith("未找到《渔力全开》的下载信息。")
    assert "未能自动获取该游戏的英文名" in text


def test_no_hint_when_resolution_ok():
    report = SearchReport(query="渔力全开", onlinefix_ok=True, gamer520_ok=True)
    report.gamer520_candidates.append(
        Candidate(source="gamer520.com", title="渔力全开", page_url="b", kind="body")
    )
    text = format_report(report)
    assert "未能自动获取该游戏的英文名" not in text


def test_no_hint_when_sources_unavailable():
    report = SearchReport(
        query="渔力全开",
        onlinefix_ok=False,
        gamer520_ok=False,
        name_resolution_failed=True,
    )
    text = format_report(report)
    assert text == "暂时无法查询《渔力全开》的下载信息，请稍后再试。"