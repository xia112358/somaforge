import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import URDFLoader from 'urdf-loader';
import { ContactDragController } from './contact/drag-controller';
import { ContactHandleLayer } from './contact/handle-layer';
import { contactPositionOffset, formatPositionOffset, POSITION_OFFSET_EPSILON_M } from './contact/offset';
import { api } from './core/api';
import type { EditHandle, Generation, MotionItem, RecentMotion, Session, Vec3 } from './core/types';
import { formatTimelineTime, frameToX, getTimelineMetrics, renderTimeline, xToFrame } from './timeline/renderer';
import { mountAppShell, refreshIcons } from './ui/app-shell';
import { byId, setupTabs } from './ui/dom';
import './theme.css';

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('missing #app root');
mountAppShell(app);
setupTabs();
const sceneCanvas = document.querySelector<HTMLCanvasElement>('#scene')!;
const timeline = document.querySelector<HTMLCanvasElement>('#timeline')!;
const renderer = new THREE.WebGLRenderer({ canvas: sceneCanvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = false;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1016);
scene.fog = new THREE.Fog(0x0b1016, 9, 20);
scene.up.set(0, 0, 1);
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
camera.up.set(0, 0, 1);
camera.position.set(3.2, -4.5, 2.7);
const controls = new OrbitControls(camera, sceneCanvas);
controls.target.set(0, 0, 0.9);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xf4fbff, 0x17202a, 2.4));
const sun = new THREE.DirectionalLight(0xffffff, 3.1); sun.position.set(3, -4, 7); scene.add(sun);
const grid = new THREE.GridHelper(14, 28, 0x33404c, 0x1d2730); grid.rotation.x = Math.PI / 2; scene.add(grid);

let session: Session | null = null;
let robot: any = null;
let terrain: THREE.Object3D | null = null;
let surfaceGroup = new THREE.Group(); scene.add(surfaceGroup);
const contactHandleLayer = new ContactHandleLayer(sceneCanvas, camera);
scene.add(contactHandleLayer.handles, contactHandleLayer.restoreGhosts);
let contactSampleGroup = new THREE.Group(); scene.add(contactSampleGroup);
let guideGroup = new THREE.Group(); scene.add(guideGroup);
let rootPath: THREE.Line | null = null;
let selectedHandle: EditHandle | null = null;
let frame = 0, playing = false, lastTick = performance.now(), frameAccumulator = 0;
let statusFilter = 'all', anchorSearch = '', currentOnly = true;
let resizingTimeline = false;
let scrubbingTimeline = false;
let generationPoll: number | null = null;
let openingMotion = false;
const partColors = [0x18b6a4, 0x68d391, 0xf06449, 0xffb547, 0x4f8cff, 0xb678e6, 0x31a7d8, 0xe05a9d];
const partParent: Record<string, string> = {
  LHEE:'left_foot', LTOE:'left_foot', RHEE:'right_foot', RTOE:'right_foot',
  LH:'left_hand', RH:'right_hand', LK:'left_knee', RK:'right_knee',
  left_heel:'left_foot', left_toe:'left_foot', right_heel:'right_foot', right_toe:'right_foot',
  left_hand:'left_hand', right_hand:'right_hand', left_knee:'left_knee', right_knee:'right_knee',
};

const savedTimelineHeight=Number(localStorage.getItem('motion-edit.timeline-height'));
let timelineHeight=Number.isFinite(savedTimelineHeight)&&savedTimelineHeight>0?savedTimelineHeight:(window.innerWidth<=760?200:230);
function setTimelineHeight(value:number,persist=false){timelineHeight=Math.max(150,Math.min(window.innerHeight*.48,Math.round(value)));document.documentElement.style.setProperty('--timeline-height',`${timelineHeight}px`);if(persist)localStorage.setItem('motion-edit.timeline-height',String(timelineHeight));resize();}
setTimelineHeight(timelineHeight);

async function refreshRecentMotions() {
  const data = await api<{ items: RecentMotion[]; active_motion_id: string | null }>('/api/recent-motions');
  const list = byId('recentMotionList');
  byId('recentMotionCount').textContent = String(data.items.length);
  const buttons = data.items.map(item => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `recent-motion-item${item.motion_id === data.active_motion_id ? ' active' : ''}`;
    button.dataset.motionKey = item.motion_id;
    button.setAttribute('aria-pressed', String(item.motion_id === data.active_motion_id));
    const marker = document.createElement('span');
    marker.className = 'recent-motion-marker';
    const copy = document.createElement('span');
    copy.className = 'recent-motion-copy';
    const label = document.createElement('strong');
    label.textContent = item.label;
    const kind = document.createElement('small');
    kind.textContent = item.provenance;
    copy.append(label, kind);
    button.append(marker, copy);
    button.onclick = () => { void openMotion(item.motion_id); };
    return button;
  });
  list.replaceChildren(...buttons);
  return data.items;
}

