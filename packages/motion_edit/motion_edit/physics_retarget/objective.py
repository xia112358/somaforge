from __future__ import annotations

import numpy as np

from .force_response import force_directions
from .schema import ForceGuidedRetargetConfig, PhysicsRollout


def evaluate_rollout_objective(
    *,
    target_force_w: np.ndarray,
    target_mask: np.ndarray,
    target_joint_pos: np.ndarray | None,
    rollout: PhysicsRollout,
    config: ForceGuidedRetargetConfig,
) -> tuple[float, dict[str, float]]:
    target_force = np.asarray(target_force_w, dtype=np.float64)
    target_contact = np.asarray(target_mask, dtype=bool)
    rollout.validate(expected_frames=target_force.shape[0], expected_parts=target_force.shape[1])
    actual_force = np.asarray(rollout.force_w, dtype=np.float64)
    actual_mask = np.asarray(rollout.mask, dtype=bool)
    if target_contact.shape != target_force.shape[:2]:
        raise ValueError(f"target_mask must be {target_force.shape[:2]}, got {target_contact.shape}")
    normals = force_directions(target_force, target_contact)

    active = target_contact
    target_normal = np.sum(target_force * normals, axis=2)
    actual_normal = np.sum(actual_force * normals, axis=2)
    target_tangent = target_force - target_normal[..., None] * normals
    actual_tangent = actual_force - actual_normal[..., None] * normals
    force_scale = max(float(np.sqrt(np.mean(np.square(target_normal[active])))) if np.any(active) else 0.0, config.force_epsilon_n)

    normal_rmse = _masked_rmse(actual_normal - target_normal, active) / force_scale
    tangent_rmse = _masked_rmse(
        np.linalg.norm(actual_tangent - target_tangent, axis=2), active
    ) / force_scale
    unexpected_force = _masked_rmse(np.linalg.norm(actual_force, axis=2), ~active) / force_scale
    mask_error = float(np.mean(actual_mask != target_contact))

    tracking_rmse = 0.0
    if target_joint_pos is not None and rollout.joint_pos is not None:
        target_joint = np.asarray(target_joint_pos, dtype=np.float64)
        actual_joint = np.asarray(rollout.joint_pos, dtype=np.float64)
        if target_joint.shape != actual_joint.shape:
            raise ValueError(f"target/rollout joint_pos mismatch: {target_joint.shape} vs {actual_joint.shape}")
        tracking_rmse = float(np.sqrt(np.mean(np.square(actual_joint - target_joint)))) / 0.1

    metrics = {
        "normal_force_nrmse": normal_rmse,
        "tangential_force_nrmse": tangent_rmse,
        "unexpected_force_nrmse": unexpected_force,
        "contact_state_error": mask_error,
        "joint_tracking_nrmse": tracking_rmse,
        "force_scale_n": force_scale,
    }
    objective = (
        config.force_weight * normal_rmse
        + config.tangential_force_weight * tangent_rmse
        + config.unexpected_contact_weight * unexpected_force
        + config.contact_state_weight * mask_error
        + config.tracking_weight * tracking_rmse
    )
    metrics["objective"] = float(objective)
    return float(objective), metrics


def _masked_rmse(values: np.ndarray, mask: np.ndarray) -> float:
    selected = np.asarray(values, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    if selected.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(selected))))
