# Amazon 搜索与数据提取 (Scrape.do)

使用 Scrape.do 结构化 Amazon API 进行产品搜索、产品详细信息（PDP）提取以及卖家（offers）提取。

## 前置环境配置

必须设置 `SCRAPEDO_API_TOKEN` 环境变量：

```bash
export SCRAPEDO_API_TOKEN="YOUR_SCRAPEDO_TOKEN"
```

如果未设置此变量，脚本将优雅报错并返回错误信息 JSON。

## 支持 marketplace
- 美国 (geocode: `us`)
- 英国 (geocode: `gb`)

---

## 1. 搜索 Amazon (searchResults)

搜索并返回结构化产品列表，包含：ASIN, Title, PDP URL, Thumbnail URL, Price, Rating, ReviewCount, isSponsored, Position, and Badge.

```bash
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py search "laptop stands" [geocode=us] [page=1]
```

## 2. 产品详情 (pdp)

抓取商品的核心详细数据，包含：ASIN, is_sponsored, Brand, Title, URL, Thumbnail, Rating, Price, is_prime, Description, category best_seller_rankings, and technical_details.

```bash
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py pdp "B0C7BKZ883" [geocode=us]
```

## 3. 卖家 Offers 信息 (offer-listing)

获取当前产品的所有商家报价（含 FBA/FBM 标识、merchantName、shipsFrom、以及是否是 Buy Box 获得者 `isBuyBoxWinner` 字段）。

```bash
python3 /app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py offers "B0DGJ7HYG1" [geocode=us]
```

---

## 4. 两层自动化调研流程

1. **第一层 (Amazon 探索):**
   - 运行 `search` 获取 ASIN 与产品。
   - 针对重点产品运行 `pdp` 拿到品牌名称。
   - 运行 `offers` 获取卖家的 `merchantName` 和 `shipsFrom` 信息。若卖家名称不匹配品牌名称，则判定可能为第三方 reseller 零售商。
2. **第二层 (Agent-Reach 深入):**
   - 过滤出拥有品牌的真实商家。
   - 启动 `agent-reach` 传统渠道（如 Jina Reader 读官网，Exa 搜招聘，LinkedIn 找决策人）来组装完整的 B2B 意向客户档案。
