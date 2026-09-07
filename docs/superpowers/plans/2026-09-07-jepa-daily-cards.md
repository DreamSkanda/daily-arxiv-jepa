# JEPA 每日论文卡 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 daily-arxiv-vla 的每日论文卡流水线重定向到 JEPA / 联合嵌入 / 隐空间预测 / 世界模型主题，产出 `https://dreamskanda.github.io/daily-arxiv-jepa/`。

**Architecture:** 纯主题重定向，**零新增业务逻辑**。改动面 = 检索式字符串（2 处 Python 默认值 + `.env.example`）、品牌文案（build_site.py 5 处 + CSS 水印 1 处）、仓库元数据（package.json / package-lock.json / UA）、CI 精简（删除 deploy.yml 两处查询覆盖）、数据重置（删除 papers.md 后本地真实回填 120 篇）、README 重写。新增 1 个测试文件，只覆盖两类真实失效模式：字符串漂移与品牌漏改。

**Tech Stack:** Python 3.14（本地）/ 3.9（CI）、`arxiv` 库、pytest、原生 HTML/CSS/JS 静态站、GitHub Actions + Pages。

**Spec:** `docs/superpowers/specs/2026-09-07-jepa-daily-cards-design.md`

## Global Constraints

以下值为 spec 逐字规定，所有任务隐含遵守：

- **定稿检索式（260 字符，两处 Python 默认值必须逐字相同）：**
  ```
  (ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR abs:"latent world model")
  ```
- **禁止**加入任何 `ANDNOT` 排除项（不排除 VLA/WAM，与 daily-arxiv-vla 内容重叠已被接受）。
- **禁止**加入 `abs:"latent space"`（实测 +9955 篇潜空间生成模型噪声）与 `abs:"latent dynamics"`（实测 +450 篇多为动力系统/降阶建模）。
- **站点标签** `DEFAULT_ARXIV_KEYWORD_LABEL = "JEPA / 世界模型"`。
- **`ARXIV_INIT_RESULTS` 代码默认值** `"500"` → `"120"`（`arxiv_crawler.py:47`）。CI 未设置该变量，只改 `.env.example` 无效。
- **`ARXIV_DAILY_RESULTS`**：`deploy.yml` 保持 `80`；`arxiv_crawler.py:48` 代码默认值保持 `"20"`；`.env.example:9` 保持 `20`。
- **类目白名单不动**：`_ALLOWED_PRIMARY_CATEGORIES = {cs.CV, cs.AI, cs.CL, cs.LG, cs.MM, cs.RO}`。
- **不新增** `SITE_TOPIC_LABEL`、`SUMMARY_MAX_ITEMS`、EXT 类目分层、概念词闸门、LLM 相关性复判。
- **不修改**摘要生成 system prompt（已核对为主题中立）、`COVER_THEMES` 配色、hero 副标题、hero-tags、footer、`Research Brief`（build_site.py:810）、`- ArXiv Papers` 标题后缀（:798）。
- **测试不得 `import scripts/arxiv_crawler.py`**：该模块在模块级 `import arxiv`，而本地与测试环境不装运行时依赖（实测缺 `arxiv`/`dotenv`/`openai`/`tqdm`）。必须用 `ast` 提取常量。
- **本地 Python 3.14.7，已有 `pytest` 与 `PIL`**；`import build_site` 可正常工作（已实测）。
- **⚠️ 提交策略（用户明确指示，覆盖 skill 的"frequent commits"）：所有任务过程中一律不执行 `git commit`。只在 Task 6 做唯一一次提交。** 且 `.git` 在沙箱内只读，提交需提权。
- 工作分支 `dev_jepa`；仓库默认分支为 `master`，cron 与 Pages 只认默认分支，最终需由用户合并。

---

## File Structure

| 文件 | 职责 | 动作 |
| --- | --- | --- |
| `tests/test_topic_retarget.py` | 主题重定向回归测试：检索式一致性/内容、标签解析、品牌渲染、仓库残留扫描 | 新建 |
| `requirements-dev.txt` | 测试依赖，与 CI 运行时依赖隔离 | 新建 |
| `scripts/arxiv_crawler.py` | 检索式默认值、`ARXIV_INIT_RESULTS` 默认值、docstring | 改 9–13, 22, 40, 41, 47 |
| `scripts/build_site.py` | 检索式默认值、站点标签、brand-mark、eyebrow、placeholder、favicon 字母 | 改 39–43, 44, 735, 809, 822, 841 |
| `scripts/modern_ui.css` | hero 背景水印字母 | 改 157 |
| `scripts/fetch_paper_images.py` | HTTP User-Agent 标识 | 改 164 |
| `package.json` / `package-lock.json` | 包名 | 改 2 / 2,7 |
| `.env.example` | 检索式与初始回填量示例 | 改 7, 8 |
| `.github/workflows/deploy.yml` | 删除两处 `ARXIV_QUERY_KEYWORD` 覆盖 | 删 50, 94 |
| `papers.md` | 论文语料 | 删除 VLA 语料 → 本地回填 120 篇 JEPA 语料 |
| `README.md` | 项目文档 | 改 1,3,7,41,139 + 新增 2 小节 |

---

