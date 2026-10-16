# Purpose: Reproduce approved human drawing evidence with the existing processing and physics modules.
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def dataset(source):
    manifest = read(source / "manifest.json")
    names, identities = set(), set()
    for sample in manifest["samples"]:
        name, identity = sample["id"], sample["demonstration_id"]
        if (
            not re.fullmatch(r"[a-z0-9-]+", name)
            or not re.fullmatch(r"[a-f0-9]{32}", identity)
            or name in names
            or identity in identities
        ):
            raise ValueError("Invalid or duplicate evidence sample.")
        names.add(name)
        identities.add(identity)
        path = source / "demonstrations" / (identity + ".json")
        raw = read(path)
        if (
            digest(path) != sample["sha256"]
            or raw["source"]["type"] != "human_capture"
            or raw["device"]["pointer_type"] != sample["pointer_type"]
            or len(raw["strokes"]) != sample["strokes"]
            or sum(len(s["points"]) for s in raw["strokes"]) != sample["samples"]
        ):
            raise ValueError(f"Evidence provenance/checksum mismatch: {name}.")
    if (
        not names
        or not manifest["poses"]
        or set(manifest["methods"])
        != {
            "compensated",
            "uncompensated",
        }
    ):
        raise ValueError("Evidence needs captures, poses and the two declared methods.")
    if manifest["methods"] != {
        "compensated": {},
        "uncompensated": {"tracking_lead_seconds": 0, "tracking_integral_gain": 0},
    }:
        raise ValueError("The ablation may change only lead and integral compensation.")
    if any(not re.fullmatch(r"[a-z0-9-]+", name) for name in manifest["poses"]):
        raise ValueError("Invalid evidence pose name.")
    return manifest


def prepare(source, output):
    from src.stroke_processing.stroke_processing import extract_skill

    manifest = dataset(source)
    if (output / "prepared.json").exists():
        raise ValueError("Use a new output directory; prepared evidence is immutable.")
    config = read(Path("config.json"))
    skills = {}
    for sample in manifest["samples"]:
        raw = read(source / "demonstrations" / (sample["demonstration_id"] + ".json"))
        skill = extract_skill(raw, sample["demonstration_id"], Path("contracts"), config)
        folder = output / sample["id"]
        folder.mkdir(parents=True, exist_ok=True)
        write(folder / "skill.json", skill)
        skills[sample["id"]] = digest(folder / "skill.json")
    write(
        output / "prepared.json",
        {
            "manifest": manifest,
            "manifest_sha256": digest(source / "manifest.json"),
            "processing_config": config,
            "processing_code_sha256": digest(Path("src/stroke_processing/stroke_processing.py")),
            "contracts_sha256": {
                p.name: digest(p) for p in sorted(Path("contracts").glob("*.json"))
            },
            "skill_sha256": skills,
        },
    )
    print(f"Prepared {len(skills)} immutable human skills.", flush=True)


def verify_artifacts(folder, skill, result):
    import imageio.v2 as imageio
    import numpy as np

    trace = read(folder / "trace.json")
    measured = {
        (p["t"], p["stroke"], *p["actual_local"])
        for p in trace["samples"]
        if p["phase"] == "draw" and p["contact"] and p["inside_paper"]
    }
    if any((p["t"], p["stroke"], *p["local"]) not in measured for p in trace["ink"]):
        raise ValueError("Ink does not agree with independently measured tip samples.")
    if any(p["ink_radius"] is not None for p in trace["samples"] if p["phase"] != "draw"):
        raise ValueError("Ink was deposited outside the drawing phase.")
    if read(folder / "skill.json") != skill:
        raise ValueError("A run changed the frozen drawing skill.")
    frames = trace["video"]["frames"]
    if (
        trace["video"]["renderer"] != "MuJoCo"
        or not frames
        or frames[0]["ink_count"] != 0
        or frames[-1]["ink_count"] > len(trace["ink"])
        or (result["success"] and frames[-1]["ink_count"] != len(trace["ink"]))
    ):
        raise ValueError("Native frame provenance is incomplete.")
    reader = imageio.get_reader(str(folder / "simulation.mp4"), input_params=["-threads", "1"])
    try:
        count = reader.count_frames()
        if count != len(frames):
            raise ValueError("Encoded video frame count differs from simulator samples.")
        final = reader.get_data(count - 1)
        difference = None
        if (folder / "simulator-final.png").exists():
            rendered = imageio.imread(folder / "simulator-final.png")
            difference = float(np.abs(final.astype(float) - rendered).mean())
            if difference >= 5 or final.std() <= 10:
                raise ValueError("Encoded final frame does not match the native simulator render.")
        elif result["success"]:
            raise ValueError("A successful run has no native final render.")
    finally:
        reader.close()
    return {
        "measured_ink_points": len(trace["ink"]),
        "frames": count,
        "final_frame_mae": difference,
        "unrecorded_final_ink_points": len(trace["ink"]) - frames[-1]["ink_count"],
    }


