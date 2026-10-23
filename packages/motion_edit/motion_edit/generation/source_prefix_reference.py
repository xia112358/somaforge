"""Source-preserving start reference for standard trajectory augmentation.

This changes optimization targets, never solved poses or contact truth. The
same rigid surface map is applied to every source body, preserving the source
stance and its relative motion before a smooth transition to the edited task.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from motion_edit.contact.surface_frame import map_points_between_surface_frames

SCHEMA = "source_prefix_reference_v1"


def load_prefix_configuration(path):
    path = Path(path).expanduser().resolve()
    raw = path.read_bytes()
    config = json.loads(raw)
    # Structural validation before reading any motion or creating outputs.
    end = config.get("transition_end_frame") if isinstance(config, dict) else None
    if type(end) is not int:
        raise ValueError("Source prefix configuration needs transition_end_frame")
    prefix_weights(config, end + 1)
    return config, dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())


def prefix_implementation_fingerprints():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ("source_prefix_reference.py", "rollout_authority.py", "trajectory_problem.py",
                         "trajectory_types.py", "taskspace_kinematics.py", "ik_runtime.py", "torch_newton_ik.py", "torch_newton_kinematics.py",
                         "torch_newton_worker.py", "loaded_material_reference.py",
                         "continuous_ik.py", "continuous_factored_ik.py", "continuous_constrained_ik.py")}


def configure_plan_prefix(plan, config=None, provenance=None, *, required=False):
    """Validate against the native source clock and return a separate plan."""
    existing = plan.metadata.get("source_prefix_reference")
    if config is not None and existing is not None and config != existing:
        raise ValueError("Source prefix configuration conflicts with the authored plan")
    config = existing if config is None else config
    if config is None:
        if required:
            raise ValueError("Standard augmentation requires source_prefix_reference on every plan or --source-prefix-config")
        return plan
    with np.load(Path(plan.source_motion_path).expanduser(), allow_pickle=False) as source:
        qpos = source["joint_pos"]
        prefix_weights(config, len(qpos))
        yaw = prefix_root_yaw_condition(config, plan.surface_transforms, qpos,
                                       plan.metadata.get("root_yaw_condition"))
    metadata = dict(plan.metadata, source_prefix_reference=dict(config))
    metadata["root_yaw_condition"] = yaw
    if provenance is not None:
        metadata["source_prefix_configuration"] = dict(provenance)
    return replace(plan, metadata=metadata)


def verify_prefix_diagnostics(diagnostics, expected, expected_yaw=None):
    if diagnostics.get("source_prefix_reference") != expected:
        raise ValueError("Generated source prefix reference does not match its effective plan")
    if expected is not None:
        actual = diagnostics.get("root_yaw_condition")
        if (expected_yaw is None or actual is None
                or diagnostics.get("root_yaw_optimized") is not True
                or not _same_yaw(actual["reference_delta_degrees"], expected_yaw["reference_delta_degrees"])):
            raise ValueError("Generated root heading does not match the source prefix surface rotation")


def _prefix_transform(config, transforms):
    matching = [t for t in transforms if t.get("transform_id") == config["surface_transform_id"]]
    if len(matching) != 1:
        raise ValueError("Source prefix surface transform is missing or ambiguous")
    return matching[0]


def _same_yaw(first, second):
    angles = np.deg2rad([first, second])
    return bool(np.isfinite(angles).all() and np.allclose(
        [np.cos(angles[0]), np.sin(angles[0])],
        [np.cos(angles[1]), np.sin(angles[1])], rtol=0., atol=1.e-7))


def prefix_root_yaw_condition(config, transforms, source_qpos, existing=None):
    """Bind root attitude to the exact rigid map used by the world targets.

    IK currently supports world-Z edits. Reject tilted maps rather than mapping
    positions while leaving the source attitude unchanged. Source poses remain
    untouched; the derived condition rotates the optimizer's root initializer.
    """
    transform = _prefix_transform(config, transforms)
    mapped = map_points_between_surface_frames(
        np.concatenate((np.zeros((1, 3)), np.eye(3))),
        transform["source_surface"], transform["target_surface"])
    rotation = (mapped[1:] - mapped[0]).T
    yaw = float(np.rad2deg(np.arctan2(rotation[1, 0], rotation[0, 0])))
    c, s = np.cos(np.deg2rad(yaw)), np.sin(np.deg2rad(yaw))
    if not np.allclose(rotation, [[c, -s, 0.], [s, c, 0.], [0., 0., 1.]], rtol=0., atol=1.e-7):
        raise ValueError("Source prefix surface rotation must be world-Z yaw for the current IK backend")
    qpos = np.asarray(source_qpos, dtype=float)
    if (qpos.ndim != 2 or qpos.shape[1] < 7 or not len(qpos)
            or not np.isfinite(qpos[0]).all()
            or not np.isclose(np.linalg.norm(qpos[0, 3:7]), 1., rtol=0., atol=1.e-5)):
        raise ValueError("Source prefix requires a finite source initial pose with normalized WXYZ root quaternion")
    if existing is not None:
        if not _same_yaw(existing["reference_delta_degrees"], yaw):
            raise ValueError("Root heading conflicts with the source prefix surface rotation")
        return dict(existing)
    return dict(reference_delta_degrees=yaw, initial_qpos=qpos[0].tolist())


def rotate_root_reference(root_source, yaw_degrees):
    """Left-compose the same world rotation, retaining the mapped root positions."""
    from scipy.spatial.transform import Rotation
    root = np.array(root_source, dtype=float, copy=True)
    if (root.ndim != 2 or root.shape[1] != 7 or not np.isfinite(root).all()
            or not np.isfinite(yaw_degrees)
            or not np.allclose(np.linalg.norm(root[:, 3:7], axis=1), 1., rtol=0., atol=1.e-5)):
        raise ValueError("Root rotation requires finite positions and normalized WXYZ quaternions")
    root[:, 3:7] = (Rotation.from_euler("z", yaw_degrees, degrees=True) *
                   Rotation.from_quat(root[:, [4, 5, 6, 3]])).as_quat()[:, [3, 0, 1, 2]]
    return root


def prefix_weights(config, frames):
    required = {"schema", "hold_frames", "transition_end_frame", "surface_transform_id",
                "joint_prior_scale", "semantic_weight"}
    if set(config) != required or config["schema"] != SCHEMA:
        raise ValueError("Invalid source_prefix_reference contract")
    hold, end = config["hold_frames"], config["transition_end_frame"]
    if (type(hold) is not int or type(end) is not int or not 1 <= hold < end < frames):
        raise ValueError("Source prefix requires 1 <= hold_frames < transition_end_frame < frame count")
    if not isinstance(config["surface_transform_id"], str) or not config["surface_transform_id"]:
        raise ValueError("Source prefix requires an explicit surface transform")
    for name in ("joint_prior_scale", "semantic_weight"):
        if not np.isfinite(config[name]) or config[name] <= 0:
            raise ValueError(f"Source prefix {name} must be positive and finite")
    # hold_frames is exclusive. Both endpoints have zero first/second slope.
    u = np.clip((np.arange(frames) - (hold - 1)) / (end - (hold - 1)), 0., 1.)
    return 1. - (6. * u**5 - 15. * u**4 + 10. * u**3)


def apply_source_prefix(spec, source_keypoints, transforms, config):
    """Return a taskspace with a rigid source prefix and untouched source data."""
    if spec.frame_start != 0:
        raise ValueError("Source prefix requires a frame-zero taskspace")
    alpha = prefix_weights(config, spec.frame_count)
    transform = _prefix_transform(config, transforms)
    source = np.stack([source_keypoints[name] for name in spec.semantic_names], axis=1)
    if source.shape != spec.semantic_targets_w.shape or not np.isfinite(source).all():
        raise ValueError("Source prefix needs complete finite same-clock source keypoints")
    rigid = map_points_between_surface_frames(source, transform["source_surface"], transform["target_surface"])
    metadata = dict(spec.metadata)
    metadata["source_prefix_reference"] = dict(config)
    metadata["root_yaw_condition"] = prefix_root_yaw_condition(
        config, transforms, spec.source_qpos, metadata.get("root_yaw_condition"))
    metadata["source_prefix_reference_contract"] = "rigid_source_semantic_and_joint_prior; solved_trajectory_not_spliced"
    return replace(spec,
        semantic_targets_w=alpha[:, None, None] * rigid + (1-alpha[:, None, None]) * spec.semantic_targets_w,
        semantic_weights=alpha[:, None] * config["semantic_weight"] + (1-alpha[:, None]) * spec.semantic_weights,
        metadata=metadata)


def prefix_joint_prior_scales(config, frames, existing):
    alpha = prefix_weights(config, frames)
    existing = np.asarray(existing, dtype=float)
    if existing.ndim < 1 or existing.shape[0] != frames:
        raise ValueError("Source prefix joint priors must share the source frame clock")
    alpha = alpha.reshape((frames,) + (1,) * (existing.ndim - 1))
    return alpha * np.maximum(existing, config["joint_prior_scale"]) + (1-alpha) * existing
