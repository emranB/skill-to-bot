# Purpose: Follow continuous drawing targets under Panda physics and evaluate measured pen-tip ink.
import json
import math
import time

import imageio.v2 as imageio
import numpy as np
from robosuite.utils.transform_utils import mat2quat, quat2axisangle

from src.skill_to_robot.skill_to_robot import eef_target


def path_distance(points, path):
    """Maximum point-to-polyline distance, bounded in memory and independent of timing lag."""
    points, path = np.asarray(points), np.asarray(path)
    if len(points) == 0 or len(path) < 2:
        raise ValueError("A completed stroke needs at least two measured ink positions.")
    start, delta = path[:-1], np.diff(path, axis=0)
    lengths = np.maximum(np.sum(delta * delta, axis=1), 1e-20)
    maximum = 0.0
    for offset in range(0, len(points), 64):
        relative = points[offset : offset + 64, None, :] - start
        fraction = np.clip(np.sum(relative * delta, axis=2) / lengths, 0, 1)
        distance = np.linalg.norm(relative - fraction[:, :, None] * delta, axis=2)
        maximum = max(maximum, float(distance.min(axis=1).max()))
    return maximum


def execute(environment, plan: dict, directory, config: dict, progress) -> dict:
    env = environment.env
    started = time.monotonic()
    initial_time = float(env.sim.data.time)
    control_interval = int(env.control_timestep / env.model_timestep) * env.model_timestep
    if control_interval <= 0:
        raise ValueError("Control frequency exceeds the MuJoCo integration rate.")
    next_render = 1 / config["video_fps"]
    orientation = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]])
    rotation_action = quat2axisangle(mat2quat(orientation))
    deadline = time.monotonic() + config["execution_timeout"]
    trace, steps, completed = [], 0, 0
    errors, coverage, outside = [], [], 0
    frames, shape_errors = [], []
    correction = np.zeros(3)
    previous_target = None
    failure = None
    visibility = None
    writer = imageio.get_writer(
        str(directory / "simulation.mp4"),
        fps=config["video_fps"],
        codec="libx264",
        macro_block_size=16,
        ffmpeg_params=["-threads", "1", "-movflags", "+faststart"],
    )

    def record_frame(elapsed):
        writer.append_data(environment.render())
        frames.append({"t": elapsed, "sample_count": len(trace), "ink_count": len(environment.ink)})

    record_frame(0)

    def step(target, phase, stroke, pressure=None, style=None):
        nonlocal steps, outside, next_render, previous_target
        if time.monotonic() > deadline:
            raise TimeoutError("Drawing execution exceeded its deadline.")
        command = np.asarray(target).copy()
        if phase == "draw":
            lead = (
                np.zeros(3)
                if previous_target is None
                else (command - previous_target)
                * config["tracking_lead_seconds"]
                / control_interval
            )
            lead[2] = 0
            command += correction + np.clip(
                lead, -config["tracking_max_offset"], config["tracking_max_offset"]
            )
        previous_target = np.asarray(target).copy()
        position = eef_target(command, orientation, plan["tool_offset"])
        env.step(np.r_[position, rotation_action, 1])
        steps += 1
        elapsed = float(env.sim.data.time) - initial_time
        actual = environment.tip_position()
        if (
            not np.isfinite(actual).all()
            or not math.isfinite(elapsed)
            or (trace and elapsed <= trace[-1]["t"])
        ):
            raise ValueError("Simulation pen state or clock became invalid.")
        local = environment.local_position(actual)
        if phase == "draw":
            correction[:2] = np.clip(
                correction[:2]
                + (np.asarray(target)[:2] - actual[:2])
                * config["tracking_integral_gain"]
                * control_interval,
                -config["tracking_max_offset"],
                config["tracking_max_offset"],
            )
        physical, near = environment.contact(local)
        inside = (
            abs(local[0]) <= config["paper_width"] / 2
            and abs(local[1]) <= config["paper_height"] / 2
        )
        ink = environment.deposit(stroke, local, pressure, phase, style)
        if ink is not None:
            ink["t"] = elapsed
        desired_local = environment.local_position(target)
        error = float(np.linalg.norm(actual - target))
        sample = {
            "t": elapsed,
            "phase": phase,
            "stroke": stroke,
            "desired_local": desired_local.tolist(),
            "actual_local": local.tolist(),
            "actual_world": actual.tolist(),
            "contact": bool(near),
            "physical_contact": bool(physical),
            "inside_paper": bool(inside),
            "pressure": pressure,
            "effective_pressure": config["default_pressure"] if pressure is None else pressure,
            "ink_radius": ink["radius"] if ink else None,
            "error_m": error,
        }
        trace.append(sample)
        if phase == "draw":
            errors.append(error)
            coverage.append(near and inside)
            outside += int(not inside)
        if elapsed >= next_render:
            record_frame(elapsed)
            next_render += 1 / config["video_fps"]
        return error

    def reach(target, phase, stroke):
        start = environment.tip_position()
        target = np.asarray(target)
        count = max(
            1,
            math.ceil(np.linalg.norm(target - start) / control_interval / config["travel_speed"]),
        )
        for i in range(1, count + 1):
            step(start + (target - start) * i / count, phase, stroke)
        for _ in range(int(config["phase_timeout"] / control_interval)):
            if step(target, phase, stroke) <= config["approach_tolerance"]:
                return
        raise ValueError(
            f"Robot could not reach drawing {phase}: tip error {np.linalg.norm(environment.tip_position() - target) * 1000:.1f} mm."
        )

    try:
        for phase in plan["phases"]:
            kind, stroke = phase["phase"], phase["stroke"]
            progress(kind, stroke)
            if kind != "draw":
                reach(phase["target"], kind, stroke)
                continue
            points = phase["points"]
            correction[:] = 0
            previous_target = np.asarray(points[0]["tip"])
            distance = sum(
                np.linalg.norm(np.asarray(b["tip"]) - a["tip"]) for a, b in zip(points, points[1:])
            )
            duration = points[-1]["t"] - points[0]["t"]
            scale = distance / config["drawing_speed"] / max(duration, 1e-9)
            for a, b in zip(points, points[1:]):
                start, end = np.asarray(a["tip"]), np.asarray(b["tip"])
                length = np.linalg.norm(end - start)
                count = max(
                    1,
                    math.ceil(length / config["max_cartesian_step"]),
                    math.ceil(length / control_interval / config["drawing_speed"]),
                    math.ceil((b["t"] - a["t"]) * scale / control_interval),
                )
                for index in range(1, count + 1):
                    fraction = index / count
                    pressure = (
                        None
                        if a["pressure"] is None
                        else a["pressure"] + fraction * (b["pressure"] - a["pressure"])
                    )
                    target = start + fraction * (end - start)
                    step(target, kind, stroke, pressure, phase)
                    # Pause path advancement when the physical tip falls behind a fine curve.
                    for _ in range(int(config["phase_timeout"] / control_interval)):
                        if (
                            np.linalg.norm(environment.tip_position()[:2] - target[:2])
                            <= config["tracking_tolerance"]
                        ):
                            break
                        step(target, kind, stroke, pressure, phase)
                    else:
                        raise ValueError("Pen could not converge to the drawing path.")
            for _ in range(int(config["phase_timeout"] / control_interval)):
                if (
                    step(
                        np.asarray(points[-1]["tip"]),
                        kind,
                        stroke,
                        points[-1]["pressure"],
                        phase,
                    )
                    <= config["approach_tolerance"]
                ):
                    break
            else:
                raise ValueError("Robot did not finish the drawing stroke.")
            completed += 1
            actual = [p["local"][:2] for p in environment.ink if p["stroke"] == stroke]
            desired = [p["local"][:2] for p in points]
            shape_errors.append(max(path_distance(actual, desired), path_distance(desired, actual)))
        progress("park", stroke)
        reach(plan["park_tip"], "park", stroke)
        visibility = environment.visibility()
        if (
            visibility["paper_fraction"] < config["min_visible_paper"]
            or not visibility["ink_pixels"]
        ):
            raise ValueError("Simulator camera cannot clearly see the completed paper and ink.")
        imageio.imwrite(directory / "simulator-final.png", environment.render())
        for _ in range(config["video_fps"]):
            record_frame(float(env.sim.data.time) - initial_time)
    except Exception as error:
        failure = str(error) or type(error).__name__
    finally:
        try:
            writer.close()
        except Exception as error:
            failure = failure or f"Video encoding failed: {str(error) or type(error).__name__}."
        (directory / "trace.json").write_text(
            json.dumps(
                {
                    "frame": "paper_local",
                    "units": "meters",
                    "samples": trace,
                    "ink": environment.ink,
                    "video": {
                        "renderer": "MuJoCo",
                        "ink_renderer": "measured_ink_geometry",
                        "camera": "agentview",
                        "camera_position": config["camera_position"],
                        "camera_target": config["camera_target"],
                        "camera_fov": config["camera_fov"],
                        "fps": config["video_fps"],
                        "frames": frames,
                    },
                    "stroke_shape_error_m": shape_errors,
                },
                indent=2,
            )
        )
    mean = float(np.mean(errors)) if errors else None
    percentile = float(np.percentile(errors, 95)) if errors else None
    maximum = max(errors) if errors else None
    contact_coverage = sum(coverage) / len(coverage) if coverage else 0
    strokes = len(plan["phases"]) // 4
    success = bool(
        not failure
        and completed == strokes
        and mean is not None
        and mean <= config["drawing_tolerance"]
        and maximum <= config["max_path_error"]
        and contact_coverage >= config["min_contact_coverage"]
        and outside == 0
        and len(shape_errors) == strokes
        and max(shape_errors) <= config["shape_tolerance"]
    )
    if not success and not failure:
        failure = "Drawing did not meet tracking, shape, contact coverage or paper-bound criteria."
    return {
        "success": success,
        "error": failure,
        "mean_path_error_m": mean,
        "p95_path_error_m": percentile,
        "max_path_error_m": maximum,
        "max_shape_error_m": max(shape_errors) if shape_errors else None,
        "contact_coverage": contact_coverage,
        "physical_contact_coverage": sum(
            s["physical_contact"] for s in trace if s["phase"] == "draw"
        )
        / len(errors)
        if errors
        else 0,
        "out_of_paper_samples": outside,
        "strokes_completed": completed,
        "stroke_count": strokes,
        "ink_points": len(environment.ink),
        "execution_duration_s": float(env.sim.data.time) - initial_time,
        "wall_duration_s": time.monotonic() - started,
        "steps": steps,
        "video": "simulation.mp4",
        "visibility": visibility,
    }
