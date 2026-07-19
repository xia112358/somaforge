from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi import HTTPException

from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, write_contact_edit_plan
from motion_edit.generation.contact_aware import ContactAwareGenerationResult
from motion_edit.generation.lte_fullbody import LteGenerationResult
from motion_edit.web.motion_data import load_contact_force_payload, load_motion_sequence
from motion_edit.web.server import (
    WEB_DIST,
    EditorState,
    GenerateRequest,
    GenerationJob,
    _apply_generation_settings,
    _asset_config,
    _edit_handle_payloads,
    _reset_generation_settings,
    _recent_payload,
    _run_generation,
    create_app,
)
from motion_edit.workbench.recent import RecentMotionEntry
from motion_edit.storage.schema import MotionAssetRecord
from motion_edit.segmentation.cli import build_parser as build_segmentation_parser


def _test_surface_edit() -> dict:
    return {
        "edit_id": "edit-anchor-1",
        "motion_id": "test-motion",
        "anchor_id": "anchor-1",
        "body": "right_toe_sole",
        "old_world_position": [0.0, 0.0, 0.0],
        "new_world_position": [0.01, 0.0, 0.0],
        "requested_delta_world": [0.01, 0.0, 0.0],
        "delta_world": [0.01, 0.0, 0.0],
        "tangent_delta": [0.01, 0.0],
        "affected_frames": [0, 1],
        "surface_id": "surface-1",
        "surface_normal": [0.0, 0.0, 1.0],
        "surface_coordinates_before": {"u": 0.0, "v": 0.0},
        "surface_coordinates_after": {"u": 0.01, "v": 0.0},
        "constraint_mode": "reject",
    }


def _generate_endpoint(app):
    return next(route.endpoint for route in app.routes if route.path == "/api/session/generate")


