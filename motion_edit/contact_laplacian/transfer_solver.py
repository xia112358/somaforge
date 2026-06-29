from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .kinematics import KinematicsProvider
from .schema import BatchContactLaplacianConfig, ContactHandleSpec, ContactLaplacianSolveResult, InteractionMeshSpec
from .solver import solve_batch_contact_laplacian


@dataclass(frozen=True)
class TransferWindowSpec:
    """Frame interval owned by one local contact-transfer solve.

    ``start_frame`` is inclusive and ``end_frame`` is exclusive. The wrapper is
    intentionally agnostic to how these windows were derived: callers may use
    stable-proto boundaries, editor cut frames, or hand-authored swing phases.
    """

    transfer_id: str
    start_frame: int
    end_frame: int
    metadata: dict[str, object] = field(default_factory=dict)

    def validate(self, *, n_frames: int | None = None) -> None:
        start = int(self.start_frame)
        end = int(self.end_frame)
        if start < 0:
            raise ValueError(f"{self.transfer_id}: start_frame must be nonnegative")
        if end <= start:
            raise ValueError(f"{self.transfer_id}: end_frame must be greater than start_frame")
        if n_frames is not None and end > int(n_frames):
            raise ValueError(f"{self.transfer_id}: end_frame={end} exceeds n_frames={n_frames}")


@dataclass(frozen=True)
class TransferLocalContactLaplacianConfig:
    """Policy for applying the batch solver to independent transfer windows."""

    batch_config: BatchContactLaplacianConfig = field(default_factory=BatchContactLaplacianConfig)
    boundary_pin_frames: int = 1
    solve_empty_windows: bool = False

    def __post_init__(self) -> None:
        if int(self.boundary_pin_frames) < 0:
            raise ValueError("boundary_pin_frames must be nonnegative")


def solve_transfer_local_contact_laplacian(
    q_init: np.ndarray,
    kinematics: KinematicsProvider,
    handles: list[ContactHandleSpec],
    semantic_points: list[str],
    transfer_windows: Sequence[TransferWindowSpec],
    config: TransferLocalContactLaplacianConfig | None = None,
    *,
    q_prior: np.ndarray | None = None,
    body_edges: Sequence[tuple[str, str]] | None = None,
    interaction_mesh: InteractionMeshSpec | None = None,
) -> ContactLaplacianSolveResult:
    """Solve independent contact deformation subproblems per transfer window.

    This is a locality wrapper around :func:`solve_batch_contact_laplacian`. It
    does not change the batch objective. Instead, it remaps each handle to the
    local frame coordinates of the transfer that owns it, solves only that slice,
    and writes the slice back. Frames outside affected transfer windows are left
    untouched, so a contact edit in one swing cannot be propagated through the
    entire motion by the temporal Laplacian.
    """

    cfg = config or TransferLocalContactLaplacianConfig()
    q = np.asarray(q_init, dtype=np.float64).copy()
    if q.ndim != 2:
        raise ValueError(f"q_init must have shape [T, nq], got {q.shape}")
    n_frames, nq = q.shape
    if int(kinematics.nq) != nq:
        raise ValueError(f"q_init has nq={nq}, but kinematics provider has nq={kinematics.nq}")
    prior = np.asarray(q_prior if q_prior is not None else q_init, dtype=np.float64)
    if prior.shape != q.shape:
        raise ValueError(f"q_prior must have shape {q.shape}, got {prior.shape}")
    for handle in handles:
        handle.validate()
    windows = sorted(transfer_windows, key=lambda window: (int(window.start_frame), int(window.end_frame), window.transfer_id))
    for window in windows:
        window.validate(n_frames=n_frames)

    warnings: list[str] = []
    window_metadata: list[dict[str, object]] = []
    for window in windows:
        start = int(window.start_frame)
        end = int(window.end_frame)
        local_handles = _slice_handles_for_window(handles, start=start, end=end)
        if not local_handles and not bool(cfg.solve_empty_windows):
            window_metadata.append(
                {
                    "transfer_id": window.transfer_id,
                    "start_frame": start,
                    "end_frame": end,
                    "handle_count": 0,
                    "solved": False,
                    "reason": "no_overlapping_contact_handles",
                }
            )
            continue

        local_mesh = _slice_interaction_mesh(interaction_mesh, start=start, end=end)
        before = q[start:end].copy()
        result = solve_batch_contact_laplacian(
            before,
            kinematics,
            local_handles,
            semantic_points,
            cfg.batch_config,
            q_prior=prior[start:end],
            body_edges=body_edges,
            interaction_mesh=local_mesh,
        )
        local_q = _pin_window_boundaries(
            np.asarray(result.q, dtype=np.float64),
            before,
            pin_frames=int(cfg.boundary_pin_frames),
        )
        q[start:end] = local_q
        warnings.extend(f"{window.transfer_id}: {warning}" for warning in result.warnings)
        deformation = local_q - before
        window_metadata.append(
            {
                "transfer_id": window.transfer_id,
                "start_frame": start,
                "end_frame": end,
                "handle_count": len(local_handles),
                "solved": True,
                "boundary_pin_frames": int(cfg.boundary_pin_frames),
                "deformation_norm": float(np.linalg.norm(deformation)),
                "deformation_max_frame_norm": float(np.max(np.linalg.norm(deformation, axis=1))) if len(deformation) else 0.0,
                "batch_metadata": result.metadata,
                "source_window_metadata": dict(window.metadata),
            }
        )

    deformation = q - np.asarray(q_init, dtype=np.float64)
    frame_deformation_norm = np.linalg.norm(deformation, axis=1) if len(deformation) else np.zeros(0, dtype=np.float64)
    metadata = {
        "solver": "transfer_local_contact_laplacian",
        "subsolver": "batch_contact_laplacian",
        "locality_policy": "independent_transfer_windows",
        "trajectory_shape": [int(n_frames), int(nq)],
        "window_count": len(windows),
        "solved_window_count": sum(1 for item in window_metadata if bool(item.get("solved"))),
        "handle_count": int(len(handles)),
        "boundary_pin_frames": int(cfg.boundary_pin_frames),
        "solve_empty_windows": bool(cfg.solve_empty_windows),
        "deformation_norm": float(np.linalg.norm(deformation)),
        "deformation_max_frame_norm": float(np.max(frame_deformation_norm)) if len(frame_deformation_norm) else 0.0,
        "windows": window_metadata,
    }
    return ContactLaplacianSolveResult(q=q, metadata=metadata, warnings=warnings)