function markRecentMotionActive(motionKey: string) {
  document.querySelectorAll<HTMLButtonElement>('.recent-motion-item').forEach(button => {
    const active = button.dataset.motionKey === motionKey;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}

async function openMotion(motionId: string, generated = false) {
  if (openingMotion || session?.motion_id === motionId) return;
  openingMotion = true;
  document.querySelectorAll<HTMLButtonElement>('.recent-motion-item').forEach(button=>button.disabled=true);
  try {
    showStatus(generated ? 'Opening generated motion' : 'Opening motion');
    const next = await api<Session>('/api/session/load', { method: 'POST', body: JSON.stringify({ motion_id: motionId }) });
    frame = Math.min(frame, next.qpos.length - 1);
    await applySession(next, true);
    await refreshRecentMotions();
    if (generated) showStatus('Generated motion opened');
  } catch (error) {
    showStatus(String(error), true);
  } finally {
    openingMotion = false;
    document.querySelectorAll<HTMLButtonElement>('.recent-motion-item').forEach(button=>button.disabled=session?.generation.status==='running');
  }
}

async function loadMotions() {
  const data = await api<{ motions: MotionItem[] }>('/api/motions');
  try {
    const current = await api<Session>('/api/session');
    await applySession(current, true);
    await refreshRecentMotions();
  } catch {
    const recent = await refreshRecentMotions();
    const target = recent[0];
    if (target) await openMotion(target.motion_id);
    else {
      const motion = data.motions.find(item => item.ready);
      if (motion) await openMotion(motion.motion_id);
    }
  }
}

async function applySession(next: Session, rebuildScene = false) {
  const selectedId = selectedHandle?.handle_id;
  session = next; selectedHandle = selectedId ? next.edit_handles.find(handle => handle.handle_id === selectedId) || null : null; frame = Math.min(frame, next.qpos.length - 1);
  markRecentMotionActive(next.motion_id);
  const motionLabel = next.motion_id;
  byId('motionLabel').textContent = motionLabel;
  byId('viewportMotion').textContent = motionLabel;
  byId<HTMLInputElement>('fpsInput').value = String(next.fps);
  byId('anchorCount').textContent = next.read_only ? 'Playback only' : `${next.edit_handles.length} handles`;
  byId('editCount').textContent = next.read_only ? 'No contact layer' : `${next.pending_edit_count} edits`;
  byId<HTMLButtonElement>('undoBtn').disabled = !next.can_undo;
  byId<HTMLButtonElement>('redoBtn').disabled = !next.can_redo;
  byId<HTMLInputElement>('planPath').value = next.settings.edit_plan_path || '';
  byId<HTMLInputElement>('outputMotion').value = next.settings.output_motion_path || '';
  byId<HTMLInputElement>('outputLayer').value = next.settings.output_contact_layer || '';
  byId<HTMLInputElement>('outputSegment').value = next.settings.output_segment_layer || '';
  byId<HTMLInputElement>('outputMotionId').value = next.settings.output_motion_id || '';
  byId<HTMLInputElement>('registerMotion').checked = next.settings.register_motion;
  byId<HTMLInputElement>('overwriteOutput').checked = next.settings.overwrite;
  byId('sourceLayer').textContent = next.settings.source_contact_layer || 'None';
  byId('planStatus').textContent = next.read_only
    ? 'Read-only kinematic reference'
    : next.plan ? `${next.plan.status} · ${next.plan.edit_count} edits` : 'No plan saved';
  renderGeneration(next.generation);
  renderLegend(); drawTimeline();
  if (rebuildScene) await rebuild(next);
  else { rebuildHandles(); if (selectedHandle) selectHandle(selectedHandle); }
  setFrame(frame);
}

async function rebuild(data: Session) {
  byId('sceneStatus').textContent = 'Loading scene'; byId('sceneStatus').classList.remove('hidden');
  if (robot) scene.remove(robot); if (terrain) scene.remove(terrain);
  surfaceGroup.clear(); surfaceGroup.visible=byId<HTMLInputElement>('surfaceToggle').checked; contactHandleLayer.clear(); contactSampleGroup.clear(); guideGroup.clear(); selectedHandle = null;
  delete sceneCanvas.dataset.selectedHandleX;delete sceneCanvas.dataset.selectedHandleY;delete sceneCanvas.dataset.selectedHandleId;
  if(rootPath){scene.remove(rootPath);rootPath=null;}
  const loadingManager = new THREE.LoadingManager();
  const robotAssetsLoaded = new Promise<void>((resolve, reject) => {
    loadingManager.onLoad = () => resolve();
    loadingManager.onError = url => reject(new Error(`failed to load robot asset: ${url}`));
  });
  const urdfLoader = new URDFLoader(loadingManager);
  urdfLoader.loadMeshCb = (path: string, manager: THREE.LoadingManager, done: (mesh: THREE.Object3D, error?: Error) => void) => {
    if (path.toLowerCase().endsWith('.obj')) {
      new OBJLoader(manager).load(path, object => done(object), undefined, error => done(new THREE.Group(), error as Error));
      return;
    }
    done(new THREE.Group(), new Error(`unsupported URDF mesh: ${path}`));
  };
  robot = await urdfLoader.loadAsync(data.robot_urdf_url);
  await robotAssetsLoaded;
  let robotMeshCount = 0;
  robot.traverse((obj: any) => { if (obj.isMesh) robotMeshCount++; });
  sceneCanvas.dataset.robotMeshes = String(robotMeshCount);
  scene.add(robot);
  if (data.terrain_obj_url) {
    terrain = await new OBJLoader().loadAsync(data.terrain_obj_url);
    terrain.traverse((obj: any) => { if (obj.isMesh) obj.material = new THREE.MeshStandardMaterial({ color: 0x596570, roughness: .86, metalness: .03 }); });
    scene.add(terrain);
  }
  buildSurfaces(); buildRootPath(); buildContactSamples(); rebuildHandles(); focusScene();
  byId('sceneStatus').classList.add('hidden');
}

function buildRootPath(){
  if(!session)return;const points=session.qpos.map(q=>new THREE.Vector3(q[0],q[1],q[2]));
  rootPath=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0xaeb7c2,transparent:true,opacity:.45}));rootPath.visible=byId<HTMLInputElement>('rootPathToggle').checked;scene.add(rootPath);
}

