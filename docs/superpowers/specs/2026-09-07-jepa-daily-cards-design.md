# JEPA 每日论文卡 —— 设计文档

**日期：** 2026-09-07
**仓库：** `DreamSkanda/daily-arxiv-jepa`（fork 自 `infinity4b/daily-arxiv-vla`，默认分支 `master`，开发分支 `dev_jepa`）
**目标：** 把 daily-arxiv-vla 的"每日 arXiv 论文卡"流水线原样复用到 JEPA 主题上，产出 `https://dreamskanda.github.io/daily-arxiv-jepa/`。

---

## 1. 核心判断：这是一次主题重定向，不是功能开发

fork 带来的流水线已完整可用（爬取 → AI 摘要 → 首图抓取 → Playwright 截图兜底 → 静态站构建 → Pages 部署 → 每日 cron）。经与需求方确认，本次**不新增任何业务逻辑**，改动面为：检索式字符串、品牌文案、仓库元数据、初始回填规模、CI 环境变量删减、数据重置、README 重写。

> 设计过程中曾提出三项"必需修复"（新增 `SITE_TOPIC_LABEL`、修 init/daily 误判、新增 `SUMMARY_MAX_ITEMS`），经实测全部证伪，降级为配置项或流程步骤，详见 §5。

---

## 2. 证据基础（2026-09-07 实测 arXiv API，`export.arxiv.org`）

所有检索决策均由实测量支撑，非估算。

### 2.1 语料量

| 检索式 | 语料量 | 判断 |
| --- | --- | --- |
| `all:"JEPA"` | 417 | 精度高 |
| + `all:"Joint Embedding Predictive Architecture"` | 439 | 补 22 篇不用缩写的 |
| + `joint embedding self-supervised` | 447 | 仅 +8，收益极小 |
| + `latent world model` | 567 | +128，抽样多为 Dreamer 类规划/驾驶 |
| `all:"world model"` 单独 | 3689 | 世界模型主体 |
| `all:"world models"` 单独 | 3715 | 与单数几乎同集合（并集 3717），说明 arXiv **不做词干化**，两种形态都要写 |
| `all:"joint embedding"` | 758 | 联合嵌入自监督 |
| `all:"latent world model"` | 156 | 隐空间世界模型 |
| **定稿式（§3）** | **4513** | 采纳 |

### 2.2 排除 VLA/WAM 的两种写法（最终**不采用**，需求方决定不排除）

| 写法 | 语料 | 被排除 | 特征 |
| --- | --- | --- | --- |
| `ANDNOT all:(...)` | 4178 | 275 | 与 VLA 站零重叠，但误杀仅引用对比过 VLA 的世界模型论文（GIFT、Motus2、PAVE） |
| `ANDNOT ti:(...)` | 4315 | 137 | 被排除样本全是标题即身份的 VLA/WAM（SV-WAM、REFACTOR-VLA、ZimaBlue、GameWAM、GeoWAM、Hydra、ForeTime-VLA），但会误杀 `WA-JEPA`（JEPA 论文，标题含 World-Action） |

### 2.3 "隐空间"口径（决定性）

| 增量词 | 增量语料 | 抽样结论 |
| --- | --- | --- |
| `abs:"latent space"` | **+9955**（4452 → 14407，3.2×） | **拒绝**。全是潜空间生成模型：扩散音乐生成、Brain2Speech、3D 编辑、Flow Matching 修复。几乎所有生成模型论文都写 "latent space" |
| `abs:"latent dynamics"` | +450 | **拒绝**。16 篇样本仅 2–3 篇相关，主体是动力系统/降阶建模社区术语：math.DS 拓扑方法、physics.flu-dyn Rayleigh–Taylor ROM、math.NA autoencoder-ROM、stat.ME 高维时序、cs.CE PDE 加速、Neural ODE |
| `abs:"latent prediction"` | +61 | **采纳**。正是"在表示空间预测"的 JEPA 内核且天然跨领域：EEG-VID、DINO-A 音频自蒸馏、ω-0、Hierarchical Latent Prediction for LM、ARIMA 符号音乐、Structured 4D Latent Predictive Model、OLIVE 语音 SSL |

### 2.4 定稿式的产量与精度

以下数字由**从 §3 逐字提取的检索式**直接打 API 复测得到（非从相邻变体推断），实测 `totalResults = 4513`，与 §2.1 一致：

