\# 礼服选品Agent — 项目规格



\## 一、项目目标



构建一个每日自动运行的选品Agent，监控以下电商/社交平台的礼服类目商品，

基于销量排名、点赞数、收藏数、评论数、上新时间等信号，

输出「今日值得打板/跟款」的候选款式清单，供选品团队人工复核。



\## 二、数据源分类（不同类型网站用不同抓取策略）



\### A类：DTC快时尚礼服站（有明确Best Seller/Trending排序）

\- shopamericanthreads.com

\- ohpolly.com

\- meshki.us

\- princesspolly.com

\- revolve.com

\- lulus.com

\- windsorstore.com

\- ever-pretty.com



\### B类：礼服/婚纱专营站（伴娘裙/婚纱/晚礼服，SKU结构更复杂）

\- stacees.com

\- jjshouse.com

\- promgirl.com

\- azazie.com

\- newyorkdress.com

\- sherrihill.com

\- macduggal.com

\- couturecandy.com

\- babyboofashion.com

\- thedressoutlet.com

\- simplydresses.com



\### C类：综合电商平台（需按类目筛选+按销量/评论数排序）

\- amazon.com（Women's Dresses类目，用Best Sellers/评论数排序）

\- ebay.com（用Best Match/最多关注人数排序）



\### D类：社交趋势信号源（用于交叉验证"正在被讨论/收藏"的款式）

\- pinterest.com（搜索"prom dress 2026"等关键词，抓取Pin的Save数）

\- tiktok.com（#promdress #eveningdress 等话题下的热门视频，提取画面中的服装特征）



\## 三、每个站点需要提取的字段



统一Schema（不是每个字段都能从每个站点拿到，缺失字段留空即可）：



```json

{

&#x20; "source\_site": "string",

&#x20; "source\_category": "A/B/C/D",

&#x20; "product\_url": "string",

&#x20; "product\_title": "string",

&#x20; "product\_image\_urls": \["string"],

&#x20; "price": "number",

&#x20; "currency": "string",

&#x20; "rank\_position": "number（该站点分类页/排行榜中的位次）",

&#x20; "review\_count": "number",

&#x20; "review\_rating": "number",

&#x20; "like\_or\_save\_count": "number（点赞/收藏/关注人数，字段含义按平台注明）",

&#x20; "is\_bestseller\_tag": "boolean（页面是否有Best Seller/Trending等官方标签）",

&#x20; "is\_new\_arrival": "boolean",

&#x20; "color": "string",

&#x20; "style\_tags": \["string"]（如 mermaid/a-line/off-shoulder/sequin 等）,

&#x20; "scraped\_at": "datetime"

}

```



\## 四、技术架构



\- 语言：Python 3.11+

\- 抓取层：

&#x20; - A/B类站点优先用 requests + BeautifulSoup（大部分是服务端渲染的电商模板）

&#x20; - 如遇到JS渲染内容（无限滚动/动态加载排序），用 Playwright headless

&#x20; - C类（Amazon/eBay）反爬较强，优先考虑官方API（Amazon Product Advertising API / eBay Browse API）而不是硬抓页面，避免被封IP

&#x20; - D类（Pinterest/TikTok）优先用官方开放API（Pinterest API的Trends/Search端点，

&#x20;   TikTok Creative Center的公开趋势数据），不做登录态模拟抓取

\- 存储：SQLite（本地，简单）或 PostgreSQL（如果后续要接入现有Pinecone/数据管道）

\- 去重与相似款聚类：

&#x20; - 用图片embedding（CLIP或类似模型）做款式相似度聚类，

&#x20;   避免同一款式在多个站点被重复统计为"不同候选"

&#x20; - 相似度阈值设为可配置参数

\- 调度：设计成可以被外部cron/n8n通过命令行或HTTP调用的独立脚本，

&#x20; 不要在脚本内部写死定时逻辑（调度交给n8n处理）

\- 代理：脚本需要支持通过环境变量配置HTTP\_PROXY/HTTPS\_PROXY

&#x20; （本地环境用Clash代理，端口7890）



\## 五、打分与排序逻辑



给每个候选款式计算一个「打板优先级得分」，公式设计为可调权重：

score =
w1 * normalize(rank_position, 反向) # 排名越靠前分越高

w2 * normalize(review_count)
w3 * normalize(like_or_save_count)
w4 * (is_bestseller_tag ? 1 : 0)
w5 * (is_new_arrival ? 0.5 : 0) # 新款给予一定加分，避免只推荐"老爆款"
w6 * cross_platform_count # 同一款式在几个不同站点/平台都出现，
# 说明是跨平台的真实趋势，加分

初始权重建议：w1=0.25, w2=0.15, w3=0.25, w4=0.15, w5=0.1, w6=0.1
权重写入配置文件（config.yaml），不要硬编码，方便后续根据实际效果调整。

## 六、输出格式

每日生成一份报告，格式为Markdown + 一份结构化JSON：

- Markdown报告：按打分从高到低列出Top 30候选款式，
  每个款式附：缩略图、来源站点、价格、关键数据、评分理由（一句话说明为什么入选）
- JSON：完整数据，供后续接入Shopify选品系统或人工筛选工具使用
- 报告输出到本地目录 `./reports/YYYY-MM-DD.md`，方便后续用n8n读取并推送到Telegram

## 七、合规与稳健性要求

- 严格遵守各站点的robots.txt，对明确禁止抓取的路径不抓取
- 请求间隔加随机延迟（1-3秒），避免对目标站点造成压力或触发封禁
- 每个站点的抓取逻辑独立封装成单独模块（scrapers/站点名.py），
  某一个站点抓取失败不应影响其他站点的正常运行（try/except隔离）
- 记录详细日志，抓取失败的站点/原因要能追溯
- Amazon/eBay类目如果官方API申请有门槛，先做架构预留，
  用mock数据跑通整体流程，API权限下来后再接入

## 八、第一阶段交付范围（不要一次性做完整系统）

先完成：
1. 项目骨架（目录结构、config.yaml、requirements.txt）
2. A类里选2个站点（建议先做 lulus.com 和 princesspolly.com，
   页面结构相对标准）的完整抓取模块
3. 统一Schema的存储层（SQLite）
4. 简单打分逻辑（先用w1/w2/w3三个字段，其余站点接入后再扩展）
5. Markdown报告生成

跑通这个最小闭环后，再逐个站点扩展。