function buildSurfaces() {
  if (!session) return;
  for (const surface of session.surfaces) {
    if (surface.surface_id === 'terrain_ground_z0') continue;
    const offset = new THREE.Vector3(...surface.normal).normalize().multiplyScalar(.002);
    const polygon = surface.metadata.polygon_world as number[][] | undefined;
    let vertices: THREE.Vector3[];
    if (polygon?.length && polygon.length >= 3) {
      vertices = polygon.map(point => new THREE.Vector3(point[0], point[1], point[2]).add(offset));
    } else {
      const o = new THREE.Vector3(...surface.origin), u = new THREE.Vector3(...surface.tangent_u), v = new THREE.Vector3(...surface.tangent_v);
      const [u0,u1] = surface.bounds.u, [v0,v1] = surface.bounds.v;
      vertices = [o.clone().addScaledVector(u,u0).addScaledVector(v,v0), o.clone().addScaledVector(u,u1).addScaledVector(v,v0), o.clone().addScaledVector(u,u1).addScaledVector(v,v1), o.clone().addScaledVector(u,u0).addScaledVector(v,v1)].map(point => point.add(offset));
    }
    const indices: number[] = []; for (let i = 1; i < vertices.length - 1; i++) indices.push(0, i, i + 1);
    const geo = new THREE.BufferGeometry().setFromPoints(vertices); geo.setIndex(indices); geo.computeVertexNormals();
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0x4d9fbd, transparent: true, opacity: .08, side: THREE.DoubleSide, depthWrite: false }));
    mesh.userData.surface = surface; surfaceGroup.add(mesh);
  }
}

function handleStatus(handle: EditHandle) { return String(handle.metadata.surface_editor_status || 'bound'); }
function activeAt(handle: EditHandle) { return frame >= handle.start_frame && frame < handle.end_frame; }
function updatePositionOffset(handle:EditHandle|null,preview?:THREE.Vector3){
  const panel=byId('positionOffset');
  if(!handle){panel.classList.add('disabled');panel.classList.remove('edited');byId('offsetU').textContent='—';byId('offsetV').textContent='—';return;}
  const {u,v}=contactPositionOffset(handle,preview);
  panel.classList.remove('disabled');panel.classList.toggle('edited',Math.max(Math.abs(u),Math.abs(v))>POSITION_OFFSET_EPSILON_M);
  byId('offsetU').textContent=formatPositionOffset(u);byId('offsetV').textContent=formatPositionOffset(v);
}
function matchingHandles() {
  if (!session) return [];
  const query = anchorSearch.trim().toLowerCase();
  return session.edit_handles.filter(handle => {
    const status = handleStatus(handle);
    if (currentOnly && !activeAt(handle)) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    const sources=Array.isArray(handle.metadata.source_bodies)?handle.metadata.source_bodies.join(' '):'';
    const roles=Array.isArray(handle.metadata.patch_roles)?handle.metadata.patch_roles.join(' '):'';
    return !query || `${handle.handle_id} ${handle.body} ${handle.surface_id} ${handle.object_id || ''} ${sources} ${roles}`.toLowerCase().includes(query);
  });
}
function rebuildHandles() {
  if (!session) return;
  const visible = new Set(matchingHandles().map(handle => handle.handle_id));
  contactHandleLayer.rebuild({
    handles: session.edit_handles,
    visibleHandleIds: visible,
    selectedHandle,
    radius: Number(byId<HTMLInputElement>('handleSize').value) / 1000,
  });
  contactHandleLayer.setVisible(byId<HTMLInputElement>('handleToggle').checked);
}

