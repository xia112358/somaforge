from __future__ import annotations

from motion_edit.generation.lte_fullbody import CONTACT_BODY_LINK_CANDIDATES


WBT_CONTACT_BODY_TO_LTE_SEMANTIC: dict[str, str] = {
    "left_heel": "left_foot",
    "left_toe": "left_foot",
    "right_heel": "right_foot",
    "right_toe": "right_foot",
    "lhee": "left_foot",
    "ltoe": "left_foot",
    "rhee": "right_foot",
    "rtoe": "right_foot",
}


def install_lte_contact_semantic_aliases() -> None:
    """Register physical WBT contact parts as aliases of LTE semantic endpoints.

    Contact plans retain their physical part identity (for example ``right_toe``)
    for force lookup and Newton patch binding.  The body-position Laplacian only
    exposes one semantic point per foot, so heel/toe handles must resolve to that
    foot endpoint without rewriting the plan or contact graph.
    """

    for body, semantic in WBT_CONTACT_BODY_TO_LTE_SEMANTIC.items():
        existing = tuple(CONTACT_BODY_LINK_CANDIDATES.get(body, ()))
        CONTACT_BODY_LINK_CANDIDATES[body] = (
            semantic,
            *(candidate for candidate in existing if candidate != semantic),
        )