- 近 120 篇月份分布：2026-09（前 6 天）**41** 篇、2026-08 **79** 篇 → **日均约 7 篇，月产约 200–250 篇**
- 主类目分布：CORE 6 类 **112/120 = 93%**；其余 7% 为 math.ST、econ.GN、q-bio.QM、cs.IR、eess.IV、cs.SD、astro-ph.CO、cs.DC 各 1
- 强概念词命中 114/120 = 95%，真噪声约 2–4%，且**恰好落在现有类目白名单之外**

> 说明：§2.4 早期草稿引用的是 V1 变体（4452，不含 `latent prediction`）的 40/80 分布；定稿式加入 `abs:"latent prediction"`（+61 篇）后复测为 41/79，CORE 占比不变，差异在测量误差内。

### 2.5 首页负载（fork 从未达到的量级）

实测当前 VLA 站 1917 篇 → `data.json` **3.93 MB**（indent=2，2.1 KB/篇；compact 3.60 MB）。按每月 230 篇外推：12 个月后约 4.8 MB，20 个月后约 8 MB。见 §7 推迟项。

---

## 3. 定稿检索式

**逐字字符串**（两处 Python 默认值必须完全一致，见 §6 测试 1）：

```
(ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR abs:"latent world model")
```

设计要点：

- **不排除 VLA/WAM**。需求方明确：只要与 JEPA / 隐空间 / 联合嵌入 / 世界模型相关就收，与 daily-arxiv-vla 内容重叠可接受。
- **用 `ti:` / `abs:` 而非 `all:`**：`all:` 会命中仅出现在 comments / journal-ref / 类目里的蹭词论文。收紧后语料 4518 → 4178（含排除项时），精度提升。
- **"world model" 与 "world models" 都写**：arXiv 不做词干化（§2.1 实测）。
- **`abs:"latent world model"` 在逻辑上被 `abs:"world model"` 蕴含**，保留是为了让检索意图在字符串里自解释，不产生额外语料。
- 覆盖四类：JEPA 本体（含 I-JEPA / V-JEPA / LeJEPA 等变体，因 `JEPA` 为独立 token）、联合嵌入自监督、隐空间预测、世界模型。

---

## 4. 类目策略：不动

沿用 `ArxivCollector._ALLOWED_PRIMARY_CATEGORIES = {cs.CV, cs.AI, cs.CL, cs.LG, cs.MM, cs.RO}`。

- **理由**：实测它挡掉的 7% 正是需求方想丢的蹭词论文（math.ST 因果、econ.GN Dutch Books、astro-ph.CO、quant-ph）。
- **已知代价**：跨领域 JEPA 进不来 —— `MR-JEPA`（eess.IV，心脏 MRI）、`CoJEPA`（cs.SD，音乐）、`LeJEPA`（q-bio.QM，分子图）。此行为与 daily-arxiv-vla 一致，符合"同样的事"。记入 §7 推迟项。
- **不做**概念词闸门、不做 EXT 分层、不做 LLM 相关性复判。曾评估的三层过滤方案（CORE 直通 / EXT 需命中概念词 / OUT 丢弃）与 LLM 闸门方案均被否决：前者为 4% 跨领域内容引入约 150 行新逻辑，后者为消除 2–4% 噪声使 CI 时长翻倍且引入非确定性。

---

## 5. 数据重置与回填

### 5.1 重置

`git rm papers.md` —— 移除 1917 行 / 7 MB 的 VLA 语料。

**可逆性**：删除不等于丢失。VLA 语料完整保留在 git 历史中（当前唯一提交 `cc76072`），任何时候可用 `git show cc76072:papers.md > /tmp/papers-vla.md` 取回，因此**不需要**额外生成 `papers-vla-archive.md` 归档文件。

**关键：必须整文件删除，不能清空成只剩表头。** `arxiv_crawler.py` 的运行模式判断是：

```python
if os.path.exists(papers_md) and os.path.getsize(papers_md) > 0:
    count = collector.run_daily()      # 只抓 ARXIV_DAILY_RESULTS 篇
else:
    count = collector.initialize()     # 抓 ARXIV_INIT_RESULTS 篇
```

而 `_ensure_md_header()` 写入的表头本身就让文件非空，所以"清空成表头"会误判为 daily 模式，首跑只回填 80 篇。**整文件删除后走 `initialize()`，无需改这段逻辑。**

