"""Owned fixed-q Newton query workers for the full1000 training experiment.

Only workers created by this instance are terminated. Source scene and checkpoint
paths are explicit inputs; historical defaults are supplied by the training config.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

def terrain_text(source, scale):
    """Exact vertical scaling of this single box, preserving ground and faces."""
    if not 0.85 <= scale <= 1.15:
        raise ValueError('Outside declared experiment range')
    lines = []
    for line in source.splitlines():
        if line.startswith('v '):
            _, x, y, z = line.split()
            line = f'v {x} {y} {float(z)*scale:.10f}'
        lines.append(line)
    return '\n'.join(lines)+'\n'

class Workers:
    def __init__(self, root, heights, device, *, query_worlds=1, tensor_transport=False, solid_geometry=False, checkpoint, source_manifest, source_model):
        self.checkpoint = str(checkpoint)
        self.source_manifest = Path(source_manifest)
        self.source_model = Path(source_model)
        self.processes = []; self.logs = []; self.entries = {}
        self.root, self.heights, self.device = root, heights, device
        self.query_worlds = query_worlds
        self.tensor_transport = tensor_transport
        self.solid_geometry = solid_geometry
        self.tensor_clients = {}

    def __enter__(self):
        base = json.loads(self.source_manifest.read_text())
        mesh = Path(base['terrains'][0]['terrain_file']).read_text()
        self.root.mkdir(parents=True)
        try:
            for h in self.heights:
                folder = self.root/f'h{h:.8f}'; folder.mkdir()
                terrain = folder/'terrain.obj'; terrain.write_text(terrain_text(mesh,h))
                manifest = copy.deepcopy(base)
                manifest['terrains'][0].update(terrain_file=str(terrain.resolve()), terrain_sha256=hashlib.sha256(terrain.read_bytes()).hexdigest())
                mp = folder/'manifest.json'; mp.write_text(json.dumps(manifest,indent=2))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
                log = (folder/'worker.log').open('x'); self.logs.append(log)
                args = [sys.executable,'scripts/serve_newton_contact_queries.py','--checkpoint',self.checkpoint,
                    '--motion-manifest',str(mp),'--binding',str(folder/'binding.json'),'--create-native-binding',
                    '--inspection-output',str(folder/'model.json'),'--query-nconmax','2048','--query-njmax','16384',
                    '--port',str(port),'--device',self.device,'--capture-contact-sources',
                    '--query-worlds',str(self.query_worlds)]
                if self.tensor_transport:
                    key = os.urandom(32)
                    auth_path = folder/'tensor_auth.bin'
                    with os.fdopen(os.open(auth_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
                        stream.write(key)
                    args += ['--tensor-auth', str(auth_path)]
                if self.solid_geometry:
                    args += ['--solid-geometry']
                process = subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
                self.processes.append(process)
                self.entries[h] = dict(folder=folder,endpoint=f'http://127.0.0.1:{port}', port=port)
            deadline = time.monotonic()+240
            while not all('"ready": true' in (e['folder']/'worker.log').read_text() for e in self.entries.values()):
                if any(p.poll() is not None for p in self.processes) or time.monotonic()>deadline:
                    raise RuntimeError(f'Scene startup failed: {self.root}')
                time.sleep(1)
            for h,e in self.entries.items():
                e['model'] = json.loads((e['folder']/'model.json').read_text())
                e['fp'] = e['model']['model_fingerprint']
                levels = [z for b in e['model']['terrain_mesh_bounds'] for z in b['z_levels']]
                # This corpus uses a height SCALE, not a box height in metres.
                # The scene builder adds a 4 cm thick ground slab below z=0.
                reference=json.loads(self.source_model.read_text())
                reference_levels=[z for b in reference['terrain_mesh_bounds'] for z in b['z_levels']]
                if (abs(max(levels)-0.70449438*h)>2e-5 or 0. not in levels
                        or min(levels)!=min(reference_levels)):
                    raise ValueError('Actual Newton terrain differs from requested height')
            # Compare workers produced by the same current Newton build.  A
            # frozen pre-upgrade model.json is not a valid byte-level oracle:
            # current Newton expands capsule/cylinder scale components that
            # older inspection output stored as zeros.  Cross-height equality
            # still catches an accidental robot/config mutation without
            # rejecting that representation-only upgrade.
            current_reference = next(iter(self.entries.values()))['model']
            for h, e in self.entries.items():
                for key in ('shape_body','shape_type','shape_transform','shape_scale','shape_margin','shape_gap'):
                    if e['model'][key] != current_reference[key]:
                        raise ValueError(
                            f'Unexpected asset/config change at height {h}: {key}'
                        )
            from somaforge_core.newton_scene_router import NewtonSceneRouter
            self.router = NewtonSceneRouter({e['fp']:e['endpoint'] for e in self.entries.values()},workers=3)
            for index,entry in enumerate(self.entries.values()):entry['scene_id']=index
            if self.solid_geometry:
                from contact_solver.native_contact_position import NativeContactPositionRouter
                self.position_router=NativeContactPositionRouter({index:json.loads(
                    (entry['folder']/'contact_position_metadata.json').read_text())
                    for index,entry in enumerate(self.entries.values())})
            if self.tensor_transport:
                from somaforge_core.newton_tensor_transport import TensorSceneClient, TensorSceneRouter
                for index, (height, entry) in enumerate(self.entries.items()):
                    client = TensorSceneClient(entry['port'], (entry['folder']/'tensor_auth.bin').read_bytes())
                    if client.metadata['provenance']['model_fingerprint'] != entry['fp']:
                        raise ValueError('Tensor scene fingerprint differs from actual model inspection')
                    self.tensor_clients[index] = client
                    entry['scene_id'] = index
                self.tensor_router = TensorSceneRouter(self.tensor_clients)
                if self.solid_geometry:
                    from contact_solver.solid_witness_loss import SolidSceneRouter
                    self.solid_router = SolidSceneRouter({index: client.metadata['solid_geometry']
                        for index, client in self.tensor_clients.items()}, self.tensor_router.link_names)
            return self
        except Exception:
            self.__exit__(None,None,None); raise

    def __exit__(self,*unused):
        for client in self.tensor_clients.values():
            try: client.close()
            except (EOFError, BrokenPipeError, OSError): pass
        for p in self.processes:
            if p.poll() is None: p.terminate()
        for p in self.processes: p.wait(timeout=30)
        for log in self.logs: log.close()

    def target_interval_provider(self):
        if not self.tensor_transport or not self.solid_geometry:
            raise ValueError('Coherent target intervals require actual tensor and complete-solid scenes')
        if not hasattr(self,'_target_interval_provider'):
            from contact_solver.shape_target_interval import ShapeTargetIntervalProvider
            self._target_interval_provider=ShapeTargetIntervalProvider(self.position_router.metadata,self.solid_router)
        return self._target_interval_provider

    def target_interval(self,model,rows,active,surface,scene,scene_ids):
        return self.target_interval_provider()(model,rows,active,surface,scene,scene_ids)
