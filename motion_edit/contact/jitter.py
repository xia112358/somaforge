from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Iterable

from motion_edit.contact.edits import move_contact_anchor_on_surface
from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact.plans import ContactEditPlan, validate_contact_edit_plan, write_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorRecord
from motion_edit.paths import LAYERS_ROOT


DEFAULT_JITTER_BODIES = ("left_foot", "right_foot", "left_hand", "right_hand")


@dataclass(frozen=True)
class ContactJitterPlanResult:
    plan_path: Path
    plan_id: str
    motion_id: str
    source_motion_path: str
    source_contact_layer: str
    edit_count: int
    attempted_anchor_count: int
    seed: int


def _load_cut_summary(path: str | Path) -> list[dict]:
    summary_path = Path(path).expanduser()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"cut summary must be a list: {summary_path}")
    return [item for item in payload if isinstance(item, dict) and item.get("status", "ok") == "ok"]


def _anchor_can_jitter(anchor: ContactAnchorRecord, bodies: set[str]) -> bool:
    return (
        anchor.editable
        and anchor.body in bodies
        and anchor.world_position is not None
        and anchor.surface_id is not None
        and anchor.surface_coordinates is not None
        and anchor.surface_normal is not None
        and anchor.surface_tangent_u is not None
        and anchor.surface_tangent_v is not None
    )


def _sample_disk(rng: random.Random, radius: float) -> tuple[float, float]:
    # Rejection sampling keeps the u/v metric isotropic because the stored tangent basis is orthonormal.
    while True:
        du = rng.uniform(-radius, radius)
        dv = rng.uniform(-radius, radius)
        if du * du + dv * dv <= radius * radius:
            return du, dv


def _iter_selected_anchors(
    anchors: Iterable[ContactAnchorRecord],
    *,
    rng: random.Random,
    bodies: set[str],
    edit_probability: float,
    max_edits: int,
) -> list[ContactAnchorRecord]:
    candidates = [anchor for anchor in anchors if _anchor_can_jitter(anchor, bodies)]
    rng.shuffle(candidates)
    selected = [anchor for anchor in candidates if rng.random() < edit_probability]
    if not selected and candidates:
        selected = [candidates[0]]
    if max_edits > 0:
        selected = selected[:max_edits]
    return selected


def _make_jitter_plan_for_motion(
    item: dict,
    *,
    augmentation_index: int,
    rng: random.Random,
    seed: int,
    output_dir: Path,
    offset_radius: float,
    edit_probability: float,
    max_edits: int,
    max_attempts: int,
    bodies: set[str],
    mode: str,
) -> ContactJitterPlanResult | None:
    motion_id = str(item.get("motion_id") or item.get("motion_asset_id") or "")
    motion_path = str(item.get("motion_path") or "")
    contact_layer = str(item.get("ready_layer") or "")
    if not motion_id or not motion_path or not contact_layer:
        return None

    graph = read_contact_graph(LAYERS_ROOT / contact_layer, motion_id)
    selected = _iter_selected_anchors(
        graph.anchors,
        rng=rng,
        bodies=bodies,
        edit_probability=edit_probability,
        max_edits=max_edits,
    )

    edits: list[dict] = []
    attempted = 0
    for anchor in selected:
        attempted += 1
        edit = None
        for _ in range(max_attempts):
            du, dv = _sample_disk(rng, offset_radius)
            try:
                _moved, edit_record = move_contact_anchor_on_surface(
                    anchor,
                    tangent_delta=(du, dv),
                    mode=mode,
                    source="random_surface_jitter",
                    edit_id=f"{anchor.anchor_id}_jitter_{augmentation_index:04d}",
                )
            except ValueError:
                continue
            edit = edit_record.to_dict()
            edit.setdefault("metadata", {})
            edit["metadata"].update(
                {
                    "augmentation_index": augmentation_index,
                    "augmentation_seed": seed,
                    "offset_radius": offset_radius,
                }
            )
            break
        if edit is not None:
            edits.append(edit)

    if not edits:
        return None

    stem = motion_id.replace("/", "_")
    plan_id = f"{stem}_surface_jitter_{augmentation_index:04d}"
    plan = ContactEditPlan(
        plan_id=plan_id,
        source_motion_path=motion_path,
        source_motion_id=motion_id,
        source_contact_layer=contact_layer,
        source_segment_layer=None,
        edits=edits,
        status="validated",
        output_motion_path=f"data/motions/generated/{plan_id}.npz",
        output_contact_layer=f"contact/{plan_id}",
        output_segment_layer=f"candidates/{plan_id}",
        metadata={
            "augmentation": "random_surface_jitter",
            "augmentation_index": augmentation_index,
            "augmentation_seed": seed,
            "offset_radius": offset_radius,
            "edit_probability": edit_probability,
            "max_edits": max_edits,
            "constraint_mode": mode,
            "source_cut_summary_motion_asset_id": item.get("motion_asset_id"),
        },
    )
    validate_contact_edit_plan(plan)
    plan_path = output_dir / f"{plan_id}.json"
    write_contact_edit_plan(plan_path, plan)
    return ContactJitterPlanResult(
        plan_path=plan_path,
        plan_id=plan_id,
        motion_id=motion_id,
        source_motion_path=motion_path,
        source_contact_layer=contact_layer,
        edit_count=len(edits),
        attempted_anchor_count=attempted,
        seed=seed,
    )


