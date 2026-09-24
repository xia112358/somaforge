#!/usr/bin/env python3
"""Play a saved predictor-only closed loop beside its reference endpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path.cwd().resolve()
if not (ROOT / "packages/somaforge_core/somaforge_core").is_dir():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/somaforge_core"))

from somaforge_core.robot_assets import canonical_g1_urdf_path, decode_robot_asset_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path,
        default=ROOT / "tmp/temporal207_hold_compact_v4/manifest.json",
    )
    parser.add_argument("--port", type=int, default=8194)
    args = parser.parse_args()

    report = json.loads(args.report.read_text())
    projected = report.get("schema") == "gt_topology_whole_surface_true_closed_loop_v1"
    if report.get("schema") not in {
        "full_interaction_predictor_only_closed_loop_v1",
        "interaction_predictor_only_closed_loop_v2",
        "gt_topology_whole_surface_true_closed_loop_v1",
    }:
        raise ValueError("expected a predictor-only or projected closed-loop report")
    checkpoint = __import__("torch").load(
        report["checkpoint"], map_location="cpu", weights_only=False
    )
    decode_robot_asset_json(checkpoint["robot_asset_json"], context="predictor-only viewer")
    if projected:
        manifest_path = Path(report.get("manifest", args.manifest))
    elif report.get("schema") == "interaction_predictor_only_closed_loop_v2":
        manifest_path = Path(report["data_contract"]["manifest"])
    else:
        manifest_path = args.manifest
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["motion_files"][int(report["motion_id"])]
    terrain = next(
        row["terrain_file"] for row in manifest["terrains"]
        if row["terrain_id"] == entry["terrain_id"]
    )

    import trimesh
    import viser
    import yourdfpy
    from viser.extras import ViserUrdf

    server = viser.ViserServer(host="127.0.0.1", port=args.port)
    server.scene.set_up_direction("+z")
    server.gui.add_markdown(
        (
            f"## Predictor＋Newton 接触实现（{len(report['events'])} 个连续事件）\n"
            "左：预测计划经 Newton projector 实现后的关键帧；右：示范参考。无 Infiller 和中间插值。\n"
            "左侧彩点是投影后重新查询得到的 Newton 实际有效接触。"
            if projected else
            "## 纯 Predictor 连续递推\n"
            "左：网络原始递推；右：示范参考。无 Infiller、projector、插值或穿透修正。\n"
            "左侧彩点是每步重新查询得到的 Newton 实际有效接触。"
        )
    )
    step = server.gui.add_slider(
        "递推步骤（0=起姿）", min=0, max=len(report["events"]), step=1, initial_value=0
    )
    play = server.gui.add_checkbox("播放", initial_value=True)
    speed = server.gui.add_slider("每秒事件", min=0.2, max=3.0, step=0.2, initial_value=1.0)
    details = server.gui.add_markdown("")

    mesh = trimesh.load(terrain, force="mesh")
    offsets = (np.asarray((0.0, -1.6, 0.0)), np.asarray((0.0, 1.6, 0.0)))
    labels = (
        ("预测＋Newton实现", "示范参考（仅对照）")
        if projected else ("纯 Predictor", "示范参考（仅对照）")
    )
    roots, robots = [], []
    markers = []
    colors = np.asarray(
        ((60, 160, 255), (255, 145, 60), (60, 230, 130),
         (250, 90, 190), (240, 210, 50), (150, 115, 250)),
        dtype=np.uint8,
    )
    for side in range(2):
        prefix = f"/side{side}"
        server.scene.add_frame(prefix, position=offsets[side], show_axes=False)
        roots.append(server.scene.add_frame(prefix + "/robot", show_axes=False))
        robot = ViserUrdf(
            server,
            yourdfpy.URDF.load(
                str(canonical_g1_urdf_path()), load_meshes=True, build_scene_graph=True
            ),
            root_node_name=prefix + "/robot",
        )
        robots.append(robot)
        server.scene.add_mesh_simple(
            prefix + "/terrain", vertices=mesh.vertices, faces=mesh.faces,
            color=(130, 150, 165), opacity=0.65, side="double",
        )
        server.scene.add_label(prefix + "/title", labels[side], position=(0.0, 0.0, 2.1))
        if side == 0:
            markers = [
                server.scene.add_point_cloud(
                    prefix + f"/contact{part}", points=np.zeros((1, 3), np.float32),
                    colors=colors[part], point_size=0.04,
                )
                for part in range(6)
            ]
    indices = [report["joint_names"].index(name) for name in robots[0].get_actuated_joint_limits()]
    predicted = report["visualization"]["predicted_q_world"]
    reference = report["visualization"]["reference_q_world"]

    def update(_=None) -> None:
        frame = int(step.value)
        for side, sequence in enumerate((predicted, reference)):
            qpos = np.asarray(sequence[frame], dtype=np.float32)
            roots[side].position = qpos[:3]
            roots[side].wxyz = qpos[3:7]
            robots[side].update_cfg(qpos[7:][indices])
        for marker in markers:
            marker.visible = False
        if frame:
            event = report["events"][frame - 1]
            mask = np.asarray(event["actual_contact"], dtype=bool)
            contact_frame = frame if projected else frame - 1
            points = np.asarray(
                report["visualization"]["actual_contact_position_w"][contact_frame],
                dtype=np.float32,
            )
            for part, marker in enumerate(markers):
                marker.visible = bool(mask[part])
                if mask[part]:
                    marker.points = points[part : part + 1]
            if projected:
                details.content = (
                    f"步骤 {frame}/{len(report['events'])} · 帧 {event['frames'][0]}→{event['frames'][1]}  \n"
                    f"计划与示范一致：{event['predicted_plan_matches_gt']} · 预测计划实际实现："
                    f"{event['converged']} · 穿透 {event['projected_penetration_cm']:.6f} cm  \n"
                    f"root 参考误差 {event['projected_root_error_cm']:.2f} cm · body 参考误差 "
                    f"{event['projected_body_error_cm']:.2f} cm"
                )
            else:
                details.content = (
                    f"步骤 {frame}/{len(report['events'])} · 帧 {event['frames'][0]}→{event['frames'][1]}"
                    f" · {event['terminal_event']}  \n"
                    f"计划正确：{event['predicted_plan_matches_gt']} · 计划被姿态实现："
                    f"{event['predicted_plan_realized']} · 实际接触正确："
                    f"{event['actual_contact_matches_gt']}  \n"
                    f"root 误差 {event['root_error_cm']:.2f} cm · body 误差 "
                    f"{event['body_error_cm']:.2f} cm"
                )
        else:
            details.content = f"步骤 0/{len(report['events'])} · 相同真实起姿"

    step.on_update(update)
    update()

    @server.on_client_connect
    def connected(client):
        client.camera.look_at = (0.7, 0.0, 0.8)
        client.camera.position = (4.5, 5.0, 3.0)
        print("BROWSER_CONNECTED", client.client_id, flush=True)

    print(f"READY http://127.0.0.1:{args.port}", flush=True)
    last = time.monotonic()
    remainder = 0.0
    while True:
        now = time.monotonic()
        delta = now - last
        last = now
        if play.value:
            remainder += delta * float(speed.value)
            if remainder >= 1.0:
                step.value = (int(step.value) + 1) % (len(report["events"]) + 1)
                remainder %= 1.0
        else:
            remainder = 0.0
        time.sleep(0.02)


if __name__ == "__main__":
    main()
