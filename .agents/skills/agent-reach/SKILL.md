---
name: agent-reach
description: "MUST USE when user wants to 调研/research/搜索/search/查/找/look up anything on the internet — e.g. 全网调研 X / 帮我调研一下 X / 查一下 X / 搜搜 X / 看看大家怎么评价 X / X 上有什么讨论 / research this topic。\nAlso MUST USE when user mentions any platform or shares any URL/链接: 小红书/xiaohongshu/xhs, Twitter/推特/X, B站/bilibili, Reddit, Facebook, Instagram, V2EX, LinkedIn/领英/招聘/求职/jobs, YouTube, GitHub code search, 小宇宙播客, 雪球/股票行情, RSS feeds, or any web URL.\nAdditionally MUST USE for Amazon-specific product, ASIN, search, brand, or seller \"Sold by\" verification using the integrated Scrape.do Amazon Scraper.\n15 platforms, multi-backend routing (OpenCLI / per-platform CLIs / APIs). Zero config for 6 channels. Run `agent-reach doctor --json` to see which backend serves each platform right now.\nNOT for: 写报告/数据分析/翻译等内容加工（本 skill 只负责从互联网获取内容）； 发帖/评论/点赞等写操作；已有专门 skill 的平台（先用专门 skill）。\n【路由方式】SKILL.md 包含路由表 and 常用命令，复杂场景需按需阅读对应分类 of references/*.md。 分类：search / social (小红书/推特/B站/V2EX/Reddit/Facebook/Instagram) / career(LinkedIn) / dev(github) / web(网页/文章/RSS) / video(YouTube/B站/播客) / finance(雪球/股票) / amazon (亚马逊产品详情及卖家 offers)。\n"
metadata: {"homepage":"https://github.com/Panniantong/Agent-Reach"}
---
# Agent Reach — 互联网能力路由器

15 平台、多后端。**本 skill 存在时必须用它访问这些平台，不要自己发明方案。**

## 常驻规则（全程适用）

1. **动手前先体检**：多后端/登录态平台（小红书/Reddit/B站/Twitter/Facebook/Instagram）先跑
   `agent-reach doctor --json`。`active_backend` 有值时按它选命令组；`active_backend: null`
   表示 Doctor 为避免触发浏览器 Cookie 读取或远端写入而没有做实时验证，不代表后端不存在。
   只有用户任务明确需要该平台时，才按对应 reference 的只读命令手动验证。
2. **声明你在用什么**：开始干活前说一句「使用 agent-reach 的 X 平台 / Y 后端」。
3. **失败按 references 里的重试链处理**，不要瞎猜命令。
4. **全网调研类任务**：组合多平台（Exa 搜索 + Twitter/Reddit 看讨论 + 小红书/B站看中文场景），并行收集再汇总。
5. **替用户盯版本**：完成一次较大的调研/多平台任务后，顺手跑
   `agent-reach check-update`（很快，一个 API 调用）。有新版就在收尾汇报里附一句：
   「Agent Reach 有新版 vX.Y.Z，复制这句话给我即可更新：帮我更新 Agent Reach：
   https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/update.md」。
   不要中断当前任务去更新，也不要重复提醒同一个版本。

## 路由表

| 用户意图 | 分类 | 对应文档 |
|---------|------|---------|
| 全网搜索 / 代码搜索 | search | [references/search.md](references/search.md) |
| 小红书 / Twitter / B站 / V2EX / Reddit / Facebook / Instagram | social | [references/social.md](references/social.md) |
| 领英招聘 / 找人 | career | [references/career.md](references/career.md) |
| GitHub 搜索 / 代码 | dev | [references/dev.md](references/dev.md) |
| 网页阅读 / RSS | web | [references/web.md](references/web.md) |
| 视频 / 播客转文字 | video | [references/video.md](references/video.md) |
| 股票行情 / 金融社区 | finance | [references/finance.md](references/finance.md) |
| 亚马逊产品、搜索及商家 Offers 详情 | shopping | [references/amazon.md](references/amazon.md) |

