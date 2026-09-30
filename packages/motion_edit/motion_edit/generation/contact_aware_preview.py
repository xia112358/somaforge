from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.io import read_contact_surfaces
from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact.newton_bindings import bind_newton_contact_patches
from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, validate_contact_edit_plan
from motion_edit.contact_laplacian.schema import BatchContactLaplacianConfig
from motion_edit.generation.lte_fullbody import (
    LTE_FULLBODY_KEYPOINT_LINKS,
    _batch_contact_laplacian_proxy_motion,
    _load_motion_npz,
    _stamp_robot_asset,
)
from motion_edit.generation.task_variant_compat import (
    apply_pose_edits_to_proxy,
    expand_task_variant_plan,
    pose_edits_for_semantic_proxy,
)
from motion_edit.generation.taskspace_builder import build_contact_aware_taskspace_motion
from motion_edit.generation.taskspace_spec import write_contact_aware_taskspace_motion
from motion_edit.paths import LAYERS_ROOT


@dataclass(frozen=True)
class ContactAwarePreviewResult:
    output_motion_path: Path
    semantic_task_proxy_path: Path
    taskspace_spec_path: Path
    ik_output_path: Path
    binding_summary: dict[str, Any]
    diagnostics: dict[str, Any]
    warnings: tuple[str, ...]


def _resolve_layers_root(layers_root: Path | None, *, contact_layer: str) -> Path:
    """Resolve runtime Motion Edit layers when an isolated worktree has no data symlink."""

    if layers_root is not None:
        return Path(layers_root).expanduser().resolve()
    configured_root = os.environ.get("SOMAFORGE_ROOT")
    if configured_root:
        runtime_layers = (
            Path(configured_root).expanduser().resolve()
            / "runtime"
            / "current"
            / "motion_edit"
            / "data"
            / "layers"
        )
        if (runtime_layers / contact_layer).is_dir():
            return runtime_layers
    if (LAYERS_ROOT / contact_layer).is_dir():
        return LAYERS_ROOT
    return LAYERS_ROOT


