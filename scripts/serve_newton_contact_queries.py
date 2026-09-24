"""Dedicated contact-query worker initialized from a policy's actual config.

No policy actions, training or integration. A binding references the exact
initialized model fingerprint and an explicit surface catalog; unknown scenes
are rejected instead of rebuilding an approximate collision world.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


@dataclass
class Config:
    checkpoint: Path
    binding: Path
    inspection_output: Path
    port: int = 8099
    inspect_only: bool = False
    probe_motion: Path | None = None
    motion_manifest: Path | None = None
    create_native_binding: bool = False
    relabel_motion: Path | None = None
    labels_output: Path | None = None
    query_nconmax: int | None = None
    query_njmax: int | None = None
    geometry_output: Path | None = None
    capture_contact_sources: bool = False
    relabel_jobs: Path | None = None
    relabel_continue_on_error: bool = False
    query_worlds: int = 1
    query_poses: Path | None = None
    query_output: Path | None = None
    query_repeats: int = 3
    audit_device_reader: bool = False
    tensor_auth: Path | None = None


def inspect_model(model):
    """Fingerprint realized collision settings, geometry and joint mapping."""
    import numpy as np
    digest = hashlib.sha256()
    result = dict(body_labels=list(model.body_label), shape_labels=list(model.shape_label),
                  joint_labels=list(model.joint_label))
    for key in ('shape_body', 'shape_type', 'shape_transform', 'shape_scale', 'shape_flags',
                'shape_margin', 'shape_gap', 'shape_collision_group', 'joint_q_start', 'joint_type',
                'joint_parent', 'joint_child', 'joint_X_p', 'joint_X_c'):
        value = getattr(model, key, None)
        if value is None:
            raise ValueError(f'Cannot fingerprint missing Newton model field {key}')
        array = value.numpy()
        digest.update(key.encode()); digest.update(array.tobytes())
        result[key] = array.tolist()
    digest.update(json.dumps(result, sort_keys=True).encode())
    digest.update(repr(sorted(model.shape_collision_filter_pairs)).encode())
    for source in model.shape_source:
        if source is not None and hasattr(source, 'vertices'):
            digest.update(np.asarray(source.vertices).tobytes())
            digest.update(np.asarray(source.indices).tobytes())
    result['model_fingerprint'] = digest.hexdigest()
    result['world_count'] = int(model.world_count)
    for key in ('body_world', 'shape_world', 'joint_world'):
        value = getattr(model, key, None)
        if value is not None:
            result[key] = value.numpy().tolist()
    from scipy.spatial.transform import Rotation
    result['terrain_mesh_bounds'] = []
    for i, source in enumerate(model.shape_source):
        if int(result['shape_body'][i]) >= 0 or source is None or not hasattr(source, 'vertices'):
            continue
        transform = np.asarray(result['shape_transform'][i])
        vertices = np.asarray(source.vertices)*result['shape_scale'][i]
        vertices = Rotation.from_quat(transform[3:]).apply(vertices)+transform[:3]
        result['terrain_mesh_bounds'].append(dict(shape=i, minimum=vertices.min(0).tolist(),
            maximum=vertices.max(0).tolist(), z_levels=np.unique(np.round(vertices[:,2],5)).tolist()))
    return result


def native_binding(model, info):
    """Surface planes from actual static triangle meshes, not a second model."""
    import numpy as np
    import re
    from scipy.spatial.transform import Rotation
    body_env = {i: int(info.get('body_world', [])[i]) if 'body_world' in info else int(match[1]) for i,label in enumerate(model.body_label)
                if (match := re.search(r'/env_(\d+)/Robot/',label))}
    if set(body_env.values()) != set(range(max(1, int(model.world_count)))):
        raise ValueError('Native worker requires one canonical robot in each Newton world')
    planes_by_shape = {}; all_planes = set(); triangles_by_shape = {}; indices_by_shape = {}
    for i,body in enumerate(info['shape_body']):
        if body in body_env:
            continue
        source = model.shape_source[i]
        if body >= 0 or source is None or not hasattr(source,'vertices'):
            raise ValueError('Native catalog currently requires static triangle-mesh terrain')
        transform=np.asarray(info['shape_transform'][i])
        v=Rotation.from_quat(transform[3:]).apply(np.asarray(source.vertices)*info['shape_scale'][i])+transform[:3]
        triangles=v[np.asarray(source.indices).reshape(-1,3)]
        normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        length=np.linalg.norm(normal,axis=-1);valid=length>1e-10
        normal=normal[valid]/length[valid,None]
        offset=(normal*triangles[valid,0]).sum(-1)
        keys=[tuple(np.round(np.r_[n,d],8)) for n,d in zip(normal,offset)]
        planes=set(keys)
        grouped={p:[] for p in planes}
        grouped_indices={p:[] for p in planes}
        for plane,triangle,index in zip(keys,triangles[valid],np.flatnonzero(valid)):
            grouped[plane].append(triangle.tolist());grouped_indices[plane].append(int(index))
        triangles_by_shape[i]=grouped
        indices_by_shape[i]=grouped_indices
        planes_by_shape[i]=planes;all_planes.update(planes)
    # Stable ground/top/other ordering. Multiple top heights stay distinct.
    ordered=sorted(all_planes,key=lambda p:(0 if p==(0.,0.,1.,0.) else 1 if p[:3]==(0.,0.,1.) else 2,p))
    ids={plane:i for i,plane in enumerate(ordered)}
    return dict(model_fingerprint=info['model_fingerprint'],scene=None,
        body_env=body_env,shape_surface={i:[dict(surface=ids[p],normal_w=p[:3],plane_offset=p[3],
            triangles_w=triangles_by_shape[i][p],triangle_indices=indices_by_shape[i][p],
            attribution_schema='native_triangle_nearest_v1')
            for p in sorted(planes)] for i,planes in planes_by_shape.items()},
        surface_catalog=[dict(surface=ids[p],normal_w=p[:3],plane_offset=p[3]) for p in ordered])


def main():
    import tyro
    from dataclasses import replace
    from holosoma.utils.sim_utils import (parse_isaaclab_launcher_args, setup_simulation_environment,
        sync_launcher_headless_config, close_simulation_app)
    from holosoma.utils.eval_utils import CheckpointConfig, load_saved_experiment_config
    from somaforge_core.robot_assets import canonical_g1_asset_metadata
    from somaforge_core.motion_schema import G1_29DOF_JOINT_ORDER
    from somaforge_core.newton_contact_query import DedicatedNewtonSceneQuery
    from somaforge_core.newton_contacts import SCHEMA
    official = parse_isaaclab_launcher_args('Dedicated Newton contact queries')
    cfg = tyro.cli(Config)
    import os
    # Queries run outside the simulation graph. Lazy buffers allocated during
    # capture are not valid for ad-hoc conversion/constraint launches.
    os.environ['HOLOSOMA_NEWTON_USE_CUDA_GRAPH'] = '0'
    saved, _ = load_saved_experiment_config(CheckpointConfig(checkpoint=str(cfg.checkpoint)))
    saved = saved.get_eval_config(saved.evaluation)
    original_capacity = dict(nconmax=saved.simulator.config.mujoco_warp.nconmax_per_env,
                             njmax=saved.simulator.config.mujoco_warp.njmax_per_env)
    if cfg.query_nconmax is not None or cfg.query_njmax is not None:
        settings=saved.simulator.config.mujoco_warp
        settings=replace(settings,nconmax_per_env=cfg.query_nconmax or settings.nconmax_per_env,
                         njmax_per_env=cfg.query_njmax or settings.njmax_per_env)
        saved=replace(saved,simulator=replace(saved.simulator,config=replace(saved.simulator.config,mujoco_warp=settings)))
    if cfg.motion_manifest is not None:
        from holosoma.utils.motion_matched_config import _apply_motion_matched_manifest_to_command
        manifest = str(cfg.motion_manifest.resolve())
        saved = replace(saved, command=_apply_motion_matched_manifest_to_command(saved.command,manifest),
            terrain=replace(saved.terrain, terrain_term=replace(saved.terrain.terrain_term,motion_matched_manifest=manifest)))
    if cfg.query_worlds < 1:
        raise ValueError('query_worlds must be positive')
    saved = replace(saved, training=replace(saved.training, num_envs=cfg.query_worlds))
    saved = sync_launcher_headless_config(saved, official)
    app = None
    try:
        env, device, app = setup_simulation_environment(saved, device=official.device, launcher_args=official)
        from isaaclab_newton.physics.newton_manager import NewtonManager as manager
        model = manager._model
        info = inspect_model(model)
        from somaforge_core.newton_runtime_compat import runtime_provenance
        info['newton_runtime'] = runtime_provenance()
        info['robot_asset'] = canonical_g1_asset_metadata()
        if cfg.geometry_output is not None:
            from motion_edit.generation.native_geometry_release import export_geometry
            geometry = export_geometry(model, manager._solver, info)
            with cfg.geometry_output.open('x') as stream:
                json.dump(geometry, stream)
        info['policy_solver_capacity'] = original_capacity
        info['query_solver_capacity'] = dict(nconmax=saved.simulator.config.mujoco_warp.nconmax_per_env,
                                             njmax=saved.simulator.config.mujoco_warp.njmax_per_env)
        if cfg.probe_motion is not None:
            import newton
            import warp as wp
            wp.config.verify_cuda = True
            import numpy as np
            from somaforge_core.robot_assets import decode_robot_asset_json
            from somaforge_core.newton_contacts import snapshot_solver_contacts
            with np.load(cfg.probe_motion, allow_pickle=False) as motion:
                decode_robot_asset_json(motion['robot_asset_json'], context=str(cfg.probe_motion))
                if tuple(motion['joint_names'].astype(str)) != G1_29DOF_JOINT_ORDER:
                    raise ValueError('Probe motion joint order differs')
                poses = motion['joint_pos'].copy()
            joint_names = [x.rsplit('/',1)[-1] for x in model.joint_label]
            indices = [info['joint_q_start'][joint_names.index(x)] for x in G1_29DOF_JOINT_ORDER]
            roots = [info['joint_q_start'][i] for i,k in enumerate(info['joint_type']) if k == int(newton.JointType.FREE)]
            if len(roots) != 1:
                raise ValueError('Probe requires one free root')
            state = model.state(); contacts = manager._collision_pipeline.contacts()
            rows = []
            for frame in np.unique(np.linspace(0,len(poses)-1,3).astype(int)):
                q = poses[frame]
                coords = model.joint_q.numpy().copy(); root=roots[0]
                coords[root:root+3] = q[:3]; coords[root+3:root+7] = q[[4,5,6,3]]; coords[indices] = q[7:]
                state.joint_q.assign(coords); state.joint_qd.zero_()
                newton.eval_fk(model,state.joint_q,state.joint_qd,state)
                print('probe FK complete', int(frame), flush=True)
                manager._collision_pipeline.collide(state,contacts)
                print('probe collide complete', int(contacts.rigid_contact_count.numpy()[0]), flush=True)
                solver=manager._solver
                solver._update_mjc_data(solver.mjw_data,model,state)
                print('probe state conversion complete', flush=True)
                if solver.newton_shape_to_mjc_geom is None:
                    solver._create_inverse_shape_mapping()
                size=int(contacts.rigid_contact_count.numpy()[0])
                shape_pairs=np.stack((contacts.rigid_contact_shape0.numpy()[:size],contacts.rigid_contact_shape1.numpy()[:size]),-1)
                mapped=solver.newton_shape_to_mjc_geom.numpy()[shape_pairs]
                print('probe mapping', json.dumps(dict(shape_pairs=shape_pairs.tolist(),mapped=mapped.tolist(),
                    geom_count=len(solver.mjw_model.geom_bodyid),body_count=model.body_count,
                    world_count=model.world_count,nworld=solver.mjw_data.nworld,
                    buffers={key:getattr(contacts,key).shape if getattr(contacts,key) is not None else None
                             for key in ('rigid_contact_stiffness','rigid_contact_damping','rigid_contact_friction')})),flush=True)
                if (mapped < 0).any() or (mapped >= len(solver.mjw_model.geom_bodyid)).any():
                    raise ValueError('Newton collision candidates contain unmapped MuJoCo shapes')
                solver._convert_contacts_to_mjwarp(model,state,contacts)
                print('probe contacts conversion complete', int(solver.mjw_data.nacon.numpy()[0]), flush=True)
                import warp as wp
                with wp.ScopedDevice(model.device):
                    solver._mujoco_warp.fwd_position(solver.mjw_model,solver.mjw_data,factorize=False)
                    wp.synchronize_device(model.device)
                snapshot=snapshot_solver_contacts(solver,model)
                if not np.array_equal(coords,state.joint_q.numpy()):
                    raise AssertionError('Contact query changed q')
                rows.append(dict(frame=int(frame),candidate_count=int(snapshot['count']),
                    active=int(snapshot['active'].sum()),allocated=int(snapshot['constraint_allocated'].sum()),
                    q_unchanged=True))
            info['fixed_q_probe']=dict(motion=str(cfg.probe_motion),coordinate_convention='input world coordinates unchanged',rows=rows)
        cfg.inspection_output.parent.mkdir(parents=True, exist_ok=True)
        with cfg.inspection_output.open('x') as stream:
            json.dump(info, stream, indent=2)
        if cfg.create_native_binding:
            with cfg.binding.open('x') as stream:
                json.dump(native_binding(model,info),stream,indent=2)
        if cfg.inspect_only:
            return
        binding = json.loads(cfg.binding.read_text())
        if binding['model_fingerprint'] != info['model_fingerprint']:
            raise ValueError('Surface binding belongs to a different realized Newton model')
        labels = [label.rsplit('/', 1)[-1] for label in model.joint_label]
        import newton
        indices, roots = [], []
        for world in range(cfg.query_worlds):
            members = [i for i in range(len(labels)) if info['joint_world'][i] == world]
            world_indices = []
            for name in G1_29DOF_JOINT_ORDER:
                matches = [i for i in members if labels[i] == name]
                if len(matches) != 1:
                    raise ValueError(f'Expected unique joint {name} in world {world}')
                world_indices.append(int(info['joint_q_start'][matches[0]]))
            free = [i for i in members if info['joint_type'][i] == int(newton.JointType.FREE)]
            if len(free) != 1:
                raise ValueError('Expected one canonical free robot root per world')
            indices.append(world_indices)
            roots.append(int(info['joint_q_start'][free[0]]))
        query = DedicatedNewtonSceneQuery(model, manager._solver, manager._collision_pipeline,
            scene=binding['scene'], body_env={int(k): int(v) for k,v in binding['body_env'].items()},
            shape_surface={int(k): v for k,v in binding['shape_surface'].items()},
            joint_q_indices=indices[0] if cfg.query_worlds == 1 else indices,
            root_q_start=roots[0] if cfg.query_worlds == 1 else roots, model_provenance=info,
            capture_contact_sources=cfg.capture_contact_sources, audit_device_reader=cfg.audit_device_reader)
        if cfg.tensor_auth is not None:
            from somaforge_core.newton_tensor_transport import serve_tensor_queries
            serve_tensor_queries(query, cfg.port, cfg.tensor_auth.read_bytes())
            return
        if cfg.query_poses is not None:
            import numpy as np
            import time
            import warp as wp
            from somaforge_core.robot_assets import decode_robot_asset_json
            if cfg.query_output is None or cfg.query_repeats < 1:
                raise ValueError('Offline query requires output and positive repeats')
            with np.load(cfg.query_poses, allow_pickle=False) as poses:
                decode_robot_asset_json(poses['robot_asset_json'], context=str(cfg.query_poses))
                qpos = poses['qpos'].copy()
            if qpos.ndim != 2 or qpos.shape[1] != 36 or not len(qpos) or not np.isfinite(qpos).all():
                raise ValueError('Expected nonempty finite canonical qpos [N,36]')
            query(qpos[:min(len(qpos), cfg.query_worlds)], None)
            elapsed = []
            for _ in range(cfg.query_repeats):
                wp.synchronize_device(model.device)
                start = time.perf_counter()
                result = query(qpos, None)
                wp.synchronize_device(model.device)
                elapsed.append(time.perf_counter()-start)
            with cfg.query_output.open('x') as stream:
                json.dump(dict(seconds=elapsed, batch=len(qpos), worlds=cfg.query_worlds,
                    result=result), stream)
            if cfg.audit_device_reader:
                import torch
                device_q = torch.as_tensor(qpos, device=str(model.device))
                device_elapsed, device_masks, device_surfaces = [], [], []
                for repeat in range(cfg.query_repeats):
                    wp.synchronize_device(model.device)
                    start = time.perf_counter()
                    for chunk in device_q.split(cfg.query_worlds):
                        observed = query.query_device(chunk)
                        if repeat == cfg.query_repeats-1:
                            device_masks.append(observed['contact_part_mask'].clone())
                            device_surfaces.append(observed['contact_surface'].clone())
                    wp.synchronize_device(model.device)
                    device_elapsed.append(time.perf_counter()-start)
                with cfg.query_output.with_suffix('.device.json').open('x') as stream:
                    json.dump(dict(seconds=device_elapsed, batch=len(qpos), worlds=cfg.query_worlds,
                        contact_part_mask=torch.cat(device_masks).cpu().tolist(),
                        contact_surface=torch.cat(device_surfaces).cpu().tolist(),
                        contract='GPU q, one batched fixed-q pass, GPU raw contacts and effective masks; CPU error flags only'), stream)
            return
        if cfg.relabel_motion is not None or cfg.relabel_jobs is not None:
            if cfg.relabel_motion is not None and cfg.relabel_jobs is not None:
                raise ValueError('Choose relabel-motion or relabel-jobs, not both')
            if cfg.relabel_jobs is None:
                if cfg.labels_output is None:
                    raise ValueError('relabel-motion requires labels-output')
                jobs = [dict(motion=str(cfg.relabel_motion), labels_output=str(cfg.labels_output))]
            else:
                batch = json.loads(cfg.relabel_jobs.read_text())
                if batch['model_fingerprint'] != info['model_fingerprint']:
                    raise ValueError('Relabel batch belongs to a different native scene')
                jobs = batch['jobs']
                targets = [str(Path(job['labels_output']).resolve()) for job in jobs]
                if not jobs or len(set(targets)) != len(targets) or any(Path(p).exists() for p in targets):
                    raise ValueError('Relabel batch needs nonempty, distinct, new outputs')
            from somaforge_core.newton_contact_query import install_contact_query
            from relabel_newton_motion import relabel
            import time
            install_contact_query(query)
            failed_jobs = []
            try:
                for job in jobs:
                    started = time.perf_counter()
                    try:
                        relabel(Path(job['motion']), cfg.binding, Path(job['labels_output']))
                    except Exception as exc:
                        if not cfg.relabel_continue_on_error:
                            raise
                        failed_jobs.append(dict(motion=job['motion'],error=f'{type(exc).__name__}: {exc}'))
                        print('native-relabel-job ' + json.dumps(dict(**failed_jobs[-1],status='failed',
                            elapsed_seconds=time.perf_counter()-started)), flush=True)
                    else:
                        print('native-relabel-job ' + json.dumps(dict(motion=job['motion'],status='complete',
                            elapsed_seconds=time.perf_counter()-started)), flush=True)
            finally:
                install_contact_query(None)
            if failed_jobs:
                raise RuntimeError(f'{len(failed_jobs)} native relabel jobs failed; these outputs are not validated')
            return

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    size = int(self.headers.get('Content-Length', 0))
                    if not 0 < size <= 32*1024*1024:
                        raise ValueError('Invalid query size')
                    import numpy as np
                    value = json.loads(self.rfile.read(size))
                    result = query(np.asarray(value['qpos'], np.float32), None if value['scene'] is None else
                                   [np.asarray(x, np.float32) for x in value['scene']])
                except Exception as exc:
                    result = dict(error=f'{type(exc).__name__}: {exc}')
                data = json.dumps(result).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)

        with HTTPServer(('127.0.0.1', cfg.port), Handler) as server:
            print(json.dumps(dict(ready=True, port=cfg.port, schema=SCHEMA,
                                  model_fingerprint=info['model_fingerprint'])), flush=True)
            server.serve_forever()
    except Exception:
        # Kit shutdown may exit before Python renders an uncaught traceback.
        import traceback
        traceback.print_exc()
        import sys
        sys.stderr.flush()
        raise
    finally:
        if app is not None:
            close_simulation_app(app)


if __name__ == '__main__':
    main()
