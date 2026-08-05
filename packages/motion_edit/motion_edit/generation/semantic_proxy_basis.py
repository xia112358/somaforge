"""Reuse a solved semantic deformation for proportional task variants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np


_OBJECTIVE_CONFIG_KEYS = (
    "damping",
    "edit_contact_weight",
    "fixed_contact_weight",
    "temporal_laplacian_weight",
    "body_relative_weight",
    "q_prior_weight",
    "q_smooth_weight",
    "mesh_laplacian_weight",
)


def reuse_proportional_semantic_proxy(
    *,
    basis_path: str | Path,
    source_motion: dict[str, Any],
    source_motion_path: str | Path,
    edits: Sequence[Any],
    config: Any,
) -> tuple[dict[str, Any], float, dict[str, Any]]:
    """Scale a converged proxy when every edit is proportional to its basis.

    The task-space solver is linear for the body-position provider and fixed
    source Delaunay topology. Fixed contacts contribute zero displacement, so
    scaling all edited-contact and surface displacements scales the complete
    deformation by the same factor.
    """

    path = Path(basis_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"semantic proxy basis is missing: {path}")
    with np.load(path, allow_pickle=True) as data:
        basis = {key: np.asarray(data[key]) for key in data.files}

    metadata = _json_object(basis.get("motion_edit_generation_metadata"))
    _validate_source(metadata, source_motion_path)
    _validate_config(metadata, config)
    scale = _proportional_edit_scale(metadata.get("edits"), edits)
    _validate_convergence(metadata)

    source_body_pos = np.asarray(source_motion["body_pos_w"], dtype=np.float64)
    basis_body_pos = np.asarray(basis["body_pos_w"], dtype=np.float64)
    if basis_body_pos.shape != source_body_pos.shape:
        raise ValueError(
            "semantic proxy basis body_pos_w shape differs from source motion: "
            f"{basis_body_pos.shape} != {source_body_pos.shape}"
        )

    output = dict(basis)
    output["body_pos_w"] = source_body_pos + scale * (
        basis_body_pos - source_body_pos
    )
    fps = float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    output["body_lin_vel_w"] = np.gradient(
        output["body_pos_w"],
        1.0 / fps,
        axis=0,
    )

    for key, value in tuple(basis.items()):
        if not key.startswith("offset_"):
            continue
        semantic_name = key.removeprefix("offset_")
        keypoint_key = f"keypoint_{semantic_name}"
        if keypoint_key not in basis:
            continue
        offset = scale * np.asarray(value, dtype=np.float64)
        source_keypoint = (
            np.asarray(basis[keypoint_key], dtype=np.float64)
            - np.asarray(value, dtype=np.float64)
        )
        output[key] = offset
        output[keypoint_key] = source_keypoint + offset

    current_edits = [_edit_dict(edit) for edit in edits]
    reuse_metadata = {
        **metadata,
        "source_plan": None,
        "source_plan_id": None,
        "edits": current_edits,
        "num_edits": len(current_edits),
        "semantic_proxy_reuse": {
            "active": True,
            "basis_path": str(path),
            "scale": float(scale),
            "contract": "proportional_linear_deformation",
        },
    }
    output["motion_edit_generation_metadata"] = np.asarray(
        json.dumps(reuse_metadata, sort_keys=True)
    )
    return output, float(scale), reuse_metadata


def _validate_source(metadata: dict[str, Any], source_motion_path: str | Path) -> None:
    cached = metadata.get("source_motion")
    if not cached:
        raise ValueError("semantic proxy basis has no source_motion metadata")
    cached_path = Path(str(cached)).expanduser().resolve()
    current_path = Path(source_motion_path).expanduser().resolve()
    if cached_path != current_path:
        raise ValueError(
            "semantic proxy basis uses a different source motion: "
            f"{cached_path} != {current_path}"
        )


def _validate_config(metadata: dict[str, Any], config: Any) -> None:
    cached = dict(metadata.get("contact_laplacian_config") or {})
    current = dict(config.__dict__)
    mismatches = {
        key: (cached.get(key), current.get(key))
        for key in _OBJECTIVE_CONFIG_KEYS
        if cached.get(key) != current.get(key)
    }
    if mismatches:
        raise ValueError(
            f"semantic proxy basis objective differs from current config: {mismatches}"
        )


def _validate_convergence(metadata: dict[str, Any]) -> None:
    iterations = list(
        (metadata.get("solver_metadata") or {}).get("iterations") or []
    )
    if not iterations:
        raise ValueError("semantic proxy basis has no solver convergence metadata")
    final = dict(iterations[-1])
    if not bool(final.get("accepted", False)):
        raise ValueError("semantic proxy basis final solver step was not accepted")
    if float(final.get("relative_improvement", np.inf)) > 1.0e-8:
        raise ValueError("semantic proxy basis did not converge sufficiently")


def _proportional_edit_scale(
    cached_edits_raw: Any,
    current_edits: Sequence[Any],
) -> float:
    cached = {
        str(item["anchor_id"]): dict(item)
        for item in list(cached_edits_raw or [])
    }
    current = {
        str(item["anchor_id"]): item
        for item in (_edit_dict(edit) for edit in current_edits)
    }
    if set(cached) != set(current):
        raise ValueError("semantic proxy basis anchor set differs from current plan")

    basis_vectors: list[np.ndarray] = []
    current_vectors: list[np.ndarray] = []
    for anchor_id in sorted(cached):
        first = cached[anchor_id]
        second = current[anchor_id]
        if list(first.get("affected_frames") or []) != list(
            second.get("affected_frames") or []
        ):
            raise ValueError(
                f"semantic proxy basis frames differ for anchor {anchor_id}"
            )
        basis_vectors.append(
            np.asarray(first.get("delta_world"), dtype=np.float64).reshape(3)
        )
        current_vectors.append(
            np.asarray(second.get("delta_world"), dtype=np.float64).reshape(3)
        )
    basis_vector = np.concatenate(basis_vectors)
    current_vector = np.concatenate(current_vectors)
    denominator = float(np.dot(basis_vector, basis_vector))
    if denominator <= 1.0e-16:
        raise ValueError("semantic proxy basis has no nonzero edit displacement")
    scale = float(np.dot(basis_vector, current_vector) / denominator)
    residual = current_vector - scale * basis_vector
    if float(np.max(np.abs(residual), initial=0.0)) > 1.0e-8:
        raise ValueError(
            "current edit displacements are not proportional to semantic proxy basis"
        )
    return scale


def _edit_dict(edit: Any) -> dict[str, Any]:
    return dict(edit.to_dict() if hasattr(edit, "to_dict") else edit)


def _json_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = value.item() if hasattr(value, "item") else value
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    result = json.loads(str(raw))
    if not isinstance(result, dict):
        raise ValueError("semantic proxy basis metadata must be a JSON object")
    return result