def _contact_binding_motion(
    plan: ContactEditPlan,
    *,
    source_motion: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Select the Newton rollout that owns raw contacts and their body poses."""

    required_raw = (
        "raw_contact_count",
        "raw_contact_shape0",
        "raw_contact_shape1",
        "raw_contact_body0",
        "raw_contact_body1",
        "raw_contact_point0_w",
        "raw_contact_point1_w",
        "raw_contact_normal_w",
        "raw_contact_force_w",
    )
    if all(key in source_motion for key in required_raw):
        return source_motion, str(plan.source_motion_path)

    candidate_value = plan.metadata.get("contact_force_source_path")
    if not candidate_value:
        return source_motion, str(plan.source_motion_path)
    candidate = Path(str(candidate_value)).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"Newton contact source motion is missing: {candidate}")
    contact_motion = _load_motion_npz(candidate)
    missing = [key for key in required_raw if key not in contact_motion]
    if missing:
        raise ValueError(f"Newton contact source motion is missing raw-contact arrays: {missing}")

    source_frames = int(np.asarray(source_motion["joint_pos"]).shape[0])
    contact_frames = int(np.asarray(contact_motion["body_pos_w"]).shape[0])
    if contact_frames != source_frames:
        raise ValueError(
            f"Newton contact source frame count differs from source motion: {contact_frames} != {source_frames}"
        )
    source_fps = float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    contact_fps = float(np.asarray(contact_motion["fps"]).reshape(-1)[0])
    if not np.isclose(source_fps, contact_fps, atol=1.0e-6, rtol=0.0):
        raise ValueError(f"Newton contact source fps differs from source motion: {contact_fps} != {source_fps}")
    source_joint_names = [str(item) for item in np.asarray(source_motion["joint_names"]).reshape(-1)]
    contact_joint_names = [str(item) for item in np.asarray(contact_motion["joint_names"]).reshape(-1)]
    if contact_joint_names != source_joint_names:
        raise ValueError("Newton contact source joint_names differ from source motion")
    return contact_motion, str(candidate)


def _run_pyroki_preview_subprocess(
    *,
    taskspace_path: Path,
    source_motion_path: Path,
    ik_output_path: Path,
    ik_script: str | Path | None,
    ik_conda_env: str,
    ik_max_nfev: int | None,
    ik_q_acceleration_weight: float | None = None,
    ik_collision_similarity_weight: float | None = None,
    ik_collision_max_refinements: int | None = None,
    ik_collision_reference_cache: str | Path | None = None,
) -> None:
    worker_name = os.environ.get("SOMAFORGE_IK_WORKER_SOCKET")
    if worker_name:
        kwargs: dict[str, Any] = {
            "lte_path": str(taskspace_path.resolve()),
            "source_motion_path": str(source_motion_path.resolve()),
            "output_path": str(ik_output_path.resolve()),
        }
        if ik_max_nfev is not None:
            kwargs["max_nfev"] = int(ik_max_nfev)
        if ik_q_acceleration_weight is not None:
            kwargs["q_acceleration_weight"] = float(ik_q_acceleration_weight)
        if ik_collision_similarity_weight is not None:
            kwargs["collision_similarity_weight"] = float(
                ik_collision_similarity_weight
            )
        if ik_collision_max_refinements is not None:
            kwargs["collision_max_refinements"] = int(
                ik_collision_max_refinements
            )
        if ik_collision_reference_cache is not None:
            kwargs["collision_reference_cache_path"] = str(
                Path(ik_collision_reference_cache).expanduser().resolve()
            )
        address = (
            "\0" + worker_name[1:]
            if worker_name.startswith("@")
            else worker_name
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(address)
            stream = client.makefile("rw", encoding="utf-8")
            stream.write(json.dumps({"kwargs": kwargs}) + "\n")
            stream.flush()
            response = json.loads(stream.readline())
        if not response.get("ok"):
            raise RuntimeError(
                "persistent PyRoki worker failed:\n"
                + str(response.get("traceback", response))
            )
        if not ik_output_path.is_file():
            raise FileNotFoundError(ik_output_path)
        return
    script = Path(ik_script).expanduser() if ik_script is not None else Path(__file__).with_name("pyroki_fullbody_ik.py")
    package_root = Path(__file__).resolve().parents[2]
    target_env = str(ik_conda_env)
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    current_env_name = Path(current_env).name if current_env else ""
    interpreter = (
        [sys.executable]
        if target_env in {current_env, current_env_name}
        else ["conda", "run", "-n", target_env, "python"]
    )
    cmd = [
        *interpreter,
        str(script.resolve()),
        "--taskspace-spec",
        str(taskspace_path.resolve()),
        "--source-motion",
        str(source_motion_path.resolve()),
        "--out",
        str(ik_output_path.resolve()),
    ]
    if ik_max_nfev is not None:
        cmd.extend(["--max-nfev", str(int(ik_max_nfev))])
    if ik_q_acceleration_weight is not None:
        cmd.extend(["--q-acceleration-weight", str(float(ik_q_acceleration_weight))])
    if ik_collision_similarity_weight is not None:
        cmd.extend(
            [
                "--collision-similarity-weight",
                str(float(ik_collision_similarity_weight)),
            ]
        )
    if ik_collision_max_refinements is not None:
        cmd.extend(
            [
                "--collision-max-refinements",
                str(int(ik_collision_max_refinements)),
            ]
        )
    if ik_collision_reference_cache is not None:
        cmd.extend(
            [
                "--collision-reference-cache",
                str(Path(ik_collision_reference_cache).expanduser().resolve()),
            ]
        )
    subprocess_env = dict(os.environ)
    python_paths = [
        str(package_root),
        str(package_root.parent / "somaforge_core"),
    ]
    inherited_python_path = subprocess_env.get("PYTHONPATH")
    if inherited_python_path:
        python_paths.append(inherited_python_path)
    subprocess_env["PYTHONPATH"] = os.pathsep.join(python_paths)
    subprocess.run(
        cmd,
        cwd=str(package_root),
        env=subprocess_env,
        check=True,
    )


def _task_visualization_proxy(
    *,
    proxy: dict[str, Any],
    source_motion: dict[str, Any],
) -> dict[str, Any]:
    """Make the first-stage dense task compatible with the existing body viewer."""

    output = dict(proxy)
    passthrough = (
        "fps",
        "joint_pos",
        "joint_vel",
        "joint_names",
        "body_names",
        "body_quat_w",
        "body_ang_vel_w",
    )
    for key in passthrough:
        if key not in output and key in source_motion:
            output[key] = np.asarray(source_motion[key])
    if "body_pos_w" not in output or "body_lin_vel_w" not in output:
        raise ValueError("semantic task proxy must contain body_pos_w and body_lin_vel_w")
    if "body_quat_w" not in output:
        positions = np.asarray(output["body_pos_w"])
        quaternions = np.zeros((*positions.shape[:2], 4), dtype=np.float32)
        quaternions[..., 0] = 1.0
        output["body_quat_w"] = quaternions
    if "body_ang_vel_w" not in output:
        output["body_ang_vel_w"] = np.zeros_like(np.asarray(output["body_pos_w"]), dtype=np.float32)
    output["algorithm"] = np.asarray("motion_edit_contact_aware_semantic_task_proxy")
    output["is_qpos"] = np.asarray(False)
    output["note"] = np.asarray(
        "First-stage dense task-space target. Green body points are generated targets; the URDF pose remains the source joint seed."
    )
    return output


def merge_pyroki_preview_motion(
    *,
    source_motion: dict[str, Any],
    ik_motion: dict[str, Any],
    plan: ContactEditPlan,
    proxy_metadata: dict[str, Any],
    semantic_task_proxy_path: Path | None = None,
    taskspace_path: Path,
    ik_output_path: Path,
    binding_summary: dict[str, Any],
) -> dict[str, Any]:
    required = (
        "fps",
        "joint_pos",
        "joint_vel",
        "joint_names",
        "body_names",
        "body_pos_w",
        "body_quat_w",
        "body_lin_vel_w",
        "body_ang_vel_w",
    )
    missing = [key for key in required if key not in ik_motion]
    if missing:
        raise ValueError(f"PyRoki preview output is missing required fields: {missing}")

    generated = dict(source_motion)
    stale_exact = {
        "kinematics_provenance_json",
        "contact_force_provenance_json",
        "raw_contact_source",
        "contact_force_part_position_source",
    }
    for key in list(generated):
        if (
            key in stale_exact
            or key.startswith("raw_contact_")
            or key.startswith("contact_force_")
        ):
            generated.pop(key, None)
    for key in required:
        generated[key] = np.asarray(ik_motion[key])
    for key in (
        "is_qpos",
        "ik_backend",
        "kinematics_backend",
        "newton_canonicalization_required",
        "robot_urdf",
        "target_names",
        "ik_diagnostics_json",
    ):
        if key in ik_motion:
            generated[key] = np.asarray(ik_motion[key])

    metadata = {
        **dict(proxy_metadata),
        "output_kind": "pyroki_contact_aware_preview",
        "joint_consistency": "pyroki_urdf_fk",
        "kinematics_provenance": "preview_only_not_newton",
        "newton_canonicalization_required": True,
        "semantic_task_proxy_motion": str(semantic_task_proxy_path) if semantic_task_proxy_path is not None else None,
        "contact_aware_taskspace_motion": str(taskspace_path),
        "pyroki_preview_motion": str(ik_output_path),
        "newton_contact_patch_binding": binding_summary,
        "source_plan_id": plan.plan_id,
        "source_motion": plan.source_motion_path,
    }
    generated["motion_edit_generation_metadata"] = np.asarray(json.dumps(metadata, sort_keys=True))
    generated["source_contact_edit_plan"] = np.asarray(plan.plan_id)
    generated["source_motion_path"] = np.asarray(plan.source_motion_path)
    from somaforge_core.support_evidence import reference_only_support
    reference_only_support(generated, reason='IK preview has not been physically executed')
    return generated


def _json_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = np.asarray(value, dtype=object)
    item = raw.item() if raw.ndim == 0 else raw.reshape(-1)[0]
    if isinstance(item, bytes):
        item = item.decode("utf-8")
    try:
        parsed = json.loads(str(item))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}
