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


class _FakeHttpd:
    def shutdown(self) -> None:
        return None

    def server_close(self) -> None:
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

    def test_cutter_opens_3d_viewer_and_wrapper_timeline(self) -> None:
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
                    viewer_port=8094,
                    timeline_port=8095,
                    fps=50,
                    with_terrain=False,
                )
                with (
                    mock.patch("motion_edit.segmentation.cutter.launch_viewer", return_value=_FakeProcess()) as launch,
                    mock.patch("motion_edit.segmentation.cutter.start_segmentation_timeline_wrapper", return_value=_FakeHttpd()) as timeline,
                ):
                    _cmd_cutter(args)

                kwargs = launch.call_args.kwargs
                self.assertEqual(launch.call_args.args[0], str(motion))
                self.assertIsNone(kwargs["segment_path"])
                self.assertEqual(kwargs["timeline_port"], 8094)
                timeline_kwargs = timeline.call_args.kwargs
                self.assertEqual(timeline_kwargs["timeline_port"], 8095)
                self.assertEqual(timeline_kwargs["viser_port"], 8094)
                self.assertEqual(timeline_kwargs["controller"].session.session_id, "seg_session")
                self.assertEqual(read_canonical_segments("motion_a_raw")[0].start_frame, 0)


if __name__ == "__main__":
    unittest.main()
