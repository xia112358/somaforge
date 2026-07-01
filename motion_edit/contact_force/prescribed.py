from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from .schema import (
    CanonicalContactForceField,
    ContactForceSample,
    PrescribedContactSolveConfig,
)


_PARENT_ALIASES: dict[str, tuple[str, ...]] = {
    "left_foot": ("left_foot", "lf", "left_ankle", "left_toe", "left_heel", "left_sole"),
    "right_foot": ("right_foot", "rf", "right_ankle", "right_toe", "right_heel", "right_sole"),
    "left_hand": ("left_hand", "lh", "left_wrist", "left_palm", "left_thumb", "left_pinky"),
    "right_hand": ("right_hand", "rh", "right_wrist", "right_palm", "right_thumb", "right_pinky"),
    "left_knee": ("left_knee", "lk"),
    "right_knee": ("right_knee", "rk"),
}


class PrescribedContactBackend(Protocol):
    """Backend interface for prescribed-state contact force queries."""

    def solve_frame(
        self,
        *,
        frame_index: int,
        qpos: np.ndarray,
        qvel: np.ndarray | None,
        qacc: np.ndarray | None,
        config: PrescribedContactSolveConfig,
    ) -> list[ContactForceSample]:
        ...


def solve_prescribed_contact_forces(
    qpos_ref: np.ndarray,
    backend: PrescribedContactBackend,
    config: PrescribedContactSolveConfig | None = None,
    *,
    qvel_ref: np.ndarray | None = None,
    qacc_ref: np.ndarray | None = None,
    contact_mask: np.ndarray | None = None,
    contact_part_position_w: np.ndarray | None = None,
) -> CanonicalContactForceField:
    """Bake part-level contact forces from prescribed reference states.

    The state sequence is never integrated by this wrapper. For each frame, the
    backend receives the prescribed qpos/qvel/qacc, computes contacts for that
    frame, and returns force samples. Samples are aggregated into canonical
    parent-limb force channels.
    """

    cfg = config or PrescribedContactSolveConfig()
    qpos = np.asarray(qpos_ref, dtype=np.float64)
    if qpos.ndim != 2:
        raise ValueError(f"qpos_ref must have shape [T, nq], got {qpos.shape}")
    n_frames = qpos.shape[0]
    qvel = _optional_frame_array(qvel_ref, n_frames=n_frames, name="qvel_ref")
    qacc = _optional_frame_array(qacc_ref, n_frames=n_frames, name="qacc_ref")
    part_order = tuple(str(part) for part in cfg.part_order)
    n_parts = len(part_order)
    intended_mask = _optional_mask(contact_mask, n_frames=n_frames, n_parts=n_parts)
    position_prior = _optional_position(contact_part_position_w, n_frames=n_frames, n_parts=n_parts)

    force_w = np.zeros((n_frames, n_parts, 3), dtype=np.float64)
    position_w = (
        position_prior.copy()
        if position_prior is not None
        else np.full((n_frames, n_parts, 3), np.nan, dtype=np.float64)
    )
    position_weight = np.zeros((n_frames, n_parts), dtype=np.float64)
    observed_mask = np.zeros((n_frames, n_parts), dtype=bool)
    unknown_samples = 0
    skipped_by_intended_mask = 0
    sample_count = 0

    for frame in range(n_frames):
        samples = backend.solve_frame(
            frame_index=frame,
            qpos=qpos[frame],
            qvel=None if qvel is None else qvel[frame],
            qacc=None if qacc is None else qacc[frame],
            config=cfg,
        )
        for sample in samples:
            sample.validate()
            part_index = _assign_sample_to_part(
                sample,
                frame=frame,
                part_order=part_order,
                position_prior=position_prior,
                max_distance=float(cfg.assignment_max_distance),
            )
            if part_index is None:
                unknown_samples += 1
                continue
            if intended_mask is not None and cfg.zero_inactive_contacts and not bool(intended_mask[frame, part_index]):
                skipped_by_intended_mask += 1
                continue
            force = np.asarray(sample.force_w, dtype=np.float64) * float(cfg.force_unit_scale)
            position = np.asarray(sample.position_w, dtype=np.float64)
            force_w[frame, part_index] += force
            weight = max(float(np.linalg.norm(force)), float(cfg.force_norm_eps))
            if not np.all(np.isfinite(position_w[frame, part_index])):
                position_w[frame, part_index] = 0.0
            position_w[frame, part_index] += position * weight
            position_weight[frame, part_index] += weight
            observed_mask[frame, part_index] = True
            sample_count += 1

    weighted = position_weight > 0.0
    position_w[weighted] = position_w[weighted] / position_weight[weighted, None]
    if position_prior is not None:
        position_w[~weighted] = position_prior[~weighted]
    mask = intended_mask.copy() if intended_mask is not None else observed_mask
    if cfg.zero_inactive_contacts and intended_mask is not None:
        force_w[~intended_mask] = 0.0
    if position_prior is None:
        # Keep inactive positions finite for downstream npz consumers without
        # inventing active contact points.
        inactive = ~mask
        position_w[inactive] = 0.0
    missing_intended = int(np.count_nonzero(mask & ~observed_mask)) if intended_mask is not None else 0
    force_norm = np.linalg.norm(force_w, axis=2)
    metadata = {
        "force_source": "prescribed_motion_contact_solve",
        "state_policy": "prescribed_qpos_qvel_qacc",
        "force_applied_to_body": False,
        "integrated": False,
        "solve_mode": cfg.solve_mode,
        "part_order": list(part_order),
        "sample_count": int(sample_count),
        "unknown_sample_count": int(unknown_samples),
        "skipped_by_intended_mask_count": int(skipped_by_intended_mask),
        "missing_intended_contact_frames": int(missing_intended),
        "force_norm_max": float(np.max(force_norm)) if force_norm.size else 0.0,
        "force_norm_mean_active": float(np.mean(force_norm[mask])) if np.any(mask) else 0.0,
        **dict(cfg.metadata),
    }
    field = CanonicalContactForceField(
        part_order=part_order,
        force_w=force_w,
        position_w=position_w,
        mask=mask,
        metadata=metadata,
    )
    field.validate()
    return field


