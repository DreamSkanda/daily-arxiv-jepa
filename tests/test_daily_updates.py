"""离线回归：可选摘要不能丢失论文，失败后可重试且不覆盖已有摘要。"""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]
HEADER = "| 日期 | 标题 | 链接 | 简要总结 |\n| --- | --- | --- | --- |\n"
OLD_ROW = (
    "| 2026-09-04 | Existing JEPA paper | https://arxiv.org/abs/2609.00001 | "
    "<details><summary>展开</summary>已有中文摘要，必须保留。</details> |\n"
)
NEW_LINK = "https://arxiv.org/abs/2610.00001"
NEW_ROW = (
    f"| 2026-10-30 | New world model paper | {NEW_LINK} | "
    "<details><summary>展开</summary>待生成</details> |\n"
)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def summaries(monkeypatch, tmp_path):
    module = load_script("generate_summaries")
    papers = tmp_path / "papers.md"
    papers.write_text(HEADER + NEW_ROW + OLD_ROW, encoding="utf-8")
    monkeypatch.setattr(module, "get_papers_md_path", lambda: str(papers))
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    monkeypatch.delenv("MODELSCOPE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("MODELSCOPE_MODELS", "test-model")
    monkeypatch.setenv("API_MAX_RETRIES", "1")
    monkeypatch.setenv("HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("BATCH_WRITE_SIZE", "1")
    # No test may make real arXiv or ModelScope requests.
    monkeypatch.setattr(module.requests, "get", Mock(return_value=Mock(text="<article>Paper</article>")))
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="## 论文概述\n- 测试中文摘要"))]
    )
    monkeypatch.setattr(module, "OpenAI", Mock(return_value=client))
    return module, papers, client


@pytest.mark.parametrize("token", [None, "", "   "])
def test_missing_key_keeps_file_byte_identical(summaries, monkeypatch, token):
    module, papers, _ = summaries
    if token is not None:
        monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", token)
    before = papers.read_bytes()
    assert module.update_papers_md() == (1, 0)
    assert papers.read_bytes() == before
    module.OpenAI.assert_not_called()
    module.requests.get.assert_not_called()


def test_no_pending_papers_needs_no_client(summaries):
    module, papers, _ = summaries
    papers.write_text(HEADER + OLD_ROW, encoding="utf-8")
    assert module.update_papers_md() == (0, 0)
    module.OpenAI.assert_not_called()


def test_cli_without_key_exits_successfully(summaries):
    _, papers, _ = summaries
    scripts = papers.parent / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts/generate_summaries.py", scripts / "generate_summaries.py")
    before = papers.read_bytes()
    result = subprocess.run(
        [sys.executable, str(scripts / "generate_summaries.py")],
        env={**os.environ, "MODELSCOPE_ACCESS_TOKEN": ""},
        capture_output=True, text=True, check=True,
    )
    assert "保留「待生成」" in result.stdout
    assert papers.read_bytes() == before


def test_successful_batch_tail_is_saved(summaries, monkeypatch):
    module, papers, _ = summaries
    monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    monkeypatch.setenv("BATCH_WRITE_SIZE", "5")
    assert module.update_papers_md() == (1, 1)
    assert OLD_ROW in papers.read_text(encoding="utf-8")
    assert "测试中文摘要" in papers.read_text(encoding="utf-8")


def test_client_initialization_failure_keeps_pending(summaries, monkeypatch):
    module, papers, _ = summaries
    monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    module.OpenAI.side_effect = ValueError("invalid client configuration")
    before = papers.read_bytes()
    assert module.update_papers_md() == (1, 0)
    assert papers.read_bytes() == before


@pytest.mark.parametrize("failure", ["api_error", "quota", "empty", "http_error"])
def test_service_failure_keeps_pending_and_later_recovers(summaries, monkeypatch, failure):
    module, papers, client = summaries
    monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    response = client.chat.completions.create.return_value
    if failure == "empty":
        client.chat.completions.create.return_value = SimpleNamespace(choices=[])
    elif failure == "http_error":
        module.requests.get.side_effect = requests.exceptions.Timeout("arXiv timed out")
    else:
        message = "rate limit exceeded" if failure == "quota" else "service unavailable"
        client.chat.completions.create.side_effect = RuntimeError(message)
    before = papers.read_bytes()
    assert module.update_papers_md() == (1, 0)
    assert papers.read_bytes() == before

    # A later process starts with a fresh per-run rate-limit cache.
    module.RATE_LIMITED_MODELS.clear()
    module.requests.get.side_effect = None
    client.chat.completions.create.side_effect = None
    client.chat.completions.create.return_value = response
    assert module.update_papers_md() == (1, 1)
    saved = papers.read_text(encoding="utf-8")
    assert OLD_ROW in saved
    assert "待生成" not in saved
    assert "测试中文摘要" in saved
    assert f"| 2026-10-30 | New world model paper | {NEW_LINK} |" in saved
    calls = client.chat.completions.create.call_count
    assert module.update_papers_md() == (0, 0)
    assert client.chat.completions.create.call_count == calls


