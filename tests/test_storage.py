from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from motion_edit import cli, paths
from motion_edit.contact import contact_graph_from_masks, write_contact_layer
from motion_edit.io import write_jsonl
from motion_edit.layers import write_layer
from motion_edit.schema import SegmentRecord
from motion_edit.storage import io as storage_io
from motion_edit.storage import (
    MotionAssetRecord,
    MotionVersionRecord,
    TokenRecord,
    list_motion_assets,
    read_canonical_segments,
    read_motion_asset,
    read_motion_version,
    read_token_catalog,
    write_canonical_segments,
    write_motion_asset,
    write_motion_version,
    write_token_catalog,
)
from motion_edit.storage.tokens import build_tokens_from_segments


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

    def test_motion_asset_record_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets" / "climb00.json"
            record = MotionAssetRecord(
                motion_asset_id="climb00",
                motion_path="/motions/climb00.npz",
                source="local",
                fps=50.0,
            )
            write_motion_asset(record, path)
            loaded = read_motion_asset("climb00", path)
            listed = list_motion_assets(path.parent)

        self.assertEqual(loaded.motion_asset_id, "climb00")
        self.assertEqual(loaded.motion_path, "/motions/climb00.npz")
        self.assertEqual(loaded.fps, 50.0)
        self.assertEqual([item.motion_asset_id for item in listed], ["climb00"])

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

    def test_build_token_catalog_from_canonical_segments(self) -> None:
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="seg_0",
            start_frame=2,
            end_frame=8,
            source="canonical",
            status="accepted",
            metadata={
                "motion_version_id": "motion_a_raw",
                "active_body": "LF",
                "support_bodies": ["RF"],
                "transition_type": "support_transfer",
                "source_anchor_id": "anchor_src",
                "target_anchor_id": "anchor_dst",
                "parent_transition_id": "transition_0",
                "contact_anchor_edit": {"tangent_delta": [0.1, 0.0]},
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(storage_io, "TOKENS_ROOT", root / "tokens"),
            ):
                write_canonical_segments("motion_a_raw", [segment])
                cli._cmd_build_token_catalog(type("Args", (), {"motion_version_id": "motion_a_raw", "output": None})())
                tokens = read_token_catalog("motion_a_raw")

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].motion_version_id, "motion_a_raw")
        self.assertEqual(tokens[0].segment_id, "seg_0")
        self.assertEqual(tokens[0].token_family, "LF__RF__support_transfer")
        self.assertEqual(tokens[0].continuous_params["duration"], 6)
        self.assertEqual(tokens[0].continuous_params["tangent_delta"], [0.1, 0.0])
        self.assertNotIn("qpos", tokens[0].metadata)

    def test_build_tokens_from_segments_does_not_copy_motion_arrays(self) -> None:
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="seg_0",
            start_frame=0,
            end_frame=2,
            source="canonical",
            motion_path="/motions/motion_a.npz",
            metadata={"active_body": "LF", "support_bodies": ["RF"]},
        )

        tokens = build_tokens_from_segments("motion_a_raw", [segment])

        self.assertEqual(tokens[0].segment_id, "seg_0")
        self.assertNotIn("motion_path", tokens[0].to_dict())

    def test_ensure_data_dirs_includes_canonical_storage_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(paths, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(paths, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(paths, "MOTIONS_ROOT", root / "motions"),
                mock.patch.object(paths, "MOTION_ASSETS_ROOT", root / "motion_assets"),
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
            self.assertTrue((root / "motion_assets").is_dir())
            self.assertTrue((root / "motion_versions").is_dir())
            self.assertTrue((root / "segments").is_dir())
            self.assertTrue((root / "tokens").is_dir())
            self.assertTrue((root / "exports" / "split_npz").is_dir())

    def test_register_motion_asset_cli_writes_reference_without_copying_motion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"source-motion")
            with (
                mock.patch.object(paths, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(paths, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(paths, "MOTIONS_ROOT", root / "motions"),
                mock.patch.object(paths, "MOTION_ASSETS_ROOT", root / "motion_assets"),
                mock.patch.object(paths, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(paths, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(paths, "TOKENS_ROOT", root / "tokens"),
                mock.patch.object(paths, "EXPORTS_ROOT", root / "exports"),
                mock.patch.object(paths, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(paths, "BACKUPS_ROOT", root / "backups"),
                mock.patch.object(storage_io, "MOTION_ASSETS_ROOT", root / "motion_assets"),
            ):
                cli._cmd_register_motion_asset(
                    type(
                        "Args",
                        (),
                        {
                            "motion_asset_id": "motion_a",
                            "motion": str(motion),
                            "fps": 50.0,
                            "source": "local",
                        },
                    )()
                )
                loaded = read_motion_asset("motion_a")

            self.assertEqual(motion.read_bytes(), b"source-motion")
            self.assertFalse((root / "motions" / "raw" / "motion_a.npz").exists())

        self.assertEqual(loaded.motion_path, str(motion))
        self.assertEqual(loaded.source, "local")

    def test_build_canonical_segmentation_from_contact_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers_root = root / "layers"
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
                body_names=["LF", "RF"],
            )
            write_contact_layer(layers_root / "contact" / "force_contact", graph)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"npz")
            args = type(
                "Args",
                (),
                {
                    "motion_version_id": "motion_a_raw",
                    "motion": str(motion),
                    "motion_id": "motion_a",
                    "contact_layer": "contact/force_contact",
                    "source": None,
                    "cut_source": "contact_auto",
                },
            )()
            with (
                mock.patch.object(cli, "LAYERS_ROOT", layers_root),
                mock.patch.object(paths, "LAYERS_ROOT", layers_root),
                mock.patch.object(paths, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(paths, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(paths, "MOTIONS_ROOT", root / "motions"),
                mock.patch.object(paths, "TOKENS_ROOT", root / "tokens"),
                mock.patch.object(paths, "EXPORTS_ROOT", root / "exports"),
                mock.patch.object(paths, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(paths, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(paths, "BACKUPS_ROOT", root / "backups"),
                mock.patch.object(storage_io, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
            ):
                cli._cmd_build_canonical_segmentation(args)
                segments = read_canonical_segments("motion_a_raw")
                version = read_motion_version("motion_a_raw")

            self.assertEqual(version.motion_version_id, "motion_a_raw")
            self.assertEqual(version.contact_layer, "contact/force_contact")
            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0].metadata["motion_version_id"], "motion_a_raw")
            self.assertEqual(segments[0].metadata["cut_source"], "contact_auto")
            self.assertIn("parent_transition_id", segments[0].metadata)
            self.assertEqual(len(list((root / "segments").glob("motion_a_raw*.jsonl"))), 1)

    def test_migrate_layer_to_canonical_rebinds_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers_root = root / "layers"
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
                body_names=["LF", "RF"],
            )
            write_contact_layer(layers_root / "contact" / "force_contact", graph)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"npz")
            legacy = SegmentRecord(
                motion_id="motion_a",
                segment_id="legacy_seg",
                start_frame=0,
                end_frame=2,
                source="force_contact",
                motion_path=str(motion),
            )
            write_layer(layers_root / "candidates" / "force_contact" / "motion_a.jsonl", [legacy])
            args = type(
                "Args",
                (),
                {
                    "motion_version_id": "motion_a_raw",
                    "motion": str(motion),
                    "motion_id": "motion_a",
                    "contact_layer": "contact/force_contact",
                    "source": "candidates/force_contact",
                    "cut_source": "migrated",
                },
            )()
            with (
                mock.patch.object(cli, "LAYERS_ROOT", layers_root),
                mock.patch.object(paths, "LAYERS_ROOT", layers_root),
                mock.patch.object(paths, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(paths, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(paths, "MOTIONS_ROOT", root / "motions"),
                mock.patch.object(paths, "TOKENS_ROOT", root / "tokens"),
                mock.patch.object(paths, "EXPORTS_ROOT", root / "exports"),
                mock.patch.object(paths, "CATALOGS_ROOT", root / "catalogs"),
                mock.patch.object(paths, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(paths, "BACKUPS_ROOT", root / "backups"),
                mock.patch.object(storage_io, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
                mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
            ):
                cli._cmd_build_canonical_segmentation(args)
                segments = read_canonical_segments("motion_a_raw")

            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0].segment_id, "legacy_seg")
            self.assertEqual(segments[0].metadata["cut_source"], "migrated")
            self.assertEqual(segments[0].metadata["motion_version_id"], "motion_a_raw")
            self.assertIn("contact_transition", segments[0].metadata)

    def test_mark_segment_status_updates_canonical_segmentation(self) -> None:
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="seg_0",
            start_frame=0,
            end_frame=2,
            source="canonical",
            status="candidate",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"):
                write_canonical_segments("motion_a_raw", [segment])
                cli._cmd_mark_segment_status(
                    type(
                        "Args",
                        (),
                        {
                            "motion_version_id": "motion_a_raw",
                            "segment_id": "seg_0",
                            "status": "accepted",
                        },
                    )()
                )
                loaded = read_canonical_segments("motion_a_raw")

            self.assertFalse((root / "layers" / "accepted").exists())

        self.assertEqual(loaded[0].status, "accepted")
        self.assertEqual(loaded[0].metadata["status_history"][0]["old_status"], "candidate")
        self.assertEqual(loaded[0].metadata["status_history"][0]["new_status"], "accepted")

    def test_cutter_update_canonical_writes_back_to_segment_index(self) -> None:
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="seg_0",
            start_frame=0,
            end_frame=4,
            source="canonical",
            status="candidate",
            motion_path="motion_a.npz",
            metadata={"motion_version_id": "motion_a_raw", "parent_transition_id": "transition_0"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"npz")
            process = mock.Mock(pid=1234)

            def _save_edited() -> None:
                session_file = root / "workbench" / "sessions" / "check" / "motion_a.segments.jsonl"
                edited = segment.to_cutter_json()
                edited["start_frame"] = 1
                edited["end_frame"] = 3
                write_jsonl(session_file, [edited])

            process.wait.side_effect = _save_edited
            with (
                mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
                mock.patch.object(cli, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(cli, "launch_viewer", return_value=process) as launch_mock,
            ):
                write_canonical_segments("motion_a_raw", [segment])
                cli._cmd_cutter(
                    type(
                        "Args",
                        (),
                        {
                            "motion": str(motion),
                            "source": None,
                            "session_name": "check",
                            "destination": None,
                            "motion_version_id": "motion_a_raw",
                            "update_canonical": True,
                            "motion_id": "motion_a",
                            "repo_root": None,
                            "conda_env": "hsretargeting",
                            "timeline_port": 8094,
                            "fps": 50,
                            "with_terrain": False,
                        },
                    )()
                )
                loaded = read_canonical_segments("motion_a_raw")

        launch_mock.assert_called_once()
        self.assertEqual((loaded[0].start_frame, loaded[0].end_frame), (1, 3))
        self.assertEqual(loaded[0].source, "viser_cutter")
        self.assertEqual(loaded[0].status, "manual")
        self.assertEqual(loaded[0].metadata["cut_source"], "cutter_refined")
        self.assertFalse((root / "layers" / "manual").exists())


if __name__ == "__main__":
    unittest.main()