@dataclass
class MuJoCoPrescribedContactBackend:
    """MuJoCo backend for prescribed-state contact-force baking.

    The backend overwrites ``mjData`` with the provided state at every frame and
    calls ``mj_forward`` or ``mj_inverse``. It does not call ``mj_step`` and does
    not let contact forces advance the trajectory.
    """

    model_path: str | Path
    geom_part_map: dict[str, str] = field(default_factory=dict)
    body_part_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            import mujoco  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised only without optional dependency.
            raise ImportError("MuJoCoPrescribedContactBackend requires the optional 'mujoco' package") from exc
        self._mujoco = mujoco
        self.model = mujoco.MjModel.from_xml_path(str(Path(self.model_path).expanduser()))
        self.data = mujoco.MjData(self.model)

    def solve_frame(
        self,
        *,
        frame_index: int,
        qpos: np.ndarray,
        qvel: np.ndarray | None,
        qacc: np.ndarray | None,
        config: PrescribedContactSolveConfig,
    ) -> list[ContactForceSample]:
        mujoco = self._mujoco
        qpos_arr = np.asarray(qpos, dtype=np.float64)
        if qpos_arr.shape != (self.model.nq,):
            raise ValueError(f"qpos has shape {qpos_arr.shape}; MuJoCo model expects {(self.model.nq,)}")
        self.data.qpos[:] = qpos_arr
        if qvel is not None:
            qvel_arr = np.asarray(qvel, dtype=np.float64)
            if qvel_arr.shape != (self.model.nv,):
                raise ValueError(f"qvel has shape {qvel_arr.shape}; MuJoCo model expects {(self.model.nv,)}")
            self.data.qvel[:] = qvel_arr
        else:
            self.data.qvel[:] = 0.0
        if config.solve_mode == "inverse":
            if qacc is None:
                raise ValueError("solve_mode='inverse' requires qacc_ref")
            qacc_arr = np.asarray(qacc, dtype=np.float64)
            if qacc_arr.shape != (self.model.nv,):
                raise ValueError(f"qacc has shape {qacc_arr.shape}; MuJoCo model expects {(self.model.nv,)}")
            self.data.qacc[:] = qacc_arr
            mujoco.mj_inverse(self.model, self.data)
        else:
            mujoco.mj_forward(self.model, self.data)
        samples: list[ContactForceSample] = []
        for contact_index in range(int(self.data.ncon)):
            contact = self.data.contact[contact_index]
            force_contact = np.zeros(6, dtype=np.float64)
            mujoco.mj_contactForce(self.model, self.data, contact_index, force_contact)
            frame = np.asarray(contact.frame, dtype=np.float64).reshape(3, 3)
            # MuJoCo stores contact-frame axes in world coordinates. The force
            # returned by mj_contactForce is expressed in that contact frame.
            force_w = frame.T @ force_contact[:3]
            geom1_name = self._geom_name(int(contact.geom1))
            geom2_name = self._geom_name(int(contact.geom2))
            body1_name = self._body_name_from_geom(int(contact.geom1))
            body2_name = self._body_name_from_geom(int(contact.geom2))
            samples.append(
                ContactForceSample(
                    frame_index=int(frame_index),
                    position_w=np.asarray(contact.pos, dtype=np.float64).copy(),
                    force_w=force_w,
                    part_hint=_part_from_names(
                        (geom1_name, geom2_name, body1_name, body2_name),
                        geom_part_map=self.geom_part_map,
                        body_part_map=self.body_part_map,
                    ),
                    geom1_name=geom1_name,
                    geom2_name=geom2_name,
                    body1_name=body1_name,
                    body2_name=body2_name,
                    distance=float(contact.dist),
                    metadata={"contact_index": int(contact_index)},
                )
            )
        return samples

    def _geom_name(self, geom_id: int) -> str | None:
        if geom_id < 0:
            return None
        name = self._mujoco.mj_id2name(self.model, self._mujoco.mjtObj.mjOBJ_GEOM, geom_id)
        return str(name) if name is not None else None

    def _body_name_from_geom(self, geom_id: int) -> str | None:
        if geom_id < 0:
            return None
        body_id = int(self.model.geom_bodyid[geom_id])
        name = self._mujoco.mj_id2name(self.model, self._mujoco.mjtObj.mjOBJ_BODY, body_id)
        return str(name) if name is not None else None


