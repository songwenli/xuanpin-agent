# 礼服选品 Agent（第一阶段）

当前版本按 `prom dress` 关键词或 Prom 专用分类抓取规格中的全部 A/B 类站点，
并提供统一数据模型、SQLite 存储、基于排名/评论/收藏的简单评分，以及
Markdown/JSON 日报。每个站点均为独立模块，单站失败不会中断其他站点。

## 使用

```bash
python -m venv .venv
pip install -r requirements.txt
python -m dress_agent --config config.yaml
```

## 网页端

安装依赖后，在项目根目录运行：

```bash
python -m webapp
```

Windows 也可以直接运行（会自动寻找项目虚拟环境或 Codex Python）：

```powershell
.\start_web.ps1
```

然后打开 `http://127.0.0.1:8000`。服务监听所有本机网卡，同一局域网中的
同事可以使用电脑的局域网 IP 加端口 `8000` 访问；Windows 防火墙需允许该端口。
网页支持：

- 一键启动抓取任务并查看运行状态。
- 浏览 SQLite 中的评分商品和原站链接。
- 查看本地生成的历史 Markdown 日报。
- 访问 `http://127.0.0.1:8000/docs` 调试 REST API。

网页服务当前监听本机全部网卡，局域网访问由 Windows 防火墙控制。公网发布应
通过 Tunnel 或反向代理完成，不要在路由器上直接映射端口。

## 临时公网发布

先保持 `start_web.ps1` 的窗口运行，再打开另一个 PowerShell：

```powershell
.\start_public.ps1
```

脚本会输出随机的 `https://*.trycloudflare.com` 公网地址。该地址仅适合测试，
没有 SLA；电脑、Agent 窗口或 Tunnel 窗口关闭后地址会失效。

HTTP 代理由 `requests` 自动读取 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。
输出数据库默认为 `data/products.db`，日报默认为 `reports/YYYY-MM-DD.md` 和
`reports/YYYY-MM-DD.json`。运行调度应交给 cron 或 n8n。

## 后续 TODO

- 接入规格中的 C/D 类平台与官方 API。
- 增加图片 embedding 相似款聚类与跨平台计数。
- 扩展完整权重（Best Seller、新款、跨平台信号）。
- 对需要 JavaScript 渲染的站点增加 Playwright 适配器。
