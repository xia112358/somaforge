from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from motion_edit import cli
from motion_edit.contact import (
    anchors_from_contact_mask,
    bind_anchor_to_plane,
    bind_anchor_to_surface,
    bind_anchors_to_surfaces,
    bind_segment_to_contact_graph,
    contact_graph_from_masks,
    detect_contact_events,
    make_anchor_move_edit,
    move_contact_anchor,
    move_contact_anchor_on_surface,
    move_anchor_in_graph,
    move_anchor_in_contact_layer,
    read_contact_anchors,
    read_contact_events,
    read_contact_graph,
    read_contact_patches,
    read_contact_surfaces,
    read_contact_transitions,
    segment_from_contact_transition,
    surface_compatible_with_body,
    transitions_from_proto_indices,
    write_contact_surfaces,
    write_contact_jsonl,
    write_contact_layer,
)
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord, ContactSurfaceRecord
from motion_edit.schema import SegmentRecord


class ContactEventTests(unittest.TestCase):
    def test_anchor_world_position_roundtrips_jsonl(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.1, 0.2, 0.3],
            object_position=[0.0, 0.2, 0.3],
            object_id="terrain",
            normal=[0.0, 0.0, 1.0],
            surface_id="platform_top",
            surface_type="box_face",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-0.5, 0.5]},
            surface_coordinates={"u": 0.1, "v": 0.2},
            surface_binding_source="manual",
            editable=True,
            position_source="manual",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anchors.jsonl"
            write_contact_jsonl(path, [anchor])
            loaded = read_contact_anchors(path)[0]

        self.assertEqual(loaded.world_position, [0.1, 0.2, 0.3])
        self.assertEqual(loaded.object_position, [0.0, 0.2, 0.3])
        self.assertEqual(loaded.normal, [0.0, 0.0, 1.0])
        self.assertEqual(loaded.surface_id, "platform_top")
        self.assertEqual(loaded.surface_type, "box_face")
        self.assertEqual(loaded.surface_normal, [0.0, 0.0, 1.0])
        self.assertEqual(loaded.surface_bounds, {"u": [-1.0, 1.0], "v": [-0.5, 0.5]})
        self.assertEqual(loaded.surface_coordinates, {"u": 0.1, "v": 0.2})
        self.assertEqual(loaded.surface_binding_source, "manual")
        self.assertTrue(loaded.editable)
        self.assertEqual(loaded.position_source, "manual")

    def test_contact_surface_record_roundtrips_jsonl(self) -> None:
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="box_0_top",
            object_id="box_0",
            surface_type="box_face",
            origin=[1.0, 0.0, 0.8],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-0.25, 0.25], "v": [-0.25, 0.25]},
            source="manual_surface_catalog",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "surfaces.jsonl"
            write_contact_surfaces(path, [surface])
            loaded = read_contact_surfaces(path)[0]

        self.assertEqual(loaded.surface_id, "box_0_top")
        self.assertEqual(loaded.object_id, "box_0")
        self.assertEqual(loaded.normal, [0.0, 0.0, 1.0])
        self.assertEqual(loaded.bounds, {"u": [-0.25, 0.25], "v": [-0.25, 0.25]})

    def test_contact_surface_record_rejects_non_normalized_axes(self) -> None:
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="bad_top",
            object_id=None,
            surface_type="plane",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 2.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
        )

        with self.assertRaisesRegex(ValueError, "normal"):
            surface.validate()

    def test_anchor_edit_surface_constraint_fields_validate(self) -> None:
        edit = ContactAnchorEditRecord(
            edit_id="edit_a",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            old_world_position=[0.0, 0.0, 0.0],
            new_world_position=[0.1, 0.0, 0.0],
            requested_delta_world=[0.1, 0.0, 0.2],
            delta_world=[0.1, 0.0, 0.0],
            tangent_delta=[0.1, 0.0],
            surface_id="platform_top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_coordinates_before={"u": 0.0, "v": 0.0},
            surface_coordinates_after={"u": 0.1, "v": 0.0},
            constraint_mode="reject",
            clamped=False,
        )

        data = edit.to_dict()

        self.assertEqual(data["requested_delta_world"], [0.1, 0.0, 0.2])
        self.assertEqual(data["delta_world"], [0.1, 0.0, 0.0])
        self.assertEqual(data["tangent_delta"], [0.1, 0.0])
        self.assertEqual(data["surface_id"], "platform_top")

    def test_move_contact_anchor_records_old_new_and_delta(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.0],
            position_source="body_pos_w_mean",
        )

        moved = move_contact_anchor(anchor, delta_world=[0.1, 0.0, 0.0])
        edit = make_anchor_move_edit(anchor, new_world_position=[1.1, 2.0, 0.0], affected_frames=[0, 10], source="lte")

        self.assertEqual(moved.world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved.position_source, "manual")
        self.assertEqual(moved.metadata["contact_anchor_edits"][-1]["old_world_position"], [1.0, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")
        self.assertEqual(edit.old_world_position, [1.0, 2.0, 0.0])
        self.assertEqual(edit.new_world_position, [1.1, 2.0, 0.0])
        self.assertEqual(edit.delta_world, [0.10000000000000009, 0.0, 0.0])

    def test_move_contact_anchor_on_surface_projects_normal_delta(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, requested_world_delta=[0.1, 0.0, 0.2])

        self.assertEqual(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(edit.requested_delta_world, [0.1, 0.0, 0.2])
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])
        self.assertEqual(edit.tangent_delta, [0.1, 0.0])
        self.assertEqual(edit.surface_id, "top")
        self.assertEqual(edit.constraint_mode, "reject")
        self.assertFalse(edit.clamped)

    def test_move_contact_anchor_on_surface_uses_tangent_basis(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[1.0, 2.0, 0.0],
            surface_tangent_u=[0.0, 1.0, 0.0],
            surface_tangent_v=[1.0, 0.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.3])

        self.assertEqual(moved.world_position, [1.3, 2.2, 0.0])
        self.assertEqual(moved.surface_coordinates, {"u": 0.2, "v": 0.3})
        self.assertEqual(edit.delta_world, [0.3, 0.2, 0.0])

    def test_move_contact_anchor_on_surface_rejects_outside_bounds(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        with self.assertRaises(ValueError):
            move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.0])

    def test_move_contact_anchor_on_surface_clamps_outside_bounds(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.0], mode="clamp")

        self.assertEqual(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(moved.object_id, "box")
        self.assertEqual(moved.surface_id, "top")
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])
        self.assertEqual(edit.tangent_delta, [0.1, 0.0])
        self.assertEqual(edit.surface_id, "top")
        self.assertEqual(edit.constraint_mode, "clamp")
        self.assertTrue(edit.clamped)

    def test_bind_anchor_to_plane_creates_surface_binding_for_safe_moves(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.2, 0.3, 0.0],
        )

        bound = bind_anchor_to_plane(
            anchor,
            surface_id="platform_top",
            normal=[0.0, 0.0, 1.0],
            origin=[0.0, 0.0, 0.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [0.0, 1.0], "v": [0.0, 1.0]},
            surface_type="box_face",
            source="terrain_binding",
        )
        moved, edit = move_contact_anchor_on_surface(bound, tangent_delta=[0.1, 0.0])

        self.assertEqual(bound.surface_coordinates, {"u": 0.2, "v": 0.3})
        self.assertEqual(bound.surface_binding_source, "terrain_binding")
        self.assertEqual(moved.world_position, [0.30000000000000004, 0.3, 0.0])
        self.assertEqual(edit.surface_id, "platform_top")

    def test_bind_anchor_to_surface_computes_surface_coordinates(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.2, 0.3, 0.02],
        )
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="box_0_top",
            object_id="box_0",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            source="manual_surface_catalog",
        )

        bound = bind_anchor_to_surface(anchor, surface, max_distance=0.05)

        self.assertEqual(bound.object_id, "box_0")
        self.assertEqual(bound.surface_id, "box_0_top")
        self.assertEqual(bound.world_position, [0.2, 0.3, 0.0])
        self.assertEqual(bound.surface_coordinates, {"u": 0.2, "v": 0.3})
        self.assertEqual(bound.metadata["surface_bindings"][-1]["signed_surface_distance"], 0.02)
        self.assertEqual(bound.metadata["surface_bindings"][-1]["projected_world_position"], [0.2, 0.3, 0.0])

    def test_bind_anchor_to_surface_rejects_distance_and_bounds(self) -> None:
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="top",
            object_id=None,
            surface_type="plane",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
        )
        far = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_far",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.2],
        )
        outside = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_outside",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.2, 0.0, 0.0],
        )

        with self.assertRaisesRegex(ValueError, "max_distance"):
            bind_anchor_to_surface(far, surface, max_distance=0.05)
        with self.assertRaisesRegex(ValueError, "bounds"):
            bind_anchor_to_surface(outside, surface, max_distance=0.05)

    def test_bind_anchor_to_surface_clamps_bounds(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.2, 0.0, 0.0],
        )
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="top",
            object_id="box",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
        )

        bound = bind_anchor_to_surface(anchor, surface, mode="clamp")

        self.assertEqual(bound.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(bound.surface_coordinates, {"u": 0.1, "v": 0.0})
        self.assertTrue(bound.metadata["surface_bindings"][-1]["clamped"])

    def test_bind_anchors_to_surfaces_applies_body_policy_and_failure_metadata(self) -> None:
        foot = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
        )
        hand = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lh",
            body="LH",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
        )
        vertical = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="wall",
            object_id="wall",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[1.0, 0.0, 0.0],
            tangent_u=[0.0, 1.0, 0.0],
            tangent_v=[0.0, 0.0, 1.0],
            bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
        )

        bound = bind_anchors_to_surfaces([foot, hand], [vertical])

        self.assertFalse(surface_compatible_with_body("LF", vertical))
        self.assertTrue(surface_compatible_with_body("LH", vertical))
        self.assertTrue(bound[0].metadata["surface_binding_failed"])
        self.assertEqual(bound[1].surface_id, "wall")

    def test_bound_anchor_can_move_on_surface(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.01],
        )
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="top",
            object_id="box",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
        )

        bound = bind_anchor_to_surface(anchor, surface)
        moved, edit = move_contact_anchor_on_surface(bound, tangent_delta=[0.1, 0.0])

        self.assertEqual(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])

    def test_bind_contact_surfaces_cli_writes_bound_contact_layer(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True], [True], [False]]),
            body_pos_w=np.asarray([[[0.1, 0.2, 0.02]], [[0.1, 0.2, 0.02]], [[0.0, 0.0, 0.0]]]),
            body_names=["LF"],
        )
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="box_0_top",
            object_id="box_0",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contact_layer(root / "layers" / "contact" / "force_contact", graph)
            surface_catalog = root / "surfaces.jsonl"
            write_contact_surfaces(surface_catalog, [surface])
            with mock.patch.object(cli, "LAYERS_ROOT", root / "layers"):
                cli._cmd_bind_contact_surfaces(
                    type(
                        "Args",
                        (),
                        {
                            "contact_layer": "contact/force_contact",
                            "motion_id": "motion_a",
                            "surface_catalog": str(surface_catalog),
                        "terrain_urdf": None,
                        "top_only_surfaces": False,
                        "no_ground": False,
                        "ground_z": 0.0,
                        "ground_half_extent": 10.0,
                        "output_contact_layer": "contact/force_contact_bound",
                            "max_distance": 0.05,
                            "mode": "reject",
                            "motion_version_id": None,
                            "update_motion_version": False,
                            "rebind_canonical_segments": False,
                        },
                    )()
                )
                bound = read_contact_graph(root / "layers" / "contact" / "force_contact_bound", "motion_a")
                written_surfaces = read_contact_surfaces(
                    root / "layers" / "contact" / "force_contact_bound" / "surfaces" / "motion_a.jsonl"
                )

        self.assertEqual(bound.anchors[0].surface_id, "box_0_top")
        self.assertEqual(bound.anchors[0].world_position, [0.1, 0.2, 0.0])
        self.assertEqual(bound.patches[0].patch_center_world, bound.anchors[0].world_position)
        self.assertEqual(written_surfaces[0].surface_id, "box_0_top")

    def test_create_box_surface_catalog_cli_emits_top_and_side_faces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "surfaces.jsonl"
            cli._cmd_create_box_surface_catalog(
                type(
                    "Args",
                    (),
                    {
                        "motion_id": "motion_a",
                        "box": ["box_0:1.0,0.0,0.4:0.5,0.5,0.8"],
                        "top_only": False,
                        "output": str(output),
                    },
                )()
            )
            surfaces = read_contact_surfaces(output)

        by_id = {surface.surface_id: surface for surface in surfaces}
        self.assertEqual(len(surfaces), 5)
        self.assertEqual(by_id["box_0_top"].origin, [1.0, 0.0, 0.8])
        self.assertEqual(by_id["box_0_top"].normal, [0.0, 0.0, 1.0])
        self.assertEqual(by_id["box_0_top"].bounds, {"u": [-0.25, 0.25], "v": [-0.25, 0.25]})
        self.assertEqual(by_id["box_0_pos_x"].normal, [1.0, 0.0, 0.0])
        self.assertEqual(by_id["box_0_neg_y"].normal, [0.0, -1.0, 0.0])

    def test_create_urdf_surface_catalog_uses_mesh_geometry_and_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh_dir = root / "meshes"
            mesh_dir.mkdir()
            obj = mesh_dir / "box.obj"
            obj.write_text(
                "\n".join(
                    [
                        "v 0 0 0",
                        "v 2 0 0",
                        "v 0 4 0",
                        "v 2 4 0",
                        "v 0 0 1",
                        "v 2 0 1",
                        "v 0 4 1",
                        "v 2 4 1",
                        "f 5 6 8",
                        "f 5 8 7",
                    ]
                ),
                encoding="utf-8",
            )
            urdf = root / "terrain.urdf"
            urdf.write_text(
                f"""<?xml version="1.0"?>
<robot name="terrain">
  <link name="box_link">
    <collision>
      <origin xyz="1 2 3" rpy="0 0 0"/>
      <geometry>
        <mesh filename="{obj}" scale="0.5 0.25 2.0"/>
      </geometry>
    </collision>
  </link>
</robot>
""",
                encoding="utf-8",
            )
            output = root / "surfaces.jsonl"

            cli._cmd_create_urdf_surface_catalog(
                type(
                    "Args",
                    (),
                    {
                        "motion_id": "motion_a",
                        "terrain_urdf": str(urdf),
                        "top_only": True,
                        "no_ground": False,
                        "ground_z": 0.0,
                        "ground_half_extent": 10.0,
                        "output": str(output),
                    },
                )()
            )
            surfaces = read_contact_surfaces(output)

        self.assertEqual(len(surfaces), 2)
        top = next(surface for surface in surfaces if surface.surface_id == "box_link_0_top")
        ground = next(surface for surface in surfaces if surface.surface_id == "terrain_ground_z0")
        self.assertEqual(top.surface_id, "box_link_0_top")
        self.assertEqual(top.origin, [1.5, 2.5, 5.0])
        self.assertEqual(top.bounds, {"u": [-0.5, 0.5], "v": [-0.5, 0.5]})
        self.assertEqual(top.metadata["surface_extraction"], "obj_face_groups")
        self.assertEqual(len(top.metadata["polygon_world"]), 4)
        self.assertEqual(ground.surface_type, "plane")

    def test_create_urdf_surface_catalog_emits_side_faces_and_ground(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obj = root / "box.obj"
            obj.write_text(
                "\n".join(
                    [
                        "v 0 0 0",
                        "v 1 0 0",
                        "v 0 1 0",
                        "v 1 1 0",
                        "v 0 0 1",
                        "v 1 0 1",
                        "v 0 1 1",
                        "v 1 1 1",
                        "f 5 6 8",
                        "f 5 8 7",
                        "f 1 3 4",
                        "f 1 4 2",
                        "f 1 5 7",
                        "f 1 7 3",
                        "f 2 4 8",
                        "f 2 8 6",
                    ]
                ),
                encoding="utf-8",
            )
            urdf = root / "terrain.urdf"
            urdf.write_text(
                f"""<robot name="terrain"><link name="box"><collision><geometry><mesh filename="{obj}"/></geometry></collision></link></robot>""",
                encoding="utf-8",
            )
            output = root / "surfaces.jsonl"

            cli._cmd_create_urdf_surface_catalog(
                type(
                    "Args",
                    (),
                    {
                        "motion_id": "motion_a",
                        "terrain_urdf": str(urdf),
                        "top_only": False,
                        "no_ground": False,
                        "ground_z": 0.0,
                        "ground_half_extent": 10.0,
                        "output": str(output),
                    },
                )()
            )
            surfaces = read_contact_surfaces(output)

        ids = {surface.surface_id for surface in surfaces}
        self.assertIn("box_0_top", ids)
        self.assertIn("box_0_side_00", ids)
        self.assertIn("box_0_side_01", ids)
        self.assertIn("terrain_ground_z0", ids)

    def test_bind_contact_surfaces_can_generate_catalog_from_terrain_urdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers = root / "layers"
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.5, 0.5, 1.0]], [[0.5, 0.5, 1.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["left_foot"],
            )
            write_contact_layer(layers / "contact" / "force_contact", graph)
            obj = root / "box.obj"
            obj.write_text(
                "\n".join(
                    [
                        "v 0 0 0",
                        "v 1 0 0",
                        "v 0 1 0",
                        "v 1 1 0",
                        "v 0 0 1",
                        "v 1 0 1",
                        "v 0 1 1",
                        "v 1 1 1",
                        "f 5 6 8",
                        "f 5 8 7",
                    ]
                ),
                encoding="utf-8",
            )
            urdf = root / "terrain.urdf"
            urdf.write_text(
                f"""<robot name="terrain"><link name="box"><collision><geometry><mesh filename="{obj}"/></geometry></collision></link></robot>""",
                encoding="utf-8",
            )
            with mock.patch.object(cli, "LAYERS_ROOT", layers), mock.patch.object(cli, "SURFACES_ROOT", root / "surfaces"):
                cli._cmd_bind_contact_surfaces(
                    type(
                        "Args",
                        (),
                        {
                            "contact_layer": "contact/force_contact",
                            "motion_id": "motion_a",
                            "surface_catalog": None,
                            "terrain_urdf": str(urdf),
                            "top_only_surfaces": True,
                            "no_ground": False,
                            "ground_z": 0.0,
                            "ground_half_extent": 10.0,
                            "output_contact_layer": "contact/force_contact_bound",
                            "max_distance": 0.05,
                            "mode": "reject",
                            "motion_version_id": None,
                            "update_motion_version": False,
                            "rebind_canonical_segments": False,
                        },
                    )()
                )
                bound = read_contact_graph(layers / "contact" / "force_contact_bound", "motion_a")
                generated = read_contact_surfaces(root / "surfaces" / "motion_a_terrain_surfaces.jsonl")

        self.assertEqual(generated[0].surface_id, "box_0_top")
        self.assertEqual(generated[1].surface_id, "terrain_ground_z0")
        self.assertEqual(bound.anchors[0].surface_id, "box_0_top")
        self.assertEqual(bound.anchors[0].world_position, [0.5, 0.5, 1.0])

    def test_move_anchor_in_graph_updates_anchor_patch_and_returns_edit(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [True, False], [False, False]]),
            body_pos_w=np.asarray(
                [
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
                ]
            ),
            body_names=["left_foot", "right_foot"],
        )

        with self.assertRaises(ValueError):
            move_anchor_in_graph(graph, anchor_id=graph.anchors[0].anchor_id, delta_world=[0.1, 0.0, 0.0])

        moved_graph, edit = move_anchor_in_graph(
            graph,
            anchor_id=graph.anchors[0].anchor_id,
            delta_world=[0.1, 0.0, 0.0],
            allow_free_3d=True,
        )

        self.assertEqual(moved_graph.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved_graph.patches[0].patch_center_world, [1.1, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")

    def test_move_anchor_in_contact_layer_writes_graph_and_edit_record(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [True, False], [False, False]]),
            body_pos_w=np.asarray(
                [
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
                ]
            ),
            body_names=["left_foot", "right_foot"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contact_layer(root / "source", graph)
            moved_graph, edit = move_anchor_in_contact_layer(
                root / "source",
                root / "moved",
                motion_id="motion_a",
                anchor_id=graph.anchors[0].anchor_id,
                delta_world=[0.1, 0.0, 0.0],
                allow_free_3d=True,
            )
            loaded = read_contact_graph(root / "moved", "motion_a")
            edit_lines = (root / "moved" / "edits" / "motion_a.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertEqual(loaded.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved_graph.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")
        self.assertEqual(len(edit_lines), 1)

    def test_detects_touchdown_liftoff_active_and_support_changes(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        active = np.asarray(
            [
                [False, True],
                [True, False],
                [True, False],
                [False, True],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        events = detect_contact_events(
            motion_id="motion_a",
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_names=["LF", "RF"],
            source="test",
        )

        event_types = [(event.frame, event.body, event.event_type) for event in events]
        self.assertIn((1, "LF", "touchdown"), event_types)
        self.assertIn((2, "RF", "liftoff"), event_types)
        self.assertIn((1, "active", "active_change"), event_types)
        self.assertIn((2, "support", "support_switch"), event_types)

    def test_anchor_interval_grouping(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        anchors = anchors_from_contact_mask(
            motion_id="motion_a",
            contact_mask=contact,
            support_mask=support,
            body_names=["LF", "RF"],
        )

        spans = [(anchor.body, anchor.start_frame, anchor.end_frame, anchor.role) for anchor in anchors]
        self.assertIn(("LF", 1, 3, "support"), spans)
        self.assertIn(("RF", 0, 2, "support"), spans)
        self.assertIn(("RF", 4, 5, "support"), spans)

    def test_anchor_position_estimated_from_body_pos_w_interval(self) -> None:
        contact = np.asarray([[True, False], [True, False], [False, False]])
        body_pos_w = np.asarray(
            [
                [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[1.2, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
            ]
        )

        anchors = anchors_from_contact_mask(
            motion_id="motion_a",
            contact_mask=contact,
            body_pos_w=body_pos_w,
            body_names=["LF", "RF"],
        )

        self.assertEqual(anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(anchors[0].position_source, "body_pos_w_mean")
        self.assertEqual(anchors[0].metadata["first_world_position"], [1.0, 2.0, 0.0])
        self.assertEqual(anchors[0].metadata["last_world_position"], [1.2, 2.0, 0.0])
        self.assertAlmostEqual(anchors[0].metadata["max_drift_xy"], 0.2)

    def test_transition_converts_to_segment_with_contact_metadata(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        active = np.asarray(
            [
                [False, True],
                [True, False],
                [True, False],
                [False, True],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        events, anchors, transitions = transitions_from_proto_indices(
            motion_id="motion_a",
            starts=[1],
            ends=[4],
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_names=["LF", "RF"],
        )
        segment = segment_from_contact_transition(
            transition=transitions[0],
            segment_id="motion_a_force_0000",
            source="force_contact",
            status="candidate",
            track="proto",
            motion_path="/tmp/motion_a.npz",
            clip_npz="/tmp/motion_a.npz",
            clip_output_dir=None,
            clip_file_name="motion_a.npz",
            atom_label="force_contact_00",
            contact_start="11",
            contact_end="00",
            active="10",
            support="01",
            events=events,
            anchors=anchors,
        )

        self.assertEqual(segment.metadata["active_body"], "LF")
        self.assertEqual(segment.metadata["support_bodies"], ["RF"])
        self.assertEqual(segment.metadata["contact_transition"]["start_frame"], 1)
        self.assertGreaterEqual(len(segment.metadata["contact_events"]), 1)
        self.assertGreaterEqual(len(segment.metadata["contact_anchors"]), 1)

    def test_contact_records_roundtrip_as_typed_jsonl(self) -> None:
        contact = np.asarray([[False, True], [True, True], [True, False]])
        events, anchors, transitions = transitions_from_proto_indices(
            motion_id="motion_a",
            starts=[0],
            ends=[3],
            contact_mask=contact,
            body_names=["LF", "RF"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contact_jsonl(root / "events.jsonl", events)
            write_contact_jsonl(root / "anchors.jsonl", anchors)
            write_contact_jsonl(root / "patches.jsonl", contact_graph_from_masks(motion_id="motion_a", contact_mask=contact, body_names=["LF", "RF"]).patches)
            write_contact_jsonl(root / "transitions.jsonl", transitions)

            loaded_events = read_contact_events(root / "events.jsonl")
            loaded_anchors = read_contact_anchors(root / "anchors.jsonl")
            loaded_patches = read_contact_patches(root / "patches.jsonl")
            loaded_transitions = read_contact_transitions(root / "transitions.jsonl")

        self.assertEqual(loaded_events[0].event_id, events[0].event_id)
        self.assertEqual(loaded_anchors[0].anchor_id, anchors[0].anchor_id)
        self.assertEqual(loaded_patches[0].anchor_id, loaded_anchors[0].anchor_id)
        self.assertEqual(loaded_transitions[0].transition_id, transitions[0].transition_id)

    def test_contact_graph_groups_events_anchors_and_transitions(self) -> None:
        contact = np.asarray([[True, False], [False, False], [True, False]])

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_names=["LF", "RF"],
            source="test",
        )

        self.assertEqual(graph.motion_id, "motion_a")
        self.assertTrue(any(event.event_type == "liftoff" for event in graph.events))
        self.assertTrue(any(event.event_type == "touchdown" for event in graph.events))
        self.assertEqual(len(graph.anchors), 2)
        self.assertEqual(len(graph.patches), 2)
        self.assertEqual(graph.patches[0].patch_type, "foot")
        self.assertEqual(graph.transitions[0].active_body, "LF")
        self.assertEqual(graph.to_dict()["motion_id"], "motion_a")
        self.assertEqual(len(graph.to_dict()["patches"]), 2)

    def test_contact_patch_uses_anchor_position_and_patch_preset(self) -> None:
        contact = np.asarray([[True, False], [True, False], [False, False]])
        body_pos_w = np.asarray(
            [
                [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[1.2, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
            ]
        )

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_pos_w=body_pos_w,
            body_names=["left_foot", "right_foot"],
        )

        patch = graph.patches[0]
        self.assertEqual(patch.patch_type, "foot")
        self.assertEqual(patch.patch_center_world, [1.1, 2.0, 0.0])
        self.assertEqual(patch.link_names, ["left_foot", "left_foot_sole"])
        self.assertAlmostEqual(patch.slip_score or 0.0, 0.1)

    def test_contact_layer_roundtrips_graph_components(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "contact_layer"
            write_contact_layer(root, graph)
            loaded = read_contact_graph(root, "motion_a")

        self.assertEqual([event.event_id for event in loaded.events], [event.event_id for event in graph.events])
        self.assertEqual([anchor.anchor_id for anchor in loaded.anchors], [anchor.anchor_id for anchor in graph.anchors])
        self.assertEqual([patch.patch_id for patch in loaded.patches], [patch.patch_id for patch in graph.patches])
        self.assertEqual(
            [transition.transition_id for transition in loaded.transitions],
            [transition.transition_id for transition in graph.transitions],
        )

    def test_contact_layer_read_derives_missing_patches_for_legacy_layers(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "contact_layer"
            write_contact_jsonl(root / "events" / "motion_a.jsonl", graph.events)
            write_contact_jsonl(root / "anchors" / "motion_a.jsonl", graph.anchors)
            write_contact_jsonl(root / "transitions" / "motion_a.jsonl", graph.transitions)
            loaded = read_contact_graph(root, "motion_a")

        self.assertEqual(len(loaded.patches), len(graph.anchors))

    def test_bind_segment_to_contact_graph_refreshes_metadata_for_bounds(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="segment_a",
            start_frame=1,
            end_frame=2,
            source="manual",
            metadata={"contact_transition": {"stale": True}},
        )

        bound = bind_segment_to_contact_graph(segment, graph)

        self.assertEqual(bound.metadata["contact_transition"]["transition_id"], graph.transitions[0].transition_id)
        self.assertEqual(bound.metadata["contact_binding"]["transition_id"], graph.transitions[0].transition_id)
        self.assertEqual(bound.metadata["contact_binding"]["patch_count"], 2)
        self.assertEqual(len(bound.metadata["contact_patches"]), 2)
        self.assertEqual(bound.metadata["active_body"], "LF")


if __name__ == "__main__":
    unittest.main()
