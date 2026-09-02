# 0001 - online-fix.me 抓取与链接解析策略

## Status

Accepted（2026-09-02 修订：站内下载入口不再单独外发，改为详情页点击指引）

## Context

插件需要从 online-fix.me 获取带联机补丁的游戏下载链接，从 gamer520.com 获取游戏本体链接。
online-fix.me 为俄语 DLE 站点且带有反爬保护；gamer520.com 为 WordPress，网盘链接常以二维码图片
形式给出（真实链接藏在图片 `data` 参数中）。

开发时参考了开源项目 [online-fix-helper](https://github.com/Leeanran2026/online-fix-helper)
的抓取思路：搜索 URL 与结果选择器、详情页下载优先级、随机 UA 与请求延迟、Cloudflare 挑战重试。
按用户要求，README 不体现该借鉴关系；归属记录仅保留在本 ADR 等开发文档中。

## Decision

- online-fix.me 搜索只把 `/games/` 分类命中作为候选，忽略 updates/DLC 等条目。
- online-fix.me 的服务器/Drive/Hosters 下载入口依赖站点 Referer（实测无 Referer 访问
  `uploads.online-fix.me` 返回 401），详情页外直接点击不可用；因此插件不单独外发这些地址，
  只返回详情页与可独立访问的网盘链接，并在回复中给出“停留在详情页内直接点击下载按钮”的指引。
- online-fix.me 解压密码固定为 `online-fix.me`。
- 反爬策略：随机 UA、请求间隔（online-fix.me 1~2s，gamer520.com 0.8~1.5s）、
  反爬挑战重试一次；每个来源受 `request_timeout` 总超时约束。
- 结果优先级：全量游戏 ＞ 仅游戏本体；gamer520.com 条目在无 online-fix.me 全量命中时标注
  “未找到对应的联机补丁”。
- 缓存按规范化游戏名分站保存解析结果（默认 24 小时）；升级后格式化层仍会过滤旧缓存中的站内直链。
- gamer520.com 网盘链接同时解析普通 `<a>` 链接与二维码图片 `data` 参数（百度/夸克等），
  并跟随“立即获取/获取资源”隐藏入口获取真实网盘地址；见 ADR-0004。

## Consequences

- 请求量受控：每来源每游戏最多 `result_count` 次详情/文章页请求，配合缓存降低被封风险。
- online-fix.me 独立补丁页（非 `/games/` 路径）不参与搜索，因此“本体 + 独立补丁”组合暂不产出；
  全量游戏条目内的 `Fix Repair` 文件仍可由用户从详情页进入目录后获取。
- 用户不会在聊天回复里直接点到返回 401 的服务站链接；代价是服务器直链不能脱离详情页单独使用，
  需要用户按回复中的指引操作。
- 站点改版时选择器可能失效，需更新 `app/online_fix.py`、`app/gamer520.py` 中的 `parse_*` 函数。