function buildContactSamples() {
  if (!session) return; contactSampleGroup.clear();sceneCanvas.dataset.contactSample='point-force';
  const sampleCount=session.contact_force.part_order.length;
  sceneCanvas.dataset.contactPartSlots=String(sampleCount);
  for(let i=0;i<sampleCount;i++){
    const group=new THREE.Group();const material=new THREE.MeshBasicMaterial({color:partColors[i%partColors.length],depthTest:true,transparent:true});
    const point=new THREE.Mesh(new THREE.SphereGeometry(.014,14,10),material);
    const shaft=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,1,8),material);const head=new THREE.Mesh(new THREE.ConeGeometry(.022,.055,10),material);
    group.add(point,shaft,head);group.userData.point=point;group.userData.shaft=shaft;group.userData.head=head;group.userData.material=material;contactSampleGroup.add(group);
  }
  updateContactSamples();
}

function updateContactSamples() {
  if (!session) return;
  const currentSession=session;
  contactSampleGroup.visible = byId<HTMLInputElement>('contactSampleToggle').checked;
  const points=currentSession.contact_force.positions[frame]||[],forces=currentSession.contact_force.forces[frame]||[];
  const masks=currentSession.contact_force.masks[frame]||[],valid=currentSession.contact_force.position_valid[frame]||[];
  let visibleCount=0;
  contactSampleGroup.children.forEach((obj, i) => {
    const glyph=obj as THREE.Group, visible = i<points.length&&i<forces.length&&Boolean(masks[i])&&Boolean(valid[i]);
    glyph.visible = visible; if (!visible) return;
    visibleCount++;
    const f = new THREE.Vector3(...forces[i]); const mag = f.length();
    const scale = Number(byId<HTMLInputElement>('forceScale').value) / 100;
    const length=Math.min(.9,mag/1200*scale),headLength=Math.min(.055,length*.35),shaftLength=Math.max(.001,length-headLength);
    glyph.position.set(...points[i]);if(mag>1e-5)glyph.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),f.normalize());
    const body=partParent[currentSession.contact_force.part_order[i]]||currentSession.contact_force.part_order[i];
    const emphasized=!selectedHandle||selectedHandle.body===body;
    glyph.scale.setScalar(selectedHandle&&emphasized?1.35:1);
    const material=glyph.userData.material as THREE.MeshBasicMaterial;material.opacity=emphasized?1:.22;
    const shaft=glyph.userData.shaft as THREE.Mesh,head=glyph.userData.head as THREE.Mesh;shaft.scale.set(1,shaftLength,1);shaft.position.set(0,shaftLength/2,0);head.scale.set(1,headLength/.055,1);head.position.set(0,shaftLength+headLength/2,0);
    shaft.visible=mag>1e-5;head.visible=mag>1e-5;
  });
  sceneCanvas.dataset.visibleContactParts=String(visibleCount);
  sceneCanvas.dataset.selectedContactBody=selectedHandle?.body||'';
}

function applyRobotFrame() {
  if (!session || !robot) return; const q = session.qpos[frame];
  robot.position.set(q[0],q[1],q[2]); robot.quaternion.set(q[4],q[5],q[6],q[3]);
  session.joint_names.forEach((name,i) => robot.setJointValue?.(name,q[7+i]));
}

function setFrame(value: number) {
  if (!session) return; frame = Math.max(0, Math.min(session.qpos.length - 1, Math.round(value)));
  byId<HTMLInputElement>('frameInput').value = String(frame); byId('frameTotal').textContent = `/ ${session.qpos.length - 1}`;
  byId('viewportFrame').textContent = `Frame ${frame}`; byId('viewportTime').textContent = `${(frame / session.fps).toFixed(2)} s`;
  applyRobotFrame(); updateContactSamples(); rebuildHandles(); drawTimeline();
}

function timelineMetrics() {
  return getTimelineMetrics(timeline, session?.contact_force.part_order.length ?? 8);
}