### 5.2 回填规模

| 变量 | 位置 | 现值 | 新值 | 理由 |
| --- | --- | --- | --- | --- |
| `ARXIV_INIT_RESULTS` | `arxiv_crawler.py:47` 代码默认值 | `"500"` | **`"120"`** | CI **未设置**该变量，首跑读的是代码默认值，所以必须改代码而非只改 `.env.example`。120 篇 ≈ 2.5 周历史；首跑摘要生成 120 × 约 60s ≈ 2.5h，加抓图/截图/构建 ≈ 3h，对 6h 硬限留足余量 |
| `ARXIV_INIT_RESULTS` | `.env.example:8` | `500` | `120` | 与代码默认值保持一致 |
| `ARXIV_DAILY_RESULTS` | `deploy.yml:51` | `80` | **保持 80** | 日均 7 篇 → 80 提供约 11 天容错，单次 CI 失败不漏论文。（曾按纯 JEPA 日均 2–3 篇提议降到 40，范围扩大后该提议作废） |
| `ARXIV_DAILY_RESULTS` | `arxiv_crawler.py:48` 代码默认值 | `"20"` | 保持 `"20"` | 与 VLA 站行为一致；CI 已显式覆盖为 80 |

### 5.3 加深历史的操作方法（写入 README）

`initialize()` 只在 papers.md 缺失时触发，之后永远是 `run_daily()`。要把历史从 120 篇加深，**临时**把 `deploy.yml` 的 `ARXIV_DAILY_RESULTS` 每轮 +100 跑几次：每轮拉取最新 N 篇并去重入库，新增的待生成摘要会在后续每日运行中自然消化。

**该机制已被实证有效**：VLA 站 1917 篇中仅剩 16 篇 `待生成`。`generate_summaries.py` 按 `BATCH_WRITE_SIZE=5` 增量写盘，CI 每日重跑会继续处理未决条目。

**因此不新增 `SUMMARY_MAX_ITEMS`。** 唯一的 6h 超限风险来自一次性巨量回填，已由 §5.2 的 `INIT=120` 消除。

---

## 6. 改动清单（精确到行）

### 6.1 检索式与常量

| 文件 | 行 | 现值 → 新值 |
| --- | --- | --- |
| `scripts/arxiv_crawler.py` | 9–13 | `DEFAULT_ARXIV_QUERY` 三行拼接 → §3 定稿串 |
| `scripts/arxiv_crawler.py` | 22 | docstring：`默认同时检索 VLA 与 World Action Model 相关短语` → `默认检索 JEPA / 联合嵌入 / 隐空间预测 / 世界模型相关短语` |
| `scripts/arxiv_crawler.py` | 40 | docstring：`搜索关键词（默认同时检索 VLA 与 World Action Model）` → `搜索关键词（默认检索 JEPA / 世界模型相关短语）` |
| `scripts/arxiv_crawler.py` | 41 | docstring：`初始化抓取数量（默认 500）` → `（默认 120）` |
| `scripts/arxiv_crawler.py` | 47 | `os.getenv("ARXIV_INIT_RESULTS", "500")` → `"120"` |
| `scripts/build_site.py` | 39–43 | `DEFAULT_ARXIV_QUERY` → §3 定稿串，**必须与 crawler 逐字相同** |
| `scripts/build_site.py` | 44 | `DEFAULT_ARXIV_KEYWORD_LABEL = "VLA / World Action Model"` → `"JEPA / 世界模型"` |

### 6.2 品牌文案

| 文件 | 行 | 现值 → 新值 |
| --- | --- | --- |
| `scripts/build_site.py` | 809 | `<span class="site-brand-mark">VLA/WAM</span>` → `JEPA/WM` |
| `scripts/build_site.py` | 822 | `<p class="eyebrow">VLA &amp; World Action Model Feed</p>` → `JEPA &amp; World Model Feed` |
| `scripts/build_site.py` | 841 | placeholder `比如：OpenVLA、World Action Model、实时推理...` → `比如：V-JEPA、latent prediction、世界模型...` |
| `scripts/build_site.py` | 735 | favicon SVG 内嵌字母 `%3EV%3C/text%3E` → `%3EJ%3C/text%3E`（VLA 的 V → JEPA 的 J；计划编写阶段补入，spec 初稿漏项） |
| `scripts/modern_ui.css` | 157 | `content: "VLA";` → `content: "JEPA";` |
| `scripts/fetch_paper_images.py` | 164 | UA `daily-arxiv-vla/paper-image-fetcher` → `daily-arxiv-jepa/paper-image-fetcher` |
| `package.json` | 2 | `"name": "daily-arxiv-vla"` → `"daily-arxiv-jepa"` |
| `package-lock.json` | 2, 7 | 同上（两处） |

