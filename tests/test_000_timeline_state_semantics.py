from __future__ import annotations

import tempfile

import numpy as np

import test_workbench as _workbench_tests


def _timeline_state_keeps_semantic_status_and_selected_flag(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _workbench_tests.Path(tmp)
        graph = _workbench_tests.contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray(
                [
                    [True, False],
                    [True, False],
                    [False, True],
                    [False, True],
                ]
            ),
            body_pos_w=np.zeros((4, 2, 3), dtype=np.float32),
            body_names=["LF", "RH"],
        )
        graph = type(graph)(
            motion_id=graph.motion_id,
            events=graph.events,
            anchors=[
                type(anchor)(
                    **{
                        **anchor.__dict__,
                        "surface_id": "top",
                        "surface_normal": [0.0, 0.0, 1.0],
                        "surface_origin": [0.0, 0.0, 0.0],
                        "surface_tangent_u": [1.0, 0.0, 0.0],
                        "surface_tangent_v": [0.0, 1.0, 0.0],
                        "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                        "surface_coordinates": {"u": 0.0, "v": 0.0},
                    }
                )
                for anchor in graph.anchors
            ],
            patches=graph.patches,
            transitions=graph.transitions,
        )
        _workbench_tests.write_contact_layer(root / "layers" / "contact" / "bound", graph)
        session = _workbench_tests.prepare_surface_editor_session(
            motion_path=str(root / "motion_a.npz"),
            motion_id="motion_a",
            contact_layer="contact/bound",
            surface_catalog=None,
            session_name="timeline_state",
            layers_root=root / "layers",
            workbench_root=root / "workbench",
        )
        state = _workbench_tests.load_editor_state(session.session_dir / "session.json")
        controller = _workbench_tests.SurfaceEditorController.create(_workbench_tests._FakeServer(), state)
        controller.select_anchor(graph.anchors[0].anchor_id)
        controller.recent_motion_items = lambda: [  # type: ignore[method-assign]
            {"label": "motion_a", "motion_path": str(root / "motion_a.npz"), "motion_id": "motion_a"}
        ]
        payload = _workbench_tests.contact_timeline_state(
            controller=controller,
            playback=_workbench_tests._FakePlayback(n_frames=4, frame=2),
            motion_name="motion_a.npz",
            fps=50,
        )

    self.assertEqual(payload["motion_name"], "motion_a.npz")
    self.assertEqual(payload["current_frame"], 2)
    self.assertEqual(payload["bodies"], ["LF", "RH"])
    self.assertEqual(len(payload["anchors"]), 2)
    self.assertEqual(payload["anchors"][0]["status"], "suspicious")
    self.assertTrue(payload["anchors"][0]["selected"])
    self.assertEqual(payload["selected_anchor"]["anchor_id"], graph.anchors[0].anchor_id)
    self.assertTrue(payload["selected_anchor"]["selected"])
    self.assertEqual(payload["selected_anchor"]["surface_id"], "top")
    self.assertEqual(payload["binding_counts"]["anchor_count"], 2)
    self.assertEqual(payload["binding_counts"]["failed_count"], 0)
    self.assertEqual(payload["layers"]["contact_layer"], "contact/bound")
    self.assertEqual(payload["recent_motions"][0]["label"], "motion_a")


_workbench_tests.SurfaceEditorSessionTests.test_contact_timeline_state_exports_anchor_lanes = (
    _timeline_state_keeps_semantic_status_and_selected_flag
)
