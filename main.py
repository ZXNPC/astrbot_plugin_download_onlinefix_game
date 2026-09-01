"""AstrBot 插件：根据游戏名称从 online-fix.me 与 gamer520.com 查找下载链接。"""

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

PLUGIN_NAME = "astrbot_plugin_download_onlinefix_game"
PLUGIN_AUTHOR = "ZXNPC"
PLUGIN_DESC = "根据游戏名称从 online-fix.me 与 gamer520.com 查找带联机补丁的游戏下载链接"
PLUGIN_VERSION = "v0.9.0"
PLUGIN_REPO = "https://github.com/ZXNPC/astrbot_plugin_download_onlinefix_game"

# 自然语言入口：我想玩 X / 我要玩 X / 帮我找 X
NL_PATTERN = r"^(?:我想玩(?:一下)?|我要玩|帮我(?:找|查)(?:一下)?)\s*[:：]?\s*(.+?)[。！？!?.,，\s]*$"
NL_REGEX = re.compile(NL_PATTERN)
# AstrBot 会剥掉 wake_prefix（默认 "/"），所以指令正文可能是 "game xxx" 或 "/game xxx"
CMD_REGEX = re.compile(r"^(?:/)?game\s+(.+?)\s*$", re.IGNORECASE)


@register(PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, repo=PLUGIN_REPO)
class OnlineFixGameDownload(Star):
    def __init__(self, context: Context, config: Optional[AstrBotConfig] = None):
        super().__init__(context)
        self.config = config if config is not None else {}
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        ttl_hours = float(self.config.get("cache_ttl", 24))
        self.cache = SearchCache(data_dir / "cache.json", ttl_seconds=ttl_hours * 3600)
        self.service = GameDownloadService(self.config, self.cache)
        self._maybe_clear_cache()

    def _maybe_clear_cache(self) -> None:
        """按配置手动清空缓存；清空后自动把 clear_cache 复位为 false。"""
        try:
            if not self.config.get("clear_cache", False):
                return
            self.cache.clear()
            self.config["clear_cache"] = False
            save = getattr(self.config, "save_config", None)
            if callable(save):
                save()
            logger.info("已按配置清空搜索/名称缓存，并将 clear_cache 复位为 false")
        except Exception:
            logger.error(f"清空缓存失败，异常堆栈：\n{traceback.format_exc()}")

    @filter.command("game")
    async def game_command(self, event: AstrMessageEvent):
        """按 /game <游戏名> 查找下载链接。"""
        text = (event.message_str or "").strip()
        m = CMD_REGEX.match(text)
        game_name = m.group(1).strip() if m else ""
        if not game_name:
            yield event.plain_result(
                "用法：/game 游戏名，例如 /game 赛博朋克2077；也可以直接发送「我想玩赛博朋克2077」。"
            )
            return
        yield event.plain_result(await self._search_and_reply(game_name))

    @filter.regex(NL_REGEX)
    async def game_natural_language(self, event: AstrMessageEvent):
        """匹配「我想玩 xxx」等自然语言表达。"""
        m = NL_REGEX.search((event.get_message_str() or "").strip())
        if not m:
            return
        game_name = m.group(1).strip()
        if not game_name:
            return
        yield event.plain_result(await self._search_and_reply(game_name))

    async def _search_and_reply(self, game_name: str) -> str:
        self._maybe_clear_cache()
        try:
            report = await self.service.search(game_name)
        except Exception:  # 兜底，避免插件因单个异常崩溃
            logger.error(f"游戏下载查询失败，异常堆栈：\n{traceback.format_exc()}")
            return "查询时出现错误，请稍后再试。"
        if not report.onlinefix_ok or not report.gamer520_ok:
            logger.warning(
                "游戏下载部分来源失败：onlinefix=%s gamer520=%s",
                report.onlinefix_error or "ok",
                report.gamer520_error or "ok",
            )
        return format_report(report)