from __future__ import annotations

from motion_edit.contact.schema import ContactAnchorRecord, ContactPatchRecord


def patches_from_anchors(anchors: list[ContactAnchorRecord]) -> list[ContactPatchRecord]:
    patches: list[ContactPatchRecord] = []
    for anchor in anchors:
        patch = ContactPatchRecord(
            motion_id=anchor.motion_id,
            patch_id=f"{anchor.anchor_id}_patch",
            body=anchor.body,
            start_frame=anchor.start_frame,
            end_frame=anchor.end_frame,
            anchor_id=anchor.anchor_id,
            metadata={"role": anchor.role, "source_anchor_id": anchor.anchor_id},
        )
        patch.validate()
        patches.append(patch)
    return sorted(patches, key=lambda patch: (patch.start_frame, patch.end_frame, patch.body, patch.patch_id))

