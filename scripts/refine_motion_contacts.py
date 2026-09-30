"""Refine one canonical motion with the shared regional contact objective.

Orchestrates the existing AppLauncher Newton worker; never starts a trainer.
All outputs are candidates and require fresh downstream trajectory validation.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def main():
    from motion_edit.generation.native_contact_refinement import (
        RefinementConfig, REFINEMENT_OBJECTIVE_SCHEMA)
    defaults = RefinementConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('motion', 'events', 'taskspace', 'checkpoint', 'manifest', 'binding', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--steps', type=int, default=defaults.steps)
    parser.add_argument('--learning-rate', type=float, default=defaults.learning_rate)
    parser.add_argument('--query-worlds', type=int, default=1)
    parser.add_argument('--cpu-threads', type=int, default=2)
    parser.add_argument('--verification-evidence', type=Path)
    parser.add_argument('--support-phases', type=Path, required=True)
    parser.add_argument('--event-reference-contacts', type=Path, required=True,
                        help='Verified Newton labels of the aggregate continuity reference')
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--source-support', action='store_true')
    parser.add_argument('--continuity-reference', type=Path, required=True,
                        help='Aligned aggregate source motion, before augmentation IK')
    parser.add_argument('--audit-frames', type=int, nargs='*', default=[])
    args = parser.parse_args()
    import numpy as np
    import torch
    from somaforge_core import G1_29DOF_JOINT_ORDER
    from somaforge_core.robot_assets import decode_robot_asset_json, somaforge_root
    from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics
    from somaforge_core.newton_tensor_transport import TensorSceneClient, TensorSceneRouter
    from motion_edit.generation.native_contact_refinement import (
        refine_trajectory, RefinementConfig, demonstrated_approach_tasks)
    from motion_edit.generation.taskspace_spec import read_contact_aware_taskspace_motion
    from contact_solver.contact_regions import CONTACT_INTERVAL_SCHEMA
    from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
    torch.set_num_threads(args.cpu_threads)
    # Never overwrite an experiment or its evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    with np.load(args.motion, allow_pickle=False) as source:
        seed = {key: source[key].copy() for key in ('joint_pos', 'joint_names', 'fps', 'robot_asset_json')}
        initializer = json.loads(source['source_initializer_json'].item()) if 'source_initializer_json' in source else None
    decode_robot_asset_json(seed['robot_asset_json'], context=str(args.motion))
    names = seed['joint_names'].astype(str).tolist()
    order = [names.index(name) for name in G1_29DOF_JOINT_ORDER]
    q = np.concatenate((seed['joint_pos'][:, :7], seed['joint_pos'][:, 7:][:, order]), -1)
    with np.load(args.continuity_reference, allow_pickle=False) as original:
        decode_robot_asset_json(original['robot_asset_json'], context=str(args.continuity_reference))
        original_names = original['joint_names'].astype(str).tolist()
        if set(original_names) != set(names) or len(original_names) != len(names):
            raise ValueError('Continuity reference joint names differ')
        if original['joint_pos'].shape != seed['joint_pos'].shape or not np.array_equal(original['fps'], seed['fps']):
            raise ValueError('Continuity reference must have the same frame count and sampling rate')
        original_order = [original_names.index(name) for name in G1_29DOF_JOINT_ORDER]
        temporal = np.concatenate((original['joint_pos'][:, :7], original['joint_pos'][:, 7:][:, original_order]), -1)
    events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
    from motion_edit.generation.event_acceptance import materialize_contract, optimization_events
    event_contract = materialize_contract(args.continuity_reference, args.event_reference_contacts, args.events, args.support_phases)
    (args.output/'event_contract.json').write_text(json.dumps(event_contract, indent=2))
    events = optimization_events(event_contract)
    binding = json.loads(args.binding.read_text())
    fk = CanonicalG1ForwardKinematics().cuda()
    tensor = torch.tensor(q, dtype=torch.float32, device='cuda')
    spec = read_contact_aware_taskspace_motion(args.taskspace)
    if spec.frame_count != len(q):
        raise ValueError('Taskspace and motion frame counts differ')
    approach = demonstrated_approach_tasks(spec, events, fk, tensor, binding['surface_catalog'])
    support_reference = None
    if args.source_support:
        from motion_edit.generation.source_support import build_support_reference
        support_reference = build_support_reference(spec, approach[3], approach[2])
    from motion_edit.generation.source_support import SourcePhaseMotion
    phase_motion = SourcePhaseMotion(fk, torch.as_tensor(temporal, device=tensor.device, dtype=tensor.dtype),
                                     args.event_reference_contacts, event_contract)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    auth = args.output / 'query.auth'
    with auth.open('xb') as stream:
        os.chmod(auth, 0o600); stream.write(os.urandom(32))
    command = [sys.executable, str(somaforge_root()/'scripts/serve_newton_contact_queries.py'),
               '--checkpoint', str(args.checkpoint), '--motion-manifest', str(args.manifest),
               '--binding', str(args.binding), '--inspection-output', str(args.output/'model.json'),
               '--port', str(port), '--query-nconmax', '2048', '--query-njmax', '16384',
               '--query-worlds', str(args.query_worlds), '--capture-contact-sources', '--tensor-auth', str(auth), '--device', 'cuda:0']
    client = None
    with (args.output/'worker.log').open('w') as log:
        worker = subprocess.Popen(command, cwd=somaforge_root(), stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+240
            while '"ready": true' not in (args.output/'worker.log').read_text():
                if worker.poll() is not None:
                    raise RuntimeError('Native worker exited; inspect worker.log')
                if time.monotonic() > deadline:
                    raise TimeoutError('Native worker initialization timed out')
                time.sleep(1)
            client = TensorSceneClient(port, auth.read_bytes())
            fingerprint = client.metadata['provenance']['model_fingerprint']
            if fingerprint != binding['model_fingerprint']:
                raise ValueError('Native scene fingerprint differs from binding')
            def audit_frames(poses, label):
                from somaforge_core.contact_face_selection import select_contact_pairs
                records = []
                for frame in args.audit_frames:
                    device, native = client.query(poses[frame:frame+1], audit=True)
                    selected = select_contact_pairs(native['pairs'], native['surface_catalog'])
                    if not np.array_equal(selected['contact_part_mask'], device['contact_part_mask'].cpu().numpy()):
                        raise AssertionError('Same-pass CPU/device contact masks differ')
                    if not np.array_equal(selected['contact_surface'], device['contact_surface'].cpu().numpy()):
                        raise AssertionError('Same-pass CPU/device contact surfaces differ')
                    records.append(dict(frame=frame, same_pass_verified=True, native=native))
                if records:
                    (args.output/f'{label}_same_pass_audit.json').write_text(json.dumps(records, indent=2))
            audit_frames(tensor, 'initial')
            router = TensorSceneRouter({0: client})
            if args.verification_evidence is not None:
                checked = 0
                for evidence_path in sorted(args.verification_evidence.glob('native_evidence_*.npz')):
                    with np.load(evidence_path, allow_pickle=False) as evidence:
                        poses = torch.as_tensor(evidence['q'], device=tensor.device, dtype=tensor.dtype)
                        observed = router(poses, torch.zeros(len(poses), dtype=torch.long, device=tensor.device))
                        for field in ('contact_part_mask', 'contact_surface'):
                            np.testing.assert_array_equal(observed[field].cpu().numpy(), evidence[field],
                                                          err_msg=f'Parallel parity: {evidence_path.name} {field}')
                        checked += len(poses)
                if checked == 0:
                    raise ValueError('No single-world evidence to verify')
                (args.output/'parallel_parity.json').write_text(json.dumps(dict(
                    frames=checked, query_worlds=args.query_worlds, contact_masks_equal=True,
                    surfaces_equal=True, evidence=str(args.verification_evidence)), indent=2))
            query_index = 0
            def query(q):
                nonlocal query_index
                observed = router(q, torch.zeros(len(q), dtype=torch.long, device=q.device))
                observed['provenance'] = client.metadata['provenance']
                if args.audit_only:
                    evidence = {f'pair_{k}': v.detach().cpu().numpy() for k,v in observed['pairs'].items()}
                    evidence.update({k:observed[k].detach().cpu().numpy()
                        for k in ('contact_part_mask', 'contact_surface', 'configured_margin')})
                    evidence.update(q=q.detach().cpu().numpy(), metadata_json=json.dumps(client.metadata),
                                    link_names=np.asarray(observed['link_names']))
                    np.savez_compressed(args.output/f'native_evidence_{query_index:04d}.npz', **evidence)
                    query_index += 1
                return observed
            def progress(row):
                print(json.dumps({k:v for k,v in row.items() if k != 'event_acceptance'}), flush=True)
                with (args.output/'history.jsonl').open('a') as stream:
                    stream.write(json.dumps(row)+'\n')
            result, history = refine_trajectory(tensor, fk, events, query, fingerprint,
                config=RefinementConfig(steps=0 if args.audit_only else args.steps, learning_rate=args.learning_rate), approach_tasks=approach, progress=progress,
                continuity_reference=torch.as_tensor(temporal, dtype=tensor.dtype, device=tensor.device),
                event_contract=event_contract, support_reference=support_reference, phase_motion_loss=phase_motion)
            audit_frames(result, 'final')
            pose = result.cpu().numpy()
            seed['joint_pos'] = np.concatenate((pose[:, :7], pose[:, 7:][:, np.argsort(order)]), -1)
            np.savez_compressed(args.output/'seed.npz', **seed)
            canonicalize_motion_with_direct_newton_fk(args.output/'seed.npz', args.output/'motion.npz')
            (args.output/'audit.json').write_text(json.dumps(dict(
                initial=history[0], final=history[-1], source=str(args.motion.resolve()),
                source_initializer=initializer, objective_schema=REFINEMENT_OBJECTIVE_SCHEMA, contact_interval_schema=CONTACT_INTERVAL_SCHEMA, model_fingerprint=fingerprint,
                query_worlds=args.query_worlds, learning_rate=args.learning_rate, source_support_enabled=args.source_support, audit_only=args.audit_only, event_contract_schema=event_contract['schema'],
                continuity_reference=str(args.continuity_reference.resolve()),
                query_schema='newton_device_witness_batch_v1',
                surface_attribution_schema='newton_source_triangle_normal_fan_v1',
                event_file=str(args.events.resolve()), training_ready=False), indent=2))
        finally:
            if client is not None:
                client.close()
            if worker.poll() is None:
                # This is our dedicated query worker, never a training process.
                worker.terminate()
                try: worker.wait(timeout=20)
                except subprocess.TimeoutExpired: worker.kill(); worker.wait()


if __name__ == '__main__':
    main()