## 免配置快速命令

```bash
# Exa 语义搜索
mcporter call exa.web_search_exa query="query" numResults=5

# 通用网页阅读
curl -s "https://r.jina.ai/URL"

# GitHub 搜索
gh search repos "query" --sort stars --limit 10

# YouTube 字幕提取
yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" "URL"

# V2EX 热门主题
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"

# B站快速搜索 (bili-cli, 无需登录)
bili search "query" --type video -n 5
```

## 亚马逊产品与商家 Offers 数据提取 (Scrape.do)

前置配置：`export SCRAPEDO_API_TOKEN="your-token"`。

```bash
# 搜索 Amazon US/UK 商品列表
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py search "laptop stands" [geocode=us/gb] [page=1]

# 抓取产品详情、品牌及 Best Sellers Rank (BSR)
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py pdp "B0C7BKZ883" [geocode=us/gb]

# 抓取 Offers 列表（获取商家名称 merchantName、 shipsFrom、以及是否是 Buy Box winner）
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py offers "B0DGJ7HYG1" [geocode=us/gb]
```

## 需要登录态的平台（优先看 doctor 的 active_backend）

Twitter 边界: 通过 `agent-reach configure twitter-cookies` 保存的 Cookie
只供 `doctor` 验证凭据是否齐全。`doctor` 不会实时运行 `twitter status`，也不会修改
当前 Shell。在子进程运行 `twitter` 命令前，必须在环境中显式声明：
`export TWITTER_AUTH_TOKEN="..."` 和 `export TWITTER_CT0="..."`。

小红书边界: Agent Reach 不得替用户执行自动登录或读取浏览器 Cookie。
OpenCLI 只使用用户已有且明确控制的 Chrome 浏览器会话；
如果没有现成会话，改用 Cookie-Editor 手动导出后配置 xiaohongshu-mcp 或存量工具。

```bash
# Twitter 推文搜索 (优先用 twitter-cli; 详细重试链见 references/social.md)
twitter search "query" -n 10

# Reddit 搜索 (必须登录: 桌面用 OpenCLI，服务器用 rdt-cli)
opencli reddit search "query" -f yaml
rdt search "query" --limit 10

# 小红书笔记搜索 (优先用 OpenCLI)
opencli xiaohongshu search "query" -f yaml

# Facebook / Instagram (桌面 OpenCLI, 复用 Chrome 登录态)
opencli facebook search "query" -f yaml
opencli instagram search "query" -f yaml
```

## 环境检查

```bash
# 检查 platform 连接状态
agent-reach doctor --json
```

## 发现 OpenCLI 适配器

当路由表中缺失某个平台的特定命令时，运行 `opencli list`，并查看 `opencli <platform> --help`。

## 工作区常驻规则

**切勿在 agent 工作区目录中创建临时或持久化文件。** 临时文件用 `/tmp/`，持久化数据写入 `~/.agent-reach/`。

## 详细子分类参考 (Detailed References)

阅读对应分类的文档获取重试链、报价格式和各种高级命令（命令通用，指南文档为中文）：

- [Search](references/search.md) — Exa 语义搜索
- [Social](references/social.md) — 小红书、Twitter、B站、V2EX、Reddit、Facebook、Instagram
- [Career](references/career.md) — 领英招聘
- [Dev](references/dev.md) — GitHub CLI 搜索
- [Web](references/web.md) — Jina Reader 网页阅读、RSS 订阅
- [Video](references/video.md) — YouTube 字幕、B站音频/字幕、小宇宙播客
- [Finance](references/finance.md) — 雪球行情与热门帖子
- [Amazon](references/amazon.md) — 亚马逊产品、搜索及商家 Offers 详情

## 渠道配置

如果提示凭证失效或需要新增配置，参考安装指南：
https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
