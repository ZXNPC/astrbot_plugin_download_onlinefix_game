# 0002 - Steam 名称解析取代 Google 翻译

## Status

Accepted

## Context

online-fix.me 搜索需要英文游戏名，而游戏请求通常是中文名。原实现用 Google 免费翻译端点
（translate.googleapis.com）做中文→英文翻译，但直译往往得不到官方英文名：
例如「渔力全开」被直译为无关结果，而 Steam 商店上该游戏的官方英文名是 "How to Fish"。

实测验证（2026-09-01）：`store.steampowered.com/api/storesearch` 用中文关键词 + `l=schinese`
能命中（渔力全开 → appid 4001890），再用 `api/appdetails?appids=<id>&l=english` 可取回官方
英文名；而 `l=english` 直接搜中文关键词为 0 命中，因此必须两步查询。

## Decision

- 中文游戏名经 Steam 商店两步查询解析英文名：storesearch（`l=schinese&cc=cn`）→
  取第一个 `type=app` 且中文名与查询词有 CJK 重叠的命中；若命中名称已不含中文则直接使用，
  否则 appdetails（`l=english&cc=us`）取官方英文名。
- 解析失败（无命中 / 网络错误 / 非 Steam 游戏）时退回原中文词继续搜索，
  并在回复末尾提示用户改用 `/game <英文名>` 重新搜索。
- 只缓存解析成功的英文名（缓存段 `names`，按原文 key，TTL 与搜索结果一致）；
  失败不缓存，以便下一次查询可立即重试。
- 移除 Google 翻译路线及 `translate_enabled`、`proxy` 两个配置项；Steam 直连，
  若后续用户反馈存在卡顿，再评估是否恢复代理支持。
- 新增 `clear_cache` 配置项：设为 true 后，在下次查询时清空全部缓存（search + names）
  并自动复位为 false（通过 AstrBotConfig 内存回写 + `save_config()` 持久化）。
- 缓存文件内原 `translate` 段更名为 `names`，加载时懒迁移旧条目。
- 回复中仅单个候选（只有游戏本体或只有全量游戏）时不使用序号标识。

## Consequences

- 非 Steam 游戏（或 Steam 无中文名条目）无法解析英文名，online-fix.me 命中率下降，
  但会给出可操作的提示，用户可改用 `/game <英文名>`。
- 每个含中文的查询最多增加 2 个 Steam 请求；解析结果按名称缓存，重复查询不重复请求。
- Steam 的区域与可用性（cc=cn）会影响个别游戏的可见性；本版本不做代理，
  如遇卡顿由用户反馈后按本 ADR 的基线评估恢复代理。
- 移除翻译与代理后配置面更小；`clear_cache` 让用户可在 24 小时缓存窗口内手动强制刷新。