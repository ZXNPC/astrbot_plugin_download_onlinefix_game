# 0004 - gamer520.com 隐藏下载入口跟随与搜索分类过滤

## Status

Accepted

## Context

gamer520.com 的较新文章不再把百度/夸克/迅雷链接直接写进正文，而是通过侧栏
“立即获取/获取资源”按钮（`go-down`）提供：按钮调用 WordPress `admin-ajax`
接口拿到一个 `/go?post_id=...` 地址，页面再通过 `window.location` 跳到真实
网盘地址或另一个跳转文章。原实现只解析静态 `<a>` 与二维码 `data`，因此这类
文章会退化成“只有文章页链接”，例如搜索“幸福工厂”命中修改器文章时返回空链接。
另外，站点搜索会混入修改器、金手指、模拟器等非游戏本体分类；这些命中不应参与
“游戏本体”候选排序。

## Decision

- gamer520.com 搜索命中按 `.meta-category` 过滤非游戏本体分类（修改器、金手指、
  模拟器/模拟器合集、主题等），仍保留 PC PLAY、Switch 游戏、语言子分类等条目。
- 文章解析先静态解析 `.entry-content`/`article` 内的网盘 `<a>` 与二维码图片；
  若页面存在 `.go-down[data-id]`，再走 `user_down_ajax` → `/go` →
  `window.location` 链路解析真实地址。
- 链路目标可能是直接网盘地址，也可能是 `gamer520.com`/`gamers520.com` 的下一篇文章；
  后者最多递归 3 层并记录已访问 URL 防环。中间文章只扫描正文区，避免把导航栏网盘
  链接误当资源。
- 隐藏链路失败或没有可用链接时，仍保留文章页作为兜底入口；请求沿用同一 httpx client，
  保留站点 cookie，并使用反爬请求间隔。
- 缓存 key 增加解析版本，升级后不会继续命中旧格式缓存。

## Consequences

- 新文章的“立即获取”入口可以自动返回真实网盘地址；站点若更换按钮类名或接口字段，
  需要更新 `extract_download_gate`/`_request_gate_url`/`extract_redirect_target`。
- 修改器等非游戏分类不再出现在“游戏本体”结果中；若未来要支持修改器查询，需要新增独立用途。
- 每篇文章最多额外 3~4 个页面/接口请求，整体仍受每个来源 `request_timeout` 与缓存约束。