function frameToTimelineX(value: number, metrics: ReturnType<typeof timelineMetrics>) {
  return frameToX(value, metrics, session?.qpos.length ?? 1);
}

function timelineXToFrame(value: number, metrics: ReturnType<typeof timelineMetrics>) {
  return xToFrame(value, metrics, session?.qpos.length ?? 1);
}

function drawTimeline() {
  renderTimeline({ canvas: timeline, session, frame, selectedHandle, stableCuts: stableCutFrames(), partColors });
}
function stableCutFrames() {
  if (!session) return [];
  const values = new Set<number>();
  session.graph.transitions.forEach(t => { values.add(t.start_frame); values.add(Math.max(t.start_frame,t.end_frame-1)); const stable=t.metadata?.stable_anchor_frames; if(Array.isArray(stable)) stable.forEach(value=>values.add(Number(value))); });
  return [...values].filter(value=>Number.isFinite(value)).sort((a,b)=>a-b);
}

function renderLegend() {
  if (!session) return; byId('partLegend').innerHTML=session.contact_force.part_order.map((name,i)=>`<span><b style="background:#${partColors[i].toString(16).padStart(6,'0')}"></b>${name}</span>`).join('');
}

function selectHandle(handle: EditHandle | null) {
  selectedHandle=handle; const box=byId('selection');
  if(!handle){box.className='selection empty';box.textContent='None';updatePositionOffset(null);guideGroup.clear();updateContactSamples();drawTimeline();updateSelectedHandleProjection();return;}
  box.className='selection'; box.innerHTML=`<strong>${handle.body}</strong><code>${handle.handle_id}</code><dl><dt>Frames</dt><dd>${handle.start_frame}–${handle.end_frame}</dd><dt>Surface</dt><dd>${handle.surface_id}</dd><dt>Members</dt><dd>${String(handle.metadata.member_count||handle.member_anchor_ids.length)}</dd><dt>Status</dt><dd>${handleStatus(handle)}</dd></dl>`;
  updatePositionOffset(handle);
  renderSelectionGuides(handle);updateContactSamples();
  rebuildHandles();drawTimeline();updateSelectedHandleProjection();
}

function renderSelectionGuides(handle:EditHandle){
  guideGroup.clear();guideGroup.visible=byId<HTMLInputElement>('guideToggle').checked;
  const origin=new THREE.Vector3(...handle.world_position);const vectors:[[Vec3,number],[Vec3,number],[Vec3,number]]=[[handle.surface_tangent_u,0xf06449],[handle.surface_tangent_v,0x68d391],[handle.surface_normal,0x4f8cff]];
  for(const [raw,color] of vectors){const v=new THREE.Vector3(...raw).normalize().multiplyScalar(.14);const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([origin.clone().addScaledVector(v,-1),origin.clone().add(v)]),new THREE.LineBasicMaterial({color}));guideGroup.add(line);}
}

const contactDragController = new ContactDragController({
  canvas: sceneCanvas,
  controls,
  layer: contactHandleLayer,
  getSession: () => session,
  getSelectedHandle: () => selectedHandle,
  selectHandle,
  updatePositionOffset,
  rebuildHandles,
  restoreHandle: async handle => Boolean(await runSessionAction('/api/session/restore-handle', {
    handle_id: handle.handle_id,
    mode: byId<HTMLSelectElement>('modeSelect').value,
  })),
  moveHandle: async (handle, requestedPosition) => {
    try {
      showStatus('Moving contact episode');
      const next = await api<Session>('/api/session/move-handle', {
        method: 'POST',
        body: JSON.stringify({
          handle_id: handle.handle_id,
          requested_world_position: requestedPosition.toArray(),
          mode: byId<HTMLSelectElement>('modeSelect').value,
        }),
      });
      selectedHandle = next.edit_handles.find(item => item.handle_id === handle.handle_id) || null;
      await applySession(next);
      showStatus('Contact episode moved');
      return true;
    } catch (error) {
      showStatus(String(error), true);
      return false;
    }
  },
});

