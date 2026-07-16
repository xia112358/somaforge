from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from somaforge_core import decode_contact_force_provenance, decode_robot_asset_json
from somaforge_core.contact_schema import CONTACT_FORCE_PART_ORDER, canonical_contact_part_id


@dataclass(frozen=True)
class NewtonForceTarget:
    force_w: np.ndarray
    mask: np.ndarray
    joint_pos: np.ndarray | None
    provenance: dict[str, object]


def load_newton_force_target(path: str | Path) -> NewtonForceTarget:
    """Load canonical 8-part target forces produced by a Newton rollout."""

    source = Path(path).expanduser().resolve()
    with np.load(source, allow_pickle=False) as data:
        decode_robot_asset_json(data.get("robot_asset_json"), context=f"force target {source}")
        provenance = decode_contact_force_provenance(
            data.get("contact_force_provenance_json"),
            context=f"force target {source}",
            require_newton=True,
        )
        if "contact_force_part_w" not in data or "contact_force_part_mask" not in data:
            raise KeyError(f"{source} is missing canonical 8-part force or mask")
        force = np.asarray(data["contact_force_part_w"], dtype=np.float64)
        mask = np.asarray(data["contact_force_part_mask"], dtype=bool)
        order = _part_order(data, force.shape[1] if force.ndim == 3 else -1, source)
        indices = [order.index(part) for part in CONTACT_FORCE_PART_ORDER]
        force = force[:, indices]
        mask = mask[:, indices]
        joint_pos = np.asarray(data["joint_pos"], dtype=np.float64) if "joint_pos" in data else None

    if force.ndim != 3 or force.shape[1:] != (len(CONTACT_FORCE_PART_ORDER), 3):
        raise ValueError(f"{source} force must have shape [T,8,3], got {force.shape}")
    if mask.shape != force.shape[:2]:
        raise ValueError(f"{source} mask must have shape {force.shape[:2]}, got {mask.shape}")
    if not np.all(np.isfinite(force)):
        raise ValueError(f"{source} force contains NaN or Inf")
    return NewtonForceTarget(
        force_w=force,
        mask=mask,
        joint_pos=joint_pos,
        provenance=dict(provenance),
    )


def _part_order(data: np.lib.npyio.NpzFile, width: int, source: Path) -> list[str]:
    if "contact_force_part_order" not in data:
        if width != len(CONTACT_FORCE_PART_ORDER):
            raise ValueError(f"{source} has {width} force parts and no contact_force_part_order")
        return list(CONTACT_FORCE_PART_ORDER)
    raw = np.asarray(data["contact_force_part_order"]).reshape(-1).tolist()
    order = [canonical_contact_part_id(str(item)) for item in raw]
    if len(order) != width or len(set(order)) != len(order):
        raise ValueError(f"{source} has an invalid contact_force_part_order")
    missing = [part for part in CONTACT_FORCE_PART_ORDER if part not in order]
    if missing:
        raise ValueError(f"{source} is missing canonical force parts: {missing}")
    return order