def _slice_handles_for_window(handles: Sequence[ContactHandleSpec], *, start: int, end: int) -> list[ContactHandleSpec]:
    local: list[ContactHandleSpec] = []
    for handle in handles:
        frames = np.asarray(handle.frames, dtype=np.int64)
        mask = (frames >= int(start)) & (frames < int(end))
        if not bool(np.any(mask)):
            continue
        metadata = dict(handle.metadata)
        metadata.update(
            {
                "global_frames": frames[mask].astype(np.int64).tolist(),
                "transfer_window_start": int(start),
                "transfer_window_end": int(end),
            }
        )
        local.append(
            ContactHandleSpec(
                anchor_id=handle.anchor_id,
                body=handle.body,
                semantic_name=handle.semantic_name,
                frames=(frames[mask] - int(start)).astype(np.int64),
                target_xyz=np.asarray(handle.target_xyz, dtype=np.float64)[mask],
                kind=handle.kind,
                weight=float(handle.weight),
                surface_id=handle.surface_id,
                object_id=handle.object_id,
                metadata=metadata,
            )
        )
    return local


def _slice_interaction_mesh(mesh: InteractionMeshSpec | None, *, start: int, end: int) -> InteractionMeshSpec | None:
    if mesh is None:
        return None
    reference_robot_points = mesh.reference_robot_points
    if reference_robot_points is not None:
        ref_robot = np.asarray(reference_robot_points, dtype=np.float64)
        if ref_robot.ndim == 3:
            reference_robot_points = ref_robot[int(start) : int(end)]
    return InteractionMeshSpec(
        robot_points=mesh.robot_points,
        object_points=np.asarray(mesh.object_points, dtype=np.float64),
        edges=mesh.edges,
        knn_k=int(mesh.knn_k),
        reference_robot_points=reference_robot_points,
        reference_object_points=mesh.reference_object_points,
        metadata=dict(mesh.metadata),
    )


def _pin_window_boundaries(local_q: np.ndarray, reference: np.ndarray, *, pin_frames: int) -> np.ndarray:
    out = np.asarray(local_q, dtype=np.float64).copy()
    if int(pin_frames) <= 0 or out.size == 0:
        return out
    n = min(int(pin_frames), out.shape[0])
    out[:n] = reference[:n]
    out[-n:] = reference[-n:]
    return out
