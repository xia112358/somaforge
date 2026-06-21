from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from motion_edit import paths
from motion_edit.schema import SegmentRecord
from motion_edit.storage import (
    MotionVersionRecord,
    TokenRecord,
    read_canonical_segments,
    read_motion_version,
    read_token_catalog,
    write_canonical_segments,
    write_motion_version,
    write_token_catalog,
)


class StorageSchemaTests(unittest.TestCase):
    def test_motion_version_record_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "versions" / "climb00_raw.json"
            record = MotionVersionRecord(
                motion_version_id="climb00_raw",
                base_motion_id="climb00",
                kind="raw",
                motion_path="/motions/climb00.npz",
                contact_layer="contact/force_contact",
                canonical_segment_path="data/segments/climb00_raw.jsonl",
            )
            write_motion_version(record, path)
            loaded = read_motion_version("climb00_raw", path)

        self.assertEqual(loaded.motion_version_id, "climb00_raw")
        self.assertEqual(loaded.motion_path, "/motions/climb00.npz")
        self.assertEqual(loaded.contact_layer, "contact/force_contact")

    def test_canonical_segments_write_read_adds_motion_version_id(self) -> None:
        segment = SegmentRecord(
            motion_id="climb00",
            segment_id="seg_0",
            start_frame=1,
            end_frame=5,
            source="force_contact",
            motion_path="/motions/climb00.npz",
            metadata={"cut_source": "contact_auto"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "segments" / "climb00_raw.jsonl"
            written = write_canonical_segments("climb00_raw", [segment], path)
            loaded = read_canonical_segments("climb00_raw", path)

        self.assertEqual(written.name, "climb00_raw.jsonl")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].segment_id, "seg_0")
        self.assertEqual(loaded[0].metadata["motion_version_id"], "climb00_raw")

    def test_token_catalog_references_segments_without_motion_arrays(self) -> None:
        token = TokenRecord(
            token_id="tok_0",
            motion_version_id="climb00_raw",
            segment_id="seg_0",
            token_family="LF_to_RF_support_transfer",
            active_body="LF",
            support_bodies=["RF"],
            continuous_params={"duration": 4},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokens" / "climb00_raw.jsonl"
            write_token_catalog("climb00_raw", [token], path)
            loaded = read_token_catalog("climb00_raw", path)

        self.assertEqual(loaded[0].motion_version_id, "climb00_raw")
        self.assertEqual(loaded[0].segment_id, "seg_0")
        self.assertNotIn("qpos", loaded[0].metadata)
        self.assertNotIn("motion", loaded[0].continuous_params)

    def test_ensure_data_dirs_includes_canonical_storage_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(paths, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(paths, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(paths, "MOTIONS_ROOT", root / "motions"),
                mock.patch.object(paths, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(paths, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(paths, "TOKENS_ROOT", root / "tokens"),
                mock.patch.object(paths, "EXPORTS_ROOT", root / "exports"),
                mock.patch.object(paths, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(paths, "BACKUPS_ROOT", root / "backups"),
            ):
                paths.ensure_data_dirs()

            self.assertTrue((root / "motions" / "raw").is_dir())
            self.assertTrue((root / "motions" / "generated").is_dir())
            self.assertTrue((root / "motion_versions").is_dir())
            self.assertTrue((root / "segments").is_dir())
            self.assertTrue((root / "tokens").is_dir())
            self.assertTrue((root / "exports" / "split_npz").is_dir())


if __name__ == "__main__":
    unittest.main()