class WebMotionDataTests(unittest.TestCase):
    def test_edit_handle_payload_includes_read_only_offset_from_initial_position(self) -> None:
        initial = SimpleNamespace(
            handle_id="episode-1",
            world_position=[1.0, 2.0, 3.0],
        )
        current = SimpleNamespace(
            handle_id="episode-1",
            world_position=[1.03, 1.98, 3.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            to_dict=lambda: {"handle_id": "episode-1"},
        )

        payload = _edit_handle_payloads([current], [initial])[0]

        self.assertEqual(payload["initial_world_position"], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(payload["position_offset"]["u"], 0.03)
        self.assertAlmostEqual(payload["position_offset"]["v"], -0.02)
        self.assertTrue(payload["has_position_offset"])

    @patch("motion_edit.web.server.read_motion_asset")
    def test_asset_config_uses_bound_layer_as_prevalidated_source(self, read_motion_asset_mock) -> None:
        read_motion_asset_mock.return_value = MotionAssetRecord(
            motion_asset_id="motion-bound",
            motion_path="motion.npz",
            contact_force_npz="force.npz",
            motion_id="climb_01",
            contact_layer="contact/raw",
            bound_contact_layer="contact/bound",
            surface_catalog_path="surfaces.jsonl",
        )

        config = _asset_config("motion-bound")

        self.assertEqual(config.source_contact_layer, "contact/bound")
        self.assertTrue(config.prebound_contact_layer)
        self.assertEqual(config.motion, "motion.npz")
        self.assertEqual(config.contact_force_motion, "force.npz")

    def test_loads_named_motion_and_eight_part_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.npz"
            qpos = np.zeros((3, 9), dtype=np.float32)
            force = np.zeros((3, 8, 3), dtype=np.float32)
            force[1, 0, 2] = 100.0
            raw_points = np.zeros((3, 2, 3), dtype=np.float32)
            raw_forces = np.zeros((3, 2, 3), dtype=np.float32)
            raw_points[1, 0] = [0.3, 0.4, 0.5]
            raw_forces[1, 0] = [4.0, 5.0, 6.0]
            np.savez(
                path,
                fps=np.asarray(50),
                joint_pos=qpos,
                joint_names=np.asarray(["joint_a", "joint_b"]),
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"]),
                contact_force_part_w=force,
                contact_force_part_mask=np.linalg.norm(force, axis=-1) > 0,
                contact_force_part_position_w=np.zeros_like(force),
                contact_force_part_position_valid=np.linalg.norm(force, axis=-1) > 0,
                raw_contact_count=np.asarray([0, 1, 0]),
                raw_contact_point0_w=raw_points,
                raw_contact_force_w=raw_forces,
            )
            loaded, fps, names = load_motion_sequence(path)
            contacts = load_contact_force_payload(path, frame_count=3)
        self.assertEqual(loaded.shape, (3, 9))
        self.assertEqual(fps, 50)
        self.assertEqual(names, ("joint_a", "joint_b"))
        self.assertEqual(len(contacts["part_order"]), 8)
        self.assertTrue(contacts["masks"][1][0])
        self.assertTrue(contacts["position_valid"][1][0])
        self.assertEqual(contacts["sample_points"][1], [[0.30000001192092896, 0.4000000059604645, 0.5]])
        self.assertEqual(contacts["sample_forces"][1], [[4.0, 5.0, 6.0]])

    @patch("motion_edit.web.server.read_recent_motions")
    def test_recent_payload_shows_recent_assets_and_versions_as_peers(self, read_recent_motions_mock) -> None:
        read_recent_motions_mock.return_value = [
            RecentMotionEntry(label="Current", motion_path="current.npz", motion_id="motion", motion_asset_id="asset-a"),
            RecentMotionEntry(
                label="Current · Edited",
                motion_path="edited.npz",
                motion_id="motion",
                motion_asset_id="asset-a",
                motion_version_id="asset-a-edited",
                metadata={"kind": "generated"},
            ),
            RecentMotionEntry(label="Old", motion_path="old.npz", motion_id="motion", motion_asset_id="asset-old"),
        ]
        state = EditorState(motion_asset_id="asset-a", motion_version_id="asset-a-edited")

        payload = _recent_payload(state)

        self.assertEqual(
            [item["key"] for item in payload["items"]],
            ["asset:asset-a", "version:asset-a-edited", "asset:asset-old"],
        )
        self.assertEqual(payload["active_key"], "version:asset-a-edited")
        self.assertTrue(payload["items"][1]["active"])
        self.assertFalse(payload["items"][2]["active"])

    def test_single_port_app_includes_api_and_built_frontend(self) -> None:
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/assets", paths)
        self.assertIn("/api/recent-motions", paths)
        self.assertIn("/api/session/load", paths)
        self.assertIn("/api/session/move", paths)
        self.assertIn("/api/session/move-handle", paths)
        self.assertIn("/api/session/undo", paths)
        self.assertIn("/api/session/redo", paths)
        self.assertIn("/api/session/reset", paths)
        self.assertIn("/api/session/discard", paths)
        self.assertIn("/api/session/restore-anchor", paths)
        self.assertIn("/api/session/restore-handle", paths)
        self.assertIn("/api/session/validate", paths)
        self.assertIn("/api/session/settings", paths)
        self.assertIn("/api/session/generate", paths)
        self.assertIn("/api/session/generation", paths)
        self.assertTrue((WEB_DIST / "index.html").is_file())

    def test_generation_job_uses_formal_generator_and_marks_plan_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "edit-plan.json"
            output_motion = root / "generated.npz"
            write_contact_edit_plan(
                plan_path,
                ContactEditPlan(
                    plan_id="test-edit",
                    source_motion_path=str(root / "source.npz"),
                    source_motion_id="test-motion",
                    source_contact_layer="contact/source",
                    status="validated",
                ),
            )
            calls: list[dict] = []

            def fake_generator(plan: ContactEditPlan, **kwargs) -> ContactAwareGenerationResult:
                calls.append({"plan": plan, **kwargs})
                return ContactAwareGenerationResult(
                    generation=LteGenerationResult(
                        output_motion_path=output_motion,
                        output_contact_layer="contact/edited",
                        output_segment_layer="candidates/edited",
                        output_motion_version_id="edited-v1",
                        warnings=["test warning"],
                    )
                )

            state = EditorState(generation=GenerationJob(status="running"))
            _run_generation(
                state,
                fake_generator,
                plan_path=plan_path,
                source_contact_layer="contact/source",
                output_contact_layer="contact/edited",
                output_motion_path=str(output_motion),
                output_segment_layer="candidates/edited",
                output_motion_version_id="edited-v1",
                register_motion_version=True,
                overwrite=False,
                fps=50.0,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["fullbody_solver"], "batch_contact_laplacian")
            self.assertFalse(calls[0]["bake_force"])
            self.assertEqual(state.generation.status, "succeeded")
            self.assertEqual(state.generation.warnings, ["test warning"])
            generated_plan = read_contact_edit_plan(plan_path)
            self.assertEqual(generated_plan.status, "generated")
            self.assertEqual(generated_plan.output_motion_path, str(output_motion))

    def test_generate_http_uses_editor_state_fps_and_starts_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "edit-plan.json"
            output_motion = root / "generated.npz"
            write_contact_edit_plan(
                plan_path,
                ContactEditPlan(
                    plan_id="test-http-generate",
                    source_motion_path=str(root / "source.npz"),
                    source_motion_id="test-motion",
                    source_contact_layer="contact/source",
                    status="validated",
                    edits=[_test_surface_edit()],
                ),
            )
            calls: list[dict] = []

            def fake_generator(plan: ContactEditPlan, **kwargs) -> ContactAwareGenerationResult:
                calls.append({"plan": plan, **kwargs})
                return ContactAwareGenerationResult(
                    generation=LteGenerationResult(
                        output_motion_path=output_motion,
                        output_contact_layer="contact/edited",
                        output_segment_layer="candidates/edited",
                        output_motion_version_id=None,
                    )
                )

            app = create_app(generation_fn=fake_generator)
            state = app.state.editor_state
            state.session = SimpleNamespace(
                edit_plan_path=str(plan_path),
                contact_layer="contact/source",
                output_contact_layer="contact/edited",
            )
            state.fps = 60.0
            state.output_motion_path = str(output_motion)
            state.output_segment_layer = "candidates/edited"
            state.register_motion_version = False

            with patch("motion_edit.web.server._save_session", return_value={}):
                response = _generate_endpoint(app)(GenerateRequest(register_motion_version=False))

            self.assertIn(response["status"], {"running", "succeeded"})
            deadline = time.time() + 2.0
            while state.generation.status == "running" and time.time() < deadline:
                time.sleep(0.01)
            self.assertEqual(state.generation.status, "succeeded")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["fps"], 60.0)
            self.assertTrue(state.overwrite)

            output_motion.touch()
            with patch("motion_edit.web.server._save_session", return_value={}):
                repeated = _generate_endpoint(app)(GenerateRequest(register_motion_version=False))
            self.assertIn(repeated["status"], {"running", "succeeded"})
            deadline = time.time() + 2.0
            while state.generation.status == "running" and time.time() < deadline:
                time.sleep(0.01)
            self.assertEqual(state.generation.status, "succeeded")
            self.assertEqual(len(calls), 2)

    def test_existing_default_output_enables_repeat_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_root = Path(tmp)
            record = SimpleNamespace(output_segment_layer=None, fps=50)
            state = EditorState()
            with (
                patch("motion_edit.web.server.PACKAGE_ROOT", package_root),
                patch("motion_edit.web.server.read_motion_asset", return_value=record),
            ):
                _reset_generation_settings(state, "asset-a")
                self.assertFalse(state.overwrite)
                output = Path(state.output_motion_path)
                output.parent.mkdir(parents=True)
                output.touch()
                _reset_generation_settings(state, "asset-a")
            self.assertTrue(state.overwrite)

    def test_stale_client_cannot_disable_overwrite_for_existing_default_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_root = Path(tmp)
            state = EditorState(motion_asset_id="asset-a")
            default_output = package_root / "data" / "motions" / "generated" / "asset-a_edited.policy_ref_v1.npz"
            default_output.parent.mkdir(parents=True)
            default_output.touch()
            state.output_motion_path = str(default_output)
            with patch("motion_edit.web.server.PACKAGE_ROOT", package_root):
                _apply_generation_settings(state, GenerateRequest(overwrite=False))
            self.assertTrue(state.overwrite)

    def test_generate_http_does_not_leave_queued_job_when_worker_arguments_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "edit-plan.json"
            output_motion = root / "generated.npz"
            write_contact_edit_plan(
                plan_path,
                ContactEditPlan(
                    plan_id="test-http-thread-failure",
                    source_motion_path=str(root / "source.npz"),
                    source_motion_id="test-motion",
                    source_contact_layer="contact/source",
                    status="validated",
                    edits=[_test_surface_edit()],
                ),
            )
            app = create_app()
            state = app.state.editor_state
            state.session = SimpleNamespace(
                edit_plan_path=str(plan_path),
                contact_layer="contact/source",
                output_contact_layer="contact/edited",
            )
            state.output_motion_path = str(output_motion)
            state.register_motion_version = False
            state.fps = "invalid"  # type: ignore[assignment]

            with patch("motion_edit.web.server._save_session", return_value={}):
                with self.assertRaises(HTTPException) as caught:
                    _generate_endpoint(app)(GenerateRequest(register_motion_version=False))

            self.assertEqual(caught.exception.status_code, 400)
            self.assertIn("could not convert string to float", str(caught.exception.detail))
            self.assertEqual(state.generation.status, "failed")
            self.assertEqual(state.generation.stage, "preflight")
            self.assertIn("could not convert string to float", state.generation.error or "")
            self.assertIsNone(state.generation_worker)

    def test_segmentation_cli_no_longer_imports_removed_cutter(self) -> None:
        parser = build_segmentation_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        self.assertNotIn("cutter", subparsers.choices)
        self.assertIn("start", subparsers.choices)


if __name__ == "__main__":
    unittest.main()
