"""Compare frozen shared and isolated models; never construct an optimizer."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import torch




def audit(model, cfg, inputs, validation, labels_for, objective):
    model.eval()
    original = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    checkpoint = torch.load(cfg.initial_position_checkpoint, map_location='cpu', weights_only=False)
    archive = Path('tmp/full1000_isolated_contact_20260924/code_before/packages/climb00_pipeline/climb00_pipeline/full1000_position_predictor.py')
    name = 'climb00_pipeline._before_execution_isolation'
    spec = importlib.util.spec_from_file_location(name, archive)
    old_module = importlib.util.module_from_spec(spec)
    sys.modules[name] = old_module
    spec.loader.exec_module(old_module)
    old = old_module.Full1000PositionPredictor(cfg.width, cfg.layers, cfg.location_width,
        region_plan=True, unified_contact=True).to(validation.device).eval()
    old.load_state_dict(checkpoint['model'])
    old_original = {k: v.detach().cpu().clone() for k, v in old.state_dict().items()}

    count = min(cfg.static_audit_samples, len(validation))
    ids = validation[torch.linspace(0, len(validation)-1, count, device=validation.device).long()]
    batches = [('reference_validation', ids, {k: v[ids] for k, v in inputs.items()})]
    if cfg.static_audit_pool is not None:
        if cfg.static_audit_pool.parent.resolve() != cfg.initial_position_checkpoint.parent.resolve():
            raise ValueError('Pool must accompany the asset-validated checkpoint')
        state = torch.load(cfg.static_audit_pool, map_location=validation.device, weights_only=False)
        if state['schema'] != 'persistent_parallel_rollout_training_state_v1' or state['step'] != checkpoint['step']:
            raise ValueError('Pool/checkpoint mismatch')
        pool = state['pool']; slots = (pool['age'] > 0).nonzero().flatten()[:cfg.static_audit_samples]
        if not len(slots): raise ValueError('No generated pool inputs')
        batches.append(('generated_pool_states', pool['indices'][slots],
            {k: v[slots] for k, v in pool['observation'].items()}))

    def cpu(value):
        if isinstance(value, torch.Tensor): return value.detach().cpu()
        if isinstance(value, dict): return {k: cpu(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)): return type(value)(cpu(v) for v in value)
        return value

    records = []
    for source, ids, observation in batches:
        reference, pairs = None, None
        for mode, network in [('previous_shared', old), ('isolated', model)]:
            prediction = network(**observation)
            if reference is None:
                reference = {k: getattr(prediction, k).detach().clone() for k in
                    ('qpos', 'role_logits', 'location_logits', 'region_logits', 'conditioned_contact', 'conditioned_points_local', 'planned_regions')}
            else:
                for key, value in reference.items():
                    torch.testing.assert_close(getattr(prediction, key), value, rtol=0, atol=0)
            loss, metrics, queried = objective(prediction, observation, ids,
                labels_for(observation, ids, recursive=source == 'generated_pool_states'))
            if pairs is None:
                pairs = cpu(queried[0].pair)
                torch.save({'schema': 'frozen_actual_newton_gradient_witnesses_v1',
                    'sample_indices': ids.cpu(), 'q_world': prediction.qpos.detach().cpu(),
                    'q_local': queried[0].q.detach().cpu(), 'observations': cpu(observation),
                    'world_frame': cpu(queried[0].world_frame), 'newton': cpu(queried[1])},
                    cfg.output/f'witnesses_{source}.pt')
            else:
                for key, value in pairs.items():
                    torch.testing.assert_close(queried[0].pair[key].cpu(), value, rtol=0, atol=0, equal_nan=True)
            terms = {'planner': metrics['audit_planner'], 'contact_execution': metrics['unified_region_loss'],
                'imitation': metrics['audit_imitation'], 'layout': metrics['audit_layout'], 'joint_limits': metrics['audit_safety']}
            torch.testing.assert_close(sum(terms.values()), loss)
            terms['total'] = loss
            named = list(network.named_parameters()); params = [p for _, p in named]
            sets = {
                'planner': [i for i, (n, _) in enumerate(named) if not n.startswith(model.EXECUTION_PREFIXES)],
                'executor': [i for i, (n, _) in enumerate(named) if n.startswith(model.EXECUTION_PREFIXES)],
                'planning_encoder': [i for i, (n, _) in enumerate(named) if n.startswith(('height.', 'global_encoder.', 'part_encoder.', 'terrain_reasoning.', 'shared.', 'norm.'))],
                'planning_heads': [i for i, (n, _) in enumerate(named) if n.startswith(('role_head.', 'location_', 'region_head.', 'region_prior'))],
                'execution_geometry': [i for i, (n, _) in enumerate(named) if n.startswith('execution_geometry_encoder.')],
                'execution_adapter': [i for i, (n, _) in enumerate(named) if n.startswith('execution_adapter.')],
                'execution_norm': [i for i, (n, _) in enumerate(named) if n.startswith('execution_norm.')],
            }
            details = {}
            for term, value in terms.items():
                gradients = torch.autograd.grad(value.mean(), params, retain_graph=True, allow_unused=True)
                norms = {group: sum((float(gradients[i].detach().double().square().sum())
                    for i in members if gradients[i] is not None), 0.)**.5 for group, members in sets.items()}
                if mode == 'isolated' and term != 'total':
                    forbidden = 'executor' if term == 'planner' else 'planner'
                    assert all(gradients[i] is None for i in sets[forbidden]), (source, term, forbidden)
                details[term] = {'mean_loss': float(value.detach().mean()), 'gradient_norms': norms}
            if mode == 'isolated':
                assert details['contact_execution']['gradient_norms']['executor'] > 0
                assert details['contact_execution']['gradient_norms']['execution_geometry'] > 0
                assert details['planner']['gradient_norms']['planner'] > 0
            record = {'source': source, 'mode': mode, 'samples': len(ids), 'sample_indices': ids.cpu().tolist(),
                'forward_bitwise_equal': True, 'newton_pairs': len(queried[0].pair['dist']),
                'valid_gradient_samples': int(metrics['region_gradient_valid'].sum()), 'components': details}
            records.append(record)
            print(json.dumps({'isolation_audit': source, 'mode': mode,
                'contact_gradient_norms': details['contact_execution']['gradient_norms']}), flush=True)
            del prediction, loss, metrics, queried, terms, gradients
    for network, before in [(model, original), (old, old_original)]:
        for name, value in network.state_dict().items():
            torch.testing.assert_close(value.cpu(), before[name], rtol=0, atol=0)
        assert all(p.grad is None for p in network.parameters())
    report = {'schema': 'isolated_planning_execution_gradient_audit_v1', 'parameter_updates': 0,
        'optimizer_constructed': False, 'weights_bitwise_unchanged': True,
        'source_checkpoint': str(cfg.initial_position_checkpoint),
        'source_checkpoint_sha256': hashlib.sha256(cfg.initial_position_checkpoint.read_bytes()).hexdigest(),
        'identical_actual_newton_pairs': True, 'records': records,
        'scope': 'Fixed weights and inputs, fresh actual Newton witnesses reused only at bitwise-identical q/scene. No training or quality claim.'}
    (cfg.output/'isolation_audit.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    write_witness_manifest(cfg)
    print(json.dumps({'isolation_audit_complete': True, 'parameter_updates': 0}), flush=True)

def write_witness_manifest(cfg):
    from somaforge_core.robot_assets import decode_robot_asset_json
    from somaforge_core.newton_contacts import SCHEMA
    from somaforge_core.contact_face_selection import FACE_POLICY
    checkpoint = torch.load(cfg.initial_position_checkpoint, map_location='cpu', weights_only=False)
    asset = checkpoint['robot_asset_json']
    decode_robot_asset_json(asset, context='frozen contact audit')
    samples = torch.load(cfg.data_cache, map_location='cpu', weights_only=False)['samples']
    scenes = {}
    for folder in sorted((cfg.output/'newton_workers').glob('h*')):
        model_file, binding_file = folder/'model.json', folder/'binding.json'
        model = json.loads(model_file.read_text())
        scenes[folder.name] = {'model_fingerprint': model['model_fingerprint'],
            'model': str(model_file.resolve()), 'binding': str(binding_file.resolve()),
            'model_sha256': hashlib.sha256(model_file.read_bytes()).hexdigest(),
            'binding_sha256': hashlib.sha256(binding_file.read_bytes()).hexdigest()}
    witnesses = []
    for path in sorted(cfg.output.glob('witnesses_*.pt')):
        payload = torch.load(path, map_location='cpu', weights_only=False)
        indices = payload['sample_indices'].tolist()
        scene_names = [f"h{float(samples[i]['height']):.8f}" for i in indices]
        if not all(name in scenes for name in scene_names): raise ValueError('Unknown witness scene')
        witnesses.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'sample_indices': indices, 'scene_by_batch_sample': scene_names})
    (cfg.output/'witness_manifest.json').write_text(json.dumps({
        'schema': 'frozen_actual_newton_gradient_witness_manifest_v1',
        'robot_asset_json': asset, 'contact_semantics': SCHEMA, 'face_selection': FACE_POLICY,
        'sampling': 'static query at saved raw predicted q; no integration; same real witnesses reused across derivative variants',
        'indexing': 'pairs.sample indexes the saved q batch; pairs.worldid is the reused solver slot within its scene',
        'scenes': scenes, 'witnesses': witnesses}, indent=2))