function focusScene(){const box=new THREE.Box3();if(robot)box.expandByObject(robot);if(terrain)box.expandByObject(terrain);if(box.isEmpty())return;const sphere=box.getBoundingSphere(new THREE.Sphere());controls.target.copy(sphere.center);camera.position.copy(sphere.center).add(new THREE.Vector3(sphere.radius*1.8,-sphere.radius*2.4,sphere.radius*1.35));controls.update();}
function showStatus(text:string,error=false){const el=byId('sceneStatus');el.textContent=text;el.classList.remove('hidden');el.classList.toggle('error',error);setTimeout(()=>el.classList.add('hidden'),3000);}
function generationSettings(){return {
  edit_plan_path:byId<HTMLInputElement>('planPath').value,
  output_motion_path:byId<HTMLInputElement>('outputMotion').value,
  output_contact_layer:byId<HTMLInputElement>('outputLayer').value,
  output_segment_layer:byId<HTMLInputElement>('outputSegment').value,
  output_motion_id:byId<HTMLInputElement>('outputMotionId').value,
  register_motion:byId<HTMLInputElement>('registerMotion').checked,
  overwrite:byId<HTMLInputElement>('overwriteOutput').checked,
};}
async function syncOutputSettings(){const next=await api<Session>('/api/session/settings',{method:'PUT',body:JSON.stringify(generationSettings())});session=next;return next;}
function stopGenerationPoll(){if(generationPoll!==null){window.clearInterval(generationPoll);generationPoll=null;}}
function pollGeneration(){if(generationPoll!==null)return;generationPoll=window.setInterval(async()=>{try{const next=await api<Generation>('/api/session/generation');renderGeneration(next);if(next.status!=='running'){stopGenerationPoll();if(next.status==='succeeded'){byId('planStatus').textContent='generated';if(next.output_motion_id)await openMotion(next.output_motion_id,true);else await refreshRecentMotions();}}}catch(e){stopGenerationPoll();showStatus(String(e),true);}},900);}
function renderGeneration(job:Generation){
  const running=job.status==='running',readOnly=Boolean(session?.read_only),button=byId<HTMLButtonElement>('generateBtn'),status=byId('generationStatus');button.disabled=running||!session||readOnly;
  button.innerHTML=running?'<i data-lucide="loader-circle" class="spin"></i><span>Generating</span>':'<i data-lucide="wand-sparkles"></i><span>Generate</span>';refreshIcons();
  status.className=`generation-status ${job.status}`;
  if(job.status==='running'){
    const labels:Record<string,string>={queued:'Queued',reading_plan:'Reading edit plan',validating:'Validating',loading_motion:'Loading motion',contact_laplacian:'Optimizing contact trajectory',writing_intermediates:'Preparing full-body IK',fullbody_ik:'Solving full-body IK',merging_ik:'Merging IK result',writing_output:'Writing motion',registering:'Registering motion',saving_plan:'Saving edit plan'};
    const elapsed=job.started_at===null?'':` · ${Math.max(0,Math.round(Date.now()/1000-job.started_at))}s`;
    status.innerHTML='<strong>Generating reference</strong><span></span>';status.querySelector('span')!.textContent=`${labels[job.stage||'']||'Working'}${elapsed}`;
  }
  else if(job.status==='succeeded'){byId<HTMLInputElement>('overwriteOutput').checked=true;status.innerHTML=`<strong>Generated${job.warnings.length?` · ${job.warnings.length} warnings`:''}</strong><span></span>`;status.querySelector('span')!.textContent=job.output_motion_path||'Output written';status.setAttribute('title',job.output_motion_path||'');}
  else if(job.status==='failed'){status.innerHTML='<strong>Generation failed</strong><span></span>';status.querySelector('span')!.textContent=job.error||'Unknown error';status.setAttribute('title',job.error||'');}
  else if(readOnly)status.innerHTML='<strong>Playback only</strong><span>Kinematic reference · no contact layer</span>';
  else status.innerHTML='<strong>Ready</strong><span>Formal edited reference</span>';
  document.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLButtonElement>('.tab-page input,.tab-page select,.tab-page button').forEach(control=>control.disabled=running);
  document.querySelectorAll<HTMLButtonElement>('.recent-motion-item').forEach(control=>control.disabled=running||openingMotion);
  byId<HTMLButtonElement>('undoBtn').disabled=running||readOnly||!(session?.can_undo);
  byId<HTMLButtonElement>('redoBtn').disabled=running||readOnly||!(session?.can_redo);
  byId<HTMLButtonElement>('saveBtn').disabled=running||readOnly;
  byId<HTMLButtonElement>('validateBtn').disabled=running||readOnly;
  byId<HTMLButtonElement>('generateBtn').disabled=running||readOnly||!session;
  byId<HTMLButtonElement>('discardBtn').disabled=running||readOnly;
  document.querySelectorAll<HTMLInputElement>('[data-generation-setting]').forEach(control=>control.disabled=running||readOnly);
  byId<HTMLInputElement>('outputMotionId').disabled=running||readOnly||!byId<HTMLInputElement>('registerMotion').checked;
  if(running)pollGeneration();else stopGenerationPoll();
}

