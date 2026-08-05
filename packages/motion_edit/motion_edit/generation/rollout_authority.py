from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


_REQUIRED_ROLLOUT_FIELDS: tuple[str, ...] = (
    "fps",
    "joint_pos",
    "joint_vel",
    "joint_names",
    "body_names",
    "body_pos_w",
    "body_quat_w",
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
_INSTALLED = False


def _has_force_rollout_contract(motion: Mapping[str, Any]) -> bool:
    return all(name in motion for name in _REQUIRED_ROLLOUT_FIELDS)


def _resolve_source_path(plan: Any) -> Path:
    """Resolve the single motion used by the complete editing pipeline."""

    path = Path(str(getattr(plan, "source_motion_path"))).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"rollout source motion is missing: {path}")
    legacy = getattr(plan, "metadata", {}).get("contact_force_source_path")
    if legacy is not None:
        legacy_path = Path(str(legacy)).expanduser().resolve()
        if legacy_path != path:
            raise ValueError(
                "source_motion_path and metadata.contact_force_source_path must "
                "refer to the same unified rollout source"
            )
    return path


def _load_source_motion(plan: Any, preview: Any) -> tuple[dict[str, Any], Path]:
    path = _resolve_source_path(plan)
    motion = preview._load_motion_npz(path)
    missing = [name for name in _REQUIRED_ROLLOUT_FIELDS if name not in motion]
    if missing:
        raise ValueError(
            "contact-aware generation requires one unified rollout source as its "
            f"sole reference; {path} is missing: {missing}"
        )
    return motion, path


def _load_force_rollout(plan: Any, preview: Any) -> tuple[dict[str, Any], Path]:
    """Compatibility alias for callers migrating to the unified source."""

    return _load_source_motion(plan, preview)


def _stamp_rollout_authority_metadata(
    generated: dict[str, Any],
    *,
    source_path: Path,
) -> dict[str, Any]:
    output = dict(generated)
    metadata = {}
    if "motion_edit_generation_metadata" in output:
        raw = np.asarray(output["motion_edit_generation_metadata"], dtype=object)
        item = raw.item() if raw.ndim == 0 else raw.reshape(-1)[0]
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        try:
            parsed = json.loads(str(item))
            if isinstance(parsed, dict):
                metadata = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            metadata = {}
    metadata.update(
        {
            "reference_authority": "rollout_source_only",
            "geometry_source_motion": str(source_path),
            "semantic_source_motion": str(source_path),
            "contact_patch_source_motion": str(source_path),
            "contact_target_pose_source_motion": str(source_path),
            "joint_initializer_source_motion": str(source_path),
            "pyroki_source_motion": str(source_path),
            "merge_baseline_motion": str(source_path),
            "reference_role_contract": "single_rollout_source",
            "cross_reference_mixing": False,
        }
    )
    output["motion_edit_generation_metadata"] = np.asarray(
        json.dumps(metadata, sort_keys=True)
    )
    output["source_motion_path"] = np.asarray(str(source_path))
    return output