def test_one_failed_paper_does_not_discard_other_summaries(summaries, monkeypatch):
    module, papers, _ = summaries
    monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    second = NEW_ROW.replace("2610.00001", "2610.00002")
    papers.write_text(HEADER + NEW_ROW + second + OLD_ROW, encoding="utf-8")
    monkeypatch.setattr(module, "generate_summary_for_link", Mock(side_effect=[RuntimeError("failed"), "成功摘要"]))
    assert module.update_papers_md() == (2, 1)
    saved = papers.read_text(encoding="utf-8")
    assert NEW_ROW in saved
    assert OLD_ROW in saved
    assert saved.count("待生成") == 1
    assert "成功摘要" in saved


def test_failed_atomic_replace_preserves_entire_file(summaries, monkeypatch):
    module, papers, _ = summaries
    monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    before = papers.read_bytes()
    monkeypatch.setattr(module.os, "replace", Mock(side_effect=OSError("disk error")))
    with pytest.raises(OSError, match="disk error"):
        module.update_papers_md()
    assert papers.read_bytes() == before
    assert list(papers.parent.iterdir()) == [papers]


def workflow_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
    return workflow, workflow["jobs"]["build"]["steps"]


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.mark.parametrize("mode", ["missing_key", "service_failure", "success"])
def test_daily_pipeline_saves_papers_and_builds_site(summaries, monkeypatch, tmp_path, mode):
    module, papers, client = summaries
    repo = papers.parent
    remote = tmp_path / "remote.git"
    run("git", "init", "--bare", str(remote), cwd=repo)
    run("git", "init", "-b", "master", cwd=repo)
    run("git", "config", "user.name", "Regression Test", cwd=repo)
    run("git", "config", "user.email", "test@example.invalid", cwd=repo)
    run("git", "remote", "add", "origin", str(remote), cwd=repo)
    papers.write_text(HEADER + OLD_ROW, encoding="utf-8")
    run("git", "add", "papers.md", cwd=repo)
    run("git", "commit", "-m", "Existing papers", cwd=repo)
    run("git", "push", "-u", "origin", "master", cwd=repo)

    crawler = load_script("arxiv_crawler")
    collector = crawler.ArxivCollector(str(papers))
    new_paper = SimpleNamespace(
        published=datetime(2026, 10, 30), title="New world model paper",
        entry_id=NEW_LINK + "v1", primary_category="cs.AI",
    )
    monkeypatch.setattr(collector, "_search", lambda _: [new_paper])
    assert collector.run_daily() == 1
    assert collector.run_daily() == 0  # Rerunning cannot duplicate the new paper.

    _, steps = workflow_steps()
    by_id = {step["id"]: step for step in steps if "id" in step}
    run("bash", "-e", "-c", by_id["save_papers"]["run"], cwd=repo)
    checkpoint = run("git", "--git-dir", str(remote), "show", "master:papers.md", cwd=repo)
    assert checkpoint == HEADER + NEW_ROW + OLD_ROW

    if mode != "missing_key":
        monkeypatch.setenv("MODELSCOPE_ACCESS_TOKEN", "fake-test-token")
    if mode == "service_failure":
        client.chat.completions.create.side_effect = RuntimeError("service unavailable")
    assert module.update_papers_md() == (1, int(mode == "success"))

    # Run the real website builder with isolated input/output paths.
    scripts = repo / "scripts"
    scripts.mkdir()
    for name in ("build_site.py", "modern_ui.css"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    run(sys.executable, "scripts/build_site.py", cwd=repo)
    run("bash", "-e", "-c", by_id["save_site"]["run"], cwd=repo)
    saved = run("git", "--git-dir", str(remote), "show", "master:papers.md", cwd=repo)
    assert OLD_ROW in saved
    assert saved.count(NEW_LINK) == 1
    assert ("待生成" in saved) == (mode != "success")
    data = json.loads(run("git", "--git-dir", str(remote), "show", "master:site/assets/data.json", cwd=repo))
    assert len(data) == 2
    assert "New world model paper" in json.dumps(data)
    assert "2026-10-30" in json.dumps(data)
    assert NEW_LINK in json.dumps(data)
    detail_pages = list((repo / "site/papers").glob("*/index.html"))
    assert len(detail_pages) == 2
    if mode != "success":
        assert any("待生成" in page.read_text(encoding="utf-8") for page in detail_pages)


def test_workflow_keeps_optional_summary_off_the_failure_path():
    workflow, steps = workflow_steps()
    positions = {step.get("id"): i for i, step in enumerate(steps) if step.get("id")}
    summary = steps[positions["summaries"]]
    assert positions["save_papers"] < positions["summaries"] < positions["save_site"]
    assert summary["continue-on-error"] is True
    assert 0 < summary["timeout-minutes"] <= 20
    assert summary["env"]["BATCH_WRITE_SIZE"] == 1
    assert "if" not in steps[positions["save_site"]]
    assert any(step.get("uses", "").startswith("actions/upload-pages-artifact@") for step in steps)
    assert workflow["jobs"]["deploy"]["needs"] == "build"
    for step in steps:
        if "arxiv_crawler.py" in step.get("run", ""):
            assert not step.get("continue-on-error", False)
            assert "MODELSCOPE_ACCESS_TOKEN" not in step.get("env", {})
