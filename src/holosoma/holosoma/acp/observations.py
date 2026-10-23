"""Measured actor observations and explicitly privileged reference streams."""
from __future__ import annotations

import torch

from holosoma.acp.models import contact_schedule
from holosoma.managers.observation.terms.wbt import base_ang_vel, base_lin_vel, projected_gravity


def command(env):
    return env.command_manager.get_state("motion_command")


def yaw(quaternion):
    x, y, z, w = quaternion.unbind(-1)
    return torch.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))


def rotate_yaw(points, angle):
    while angle.ndim < points.ndim - 1:
        angle = angle.unsqueeze(-1)
    x, y, z = points.unbind(-1)
    return torch.stack((angle.cos()*x-angle.sin()*y, angle.sin()*x+angle.cos()*y, z), -1)


def to_local(env, points):
    root = env.simulator.robot_root_states
    return rotate_yaw(points-root[:, None, :3], -yaw(root[:, 3:7]))


def proprio(env):
    actions = env.action_manager.action
    return torch.cat((base_ang_vel(env), projected_gravity(env),
                      env.simulator.dof_pos-env.default_dof_pos, env.simulator.dof_vel, actions), -1)


def terrain(env, rows=17, columns=11):
    root = env.simulator.robot_root_states
    x = torch.linspace(-(rows-1)*0.05, (rows-1)*0.05, rows, device=env.device)
    y = torch.linspace(-(columns-1)*0.05, (columns-1)*0.05, columns, device=env.device)
    xx, yy = torch.meshgrid(x, y, indexing="ij")
    local = torch.stack((xx.flatten(), yy.flatten(), torch.zeros_like(xx.flatten())), -1)
    local = local[None].expand(env.num_envs, -1, -1)
    world = rotate_yaw(local, yaw(root[:, 3:7]))+root[:, None, :3]
    state = env.terrain_manager.get_state("locomotion_terrain")
    query = getattr(state, "query_terrain_heights", None)
    if not callable(query):
        raise RuntimeError("ACP requires actual initialized terrain height queries")
    heights = query(world[..., :2].reshape(-1, 2)).reshape(env.num_envs, -1)
    valid = torch.isfinite(heights)
    if not valid.any(-1).all():
        raise RuntimeError("ACP height scan has no observed terrain")
    return torch.cat((local[..., :2], torch.where(valid, heights-root[:, 2:3], 0)[..., None]), -1), valid


def goal(env):
    cmd = command(env)
    steps = (cmd.time_steps + cmd.acp_goal_lookahead).minimum(cmd.motion.motion_end_idx[cmd.motion_ids]-1)
    target = cmd.motion.body_pos_w[steps, 0]+cmd._reference_env_origins
    target_quat = cmd.motion.body_quat_w[steps, 0]
    root = env.simulator.robot_root_states
    delta = rotate_yaw(target-root[:, :3], -yaw(root[:, 3:7]))[:, :2]
    delta = delta / delta.norm(dim=-1, keepdim=True).clamp_min(0.3)
    heading = yaw(target_quat)-yaw(root[:, 3:7])
    return torch.cat((delta, torch.atan2(heading.sin(), heading.cos())[:, None]), -1)


def contact_targets(env):
    cache = env._holosoma_step_cache
    if "acp_command" not in cache:
        cmd = command(env)
        idx = cmd.time_steps
        target = to_local(env, cmd.acp_target_w[idx]+cmd._reference_env_origins[:, None])
        occupancy = cmd.acp_target_occupancy[idx]
        inside = (target[..., 0].abs() <= 0.8) & (target[..., 1].abs() <= 0.5)
        reference = target * (occupancy & inside)[..., None]
        stage = env.acp_settings["stage"]
        predicted = torch.zeros_like(reference)
        if stage > 1 and env.acp_planner is not None:
            scan, valid = terrain(env)
            history = history_observation(env)
            with torch.no_grad():
                predicted = env.acp_planner(history, goal(env), scan, valid)["positions"]
            probability = contact_schedule(env.acp_iteration, env.acp_settings["input_start"],
                                            env.acp_settings["anneal_steps"])
            if env.is_evaluating:
                probability = 1.0
            use_planner = torch.rand(env.num_envs, 1, 1, device=env.device) < probability
            selected = torch.where(use_planner, predicted, reference)
        else:
            selected = reference
        cache["acp_command"] = (selected, predicted, reference)
    return cache["acp_command"][0].flatten(1)


def history_observation(env):
    """One history update per actual observation; no planner-driven extra samples."""
    return env.acp_history.flatten(1)


def actor_contacts(env):
    contacts = contact_targets(env).reshape(env.num_envs, 9, 3)
    if env.acp_settings.get("observation_noise", False) and not env.is_evaluating:
        valid = contacts.abs().sum(-1) > 0
        contacts = contacts + (2*torch.rand_like(contacts)-1)*0.1*valid[..., None]
    return contacts.flatten(1)


def tracker_scan(env):
    scan = terrain(env, 9, 7)[0][..., 2]
    if env.acp_settings.get("observation_noise", False) and not env.is_evaluating:
        scan = scan + (2*torch.rand_like(scan)-1)*0.1
    return scan


def critic_reference(env):
    cmd = command(env)
    from holosoma.acp.labels import BODY_NAMES
    ids = [env.simulator.body_names.index(name) for name in BODY_NAMES]
    return torch.cat((cmd.motion.body_lin_vel_w[cmd.time_steps, 0],
                      cmd.motion.body_ang_vel_w[cmd.time_steps, 0], cmd.joint_pos, cmd.joint_vel,
                      cmd.acp_reference_active[cmd.time_steps].float(),
                      to_local(env, cmd.motion.body_pos_w[cmd.time_steps][:, ids]
                               +cmd._reference_env_origins[:, None]).flatten(1)), -1)


def critic_observation(env):
    return torch.cat((proprio(env), base_lin_vel(env), terrain(env)[0][..., 2], goal(env),
                      contact_targets(env), critic_reference(env)), -1)