def generate_contact_jitter_plans(
    cut_summary: str | Path,
    output_dir: str | Path,
    *,
    augmentations_per_motion: int = 8,
    offset_radius: float = 0.05,
    edit_probability: float = 0.35,
    max_edits: int = 12,
    max_attempts: int = 32,
    seed: int = 0,
    bodies: Iterable[str] = DEFAULT_JITTER_BODIES,
    mode: str = "reject",
    limit_motions: int | None = None,
) -> tuple[list[ContactJitterPlanResult], dict[str, int | float | str]]:
    if augmentations_per_motion <= 0:
        raise ValueError("augmentations_per_motion must be positive")
    if offset_radius <= 0.0:
        raise ValueError("offset_radius must be positive")
    if not 0.0 < edit_probability <= 1.0:
        raise ValueError("edit_probability must be in (0, 1]")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    if mode not in {"reject", "clamp"}:
        raise ValueError("mode must be reject or clamp")

    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    body_set = {str(body) for body in bodies}
    items = _load_cut_summary(cut_summary)
    if limit_motions is not None:
        items = items[: max(0, int(limit_motions))]

    results: list[ContactJitterPlanResult] = []
    skipped_no_edits = 0
    for item in items:
        for aug_index in range(augmentations_per_motion):
            aug_seed = seed + len(results) + skipped_no_edits
            rng = random.Random(aug_seed)
            result = _make_jitter_plan_for_motion(
                item,
                augmentation_index=aug_index,
                rng=rng,
                seed=aug_seed,
                output_dir=out_dir,
                offset_radius=offset_radius,
                edit_probability=edit_probability,
                max_edits=max_edits,
                max_attempts=max_attempts,
                bodies=body_set,
                mode=mode,
            )
            if result is None:
                skipped_no_edits += 1
                continue
            results.append(result)

    manifest = {
        "kind": "motion_edit_contact_jitter_plan_manifest",
        "cut_summary": str(Path(cut_summary).expanduser()),
        "output_dir": str(out_dir),
        "augmentations_per_motion": augmentations_per_motion,
        "offset_radius": offset_radius,
        "edit_probability": edit_probability,
        "max_edits": max_edits,
        "max_attempts": max_attempts,
        "seed": seed,
        "bodies": sorted(body_set),
        "mode": mode,
        "source_motion_count": len(items),
        "plan_count": len(results),
        "skipped_no_edits": skipped_no_edits,
        "plans": [
            {
                "plan_path": str(result.plan_path),
                "plan_id": result.plan_id,
                "motion_id": result.motion_id,
                "source_motion_path": result.source_motion_path,
                "source_contact_layer": result.source_contact_layer,
                "edit_count": result.edit_count,
                "attempted_anchor_count": result.attempted_anchor_count,
                "seed": result.seed,
            }
            for result in results
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    stats: dict[str, int | float | str] = {
        "source_motion_count": len(items),
        "plan_count": len(results),
        "skipped_no_edits": skipped_no_edits,
        "offset_radius": offset_radius,
        "edit_probability": edit_probability,
        "mode": mode,
    }
    return results, stats
