from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact import ContactSurfaceRecord, contact_graph_from_masks, read_contact_graph, write_contact_layer, write_contact_surfaces
from motion_edit.workbench.contact_editor_setup import ContactEditorConfig, prepare_contact_editor_session


class ContactEditorStableTransitionTests(unittest.TestCase):
    def test_contact_editor_ready_layer_rebuilds_stable_proto_transitions_from_cleaned_points(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            # Deliberately do not provide force-contact masks. The editor cuts
            # should be derived from the cleaned ContactAnchorRecords instead of
            # reparsing raw force from the motion file.
            np.savez(motion, dummy=np.asarray([1], dtype=np.int64))
            contact_mask = np.zeros((12, 1), dtype=bool)
            contact_mask[0:3, 0] = True
            contact_mask[7:10, 0] = True
            source_graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=contact_mask,
                body_pos_w=np.zeros((12, 1, 3), dtype=float),
                body_names=["left_foot"],
            )
            write_contact_layer(root / "layers" / "contact" / "source", source_graph)
            surface = ContactSurfaceRecord(
                motion_id="motion_a",
                surface_id="terrain_ground_z0",
                object_id="terrain_ground",
                surface_type="plane",
                origin=[0.0, 0.0, 0.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            )
            surface_catalog = root / "surfaces.jsonl"
            write_contact_surfaces(surface_catalog, [surface])

            prepared = prepare_contact_editor_session(
                ContactEditorConfig(
                    motion=str(motion),
                    motion_id="motion_a",
                    source_contact_layer="contact/source",
                    surface_catalog=str(surface_catalog),
                    session_name="contact_editor",
                    output_prefix="contact/editor",
                    max_surface_distance=0.08,
                ),
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            ready = read_contact_graph(root / "layers" / prepared.ready_layer, "motion_a")

        self.assertEqual(len(ready.transitions), 1)
        transition = ready.transitions[0]
        self.assertEqual((transition.start_frame, transition.end_frame), (0, 7))
        self.assertEqual(transition.metadata["segmentation_kind"], "stable_contact_anchor")
        self.assertEqual(transition.metadata["contact_source"], "cleaned_contact_points")
        self.assertEqual(transition.source, "contact_editor_anchor_proto")


if __name__ == "__main__":
    unittest.main()