**不改**（已逐处核对为主题中立）：`generate_head()` 的 `- ArXiv Papers` 标题后缀（798 行）、导航 `Research Brief`（810 行）、hero 副标题、hero-tags（`中文精读`/`核心贡献提炼`/`论文原图速览`）、footer、摘要生成 system prompt（已确认主题中立，模板为 研究单位/论文概述/核心贡献/方法描述/数据集与资源/评估与结果）、封面配色 `COVER_THEMES`。

派生文案自动生效，无需逐处改：`generate_index_html()` / `generate_paper_html()` / `generate_cover_html()` 均由 `get_arxiv_keyword_label()` 拼出 `f"{keyword} 每日论文卡"`，改 §6.1 的 LABEL 即全站标题、`<title>`、meta description 一并更新。

### 6.3 环境变量与 CI

| 文件 | 行 | 动作 |
| --- | --- | --- |
| `.env.example` | 7 | `ARXIV_QUERY_KEYWORD=` → §3 定稿串（单行） |
| `.env.example` | 8 | `ARXIV_INIT_RESULTS=500` → `120` |
| `.github/workflows/deploy.yml` | 50 | **删除** `ARXIV_QUERY_KEYWORD` 覆盖 |
| `.github/workflows/deploy.yml` | 94 | **删除** `ARXIV_QUERY_KEYWORD` 覆盖 |

**删除而非替换的理由（关键）**：`build_site.py:142-146` 的标签解析是

```python
keyword = os.getenv("ARXIV_QUERY_KEYWORD") or DEFAULT_ARXIV_QUERY
if keyword == DEFAULT_ARXIV_QUERY:
    return DEFAULT_ARXIV_KEYWORD_LABEL
return keyword          # ← 查询串会被当成站点标题渲染
```

**危害的精确机制（实施阶段实测更正）**：初稿断言"5 处副本任一处差一个空格就会毁掉标题"，实测证明该断言**过宽**。逐场景验证结果：

| 场景 | `get_arxiv_keyword_label()` 返回 |
| --- | --- |
| env 未设置 | `JEPA / 世界模型` ✅ |
| env 逐字等于 build_site 默认值 | `JEPA / 世界模型` ✅ |
| **env = 默认值 + 1 个空格** | **261 字符查询语法** ❌ |
| env = 旧 VLA 式 | 该 VLA 查询串 ❌ |
| 仅 crawler 与 build_site 的默认值互相漂移（env 未设置） | `JEPA / 世界模型` ✅ **不受影响** |

原因：该函数比较的是 env 与 **build_site 自身**的默认值，env 未设置时 `keyword` 就等于它自己的默认值，比较恒等成立。所以**危害面只在环境变量边界**，crawler↔build_site 的默认值漂移不会破坏标题。

进一步实测：`arxiv_crawler.py` 与 `build_site.py` **都不调用 `load_dotenv()`**（全仓仅 `generate_summaries.py` 调用，而它不使用查询串）。因此 `.env` / `.env.example` 里的 `ARXIV_QUERY_KEYWORD` 对爬虫与站点构建**零运行时作用**，纯属文档；能真正注入该变量的只有 shell `export` 与 CI `env:`。

结论：`deploy.yml` 的两处覆盖是该变量**唯一**的实际注入点。删掉它们即彻底关闭危害入口，`get_arxiv_keyword_label()` 恒返回人类可读标签。**净删 2 行，无需新增 `SITE_TOPIC_LABEL`。**

`test_crawler_and_build_site_queries_are_byte_identical` 仍然保留，但其理由需更正为：两处默认值漂移会让"实际爬取的主题"与"站点标签逻辑假设的主题"不一致，且任何从其中一个文件复制出去的 env 覆盖都会与另一个文件不匹配 —— 它是**语义一致性护栏**，不是标题护栏。标题护栏是 `test_deploy_yml_has_no_query_override` 与 `test_env_drift_turns_query_into_site_title`。

