# Purpose: Validate raw strokes and extract compact robot-independent drawing geometry.
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator


def pressure_types(points, tolerance):
    observed = set()
    for kind in ("pen", "touch"):
        values = [
            p["pressure"] for p in points if p["pointer_type"] == kind and p.get("pressure", 0) > 0
        ]
        if values and max(values) - min(values) > tolerance:
            observed.add(kind)
    return observed


def validate_demonstration(raw: dict, contracts: Path, config: dict) -> None:
    json.dumps(raw, allow_nan=False)
    Draft202012Validator(
        json.loads((contracts / "demonstration.schema.json").read_text())
    ).validate(raw)
    points = [point for stroke in raw["strokes"] for point in stroke["points"]]
    if len(points) > config["max_raw_points"]:
        raise ValueError("Drawing has too many samples.")
    if any(a["t_ms"] > b["t_ms"] for a, b in zip(points, points[1:])):
        raise ValueError("Drawing timestamps must be monotonic across the session.")
    types = {point["pointer_type"] for point in points}
    reported = next(iter(types)) if len(types) == 1 else "mixed"
    if reported != raw["device"]["pointer_type"]:
        raise ValueError("Pointer metadata does not match the samples.")
    observed = bool(pressure_types(points, config["pressure_tolerance"]))
    if raw["device"]["pressure_observed"] != observed:
        raise ValueError("Pressure metadata must reflect observed non-mouse variation.")
    for stroke in raw["strokes"]:
        path = stroke["points"]
        if len({p["pointer_type"] for p in path}) != 1:
            raise ValueError("A stroke must come from one pointer type.")
        distance = sum(math.hypot(b["x"] - a["x"], b["y"] - a["y"]) for a, b in zip(path, path[1:]))
        if distance <= config["duplicate_tolerance"] or path[-1]["t_ms"] <= path[0]["t_ms"]:
            raise ValueError("Each stroke needs movement and increasing time.")


def _simplify(points: list[dict], config: dict, pressure: bool) -> list[dict]:
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        if last - first < 2:
            continue
        a, b = points[first], points[last]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        length = dx * dx + dy * dy
        worst, middle = 1.0, None
        for index in range(first + 1, last):
            p = points[index]
            fraction = (
                max(0, min(1, ((p["x"] - a["x"]) * dx + (p["y"] - a["y"]) * dy) / length))
                if length
                else 0
            )
            geometric = math.hypot(p["x"] - a["x"] - fraction * dx, p["y"] - a["y"] - fraction * dy)
            score = geometric / config["simplification_tolerance"]
            # Timing and pressure extrema survive even on geometrically straight strokes.
            time_fraction = (
                (p["t_ms"] - a["t_ms"]) / (b["t_ms"] - a["t_ms"])
                if b["t_ms"] > a["t_ms"]
                else fraction
            )
            score = max(
                score,
                abs(time_fraction - fraction)
                * math.sqrt(length)
                / config["simplification_tolerance"],
            )
            if pressure:
                expected = a["pressure"] + fraction * (b["pressure"] - a["pressure"])
                score = max(score, abs(p["pressure"] - expected) / config["pressure_tolerance"])
            if score > worst:
                worst, middle = score, index
        if middle is not None:
            keep.add(middle)
            pending.extend([(first, middle), (middle, last)])
    return [points[index] for index in sorted(keep)]


def extract_skill(raw: dict, demonstration_id: str, contracts: Path, config: dict) -> dict:
    validate_demonstration(raw, contracts, config)
    strokes, count = [], 0
    for stroke in raw["strokes"]:
        pressure = stroke["points"][0]["pointer_type"] != "mouse" and any(
            p.get("pressure", 0) > 0 for p in stroke["points"]
        )
        path = [dict(p) for p in stroke["points"]]
        # Release events report zero pressure; they end a stroke rather than erase its tip.
        if pressure:
            previous = next((p["pressure"] for p in path if p.get("pressure", 0) > 0), 0.5)
            for p in path:
                if p.get("pressure", 0) > 0:
                    previous = p["pressure"]
                p["pressure"] = previous
        clean = [path[0]]
        for p in path[1:-1]:
            if math.hypot(p["x"] - clean[-1]["x"], p["y"] - clean[-1]["y"]) > config[
                "duplicate_tolerance"
            ] or (
                pressure
                and abs(p["pressure"] - clean[-1]["pressure"]) > config["pressure_tolerance"]
            ):
                clean.append(p)
        clean.append(path[-1])
        simplified = _simplify(clean, config, pressure)
        output = []
        for a, b in zip(simplified, simplified[1:]):
            steps = max(
                1, math.ceil(math.hypot(b["x"] - a["x"], b["y"] - a["y"]) / config["max_point_gap"])
            )
            for index in range(steps):
                fraction = index / steps
                point = {
                    "x": a["x"] + fraction * (b["x"] - a["x"]),
                    "y": 1 - a["y"] - fraction * (b["y"] - a["y"]),
                    "t": (a["t_ms"] + fraction * (b["t_ms"] - a["t_ms"])) / 1000,
                }
                if pressure:
                    point["pressure"] = a["pressure"] + fraction * (b["pressure"] - a["pressure"])
                output.append(point)
                count += 1
                if count > config["max_skill_points"]:
                    raise ValueError("Processed drawing exceeds the point limit.")
        last = simplified[-1]
        output.append(
            {
                "x": last["x"],
                "y": 1 - last["y"],
                "t": last["t_ms"] / 1000,
                **({"pressure": last["pressure"]} if pressure else {}),
            }
        )
        count += 1
        if count > config["max_skill_points"]:
            raise ValueError("Processed drawing exceeds the point limit.")
        strokes.append(
            {"points": output, **{k: stroke[k] for k in ("color", "brush_size") if k in stroke}}
        )
    skill = {
        "version": "2.0",
        "primitive": "draw",
        "frame": "paper_normalized",
        "aspect_ratio": raw["canvas"]["aspect_ratio"],
        "source": {
            "demonstration_id": demonstration_id,
            "type": raw["source"]["type"],
            **raw["device"],
        },
        "strokes": strokes,
    }
    Draft202012Validator(json.loads((contracts / "skill.schema.json").read_text())).validate(skill)
    return skill