def generate_contact_aware_pyroki_preview(
    plan_or_path: Any,
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
    semantic_proxy_basis: str | Path | None = None,
    layers_root: Path | None = None,
):
    """Generate every target and initializer from one rollout source motion."""

    from motion_edit.generation import contact_aware_preview as preview

    plan_path: Path | None
    if isinstance(plan_or_path, preview.ContactEditPlan):
        plan = plan_or_path
        plan_path = None
    else:
        plan_path = Path(plan_or_path).expanduser()
        plan = preview.read_contact_edit_plan(plan_path)
    if plan.status not in {"validated", "locked"} and not allow_draft:
        raise ValueError(
            "contact edit plan must be validated or locked; pass allow_draft=True to override"
        )
    preview.validate_contact_edit_plan(plan, allow_free=allow_free)

    output = Path(output_motion_path).expanduser()
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} already exists; pass overwrite=True to replace it")

    source_motion, source_path = _load_source_motion(plan, preview)

    contact_layer = source_contact_layer or plan.source_contact_layer
    resolved_layers_root = preview._resolve_layers_root(
        layers_root,
        contact_layer=contact_layer,
    )
    graph = preview.read_contact_graph(
        resolved_layers_root / contact_layer,
        plan.source_motion_id,
    )
    surface_path = (
        resolved_layers_root
        / contact_layer
        / "surfaces"
        / f"{graph.motion_id}.jsonl"
    )
    source_surfaces = (
        preview.read_contact_surfaces(surface_path)
        if surface_path.is_file()
        else []
    )
    variant = preview.expand_task_variant_plan(
        plan,
        anchors=graph.anchors,
        surfaces=source_surfaces,
    )
    edits = list(variant.edits)
    surfaces = list(variant.surfaces)
    semantic_proxy_pose_edits = preview.pose_edits_for_semantic_proxy(
        edits,
        plan.pose_edits,
    )

    config = preview.BatchContactLaplacianConfig(
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

    if semantic_proxy_basis is None:
        proxy, proxy_warnings, proxy_metadata = (
            preview._batch_contact_laplacian_proxy_motion(
                motion=source_motion,
                source_motion=source_path,
                graph=graph,
                contact_layer_root=resolved_layers_root / contact_layer,
                edits=edits,
                config=config,
                source_plan_path=plan_path,
                plan=plan,
            )
        )
    else:
        if semantic_proxy_pose_edits:
            raise ValueError(
                "semantic proxy basis reuse does not support pose_edits"
            )
        from motion_edit.generation.semantic_proxy_basis import (
            reuse_proportional_semantic_proxy,
        )

        proxy, reuse_scale, proxy_metadata = reuse_proportional_semantic_proxy(
            basis_path=semantic_proxy_basis,
            source_motion=source_motion,
            source_motion_path=source_path,
            edits=edits,
            config=config,
        )
        proxy_warnings = [
            "reused proportional semantic proxy deformation "
            f"with scale={reuse_scale:.9g}"
        ]
    proxy, pose_metadata = preview.apply_pose_edits_to_proxy(
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
        "source_plan": str(plan_path) if plan_path is not None else plan.plan_id,
        "source_plan_id": plan.plan_id,
        "reference_authority": "rollout_source_only",
        "geometry_source_motion": str(source_path),
        "reference_role_contract": "single_rollout_source",
        "cross_reference_mixing": False,
    }
    proxy["motion_edit_generation_metadata"] = np.asarray(
        json.dumps(proxy_metadata, sort_keys=True)
    )

    patches, binding_summary = preview.bind_newton_contact_patches(
        graph.anchors,
        source_motion,
        min_force_norm=float(min_raw_contact_force_norm),
    )
    binding_summary["source_motion_path"] = str(source_path)
    binding_summary["reference_authority"] = "rollout_source_only"

    semantic_names = tuple(
        name
        for name in preview.LTE_FULLBODY_KEYPOINT_LINKS
        if f"keypoint_{name}" in proxy
    )
    if not semantic_names:
        raise ValueError(
            "batch contact-Laplacian produced no semantic keypoint arrays"
        )
    semantic_targets_w = np.stack(
        [
            np.asarray(proxy[f"keypoint_{name}"], dtype=np.float64)
            for name in semantic_names
        ],
        axis=1,
    )
    taskspace = preview.build_contact_aware_taskspace_motion(
        motion_id=graph.motion_id,
        source_motion=source_motion,
        contact_pose_motion=source_motion,
        semantic_names=semantic_names,
        semantic_targets_w=semantic_targets_w,
        patches=patches,
        anchors=graph.anchors,
        surfaces=surfaces,
        edits=edits,
        source_reference_weight=float(source_reference_weight),
        boundary_ramp_frames=int(boundary_ramp_frames),
    )
    taskspace_metadata = dict(taskspace.metadata)
    taskspace_metadata.update(
        {
            "reference_authority": "rollout_source_only",
            "semantic_source_motion": str(source_path),
            "contact_patch_source_motion": str(source_path),
            "contact_target_pose_source_motion": str(source_path),
            "joint_initializer_source_motion": str(source_path),
            "reference_role_contract": "single_rollout_source",
            "cross_reference_mixing": False,
        }
    )
    plan_metadata = dict(plan.metadata or {})
    target_terrain_mesh = plan_metadata.get("target_terrain_mesh")
    if target_terrain_mesh:
        source_terrain_mesh = plan_metadata.get("source_terrain_mesh")
        if not source_terrain_mesh:
            raise ValueError(
                "reference-depth collision IK requires plan.metadata.source_terrain_mesh"
            )
        taskspace_metadata.update(
            {
                "target_terrain_mesh": str(
                    Path(target_terrain_mesh).expanduser().resolve()
                ),
                "source_terrain_mesh": str(
                    Path(source_terrain_mesh).expanduser().resolve()
                ),
                "collision_reference_motion": str(source_path),
                "environment_collision_contract": (
                    "source_rollout_soft_signed_distance_similarity"
                ),
            }
        )
    taskspace = preview.replace(taskspace, metadata=taskspace_metadata)
    taskspace.validate()

    work_dir = (
        Path(intermediate_dir).expanduser()
        if intermediate_dir is not None
        else output.with_suffix("")
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    semantic_task_proxy_path = (
        work_dir / f"{output.stem}.semantic_task_proxy.npz"
    )
    taskspace_path = work_dir / f"{output.stem}.contact_aware_taskspace.npz"
    ik_output_path = work_dir / f"{output.stem}.pyroki_preview.npz"
    np.savez_compressed(
        semantic_task_proxy_path,
        **preview._task_visualization_proxy(
            proxy=proxy,
            source_motion=source_motion,
        ),
    )
    preview.write_contact_aware_taskspace_motion(taskspace_path, taskspace)
    preview._run_pyroki_preview_subprocess(
        taskspace_path=taskspace_path,
        source_motion_path=source_path,
        ik_output_path=ik_output_path,
        ik_script=ik_script,
        ik_conda_env=ik_conda_env,
        ik_max_nfev=ik_max_nfev,
        ik_collision_similarity_weight=ik_collision_similarity_weight,
        ik_collision_max_refinements=ik_collision_max_refinements,
        ik_collision_reference_cache=ik_collision_reference_cache,
    )
    if not ik_output_path.is_file():
        raise FileNotFoundError(
            f"PyRoki IK did not produce {ik_output_path}"
        )
    ik_motion = preview._load_motion_npz(ik_output_path)
    generated = preview.merge_pyroki_preview_motion(
        source_motion=source_motion,
        ik_motion=ik_motion,
        plan=plan,
        proxy_metadata=proxy_metadata,
        semantic_task_proxy_path=semantic_task_proxy_path,
        taskspace_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
    )
    generated = _stamp_rollout_authority_metadata(
        generated,
        source_path=source_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **preview._stamp_robot_asset(generated))

    diagnostics = preview._json_object(ik_motion.get("ik_diagnostics_json"))
    warnings = tuple(
        [
            *variant.warnings,
            *proxy_warnings,
            *[str(item) for item in binding_summary.get("warnings", [])],
            "pose, force, contact timing, and local patch geometry come from one rollout source",
            "output is PyRoki-FK-consistent preview only; direct Newton/MJWarp canonicalization is required",
        ]
    )
    return preview.ContactAwarePreviewResult(
        output_motion_path=output,
        semantic_task_proxy_path=semantic_task_proxy_path,
        taskspace_spec_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
        diagnostics=diagnostics,
        warnings=warnings,
    )


def install_rollout_authority() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from motion_edit.generation import contact_aware_preview as preview

    preview.generate_contact_aware_pyroki_preview = (
        generate_contact_aware_pyroki_preview
    )
    _INSTALLED = True