`deploy.yml` 保留：`ARXIV_DAILY_RESULTS: 80`、`ARXIV_PAGE_SIZE: 10`、`ARXIV_DELAY_SECONDS: 15`、`ARXIV_RETRY_BASE_SECONDS: 60`、`ARXIV_MAX_RETRIES: 4`、`MODELSCOPE_MODELS` 列表、cron `0 4 * * *`（北京时间 12:00）。

### 6.4 数据与文档

- `git rm papers.md`（§5.1）
- `README.md` 改写，精确到行：
  - 第 1 行标题 `# ArXiv Papers 网站` → 体现 JEPA/世界模型主题
  - 第 3 行首段：`包含 VLA / Vision-Language-Action 以及 World Action Model 相关关键词` → JEPA / 联合嵌入 / 隐空间预测 / 世界模型
  - 第 7 行功能特性：`每日自动从 ArXiv 爬取 VLA 与 World Action Model 相关最新论文` → 同上口径
  - 第 41 行 `ARXIV_QUERY_KEYWORD` 说明：`默认同时检索 VLA 与 World Action Model 相关短语` → 新口径
  - 第 134 行示例 `ARXIV_QUERY_KEYWORD: "your_keyword"` → 保留（通用示例，主题中立）
  - 第 139 行 `默认配置` 段的检索式 → §3 定稿串
  - 新增小节：§5.3 的"如何加深历史回填"操作方法
  - 新增小节：§8 的平台前置条件（开启 Pages、配置 Secret、合并到 `master`）
  - 第 41 行附近补充 `ARXIV_INIT_RESULTS` 默认值已由 500 改为 120 的说明
- `site/index.html`：gitignore 忽略的过期构建产物（仍是 VLA 品牌），由 `build_site.py` 覆盖重生，无需手工改

### 6.5 测试

新增 `requirements-dev.txt`（`pytest>=8,<9`）与 `tests/test_topic_retarget.py`。不写入 `requirements.txt`，避免污染 CI 运行时依赖。`tests/` 不在 `.gitignore` 内（已核对：忽略项为 `.env`/`.venv/`/`__pycache__/`/`node_modules/`/`output/`/`tmp/`/`site/`/`TEST/`/`test_api.py`/`*.pyc`）。

断言全部针对**字符串漂移**与**品牌漏改**这两个唯一会真正咬人的失效模式（无业务逻辑可测）。实施阶段追加第 7 项（固化实测出的危害机制），共 **18 个测试**：

1. `arxiv_crawler.DEFAULT_ARXIV_QUERY == build_site.DEFAULT_ARXIV_QUERY`（防 §6.3 描述的标题灾难）
2. 查询串不含任何 VLA 专属词：`VLA`、`Vision-Language-Action`、`World Action Model`、`World-Action Model`、`action world model`
3. 查询串含必备概念词：`JEPA`、`joint embedding`、`latent prediction`、`world model`、`world models`
4. `get_arxiv_keyword_label()` 在 `ARXIV_QUERY_KEYWORD` 未设置时返回 `JEPA / 世界模型`，且返回值不含 `ti:` / `abs:`（即不是查询串）
5. `generate_index_html()` 输出含 `JEPA`、不含 `VLA/WAM` 与 `World Action Model Feed`；`generate_style_css()` 输出含 `content: "JEPA"`
7. `test_env_drift_turns_query_into_site_title`：特征测试，固化 §6.3 实测表第 3 行——env 差一个空格即令查询串变成站点标题
6. 仓库回归：遍历 git 跟踪的文本文件（排除 `docs/` 下本设计文档与实施计划，因为其中必须引用旧字符串来说明改动），断言无残留品牌串 `VLA/WAM`、`daily-arxiv-vla`、CSS 水印 `content: "VLA"`。papers.md 已被 `git rm`，无需排除

---

## 7. 明确推迟项（附触发条件）

