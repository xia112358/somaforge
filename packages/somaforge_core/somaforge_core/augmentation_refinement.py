"""Explicitly authorized augmentation, policy refinement and executed labeling.

Intermediate references are kinematic inputs. Only final policy executions get
new contact observations and dataset admission; old labels supply scene catalogs.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import trajectory_refinement as refinement

SCHEMA = "somaforge_augmentation_refinement_v1"


def read_config(path):
    config = refinement.read_json(path)
    required = {"schema", "plan_manifest", "catalog_collection", "generation", "refinement", "gpu"}
    if set(config) != required or config["schema"] != SCHEMA:
        raise ValueError("Invalid augmentation/refinement configuration")
    required_generation={"output_dir", "ik_max_nfev", "ik_q_acceleration_weight", "ik_conda_env", "collision_reference_cache"}
    if (not required_generation <= set(config["generation"])
            or set(config["generation"]) - required_generation - {"workers","threads_per_worker","device"}):
        raise ValueError("Invalid generation configuration")
    for key,default in (("workers",3),("threads_per_worker",4)):
        config["generation"].setdefault(key,default)
        if type(config["generation"][key]) is not int or config["generation"][key]<1:
            raise ValueError(f"generation.{key} must be a positive integer")
    for key in ("ik_max_nfev", "ik_q_acceleration_weight"):
        if config["generation"][key] <= 0:
            raise ValueError("Generation budgets must be positive")
    if set(config["gpu"]) != {"index", "min_free_mib", "poll_seconds"}:
        raise ValueError("Invalid GPU admission configuration")
    if (config["gpu"]["index"] < 0 or config["gpu"]["min_free_mib"] <= 0
            or not 1 <= config["gpu"]["poll_seconds"] <= 60):
        raise ValueError("Invalid GPU admission budget")
    device=config['generation'].setdefault('device',f"cuda:{config['gpu']['index']}")
    if not isinstance(device,str) or not (device=='cpu' or (device.startswith('cuda:') and device[5:].isdigit())):
        raise ValueError('generation.device must be cpu or cuda:<index>')
    return config


def preparation(config):
    from motion_edit.contact.plans import read_contact_edit_plan
    from motion_edit.generation.source_prefix_reference import configure_plan_prefix
    root = refinement.somaforge_root()
    manifest_path = refinement.resolve(config["plan_manifest"], root)
    catalog_path = refinement.resolve(config["catalog_collection"], root)
    manifest = refinement.read_json(manifest_path)
    catalog = refinement.read_json(catalog_path)
    catalog_by_name = {str(r["motion_id"]): r for r in catalog["motion_files"]}
    files = {str(p): refinement.fingerprint(p) for p in (manifest_path, catalog_path)}
    source_preparation = manifest_path.parent/"preparation.json"
    if source_preparation.exists():
        from motion_edit.generation.source_prefix_reference import prefix_implementation_fingerprints
        evidence=refinement.read_json(source_preparation)
        if evidence["implementation"] != prefix_implementation_fingerprints():
            raise ValueError("Prepared augmentation implementation changed; prepare a new version")
        files[str(source_preparation)]=refinement.fingerprint(source_preparation)
        source_files=[dict(path=k,sha256=v) for k,v in evidence["inputs"].items()]
        refinement.verify_files(source_files)
        files.update({f["path"]:f for f in source_files})
    cache = config["generation"]["collision_reference_cache"]
    if cache:
        path = refinement.resolve(cache, root); files[str(path)] = refinement.fingerprint(path)
    jobs = []
    for entry in manifest["plans"]:
        path = refinement.resolve(entry["plan_path"], manifest_path.parent)
        plan = configure_plan_prefix(read_contact_edit_plan(path), required=True)
        if plan.plan_id not in catalog_by_name:
            raise ValueError(f"Missing target-scene catalog for {plan.plan_id}")
        catalog_file = refinement.resolve(catalog_by_name[plan.plan_id]["contacts"], catalog_path.parent)
        # Geometry provenance only: no old contact mask, force or acceptance is read.
        terrain = refinement.resolve(plan.metadata["target_terrain_mesh"], path.parent)
        for item in (path, Path(plan.source_motion_path), catalog_file, terrain):
            if str(item) not in files: files[str(item)] = refinement.fingerprint(item)
        directory = refinement.resolve(config["generation"]["output_dir"], root)/plan.plan_id
        jobs.append(dict(identity=plan.plan_id, plan=str(path), directory=str(directory),
                         catalog_file=str(catalog_file), terrain=str(terrain)))
    if not jobs or len({j["identity"] for j in jobs}) != len(jobs):
        raise ValueError("Empty or duplicate augmentation plans")
    implementation = [Path(__file__), root/"scripts/run_augmentation_refinement.py",
        root/"scripts/generate_contact_aware_batch.py",
        root/"scripts/train_motion_edit_policy_finetune.py", Path(refinement.__file__),
        root/"src/holosoma/holosoma/utils/training_state.py",
        root/"src/holosoma/holosoma/config_types/algo.py",
        root/"src/holosoma/holosoma/agents/ppo/ppo.py",
        root/"src/holosoma/holosoma/agents/base_algo/base_algo.py",
        root/"src/holosoma/holosoma/agents/modules/logging_utils.py",
        root/"packages/motion_edit/motion_edit/generation/jobs.py",
        root/"packages/motion_edit/motion_edit/generation/source_prefix_reference.py",
        root/"packages/motion_edit/motion_edit/generation/rollout_authority.py",
        root/"packages/motion_edit/motion_edit/generation/pyroki_fullbody_ik.py",
        root/"packages/motion_edit/motion_edit/generation/newton_direct_fk.py"]
    for item in implementation: files[str(item)] = refinement.fingerprint(item)
    return dict(schema=SCHEMA, config=config, jobs=jobs, files=list(files.values()),
                intermediate_contacts_labeled=False, executed_contact_labeling="after_policy_rollout")


def verify_reference(job):
    receipt=Path(job['directory'])/'reference_complete.json'
    if not receipt.exists():return False
    saved=refinement.read_json(receipt)
    if saved['plan']!=refinement.fingerprint(job['plan']):raise ValueError('Completed reference plan changed')
    refinement.verify_files(saved['files'])
    return True


def generate_reference(job, config):
    """One isolated candidate process, using the same formal generator and FK."""
    from motion_edit.generation.jobs import generate_candidate
    from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
    from motion_edit.contact.plans import read_contact_edit_plan
    from motion_edit.generation.source_prefix_reference import configure_plan_prefix,verify_prefix_diagnostics
    if verify_reference(job):return
    directory=Path(job['directory']);preview=directory/'generated.npz';motion=directory/'motion.npz'
    if directory.exists():raise ValueError(f'Incomplete candidate retained; inspect before recovery: {directory}')
    directory.mkdir(parents=True)
    root=refinement.somaforge_root();generation=config['generation']
    from contextlib import redirect_stdout,redirect_stderr
    with (directory/'generation.log').open('x') as log:
        with redirect_stdout(log),redirect_stderr(log):
            generate_candidate(job['plan'],output_motion_path=preview,intermediate_dir=directory/'work',
                ik_max_nfev=generation['ik_max_nfev'],ik_q_acceleration_weight=generation['ik_q_acceleration_weight'],
                ik_conda_env=generation['ik_conda_env'],
                ik_collision_reference_cache=(refinement.resolve(generation['collision_reference_cache'],root)
                    if generation['collision_reference_cache'] else None))
            canonicalize_motion_with_direct_newton_fk(preview,motion,device='cpu')
    receipt=refinement.read_json(preview.with_suffix('.generation.json'))
    plan=configure_plan_prefix(read_contact_edit_plan(job['plan']),required=True)
    verify_prefix_diagnostics(receipt['diagnostics'],plan.metadata['source_prefix_reference'],plan.metadata['root_yaw_condition'])
    files=[refinement.fingerprint(p) for p in (preview,motion,preview.with_suffix('.generation.json'),
                                               preview.with_suffix('.generation.plan.json'))]
    refinement.write_json(directory/'reference_complete.json',dict(plan=refinement.fingerprint(job['plan']),files=files,
        reference_role='kinematic_training_input',intermediate_contacts_labeled=False,
        training_ready_as_demonstration=False),immutable=True)


def set_affinity(pid, cpus):
    if cpus and hasattr(os,'sched_setaffinity'):os.sched_setaffinity(pid,set(cpus))


def run_candidate(command, directory, environment, cpus):
    directory.mkdir(parents=True,exist_ok=False)
    refinement.write_json(directory/'command.json',command,immutable=True)
    with (directory/'process.log').open('x') as log:
        process=subprocess.Popen(command,cwd=refinement.somaforge_root(),env=environment,
                                 stdout=log,stderr=subprocess.STDOUT)
        set_affinity(process.pid,cpus)
        code=process.wait()
    refinement.write_json(directory/'process_result.json',dict(returncode=code),immutable=True)
    if code:raise RuntimeError(f'Candidate failed ({code}); see {directory / "process.log"}')


def generate_parallel(config_path, config, jobs, output, status):
    """Persistent IK workers use the configured JAX device; Newton stays on CPU."""
    from generate_contact_aware_batch import _start_ik_worker,_worker_request,_batch_environment
    import uuid
    completed={job['identity'] for job in jobs if verify_reference(job)}
    pending=[job for job in jobs if job['identity'] not in completed]
    if not pending:return
    device=config['generation']['device']
    gpu_started=device!='cpu'
    if gpu_started:
        gpu_index=int(device[5:])
        while True:
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits',
                                   f'--id={gpu_index}'],capture_output=True,text=True,check=True)
            free=int(result.stdout.strip())
            if free>=config['gpu']['min_free_mib']:break
            status('waiting_for_generation_gpu',completed=len(completed),device=device,gpu_started=False,
                   free_mib=free,required_mib=config['gpu']['min_free_mib'])
            time.sleep(config['gpu']['poll_seconds'])
    if config['generation']['workers']==1 and not gpu_started:
        previous={key:os.environ.get(key) for key in ('CUDA_VISIBLE_DEVICES','JAX_PLATFORMS')}
        os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['JAX_PLATFORMS']='cpu'
        try:
            for job in pending:
                status('generation',completed=len(completed),active=[job['identity']],workers=1,gpu_started=False)
                generate_reference(job,config);completed.add(job['identity'])
        finally:
            for key,value in previous.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
        return
    cpus=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else []
    threads=config['generation']['threads_per_worker']
    count=min(config['generation']['workers'],len(pending),max(1,len(cpus)//threads) if cpus else config['generation']['workers'])
    attempt=output/'generation_workers'/uuid.uuid4().hex;attempt.mkdir(parents=True)
    environment=_batch_environment(attempt)
    environment.update(CUDA_VISIBLE_DEVICES=str(gpu_index) if gpu_started else '',
        JAX_PLATFORMS='cuda' if gpu_started else 'cpu',XLA_PYTHON_CLIENT_PREALLOCATE='false',OMP_NUM_THREADS=str(threads),
        OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS=str(threads))
    pool=[];active={};lock=threading.Lock();stop=threading.Event()
    def publish():
        status('generation',completed=len(completed),active=list(active.values()),workers=count,
               threads_per_worker=threads,worker_attempt=str(attempt),device=device,gpu_started=gpu_started)
    try:
        for index in range(count):
            worker_environment=dict(environment,SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE=str(attempt/f'topology_{index}.npz'))
            name,process,log=_start_ik_worker(index=index,environment=worker_environment,work_root=attempt,
                ik_conda_env=config['generation']['ik_conda_env'])
            pool.append((name,process,log,worker_environment,cpus[index*threads:(index+1)*threads]))
            set_affinity(process.pid,pool[-1][4])
        def queue(index):
            name,process,log,worker_environment,affinity=pool[index]
            worker_environment=dict(worker_environment,SOMAFORGE_IK_WORKER_SOCKET=name)
            for job in pending[index::count]:
                if stop.is_set():return
                with lock:active[index]=job['identity'];publish()
                command=[sys.executable,str(refinement.somaforge_root()/'scripts/run_augmentation_refinement.py'),
                    '--config',str(Path(config_path).resolve()),'--stage','candidate','--identity',job['identity'],'--execute']
                try:
                    run_candidate(command,attempt/f'job_{job["identity"]}',worker_environment,affinity)
                    if not verify_reference(job):raise ValueError('Worker exited without a verified canonical reference')
                except Exception:
                    stop.set();raise
                with lock:
                    completed.add(job['identity']);active.pop(index);publish()
                print(f'Reference {len(completed)}/{len(jobs)}: {job["identity"]}',flush=True)
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures=[executor.submit(queue,i) for i in range(count)]
            for future in as_completed(futures):future.result()
    finally:
        for name,process,log,_,_ in pool:
            try:_worker_request(name,{'shutdown':True});process.wait(timeout=20)
            except Exception:
                if process.poll() is None:process.terminate();process.wait(timeout=20)
            log.close()


def candidate(config_path, identity):
    config=read_config(config_path)
    output=refinement.resolve(config['refinement']['output_dir'],refinement.somaforge_root())
    prepared=refinement.read_json(output/'augmentation_plan.json')
    if prepared['config']!=config:raise ValueError('Candidate configuration differs from the frozen plan')
    job=next(j for j in prepared['jobs'] if j['identity']==identity)
    inputs={f['path']:f for f in prepared['files']}
    from motion_edit.contact.plans import read_contact_edit_plan
    source=Path(read_contact_edit_plan(job['plan']).source_motion_path).resolve()
    paths=[Path(config_path).resolve(),Path(job['plan']),source,Path(__file__),
           refinement.somaforge_root()/'scripts/run_augmentation_refinement.py']
    refinement.verify_files([inputs[str(p)] for p in paths])
    generate_reference(job,config)
    return dict(stage='candidate_complete',identity=identity)


def run(config_path, stage, *, execute=False):
    config = read_config(config_path)
    root = refinement.somaforge_root()
    output = refinement.resolve(config["refinement"]["output_dir"], root)
    prepared = preparation(config)
    files={f['path']:f for f in prepared['files']}
    for p in (Path(config_path).resolve(),refinement.resolve(config['refinement']['base_checkpoint'],root),
              refinement.resolve(config['refinement']['task']['contract'],root)):
        files[str(p)]=refinement.fingerprint(p)
    prepared['files']=list(files.values())
    if not execute:
        return dict(stage=stage, jobs=len(prepared["jobs"]), launches=0, plan=prepared)
    output.mkdir(parents=True, exist_ok=True)
    refinement.write_json(output/"augmentation_plan.json", prepared, immutable=True)
    refinement.verify_files(prepared["files"])
    if stage == "prepare": return dict(stage=stage, jobs=len(prepared["jobs"]), gpu_started=False)
    if stage == "status":
        return refinement.read_json(output/"augmentation_status.json") if (output/"augmentation_status.json").exists() else dict(stage="prepared")
    def status(name, **extra):
        target=output/"augmentation_status.json"
        staged=target.with_name(f".{target.name}.{time.time_ns()}.writing")
        refinement.write_json(staged, dict(stage=name, total=len(prepared["jobs"]),
            updated_at=time.time(), intermediate_contacts_labeled=False, **extra),immutable=True)
        staged.replace(target)
    if stage in ("generate", "all"):
        generate_parallel(config_path,config,prepared['jobs'],output,status)
        status("references_generated", completed=len(prepared["jobs"]), gpu_started=False)
        if stage == "generate": return dict(stage="references_generated", count=len(prepared["jobs"]))
    # Build a standard reference manifest. Its contact_catalog_file contributes
    # only explicit target geometry, never contact truth for the new reference.
    terrains = {}; motions = []
    for job in prepared["jobs"]:
        directory = Path(job["directory"])
        saved = refinement.read_json(directory/"reference_complete.json"); refinement.verify_files(saved["files"])
        terrain_id = terrains.setdefault(job["terrain"], len(terrains))
        motion = directory/"motion.npz"
        motions.append(dict(motion_name=job["identity"], motion_file=str(motion), terrain_id=terrain_id,
                            contact_catalog_file=job["catalog_file"], motion_sha256=refinement.sha256_file(motion)))
    manifest = dict(motion_files=motions, terrains=[dict(terrain_id=v, terrain_file=k) for k,v in terrains.items()],
                    reference_role="kinematic_inputs; catalogs are geometry only; label actual policy executions")
    manifest_path = output/"generated_references.json"
    refinement.write_json(manifest_path, manifest, immutable=True)
    recipe = dict(config["refinement"], input=dict(kind="motion_manifest", path=str(manifest_path)))
    recipe_path = output/"refinement_config.json"
    refinement.write_json(recipe_path, recipe, immutable=True)
    plan = refinement.prepare(recipe_path, execute=True)
    refinement.verify_files(prepared["files"])
    if stage == "references": return dict(stage="references_prepared", count=len(motions))
    selected = output/"selected_policy.json"
    if stage in ("train", "all"):
        if selected.exists():
            trained = refinement.read_json(selected); refinement.verify_files([trained["checkpoint"]])
        else:
            while True:
                gpu = config["gpu"]
                result = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits",
                                         f"--id={gpu['index']}"], capture_output=True, text=True, check=True)
                free = int(result.stdout.strip())
                if free >= gpu["min_free_mib"]: break
                status("waiting_for_training_gpu", completed=len(motions), free_mib=free, required_mib=gpu["min_free_mib"])
                time.sleep(gpu["poll_seconds"])
            status("training", completed=len(motions))
            checkpoints=list((output/'training').rglob('model_*.pt'))
            resume=max(checkpoints,key=lambda p:int(p.stem.split('_')[-1])) if checkpoints else None
            trained = refinement.train(plan, checkpoint=resume, execute=True, device=f"cuda:{gpu['index']}", visualizer=None, headless=True)
            refinement.write_json(selected, trained, immutable=True)
        if stage == "train": return trained
    trained = refinement.read_json(selected); checkpoint = trained["checkpoint"]["path"]
    for name in (("collect","export") if stage=='all' else ("evaluate","collect","export")):
        if stage not in ("all", name): continue
        status(name, completed=len(motions), checkpoint=checkpoint)
        if name == "export": result = refinement.export_dataset(plan, checkpoint, execute=True)
        else: result = refinement.evaluate_or_collect(plan, name, checkpoint, execute=True,
            device=f"cuda:{config['gpu']['index']}", visualizer=None, headless=True)
    status("complete", completed=len(motions), checkpoint=checkpoint)
    return dict(stage=stage, checkpoint=checkpoint, result=result)