function setPlaying(next:boolean){
  playing=next;
  if(!playing)frameAccumulator=0;
  byId('playBtn').innerHTML=`<i data-lucide="${playing?'pause':'play'}"></i>`;
  refreshIcons();
}
byId('playBtn').onclick=()=>setPlaying(!playing);
byId('prevBtn').onclick=()=>setFrame(frame-1);byId('nextBtn').onclick=()=>setFrame(frame+1);
byId<HTMLInputElement>('frameInput').onchange=e=>setFrame(Number((e.target as HTMLInputElement).value));
async function runSessionAction(path:string, body?:unknown){try{const next=await api<Session>(path,{method:'POST',body:body===undefined?undefined:JSON.stringify(body)});await applySession(next);return next;}catch(e){showStatus(String(e),true);return null;}}
byId('undoBtn').onclick=()=>{void runSessionAction('/api/session/undo');};byId('redoBtn').onclick=()=>{void runSessionAction('/api/session/redo');};
byId('saveBtn').onclick=async()=>{try{await syncOutputSettings();const result=await api<{output_contact_layer:string;plan:{status:string;edit_count:number}|null}>('/api/session/save',{method:'POST'});if(result.plan)byId('planStatus').textContent=`${result.plan.status} · ${result.plan.edit_count} edits`;showStatus(`Saved ${result.output_contact_layer}`);}catch(e){showStatus(String(e),true);}};
byId('focusBtn').onclick=focusScene;byId<HTMLInputElement>('terrainToggle').onchange=e=>{if(terrain)terrain.visible=(e.target as HTMLInputElement).checked;surfaceGroup.visible=(e.target as HTMLInputElement).checked;};
byId<HTMLInputElement>('surfaceToggle').onchange=e=>surfaceGroup.visible=(e.target as HTMLInputElement).checked;
byId<HTMLInputElement>('handleToggle').onchange=e=>contactHandleLayer.setVisible((e.target as HTMLInputElement).checked);byId<HTMLInputElement>('contactSampleToggle').onchange=e=>contactSampleGroup.visible=(e.target as HTMLInputElement).checked;byId<HTMLInputElement>('handleSize').oninput=()=>rebuildHandles();byId<HTMLInputElement>('forceScale').oninput=()=>updateContactSamples();
byId<HTMLInputElement>('rootPathToggle').onchange=e=>{if(rootPath)rootPath.visible=(e.target as HTMLInputElement).checked;};byId<HTMLInputElement>('guideToggle').onchange=e=>guideGroup.visible=(e.target as HTMLInputElement).checked;
byId<HTMLInputElement>('anchorSearch').oninput=e=>{anchorSearch=(e.target as HTMLInputElement).value;rebuildHandles();};
byId<HTMLSelectElement>('statusFilter').onchange=e=>{statusFilter=(e.target as HTMLSelectElement).value;rebuildHandles();};
byId<HTMLInputElement>('currentOnly').onchange=e=>{currentOnly=(e.target as HTMLInputElement).checked;rebuildHandles();};
function selectRelativeAnchor(offset:number){const items=matchingHandles();if(!items.length)return;const current=Math.max(0,items.findIndex(item=>item.handle_id===selectedHandle?.handle_id));const handle=items[(current+offset+items.length)%items.length];selectHandle(handle);setFrame(handle.start_frame);}
byId('prevAnchor').onclick=()=>selectRelativeAnchor(-1);byId('nextAnchor').onclick=()=>selectRelativeAnchor(1);

function selectRelativeCut(offset:number){const cuts=stableCutFrames();if(!cuts.length)return;const ordered=offset>0?cuts:cuts.slice().reverse();const next=ordered.find(value=>offset>0?value>frame:value<frame) ?? ordered[0];setFrame(next);}
byId('prevCut').onclick=()=>selectRelativeCut(-1);byId('nextCut').onclick=()=>selectRelativeCut(1);
function timelinePointer(event:PointerEvent,updateFrame=false,selectLane=false){
  if(!session)return;const rect=timeline.getBoundingClientRect(),m=timelineMetrics(),localX=event.clientX-rect.left,localY=event.clientY-rect.top,next=timelineXToFrame(localX,m);
  if(updateFrame&&localX>=m.labelW)setFrame(next);
  const lane=Math.floor((localY-m.rulerH)/m.rowH);
  if(selectLane&&lane>=0&&lane<session.contact_force.part_order.length){const body=partParent[session.contact_force.part_order[lane]],candidates=session.edit_handles.filter(handle=>handle.body===body&&activeAt(handle));if(candidates.length)selectHandle(candidates[0]);}
  const hover=byId('timelineHover'),part=lane>=0&&lane<session.contact_force.part_order.length?session.contact_force.part_order[lane]:'Timeline';hover.textContent=`${part} · ${formatTimelineTime(next/session.fps)} · frame ${next}`;hover.style.left=`${Math.max(m.labelW+44,Math.min(rect.width-72,localX))}px`;hover.classList.remove('hidden');
}
timeline.addEventListener('pointerdown',event=>{if(!session)return;setPlaying(false);scrubbingTimeline=true;timeline.setPointerCapture(event.pointerId);timeline.classList.add('scrubbing');timelinePointer(event,true,true);});
timeline.addEventListener('pointermove',event=>timelinePointer(event,scrubbingTimeline,false));
timeline.addEventListener('pointerup',event=>{if(!scrubbingTimeline)return;scrubbingTimeline=false;timeline.releasePointerCapture(event.pointerId);timeline.classList.remove('scrubbing');});
timeline.addEventListener('pointercancel',()=>{scrubbingTimeline=false;timeline.classList.remove('scrubbing');});
timeline.addEventListener('pointerleave',()=>{if(!scrubbingTimeline)byId('timelineHover').classList.add('hidden');});

