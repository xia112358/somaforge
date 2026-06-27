from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from motion_edit.schema import SegmentRecord
from motion_edit.segmentation.cutter import _cmd_cutter
from motion_edit.storage import io as storage_io
from motion_edit.storage.io import read_canonical_segments, write_canonical_segments, write_motion_version
from motion_edit.storage.schema import MotionVersionRecord


class _FakeProcess:
    pid = 12345

    def wait(self) -> None:
        return None


class SegmentationCutterLauncherTests(unittest.TestCase):
    def _patch_storage(self, root: Path):
        return (
            mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
            mock.patch.object(storage_io, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
            mock.patch.object(storage_io, "TOKENS_ROOT", root / "tokens"),
        )

    def _seed(self, root: Path) -> Path:
        motion = root / "motion_a.npz"
        motion.write_bytes(b"placeholder")
        write_motion_version(MotionVersionRecord(motion_version_id="motion_a_raw", motion_path=str(motion)))
        write_canonical_segments(
            "motion_a_raw",
            [
                SegmentRecord(
                    motion_id="motion_a",
                    segment_id="seg_0",
                    start_frame=0,
                    end_frame=10,
                    source="auto_contact",
                    status="candidate",
                    motion_path=str(motion),
                )
            ],
        )
        return motion

    def test_cutter_opens_existing_viewer_with_draft_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patch_storage(root)[0], self._patch_storage(root)[1], self._patch_storage(root)[2]:
                motion = self._seed(root)
                args = argparse.Namespace(
                    motion_version_id="motion_a_raw",
                    session=None,
                    session_id="seg_session",
                    overwrite=False,
                    motion=None,
                    repo_root="/repo",
                    conda_env="env",
                    timeline_port=8094,
                    fps=50,
                    with_terrain=False,
                    save_on_exit=False,
                    allow_overlap=False,
                    reason=None,
                )
                with mock.patch("motion_edit.segmentation.cutter.launch_viewer", return_value=_FakeProcess()) as launch:
                    _cmd_cutter(args)

                kwargs = launch.call_args.kwargs
                self.assertEqual(launch.call_args.args[0], str(motion))
                self.assertEqual(Path(kwargs["segment_path"]).name, "draft_segments.jsonl")
                self.assertIn("seg_session", str(kwargs["segment_path"]))
                self.assertEqual(read_canonical_segments("motion_a_raw")[0].start_frame, 0)

    def test_cutter_save_on_exit_replaces_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patch_storage(root)[0], self._patch_storage(root)[1], self._patch_storage(root)[2]:
                self._seed(root)
                args = argparse.Namespace(
                    motion_version_id="motion_a_raw",
                    session=None,
                    session_id="seg_session_save",
                    overwrite=False,
                    motion=None,
                    repo_root="/repo",
                    conda_env="env",
                    timeline_port=8094,
                    fps=50,
                    with_terrain=False,
                    save_on_exit=True,
                    allow_overlap=False,
                    reason="save reviewed segmentation",
                )
                with mock.patch("motion_edit.segmentation.cutter.launch_viewer", return_value=_FakeProcess()):
                    _cmd_cutter(args)

                saved = read_canonical_segments("motion_a_raw")
                self.assertEqual([segment.segment_id for segment in saved], ["seg_0"])


if __name__ == "__main__":
    unittest.main()
