# Purpose: Verify strict raw data, deterministic geometry, pressure and timing preservation.
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from src.stroke_processing.stroke_processing import extract_skill, validate_demonstration

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text())
CONTRACTS = (
    Path("/app/contracts") if Path("/app/contracts").exists() else ROOT.parents[1] / "contracts"
)
FIXTURES = (
    Path("/fixtures/drawings")
    if Path("/fixtures/drawings").exists()
    else ROOT.parents[1] / "tests/fixtures/drawings"
)


@pytest.fixture
def raw():
    return json.loads((FIXTURES / "star.json").read_text())


@pytest.mark.parametrize(
    "kind",
    [
        "coordinate",
        "pressure",
        "time",
        "empty",
        "excessive",
        "finite",
        "metadata",
        "extra",
        "flat",
        "color",
        "brush",
    ],
)
def test_invalid_input(raw, kind):
    p = raw["strokes"][0]["points"][1]
    if kind == "coordinate":
        p["x"] = 2
    if kind == "pressure":
        p["pressure"] = -0.1
    if kind == "time":
        p["t_ms"] = -1
    if kind == "empty":
        raw["strokes"] = []
    if kind == "excessive":
        raw["strokes"] *= 20
    if kind == "finite":
        p["x"] = float("nan")
    if kind == "metadata":
        raw["device"]["pressure_observed"] = False
    if kind == "extra":
        raw["robot"] = "Panda"
    if kind == "flat":
        for point in raw["strokes"][0]["points"]:
            point.update(x=0.5, y=0.5)
    if kind == "color":
        raw["strokes"][0]["color"] = "transparent"
    if kind == "brush":
        raw["strokes"][0]["brush_size"] = 1
    with pytest.raises((ValueError, ValidationError)):
        validate_demonstration(raw, CONTRACTS, CONFIG)


@pytest.mark.parametrize("name", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_fixture_geometry_pressure_and_independent_raw(name):
    raw = json.loads((FIXTURES / (name + ".json")).read_text())
    original = copy.deepcopy(raw)
    skill = extract_skill(raw, "a" * 32, CONTRACTS, CONFIG)
    assert raw == original
    assert len(skill["strokes"]) == len(raw["strokes"])
    assert skill["source"]["type"] == "synthetic_fixture"
    for source, output in zip(raw["strokes"], skill["strokes"]):
        for first, last in (
            (source["points"][0], output["points"][0]),
            (source["points"][-1], output["points"][-1]),
        ):
            assert last["x"] == pytest.approx(first["x"])
            assert last["y"] == pytest.approx(1 - first["y"])
            assert last["t"] == pytest.approx(first["t_ms"] / 1000)
            if "pressure" in first:
                assert last["pressure"] == pytest.approx(first["pressure"])
        for key in ("color", "brush_size"):
            assert source.get(key) == output.get(key)
        # Every original curve/corner is within the configured finite-segment tolerance.
        points = output["points"]
        for p in source["points"]:
            best = 2
            for a, b in zip(points, points[1:]):
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                length = dx * dx + dy * dy
                f = (
                    max(0, min(1, ((p["x"] - a["x"]) * dx + (1 - p["y"] - a["y"]) * dy) / length))
                    if length
                    else 0
                )
                best = min(
                    best,
                    ((p["x"] - a["x"] - f * dx) ** 2 + (1 - p["y"] - a["y"] - f * dy) ** 2) ** 0.5,
                )
            assert best <= CONFIG["simplification_tolerance"] + 1e-8


def test_duplicate_removal_and_unavailable_pressure(raw):
    for p in raw["strokes"][0]["points"]:
        p.update(pointer_type="mouse", pressure=0.5)
    raw["device"] = {"pointer_type": "mouse", "pressure_observed": False}
    raw["strokes"][0]["points"].insert(1, copy.deepcopy(raw["strokes"][0]["points"][0]))
    skill = extract_skill(raw, "b" * 32, CONTRACTS, CONFIG)
    assert all("pressure" not in p for s in skill["strokes"] for p in s["points"])
    assert sum(p["t"] == 0 for p in skill["strokes"][0]["points"]) == 1
    with pytest.raises(ValueError, match="point limit"):
        extract_skill(raw, "b" * 32, CONTRACTS, {**CONFIG, "max_skill_points": 2})


def test_linear_pressure_resampling(raw):
    first = {"x": 0.1, "y": 0.3, "t_ms": 0, "pressure": 0.2, "pointer_type": "pen"}
    last = {**first, "x": 0.9, "t_ms": 1000, "pressure": 0.8}
    raw["strokes"] = [{"points": [first, last]}]
    skill = extract_skill(raw, "c" * 32, CONTRACTS, CONFIG)
    for point in skill["strokes"][0]["points"]:
        fraction = (point["x"] - 0.1) / 0.8
        assert point["pressure"] == pytest.approx(0.2 + fraction * 0.6)
        assert point["t"] == pytest.approx(fraction)


def test_mixed_input_does_not_fabricate_mouse_pressure(raw):
    last = raw["strokes"][0]["points"][-1]["t_ms"]
    raw["strokes"].append(
        {
            "points": [
                {"x": 0.2, "y": 0.2, "t_ms": last + 100, "pressure": 0.5, "pointer_type": "mouse"},
                {"x": 0.3, "y": 0.3, "t_ms": last + 200, "pressure": 0.5, "pointer_type": "mouse"},
            ]
        }
    )
    raw["device"]["pointer_type"] = "mixed"
    skill = extract_skill(raw, "d" * 32, CONTRACTS, CONFIG)
    assert all("pressure" in p for p in skill["strokes"][0]["points"])
    assert all("pressure" not in p for p in skill["strokes"][1]["points"])


def test_missing_pressure_and_release_keep_raw_unchanged(raw):
    original = copy.deepcopy(raw)
    raw["strokes"][0]["points"][-1]["pressure"] = 0
    raw["strokes"][0]["color"] = "#dc5278"
    raw["strokes"][0]["brush_size"] = 0.025
    skill = extract_skill(raw, "e" * 32, CONTRACTS, CONFIG)
    assert skill["strokes"][0]["points"][-1]["pressure"] > 0
    assert raw["strokes"][0]["points"][-1]["pressure"] == 0
    for stroke in raw["strokes"]:
        for point in stroke["points"]:
            point.pop("pressure", None)
    raw["device"]["pressure_observed"] = False
    skill = extract_skill(raw, "e" * 32, CONTRACTS, CONFIG)
    assert all("pressure" not in p for s in skill["strokes"] for p in s["points"])
    assert original["device"]["pressure_observed"]
    for stroke in raw["strokes"]:
        for point in stroke["points"]:
            point["pressure"] = 0.8
    skill = extract_skill(raw, "e" * 32, CONTRACTS, CONFIG)
    assert not skill["source"]["pressure_observed"]
    assert all(p["pressure"] == 0.8 for s in skill["strokes"] for p in s["points"])