def differentiate_mujoco_qpos_sequence(
    model_path: str | Path,
    qpos_ref: np.ndarray,
    *,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute qvel/qacc for a MuJoCo qpos sequence using mj_differentiatePos."""

    try:
        import mujoco  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without optional dependency.
        raise ImportError("differentiate_mujoco_qpos_sequence requires the optional 'mujoco' package") from exc
    if float(dt) <= 0.0 or not np.isfinite(float(dt)):
        raise ValueError("dt must be finite and positive")
    model = mujoco.MjModel.from_xml_path(str(Path(model_path).expanduser()))
    qpos = np.asarray(qpos_ref, dtype=np.float64)
    if qpos.ndim != 2 or qpos.shape[1] != int(model.nq):
        raise ValueError(f"qpos_ref must have shape [T, {model.nq}], got {qpos.shape}")
    qvel = np.zeros((qpos.shape[0], int(model.nv)), dtype=np.float64)
    for frame in range(max(0, qpos.shape[0] - 1)):
        mujoco.mj_differentiatePos(model, qvel[frame], float(dt), qpos[frame], qpos[frame + 1])
    if qpos.shape[0] > 1:
        qvel[-1] = qvel[-2]
    qacc = np.zeros_like(qvel)
    if qpos.shape[0] > 1:
        qacc[1:-1] = (qvel[2:] - qvel[:-2]) / (2.0 * float(dt))
        qacc[0] = (qvel[1] - qvel[0]) / float(dt)
        qacc[-1] = (qvel[-1] - qvel[-2]) / float(dt)
    return qvel, qacc


def _optional_frame_array(value: np.ndarray | None, *, n_frames: int, name: str) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != int(n_frames):
        raise ValueError(f"{name} must have shape [T, D] with T={n_frames}, got {arr.shape}")
    return arr


def _optional_mask(value: np.ndarray | None, *, n_frames: int, n_parts: int) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=bool)
    if arr.shape != (int(n_frames), int(n_parts)):
        raise ValueError(f"contact_mask must have shape {(n_frames, n_parts)}, got {arr.shape}")
    return arr


def _optional_position(value: np.ndarray | None, *, n_frames: int, n_parts: int) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (int(n_frames), int(n_parts), 3):
        raise ValueError(f"contact_part_position_w must have shape {(n_frames, n_parts, 3)}, got {arr.shape}")
    return arr


def _assign_sample_to_part(
    sample: ContactForceSample,
    *,
    frame: int,
    part_order: tuple[str, ...],
    position_prior: np.ndarray | None,
    max_distance: float,
) -> int | None:
    if sample.part_hint is not None:
        parent = _normalize_parent_part(sample.part_hint)
        if parent in part_order:
            return part_order.index(parent)
    parent = _part_from_names(
        (sample.geom1_name, sample.geom2_name, sample.body1_name, sample.body2_name),
        geom_part_map={},
        body_part_map={},
    )
    if parent in part_order:
        return part_order.index(parent)
    if position_prior is None:
        return None
    pos = np.asarray(sample.position_w, dtype=np.float64)
    candidates = position_prior[int(frame)]
    finite = np.all(np.isfinite(candidates), axis=1)
    if not bool(np.any(finite)):
        return None
    distances = np.full(len(part_order), np.inf, dtype=np.float64)
    distances[finite] = np.linalg.norm(candidates[finite] - pos[None, :], axis=1)
    index = int(np.argmin(distances))
    if float(distances[index]) > float(max_distance):
        return None
    return index


def _part_from_names(
    names: tuple[str | None, ...],
    *,
    geom_part_map: dict[str, str],
    body_part_map: dict[str, str],
) -> str | None:
    for name in names[:2]:
        if name and name in geom_part_map:
            return _normalize_parent_part(geom_part_map[name])
    for name in names[2:]:
        if name and name in body_part_map:
            return _normalize_parent_part(body_part_map[name])
    for name in names:
        if name is None:
            continue
        lowered = str(name).lower()
        for parent, aliases in _PARENT_ALIASES.items():
            if any(alias in lowered for alias in aliases):
                return parent
    return None


def _normalize_parent_part(part: str) -> str:
    lowered = str(part).lower()
    for parent, aliases in _PARENT_ALIASES.items():
        if lowered == parent or lowered in aliases or any(alias in lowered for alias in aliases):
            return parent
    return lowered
