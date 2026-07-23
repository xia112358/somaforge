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


def _resolve_force_rollout_path(plan: Any) -> Path:
    """Resolve the only motion allowed to drive contact-aware generation.

    ``contact_force_source_path`` is authoritative when present. The plan source
    path is accepted only when that file itself is already the force-bearing
    rollout. A kinematic reference without raw Newton contacts is never used as
    a fallback geometry source.
    """

    configured = getattr(plan, "metadata", {}).get("contact_force_source_path")
    value = configured or getattr(plan, "source_motion_path")
    path = Path(str(value)).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"force-bearing rollout motion is missing: {path}")
    return path


def _load_force_rollout(plan: Any, preview: Any) -> tuple[dict[str, Any], Path]:
    path = _resolve_force_rollout_path(plan)
    motion = preview._load_motion_npz(path)
    missing = [name for name in _REQUIRED_ROLLOUT_FIELDS if name not in motion]
    if missing:
        raise ValueError(
            "contact-aware generation requires one force-bearing rollout as its "
            f"sole reference; {path} is missing: {missing}"
        )
    return motion, path


def _stamp_rollout_authority_metadata(
    generated: dict[str, Any],
    *,
    rollout_path: Path,
    original_plan_source_path: str,
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
            "reference_authority": "force_rollout_only",
            "geometry_source_motion": str(rollout_path),
            "semantic_source_motion": str(rollout_path),
            "contact_patch_source_motion": str(rollout_path),
            "joint_initializer_source_motion": str(rollout_path),
            "pyroki_source_motion": str(rollout_path),
            "merge_baseline_motion": str(rollout_path),
            "original_plan_source_motion_record_only": str(original_plan_source_path),
            "cross_reference_mixing": False,
        }
    )
    output["motion_edit_generation_metadata"] = np.asarray(
        json.dumps(metadata, sort_keys=True)
    )
    output["source_motion_path"] = np.asarray(str(rollout_path))
    output["force_rollout_source_path"] = np.asarray(str(rollout_path))
    output["original_plan_source_motion_path"] = np.asarray(
        str(original_plan_source_path)
    )
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
    ik_conda_env: str = "env_pyroki_climb_projection",
    ik_script: str | Path | None = None,
    ik_max_nfev: int | None = None,
    layers_root: Path | None = None,
):
    """Generate from exactly one force-bearing rollout reference.

    The force rollout supplies semantic keypoints, fixed and edited contact
    handles, rigid patch frames, source q/qdot, PyRoki initialization, and the
    final merge baseline. ``plan.source_motion_path`` is retained only as
    provenance and never participates in optimization.
    """

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

    rollout_motion, rollout_path = _load_force_rollout(plan, preview)

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

    proxy, proxy_warnings, proxy_metadata = (
        preview._batch_contact_laplacian_proxy_motion(
            motion=rollout_motion,
            source_motion=rollout_path,
            graph=graph,
            contact_layer_root=resolved_layers_root / contact_layer,
            edits=edits,
            config=config,
            source_plan_path=plan_path,
            plan=plan,
        )
    )
    proxy, pose_metadata = preview.apply_pose_edits_to_proxy(
        proxy,
        plan.pose_edits,
    )
    proxy_metadata = {
        **dict(proxy_metadata),
        "task_variant_expansion": variant.metadata,
        "pose_edit_application": pose_metadata,
        "reference_authority": "force_rollout_only",
        "geometry_source_motion": str(rollout_path),
        "original_plan_source_motion_record_only": str(plan.source_motion_path),
        "cross_reference_mixing": False,
    }

    patches, binding_summary = preview.bind_newton_contact_patches(
        graph.anchors,
        rollout_motion,
        min_force_norm=float(min_raw_contact_force_norm),
    )
    binding_summary["source_motion_path"] = str(rollout_path)
    binding_summary["reference_authority"] = "force_rollout_only"

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
        source_motion=rollout_motion,
        contact_pose_motion=rollout_motion,
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
            "reference_authority": "force_rollout_only",
            "semantic_source_motion": str(rollout_path),
            "contact_patch_source_motion": str(rollout_path),
            "joint_initializer_source_motion": str(rollout_path),
            "original_plan_source_motion_record_only": str(
                plan.source_motion_path
            ),
            "cross_reference_mixing": False,
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
            source_motion=rollout_motion,
        ),
    )
    preview.write_contact_aware_taskspace_motion(taskspace_path, taskspace)
    preview._run_pyroki_preview_subprocess(
        taskspace_path=taskspace_path,
        source_motion_path=rollout_path,
        ik_output_path=ik_output_path,
        ik_script=ik_script,
        ik_conda_env=ik_conda_env,
        ik_max_nfev=ik_max_nfev,
    )
    if not ik_output_path.is_file():
        raise FileNotFoundError(
            f"PyRoki IK did not produce {ik_output_path}"
        )
    ik_motion = preview._load_motion_npz(ik_output_path)
    generated = preview.merge_pyroki_preview_motion(
        source_motion=rollout_motion,
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
        rollout_path=rollout_path,
        original_plan_source_path=str(plan.source_motion_path),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **preview._stamp_robot_asset(generated))

    diagnostics = preview._json_object(ik_motion.get("ik_diagnostics_json"))
    warnings = tuple(
        [
            *variant.warnings,
            *proxy_warnings,
            *[str(item) for item in binding_summary.get("warnings", [])],
            "all generation references use the force-bearing rollout; the plan source motion is provenance only",
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