### Task 1: 测试脚手架 + 检索式重定向

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/test_topic_retarget.py`
- Modify: `scripts/arxiv_crawler.py:9-13,22,40,41,47`
- Modify: `scripts/build_site.py:39-43`
- Test: `tests/test_topic_retarget.py`

**Interfaces:**
- Consumes: 无（首个任务）
- Produces:
  - `tests/test_topic_retarget.py` 中的模块级常量 `FINAL_QUERY: str`、`VLA_TERMS: tuple[str, ...]`、`REQUIRED_TERMS: tuple[str, ...]`、`TOPIC_LABEL: str`
  - 函数 `module_constant(relpath: str, name: str) -> str`（AST 提取模块级字符串常量）
  - 函数 `load_build_site()`（返回已导入的 `build_site` 模块对象，供 Task 2/3 的测试复用）
  - `scripts/arxiv_crawler.DEFAULT_ARXIV_QUERY` 与 `scripts/build_site.DEFAULT_ARXIV_QUERY` 均等于 `FINAL_QUERY`
  - `ArxivCollector.__init__` 读取的 `ARXIV_INIT_RESULTS` 默认值为 `"120"`

- [ ] **Step 1: 创建 `requirements-dev.txt`**

```
pytest>=8,<9
```

- [ ] **Step 2: 写失败测试**

创建 `tests/test_topic_retarget.py`：

```python
"""主题重定向回归测试（JEPA / 世界模型）。

本次改动没有新增业务逻辑，因此只测两类真实失效模式：
1. 检索式在多个副本间漂移 —— build_site.get_arxiv_keyword_label() 靠
   "环境变量是否等于默认查询串" 决定站点标题，任一处走样就会把 300+ 字符的
   查询语法渲染成首页 H1、<title> 与 meta description。
2. 品牌改造漏改 —— VLA 残留。

注意：不 import scripts/arxiv_crawler.py，它在模块级 import arxiv，而测试环境
不安装运行时依赖。改用 ast 提取模块级字符串常量。
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 与 spec §3 逐字一致。有意改动检索式时，必须同步更新此处与两个脚本的默认值。
FINAL_QUERY = (
    '(ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR '
    'abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR '
    'ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR '
    'abs:"latent world model")'
)

VLA_TERMS = (
    "VLA",
    "Vision-Language-Action",
    "World Action Model",
    "World-Action Model",
    "action world model",
)

REQUIRED_TERMS = ("JEPA", "joint embedding", "latent prediction", "world model", "world models")

TOPIC_LABEL = "JEPA / 世界模型"


def module_constant(relpath: str, name: str) -> str:
    """用 AST 提取模块级字符串常量，避免 import 触发运行时依赖。"""
    tree = ast.parse((ROOT / relpath).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{relpath} 中未找到模块级常量 {name}")


def load_build_site():
    """导入 scripts/build_site.py（只需 PIL，不需要 arxiv/openai/dotenv）。"""
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts" / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_crawler_and_build_site_queries_are_byte_identical():
    """两处默认值必须逐字相同，否则站点标题会渲染成查询语法。"""
    crawler_query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    build_site_query = module_constant("scripts/build_site.py", "DEFAULT_ARXIV_QUERY")
    assert crawler_query == build_site_query


def test_both_defaults_equal_final_query():
    crawler_query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    build_site_query = module_constant("scripts/build_site.py", "DEFAULT_ARXIV_QUERY")
    assert crawler_query == FINAL_QUERY
    assert build_site_query == FINAL_QUERY


def test_query_contains_no_vla_terms():
    query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    for term in VLA_TERMS:
        assert term not in query, f"检索式不应含 VLA 专属词 {term!r}"


def test_query_covers_required_concepts():
    query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    for term in REQUIRED_TERMS:
        assert term in query, f"检索式缺少必备概念词 {term!r}"


def test_query_excludes_rejected_noise_terms():
    """实测拒绝的两个隐空间口径不得回流。"""
    query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    assert "latent space" not in query
    assert "latent dynamics" not in query
    assert "ANDNOT" not in query


def test_init_results_default_is_120():
    source = (ROOT / "scripts" / "arxiv_crawler.py").read_text(encoding="utf-8")
    assert 'os.getenv("ARXIV_INIT_RESULTS", "120")' in source
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `cd /home/skanda/Projects/embodied/daily-arxiv-jepa && python3 -m pytest tests/test_topic_retarget.py -v`

Expected: **4 failed, 2 passed**

- FAIL：`test_both_defaults_equal_final_query`、`test_query_contains_no_vla_terms`、`test_query_covers_required_concepts`、`test_init_results_default_is_120`
- PASS（**属预期，非缺陷**）：`test_crawler_and_build_site_queries_are_byte_identical` —— 现状两处默认值已逐字一致（已实测），它是防未来漂移的护栏；`test_query_excludes_rejected_noise_terms` —— 旧查询串本就不含 `latent space`/`latent dynamics`/`ANDNOT`，它是防被拒噪声词回流的护栏

TDD 说明：这 2 个护栏测试在改动前就通过是正确的——它们保护"以后不要变坏"，不是"现在要变好"。真正驱动本次改动的是那 4 个红测试。

- [ ] **Step 4: 改 `scripts/arxiv_crawler.py:9-13` 的 `DEFAULT_ARXIV_QUERY`**

把

```python
DEFAULT_ARXIV_QUERY = (
	'all:"VLA" OR all:"Vision-Language-Action" OR '
	'all:"World Action Model" OR all:"World-Action Model" OR '
	'all:"action world model"'
)
```

替换为（保持该文件原有的 **Tab 缩进**）：

```python
DEFAULT_ARXIV_QUERY = (
	'(ti:"JEPA" OR abs:"JEPA" OR '
	'ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR '
	'abs:"joint embedding" OR abs:"latent prediction" OR '
	'ti:"world model" OR ti:"world models" OR '
	'abs:"world model" OR abs:"world models" OR '
	'abs:"latent world model")'
)
```

隐式字符串拼接后必须与 `FINAL_QUERY` 逐字相等（260 字符，无多余空格）。

- [ ] **Step 5: 改 `scripts/build_site.py:39-43` 的 `DEFAULT_ARXIV_QUERY`**

替换为（保持该文件原有的 **4 空格缩进**）：

```python
DEFAULT_ARXIV_QUERY = (
    '(ti:"JEPA" OR abs:"JEPA" OR '
    'ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR '
    'abs:"joint embedding" OR abs:"latent prediction" OR '
    'ti:"world model" OR ti:"world models" OR '
    'abs:"world model" OR abs:"world models" OR '
    'abs:"latent world model")'
)
```

- [ ] **Step 6: 改 `scripts/arxiv_crawler.py:47` 的初始回填默认值**

```python
		self.init_results = init_results or int(os.getenv("ARXIV_INIT_RESULTS", "120"))
```

- [ ] **Step 7: 同步 docstring（`arxiv_crawler.py:22,40,41`）**

- 第 22 行：`默认同时检索 VLA 与 World Action Model 相关短语` → `默认检索 JEPA / 联合嵌入 / 隐空间预测 / 世界模型相关短语`
- 第 40 行：`搜索关键词（默认同时检索 VLA 与 World Action Model）` → `搜索关键词（默认检索 JEPA / 世界模型相关短语）`
- 第 41 行：`初始化抓取数量（默认 500）` → `初始化抓取数量（默认 120）`

- [ ] **Step 8: 运行测试，确认通过**

Run: `python3 -m pytest tests/test_topic_retarget.py -v`
Expected: 6 passed

- [ ] **Step 9: 校验拼接结果逐字相等（防止手抄多出空格）**

Run:
```bash
python3 -c "
import ast,pathlib
t=ast.parse(pathlib.Path('scripts/arxiv_crawler.py').read_text(encoding='utf-8'))
q=[ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(getattr(x,'id',None)=='DEFAULT_ARXIV_QUERY' for x in n.targets)][0]
import sys; sys.path.insert(0,'tests')
from test_topic_retarget import FINAL_QUERY
print('len=',len(q)); print('equal=',q==FINAL_QUERY)"
```
Expected: `len= 260` 与 `equal= True`

**不要 commit**（见 Global Constraints）。

---

### Task 2: 站点标签与品牌渲染

**Files:**
- Modify: `scripts/build_site.py:44,735,809,822,841`
- Modify: `scripts/modern_ui.css:157`
- Test: `tests/test_topic_retarget.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `load_build_site()`、`TOPIC_LABEL`
- Produces:
  - `build_site.DEFAULT_ARXIV_KEYWORD_LABEL == "JEPA / 世界模型"`
  - `build_site.get_arxiv_keyword_label() -> str`：env 未设置或等于默认查询串时返回 `TOPIC_LABEL`
  - `build_site.generate_index_html() -> str`：含 `JEPA/WM`、`JEPA &amp; World Model Feed`、`V-JEPA`
  - `build_site.generate_style_css() -> str`：含 `content: "JEPA"`
  - `build_site.generate_head(title, description, stylesheet_prefix="") -> str`：favicon 含 `%3EJ%3C`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_topic_retarget.py` 末尾追加：

```python
def test_keyword_label_is_human_readable(monkeypatch):
    bs = load_build_site()
    monkeypatch.delenv("ARXIV_QUERY_KEYWORD", raising=False)
    assert bs.DEFAULT_ARXIV_KEYWORD_LABEL == TOPIC_LABEL
    label = bs.get_arxiv_keyword_label()
    assert label == TOPIC_LABEL
    assert "ti:" not in label and "abs:" not in label


def test_keyword_label_when_env_matches_default(monkeypatch):
    """env 显式设置为默认查询串时，仍必须返回人类可读标签。"""
    bs = load_build_site()
    monkeypatch.setenv("ARXIV_QUERY_KEYWORD", bs.DEFAULT_ARXIV_QUERY)
    assert bs.get_arxiv_keyword_label() == TOPIC_LABEL


def test_index_html_is_jepa_branded(monkeypatch):
    bs = load_build_site()
    monkeypatch.delenv("ARXIV_QUERY_KEYWORD", raising=False)
    html = bs.generate_index_html()
    assert "JEPA/WM" in html
    assert "JEPA &amp; World Model Feed" in html
    assert "V-JEPA" in html
    assert f"{TOPIC_LABEL} <span class=\"site-title-nowrap\">每日论文卡</span>" in html
    for banned in ("VLA/WAM", "World Action Model Feed", "OpenVLA", "VLA / World Action Model"):
        assert banned not in html, f"首页残留 VLA 品牌：{banned!r}"


def test_favicon_letter_is_j():
    bs = load_build_site()
    head = bs.generate_head("t", "d")
    assert "%3EJ%3C" in head
    assert "%3EV%3C" not in head


def test_css_watermark_is_jepa():
    bs = load_build_site()
    css = bs.generate_style_css()
    assert 'content: "JEPA"' in css
    assert 'content: "VLA"' not in css
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m pytest tests/test_topic_retarget.py -v -k "label or branded or favicon or watermark"`
Expected: **5 FAILED**（本任务新增 5 个测试，现状全部为 VLA 品牌，故全红）

- [ ] **Step 3: 改 `scripts/build_site.py:44`**

```python
DEFAULT_ARXIV_KEYWORD_LABEL = "JEPA / 世界模型"
```

- [ ] **Step 4: 改 `scripts/build_site.py:735` favicon 字母**

```python
        "font-size='30' font-family='Arial, sans-serif' fill='white'%3EJ%3C/text%3E"
```

- [ ] **Step 5: 改 `scripts/build_site.py:809` brand-mark**

```python
            <span class="site-brand-mark">JEPA/WM</span>
```

- [ ] **Step 6: 改 `scripts/build_site.py:822` eyebrow**

```python
            <p class="eyebrow">JEPA &amp; World Model Feed</p>
```

- [ ] **Step 7: 改 `scripts/build_site.py:841` 搜索 placeholder**

```python
              <input id="search" type="search" placeholder="比如：V-JEPA、latent prediction、世界模型..." aria-label="搜索论文卡片" />
```

- [ ] **Step 8: 改 `scripts/modern_ui.css:157` 水印**

```css
  content: "JEPA";
```

- [ ] **Step 9: 运行全部测试，确认通过**

Run: `python3 -m pytest tests/test_topic_retarget.py -v`
Expected: 11 passed（6 + 5）

**不要 commit。**

---

### Task 3: 仓库元数据、CI 精简与残留扫描

**Files:**
- Modify: `package.json:2`
- Modify: `package-lock.json:2,7`
- Modify: `scripts/fetch_paper_images.py:164`
- Modify: `.env.example:7,8`
- Modify: `.github/workflows/deploy.yml:50,94`（删除两行）
- Test: `tests/test_topic_retarget.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `FINAL_QUERY`、`ROOT`
- Produces:
  - `deploy.yml` 中不再出现 `ARXIV_QUERY_KEYWORD`（爬虫与构建两步均使用 Python 默认值）
  - `.env.example` 的 `ARXIV_QUERY_KEYWORD` 为 `FINAL_QUERY` 单行形式、`ARXIV_INIT_RESULTS=120`
  - 测试函数 `iter_scanned_files()`（供残留扫描使用）

- [ ] **Step 1: 追加失败测试**

在 `tests/test_topic_retarget.py` 末尾追加：

```python
BANNED_BRAND_STRINGS = (
    "VLA/WAM",
    "daily-arxiv-vla",
    'content: "VLA"',
    "World Action Model Feed",
    "VLA / World Action Model",
    'all:"VLA"',
)

SCAN_ROOTS = ("scripts", ".github")
SCAN_FILES = ("package.json", "package-lock.json", ".env.example")
SCAN_SUFFIXES = (".py", ".mjs", ".css", ".json", ".yml", ".yaml", ".example")
SCAN_EXCLUDE_DIRS = {"__pycache__", "node_modules", ".venv", "site", ".git", "docs"}


def iter_scanned_files():
    for rel in SCAN_FILES:
        path = ROOT / rel
        if path.exists():
            yield path
    for root in SCAN_ROOTS:
        for path in (ROOT / root).rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            if SCAN_EXCLUDE_DIRS & set(path.relative_to(ROOT).parts):
                continue
            yield path


def test_no_vla_brand_residue_in_code_and_config():
    offenders = []
    for path in iter_scanned_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for banned in BANNED_BRAND_STRINGS:
            if banned in text:
                offenders.append(f"{path.relative_to(ROOT)}: {banned}")
    assert not offenders, "残留 VLA 品牌串：\n" + "\n".join(offenders)


def test_deploy_yml_has_no_query_override():
    """删除 CI 覆盖后，两处默认值由测试 1 保证一致，标题漂移风险消除。"""
    text = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "ARXIV_QUERY_KEYWORD" not in text
    assert "ARXIV_DAILY_RESULTS: 80" in text


def test_env_example_matches_final_query():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    values = dict(
        (ln.split("=", 1)[0].strip(), ln.split("=", 1)[1].strip())
        for ln in lines if "=" in ln and not ln.strip().startswith("#")
    )
    assert values["ARXIV_QUERY_KEYWORD"] == FINAL_QUERY
    assert values["ARXIV_INIT_RESULTS"] == "120"


def test_package_metadata_renamed():
    import json
    assert json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["name"] == "daily-arxiv-jepa"
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["name"] == "daily-arxiv-jepa"
    assert lock["packages"][""]["name"] == "daily-arxiv-jepa"


def test_fetch_images_user_agent_renamed():
    text = (ROOT / "scripts" / "fetch_paper_images.py").read_text(encoding="utf-8")
    assert "daily-arxiv-jepa/paper-image-fetcher" in text
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m pytest tests/test_topic_retarget.py -v -k "residue or deploy_yml or env_example or package_metadata or user_agent"`
Expected: 5 FAILED

- [ ] **Step 3: 改 `package.json:2`**

```json
  "name": "daily-arxiv-jepa",
```

- [ ] **Step 4: 改 `package-lock.json:2` 与 `:7`**

两处 `"name": "daily-arxiv-vla",` → `"name": "daily-arxiv-jepa",`

- [ ] **Step 5: 改 `scripts/fetch_paper_images.py:164`**

```python
            "User-Agent": "daily-arxiv-jepa/paper-image-fetcher (+https://arxiv.org)",
```

- [ ] **Step 6: 改 `.env.example:7-8`**

```
ARXIV_QUERY_KEYWORD=(ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR abs:"latent world model")
ARXIV_INIT_RESULTS=120
```

第 9 行 `ARXIV_DAILY_RESULTS=20` 保持不变。

- [ ] **Step 7: 删除 `deploy.yml:50` 与 `:94` 两行**

删除爬虫步骤中的：
```yaml
          ARXIV_QUERY_KEYWORD: 'all:"VLA" OR all:"Vision-Language-Action" OR all:"World Action Model" OR all:"World-Action Model" OR all:"action world model"'
```
以及构建步骤中的同一行。**保留**爬虫步骤其余 env（`MODELSCOPE_ACCESS_TOKEN`、`ARXIV_DAILY_RESULTS: 80`、`ARXIV_PAGE_SIZE: 10`、`ARXIV_DELAY_SECONDS: 15`、`ARXIV_RETRY_BASE_SECONDS: 60`、`ARXIV_MAX_RETRIES: 4`）。

删除后构建步骤的 env 只剩：
```yaml
        env:
          GA_MEASUREMENT_ID: ${{ vars.GA_MEASUREMENT_ID || secrets.GA_MEASUREMENT_ID }}
```

- [ ] **Step 8: 校验 YAML 仍合法**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy.yml',encoding='utf-8')); print('YAML OK')"`
Expected: `YAML OK`（若本地无 pyyaml，改用 `python3 -c "print(open('.github/workflows/deploy.yml',encoding='utf-8').read().count('ARXIV_QUERY_KEYWORD'))"`，Expected: `0`）

- [ ] **Step 9: 运行全部测试，确认通过**

Run: `python3 -m pytest tests/test_topic_retarget.py -v`
Expected: 16 passed（6 + 5 + 5）

**不要 commit。**

---

### Task 4: 数据重置与本地真实回填

**Files:**
- Delete + regenerate: `papers.md`
- Create（本地，不提交）: `.venv/`（已被 `.gitignore` 忽略）
- Generate（本地，gitignore）: `site/`

**Interfaces:**
- Consumes: Task 1 的 `ARXIV_INIT_RESULTS` 默认值 `"120"` 与 `DEFAULT_ARXIV_QUERY`
- Produces: 含约 120 行 JEPA 语料的 `papers.md`（四列表格，简要总结列为 `<details><summary>展开</summary>待生成</details>`），交由 CI 生成摘要

**需要提权的步骤：** Step 1（pip 安装，需网络）、Step 3（arXiv API，需网络）。

- [ ] **Step 1: 把爬虫依赖装进 gitignore 覆盖的本地目录**

不用 `python3 -m venv`：Debian/Ubuntu 上常因缺 `python3-venv` 而失败。改用 `pip --target`，无 venv 依赖，且 `.gitignore` 的 `.venv/` 规则覆盖其下全部内容。

Run:
```bash
cd /home/skanda/Projects/embodied/daily-arxiv-jepa
python3 -m pip install -q --target .venv/lib "arxiv>=2.4,<3"
PYTHONPATH=.venv/lib python3 -c "import arxiv; print('arxiv ok')"
```
Expected: 打印 `arxiv ok`

后续所有需要 `arxiv` 的命令都以 `PYTHONPATH=.venv/lib` 前缀运行。

- [ ] **Step 2: 删除 VLA 语料**

Run: `rm papers.md && ls papers.md 2>&1`
Expected: `ls: cannot access 'papers.md': No such file or directory`

VLA 语料仍可从 git 历史恢复：`git show cc76072:papers.md`（7,320,951 字节 / 1918 行，已实测存在）。

- [ ] **Step 3: 本地跑初始化回填**

Run: `PYTHONPATH=.venv/lib python3 scripts/arxiv_crawler.py`
Expected: 打印 `初始化完成，新增 N 篇论文，写入 .../papers.md`，N 约 100–120（120 篇经 6 类主类目白名单过滤后的实际入库数）。耗时约 1–2 分钟（page_size=20、delay=10s 的本地默认值）。

若打印的是"每日更新完成"，说明 papers.md 未被真正删除 —— 回到 Step 2。

- [ ] **Step 4: 校验回填结果的主题与结构**

Run:
```bash
wc -l papers.md
head -2 papers.md
awk -F'|' 'NR>2{print $3}' papers.md | head -12
```
Expected:
- 行数 = 入库论文数 + 2
- 前 2 行为 `| 日期 | 标题 | 链接 | 简要总结 |` 与 `| --- | --- | --- | --- |`
- 标题抽样应为 JEPA / 世界模型 / 联合嵌入 / 隐空间预测主题

- [ ] **Step 5: 本地构建站点**

Run: `python3 scripts/build_site.py`
Expected: 打印 `生成完成：.../site`

- [ ] **Step 6: 校验产物品牌与负载**

Run:
```bash
grep -c "JEPA/WM\|JEPA &amp; World Model Feed" site/index.html
grep -o "<title>[^<]*</title>" site/index.html
grep -o 'content: "JEPA"' site/assets/style.css | head -1
grep -o "%3EJ%3C" site/index.html | head -1
for s in "VLA/WAM" "World Action Model Feed" 'content: "VLA"' "VLA / World Action Model"; do
  printf '%-32s %s\n' "$s" "$(grep -rl -- "$s" site/index.html site/assets/style.css 2>/dev/null | wc -l)"
done
python3 -c "import os;print('data.json %.2f MB'%(os.path.getsize('site/assets/data.json')/1048576))"
ls site/papers | wc -l
```
Expected:
- 第 1 行 ≥ 2；`<title>` 为 `JEPA / 世界模型 每日论文卡 - ArXiv Papers`
- `content: "JEPA"` 与 `%3EJ%3C` 各命中 1 次
- 四个残留串计数全为 `0`
- `data.json` 约 0.05–0.3 MB（120 篇，远低于 spec §7 的 6 MB 推迟阈值）
- `site/papers` 目录数 = 入库论文数

- [ ] **Step 7: 抽查一篇详情页与封面页**

Run:
```bash
d=$(ls site/papers | head -1); echo "$d"
grep -o "<title>[^<]*</title>" "site/papers/$d/index.html"
grep -c "待生成\|摘要还在生成中" "site/papers/$d/index.html" "site/index.html"
```
Expected: 详情页 `<title>` 为论文标题；因摘要尚未生成，页面出现占位文案（CI 生成摘要后消失）——这是预期状态，不是缺陷。

**不要 commit。**

---

### Task 5: README 重写

**Files:**
- Modify: `README.md:1,3,7,41,139` + 新增 2 个小节
- Test: `tests/test_topic_retarget.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `FINAL_QUERY`
- Produces: README 中记录的检索式、`ARXIV_INIT_RESULTS=120`、加深回填的操作步骤、平台前置条件清单

- [ ] **Step 1: 追加失败测试**

```python
def test_readme_retargeted():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "JEPA" in text
    assert FINAL_QUERY in text
    assert 'all:"VLA"' not in text
    assert "ARXIV_INIT_RESULTS" in text
    # 新增的两个小节
    assert "加深历史回填" in text
    assert "GitHub Pages" in text and "GitHub Actions" in text
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m pytest tests/test_topic_retarget.py -v -k readme`
Expected: FAILED

- [ ] **Step 3: 改 `README.md:1`**

```markdown
# JEPA / 世界模型 每日论文卡
```

- [ ] **Step 4: 改 `README.md:3` 首段**

```markdown
这是一个展示 ArXiv 论文精选的静态网站，支持搜索和独立详情页查看功能。项目会自动爬取 JEPA（Joint-Embedding Predictive Architecture）、联合嵌入自监督、隐空间预测与世界模型相关关键词的论文，并使用 AI 生成中文摘要。fork 自 [infinity4b/daily-arxiv-vla](https://github.com/infinity4b/daily-arxiv-vla)，与其共用同一套流水线，仅主题不同；两站内容允许重叠。
```

- [ ] **Step 5: 改 `README.md:7` 功能特性**

```markdown
- 🤖 **自动爬取**: 每日自动从 ArXiv 爬取 JEPA / 联合嵌入 / 隐空间预测 / 世界模型相关最新论文（日均约 7 篇）
```

- [ ] **Step 6: 改 `README.md:41` 环境变量说明**

```markdown
- `ARXIV_QUERY_KEYWORD`: 搜索关键词，支持 arXiv 查询语法（默认检索 JEPA / 联合嵌入 / 隐空间预测 / 世界模型；用 `ti:`/`abs:` 限定字段以避免只在 comments 里蹭词的命中）
- `ARXIV_INIT_RESULTS`: 初始化抓取数量（默认：120，约 2.5 周历史；CI 未覆盖此值，改这里即可生效）
```

- [ ] **Step 7: 改 `README.md:139` 默认配置段**

```markdown
- 搜索关键词：`(ti:"JEPA" OR abs:"JEPA" OR ti:"joint embedding predictive" OR abs:"joint embedding predictive" OR abs:"joint embedding" OR abs:"latent prediction" OR ti:"world model" OR ti:"world models" OR abs:"world model" OR abs:"world models" OR abs:"latent world model")`
- 语料规模：实测 4513 篇（2026-09-07），日均新增约 7 篇
- 每日抓取：80 篇（GitHub Actions 中覆盖，提供约 11 天容错）
- 初始回填：120 篇
```

- [ ] **Step 8: 新增小节「加深历史回填」**（插入到「爬取论文数据」小节之后）

```markdown
### 加深历史回填

`initialize()` 只在 `papers.md` 缺失时触发，之后每次运行都走 `run_daily()`。要把历史从 120 篇加深：

1. 临时把 `.github/workflows/deploy.yml` 里的 `ARXIV_DAILY_RESULTS` 每轮 +100
2. 推送触发一次运行，新入库论文的摘要会标记为「待生成」
3. 后续每日 cron 会继续消化未生成的摘要（`generate_summaries.py` 按 `BATCH_WRITE_SIZE=5` 增量写盘）
4. 达到想要的深度后把 `ARXIV_DAILY_RESULTS` 改回 80

不要一次性设成几百篇：单次运行要生成同等数量的摘要，可能撞上 GitHub Actions 的 6 小时硬限。作业被杀时「提交更改」步骤不会执行，papers.md 不会落盘，下一轮会重复同样的超时。
```

- [ ] **Step 9: 新增小节「平台前置条件」**（插入到「GitHub Pages 部署」小节开头）

```markdown
### 0. 前置条件（首次部署必做）

1. **开启 Pages**：`Settings → Pages → Build and deployment → Source` 选 **GitHub Actions**。未开启时 `deploy` 作业的 `actions/deploy-pages` 会失败。
2. **配置 Secret**：`MODELSCOPE_ACCESS_TOKEN`（必需）。fork **不继承**上游 secrets，必须在本仓库重新配置。
3. **合并到默认分支**：cron 与 Pages 只认默认分支 `master`。在 `dev_jepa` 上的改动必须合入 `master` 才会开始每日更新。
4. **可选 GA4**：`Settings → Secrets and variables → Actions → Variables` 新增 `GA_MEASUREMENT_ID`。

### 本地测试

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/test_topic_retarget.py -v
```

测试只覆盖两类真实失效模式：检索式在多副本间漂移（会让首页标题渲染成查询语法）、品牌改造漏改。测试用 `ast` 提取 `arxiv_crawler.py` 的常量而非 import，因此无需安装 `arxiv` 等运行时依赖。
```

- [ ] **Step 10: 运行全部测试，确认通过**

Run: `python3 -m pytest tests/test_topic_retarget.py -v`
Expected: 17 passed

**不要 commit。**

---

### Task 6: 最终验证与唯一一次提交

**Files:**
- 无新增改动；仅验证与提交

**Interfaces:**
- Consumes: Task 1–5 的全部产出
- Produces: `dev_jepa` 分支上的单个提交

**需要提权：** Step 4（`.git` 在沙箱内只读）。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest tests/test_topic_retarget.py -v`
Expected: 17 passed

- [ ] **Step 2: 全仓残留终检（含 README，范围比测试更广）**

Run:
```bash
grep -rn "VLA/WAM\|daily-arxiv-vla\|World Action Model Feed\|all:\"VLA\"\|content: \"VLA\"" \
  --include="*.py" --include="*.mjs" --include="*.css" --include="*.json" \
  --include="*.yml" --include="*.md" --include="*.example" . \
  | grep -v "^./docs/" | grep -v "^./site/" | grep -v "^./tests/" | grep -v "fork 自" | grep -v node_modules
```
Expected: 无输出（退出码 1）。

排除项及其理由（**执行阶段修正：本步骤初版漏了后两项排除，导致误报 9 行**）：
- `docs/` —— spec 与本计划必须引用旧字符串来说明改动
- `site/` —— 构建产物，由 `build_site.py` 重生
- `tests/` —— 测试文件**必然**把被禁串作为断言数据写出来（`BANNED_BRAND_STRINGS`、`test_index_html_is_jepa_branded` 的 banned 元组）
- `fork 自` —— `README.md` 第 5 行的 fork 溯源链接 `infinity4b/daily-arxiv-vla` 是有意保留的出处说明

自动化测试 `test_no_vla_brand_residue_in_code_and_config` 的扫描范围（`scripts/` + `.github/` + `package.json` + `package-lock.json` + `.env.example`）本来就不含 `README.md` 与 `tests/`，因此无需修改；本步骤是范围更广的人工终检。

- [ ] **Step 3: 复核将要提交的变更集**

Run: `git status --short && git diff --stat`
Expected 变更集恰好为：
```
 M .env.example
 M .github/workflows/deploy.yml
 M README.md
 M package-lock.json
 M package.json
 M papers.md          （Task 4 已删除 VLA 语料并回填 JEPA 语料，故为修改而非删除）
 M scripts/arxiv_crawler.py
 M scripts/build_site.py
 M scripts/fetch_paper_images.py
 M scripts/modern_ui.css
 M site/index.html
?? docs/
?? requirements-dev.txt
?? tests/
```

**关于 `site/index.html`（执行阶段查明的 fork 既有矛盾）**：`.gitignore` 第 7 行忽略 `site/`，但 `site/index.html` 是**已被跟踪**的文件（`git ls-files site/` 只返回它一个），且 `deploy.yml:100` 用 `git add -f site` 强制提交整个 site 目录。因此本次重建后它会显示为 ` M`，**应当一并提交**——否则仓库里会留下一个 VLA 品牌的已跟踪文件。这个 gitignore 与 force-add 相互矛盾的状况是 fork 自带的，不在本次范围内改动。

不得出现 `.env`、`.venv/`、`node_modules/`（均在 `.gitignore` 中）。

- [ ] **Step 4: 唯一一次提交（需提权）**

Run:
```bash
git add -A && git commit -F - <<'MSG'
feat: 主题重定向到 JEPA / 世界模型每日论文卡

检索式（实测 4513 篇语料，日均约 7 篇，CORE 类目占 93%）：
- 覆盖 JEPA / 联合嵌入自监督 / 隐空间预测 / 世界模型
- 用 ti:/abs: 限定字段，避免只在 comments/journal-ref 蹭词的命中
- 实测拒绝 latent space（+9955 篇潜空间生成模型噪声）与
  latent dynamics（+450 篇多为动力系统/降阶建模）；采纳 latent prediction（+61 篇全部相关）
- 不排除 VLA/WAM，与 daily-arxiv-vla 内容重叠已被接受

品牌：站点标签/brand-mark/eyebrow/搜索 placeholder/favicon 字母/hero 水印/包名/UA
数据：删除 1917 行 VLA 语料（可从 git 历史 cc76072 恢复），本地回填 JEPA 语料
CI：删除 deploy.yml 两处 ARXIV_QUERY_KEYWORD 覆盖，消除查询串多副本漂移导致
    首页标题渲染成查询语法的隐患；ARXIV_INIT_RESULTS 默认 500 -> 120 以留出 6h 余量
测试：新增 tests/test_topic_retarget.py（19 项），只覆盖字符串漂移与品牌漏改两类失效模式

设计与计划见 docs/superpowers/
MSG
```
Expected: 提交成功，`git log --oneline -1` 显示该提交。

- [ ] **Step 5: 交付给用户的手动步骤清单**

提交后向用户说明（代码无法代办）：
1. `Settings → Pages → Source` 选 **GitHub Actions**（已查证 `has_pages: false`）
2. 配置 Secret `MODELSCOPE_ACCESS_TOKEN`（fork 不继承）
3. 可选：配置 Variable `GA_MEASUREMENT_ID`
4. 把 `dev_jepa` 合入 `master` 并推送 —— cron 与 Pages 只认默认分支
5. 首次 Actions 运行约 2–3 小时（120 篇摘要）；若超时，把 `ARXIV_INIT_RESULTS` 降到 60 再跑

spec §10 验收标准第 5 条（合并后 CI 绿、Pages 可访问、次日 cron 自动新增）**只能由用户合并到 `master` 后验证**，不在本计划的代码任务范围内。

---

## Self-Review

**1. Spec coverage**

| Spec 章节 | 对应任务 |
| --- | --- |
| §3 定稿检索式 | Task 1 Step 4–5, 9 |
| §4 类目策略不动 | Global Constraints（无任务 = 正确，不需改动） |
| §5.1 数据重置 | Task 4 Step 2 |
| §5.2 回填规模（INIT=120 / DAILY 保持 80） | Task 1 Step 6；Task 3 Step 7 保留 `ARXIV_DAILY_RESULTS: 80`；测试 `test_init_results_default_is_120` |
| §5.3 加深历史方法 | Task 5 Step 8 |
| §6.1 检索式与常量 | Task 1 |
| §6.2 品牌文案（含补入的 favicon） | Task 2 |
| §6.3 环境变量与 CI | Task 3 |
| §6.4 数据与文档 | Task 4 + Task 5 |
| §6.5 测试六项 | Task 1（断言 1–3）+ Task 2（4–5）+ Task 3（6）+ Task 5（README） |
| §7 推迟项 | 不实现；Global Constraints 明确禁止 |
| §8 平台前置条件 | Task 5 Step 9 + Task 6 Step 5 |
| §9 风险缓解 | Task 6 Step 5 第 5 条；README「加深历史回填」小节的 6h 警告 |
| §10 验收标准 1–4 | Task 6 Step 1–2、Task 4 Step 3–7 |
| §10 验收标准 5（合并后 CI/Pages） | Task 6 Step 5（用户手动，代码不可代办） |

无遗漏。

**2. Placeholder scan:** 无 TBD/TODO；每个代码步骤均给出完整可粘贴内容；每个验证步骤均给出命令与预期输出。

**3. Type consistency:**
- `module_constant(relpath: str, name: str) -> str` 在 Task 1 定义，Task 1/3 的测试一致调用
- `load_build_site()` 在 Task 1 定义，Task 2 的测试使用
- `FINAL_QUERY` / `TOPIC_LABEL` / `VLA_TERMS` / `REQUIRED_TERMS` 在 Task 1 定义，Task 3/5 复用
- `iter_scanned_files()` 在 Task 3 定义并使用
- `generate_head(title, description, stylesheet_prefix="")`、`get_arxiv_keyword_label()`、`generate_index_html()`、`generate_style_css()` 签名均已对源码核实

**4. 测试计数一致性:** Task 1 = 6，Task 2 累计 11，Task 3 累计 16，Task 5 累计 17。各 Step 的 Expected 已逐个核对（含 Task 1 中 2 个改动前即通过的回归护栏测试）。

**5. 已核实的本地环境事实（避免计划基于假设）:**
- Python 3.14.7；`pytest`、`PIL` 可用；`arxiv`/`dotenv`/`openai`/`tqdm` 缺失 → 故用 AST 而非 import
- `ast.literal_eval` 对隐式字符串拼接的 `DEFAULT_ARXIV_QUERY` 可正常求值（已实测返回 125 字符的现值）
- `generate_style_css()` 从磁盘读 `scripts/modern_ui.css`（build_site.py:1168-1169）→ CSS 水印可测
- 改动前 `generate_index_html()` 含 `VLA/WAM` 与 `World Action Model Feed`，`generate_head()` 含 `%3EV%3C`（已实测）→ 新测试会先真失败


---

## 执行记录（实际执行与本计划的偏差）

本计划已于 2026-09-07 在 `dev_jepa` 分支按 inline execution 执行完毕。以下为执行中产生的偏差，均已核实：

| # | 偏差 | 处置 |
| --- | --- | --- |
| 1 | **测试总数 17 → 18**。执行 Task 6 时对护栏测试做变异验证（给 `build_site.py` 查询串尾部注入 1 个空格），发现 2 个护栏测试确实变红，但 `get_arxiv_keyword_label()` **仍返回正常标签** —— 说明 spec 初稿断言的"任一副本走样即毁标题"机制**过宽**：该函数比较的是 env 与 build_site **自身**默认值，env 未设置时恒等成立。逐场景实测后追加特征测试 `test_env_drift_turns_query_into_site_title` 固化真实机制（env = 默认值 + 1 空格 → 返回 261 字符查询语法），并更正 spec §6.3 与 §9、以及测试文件 docstring | 已追加测试；spec 已更正；Task 3 的累计计数由 16 变为 17，Task 5/6 由 17 变为 **18** |
| 2 | 查明 `arxiv_crawler.py` 与 `build_site.py` **都不调用 `load_dotenv()`**，故 `.env` 里的 `ARXIV_QUERY_KEYWORD` 对二者零运行时作用，`deploy.yml` 曾是该变量唯一实际注入点 | README 补 ⚠️ 说明（不改代码，改它会变更 CI 语义）；spec §6.3/§9 已记录 |
| 3 | **README 实改 11 处**，计划列 9 处：额外补「项目结构」树（`tests/`、`docs/superpowers/`、`requirements-dev.txt`、`modern_ui.css`、根目录名 `arxiv/` → `daily-arxiv-jepa/`）与「访问网站」真实地址 | 已改 |
| 4 | **Task 6 Step 2 的人工 grep 预期错误**：初版排除项漏了 `tests/`（测试文件必然把被禁串作为断言数据写出）与 README 第 5 行 fork 溯源链接，导致误报 9 行 | Step 2 已就地修正排除项；自动化测试 `test_no_vla_brand_residue_in_code_and_config` 的扫描范围本来就正确，无需改 |
| 5 | **`site/index.html` 是已跟踪文件**（`git ls-files site/` 仅返回它），尽管 `.gitignore:7` 忽略 `site/`、`deploy.yml:100` 又 `git add -f site`。重建后显示为 ` M` | 一并提交，否则仓库会留下 VLA 品牌的已跟踪文件；该 gitignore 与 force-add 的矛盾是 fork 自带，本次不改 |
| 6 | Task 4 回填实测：`initialize()` 分支正确触发，**新增 112 篇**（120 篇经 6 类白名单过滤，保留率 93.3%，与 spec §2.4 实测的 93% 吻合），耗时 60 秒；日期跨度 2026-08-23 → 09-04。同时验证 260 字符括号 + `ti:`/`abs:` 查询串**经 `arxiv` 库本身也能正常工作**（此前只用原始 API 验证过） | 无需处置，记录为验收证据 |
| 7 | Task 4 Step 6 的 `data.json` 单篇 0.77 KB 是**占位摘要**下的数值；CI 生成摘要后会涨到 VLA 站实测的 2.1 KB/篇 | spec §7 的 6 MB 阈值对应约 **2926 篇**（约 12 个月后），与 §2.5 外推一致 |

**最终验证证据（提交前新鲜运行）：** `python3 -m pytest tests/test_topic_retarget.py -v` → **18 passed**；站点构建产物 `site/papers` 与 `site/covers` 各 112 个目录，`<title>` 为 `JEPA / 世界模型 每日论文卡 - ArXiv Papers`，6 项品牌残留全为 0。
