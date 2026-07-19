from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from motion_edit.contact import (
    ContactGraph,
    read_contact_edit_plan,
    read_contact_surfaces,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.contact.schema import ContactAnchorRecord
from motion_edit.contact.surface_catalog import surfaces_from_obj_mesh_faces
from motion_edit.generation.lte_fullbody import _apply_anchor_edits_to_graph, _surface_transform_anchor_edits
from motion_edit.task_variants import create_approach_position_task_variant, create_height_task_variant


class TestHeightTaskVariant:
    def test_contact_follows_scaled_surface_without_relative_normal_offset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "box.obj"
            mesh.write_text(
                """v 0 0 0
v 0 0 1
v 1 0 0
v 1 0 1
v 0 1 0
v 0 1 1
v 1 1 0
v 1 1 1
f 2 4 6
f 4 8 6
""",
                encoding="utf-8",
            )
            surfaces = surfaces_from_obj_mesh_faces(
                motion_id="climb_00", obj_path=mesh, include_sides=False, include_ground=True
            )
            surface_catalog = root / "source-surfaces.jsonl"
            write_contact_surfaces(surface_catalog, surfaces)
            top = next(surface for surface in surfaces if surface.object_id != "terrain_ground")
            ground = next(surface for surface in surfaces if surface.object_id == "terrain_ground")
            graph = ContactGraph(
                motion_id="climb_00",
                anchors=[
                    ContactAnchorRecord(
                        motion_id="climb_00",
                        anchor_id="top-contact",
                        body="left_toe",
                        start_frame=2,
                        end_frame=28,
                        world_position=list(top.origin),
                        surface_id=top.surface_id,
                        surface_normal=list(top.normal),
                        surface_origin=list(top.origin),
                        surface_tangent_u=list(top.tangent_u),
                        surface_tangent_v=list(top.tangent_v),
                        surface_bounds=top.bounds,
                        surface_coordinates={"u": 0.0, "v": 0.0},
                    ),
                    ContactAnchorRecord(
                        motion_id="climb_00",
                        anchor_id="ground-contact",
                        body="right_toe",
                        start_frame=0,
                        end_frame=2,
                        world_position=list(ground.origin),
                        surface_id=ground.surface_id,
                        surface_coordinates={"u": 0.0, "v": 0.0},
                    ),
                ],
            )
            layers = root / "layers"
            write_contact_layer(layers / "contact/source", graph)
            artifacts = create_height_task_variant(
                motion_id="climb_00",
                source_motion_path=root / "clean.npz",
                contact_force_source_path=root / "force.npz",
                source_contact_layer="contact/source",
                source_surface_catalog=surface_catalog,
                source_terrain_mesh=mesh,
                height_scale=0.9,
                output_dir=root / "output",
                layers_root=layers,
            )
            plan = read_contact_edit_plan(artifacts.plan_path)
            target_surfaces = read_contact_surfaces(artifacts.surface_catalog_path)
            target_top = next(surface for surface in target_surfaces if surface.object_id != "terrain_ground")
            expanded_edits = _surface_transform_anchor_edits(plan, graph)
            edit = expanded_edits[0].to_dict()
            edited_graph = _apply_anchor_edits_to_graph(graph, expanded_edits)

            assert artifacts.surface_transform_count == 1
            assert artifacts.contact_episode_count == 1
            assert artifacts.anchor_constraint_count == 1
            assert plan.edits == []
            assert len(plan.surface_transforms) == 1
            assert abs(target_top.origin[2] - 0.9) < 1.0e-9
            assert edit["constraint_mode"] == "surface_transform"
            assert edit["surface_coordinates_before"] == edit["surface_coordinates_after"]
            assert abs(edit["delta_world"][2] + 0.1) < 1.0e-9
            assert edit["metadata"]["surface_transform"]["relative_surface_normal_offset_m"] == 0.0
            assert abs(edited_graph.anchors[0].world_position[2] - 0.9) < 1.0e-9
            assert edited_graph.anchors[0].surface_id == target_top.surface_id
            assert edited_graph.anchors[1].world_position == list(ground.origin)
            manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
            assert manifest["surface_transform_count"] == 1
            assert manifest["contact_episode_count"] == 1
            assert manifest["anchor_constraint_count"] == 1


class TestApproachPositionTaskVariant:
    def test_moves_final_ground_pose_away_without_moving_obstacle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "box.obj"
            mesh.write_text(
                """v 0 0 0
v 0 0 1
v 1 0 0
v 1 0 1
v 0 1 0
v 0 1 1
v 1 1 0
v 1 1 1
f 2 4 6
f 4 8 6
""",
                encoding="utf-8",
            )
            surfaces = surfaces_from_obj_mesh_faces(
                motion_id="climb_00", obj_path=mesh, include_sides=False, include_ground=True
            )
            surface_catalog = root / "source-surfaces.jsonl"
            write_contact_surfaces(surface_catalog, surfaces)
            top = next(surface for surface in surfaces if surface.object_id != "terrain_ground")
            ground = next(surface for surface in surfaces if surface.object_id == "terrain_ground")
            body_pos = np.zeros((160, 1, 3), dtype=np.float32)
            body_pos[:, 0, 1] = np.linspace(1.0, 0.0, 160)
            motion_path = root / "clean.npz"
            np.savez(motion_path, body_pos_w=body_pos, body_names=np.asarray(["pelvis"]))
            graph = ContactGraph(
                motion_id="climb_00",
                anchors=[
                    ContactAnchorRecord(
                        motion_id="climb_00",
                        anchor_id="last-left-step",
                        body="left_toe",
                        start_frame=132,
                        end_frame=141,
                        world_position=list(ground.origin),
                        surface_id=ground.surface_id,
                        surface_normal=list(ground.normal),
                        surface_origin=list(ground.origin),
                        surface_tangent_u=list(ground.tangent_u),
                        surface_tangent_v=list(ground.tangent_v),
                        surface_bounds=ground.bounds,
                        surface_coordinates={"u": 0.0, "v": 0.0},
                    ),
                    ContactAnchorRecord(
                        motion_id="climb_00",
                        anchor_id="first-box-contact",
                        body="left_hand",
                        start_frame=148,
                        end_frame=159,
                        world_position=list(top.origin),
                        surface_id=top.surface_id,
                        surface_normal=list(top.normal),
                        surface_origin=list(top.origin),
                        surface_tangent_u=list(top.tangent_u),
                        surface_tangent_v=list(top.tangent_v),
                        surface_bounds=top.bounds,
                        surface_coordinates={"u": 0.0, "v": 0.0},
                    ),
                ],
            )
            layers = root / "layers"
            write_contact_layer(layers / "contact/source", graph)

            artifacts = create_approach_position_task_variant(
                motion_id="climb_00",
                source_motion_path=motion_path,
                contact_force_source_path=root / "force.npz",
                source_contact_layer="contact/source",
                source_surface_catalog=surface_catalog,
                source_terrain_mesh=mesh,
                last_step_start_frame=103,
                pose_start_frame=139,
                first_obstacle_contact_frame=148,
                farther_distance_m=0.05,
                output_dir=root / "output",
                layers_root=layers,
            )

            plan = read_contact_edit_plan(artifacts.plan_path)
            assert artifacts.pose_edit_count == 1
            assert artifacts.ground_anchor_edit_count == 1
            assert artifacts.contact_episode_count == 1
            assert abs(np.linalg.norm(artifacts.translation_world) - 0.05) < 1.0e-9
            assert artifacts.translation_world[1] > 0.0
            assert plan.pose_edits[0]["affected_frames"] == [139, 148]
            assert plan.edits[0]["anchor_id"] == "last-left-step"
            assert plan.edits[0]["affected_frames"] == [139, 141]
            assert all(edit["anchor_id"] != "first-box-contact" for edit in plan.edits)

            lateral = create_approach_position_task_variant(
                motion_id="climb_00",
                source_motion_path=motion_path,
                contact_force_source_path=root / "force.npz",
                source_contact_layer="contact/source",
                source_surface_catalog=surface_catalog,
                source_terrain_mesh=mesh,
                last_step_start_frame=103,
                pose_start_frame=139,
                first_obstacle_contact_frame=148,
                farther_distance_m=0.0,
                lateral_left_m=0.05,
                output_dir=root / "output-lateral",
                plan_id="climb_00_approach_left_0p050",
                layers_root=layers,
            )
            assert abs(lateral.translation_world[0] - 0.05) < 1.0e-9
            assert abs(lateral.translation_world[1]) < 1.0e-9
            assert lateral.contact_episode_count == 1
