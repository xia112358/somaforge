"""Compare a fixed original pose against independently audited gradient probes."""
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import trimesh
import viser
import yourdfpy
from viser.extras import ViserUrdf

ROOT=Path.cwd()
from somaforge_core.robot_assets import canonical_g1_urdf_path, decode_robot_asset_json

parser=argparse.ArgumentParser()
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--port',type=int,default=8223)
parser.add_argument('--initial',default='metric_sum_sdf_sum_final')
parser.add_argument('--title',default='SDF 与共享退出面梯度对照')
args=parser.parse_args()
data=json.loads(args.report.read_text())
decode_robot_asset_json(data['robot_asset_json'],context='step14 gradient viewer')
records={r['label']:r for r in data['records']}
server=viser.ViserServer(host='127.0.0.1',port=args.port)
server.scene.set_up_direction('+z')
server.gui.add_markdown(f'## baseline1000 · {args.title}\n左：固定原姿态。右：离线优化结果；此页面仅回放，不启动训练。\n彩点为真实有效接触，红线为穿透法线，绿色箭头为左脚实际位移，可调整显示倍率。')
direction_methods={'普通 AL＋保护':'pose_al','姿态空间方向修正':'pose_projected','网络参数空间方向修正':'network_projected'}
is_direction=data.get('schema')=='constraint_direction_experiment_v1'
iteration=None
if is_direction:
    available={title:method for title,method in direction_methods.items() if method in data['results']}
    initial_method=next((title for title,method in available.items() if args.initial.startswith(method+'_')),next(iter(available)))
    choice=server.gui.add_dropdown('修正方法',options=tuple(available),initial_value=initial_method)
    def iteration_options():
        method=available[choice.value]
        options={'最终结果':method+'_final','初始姿态':method+'_initial'}
        intermediate=sorted((int(label[len(method+'_step'):]),label) for label in records if label.startswith(method+'_step') and label[len(method+'_step'):].isdigit())
        options.update({f'第 {step} 步':label for step,label in intermediate})
        return options
    iteration=server.gui.add_dropdown('迭代步（已保存）',options=tuple(iteration_options()),initial_value='最终结果')
    def selected_label():return iteration_options()[iteration.value]
    def selected_title():return f'{choice.value} · {iteration.value}'
else:
    choice=server.gui.add_dropdown('右侧实验姿态',options=tuple(records),initial_value=args.initial)
    def selected_label():return choice.value
    def selected_title():return choice.value
normal_toggle=server.gui.add_checkbox('显示穿透法线',initial_value=True)
opacity=server.gui.add_slider('箱体透明度',min=.05,max=1.,step=.05,initial_value=.35)
dx_toggle=server.gui.add_checkbox('显示左脚实际 dx',initial_value=True)
dx_scale=server.gui.add_slider('dx 显示倍率',min=1.,max=20.,step=1.,initial_value=3.)
details=server.gui.add_markdown('')
mesh=trimesh.load(data['terrain'],force='mesh')
roots=[];robots=[];markers=[];lines=[];terrains=[]
colors=np.asarray([[60,160,255],[255,145,60],[60,230,130],[250,90,190],[240,210,50],[150,115,250]],dtype=np.uint8)
for side in range(2):
    prefix=f'/side{side}'
    server.scene.add_frame(prefix,position=(0,(side-.5)*1.7,0),show_axes=False)
    roots.append(server.scene.add_frame(prefix+'/robot',show_axes=False))
    robots.append(ViserUrdf(server,yourdfpy.URDF.load(str(canonical_g1_urdf_path()),load_meshes=True,build_scene_graph=True),root_node_name=prefix+'/robot'))
    terrains.append(server.scene.add_mesh_simple(prefix+'/terrain',vertices=mesh.vertices,faces=mesh.faces,color=(130,150,165),opacity=.35,side='double'))
    server.scene.add_label(prefix+'/title','原始第14步' if side==0 else '优化实验',position=(.5,0,1.8))
    markers.append([server.scene.add_point_cloud(prefix+f'/contact{k}',points=np.zeros((1,3),np.float32),colors=colors[k],point_size=.025) for k in range(6)])
    lines.append(server.scene.add_line_segments(prefix+'/normals',points=np.zeros((1,2,3),np.float32),colors=(255,50,50),line_width=2))
