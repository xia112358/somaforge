"""Compile authored edits using the unchanged, verified source contact evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from motion_edit.contact.layers import read_verified_contact_graph
from motion_edit.contact.schema import ContactAnchorEditRecord


def editor_generation_metadata(
    *, motion_path: str, motion_id: str, contact_layer: str, terrain_mesh: str,
    edits: Iterable[ContactAnchorEditRecord], layers_root: Path,
) -> dict:
    terrain = Path(terrain_mesh).expanduser().resolve()
    if not terrain.is_file():
        raise FileNotFoundError(f"Generation terrain is missing: {terrain}")
    layer = layers_root / contact_layer
    labels = layer / "contact_labels" / f"{motion_id}.npz"
    graph = read_verified_contact_graph(
        layer, motion_id, motion_path=motion_path, labels_path=labels,
    )
    anchors = {anchor.anchor_id: anchor for anchor in graph.anchors}
    offsets = {key: {"base": [0.0, 0.0, 0.0], "windows": []} for key in anchors}
    for edit in edits:
        if edit.anchor_id not in anchors:
            raise ValueError(f"Edited anchor is not in the verified source: {edit.anchor_id}")
        anchor = anchors[edit.anchor_id]
        frames = edit.affected_frames or [anchor.start_frame, anchor.end_frame]
        if not anchor.start_frame <= frames[0] < frames[1] <= anchor.end_frame:
            raise ValueError(f"Edit window exceeds source contact episode: {edit.anchor_id}")
        if edit.surface_id != anchor.surface_id:
            raise ValueError("Editor translations must retain their verified source surface")
        if edit.delta_world is None:
            raise ValueError(f"Edit has no authored displacement: {edit.edit_id}")
        offsets[edit.anchor_id]["windows"].append({"frames": frames, "delta": edit.delta_world})
    return {
        "augmentation_objective": "consolidated_v1",
        "free_surface_contacts": True,
        "convex_surface_targets": True,
        "source_terrain_mesh": str(terrain),
        "target_terrain_mesh": str(terrain),
        "newton_contact_file": str(labels.resolve()),
        "free_surface_reference_offsets": offsets,
    }
