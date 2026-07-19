"""Dataset augmentation within the Motion Edit workflow.

Editing plans remain in :mod:`motion_edit.contact`, and one-plan trajectory
solving remains in :mod:`motion_edit.generation`.  This module owns only the
outer dataset workflow: durable execution state, static candidate acceptance,
and MotionVersion registration after acceptance.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core.robot_assets import decode_robot_asset_json

from .contact import read_contact_edit_plan
from .contact.layers import read_contact_graph
from .generation import apply_contact_edit_plan_to_motion
from .io import read_jsonl
from .paths import LAYERS_ROOT
from .storage.canonical import segments_from_contact_transitions, write_motion_version_with_canonical_segments
from .storage.io import write_motion_version
from .storage.schema import MotionVersionRecord

QUEUE_SCHEMA = "motion_edit_augmentation_queue_v1"
ACCEPTED_MANIFEST_SCHEMA = "motion_edit_accepted_augmentations_v1"
SOLVER_COMPATIBILITY_NAME = "batch_contact_laplacian"
SOLVER_CONTRACT = "whole_trajectory_contact_laplacian_then_pyroki"
_IMMUTABLE_JOB_FIELDS = (
    "job_id",
    "plan_id",
    "plan_path",
    "source_motion_id",
    "output_motion_path",
    "motion_version_id",
    "output_contact_layer",
    "output_segment_layer",
)


@dataclass(frozen=True)
class AugmentationAcceptanceReport:
    """Serializable result of static, non-simulator candidate validation."""

    passed: bool
    motion_path: str
    plan_id: str
    checks: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AugmentationQueueJob:
    """Immutable identity of one independently generated edit plan."""

    job_id: str
    plan_id: str
    plan_path: str
    source_motion_id: str
    output_motion_path: str
    motion_version_id: str
    output_contact_layer: str | None = None
    output_segment_layer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AugmentationQueue:
    """Persist execution status separately from accepted dataset membership."""

    state_path: Path
    accepted_manifest_path: Path
    source_plan_manifest: str
    solver: str = SOLVER_CONTRACT
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def open(
        cls,
        *,
        state_path: str | Path,
        accepted_manifest_path: str | Path,
        source_plan_manifest: str | Path,
    ) -> AugmentationQueue:
        state = Path(state_path).expanduser().resolve()
        accepted = Path(accepted_manifest_path).expanduser().resolve()
        queue = cls(
            state_path=state,
            accepted_manifest_path=accepted,
            source_plan_manifest=str(Path(source_plan_manifest).expanduser().resolve()),
        )
        if state.is_file():
            payload = json.loads(state.read_text(encoding="utf-8"))
            if payload.get("schema") != QUEUE_SCHEMA:
                raise ValueError(f"unsupported augmentation queue schema in {state}")
            if payload.get("source_plan_manifest") != queue.source_plan_manifest:
                raise ValueError(f"augmentation queue belongs to a different plan manifest: {state}")
            if payload.get("solver") != queue.solver:
                raise ValueError(f"augmentation queue uses a different solver contract: {state}")
            queue.jobs = {str(key): dict(value) for key, value in dict(payload.get("jobs") or {}).items()}
        return queue

    def ensure_jobs(self, jobs: Iterable[AugmentationQueueJob]) -> None:
        for job in jobs:
            existing = dict(self.jobs.get(job.job_id) or {})
            definition = job.to_dict()
            for name in _IMMUTABLE_JOB_FIELDS:
                if name in existing and existing[name] != definition[name]:
                    raise ValueError(
                        f"augmentation job {job.job_id!r} changed immutable field {name!r}: "
                        f"{existing[name]!r} != {definition[name]!r}"
                    )
            existing.update(definition)
            existing.setdefault("status", "pending")
            existing.setdefault("attempts", 0)
            existing.setdefault("errors", [])
            self.jobs[job.job_id] = existing
        self.save()

    def update(self, job_id: str, *, status: str, **fields: Any) -> dict[str, Any]:
        if job_id not in self.jobs:
            raise KeyError(f"unknown augmentation queue job: {job_id}")
        record = self.jobs[job_id]
        record.update(fields)
        record["status"] = status
        record["updated_at"] = _timestamp()
        self.save()
        self.write_accepted_manifest()
        return record

    def save(self) -> None:
        statuses = [str(record.get("status", "pending")) for record in self.jobs.values()]
        if statuses and all(status == "accepted" for status in statuses):
            status = "complete"
        elif any(status == "running" for status in statuses):
            status = "running"
        elif any(status == "failed" for status in statuses):
            status = "incomplete"
        else:
            status = "pending"
        _atomic_write_json(
            self.state_path,
            {
                "schema": QUEUE_SCHEMA,
                "source_plan_manifest": self.source_plan_manifest,
                "solver": self.solver,
                "status": status,
                "updated_at": _timestamp(),
                "jobs": self.jobs,
            },
        )

    def write_accepted_manifest(self) -> None:
        accepted = [
            dict(record)
            for _, record in sorted(self.jobs.items())
            if record.get("status") == "accepted" and record.get("acceptance", {}).get("passed") is True
        ]
        _atomic_write_json(
            self.accepted_manifest_path,
            {
                "schema": ACCEPTED_MANIFEST_SCHEMA,
                "source_plan_manifest": self.source_plan_manifest,
                "solver": self.solver,
                "acceptance_tier": "static_kinematic",
                "physics_replay_required": True,
                "updated_at": _timestamp(),
                "count": len(accepted),
                "augmentations": accepted,
            },
        )


@dataclass(frozen=True)
class AugmentationRunConfig:
    """Configuration for the outer queue; each job still solves one motion."""

    plan_manifest: str | Path
    start_index: int = 0
    limit: int | None = None
    output_motion_dir: str | Path | None = None
    motion_version_prefix: str = ""
    source_contact_layer: str | None = None
    state_path: str | Path | None = None
    accepted_manifest: str | Path | None = None
    max_attempts: int = 2
    max_proxy_contact_error_m: float = 5.0e-3
    max_environment_anchor_error_m: float = 5.0e-4
    allow_draft: bool = False
    allow_free: bool = False
    fullbody_solver: str = SOLVER_COMPATIBILITY_NAME
    contact_laplacian_iters: int = 8
    contact_laplacian_damping: float = 1.0e-4
    contact_laplacian_trust: float = 0.05
    edit_contact_weight: float = 1000.0
    fixed_contact_weight: float = 1000.0
    temporal_laplacian_weight: float = 40.0
    body_relative_weight: float = 10.0
    q_prior_weight: float = 0.02
    q_smooth_weight: float = 0.0
    mesh_laplacian_weight: float = 1.0
    overwrite: bool = False
    register_motion_version: bool = False
    build_canonical: bool = False
    dry_run: bool = False
    continue_on_error: bool = False
    lte_repo_root: str | Path | None = None
    ik_script: str | Path | None = None
    ik_conda_env: str = "env_pyroki_climb_projection"
    ik_max_nfev: int | None = None
    ik_q_prior_weight: float = 12.0
    ik_q_smooth_weight: float = 60.0
    intermediate_dir: str | Path | None = None


@dataclass(frozen=True)
class AugmentationRunSummary:
    total: int
    generated: int
    accepted: int
    skipped: int
    failed: int
    state_path: str
    accepted_manifest_path: str


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _decode_json_scalar(value: Any, *, name: str) -> dict[str, Any]:
    raw = value.item() if hasattr(value, "item") else value
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        decoded = json.loads(str(raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{name} must decode to an object")
    return decoded


def _require_finite(name: str, value: np.ndarray) -> None:
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} contains NaN or Inf")


def _load_ik_acceptance(metadata: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    raw_path = metadata.get("contact_laplacian_fullbody_ik_motion")
    if not raw_path:
        raise ValueError("generation metadata has no fullbody IK artifact path")
    path = Path(str(raw_path)).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"fullbody IK artifact is missing: {path}")
    with np.load(path, allow_pickle=True) as data:
        if "ik_metadata_json" not in data.files:
            raise ValueError(f"fullbody IK artifact has no ik_metadata_json: {path}")
        metadata = _decode_json_scalar(data["ik_metadata_json"], name="ik_metadata_json")
        solver = str(np.asarray(data.get("ik_solver", np.asarray(""))).reshape(-1)[0])
    if solver != "pyroki_jaxls_whole_trajectory":
        raise ValueError(f"unsupported fullbody IK solver: {solver!r}")
    return path, metadata


def validate_generated_augmentation(
    motion_path: str | Path,
    *,
    expected_plan_id: str,
    max_proxy_contact_error_m: float = 5.0e-3,
    max_environment_anchor_error_m: float = 5.0e-4,
) -> AugmentationAcceptanceReport:
    """Statically validate one generated candidate without Newton replay."""

    path = Path(motion_path).expanduser().resolve()
    checks: dict[str, Any] = {
        "acceptance_tier": "static_kinematic",
        "physics_replay_required": True,
        "max_proxy_contact_error_m": float(max_proxy_contact_error_m),
        "max_environment_anchor_error_m": float(max_environment_anchor_error_m),
    }
    errors: list[str] = []
    try:
        if not path.is_file():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=True) as data:
            required = {
                "joint_pos",
                "joint_vel",
                "joint_names",
                "body_pos_w",
                "body_quat_w",
                "body_names",
                "is_qpos",
                "robot_asset_json",
                "motion_edit_generation_metadata",
            }
            missing = sorted(required - set(data.files))
            if missing:
                raise ValueError(f"generated motion is missing required arrays: {missing}")

            decode_robot_asset_json(data["robot_asset_json"], context=f"augmentation {path}")
            joint_pos = np.asarray(data["joint_pos"], dtype=np.float64)
            joint_vel = np.asarray(data["joint_vel"], dtype=np.float64)
            body_pos = np.asarray(data["body_pos_w"], dtype=np.float64)
            body_quat = np.asarray(data["body_quat_w"], dtype=np.float64)
            joint_names = np.asarray(data["joint_names"]).reshape(-1)
            body_names = np.asarray(data["body_names"]).reshape(-1)
            is_qpos = bool(np.asarray(data["is_qpos"]).reshape(-1)[0])
            generation = _decode_json_scalar(
                data["motion_edit_generation_metadata"],
                name="motion_edit_generation_metadata",
            )

        if joint_pos.ndim != 2 or joint_pos.shape[1] != 36:
            raise ValueError(f"joint_pos must be canonical G1 qpos [T,36], got {joint_pos.shape}")
        if joint_vel.shape != joint_pos.shape:
            raise ValueError(f"joint_vel must match joint_pos {joint_pos.shape}, got {joint_vel.shape}")
        if joint_names.shape != (29,):
            raise ValueError(f"joint_names must contain 29 actuated joints, got {joint_names.shape}")
        if body_pos.ndim != 3 or body_pos.shape[0] != joint_pos.shape[0] or body_pos.shape[2] != 3:
            raise ValueError(f"body_pos_w must be [T,B,3] and match qpos frames, got {body_pos.shape}")
        if body_quat.shape != (*body_pos.shape[:2], 4):
            raise ValueError(f"body_quat_w must be [T,B,4], got {body_quat.shape}")
        if body_names.shape != (body_pos.shape[1],):
            raise ValueError(f"body_names must match body count {body_pos.shape[1]}, got {body_names.shape}")
        if not is_qpos:
            raise ValueError("generated joint_pos is not marked as full qpos")
        for name, value in (
            ("joint_pos", joint_pos),
            ("joint_vel", joint_vel),
            ("body_pos_w", body_pos),
            ("body_quat_w", body_quat),
        ):
            _require_finite(name, value)
        quaternion_norm_error = float(np.max(np.abs(np.linalg.norm(body_quat, axis=2) - 1.0)))
        if quaternion_norm_error > 5.0e-3:
            raise ValueError(f"body quaternion norm error is too large: {quaternion_norm_error:.6g}")

        if generation.get("source_plan_id") != expected_plan_id:
            raise ValueError(
                f"generated source_plan_id={generation.get('source_plan_id')!r} does not match {expected_plan_id!r}"
            )
        if generation.get("fullbody_solver") != SOLVER_COMPATIBILITY_NAME:
            raise ValueError(f"generated candidate used the wrong solver: {generation.get('fullbody_solver')!r}")
        if generation.get("output_kind") != "fullbody_ik_after_contact_laplacian_proxy":
            output_kind = generation.get("output_kind")
            raise ValueError(f"generated candidate is not joint-consistent fullbody output: {output_kind!r}")
        if generation.get("joint_consistency") != "fullbody_ik_subprocess":
            joint_consistency = generation.get("joint_consistency")
            raise ValueError(f"generated candidate has unknown joint consistency: {joint_consistency!r}")
        solver_metadata = dict(generation.get("solver_metadata") or {})
        if solver_metadata.get("solver") != SOLVER_COMPATIBILITY_NAME:
            raise ValueError("generation metadata does not identify the whole-trajectory Contact Laplacian solver")
        evaluation = dict(generation.get("evaluation_summary") or {})
        proxy_error = float(dict(evaluation.get("edited_contact_target_error_after") or {}).get("max", np.inf))
        if not np.isfinite(proxy_error) or proxy_error > float(max_proxy_contact_error_m):
            raise ValueError(
                f"proxy edited-contact error {proxy_error:.6g}m exceeds {float(max_proxy_contact_error_m):.6g}m"
            )

        ik_path, ik_metadata = _load_ik_acceptance(generation)
        hard_anchor_count = int(ik_metadata.get("environment_contact_anchor_count_hard", 0))
        hard_constraint_count = int(ik_metadata.get("hard_constraint_count", 0))
        anchor_error = float(ik_metadata.get("environment_anchor_error_max_m", np.inf))
        if hard_anchor_count < 1 or hard_constraint_count < 3:
            raise ValueError("fullbody IK contains no edited environment-contact hard constraint")
        if not np.isfinite(anchor_error) or anchor_error > float(max_environment_anchor_error_m):
            raise ValueError(
                f"environment-anchor error {anchor_error:.6g}m exceeds {float(max_environment_anchor_error_m):.6g}m"
            )

        checks.update(
            {
                "frame_count": int(joint_pos.shape[0]),
                "qpos_width": int(joint_pos.shape[1]),
                "body_count": int(body_pos.shape[1]),
                "quaternion_norm_error_max": quaternion_norm_error,
                "proxy_contact_error_max_m": proxy_error,
                "environment_anchor_error_max_m": anchor_error,
                "hard_environment_anchor_count": hard_anchor_count,
                "hard_constraint_count": hard_constraint_count,
                "ik_artifact": str(ik_path),
                "solver": SOLVER_CONTRACT,
            }
        )
    except Exception as exc:
        errors.append(str(exc))

    return AugmentationAcceptanceReport(
        passed=not errors,
        motion_path=str(path),
        plan_id=str(expected_plan_id),
        checks=checks,
        errors=errors,
    )


def _read_plan_manifest(path: Path) -> list[object]:
    if path.suffix == ".jsonl":
        manifest: object = read_jsonl(path)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = payload.get("plans", []) if isinstance(payload, dict) else payload
    if not isinstance(manifest, list):
        raise ValueError(f"plan manifest must contain a list of plans: {path}")
    return manifest


def _resolve_plan_path(manifest_path: Path, raw: object) -> Path:
    candidate = Path(str(raw)).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (manifest_path.parent / candidate).resolve()


def _register_accepted_candidate(
    *,
    plan: Any,
    output_motion: Path,
    motion_version_id: str,
    acceptance: dict[str, Any],
    build_canonical: bool,
) -> None:
    metadata = {
        "source_contact_edit_plan": plan.plan_id,
        "generation_mode": "lte_fullbody",
        "fullbody_solver": SOLVER_COMPATIBILITY_NAME,
        "augmentation_acceptance": acceptance,
    }
    if build_canonical:
        if not plan.output_contact_layer:
            raise ValueError(f"{plan.plan_id}: --build-canonical requires output_contact_layer")
        edited_graph = read_contact_graph(LAYERS_ROOT / plan.output_contact_layer, plan.source_motion_id)
        segments = segments_from_contact_transitions(
            edited_graph,
            motion_version_id=motion_version_id,
            motion_path=str(output_motion),
            source="lte_fullbody",
            cut_source="contact_auto",
        )
        record, _ = write_motion_version_with_canonical_segments(
            motion_version_id=motion_version_id,
            motion_path=str(output_motion),
            contact_layer=plan.output_contact_layer,
            segments=segments,
            kind="augmented",
            base_motion_id=plan.source_motion_id,
            source="lte_fullbody",
            reason=f"accepted Motion Edit augmentation {plan.plan_id}",
        )
        write_motion_version(
            MotionVersionRecord(
                motion_version_id=record.motion_version_id,
                motion_path=record.motion_path,
                kind="augmented",
                base_motion_id=plan.source_motion_id,
                motion_asset_id=record.motion_asset_id,
                parent_motion_version_id=record.parent_motion_version_id,
                contact_layer=record.contact_layer,
                canonical_segment_path=record.canonical_segment_path,
                token_catalog_path=record.token_catalog_path,
                edit_plan_id=plan.plan_id,
                metadata=metadata,
            )
        )
        return
    write_motion_version(
        MotionVersionRecord(
            motion_version_id=motion_version_id,
            motion_path=str(output_motion),
            kind="augmented",
            base_motion_id=plan.source_motion_id,
            contact_layer=plan.output_contact_layer,
            edit_plan_id=plan.plan_id,
            metadata=metadata,
        )
    )


def _run_one_generation_attempt(
    *,
    config: AugmentationRunConfig,
    job: AugmentationQueueJob,
    plan: Any,
    plan_path: Path,
    output_motion: Path,
    overwrite: bool,
    dry_run: bool,
) -> Any:
    return apply_contact_edit_plan_to_motion(
        plan,
        output_motion_path=output_motion,
        mode="lte_fullbody",
        source_plan_path=plan_path,
        source_contact_layer=config.source_contact_layer,
        output_contact_layer=plan.output_contact_layer,
        output_segment_layer=plan.output_segment_layer,
        output_motion_version_id=job.motion_version_id,
        overwrite=overwrite,
        dry_run=dry_run,
        register_motion_version=False,
        build_canonical=False,
        allow_draft=config.allow_draft,
        allow_free=config.allow_free,
        fullbody_solver=config.fullbody_solver,
        contact_laplacian_iters=config.contact_laplacian_iters,
        contact_laplacian_damping=config.contact_laplacian_damping,
        contact_laplacian_trust=config.contact_laplacian_trust,
        edit_contact_weight=config.edit_contact_weight,
        fixed_contact_weight=config.fixed_contact_weight,
        temporal_laplacian_weight=config.temporal_laplacian_weight,
        body_relative_weight=config.body_relative_weight,
        q_prior_weight=config.q_prior_weight,
        q_smooth_weight=config.q_smooth_weight,
        mesh_laplacian_weight=config.mesh_laplacian_weight,
        contact_laplacian_proxy_only=False,
        lte_repo_root=config.lte_repo_root,
        ik_script=config.ik_script,
        ik_conda_env=config.ik_conda_env,
        ik_max_nfev=config.ik_max_nfev,
        ik_q_prior_weight=config.ik_q_prior_weight,
        ik_q_smooth_weight=config.ik_q_smooth_weight,
        intermediate_dir=config.intermediate_dir,
    )


def _accept_candidate(
    *,
    config: AugmentationRunConfig,
    plan: Any,
    job: AugmentationQueueJob,
    output_motion: Path,
) -> AugmentationAcceptanceReport:
    report = validate_generated_augmentation(
        output_motion,
        expected_plan_id=plan.plan_id,
        max_proxy_contact_error_m=config.max_proxy_contact_error_m,
        max_environment_anchor_error_m=config.max_environment_anchor_error_m,
    )
    if report.passed and config.register_motion_version:
        _register_accepted_candidate(
            plan=plan,
            output_motion=output_motion,
            motion_version_id=job.motion_version_id,
            acceptance=report.to_dict(),
            build_canonical=config.build_canonical,
        )
    return report


def run_augmentation_queue(
    config: AugmentationRunConfig,
    *,
    emit: Callable[[str], None] = print,
) -> AugmentationRunSummary:
    """Run independent edit plans through generation and static admission."""

    manifest_path = Path(config.plan_manifest).expanduser().resolve()
    if config.fullbody_solver != SOLVER_COMPATIBILITY_NAME:
        raise ValueError(f"only the {SOLVER_COMPATIBILITY_NAME!r} compatibility solver name is accepted")
    if config.max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if config.build_canonical and not config.register_motion_version:
        raise ValueError("build_canonical requires register_motion_version")

    manifest = _read_plan_manifest(manifest_path)
    selected_paths: list[Path] = []
    for index, item in enumerate(manifest):
        if index < config.start_index:
            continue
        if config.limit is not None and len(selected_paths) >= config.limit:
            break
        raw_plan = item.get("plan_path") if isinstance(item, dict) else item
        if not raw_plan:
            raise ValueError(f"plan manifest entry {index} has no plan_path")
        selected_paths.append(_resolve_plan_path(manifest_path, raw_plan))

    plans = [(path, read_contact_edit_plan(path)) for path in selected_paths]
    state_path = (
        Path(config.state_path).expanduser()
        if config.state_path
        else manifest_path.with_name(f"{manifest_path.stem}.queue.json")
    )
    accepted_path = (
        Path(config.accepted_manifest).expanduser()
        if config.accepted_manifest
        else manifest_path.with_name(f"{manifest_path.stem}.accepted.json")
    )
    queue = AugmentationQueue.open(
        state_path=state_path,
        accepted_manifest_path=accepted_path,
        source_plan_manifest=manifest_path,
    )

    jobs: list[AugmentationQueueJob] = []
    job_plans: dict[str, Any] = {}
    for plan_path, plan in plans:
        output_motion = Path(plan.output_motion_path or f"data/motions/generated/{plan.plan_id}.npz").expanduser()
        if config.output_motion_dir:
            output_motion = Path(config.output_motion_dir).expanduser() / output_motion.name
        output_motion = output_motion.resolve()
        motion_version_id = f"{config.motion_version_prefix}{plan.plan_id}"
        job = AugmentationQueueJob(
            job_id=plan.plan_id,
            plan_id=plan.plan_id,
            plan_path=str(plan_path),
            source_motion_id=plan.source_motion_id,
            output_motion_path=str(output_motion),
            motion_version_id=motion_version_id,
            output_contact_layer=plan.output_contact_layer,
            output_segment_layer=plan.output_segment_layer,
        )
        if job.job_id in job_plans:
            raise ValueError(f"duplicate augmentation plan_id in manifest: {job.job_id}")
        jobs.append(job)
        job_plans[job.job_id] = plan
    queue.ensure_jobs(jobs)

    generated = accepted = skipped = failed = 0
    for job in jobs:
        plan = job_plans[job.job_id]
        plan_path = Path(job.plan_path)
        output_motion = Path(job.output_motion_path)
        record = queue.jobs[job.job_id]

        if record.get("status") == "accepted" and output_motion.is_file() and not config.overwrite:
            if config.register_motion_version and not record.get("motion_version_registered", False):
                try:
                    _register_accepted_candidate(
                        plan=plan,
                        output_motion=output_motion,
                        motion_version_id=job.motion_version_id,
                        acceptance=dict(record["acceptance"]),
                        build_canonical=config.build_canonical,
                    )
                except Exception as exc:
                    errors = [*list(record.get("errors") or []), str(exc)]
                    queue.update(job.job_id, status="failed", errors=errors)
                    failed += 1
                    emit(f"registration failed {output_motion}: {exc}")
                    if not config.continue_on_error:
                        raise
                    continue
                queue.update(job.job_id, status="accepted", motion_version_registered=True)
            skipped += 1
            accepted += 1
            emit(f"skip accepted {output_motion}")
            continue

        if config.dry_run:
            _run_one_generation_attempt(
                config=config,
                job=job,
                plan=plan,
                plan_path=plan_path,
                output_motion=output_motion,
                overwrite=False,
                dry_run=True,
            )
            queue.update(job.job_id, status="dry_run")
            emit(f"dry-run {plan_path} -> {output_motion}")
            continue

        if output_motion.is_file() and not config.overwrite:
            try:
                report = _accept_candidate(
                    config=config,
                    plan=plan,
                    job=job,
                    output_motion=output_motion,
                )
            except Exception as exc:
                queue.update(job.job_id, status="failed", errors=[str(exc)])
                failed += 1
                emit(f"registration failed {output_motion}: {exc}")
                if not config.continue_on_error:
                    raise
                continue
            if report.passed:
                queue.update(
                    job.job_id,
                    status="accepted",
                    acceptance=report.to_dict(),
                    resumed_existing=True,
                    motion_version_registered=config.register_motion_version,
                )
                accepted += 1
                emit(f"accepted existing {output_motion}")
                continue
            message = "; ".join(report.errors)
            queue.update(job.job_id, status="failed", acceptance=report.to_dict(), errors=[message])
            failed += 1
            emit(f"failed existing {output_motion}: {message}; use --overwrite to regenerate")
            if not config.continue_on_error:
                raise ValueError(message)
            continue

        errors = list(record.get("errors") or [])
        attempts = int(record.get("attempts", 0))
        if attempts >= config.max_attempts:
            skipped += 1
            failed += 1
            emit(f"skip exhausted {plan_path}: attempts={attempts}/{config.max_attempts}")
            if not config.continue_on_error:
                raise RuntimeError(f"{plan.plan_id}: retry budget exhausted")
            continue

        result = None
        while attempts < config.max_attempts:
            attempts += 1
            queue.update(job.job_id, status="running", attempts=attempts, errors=errors)
            try:
                result = _run_one_generation_attempt(
                    config=config,
                    job=job,
                    plan=plan,
                    plan_path=plan_path,
                    output_motion=output_motion,
                    overwrite=config.overwrite or attempts > 1,
                    dry_run=False,
                )
                generated += 1
                break
            except Exception as exc:
                errors.append(str(exc))
                next_status = "retrying" if attempts < config.max_attempts else "failed"
                queue.update(job.job_id, status=next_status, attempts=attempts, errors=errors)
                emit(f"{next_status} {plan_path}: {exc}")
        if result is None:
            failed += 1
            if not config.continue_on_error:
                raise RuntimeError(f"{plan.plan_id}: generation failed after {attempts} attempt(s)")
            continue

        try:
            report = _accept_candidate(
                config=config,
                plan=plan,
                job=job,
                output_motion=result.output_motion_path,
            )
        except Exception as exc:
            errors.append(str(exc))
            queue.update(job.job_id, status="failed", attempts=attempts, errors=errors)
            failed += 1
            emit(f"registration failed {result.output_motion_path}: {exc}")
            if not config.continue_on_error:
                raise
            continue
        if not report.passed:
            errors.extend(report.errors)
            queue.update(job.job_id, status="failed", attempts=attempts, errors=errors, acceptance=report.to_dict())
            failed += 1
            emit(f"rejected {result.output_motion_path}: {'; '.join(report.errors)}")
            if not config.continue_on_error:
                raise ValueError("; ".join(report.errors))
            continue
        queue.update(
            job.job_id,
            status="accepted",
            attempts=attempts,
            errors=errors,
            acceptance=report.to_dict(),
            motion_version_registered=config.register_motion_version,
        )
        accepted += 1
        emit(f"accepted {result.output_motion_path}")

    queue.write_accepted_manifest()
    summary = AugmentationRunSummary(
        total=len(jobs),
        generated=generated,
        accepted=accepted,
        skipped=skipped,
        failed=failed,
        state_path=str(queue.state_path),
        accepted_manifest_path=str(queue.accepted_manifest_path),
    )
    emit(
        f"augmentation queue total={summary.total} generated={summary.generated} accepted={summary.accepted} "
        f"skipped={summary.skipped} failed={summary.failed} manifest={summary.accepted_manifest_path}"
    )
    return summary


__all__ = [
    "ACCEPTED_MANIFEST_SCHEMA",
    "QUEUE_SCHEMA",
    "AugmentationAcceptanceReport",
    "AugmentationQueue",
    "AugmentationQueueJob",
    "AugmentationRunConfig",
    "AugmentationRunSummary",
    "run_augmentation_queue",
    "validate_generated_augmentation",
]
