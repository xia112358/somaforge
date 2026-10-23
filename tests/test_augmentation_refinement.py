"""CPU stage gating: references stay unlabeled until actual policy extraction."""
import json
from pathlib import Path
from types import SimpleNamespace
import uuid
import threading

import numpy as np
import pytest

from somaforge_core import augmentation_refinement as workflow
from somaforge_core import trajectory_refinement as refinement


@pytest.fixture
def run_fixture(monkeypatch):
    root=Path(__file__).resolve().parents[1]/'tmp/augmentation_refinement_tests'/uuid.uuid4().hex
    root.mkdir(parents=True)
    from motion_edit.contact.plans import ContactEditPlan
    from motion_edit.generation.source_prefix_reference import SCHEMA
    q=np.zeros((12,36));q[:,3]=1.;np.savez(root/'source.npz',joint_pos=q)
    plane=dict(surface_id='floor',origin=[0.,0.,0.],tangent_u=[1.,0.,0.],tangent_v=[0.,1.,0.],normal=[0.,0.,1.])
    prefix=dict(schema=SCHEMA,hold_frames=3,transition_end_frame=8,
                surface_transform_id='start',joint_prior_scale=100.,semantic_weight=10000.)
    jobs=[]
    for name in ('a','b'):
        plan=ContactEditPlan(plan_id=name,source_motion_path=str(root/'source.npz'),source_motion_id='source',
            source_contact_layer='unused',status='validated',metadata=dict(source_prefix_reference=prefix),
            surface_transforms=[dict(transform_id='start',kind='surface_follow',translation_world=[0.,0.,0.],
                                     source_surface=plane,target_surface=plane)])
        path=root/f'{name}.json';path.write_text(json.dumps(plan.to_dict()))
        jobs.append(dict(identity=name,plan=str(path),directory=str(root/'motions'/name),catalog_file='geometry.npz',terrain='floor.obj'))
    for name in ('base.pt','contract.json'):(root/name).write_text(name)
    config=dict(schema=workflow.SCHEMA,plan_manifest='unused',catalog_collection='unused',
        generation=dict(output_dir=str(root/'motions'),ik_max_nfev=25,ik_q_acceleration_weight=8,
                        ik_conda_env='current',collision_reference_cache=None,workers=1,threads_per_worker=1,device='cpu'),
        refinement=dict(base_checkpoint=str(root/'base.pt'),output_dir=str(root/'workflow'),
                        task=dict(contract=str(root/'contract.json'))),
        gpu=dict(index=0,min_free_mib=6000,poll_seconds=1))
    config_path=root/'config.json';config_path.write_text(json.dumps(config))
    prepared=dict(schema=workflow.SCHEMA,config=config,jobs=jobs,files=[])
    monkeypatch.setattr(workflow,'preparation',lambda c:prepared.copy())
    def generate(plan,*,output_motion_path,**kwargs):
        p=Path(output_motion_path);p.write_bytes(b'generated positions, no contacts')
        receipt=dict(diagnostics=dict(source_prefix_reference=prefix,root_yaw_condition=dict(reference_delta_degrees=0.),root_yaw_optimized=True))
        p.with_suffix('.generation.json').write_text(json.dumps(receipt))
        p.with_suffix('.generation.plan.json').write_text(Path(plan).read_text())
        return SimpleNamespace(output_motion_path=p)
    monkeypatch.setattr('motion_edit.generation.jobs.generate_candidate',generate)
    monkeypatch.setattr('motion_edit.generation.newton_direct_fk.canonicalize_motion_with_direct_newton_fk',
                        lambda source,output,**kw:Path(output).write_bytes(Path(source).read_bytes()))
    return root,config_path


def test_dry_run_starts_no_generation_or_training(run_fixture):
    root,path=run_fixture
    result=workflow.run(path,'all')
    assert result['launches']==0 and result['jobs']==2
    assert not (root/'workflow').exists() and not (root/'motions').exists()


def test_generated_references_have_no_new_contact_labels_and_resume_is_hash_checked(run_fixture):
    root,path=run_fixture
    assert workflow.run(path,'generate',execute=True)['count']==2
    assert workflow.run(path,'generate',execute=True)['count']==2
    assert not list(root.rglob('motion_contacts.npz'))
    for name in ('a','b'):
        receipt=json.loads((root/'motions'/name/'reference_complete.json').read_text())
        assert receipt['intermediate_contacts_labeled'] is False
        assert receipt['training_ready_as_demonstration'] is False
    (root/'motions/a/motion.npz').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):workflow.run(path,'generate',execute=True)


