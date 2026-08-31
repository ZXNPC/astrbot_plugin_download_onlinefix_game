"""AstrBot 插件：根据游戏名称从 online-fix.me 与 gamer520.com 查找下载链接。"""

import re

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from app.cache import SearchCache
from app.formatter import format_report
from app.service import GameDownloadService

PLUGIN_NAME = "astrbot_plugin_download_onlinefix_game"
PLUGIN_AUTHOR = "your_name"
PLUGIN_DESC = "根据游戏名称从 online-fix.me 与 gamer520.com 查找带联机补丁的游戏下载链接"
PLUGIN_VERSION = "v1.0.0"
PLUGIN_REPO = ""

# 自然语言入口：我想玩 X / 我要玩 X / 帮我找 X
NL_PATTERN = r"^(?:我想玩(?:一下)?|我要玩|帮我(?:找|查)(?:一下)?)\s*[:：]?\s*(.+?)[。！？!?.,，\s]*$"
NL_REGEX = re.compile(NL_PATTERN)
CMD_REGEX = re.compile(r"^/game\s+(.+?)\s*$", re.IGNORECASE)


@register(PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, repo=PLUGIN_REPO)
class OnlineFixGameDownload(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        data_dir = get_astrbot_data_path() / "plugin_data" / PLUGIN_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        ttl_hours = float(config.get("cache_ttl", 24))
        self.cache = SearchCache(data_dir / "cache.json", ttl_hours=ttl_hours * 3600)
        self.service = GameDownloadService(config, self.cache)

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
        try:
            report = await self.service.search(game_name)
        except Exception as exc:  # 兜底，避免插件因单个异常崩溃
            logger.error(f"游戏下载查询失败: {exc}")
            return "查询时出现错误，请稍后再试。"
        return format_report(report)
