# Purpose: Verify approved human inputs, immutable preparation and published experiment provenance.
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_human_preparation_preserves_input_and_rejects_changes(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(EVIDENCE / "demonstrations", source / "demonstrations")
    shutil.copyfile(EVIDENCE / "manifest.json", source / "manifest.json")
    output = tmp_path / "output"
    manifest = json.loads((source / "manifest.json").read_text())
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src/backend/orchestrator")}
    workspace = tmp_path / "service"
    shutil.copytree(ROOT / "contracts", workspace / "contracts")
    shutil.copytree(
        ROOT / "src/backend/orchestrator/src/stroke_processing",
        workspace / "src/stroke_processing",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copyfile(ROOT / "src/backend/orchestrator/config.json", workspace / "config.json")

    def prepare():
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "src/scripts/evaluate.py"),
                "prepare",
                "--source",
                str(source),
                "--output",
                str(output),
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )

    result = prepare()
    assert result.returncode == 0, result.stderr
    prepared_path = output / "prepared.json"
    prepared = json.loads(prepared_path.read_text())
    original = digest(prepared_path)
    assert prepared["manifest"] == manifest
    for sample in manifest["samples"]:
        path = source / "demonstrations" / (sample["demonstration_id"] + ".json")
        assert digest(path) == sample["sha256"]
        skill_path = output / sample["id"] / "skill.json"
        skill = json.loads(skill_path.read_text())
        assert skill["source"]["type"] == "human_capture"
        assert skill["source"]["demonstration_id"] == sample["demonstration_id"]
        assert digest(skill_path) == prepared["skill_sha256"][sample["id"]]
    assert prepare().returncode != 0
    assert digest(prepared_path) == original
    path.write_bytes(path.read_bytes() + b"\n")
    changed = prepare()
    assert changed.returncode != 0 and "checksum mismatch" in changed.stderr
    assert digest(prepared_path) == original


def test_published_evaluation_covers_the_declared_matrix_and_current_sources():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    report = json.loads((EVIDENCE / "results.json").read_text())
    prepared = report["prepared"]
    assert report["complete"] and report["finished_at"] >= report["started_at"]
    assert prepared["manifest"] == manifest
    assert prepared["manifest_sha256"] == digest(EVIDENCE / "manifest.json")
    assert prepared["processing_config"] == json.loads(
        (ROOT / "src/backend/orchestrator/config.json").read_text()
    )
    assert report["simulation_config"] == json.loads(
        (ROOT / "src/backend/simulation/config.json").read_text()
    )
    assert prepared["processing_code_sha256"] == digest(
        ROOT / "src/backend/orchestrator/src/stroke_processing/stroke_processing.py"
    )
    assert report["evaluation_code_sha256"] == digest(ROOT / "src/scripts/evaluate.py")
    for name, expected in prepared["contracts_sha256"].items():
        assert digest(ROOT / "contracts" / name) == expected
    for name, expected in report["simulation_code_sha256"].items():
        assert digest(ROOT / "src/backend/simulation" / name) == expected
    expected = set(
        itertools.product(
            [s["id"] for s in manifest["samples"]], manifest["methods"], manifest["poses"]
        )
    )
    actual = [(c["sample"], c["method"], c["pose"]) for c in report["cases"]]
    assert len(actual) == len(expected) and set(actual) == expected
    plans = {}
    for case in report["cases"]:
        assert {
            "skill.json",
            "robot-plan.json",
            "trace.json",
            "simulation-result.json",
            "simulation.mp4",
        } <= case["artifact_sha256"].keys()
        assert case["artifact_sha256"]["skill.json"] == prepared["skill_sha256"][case["sample"]]
        key = (case["sample"], case["pose"])
        plan_hash = case["artifact_sha256"]["robot-plan.json"]
        assert plans.setdefault(key, plan_hash) == plan_hash
        assert case["checks"]["frames"] > 10
        if case["method"] == "compensated":
            assert case["result"]["success"], case
            config, result = report["simulation_config"], case["result"]
            assert result["mean_path_error_m"] <= config["drawing_tolerance"]
            assert result["max_path_error_m"] <= config["max_path_error"]
            assert result["max_shape_error_m"] <= config["shape_tolerance"]
            assert result["contact_coverage"] >= config["min_contact_coverage"]
            assert result["out_of_paper_samples"] == 0
            assert result["strokes_completed"] == result["stroke_count"]
            assert "simulator-final.png" in case["artifact_sha256"]
            assert case["checks"]["measured_ink_points"] > 0
            assert case["checks"]["final_frame_mae"] < 5
        if case["pose"] == "default":
            for name in ("simulator-final.png", "simulation.mp4"):
                if name not in case["artifact_sha256"]:
                    continue
                path = EVIDENCE / "examples" / case["sample"] / case["method"] / name
                assert digest(path) == case["artifact_sha256"][name]