def test_all_stages_use_one_trained_policy_and_export_last(run_fixture,monkeypatch):
    root,path=run_fixture;calls=[]
    monkeypatch.setattr(refinement,'prepare',lambda recipe,execute:dict(config={},cases=[1,2]))
    monkeypatch.setattr(workflow.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout='16000'))
    def train(plan,**kwargs):
        calls.append(('train',None));p=root/'trained.pt';p.write_bytes(b'fixed policy')
        return dict(checkpoint=refinement.fingerprint(p))
    monkeypatch.setattr(refinement,'train',train)
    def evaluate(plan,stage,checkpoint,**kw):
        calls.append((stage,checkpoint));return dict(stage=stage)
    monkeypatch.setattr(refinement,'evaluate_or_collect',evaluate)
    monkeypatch.setattr(refinement,'export_dataset',lambda plan,checkpoint,**kw:calls.append(('export',checkpoint)))
    workflow.run(path,'all',execute=True)
    # Evaluation is a separate diagnostic, never a collection prerequisite.
    assert [c[0] for c in calls]==['train','collect','export']
    assert len({c[1] for c in calls[1:]})==1
    manifest=json.loads((root/'workflow/generated_references.json').read_text())
    assert all(r['contact_catalog_file']=='geometry.npz' for r in manifest['motion_files'])
    assert not list(root.rglob('motion_contacts.npz'))


def test_parallel_is_the_default_and_invalid_counts_fail_closed(run_fixture):
    root,path=run_fixture
    config=json.loads(path.read_text())
    config['generation'].pop('workers');config['generation'].pop('threads_per_worker')
    path.write_text(json.dumps(config))
    loaded=workflow.read_config(path)
    assert loaded['generation']['workers']==3
    assert loaded['generation']['threads_per_worker']==4
    config['generation'].pop('device');path.write_text(json.dumps(config))
    assert workflow.read_config(path)['generation']['device']=='cuda:0'
    for value in ('gpu','cuda','cuda:-1','cuda:bad',None):
        config['generation']['device']=value;path.write_text(json.dumps(config))
        with pytest.raises(ValueError,match='generation.device'):workflow.read_config(path)
    config['generation']['device']='cpu'
    for value in (0,-1,True,1.5):
        config['generation']['workers']=value;path.write_text(json.dumps(config))
        with pytest.raises(ValueError,match='positive integer'):workflow.read_config(path)


@pytest.mark.parametrize('device,workers',[('cpu',3),('cuda:2',3),('cuda:2',1)])
def test_parallel_workers_have_isolated_queues_environments_and_reuse_results(run_fixture,monkeypatch,device,workers):
    import generate_contact_aware_batch as batch
    root,path=run_fixture
    config=json.loads(path.read_text());config['generation'].pop('workers');config['generation'].pop('threads_per_worker')
    config['generation']['device']=device
    config['generation']['workers']=workers
    path.write_text(json.dumps(config))
    starts=[];commands=[];shutdown=[];affinities=[]
    count=min(workers,2);barrier=threading.Barrier(count)
    def start(*,index,environment,work_root,ik_conda_env):
        assert ik_conda_env==config['generation']['ik_conda_env']
        starts.append(dict(environment));name=f'worker-{index}'
        process=SimpleNamespace(pid=100+index,wait=lambda **kw:0,poll=lambda:0)
        return name,process,(work_root/f'fake_worker_{index}.log').open('x')
    monkeypatch.setattr(batch,'_start_ik_worker',start)
    monkeypatch.setattr(batch,'_worker_request',lambda name,payload:shutdown.append(name))
    monkeypatch.setattr(workflow,'set_affinity',lambda pid,cpus:affinities.append((pid,cpus)))
    monkeypatch.setattr(workflow.os,'sched_getaffinity',lambda pid:set(range(16)))
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','parent_unchanged')
    admission=[]
    def gpu_query(command,**kwargs):
        admission.append(command);return SimpleNamespace(stdout='16000')
    monkeypatch.setattr(workflow.subprocess,'run',gpu_query)
    def run(command,directory,environment,cpus):
        commands.append((command,environment,cpus));barrier.wait(timeout=5)
        identity=command[command.index('--identity')+1]
        folder=root/'motions'/identity;folder.mkdir(parents=True)
        motion=folder/'motion.npz';motion.write_bytes(identity.encode())
        refinement.write_json(folder/'reference_complete.json',dict(plan=refinement.fingerprint(root/f'{identity}.json'),
            files=[refinement.fingerprint(motion)],intermediate_contacts_labeled=False),immutable=True)
    monkeypatch.setattr(workflow,'run_candidate',run)
    workflow.run(path,'generate',execute=True)
    assert len(starts)==count and len(commands)==2
    assert {e['SOMAFORGE_IK_WORKER_SOCKET'] for _,e,_ in commands}=={f'worker-{i}' for i in range(count)}
    assert all(e['CUDA_VISIBLE_DEVICES']==('2' if device=='cuda:2' else '') and e['OMP_NUM_THREADS']=='4' for _,e,_ in commands)
    assert all(e['SOMAFORGE_IK_DEVICE']==('cuda:0' if device=='cuda:2' else 'cpu') for e in starts)
    assert admission==([['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits','--id=2']] if device=='cuda:2' else [])
    assert len({e['SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE'] for _,e,_ in commands})==count
    if count==2:assert set(commands[0][2]).isdisjoint(commands[1][2])
    assert workflow.os.environ['CUDA_VISIBLE_DEVICES']=='parent_unchanged'
    assert len(shutdown)==count
    status=json.loads((root/'workflow/augmentation_status.json').read_text())
    assert status['completed']==2
    workflow.run(path,'generate',execute=True)
    assert len(starts)==count and len(commands)==2