| 项 | 现状 | 触发条件 | 届时做法 |
| --- | --- | --- | --- |
| EXT 跨领域类目（eess.IV / eess.SP / cs.SD / q-bio.QM / stat.ML / cs.MA / cs.NE / cs.CE / cs.HC） | 约 4% 跨领域 JEPA 被挡 | 需求方发现想要的论文没进站点 | 类目白名单改为 `ARXIV_ALLOWED_CATEGORIES` 环境变量可覆盖；EXT 层需命中强概念词（`jepa`/`joint embedding`/`world model`/`latent prediction`/`self-supervised`）才收，避免放回 astro-ph/econ 噪声 |
| `data.json` 体积与分块归档 | 2.1 KB/篇，12 个月后约 4.8 MB | `data.json` > 6 MB | JSON 改 compact（省 8%，一行）；首页只载最近 N 天，历史按月分片懒加载（需改 `build_site.py` 内嵌的 `app.js`） |
| 检索式去重简化 | 保留冗余的 `abs:"latent world model"`、`ti:"joint embedding predictive"` | 无需主动触发 | 冗余子句不增加语料，仅为可读性保留 |

---

## 8. 平台前置条件（需求方手动，代码无法代办）

1. **开启 GitHub Pages** —— 已查证 `GET /repos/DreamSkanda/daily-arxiv-jepa/pages` 返回 404、`has_pages: false`。需在 `Settings → Pages → Build and deployment → Source` 选 **GitHub Actions**，否则 `deploy` 作业的 `actions/deploy-pages` 会失败。
2. **配置 Secret** —— `MODELSCOPE_ACCESS_TOKEN`（必需）。fork **不继承**上游 secrets，必须在新仓库重配。
3. **可选 GA4** —— `Settings → Secrets and variables → Actions → Variables` 新增 `GA_MEASUREMENT_ID`（如 `G-XXXXXXXXXX`）。不配置则站点不加载 GA，不影响功能。
4. **分支合并** —— 开发在 `dev_jepa`，但 cron 与 Pages 只认默认分支 `master`（已查证 `default_branch: master`）。**必须把 `dev_jepa` 合入 `master` 才会开始每日更新。** `deploy.yml` 的 `on.push.branches: [master, main]` 已覆盖 `master`，无需改。

---

## 9. 风险

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 首次 CI 运行超 6h | 作业被杀 → `提交更改` 步骤不执行 → papers.md 未提交 → 下次重跑同样超时，死循环 | `INIT=120`（§5.2）把首跑压到约 3h；若仍超时，把 `INIT` 降到 60 再跑一轮，之后按 §5.3 逐步加深 |
| 与 daily-arxiv-vla 内容重叠 | 两站出现同一篇论文 | 需求方已明确接受（§3）。若日后要消除，改用 §2.2 的 `ANDNOT ti:` 写法，代价是语料 4513 → 4315 且误杀 `WA-JEPA` |
| 日均 7 篇导致摘要配额吃紧 | 部分条目长期停留 `待生成` | 现有 6 模型回退链（`MODELSCOPE_MODELS`）+ 限流标记机制已足够；VLA 站 1917 篇仅 16 篇待生成即为实证 |
| env 注入走样的查询串 | 首页 H1/`<title>`/meta description/详情页与封面页标题变成 261 字符查询语法 | 已删 `deploy.yml` 两处覆盖——实测证明这是该变量唯一的实际注入点（两个脚本都不 `load_dotenv`）。`test_deploy_yml_has_no_query_override` 防其回归，`test_env_drift_turns_query_into_site_title` 固化危害机制 |
| crawler 与 build_site 默认值漂移 | 爬取主题与站点标签逻辑假设不一致（**不会**破坏标题，见 §6.3 实测表） | `test_crawler_and_build_site_queries_are_byte_identical` 强制逐字相等 |
| 用户改 `.env` 想换检索式却不生效 | 静默失效，困惑 | 两个脚本不读 `.env`（fork 既有行为，本次不改以免变更 CI 语义）；已在 README 显式说明 |
| 站点增长后首屏变慢 | 移动端加载 8 MB JSON | §7 推迟项，触发条件明确 |

---

## 10. 验收标准

1. `pytest tests/test_topic_retarget.py` 全绿
2. 本地 `python scripts/arxiv_crawler.py`（papers.md 已删）走 `initialize()` 分支，写入约 120 篇，抽样确认标题为 JEPA / 世界模型 / 联合嵌入 / 隐空间预测主题
3. 本地 `python scripts/build_site.py` 成功；`site/index.html` 的 `<title>`、H1、brand-mark、eyebrow、搜索 placeholder、CSS 水印均为 JEPA 品牌，且全文无 `VLA` 残留
4. `site/assets/data.json` 可被首页 `app.js` 正常加载渲染
5. 合入 `master` 后，GitHub Actions 首跑绿；Pages 可访问；次日 cron 自动新增论文
