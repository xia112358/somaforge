"""Compare saved actual endpoints and their raw extra predictions, without simulation."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import trimesh
import viser
import yourdfpy
from viser.extras import ViserUrdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/somaforge_core'))
from somaforge_core.robot_assets import canonical_g1_urdf_path, decode_robot_asset_json

paths = ['tmp/baseline1000_motion8_raw29_20260925/report.json',
         'tmp/full1000_regionfix1000_motion8_raw27_20260925/report.json']
reports = [json.loads((ROOT / p).read_text()) for p in paths]
ends = [19, 17]
names = ['旧 baseline1000', '新 corrected1000']
parts = ['左脚', '右脚', '左手', '右手', '左膝', '右膝']
colors = np.array([[60,160,255],[255,145,60],[60,230,130],
                   [250,90,190],[240,210,50],[150,115,250]], dtype=np.uint8)
server = viser.ViserServer(host='127.0.0.1', port=8210)
server.scene.set_up_direction('+z')
server.gui.add_markdown('## 两版实际末态对比\n左：旧1000第19次输出；右：新1000第17次输出。\n'
    '默认停在末态。滑块可查看之后10次原始递推。两版末态不是同一物理时刻。\n'
    '机器人与各自地形一起平移并排展示；没有对齐或修正机器人姿态。彩点为已保存的 Newton 有效接触。')
step = server.gui.add_slider('末态之后额外递推次数', min=0, max=10, step=1, initial_value=0)
play = server.gui.add_checkbox('播放', initial_value=False)
details = server.gui.add_markdown('')
robots, roots, markers, indices = [], [], [], []
for side, report in enumerate(reports):
    checkpoint = torch.load(report['checkpoint'], map_location='cpu', weights_only=False)
    decode_robot_asset_json(checkpoint['robot_asset_json'], context='actual endpoint comparison')
    del checkpoint
    manifest = json.loads(Path(report['data_contract']['manifest']).read_text())
    entry = manifest['motion_files'][int(report['motion_id'])]
    terrain = next(x['terrain_file'] for x in manifest['terrains'] if x['terrain_id'] == entry['terrain_id'])
    mesh = trimesh.load(terrain, force='mesh')
    prefix = f'/side{side}'
    server.scene.add_frame(prefix, position=(0, -1.6 if side == 0 else 1.6, 0), show_axes=False)
    roots.append(server.scene.add_frame(prefix+'/robot', show_axes=False))
    robot = ViserUrdf(server, yourdfpy.URDF.load(str(canonical_g1_urdf_path()),
        load_meshes=True, build_scene_graph=True), root_node_name=prefix+'/robot')
    robots.append(robot)
    indices.append([report['joint_names'].index(n) for n in robot.get_actuated_joint_limits()])
    server.scene.add_mesh_simple(prefix+'/terrain', vertices=mesh.vertices, faces=mesh.faces,
        color=(130,150,165), opacity=0.65, side='double')
    server.scene.add_label(prefix+'/title', names[side], position=(0,-0.8,1.7))
    markers.append([server.scene.add_point_cloud(prefix+f'/contact{k}',
        points=np.zeros((1,3),np.float32), colors=colors[k], point_size=0.035) for k in range(6)])

def update(_=None):
    lines = []
    for side, report in enumerate(reports):
        frame = ends[side]+int(step.value)
        q = np.asarray(report['visualization']['predicted_q_world'][frame])
        roots[side].position = q[:3]
        roots[side].wxyz = q[3:7]
        robots[side].update_cfg(q[7:][indices[side]])
        mask = report['events'][frame-1]['actual_contact']
        points = np.asarray(report['visualization']['actual_contact_position_w'][frame-1],np.float32)
        for k, marker in enumerate(markers[side]):
            marker.visible = bool(mask[k])
            if mask[k]: marker.points = points[k:k+1]
        lines.append(f"**{names[side]} · 第{frame}次输出**：" + ('、'.join(p for p,m in zip(parts,mask) if m) or '无有效接触'))
    details.content = '\n\n'.join(lines)
step.on_update(update)
update()

@server.on_client_connect
def connect(client):
    client.camera.look_at = (0.25,-0.8,0.7)
    client.camera.position = (4.8,-0.8,2.7)

print('READY http://127.0.0.1:8210', flush=True)
last = time.monotonic()
while True:
    if play.value and time.monotonic()-last >= 1:
        step.value = (int(step.value)+1)%11
        last = time.monotonic()
    elif not play.value:
        last = time.monotonic()
    time.sleep(0.03)
