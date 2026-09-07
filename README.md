# JEPA / 世界模型 每日论文卡

这是一个展示 ArXiv 论文精选的静态网站，支持搜索和独立详情页查看功能。项目会自动爬取 **JEPA（Joint-Embedding Predictive Architecture）、联合嵌入自监督、隐空间预测与世界模型**相关关键词的论文，并使用 AI 生成中文摘要。

fork 自 [infinity4b/daily-arxiv-vla](https://github.com/infinity4b/daily-arxiv-vla)，与其共用同一套流水线，仅主题不同；两站内容允许重叠（本站不排除 VLA / WAM 论文）。

## 功能特性

- 🤖 **自动爬取**: 每日自动从 ArXiv 爬取 JEPA / 联合嵌入 / 隐空间预测 / 世界模型相关最新论文（实测日均约 7 篇）
- 🧠 **AI摘要生成**: 使用ModelScope API自动为论文生成中文摘要
- 📚 从 `papers.md` 自动解析论文信息
- 🔍 实时搜索功能
- 📱 响应式设计，支持移动端
- 🎨 现代化暗色主题界面
- 📄 每篇论文生成独立静态详情页
- 🖼️ 自动从论文 HTML 提取首图，优先作为论文卡封面
- 🎭 当 HTML 原图不可直接下载时，自动使用 Playwright 截取页面里的首个 figure 作为兜底封面
- 💾 按 arXiv ID 独立记录论文页滚动进度
- ⏰ **定时任务**: 每日中午12点自动更新内容

## 本地开发

### 环境配置

首先需要配置环境变量：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
# MODELSCOPE_ACCESS_TOKEN=你的API密钥
```

可配置的环境变量：

**必需配置：**
- `MODELSCOPE_ACCESS_TOKEN`: ModelScope API 密钥

**可选配置：**
- `MODELSCOPE_BASE_URL`: API 基础 URL（默认：https://api-inference.modelscope.cn/v1/）
- `MODELSCOPE_MODEL`: 使用的模型（默认：deepseek-ai/DeepSeek-V3.2）
- `ARXIV_QUERY_KEYWORD`: 搜索关键词，支持 arXiv 查询语法（默认检索 JEPA / 联合嵌入 / 隐空间预测 / 世界模型；用 `ti:`/`abs:` 限定字段，避免只在 comments 或 journal-ref 里蹭词的命中）
- `ARXIV_INIT_RESULTS`: 初始化抓取数量（默认：120，约 2.5 周历史。GitHub Actions **未覆盖**此值，改 `scripts/arxiv_crawler.py` 里的默认值才会在 CI 生效）
- `ARXIV_DAILY_RESULTS`: 每日抓取数量（默认：20）
- `ARXIV_MAX_RETRIES`: arXiv 搜索重试次数（默认：3）
- `HTTP_MAX_RETRIES`: HTTP 请求重试次数（默认：3）
- `HTTP_TIMEOUT`: HTTP 请求超时时间（秒，默认：30）
- `HTML_MAX_CHARS`: HTML 内容最大字符数（默认：180000）
- `API_MAX_RETRIES`: API 调用重试次数（默认：3）
- `BATCH_WRITE_SIZE`: 批量写入大小，每生成 N 篇摘要写入一次文件（默认：5）
- `GA_MEASUREMENT_ID`: Google Analytics 4 的 Measurement ID（例如 `G-XXXXXXXXXX`，未配置时不加载 GA）

> ⚠️ **`.env` 对爬虫和站点构建不生效。** `scripts/arxiv_crawler.py` 与 `scripts/build_site.py` 都**没有**调用 `load_dotenv()`（全仓只有 `generate_summaries.py` 调用）。所以写在 `.env` 里的 `ARXIV_QUERY_KEYWORD`、`ARXIV_INIT_RESULTS`、`ARXIV_DAILY_RESULTS` 等**不会**被这两个脚本读取——`.env.example` 里的这些行只是文档。要改检索式或抓取量，请改 `scripts/arxiv_crawler.py` / `scripts/build_site.py` 的默认值，或在 shell / CI 里真正 `export`。这是 fork 自带的行为，本次未改动（改它会变更 CI 语义）。

### 爬取论文数据

```bash
# 初始化爬取（首次运行）
python scripts/arxiv_crawler.py

# 生成论文摘要
python scripts/generate_summaries.py

# 抓取论文首图（可选，GitHub Actions 会自动执行）
python scripts/fetch_paper_images.py --max-items 30

# 为剩余缺图论文生成 Playwright 截图兜底队列
python scripts/build_paper_image_fallback_queue.py --max-items 20

# 安装 Playwright 并执行截图兜底
npm install
npx playwright install chromium
npm run paper-image:fallbacks

# 将截图结果注册进 manifest
python scripts/register_paper_image_fallbacks.py
```

### 加深历史回填

`initialize()` 只在 `papers.md` 缺失时触发，之后每次运行都走 `run_daily()`。要把历史从 120 篇加深：

1. 临时把 `.github/workflows/deploy.yml` 里的 `ARXIV_DAILY_RESULTS` 每轮 +100
2. 推送触发一次运行，新入库论文的摘要会标记为「待生成」
3. 后续每日 cron 会继续消化未生成的摘要（`generate_summaries.py` 按 `BATCH_WRITE_SIZE=5` 增量写盘）
4. 达到想要的深度后把 `ARXIV_DAILY_RESULTS` 改回 `80`

**不要一次性设成几百篇**：单次运行要生成同等数量的摘要，可能撞上 GitHub Actions 的 6 小时硬限。作业被杀时「提交更改」步骤不会执行，`papers.md` 不会落盘，下一轮会重复同样的超时。

### 本地测试

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/test_topic_retarget.py -v
```

测试只覆盖两类真实失效模式：检索式在多副本间漂移（会让首页标题渲染成一坨查询语法）、品牌改造漏改。测试用 `ast` 提取 `arxiv_crawler.py` 的常量而非 import 它，因此**无需安装 `arxiv` 等运行时依赖**。

### 构建网站

```bash
python scripts/build_site.py
```

这将在 `site/` 目录下生成静态网站文件，包括首页、轻量数据文件、论文首图资源，以及每篇论文对应的独立静态详情页。

### Google Analytics 4

如需统计页面浏览、搜索和论文阅读行为，在本地构建前设置 Measurement ID：

```bash
export GA_MEASUREMENT_ID=G-XXXXXXXXXX
python scripts/build_site.py
```

未配置或格式不正确时，生成的页面不会加载 Google Analytics，也不会发送自定义统计事件。

验证时可以打开浏览器开发者工具的 **Network** 面板，搜索 `googletagmanager` 或 `collect`；GA4 后台的实时报告通常会有几分钟延迟。

> Google Analytics 会涉及 Cookie、隐私和数据跨境等合规问题。面向公众提供服务时，请根据所在地法规补充隐私说明，并在必要时增加用户同意机制。

### 本地预览

可以使用任何静态文件服务器预览网站：

```bash
# 使用Python内置服务器
cd site
python -m http.server 8000

# 或使用Node.js serve
npx serve site
```

## GitHub Pages 部署

### 0. 前置条件（首次部署必做）

1. **开启 Pages**：`Settings → Pages → Build and deployment → Source` 选 **GitHub Actions**。未开启时 `deploy` 作业的 `actions/deploy-pages` 会失败。
2. **配置 Secret**：`MODELSCOPE_ACCESS_TOKEN`（必需）。fork **不继承**上游 secrets，必须在本仓库重新配置。
3. **合并到默认分支**：cron 与 Pages 只认默认分支 `master`。在 `dev_jepa` 上的改动必须合入 `master` 才会开始每日更新。
4. **可选 GA4**：`Settings → Secrets and variables → Actions → Variables` 新增 `GA_MEASUREMENT_ID`。

### 1. 配置仓库

1. 确保你的仓库是公开的
2. 在仓库设置中启用 GitHub Pages
3. 选择 "GitHub Actions" 作为部署源

### 2. 配置环境变量

在仓库设置中添加以下Secret：
- `MODELSCOPE_ACCESS_TOKEN`: 你的ModelScope API密钥（必需）

如需启用 Google Analytics 4，在 `Settings → Secrets and variables → Actions → Variables` 中新增仓库变量 `GA_MEASUREMENT_ID`，值填写类似 `G-XXXXXXXXXX` 的 Measurement ID。当前工作流会自动把它注入网站构建；也兼容在 **Secrets** 中配置同名变量。不设置或格式不正确时不会加载 GA。Measurement ID 会出现在客户端 HTML 中，因此优先使用 **Variables** 即可。

**可选配置：** 如果需要修改默认配置（如搜索关键词、模型等），可以在 `.github/workflows/deploy.yml` 中添加环境变量：

```yaml
- name: 运行 arXiv 爬虫
  run: python scripts/arxiv_crawler.py
  env:
    MODELSCOPE_ACCESS_TOKEN: ${{ secrets.MODELSCOPE_ACCESS_TOKEN }}
    ARXIV_DAILY_RESULTS: "30"            # 可选：修改每日抓取数量
```

> ⚠️ **不要在 CI 里覆盖 `ARXIV_QUERY_KEYWORD`。** `build_site.py` 的 `get_arxiv_keyword_label()` 靠「环境变量是否逐字等于脚本默认查询串」来决定站点标题：任一处差一个空格，首页 H1、`<title>`、meta description、详情页与封面页标题就会全部变成 260 字符的查询语法。本仓库已刻意删除 CI 里的两处覆盖，改检索式请改 `scripts/arxiv_crawler.py` 与 `scripts/build_site.py` 的默认值（`tests/test_topic_retarget.py` 会强制两者逐字相等）。

默认配置：
- 搜索关键词：`(ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR abs:"latent world model")`
- 语料规模：实测 4513 篇（2026-09-07），日均新增约 7 篇，主类目白名单过滤后保留约 93%
- 初始回填：120 篇
- 每日抓取：80 篇（GitHub Actions 中覆盖代码默认值 20，提供约 11 天容错）
- 模型：deepseek-ai/DeepSeek-V3.2
- 其他配置见 `.env.example`

### 3. 自动部署

每次推送到 `master` 或 `main` 分支时，GitHub Actions 会自动：

1. 检出代码
2. 爬取新论文并生成摘要
3. 抓取最新论文的首图
4. 对无法直接下载原图的论文执行 Playwright 截图兜底
5. 运行构建脚本
6. 部署到 GitHub Pages

### 4. 定时任务

GitHub Actions 还会在每日中午12点自动执行：

1. 爬取ArXiv上的新论文
2. 为待生成的论文生成AI摘要
3. 抓取最新论文的首图
4. 对无法直接下载原图的论文执行 Playwright 截图兜底
5. 提交更改到仓库
6. 重新构建和部署网站

### 5. 访问网站

部署完成后，你的网站将在以下地址可访问：
```
https://你的用户名.github.io/仓库名
```

本仓库对应：`https://dreamskanda.github.io/daily-arxiv-jepa`

## 自定义配置

### 修改网站标题

编辑 `scripts/build_site.py` 中的 `generate_index_html()` 函数来修改网站标题。

## 项目结构

```
daily-arxiv-jepa/
├── papers.md                    # 论文数据源文件
├── requirements-dev.txt         # 测试依赖（pytest）
├── tests/
│   └── test_topic_retarget.py   # 检索式一致性与品牌回归测试
├── docs/superpowers/            # 设计文档与实施计划
├── scripts/
│   ├── arxiv_crawler.py         # ArXiv论文爬虫
│   ├── generate_summaries.py    # AI摘要生成脚本
│   ├── fetch_paper_images.py    # 从论文HTML提取首图
│   ├── build_paper_image_fallback_queue.py
│   ├── register_paper_image_fallbacks.py
│   ├── render_paper_image_fallbacks.mjs
│   ├── modern_ui.css            # 首页附加样式（含 hero 水印字母）
│   └── build_site.py            # 网站构建脚本
├── site/                        # 生成的静态网站
│   ├── index.html
│   ├── papers/
│   │   └── <arxiv-id>/
│   │       └── index.html
│   └── assets/
│       ├── paper-images/        # 下载到本地的论文首图
│       ├── paper-images.json    # 论文首图 manifest
│       ├── style.css
│       ├── analytics.js
│       ├── app.js
│       ├── paper.js
│       └── data.json
└── .github/
    └── workflows/
        └── deploy.yml           # GitHub Actions 部署配置
```

## 数据格式

`papers.md` 文件应包含以下格式的表格：

```markdown
| 日期 | 标题 | 链接 | 简要总结 |
|------|------|------|----------|
| 2024-01-01 | 论文标题 | https://arxiv.org/abs/xxx | <details><summary>点击查看</summary>详细内容...</details> |
```

## 技术栈

- **后端**: Python 3.9+
- **爬虫**: arxiv Python库
- **AI摘要**: ModelScope API
- **前端**: 原生 HTML/CSS/JavaScript
- **部署**: GitHub Pages + GitHub Actions
- **定时任务**: GitHub Actions Cron
- **字体**: Google Fonts (Inter)
