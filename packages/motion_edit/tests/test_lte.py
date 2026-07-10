from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from motion_edit.adapters import lte
from motion_edit.layers import read_layer


class LteContactImportTests(unittest.TestCase):
    def test_old_lte_catalog_stays_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "sample_old.npz"
            np.savez(motion, qpos=np.zeros((3, 2)))
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps({"samples": [{"sample": "sample_old", "fullbody_ik_motion": str(motion)}]}),
                encoding="utf-8",
            )
            with (
                mock.patch.object(lte, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(lte, "layer_dir", lambda _status, name: root / "layers" / "candidates" / name),
            ):
                motions, segments = lte.import_lte_catalog(catalog, layer_name="lte_old")

            imported = read_layer(root / "layers" / "candidates" / "lte_old" / "full_motion.jsonl", default_source="lte", default_status="candidate")

        self.assertEqual((motions, segments), (1, 1))
        self.assertEqual(imported[0].metadata.get("contact_lte"), None)

    def test_contact_aware_lte_catalog_stores_anchor_edit_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "sample_contact.npz"
            np.savez(motion, qpos=np.zeros((5, 2)))
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "samples": [
                            {
                                "sample": "sample_contact",
                                "fullbody_ik_motion": str(motion),
                                "source_anchor_id": "anchor_old",
                                "target_anchor_id": "anchor_new",
                                "old_anchor_world": [0.0, 0.0, 0.0],
                                "new_anchor_world": [0.2, 0.0, 0.0],
                                "affected_frames": [1, 4],
                                "body": "LF",
                                "patch_id": "patch_lf",
                                "contact_edits": [{"kind": "move_anchor"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(lte, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(lte, "layer_dir", lambda _status, name: root / "layers" / "candidates" / name),
            ):
                lte.import_lte_catalog(catalog, layer_name="lte_contact")

            imported = read_layer(
                root / "layers" / "candidates" / "lte_contact" / "full_motion.jsonl",
                default_source="lte",
                default_status="candidate",
            )
            edits = json.loads((root / "catalogs" / "lte" / "lte_contact" / "edits.jsonl").read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(imported[0].metadata["contact_lte"]["kind"], "contact_lte")
        self.assertEqual(imported[0].metadata["source_anchor_id"], "anchor_old")
        self.assertEqual(imported[0].metadata["target_anchor_id"], "anchor_new")
        self.assertEqual(imported[0].metadata["active_body"], "LF")
        self.assertEqual(imported[0].metadata["contact_anchor_edit"]["edit_type"], "move_contact_anchor")
        self.assertEqual(imported[0].metadata["contact_anchor_edit"]["old_world_position"], [0.0, 0.0, 0.0])
        self.assertEqual(imported[0].metadata["contact_anchor_edit"]["new_world_position"], [0.2, 0.0, 0.0])
        self.assertEqual(imported[0].metadata["contact_anchor_edit"]["delta_world"], [0.2, 0.0, 0.0])
        self.assertEqual(imported[0].metadata["contact_anchor_edit"]["affected_frames"], [1, 4])
        self.assertEqual(imported[0].metadata["contact_lte"]["anchor_edit"]["edit_type"], "move_contact_anchor")
        self.assertEqual(edits["kind"], "contact_lte")


if __name__ == "__main__":
    unittest.main()
