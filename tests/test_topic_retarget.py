"""主题重定向回归测试（JEPA / 世界模型）。

本次改动没有新增业务逻辑，因此只测两类真实失效模式：
1. 检索式在多副本间漂移。已实测的精确机制：get_arxiv_keyword_label() 拿
   **环境变量**与 build_site 自身默认值比较，env 差一个空格就会把 261 字符的
   查询语法渲染成首页 H1、<title> 与 meta description（见
   test_env_drift_turns_query_into_site_title）。env 未设置时该比较恒等成立，
   所以 crawler 与 build_site 的默认值漂移不会破坏标题，但会让"爬取的主题"与
   "站点标签逻辑假设的主题"不一致，且任何从其中一个文件复制出去的 env 覆盖都
   会与另一个文件不匹配 —— 故仍需强制两者逐字相等。
   本仓库已删除 deploy.yml 的两处 ARXIV_QUERY_KEYWORD 覆盖，关闭了唯一入口。
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
    """实测拒绝的两个隐空间口径不得回流（回归护栏，改动前即通过属预期）。"""
    query = module_constant("scripts/arxiv_crawler.py", "DEFAULT_ARXIV_QUERY")
    assert "latent space" not in query
    assert "latent dynamics" not in query
    assert "ANDNOT" not in query


def test_init_results_default_is_120():
    source = (ROOT / "scripts" / "arxiv_crawler.py").read_text(encoding="utf-8")
    assert 'os.getenv("ARXIV_INIT_RESULTS", "120")' in source


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
    assert f'{TOPIC_LABEL} <span class="site-title-nowrap">每日论文卡</span>' in html
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


def test_readme_retargeted():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "JEPA" in text
    assert FINAL_QUERY in text
    assert 'all:"VLA"' not in text
    assert "ARXIV_INIT_RESULTS" in text
    # 新增的两个小节
    assert "加深历史回填" in text
    assert "GitHub Pages" in text and "GitHub Actions" in text


def test_env_drift_turns_query_into_site_title(monkeypatch):
    """特征测试（characterization）：固化已实测的危害机制。

    get_arxiv_keyword_label() 拿 env 值与 build_site 自身的默认查询串比较，不相等
    就把 env 原样当站点标题返回。实测：env 只差一个空格，首页 H1、<title>、
    meta description、详情页与封面页标题就会全部变成 261 字符的查询语法。

    注意 crawler 与 build_site 之间的默认值漂移**不会**触发此问题（env 未设置时
    比较恒等成立）；真正的入口是环境变量，因此 deploy.yml 不得覆盖
    ARXIV_QUERY_KEYWORD（见 test_deploy_yml_has_no_query_override）。
    """
    bs = load_build_site()
    drifted = bs.DEFAULT_ARXIV_QUERY + " "
    monkeypatch.setenv("ARXIV_QUERY_KEYWORD", drifted)
    label = bs.get_arxiv_keyword_label()
    assert label == drifted
    assert "ti:" in label and "abs:" in label
    assert label != TOPIC_LABEL
