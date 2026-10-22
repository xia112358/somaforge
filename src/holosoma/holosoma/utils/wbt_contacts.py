"""Passive measured WBT contacts from the currently running Newton solve.

Reference commands never participate in activation, allocation or face selection.
Per-constraint forces are decoded by MJWarp; body net forces are not a substitute.
"""
from __future__ import annotations

import numpy as np
import torch

from holosoma.utils.wbt_experiment import PARTS


class MeasuredContacts:
    def __init__(self, env):
        from isaaclab_newton.physics.newton_manager import NewtonManager
        from somaforge_core.native_model_binding import inspect_model, native_binding

        self.env, self.manager = env, NewtonManager
        self.model, self.solver = NewtonManager.get_model(), NewtonManager._solver
        self.binding = native_binding(self.model, inspect_model(self.model))
        from somaforge_core.native_surface_index import NativeSurfaceIndex
        self.face_indexes = {int(shape): NativeSurfaceIndex(faces)
            for shape, faces in self.binding["shape_surface"].items()}

    def read(self):
        import warp as wp
        import mujoco_warp as mjw
        from somaforge_core.newton_contacts import snapshot_solver_contacts
        from somaforge_core.newton_support import select_support_contacts

        cache = self.env._holosoma_step_cache
        key = ("wbt_measured_contacts", id(self.model))
        if key not in cache:
            snapshot = snapshot_solver_contacts(self.solver, self.model)
            selected = select_support_contacts(snapshot, self.binding, self.model.body_label,
                face_indexes=self.face_indexes)
            count = int(snapshot["count"])
            active = np.zeros(self.env.num_envs * len(PARTS), dtype=bool)
            force = np.zeros((len(active), 3), dtype=np.float32)
            if count:
                # contact_force decodes the native friction cone/efc rows and
                # returns the world-space force ON body1 when world=True.
                ids = wp.array(np.arange(count, dtype=np.int32), dtype=wp.int32, device=self.model.device)
                wrench = wp.zeros(count, dtype=wp.spatial_vector, device=self.model.device)
                mjw.contact_force(self.solver.mjw_model, self.solver.mjw_data, ids, True, wrench)
                values = wrench.numpy()[:, :3]
                snapshot["force_on_body1_w"] = values.copy()
                if not np.isfinite(values).all():
                    raise ValueError("Nonfinite native per-contact force")
                eligible = selected["eligible"]
                groups = selected["groups"][eligible]
                if ((groups < 0) | (groups >= len(active))).any():
                    raise ValueError("Native contact body/world mapping disagrees with the WBT environment")
                active[groups] = True
                sign = np.where(selected["robot_side"][eligible] == 1, 1., -1.)
                np.add.at(force, groups, values[eligible] * sign[:, None])
            else:
                snapshot["force_on_body1_w"] = np.zeros((0, 3), dtype=np.float32)
            cache[key] = {
                "active": torch.as_tensor(active.reshape(self.env.num_envs, len(PARTS)), device=self.env.device),
                "force_w": torch.as_tensor(force.reshape(self.env.num_envs, len(PARTS), 3), device=self.env.device),
                "snapshot": snapshot,
                "excluded_rows": selected["excluded_rows"],
                "solved_root_state": self.env.simulator.robot_root_states[:].clone(),
                "solved_dof_pos": self.env.simulator.dof_pos.clone(),
            }
        data = cache[key]
        # Command window transitions can teleport without resetting the episode
        # counter. Require the exact post-solve articulation state as well.
        # This freshness check never defines or changes contact activation.
        unchanged = (self.env.simulator.robot_root_states[:] == data["solved_root_state"]).all(dim=-1)
        unchanged &= (self.env.simulator.dof_pos == data["solved_dof_pos"]).all(dim=-1)
        known = ((self.env.episode_length_buf > 0) & unchanged)[:, None].expand(-1, len(PARTS))
        return {**data, "known": known,
            "active": data["active"] & known,
            "force_w": data["force_w"] * known[..., None]}


def measured_contacts(env):
    reader = getattr(env, "_wbt_measured_contact_reader", None)
    if reader is None:
        if not hasattr(env, "_holosoma_step_cache"):
            env._holosoma_step_cache = {}
        reader = env._wbt_measured_contact_reader = MeasuredContacts(env)
    return reader.read()
