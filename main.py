"""AstrBot 插件：根据你想玩的游戏，从 gamer520.com 与 online-fix.me 查找下载信息。"""

import re
import traceback
from pathlib import Path
from typing import Optional

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .app.cache import SearchCache
from .app.formatter import format_report
from .app.service import GameDownloadService

PLUGIN_NAME = "astrbot_plugin_wanna_play_game"
PLUGIN_AUTHOR = "ZXNPC"
PLUGIN_DESC = "根据你想玩的游戏，从 gamer520.com 与 online-fix.me 查找下载信息"
PLUGIN_VERSION = "v1.0.0"
PLUGIN_REPO = "https://github.com/ZXNPC/astrbot_plugin_wanna_play_game"

CACHE_CLEAR_PHRASE = "清空游戏检索缓存"
CACHE_CLEARED_MESSAGE = (
    "已清空游戏检索缓存。"
    "下次查询会重新请求 gamer520.com 与 online-fix.me，"
    "适合游戏资源更新后需要强制刷新结果时使用。"
)

# 自然语言入口：我想玩 X / 我要玩 X
NL_PATTERN = r"^(?:我想玩(?:一下)?|我要玩)\s*[:：]?\s*(.+?)[。！？!?.,，\s]*$"
NL_REGEX = re.compile(NL_PATTERN)
# AstrBot 会剥掉 wake_prefix（默认 "/"），所以指令正文可能是 "game xxx" 或 "/game xxx"
CMD_REGEX = re.compile(r"^(?:/)?game\s+(.+?)\s*$", re.IGNORECASE)


@register(PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, repo=PLUGIN_REPO)
class WannaPlayGameDownload(Star):
    def __init__(self, context: Context, config: Optional[AstrBotConfig] = None):
        super().__init__(context)
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        ttl_hours = float((config or {}).get("cache_ttl", 24))
        self.cache = SearchCache(data_dir / "cache.json", ttl_seconds=ttl_hours * 3600)
        self.service = GameDownloadService(config or {}, self.cache)

    @filter.command("game")
    async def game_command(self, event: AstrMessageEvent):
        """按 /game <游戏名> 查找下载信息，或按 /game 清空游戏检索缓存。"""
        text = (event.message_str or "").strip()
        m = CMD_REGEX.match(text)
        command_text = m.group(1).strip() if m else ""
        if not command_text:
            yield event.plain_result(
                "用法：/game 游戏名，例如 /game 赛博朋克2077；也可以直接发送「我想玩赛博朋克2077」。"
                "清空缓存请发送 /game 清空游戏检索缓存。"
            )
            return
        if command_text == CACHE_CLEAR_PHRASE:
            try:
                self.cache.clear()
            except Exception:
                logger.error(f"清空游戏检索缓存失败，异常堆栈：\n{traceback.format_exc()}")
                yield event.plain_result("清空游戏检索缓存失败，请稍后再试。")
                return
            yield event.plain_result(CACHE_CLEARED_MESSAGE)
            return
        yield event.plain_result(await self._search_and_reply(command_text))

    @filter.regex(NL_REGEX)
    async def game_natural_language(self, event: AstrMessageEvent):
        """匹配「我想玩 xxx」「我要玩 xxx」等自然语言表达。"""
        m = NL_REGEX.search((event.get_message_str() or "").strip())
        if not m:
            return
        game_name = m.group(1).strip()
        if not game_name:
            return
        yield event.plain_result(await self._search_and_reply(game_name))

    async def _search_and_reply(self, game_name: str) -> str:
        try:
            report = await self.service.search(game_name)
        except Exception:  # 兜底，避免插件因单个异常崩溃
            logger.error(f"游戏检索查询失败，异常堆栈：\n{traceback.format_exc()}")
            return "查询时出现错误，请稍后再试。"
        if not report.onlinefix_ok or not report.gamer520_ok:
            logger.warning(
                "游戏检索部分来源失败：onlinefix=%s gamer520=%s",
                report.onlinefix_error or "ok",
                report.gamer520_error or "ok",
            )
        return format_report(report)
