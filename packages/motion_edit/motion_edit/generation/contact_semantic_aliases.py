from __future__ import annotations

from motion_edit.generation.lte_fullbody import CONTACT_BODY_LINK_CANDIDATES


# WBT contact-part identities remain physical (heel/toe), while the semantic
# body graph uses the two-point OmniRetarget foot model: ankle + toe.
WBT_CONTACT_BODY_TO_LTE_SEMANTIC: dict[str, str] = {
    "left_heel": "left_ankle",
    "left_toe": "left_foot",
    "right_heel": "right_ankle",
    "right_toe": "right_foot",
    "lhee": "left_ankle",
    "ltoe": "left_foot",
    "rhee": "right_ankle",
    "rtoe": "right_foot",
}

# Sparse/legacy proxy files may not expose explicit ankle points. Keep foot as
# a final fallback without changing the full graph's ankle-first resolution.
_WBT_CONTACT_BODY_FALLBACKS: dict[str, tuple[str, ...]] = {
    "left_heel": ("left_ankle", "left_foot"),
    "left_toe": ("left_foot",),
    "right_heel": ("right_ankle", "right_foot"),
    "right_toe": ("right_foot",),
    "lhee": ("left_ankle", "left_foot"),
    "ltoe": ("left_foot",),
    "rhee": ("right_ankle", "right_foot"),
    "rtoe": ("right_foot",),
}


def install_lte_contact_semantic_aliases() -> None:
    """Map physical heel/toe parts onto ankle/toe semantic trajectories.

    Contact plans and Newton patches keep their original physical identity and
    raw shape IDs. Only the first-stage semantic handle is resolved here:
    heel -> ankle and toe -> foot/toe.
    """

    for body, semantic in WBT_CONTACT_BODY_TO_LTE_SEMANTIC.items():
        existing = tuple(CONTACT_BODY_LINK_CANDIDATES.get(body, ()))
        preferred = _WBT_CONTACT_BODY_FALLBACKS.get(body, (semantic,))
        CONTACT_BODY_LINK_CANDIDATES[body] = (
            *preferred,
            *(candidate for candidate in existing if candidate not in preferred),
        )
