# Purpose: Generate deterministic writing and fine-curve demonstrations.
import json
import math
from pathlib import Path


def curve(control, samples=30):
    points = []
    for i in range(samples + 1):
        t = i / samples
        points.append(
            tuple(
                (1 - t) ** 3 * control[0][axis]
                + 3 * (1 - t) ** 2 * t * control[1][axis]
                + 3 * (1 - t) * t * t * control[2][axis]
                + t**3 * control[3][axis]
                for axis in (0, 1)
            )
        )
    return points


def fixtures():
    block = [
        [(0.12, 0.75), (0.12, 0.25)],
        [
            (0.12, 0.25),
            *curve([(0.12, 0.25), (0.38, 0.23), (0.38, 0.5), (0.12, 0.5)])[1:],
            *curve([(0.12, 0.5), (0.4, 0.48), (0.4, 0.78), (0.12, 0.75)])[1:],
        ],
        [
            (
                0.49 + 0.11 * math.cos(i * 2 * math.pi / 80),
                0.5 + 0.25 * math.sin(i * 2 * math.pi / 80),
            )
            for i in range(81)
        ],
        [(0.67, 0.25), (0.9, 0.25)],
        [(0.785, 0.25), (0.785, 0.75)],
    ]
    controls = [
        [(0.08, 0.7), (0.24, 0.05), (0.04, 0.05), (0.13, 0.7)],
        [(0.13, 0.7), (0.19, 0.32), (0.26, 0.48), (0.23, 0.68)],
        [(0.23, 0.68), (0.3, 0.68), (0.37, 0.48), (0.3, 0.5)],
        [(0.3, 0.5), (0.24, 0.5), (0.27, 0.79), (0.4, 0.64)],
        [(0.4, 0.64), (0.6, 0.03), (0.33, 0.04), (0.44, 0.68)],
        [(0.44, 0.68), (0.65, 0.05), (0.47, 0.05), (0.57, 0.68)],
        [(0.57, 0.68), (0.63, 0.47), (0.78, 0.4), (0.77, 0.61)],
        [(0.77, 0.61), (0.77, 0.83), (0.61, 0.82), (0.64, 0.6)],
        [(0.64, 0.6), (0.7, 0.5), (0.8, 0.68), (0.9, 0.61)],
    ]
    cursive = [[]]
    for control in controls:
        cursive[0].extend(curve(control)[1:] if cursive[0] else curve(control))
    vertices = [
        (0.5 + 0.38 * math.sin(i * 2 * math.pi / 5), 0.5 - 0.4 * math.cos(i * 2 * math.pi / 5))
        for i in range(5)
    ]
    star = [[vertices[i] for i in (0, 2, 4, 1, 3, 0)]]
    house = [
        [(0.15, 0.45), (0.5, 0.15), (0.85, 0.45)],
        [(0.22, 0.45), (0.22, 0.85), (0.78, 0.85), (0.78, 0.45)],
        [(0.44, 0.85), (0.44, 0.61), (0.57, 0.61), (0.57, 0.85)],
        [(0.29, 0.52), (0.38, 0.52), (0.38, 0.63), (0.29, 0.63), (0.29, 0.52)],
    ]
    double_hello = [
        [(x * 0.45 + shift, y * 0.65 + 0.18) for x, y in cursive[0]] for shift in (0.02, 0.5)
    ]
    loops = [
        [
            (
                0.08 + 0.84 * i / 720 + 0.025 * math.sin(i * math.pi / 30),
                0.5 + 0.23 * math.sin(i * math.pi / 30),
            )
            for i in range(721)
        ]
    ]

    return {
        "block-bot": block,
        "cursive-hello": cursive,
        "star": star,
        "house": house,
        "cursive-double-hello": double_hello,
        "fine-loops": loops,
    }


def demonstration(paths):
    clock, sample = 0.0, 0
    strokes = []
    for path in paths:
        points = []
        for first, last in zip(path, path[1:]):
            count = max(1, math.ceil(math.dist(first, last) / 0.005))
            for index in range(count):
                f = index / count
                points.append(
                    {
                        "x": first[0] + f * (last[0] - first[0]),
                        "y": first[1] + f * (last[1] - first[1]),
                        "t_ms": round(clock, 3),
                        "pressure": round(0.5 + 0.25 * math.sin(sample * 0.07), 5),
                        "pointer_type": "pen",
                        "tilt_x": 0,
                        "tilt_y": 0,
                        "twist": 0,
                    }
                )
                clock += 12
                sample += 1
        points.append({**points[-1], "x": path[-1][0], "y": path[-1][1], "t_ms": round(clock, 3)})
        clock += 200
        strokes.append({"points": points})
    return {
        "version": "1.0",
        "type": "drawing",
        "coordinate_space": "normalized_screen",
        "canvas": {"aspect_ratio": 1.5},
        "device": {
            "pointer_type": "pen",
            "pressure_observed": True,
        },
        "source": {"type": "synthetic_fixture"},
        "strokes": strokes,
    }


if __name__ == "__main__":
    output = Path(__file__).parent / "drawings"
    output.mkdir(parents=True, exist_ok=True)
    for name, paths in fixtures().items():
        (output / (name + ".json")).write_text(
            json.dumps(demonstration(paths), separators=(",", ":")) + "\n"
        )
