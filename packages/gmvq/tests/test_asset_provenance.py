from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from gmvq.data import load_contact_force_provenance, load_robot_asset_metadata, load_segment_arrays
from somaforge_core.contact_schema import encode_contact_force_provenance, newton_contact_provenance
from somaforge_core.robot_assets import G1_SPHEREHAND_SHA256, encode_robot_asset_json


class AssetProvenanceTests(unittest.TestCase):
    def test_fingerprinted_segment_pack_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "segments.npz"
            np.savez(
                path,
                segments=np.zeros((2, 3, 4), dtype=np.float32),
                robot_asset_json=np.asarray(encode_robot_asset_json()),
                contact_force_provenance_json=np.asarray(
                    [
                        encode_contact_force_provenance(
                            newton_contact_provenance(solver_config={"nconmax": 64, "njmax": 512})
                        )
                    ]
                    * 2
                ),
            )
            arrays = load_segment_arrays(path)
            metadata = load_robot_asset_metadata(path)
            contact_metadata = load_contact_force_provenance(path)

        self.assertEqual(tuple(arrays["segments"].shape), (2, 3, 4))
        self.assertEqual(metadata["urdf_sha256"], G1_SPHEREHAND_SHA256)
        self.assertEqual(contact_metadata["source_backend"], "isaaclab3_newton_mjwarp")
        self.assertEqual(contact_metadata["segment_count"], 2)

    def test_legacy_segment_pack_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy_segments.npz"
            np.savez(path, segments=np.zeros((2, 3, 4), dtype=np.float32))
            with self.assertRaisesRegex(ValueError, "legacy wrong-URDF"):
                load_segment_arrays(path)

    def test_segment_pack_without_newton_contact_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "segments.npz"
            np.savez(
                path,
                segments=np.zeros((2, 3, 4), dtype=np.float32),
                robot_asset_json=np.asarray(encode_robot_asset_json()),
            )
            with self.assertRaisesRegex(ValueError, "contact_force_provenance_json"):
                load_contact_force_provenance(path)


if __name__ == "__main__":
    unittest.main()
