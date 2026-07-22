from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.io import read_contact_surfaces
from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact.newton_bindings import bind_newton_contact_patches
from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, validate_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorEditRecord
from motion_edit.contact_laplacian.schema import BatchContactLaplacianConfig
from motion_edit.generation.lte_fullbody import (
    LTE_FULLBODY_KEYPOINT_LINKS,
    _batch_contact_laplacian_proxy_motion,
    _load_motion_npz,
    _stamp_robot_asset,
)
from motion_edit.generation.taskspace_builder import build_contact_aware_taskspace_motion
from motion_edit.generation.taskspace_spec import write_contact_aware_taskspace_motion
from motion_edit.paths import LAYERS_ROOT


@dataclass(frozen=True)
class ContactAwarePreviewResult:
    output_motion_path: Path
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
    ik_conda_env: str = "env_pyroki_climb_projection",
    ik_script: str | Path | None = None,
    ik_max_nfev: int | None = None,
    layers_root: Path = LAYERS_ROOT,
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
    graph = read_contact_graph(layers_root / contact_layer, plan.source_motion_id)
    edits = [ContactAnchorEditRecord(**raw) for raw in plan.edits]
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

    patches, binding_summary = bind_newton_contact_patches(
        graph.anchors,
        motion,
        min_force_norm=float(min_raw_contact_force_norm),
    )
    surface_path = layers_root / contact_layer / "surfaces" / f"{graph.motion_id}.jsonl"
    surfaces = read_contact_surfaces(surface_path) if surface_path.is_file() else []

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
        semantic_names=semantic_names,
        semantic_targets_w=semantic_targets_w,
        patches=patches,
        anchors=graph.anchors,
        surfaces=surfaces,
        edits=edits,
        source_reference_weight=float(source_reference_weight),
        boundary_ramp_frames=int(boundary_ramp_frames),
    )

    work_dir = Path(intermediate_dir).expanduser() if intermediate_dir is not None else output.with_suffix("")
    work_dir.mkdir(parents=True, exist_ok=True)
    taskspace_path = work_dir / f"{output.stem}.contact_aware_taskspace.npz"
    ik_output_path = work_dir / f"{output.stem}.pyroki_preview.npz"
    write_contact_aware_taskspace_motion(taskspace_path, taskspace)
    _run_pyroki_preview_subprocess(
        taskspace_path=taskspace_path,
        source_motion_path=source_motion_path,
        ik_output_path=ik_output_path,
        ik_script=ik_script,
        ik_conda_env=ik_conda_env,
        ik_max_nfev=ik_max_nfev,
    )
    if not ik_output_path.is_file():
        raise FileNotFoundError(f"PyRoki IK did not produce {ik_output_path}")
    ik_motion = _load_motion_npz(ik_output_path)
    generated = merge_pyroki_preview_motion(
        source_motion=motion,
        ik_motion=ik_motion,
        plan=plan,
        proxy_metadata=proxy_metadata,
        taskspace_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **_stamp_robot_asset(generated))

    diagnostics = _json_object(ik_motion.get("ik_diagnostics_json"))
    warnings = tuple(
        [
            *proxy_warnings,
            *[str(item) for item in binding_summary.get("warnings", [])],
            "output is PyRoki-FK-consistent preview only; direct Newton/MJWarp canonicalization is required",
        ]
    )
    return ContactAwarePreviewResult(
        output_motion_path=output,
        taskspace_spec_path=taskspace_path,
        ik_output_path=ik_output_path,
        binding_summary=binding_summary,
        diagnostics=diagnostics,
        warnings=warnings,
    )


def _run_pyroki_preview_subprocess(
    *,
    taskspace_path: Path,
    source_motion_path: Path,
    ik_output_path: Path,
    ik_script: str | Path | None,
    ik_conda_env: str,
    ik_max_nfev: int | None,
) -> None:
    script = Path(ik_script).expanduser() if ik_script is not None else Path(__file__).with_name("pyroki_fullbody_ik.py")
    package_root = Path(__file__).resolve().parents[2]
    cmd = [
        "conda",
        "run",
        "-n",
        str(ik_conda_env),
        "python",
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
    subprocess.run(cmd, cwd=str(package_root), check=True)


def merge_pyroki_preview_motion(
    *,
    source_motion: dict[str, Any],
    ik_motion: dict[str, Any],
    plan: ContactEditPlan,
    proxy_metadata: dict[str, Any],
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
        if key in stale_exact or key.startswith("raw_contact_"):
            generated.pop(key, None)
        elif key.startswith("contact_force_part_w") or key.startswith("contact_force_part_position"):
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