import torch
from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics
from contact_solver.research.recovery_field import RecoveryGeometry
fk=CanonicalG1ForwardKinematics().double()
geometry=RecoveryGeometry(data['terrain'],fk,samples=128)
with torch.no_grad():
    original_points,_=geometry.evaluate(torch.tensor(records['original']['q'],dtype=torch.float64))
    original_points=original_points[geometry.foot_ids].reshape(-1,3)[::8].numpy()
dx_lines=server.scene.add_line_segments('/side1/dx',points=np.zeros((1,2,3),np.float32),colors=(40,240,90),line_width=3)
indices=[data['joint_names'].index(n) for n in robots[0].get_actuated_joint_limits()]
parts=['左脚','右脚','左手','右手','左膝','右膝']

def update(_=None):
    text=[]
    for side,row in enumerate((records['original'],records[selected_label()])):
        q=np.asarray(row['q']);roots[side].position=q[:3];roots[side].wxyz=q[3:7]
        robots[side].update_cfg(q[7:][indices])
        points=np.asarray(row['contact_position_w'],np.float32)
        for k,m in enumerate(markers[side]):
            m.visible=bool(row['actual_contact'][k])
            if m.visible:m.points=points[k:k+1]
        p=row['penetrating_pairs'];start=np.asarray(p['geometry_point1_w'],np.float32)
        normal=np.asarray(p['normal_w'],np.float32)
        if len(start):lines[side].points=np.stack((start,start+.08*normal),axis=1)
        lines[side].visible=bool(normal_toggle.value and len(start))
        terrains[side].opacity=float(opacity.value)
        geom=row['geometry_diagnostic']['left_ankle_roll_link']
        active='、'.join(n for n,v in zip(parts,row['actual_contact']) if v) or '无'
        text.append(f"**{'原始' if side==0 else selected_title()}**\n\nNewton 全身最大负距离：{row['full_depth_cm']:.3f} cm；双足：{row['feet_depth_cm']:.3f} cm。\n\n左脚网格诊断：{geom['inside_vertex_count']} 个顶点在箱内，最大顶点最近出界距离 {geom['max_vertex_nearest_exit_cm']:.3f} cm（不是接触真值或整形状MTD）。\n\n有效接触：{active}。")
    with torch.no_grad():
        moved,_=geometry.evaluate(torch.tensor(records[selected_label()]['q'],dtype=torch.float64))
        moved=moved[geometry.foot_ids].reshape(-1,3)[::8].numpy()
    displacement=moved-original_points
    ends=original_points+float(dx_scale.value)*displacement
    vectors=ends-original_points
    length=np.linalg.norm(vectors,axis=1,keepdims=True)
    direction=vectors/np.maximum(length,1e-12)
    perp=np.cross(direction,np.array([0.,1.,0.]))
    perp/=np.maximum(np.linalg.norm(perp,axis=1,keepdims=True),1e-12)
    arrow_size=np.minimum(.025,length*.25)
    wing1=ends-direction*arrow_size+perp*arrow_size*.5
    wing2=ends-direction*arrow_size-perp*arrow_size*.5
    dx_lines.points=np.concatenate((np.stack((original_points,ends),1),np.stack((ends,wing1),1),np.stack((ends,wing2),1))).astype(np.float32)
    dx_lines.visible=bool(dx_toggle.value)
    selected=records[selected_label()]
    extra=f"\n\n实际左脚材料点平均 dx（cm）：{np.round(displacement.mean(0)*100,3).tolist()}；箭头仅显示放大 {dx_scale.value:.0f} 倍。"
    if 'shape_plane_violation_cm' in selected:
        extra+=f"\n\n整形状分离面违反：{selected['shape_plane_violation_cm']:.3f} cm；原接触保留：{selected['all_required_kept']}；静态验收：{selected['static_recovery_pass']}。"
    details.content='\n\n---\n\n'.join(text)+extra
if is_direction:
    @choice.on_update
    def change_method(_):
        iteration.options=tuple(iteration_options())
        iteration.value='最终结果'
        update()
    iteration.on_update(update)
else:
    choice.on_update(update)
normal_toggle.on_update(update);opacity.on_update(update);dx_toggle.on_update(update);dx_scale.on_update(update);update()
@server.on_client_connect
def connect(client):
    client.camera.position=(3.8,-3,2.)
    client.camera.look_at=(.55,0,.65)
    client.camera.fov=np.deg2rad(45.)
print(f'READY http://127.0.0.1:{args.port}',flush=True)
while True:time.sleep(.05)
