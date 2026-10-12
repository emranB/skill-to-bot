# Purpose: Execute robot targets through local physics and measure actual manipulation outcome.
import time

import imageio.v2 as imageio
import numpy as np
from robosuite.utils.control_utils import orientation_error
from src.skill_to_robot.skill_to_robot import robot_targets


def execute(environment, skill: dict, video_path, config: dict, progress) -> dict:
    env = environment.env
    initial = environment.object_position().copy()
    targets = robot_targets(skill, initial, config)
    goal = initial + np.array(skill["goal"]) - np.array(skill["start"])
    lifted = False
    grasped = False
    steps = 0
    transport = []
    deadline = time.monotonic() + config["execution_timeout"]
    robot = env.robots[0]
    reference_orientation = env.sim.data.site_xmat[robot.eef_site_id].reshape(3, 3).copy()
    writer = imageio.get_writer(
        str(video_path), fps=config["video_fps"], codec="libx264", macro_block_size=16
    )
    try:
        for phase in targets:
            progress(phase["phase"])
            reached = False
            for index in range(config["max_phase_steps"]):
                if time.monotonic() > deadline:
                    raise TimeoutError("Robot execution exceeded its deadline.")
                robot = env.robots[0]
                position = env.sim.data.site_xpos[robot.eef_site_id]
                orientation = env.sim.data.site_xmat[robot.eef_site_id].reshape(3, 3)
                delta = np.clip((phase["target"] - position) * config["controller_gain"], -1, 1)
                rotation = np.clip(orientation_error(reference_orientation, orientation) * 2, -1, 1)
                action = np.r_[delta, rotation, phase["gripper"]]
                env.step(action)
                steps += 1
                if steps % config["render_every"] == 0:
                    writer.append_data(environment.render())
                object_position = environment.object_position()
                lifted = lifted or object_position[2] - initial[2] > config["min_lift"]
                grasped = grasped or env._check_grasp(
                    robot.gripper, env.objects_dict["alphabet_soup_1"].contact_geoms
                )
                error = float(np.linalg.norm(phase["target"] - position))
                if error < config["target_tolerance"] and index >= config["hold_steps"]:
                    reached = True
                    break
            if not reached:
                raise ValueError(
                    f"Robot could not reach the {phase['phase']} target: error={error:.4f} m, target={phase['target'].tolist()}, actual={position.tolist()}."
                )
            if phase["phase"] == "lift" and not lifted:
                raise ValueError("The robot did not lift the object under physics.")
            if phase["phase"] == "transport":
                actual = environment.object_position().copy()
                expected = phase["target"] - [0, 0, config["grasp_z_offset"] + 0.003]
                path_error = float(np.linalg.norm(actual - expected))
                transport.append(
                    {"target": expected.tolist(), "actual": actual.tolist(), "error_m": path_error}
                )
                if path_error > config["placement_tolerance"]:
                    raise ValueError("The grasped object did not follow a transport waypoint.")
        final = environment.object_position().copy()
        position_error = float(np.linalg.norm(final - goal))
        gripper_contact = bool(
            env._check_grasp(
                env.robots[0].gripper, env.objects_dict["alphabet_soup_1"].contact_geoms
            )
        )
        velocity = float(np.linalg.norm(env.sim.data.get_body_xvelp("alphabet_soup_1_main")))
        success = bool(
            lifted
            and grasped
            and not gripper_contact
            and position_error <= config["placement_tolerance"]
            and velocity <= config["velocity_tolerance"]
        )
        return {
            "success": success,
            "lifted": bool(lifted),
            "grasped": bool(grasped),
            "released": not gripper_contact,
            "position_error_m": position_error,
            "object_speed_m_s": velocity,
            "initial": initial.tolist(),
            "goal": goal.tolist(),
            "final": final.tolist(),
            "steps": steps,
            "transport": transport,
            "video": "simulation.mp4",
        }
    finally:
        writer.close()