def evaluate(source, output):
    from src.drawing_environment.drawing_environment import (
        CONFIG,
        DrawingEnvironment,
        validate_config,
    )
    from src.robot_control.robot_control import execute
    from src.skill_to_robot.skill_to_robot import paper_pose, robot_plan, validate_skill

    manifest = dataset(source)
    prepared = read(output / "prepared.json")
    if prepared["manifest_sha256"] != digest(source / "manifest.json"):
        raise ValueError("The dataset changed after preparation.")
    if (output / "results.json").exists():
        raise ValueError(
            "Use a new output directory; completed or partial results are never resumed."
        )
    for pose in manifest["poses"].values():
        paper_pose(CONFIG, pose)
    for overrides in manifest["methods"].values():
        validate_config({**CONFIG, **overrides})
    report = {
        "version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": os.environ.get("SOURCE_REVISION", "unrecorded"),
        "source_tree_dirty": os.environ.get("SOURCE_TREE_DIRTY", "unknown"),
        "prepared": prepared,
        "simulation_config": CONFIG,
        "evaluation_code_sha256": digest(Path(__file__)),
        "simulation_code_sha256": {
            str(p): digest(p) for p in sorted(Path("src").glob("*/*.py")) if p.name != "__init__.py"
        },
        "runtime": {
            "python": platform.python_version(),
            **{p: version(p) for p in ("robosuite", "mujoco", "numpy", "imageio")},
            "thread_limits": {
                key: os.environ.get(key)
                for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "cases": [],
    }
    environment = DrawingEnvironment(CONFIG)
    try:
        for sample in manifest["samples"]:
            frozen = output / sample["id"] / "skill.json"
            if digest(frozen) != prepared["skill_sha256"][sample["id"]]:
                raise ValueError("Prepared skill checksum mismatch.")
            skill = read(frozen)
            validate_skill(skill, Path("contracts"), CONFIG)
            for pose_name, pose in manifest["poses"].items():
                for method, overrides in manifest["methods"].items():
                    folder = output / sample["id"] / method / pose_name
                    folder.mkdir(parents=True, exist_ok=False)
                    shutil.copyfile(frozen, folder / "skill.json")
                    environment.reset(pose)
                    plan = robot_plan(skill, CONFIG, pose)
                    write(folder / "robot-plan.json", plan)
                    result = execute(
                        environment, plan, folder, {**CONFIG, **overrides}, lambda *_: None
                    )
                    write(folder / "simulation-result.json", result)
                    checks = verify_artifacts(folder, skill, result)
                    if digest(frozen) != prepared["skill_sha256"][sample["id"]]:
                        raise ValueError("Execution changed the prepared skill.")
                    report["cases"].append(
                        {
                            "sample": sample["id"],
                            "method": method,
                            "pose": pose_name,
                            "result": result,
                            "checks": checks,
                            "artifact_sha256": {
                                p.name: digest(p) for p in sorted(folder.iterdir()) if p.is_file()
                            },
                        }
                    )
                    write(output / "results.json", report)
                    print(
                        f"{sample['id']} {pose_name} {method}: success={result['success']} mean={result['mean_path_error_m']} shape={result['max_shape_error_m']}",
                        flush=True,
                    )
        dataset(source)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["complete"] = True
        write(output / "results.json", report)
    finally:
        environment.close()
    if any(not c["result"]["success"] for c in report["cases"] if c["method"] == "compensated"):
        raise SystemExit("Compensated execution failed acceptance; inspect the retained results.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "run"))
    parser.add_argument("--source", type=Path, default=Path("/evidence"))
    parser.add_argument("--output", type=Path, default=Path("/evaluation"))
    args = parser.parse_args()
    {"prepare": prepare, "run": evaluate}[args.stage](args.source, args.output)


if __name__ == "__main__":
    main()
