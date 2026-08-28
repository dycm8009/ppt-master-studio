#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "studio" / "scripts" / "stage1_mini_app.py"

spec = importlib.util.spec_from_file_location("stage1_mini_app", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_project(base: Path) -> Path:
    project = base / "project"
    confirm = project / "confirm_ui"
    confirm.mkdir(parents=True)
    recommendation = {
        "stage": "stage1",
        "lang": "zh",
        "primary_language": "zh-CN",
        "recommend": {"canvas": "ppt169"},
        "audience": {"value": "C++ 开发工程师"},
        "communication_intent": {"value": "解释架构决策并形成共识"},
        "audience_outcome": {"value": "能够选择可落地的方案"},
        "core_message": {"value": "AI 友好架构需要可观测、可组合和清晰边界"},
        "delivery_context": {"value": "20 分钟技术分享"},
        "artifact_afterlife": {"value": "作为后续设计评审参考"},
        "content_divergence": {"value": "", "locked": True},
    }
    options = {
        "schema_version": 1,
        "phase": "template",
        "lang": "zh",
        "default_mode": "free_design",
        "explicit_workspace_roots": [],
    }
    (confirm / "recommendations.stage1.json").write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")
    (confirm / "template_options.json").write_text(json.dumps(options, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        project = write_project(Path(td))
        ctx = mod._load_stage1(project)
        assert ctx["canvas"] == "ppt169"
        assert ctx["primary_language"] == "zh-CN"
        assert ctx["prose"]["content_divergence"]["locked"] is True
        assert set(ctx["template"]["library"]) == {"brand", "style", "layout", "deck"}
        assert len(ctx["context_sha256"]) == 64

        page = mod.render(project)
        assert "<!doctype html>" in page
        assert "确认沟通契约与模板选择" in page
        assert "ppt-master-studio-stage1-mini-app-response/v1" in page
        assert "recommendations.stage1.json" not in page
        assert "app_block" not in page and "GenUI" not in page
        assert "navigator.clipboard.writeText" in page
        assert "不会创建或伪造 Confirm UI receipt" in page

        valid = {
            "schema": mod.RESPONSE_SCHEMA,
            "surface": "stage1",
            "status": "user-confirmed",
            "context_sha256": ctx["context_sha256"],
            "values": {
                "primary_language": "zh-CN",
                "canvas": "ppt169",
                "audience": "C++ 开发工程师",
                "communication_intent": "解释架构决策并形成共识",
                "audience_outcome": "能够选择可落地的方案",
                "core_message": "AI 友好架构需要可观测、可组合和清晰边界",
                "delivery_context": "20 分钟技术分享",
                "artifact_afterlife": "作为后续设计评审参考",
                "content_divergence": "",
                "template_choice": {
                    "mode": "free_design",
                    "library": {"brand": None, "style": None, "layout": None, "deck": None},
                    "specified_workspace_root": None,
                },
            },
        }
        report = mod.validate_response(project, valid)
        assert report["status"] == "passed", report

        stale = json.loads(json.dumps(valid, ensure_ascii=False))
        stale["context_sha256"] = "0" * 64
        report = mod.validate_response(project, stale)
        assert report["status"] == "failed"
        assert any("context_sha256" in e for e in report["errors"])

        locked = json.loads(json.dumps(valid, ensure_ascii=False))
        locked["values"]["content_divergence"] = "changed"
        report = mod.validate_response(project, locked)
        assert report["status"] == "failed"
        assert any("locked field changed" in e for e in report["errors"])

        invalid_template = json.loads(json.dumps(valid, ensure_ascii=False))
        invalid_template["values"]["template_choice"]["mode"] = "templates"
        report = mod.validate_response(project, invalid_template)
        assert report["status"] == "failed"
        assert any("requires at least one selection" in e for e in report["errors"])

    print("stage1 mini-app integration: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
