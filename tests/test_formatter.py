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
