from __future__ import annotations

from motion_edit.generation.contact_aware_preview import generate_contact_aware_pyroki_preview
from motion_edit.generation.omni_generation_defaults import OMNI_GENERATION_DEFAULTS


def test_contact_aware_preview_enables_omni_graph_by_default() -> None:
    defaults = generate_contact_aware_pyroki_preview.__kwdefaults__ or {}

    for name, expected in OMNI_GENERATION_DEFAULTS.items():
        assert defaults[name] == expected

    assert defaults["mesh_laplacian_weight"] > 0.0
    assert defaults["q_smooth_weight"] == 0.0