document.querySelectorAll<HTMLInputElement>('#planPath,#outputMotion,#outputLayer,#outputSegment,#outputMotionId,#registerMotion,#overwriteOutput').forEach(input=>{input.dataset.generationSetting='';input.addEventListener('change',()=>{byId<HTMLInputElement>('outputMotionId').disabled=!byId<HTMLInputElement>('registerMotion').checked;void syncOutputSettings().catch(e=>showStatus(String(e),true));});});
byId('validateBtn').onclick=async()=>{try{await syncOutputSettings();const result=await api<{plan:{status:string};warnings:string[]}>('/api/session/validate',{method:'POST'});byId('planStatus').textContent=`${result.plan.status}${result.warnings.length?` · ${result.warnings.length} warnings`:''}`;showStatus('ContactEditPlan validated');}catch(e){showStatus(String(e),true);}};
byId('generateBtn').onclick=async()=>{try{await syncOutputSettings();const job=await api<Generation>('/api/session/generate',{method:'POST',body:JSON.stringify(generationSettings())});renderGeneration(job);}catch(e){try{renderGeneration(await api<Generation>('/api/session/generation'));}catch{renderGeneration({status:'failed',stage:'preflight',output_motion_path:byId<HTMLInputElement>('outputMotion').value||null,output_motion_id:byId<HTMLInputElement>('outputMotionId').value||null,warnings:[],error:String(e),started_at:null,finished_at:Date.now()/1000});}}};
byId('reloadBtn').onclick=()=>{void runSessionAction('/api/session/reload');};byId('discardBtn').onclick=()=>{void runSessionAction('/api/session/discard');};

window.addEventListener('keydown',event=>{if(event.code==='Escape'&&contactDragController.active){event.preventDefault();contactDragController.cancel();return;}if((event.target as HTMLElement).matches('input,select,textarea'))return;if(event.code==='Space'){event.preventDefault();byId<HTMLButtonElement>('playBtn').click();}else if(event.code==='ArrowLeft')setFrame(frame-(event.shiftKey?10:1));else if(event.code==='ArrowRight')setFrame(frame+(event.shiftKey?10:1));else if(event.code==='BracketLeft')selectRelativeAnchor(-1);else if(event.code==='BracketRight')selectRelativeAnchor(1);});

let resizeStartY=0,resizeStartHeight=0;
byId('timelineResizer').addEventListener('pointerdown',event=>{resizingTimeline=true;resizeStartY=event.clientY;resizeStartHeight=timelineHeight;byId('timelineResizer').setPointerCapture(event.pointerId);document.body.classList.add('resizing-timeline');});
byId('timelineResizer').addEventListener('pointermove',event=>{if(resizingTimeline)setTimelineHeight(resizeStartHeight+resizeStartY-event.clientY);});
byId('timelineResizer').addEventListener('pointerup',event=>{if(!resizingTimeline)return;resizingTimeline=false;byId('timelineResizer').releasePointerCapture(event.pointerId);document.body.classList.remove('resizing-timeline');setTimelineHeight(timelineHeight,true);});

function resize(){const r=sceneCanvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();drawTimeline();}
window.addEventListener('resize',resize);resize();
function updateSelectedHandleProjection(){
  contactHandleLayer.updateProjection(selectedHandle);
}
function animate(now:number){requestAnimationFrame(animate);const dt=(now-lastTick)/1000;lastTick=now;if(playing&&session){frameAccumulator+=dt*Number(byId<HTMLInputElement>('fpsInput').value);if(frameAccumulator>=1){const step=Math.floor(frameAccumulator);frameAccumulator-=step;setFrame((frame+step)%session.qpos.length);}}controls.update();updateSelectedHandleProjection();renderer.render(scene,camera);}requestAnimationFrame(animate);
loadMotions().catch(e=>showStatus(String(e),true));
