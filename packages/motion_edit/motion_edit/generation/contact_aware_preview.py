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


def generate_contact_aware_pyroki_preview(
    plan_or_path: ContactEditPlan | str | Path,
    *,
    output_motion_path: str | Path,
    source_contact_layer: str | None = None,
    intermediate_dir: str | Path | None = None,
    overwrite: bool = False,
    allow_draft: bool = False,
    allow_free: bool = False,
    contact_laplacian_iters: int = 5,
    contact_laplacian_damping: float = 1.0e-4,
    contact_laplacian_trust: float = 0.05,
    edit_contact_weight: float = 1000.0,
    fixed_contact_weight: float = 1000.0,
    temporal_laplacian_weight: float = 10.0,
    body_relative_weight: float = 10.0,
    q_prior_weight: float = 0.05,
    q_smooth_weight: float = 1.0,
    mesh_laplacian_weight: float = 0.0,
    source_reference_weight: float = 0.01,
    boundary_ramp_frames: int = 10,
    min_raw_contact_force_norm: float = 0.0,
    ik_conda_env: str = "env_somaforge",
    ik_script: str | Path | None = None,
    ik_max_nfev: int | None = None,
    ik_collision_similarity_weight: float | None = None,
    ik_collision_max_refinements: int | None = None,
    ik_collision_reference_cache: str | Path | None = None,
    layers_root: Path | None = None,
) -> ContactAwarePreviewResult:
    """Generate one PyRoki-FK-consistent edited motion without starting Isaac.

    The output intentionally has no Newton kinematics provenance. It is a preview
    trajectory and must be passed through the direct Newton/MJWarp canonicalizer
    before WBT training or force-bearing export.
    """

    plan_path: Path | None
    if isinstance(plan_or_path, ContactEditPlan):
        plan = plan_or_path
        plan_path = None
    else:
        plan_path = Path(plan_or_path).expanduser()
        plan = read_contact_edit_plan(plan_path)
    if plan.status not in {"validated", "locked"} and not allow_draft:
        raise ValueError("contact edit plan must be validated or locked; pass allow_draft=True to override")
    validate_contact_edit_plan(plan, allow_free=allow_free)

    output = Path(output_motion_path).expanduser()
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} already exists; pass overwrite=True to replace it")
    source_motion_path = Path(plan.source_motion_path).expanduser()
    if not source_motion_path.is_file():
        raise FileNotFoundError(source_motion_path)
    motion = _load_motion_npz(source_motion_path)

    contact_layer = source_contact_layer or plan.source_contact_layer
    layers_root = _resolve_layers_root(layers_root, contact_layer=contact_layer)
    graph = read_contact_graph(layers_root / contact_layer, plan.source_motion_id)
    surface_path = layers_root / contact_layer / "surfaces" / f"{graph.motion_id}.jsonl"
    source_surfaces = read_contact_surfaces(surface_path) if surface_path.is_file() else []
    variant = expand_task_variant_plan(plan, anchors=graph.anchors, surfaces=source_surfaces)
    edits = list(variant.edits)
    surfaces = list(variant.surfaces)
    semantic_proxy_pose_edits = pose_edits_for_semantic_proxy(
        edits,
        plan.pose_edits,
    )

    config = BatchContactLaplacianConfig(
        num_iters=int(contact_laplacian_iters),
        damping=float(contact_laplacian_damping),
        trust_region=float(contact_laplacian_trust),
        edit_contact_weight=float(edit_contact_weight),
        fixed_contact_weight=float(fixed_contact_weight),
        temporal_laplacian_weight=float(temporal_laplacian_weight),
        body_relative_weight=float(body_relative_weight),
        q_prior_weight=float(q_prior_weight),
        q_smooth_weight=float(q_smooth_weight),
        mesh_laplacian_weight=float(mesh_laplacian_weight),
    )
    proxy, proxy_warnings, proxy_metadata = _batch_contact_laplacian_proxy_motion(
        motion=motion,
        source_motion=source_motion_path,
        graph=graph,
        contact_layer_root=layers_root / contact_layer,
        edits=edits,
        config=config,
        source_plan_path=plan_path,
        plan=plan,
    )
    proxy, pose_metadata = apply_pose_edits_to_proxy(
        proxy,
        semantic_proxy_pose_edits,
    )
    proxy_metadata = {
        **dict(proxy_metadata),
        "task_variant_expansion": variant.metadata,
        "pose_edit_application": pose_metadata,
        "semantic_proxy_contact_edit_count": len(edits),
        "semantic_proxy_pose_edit_count": len(semantic_proxy_pose_edits),
        "rigid_patch_contact_edit_count": len(edits),
    }

    binding_motion, binding_motion_path = _contact_binding_motion(plan, source_motion=motion)
    patches, binding_summary = bind_newton_contact_patches(
        graph.anchors,
        binding_motion,
        min_force_norm=float(min_raw_contact_force_norm),
    )
    binding_summary["source_motion_path"] = binding_motion_path

    semantic_names = tuple(name for name in LTE_FULLBODY_KEYPOINT_LINKS if f"keypoint_{name}" in proxy)
    if not semantic_names:
        raise ValueError("batch contact-Laplacian produced no semantic keypoint arrays")
    semantic_targets_w = np.stack(
        [np.asarray(proxy[f"keypoint_{name}"], dtype=np.float64) for name in semantic_names],
        axis=1,
    )
    taskspace = build_contact_aware_taskspace_motion(
        motion_id=graph.motion_id,
        source_motion=motion,
        contact_pose_motion=binding_motion,
        semantic_names=semantic_names,
        semantic_targets_w=semantic_targets_w,
        patches=patches,
        anchors=graph.anchors,
        surfaces=surfaces,
        edits=edits,
        source_reference_weight=float(source_reference_weight),
        boundary_ramp_frames=int(boundary_ramp_frames),
    )
    plan_metadata = dict(plan.metadata or {})
    target_terrain_mesh = plan_metadata.get("target_terrain_mesh")
    if target_terrain_mesh:
        source_terrain_mesh = plan_metadata.get("source_terrain_mesh")
        if not source_terrain_mesh:
            raise ValueError(
                "reference-depth collision IK requires plan.metadata.source_terrain_mesh"
            )
        taskspace = replace(
            taskspace,
            metadata={
                **dict(taskspace.metadata),
                "target_terrain_mesh": str(
                    Path(target_terrain_mesh).expanduser().resolve()
                ),
                "source_terrain_mesh": str(
                    Path(source_terrain_mesh).expanduser().resolve()
                ),
                "collision_reference_motion": str(binding_motion_path),
                "environment_collision_contract": (
                    "source_rollout_soft_signed_distance_similarity"
                ),
            },
        )
        taskspace.validate()

    work_dir = Path(intermediate_dir).expanduser() if intermediate_dir is not None else output.with_suffix("")
    work_dir.mkdir(parents=True, exist_ok=True)
    semantic_task_proxy_path = work_dir / f"{output.stem}.semantic_task_proxy.npz"
    taskspace_path = work_dir / f"{output.stem}.contact_aware_taskspace.npz"
    ik_output_path = work_dir / f"{output.stem}.pyroki_preview.npz"
    np.savez_compressed(
        semantic_task_proxy_path,
        **_task_visualization_proxy(proxy=proxy, source_motion=motion),
    )
    write_contact_aware_taskspace_motion(taskspace_path, taskspace)
    _run_pyroki_preview_subprocess(
        taskspace_path=taskspace_path,
        source_motion_path=source_motion_path,
        ik_output_path=ik_output_path,
        ik_script=ik_script,
        ik_conda_env=ik_conda_env,
        ik_max_nfev=ik_max_nfev,
        ik_collision_similarity_weight=ik_collision_similarity_weight,
        ik_collision_max_refinements=ik_collision_max_refinements,
        ik_collision_reference_cache=ik_collision_reference_cache,
    )
    if not ik_output_path.is_file():
        raise FileNotFoundError(f"PyRoki IK did not produce {ik_output_path}")
    ik_motion = _load_motion_npz(ik_output_path)
    generated = merge_pyroki_preview_motion(
        source_motion=motion,
        ik_motion=ik_motion,
        plan=plan,
        proxy_metadata=proxy_metadata,
        semantic_task_proxy_path=semantic_task_proxy_path,
        taskspace_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **_stamp_robot_asset(generated))

    diagnostics = _json_object(ik_motion.get("ik_diagnostics_json"))
    warnings = tuple(
        [
            *variant.warnings,
            *proxy_warnings,
            *[str(item) for item in binding_summary.get("warnings", [])],
            "output is PyRoki-FK-consistent preview only; direct Newton/MJWarp canonicalization is required",
        ]
    )
    return ContactAwarePreviewResult(
        output_motion_path=output,
        semantic_task_proxy_path=semantic_task_proxy_path,
        taskspace_spec_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
        diagnostics=diagnostics,
        warnings=warnings,
    )


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
