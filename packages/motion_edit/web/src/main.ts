import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import URDFLoader from 'urdf-loader';
import { ContactDragController } from './contact/drag-controller';
import { ContactHandleLayer } from './contact/handle-layer';
import { contactPositionOffset, formatPositionOffset, POSITION_OFFSET_EPSILON_M } from './contact/offset';
import { api, ApiError } from './core/api';
import { clearResources, disposeResources } from './core/resources';
import type { EditHandle, Generation, MotionItem, RecentMotion, Session, Vec3 } from './core/types';
import { formatTimelineTime, frameToX, getTimelineMetrics, renderTimeline, xToFrame } from './timeline/renderer';
import { mountAppShell, refreshIcons } from './ui/app-shell';
import { byId, setupTabs } from './ui/dom';
import { Comparison } from './review/comparison';
import { SupportMotionOverlay } from './review/support-motion';
import { SupportSlipOverlay } from './review/support-slip';
import { SequenceComparison } from './review/sequence-comparison';
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
const supportSlip = new SupportSlipOverlay(scene,points=>{
  const sphere=new THREE.Box3().setFromPoints(points).getBoundingSphere(new THREE.Sphere());
  const direction=camera.position.clone().sub(controls.target).normalize();
  controls.target.copy(sphere.center);camera.position.copy(sphere.center).addScaledVector(direction,Math.max(.45,sphere.radius*5));
  controls.update();
});
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
let actionBusy = false;
let sceneLoading = false;
let statusTimer: number | null = null;
let settingsQueue: Promise<unknown> = Promise.resolve();
let registeredMotions: MotionItem[] = [];
function busy() { return openingMotion || actionBusy || sceneLoading || session?.generation.status === 'running'; }
async function exclusive<T>(operation: () => Promise<T>): Promise<T | null> {
  if (busy()) return null;
  actionBusy = true;
  contactDragController.cancel();
  updateControls();
  try { await settingsQueue; return await operation(); }
  catch (error) { showStatus(String(error), true); return null; }
  finally { actionBusy = false; updateControls(); }
}
const comparison = new Comparison(scene, q => { if(session) { session.qpos = [q]; setFrame(0); } });
const sequenceComparison = new SequenceComparison(scene);
const supportMotion = new SupportMotionOverlay(scene, value => setFrame(value), track => {
  const points = track.map(p => new THREE.Vector3(...p));
  const center = new THREE.Box3().setFromPoints(points).getCenter(new THREE.Vector3());
  const direction = camera.position.clone().sub(controls.target).normalize();
  const displacement = points.at(-1)!.clone().sub(points[0]); displacement.z = 0;
  controls.target.copy(center);
  camera.position.copy(center).addScaledVector(direction, displacement.length() < .05 ? .48 : .95);
  controls.update();
});
const partColors = [0x18b6a4, 0x68d391, 0xf06449, 0xffb547, 0x4f8cff, 0xb678e6, 0x31a7d8, 0xe05a9d];
const partParent: Record<string, string> = {
  LHEE:'left_foot', LTOE:'left_foot', RHEE:'right_foot', RTOE:'right_foot',
  LH:'left_hand', RH:'right_hand', LK:'left_knee', RK:'right_knee',
  left_heel:'left_foot', left_toe:'left_foot', right_heel:'right_foot', right_toe:'right_foot',
  left_hand:'left_hand', right_hand:'right_hand', left_knee:'left_knee', right_knee:'right_knee',
};

let savedTimelineHeight = NaN;
try { savedTimelineHeight = Number(localStorage.getItem('motion-edit.timeline-height')); } catch { /* Storage can be unavailable. */ }
let timelineHeight=Number.isFinite(savedTimelineHeight)&&savedTimelineHeight>0?savedTimelineHeight:(window.innerWidth<=760?200:230);
function setTimelineHeight(value:number,persist=false){timelineHeight=Math.max(150,Math.min(window.innerHeight*.48,Math.round(value)));document.documentElement.style.setProperty('--timeline-height',`${timelineHeight}px`);if(persist){try{localStorage.setItem('motion-edit.timeline-height',String(timelineHeight));}catch{ /* Optional preference. */ }}resize();}
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
  if (busy() || session?.motion_id === motionId) return;
  openingMotion = true;
  setPlaying(false);
  contactDragController.cancel();
  updateControls();
  document.querySelectorAll<HTMLButtonElement>('.recent-motion-item').forEach(button=>button.disabled=true);
  try {
    showStatus(generated ? 'Opening generated motion' : 'Opening motion', false, true);
    await settingsQueue;
    const next = await api<Session>('/api/session/load', { method: 'POST', body: JSON.stringify({ motion_id: motionId }) });
    frame = 0;
    await applySession(next, true);
    await refreshRecentMotions();
    hideStatus();
    if (generated) showStatus('Generated candidate opened · native validation required');
  } catch (error) {
    showStatus(String(error), true);
  } finally {
    openingMotion = false;
    updateControls();
  }
}

async function loadMotions() {
  showStatus('Loading motions', false, true);
  byId('retryLoad').hidden = true;
  registeredMotions = (await api<{ motions: MotionItem[] }>('/api/motions')).motions;
  let current: Session | null = null;
  try { current = await api<Session>('/api/session'); }
  catch (error) { if (!(error instanceof ApiError) || error.status !== 404) throw error; }
  if (current) {
    await applySession(current, true);
    await refreshRecentMotions();
    hideStatus();
  } else {
    const recent = await refreshRecentMotions();
    const target = recent[0]?.motion_id || registeredMotions.find(item => item.ready)?.motion_id;
    if (target) await openMotion(target);
    else { showStatus('No motion available. Open a registered motion or a playback file.', false, true); }
  }
}

function renderMotionPicker() {
  const query = byId<HTMLInputElement>('motionSearch').value.trim().toLowerCase();
  const items = registeredMotions.filter(item => `${item.motion_id} ${item.label} ${item.provenance}`.toLowerCase().includes(query));
  const list = byId('motionPickerList');
  list.replaceChildren();
  for (const item of items) {
    const button = document.createElement('button');
    button.className = 'motion-picker-item';
    button.disabled = !item.ready;
    const label = document.createElement('strong'); label.textContent = item.label;
    const detail = document.createElement('small'); detail.textContent = `${item.motion_id} · ${item.provenance} · ${item.ready ? '可打开' : '文件缺失'}`;
    button.append(label, detail);
    button.onclick = () => { byId<HTMLDialogElement>('motionPicker').close(); void openMotion(item.motion_id); };
    list.append(button);
  }
  if (!items.length) list.textContent = '没有匹配的轨迹';
}
byId('openMotionBtn').onclick = async () => {
  if (busy()) return;
  try {
    registeredMotions = (await api<{ motions: MotionItem[] }>('/api/motions')).motions;
    byId<HTMLInputElement>('motionSearch').value = '';
    renderMotionPicker();
    byId<HTMLDialogElement>('motionPicker').showModal();
    byId<HTMLInputElement>('motionSearch').focus();
  } catch (error) { showStatus(String(error), true); }
};
byId('closeMotionPicker').onclick = () => byId<HTMLDialogElement>('motionPicker').close();
byId<HTMLInputElement>('motionSearch').oninput = renderMotionPicker;
byId('retryLoad').onclick = () => { void loadMotions().catch(loadError); };
function loadError(error: unknown) { showStatus(String(error), true); byId('retryLoad').hidden = false; }

async function applySession(next: Session, rebuildScene = false) {
  const selectedId = selectedHandle?.handle_id;
  const previous = session;
  session = next; selectedHandle = selectedId ? next.edit_handles.find(handle => handle.handle_id === selectedId) || null : null; frame = Math.min(frame, next.qpos.length - 1);
  if (rebuildScene && next.review?.kind === 'support_motion' && next.review.phases?.length)
    frame = next.review.phases[0].start;
  document.body.classList.toggle('review-mode', Boolean(next.review));
  document.body.classList.toggle('playback-only', next.read_only);
  byId('contactHeading').textContent = next.read_only ? 'Playback' : 'Contacts';
  if (next.read_only && document.querySelector('[data-tab="output"].active')) {
    document.querySelector<HTMLButtonElement>('[data-tab="contact"]')?.click();
  }
  byId('playbackNotice').hidden = !next.read_only || Boolean(next.review?.notice);
  if (next.contact_force.mask_status && next.contact_force.mask_status !== 'verified_newton_primary_faces') {
    byId('playbackNotice').hidden = Boolean(next.review?.notice);
    byId('playbackNotice').textContent = '接触状态未知：力与旧掩码未经同帧 Newton／主表面验证。' + (next.read_only ? '' : '手柄仅表示编辑意图。');
  } else {
    byId('playbackNotice').textContent = '只读轨迹：接触状态以已验证的 Newton 数据为准；无接触层时不显示编辑手柄。';
  }
  markRecentMotionActive(next.motion_id);
  const motionLabel = next.motion_id;
  byId('motionLabel').textContent = motionLabel;
  byId('viewportMotion').textContent = motionLabel;
  if (rebuildScene || !previous) byId<HTMLInputElement>('fpsInput').value = String(next.fps);
  byId('anchorCount').textContent = next.read_only ? 'Playback only' : `${next.edit_handles.length} handles`;
  byId('editCount').textContent = next.read_only ? (next.review ? 'Contact unknown' : 'No contact layer') : `${next.pending_edit_count} edits`;
  byId<HTMLButtonElement>('undoBtn').disabled = !next.can_undo;
  byId<HTMLButtonElement>('redoBtn').disabled = !next.can_redo;
  byId<HTMLInputElement>('planPath').value = next.settings.edit_plan_path || '';
  byId<HTMLInputElement>('outputMotion').value = next.settings.output_motion_path || '';
  byId<HTMLInputElement>('outputLayer').value = next.settings.output_contact_layer || '';
  byId<HTMLInputElement>('outputMotionId').value = next.settings.output_motion_id || '';
  byId<HTMLInputElement>('registerMotion').checked = next.settings.register_motion;
  byId<HTMLInputElement>('overwriteOutput').checked = next.settings.overwrite;
  byId('sourceLayer').textContent = next.settings.source_contact_layer || 'None';
  byId('planStatus').textContent = next.read_only
    ? 'Read-only kinematic reference'
    : next.plan ? `${next.plan.status} · ${next.plan.edit_count} edits` : 'No plan saved';
  renderGeneration(next.generation);
  renderLegend(); drawTimeline();
  if (rebuildScene) {
    try { await rebuild(next); }
    catch (error) {
      // The API may already own the new motion. Never restore an editable old
      // session against that backend after a browser asset-load failure.
      session = null; selectedHandle = null; setPlaying(false);
      contactHandleLayer.clear(); clearResources(guideGroup);
      byId('retryLoad').hidden = false; updateControls(); throw error;
    }
  }
  else selectHandle(selectedHandle);
  setFrame(frame);
}

async function rebuild(data: Session) {
  showStatus('Loading scene', false, true);
  sceneLoading = true;
  updateControls();
  try {
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
  const [robotResult, assetsResult] = await Promise.allSettled([
    urdfLoader.loadAsync(data.robot_urdf_url), robotAssetsLoaded,
  ]);
  if (robotResult.status === 'rejected' || assetsResult.status === 'rejected') {
    if (robotResult.status === 'fulfilled') disposeResources(robotResult.value);
    throw robotResult.status === 'rejected' ? robotResult.reason : (assetsResult as PromiseRejectedResult).reason;
  }
  const nextRobot = robotResult.value;
  let nextTerrain: THREE.Object3D | null = null;
  let referenceTerrain: THREE.Object3D | null = null;
  try {
    if (data.terrain_obj_url) nextTerrain = await new OBJLoader().loadAsync(data.terrain_obj_url);
    if (data.review?.comparison?.terrain_obj_url)
      referenceTerrain = await new OBJLoader().loadAsync(data.review.comparison.terrain_obj_url);
  } catch (error) {
    disposeResources(nextRobot); if (nextTerrain) disposeResources(nextTerrain); throw error;
  }
  // Review clones share source geometry. Detach them before releasing that source.
  comparison.setup(undefined, null, null, []);
  sequenceComparison.clear();
  if (robot) { scene.remove(robot); disposeResources(robot); }
  if (terrain) { scene.remove(terrain); disposeResources(terrain); }
  clearResources(surfaceGroup); contactHandleLayer.clear(); clearResources(contactSampleGroup); clearResources(guideGroup);
  selectedHandle = null;
  byId('selection').className = 'selection empty'; byId('selection').textContent = 'None';
  updatePositionOffset(null);
  if (rootPath) { scene.remove(rootPath); disposeResources(rootPath); rootPath = null; }
  robot = nextRobot; terrain = nextTerrain;
  let robotMeshCount = 0;
  robot.traverse((obj: any) => { if (obj.isMesh) robotMeshCount++; });
  sceneCanvas.dataset.robotMeshes = String(robotMeshCount);
  scene.add(robot);
  if (terrain) {
    const material = new THREE.MeshStandardMaterial({ color: 0x596570, roughness: .86, metalness: .03 });
    const oldMaterials = new Set<THREE.Material>();
    terrain.traverse((obj: any) => {
      if (!obj.isMesh) return;
      (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach((value: THREE.Material) => oldMaterials.add(value));
      obj.material = material;
    });
    oldMaterials.forEach(value => value.dispose());
    scene.add(terrain);
  }
  sceneLoading = false;
  comparison.setup(data.review, robot, terrain, data.joint_names);
  supportMotion.setup(data.review);
  supportSlip.setup(data.review);
  sequenceComparison.setup(data.review?.comparison, robot, terrain, referenceTerrain);
  setupCollection();
  applyRobotFrame();
  buildSurfaces(); buildRootPath(); buildContactSamples(); rebuildHandles(); focusScene();
  if (data.review?.kind === 'support_motion') supportMotion.focusSelected();
  applyDisplaySettings();
  hideStatus();
  } finally { sceneLoading = false; updateControls(); }
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
function matchingHandles(currentFrameOnly = currentOnly) {
  if (!session) return [];
  const query = anchorSearch.trim().toLowerCase();
  return session.edit_handles.filter(handle => {
    const status = handleStatus(handle);
    if (currentFrameOnly && !activeAt(handle)) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    const sources=Array.isArray(handle.metadata.source_bodies)?handle.metadata.source_bodies.join(' '):'';
    const roles=Array.isArray(handle.metadata.patch_roles)?handle.metadata.patch_roles.join(' '):'';
    return !query || `${handle.handle_id} ${handle.body} ${handle.surface_id} ${handle.object_id || ''} ${sources} ${roles}`.toLowerCase().includes(query);
  });
}
function rebuildHandles() {
  if (!session) return;
  const visible = new Set(matchingHandles().map(handle => handle.handle_id));
  if (selectedHandle && !visible.has(selectedHandle.handle_id)) {
    selectedHandle = null;
    byId('selection').className = 'selection empty'; byId('selection').textContent = 'None';
    updatePositionOffset(null); clearResources(guideGroup); updateContactSamples();
  }
  contactHandleLayer.rebuild({
    handles: session.edit_handles,
    visibleHandleIds: visible,
    selectedHandle,
    radius: Number(byId<HTMLInputElement>('handleSize').value) / 1000,
  });
  contactHandleLayer.setVisible(byId<HTMLInputElement>('handleToggle').checked);
  updateEpisodeBrowser();
  updateSelectedHandleProjection();
}

let episodeOptions: EditHandle[] = [];
function updateEpisodeBrowser() {
  const matches = matchingHandles(false), shown = matchingHandles().length;
  const disabled = Boolean(busy()) || !session || session.read_only || !matches.length;
  const picker = byId<HTMLSelectElement>('episodeSelect');
  picker.disabled = disabled;
  if (matches.length !== episodeOptions.length || matches.some((handle, index) => handle !== episodeOptions[index])) {
    const placeholder = new Option('选择接触段', '');
    placeholder.disabled = true;
    picker.replaceChildren(placeholder, ...matches.map((handle, index) => {
      const option = new Option(`${index + 1}. ${handle.body} · ${handle.start_frame}–${handle.end_frame - 1} · ${handle.surface_id}`, handle.handle_id);
      option.title = handle.handle_id;
      return option;
    }));
    episodeOptions = matches;
  }
  const index = matches.findIndex(handle => handle.handle_id === selectedHandle?.handle_id);
  picker.value = index < 0 ? '' : matches[index].handle_id;
  const text = !matches.length ? 'No matching episodes' : `${matches.length} matched · ${shown} shown${index < 0 ? '' : ` · Selected ${index + 1}/${matches.length}`}`;
  const status = byId('episodeBrowseStatus');
  if (status.textContent !== text) status.textContent = text;
}

function updateEpisodeFilters() {
  contactDragController.cancel();
  rebuildHandles(); drawTimeline();
}

function buildContactSamples() {
  if (!session) return; clearResources(contactSampleGroup);sceneCanvas.dataset.contactSample='point-force';
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
  if (!session || !robot || sceneLoading) return; const q = session.qpos[frame];
  if (!q) return;
  const previousPosition = robot.position.clone();
  robot.position.set(q[0],q[1],q[2]); robot.quaternion.set(q[4],q[5],q[6],q[3]);
  session.joint_names.forEach((name,i) => robot.setJointValue?.(name,q[7+i]));
  comparison.update();
  sequenceComparison.update(frame / session.fps, robot);
  if (rootPath) rootPath.position.y = sequenceComparison.offset;
  if (byId<HTMLInputElement>('followRobot').checked) {
    const delta = robot.position.clone().sub(previousPosition);
    camera.position.add(delta); controls.target.add(delta);
  }
  supportMotion.update(frame);
  supportSlip.update(frame);
  updateReviewMetrics();
}

function setFrame(value: number) {
  if (!session?.qpos.length) return; if (!Number.isFinite(value)) value = frame; frame = Math.max(0, Math.min(session.qpos.length - 1, Math.round(value)));
  byId<HTMLInputElement>('frameInput').max = String(session.qpos.length - 1);
  byId<HTMLInputElement>('frameInput').value = String(frame); byId('frameTotal').textContent = `/ ${session.qpos.length - 1}`;
  byId('viewportFrame').textContent = `Frame ${frame}`; byId('viewportTime').textContent = `${(frame / session.fps).toFixed(2)} s`;
  applyRobotFrame(); updateContactSamples(); rebuildHandles(); drawTimeline();
}

function setupCollection() {
  const review = session?.review, collection = review?.collection;
  byId('collectionPanel').hidden = !collection;
  if (!collection) return;
  const cases = byId<HTMLSelectElement>('reviewCase'), reference = byId<HTMLSelectElement>('reviewReference');
  cases.replaceChildren(); reference.replaceChildren(new Option('不对比', '-1'));
  collection.cases.forEach(row => {
    cases.add(new Option(row.label, String(row.index)));
    if (row.index !== collection.case_index) reference.add(new Option(row.label, String(row.index)));
  });
  cases.value = String(collection.case_index); reference.value = String(collection.reference_index);
  const layout = byId<HTMLSelectElement>('reviewLayout');
  layout.value = sequenceComparison.layout; layout.parentElement!.hidden = !review.comparison;
  const segments = byId<HTMLSelectElement>('reviewSegment');
  segments.replaceChildren();
  review.segments?.forEach(segment => segments.add(new Option(`${segment.label} · ${segment.start}–${segment.end}`, String(segment.start))));
  segments.parentElement!.hidden = !review.segments?.length;
  byId('reviewWorst').hidden = !review.depth_mm?.length;
}

function updateReviewMetrics() {
  const review = session?.review;
  if (!review?.collection) return;
  byId('comparisonClock').textContent = review.comparison
    ? `按时间对齐（起点 t=0，最近采样帧）：当前 ${frame}；参考 ${sequenceComparison.referenceFrame ?? '已结束，不显示'}。不自动匹配接触事件。`
    : '单轨迹回放';
  byId('scene').dataset.referenceFrame = String(sequenceComparison.referenceFrame ?? 'none');
  const depth = review.depth_mm?.[frame];
  byId('reviewMetrics').textContent = depth === undefined ? '当前帧穿透诊断：未提供' : `报告穿透深度：${depth.toFixed(2)} mm（非接触或承重判定）`;
  const segment = review.segments?.find(row => frame >= row.start && frame <= row.end);
  byId<HTMLSelectElement>('reviewSegment').value = segment ? String(segment.start) : '';
}

async function openReview(path: string, terrainPath: string | null, caseIndex = 0, referenceIndex?: number, keepFrame = false) {
  return exclusive(async () => {
    setPlaying(false);
    showStatus('Loading playback', false, true);
    const next = await api<Session>('/api/review/load', {method: 'POST', body: JSON.stringify({
      path, terrain: terrainPath, case_index: caseIndex, reference_index: referenceIndex,
    })});
    if (!keepFrame) frame = 0;
    await applySession(next, true);
    byId<HTMLInputElement>('reviewPath').value = path;
    byId<HTMLInputElement>('reviewTerrain').value = terrainPath || '';
  });
}

byId('reviewCase').onchange = () => {
  const collection = session?.review?.collection; if (!collection) return;
  const index = Number(byId<HTMLSelectElement>('reviewCase').value);
  byId<HTMLSelectElement>('reviewCase').value = String(collection.case_index);
  void openReview(collection.path, collection.terrain_override, index);
};
byId('reviewReference').onchange = () => {
  const collection = session?.review?.collection; if (!collection) return;
  const index = Number(byId<HTMLSelectElement>('reviewReference').value);
  byId<HTMLSelectElement>('reviewReference').value = String(collection.reference_index);
  void openReview(collection.path, collection.terrain_override, collection.case_index, index, true);
};
byId('reviewLayout').onchange = () => {
  sequenceComparison.setMode(byId<HTMLSelectElement>('reviewLayout').value as 'beside' | 'overlay');
  setFrame(frame); focusScene();
};
byId('reviewSegment').onchange = () => { setPlaying(false); setFrame(Number(byId<HTMLSelectElement>('reviewSegment').value)); };
byId('reviewWorst').onclick = () => {
  const depth = session?.review?.depth_mm; if (!depth?.length) return;
  setPlaying(false); setFrame(depth.reduce((best, value, index) => value > depth[best] ? index : best, 0));
};

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
  session.review?.segments?.forEach(segment => { values.add(segment.start); values.add(segment.end); });
  session.graph.transitions.forEach(t => { values.add(t.start_frame); values.add(Math.max(t.start_frame,t.end_frame-1)); const stable=t.metadata?.stable_anchor_frames; if(Array.isArray(stable)) stable.forEach(value=>values.add(Number(value))); });
  return [...values].filter(value=>Number.isInteger(value) && value >= 0 && value < session!.qpos.length).sort((a,b)=>a-b);
}

function renderLegend() {
  if (!session) return; byId('partLegend').innerHTML=session.contact_force.part_order.map((name,i)=>`<span><b style="background:#${partColors[i].toString(16).padStart(6,'0')}"></b>${name}</span>`).join('');
}

function selectHandle(handle: EditHandle | null) {
  selectedHandle=handle; const box=byId('selection');
  if(!handle){box.className='selection empty';box.textContent='None';updatePositionOffset(null);clearResources(guideGroup);updateContactSamples();rebuildHandles();drawTimeline();return;}
  box.className='selection'; box.innerHTML=`<strong>${handle.body}</strong><dl><dt>Frames</dt><dd>${handle.start_frame}–${handle.end_frame - 1}</dd><dt>Surface</dt><dd>${handle.surface_id}</dd><dt>Status</dt><dd>${handleStatus(handle)}</dd></dl><details class="selection-details"><summary>接触段详情</summary><code>${handle.handle_id}</code><dl><dt>Members</dt><dd>${String(handle.metadata.member_count||handle.member_anchor_ids.length)}</dd></dl></details>`;
  updatePositionOffset(handle);
  renderSelectionGuides(handle);updateContactSamples();
  rebuildHandles();drawTimeline();updateSelectedHandleProjection();
}

function renderSelectionGuides(handle:EditHandle){
  clearResources(guideGroup);guideGroup.visible=byId<HTMLInputElement>('guideToggle').checked;
  const origin=new THREE.Vector3(...handle.world_position);const vectors:[[Vec3,number],[Vec3,number],[Vec3,number]]=[[handle.surface_tangent_u,0xf06449],[handle.surface_tangent_v,0x68d391],[handle.surface_normal,0x4f8cff]];
  for(const [raw,color] of vectors){const v=new THREE.Vector3(...raw).normalize().multiplyScalar(.14);const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([origin.clone().addScaledVector(v,-1),origin.clone().add(v)]),new THREE.LineBasicMaterial({color}));guideGroup.add(line);}
}

const contactDragController = new ContactDragController({
  canvas: sceneCanvas,
  controls,
  layer: contactHandleLayer,
  getSession: () => session,
  isBusy: busy,
  getSelectedHandle: () => selectedHandle,
  selectHandle,
  updatePositionOffset,
  rebuildHandles,
  restoreHandle: async handle => Boolean(await runSessionAction('/api/session/restore-handle', {
    handle_id: handle.handle_id,
    mode: byId<HTMLSelectElement>('modeSelect').value,
  })),
  moveHandle: async (handle, requestedPosition) => Boolean(await runSessionAction('/api/session/move-handle', {
    handle_id: handle.handle_id,
    requested_world_position: requestedPosition.toArray(),
    mode: byId<HTMLSelectElement>('modeSelect').value,
  })),
});

function focusScene(robotOnly = false) {
  const box = new THREE.Box3();
  if (robot) box.expandByObject(robot);
  if (!robotOnly && terrain?.visible) box.expandByObject(terrain);
  if (!robotOnly) comparison.bounds(box);
  sequenceComparison.bounds(box, !robotOnly);
  if (box.isEmpty()) return;
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const halfFov = Math.min(THREE.MathUtils.degToRad(camera.fov / 2), Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect));
  const distance = Math.max(.4, sphere.radius * 1.15 / Math.sin(halfFov));
  controls.target.copy(sphere.center);
  camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(1.8, -2.4, 1.35).normalize(), distance);
  camera.far = Math.max(100, distance + sphere.radius * 4); camera.updateProjectionMatrix();
  scene.fog = null;
  controls.update();
}
function hideStatus() {
  if (statusTimer !== null) window.clearTimeout(statusTimer);
  statusTimer = null;
  byId('sceneStatus').classList.add('hidden');
}
function showStatus(text: string, error = false, persistent = false) {
  hideStatus();
  const el = byId('sceneStatus');
  el.textContent = text; el.classList.remove('hidden'); el.classList.toggle('error', error);
  el.setAttribute('role', error ? 'alert' : 'status');
  if (!error && !persistent) statusTimer = window.setTimeout(hideStatus, 3000);
}
function applyDisplaySettings() {
  const terrainVisible = byId<HTMLInputElement>('terrainToggle').checked;
  if (terrain) terrain.visible = terrainVisible;
  comparison.terrainVisible(terrainVisible);
  const opacity = Number(byId<HTMLInputElement>('terrainOpacity').value);
  terrain?.traverse((mesh: any) => {
    if (!mesh.isMesh) return;
    (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach((material: THREE.Material) => {
      material.transparent = opacity < 1; material.opacity = opacity; material.depthWrite = opacity === 1;
    });
  });
  sequenceComparison.display(terrainVisible, opacity);
  surfaceGroup.visible = byId<HTMLInputElement>('surfaceToggle').checked;
  contactSampleGroup.visible = byId<HTMLInputElement>('contactSampleToggle').checked;
  contactHandleLayer.setVisible(byId<HTMLInputElement>('handleToggle').checked);
  guideGroup.visible = byId<HTMLInputElement>('guideToggle').checked;
  if (rootPath) rootPath.visible = byId<HTMLInputElement>('rootPathToggle').checked;
  sceneCanvas.dataset.terrainVisible = String(terrain?.visible ?? false);
  sceneCanvas.dataset.surfacesVisible = String(surfaceGroup.visible);
}
function generationSettings(){return {
  edit_plan_path:byId<HTMLInputElement>('planPath').value,
  output_motion_path:byId<HTMLInputElement>('outputMotion').value,
  output_contact_layer:byId<HTMLInputElement>('outputLayer').value,
  output_motion_id:byId<HTMLInputElement>('outputMotionId').value,
  register_motion:byId<HTMLInputElement>('registerMotion').checked,
  overwrite:byId<HTMLInputElement>('overwriteOutput').checked,
};}
function syncOutputSettings(): Promise<Session> {
  const body = JSON.stringify(generationSettings());
  const request = settingsQueue.then(() => api<Session>('/api/session/settings', { method: 'PUT', body }));
  settingsQueue = request.catch(() => undefined);
  return request.then(next => { session = next; return next; });
}
function stopGenerationPoll() {
  if (generationPoll !== null) window.clearTimeout(generationPoll);
  generationPoll = null;
}
function pollGeneration() {
  if (generationPoll !== null) return;
  generationPoll = window.setTimeout(async () => {
    try {
      const next = await api<Generation>('/api/session/generation');
      renderGeneration(next);
      generationPoll = null;
      if (next.status === 'running') pollGeneration();
      else if (next.status === 'succeeded') {
        byId('planStatus').textContent = 'generated';
        if (next.output_motion_id) await openMotion(next.output_motion_id, true);
        else await refreshRecentMotions();
      }
    } catch (error) { stopGenerationPoll(); showStatus(String(error), true); byId('retryLoad').hidden = false; }
  }, 900);
}
function updateControls() {
  const blocked = Boolean(busy()), readOnly = Boolean(session?.read_only), editable = Boolean(session) && !readOnly;
  document.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLButtonElement>('[data-page="contact"] .anchor-browser input,[data-page="contact"] .anchor-browser select,[data-page="contact"] .anchor-browser button,[data-page="output"] input,[data-page="output"] button').forEach(control => control.disabled = blocked || !editable);
  document.querySelectorAll<HTMLButtonElement | HTMLSelectElement>('.recent-motion-item,#openMotionBtn,#reviewOpen,#collectionPanel select,#collectionPanel button').forEach(control => control.disabled = blocked);
  byId<HTMLButtonElement>('undoBtn').disabled = blocked || !editable || !session?.can_undo;
  byId<HTMLButtonElement>('redoBtn').disabled = blocked || !editable || !session?.can_redo;
  byId<HTMLButtonElement>('saveBtn').disabled = blocked || !editable;
  byId<HTMLInputElement>('outputMotionId').disabled = blocked || !editable || !byId<HTMLInputElement>('registerMotion').checked;
  document.querySelectorAll<HTMLButtonElement | HTMLInputElement>('#playBtn,#prevBtn,#nextBtn,#prevCut,#nextCut,#frameInput,#fpsInput').forEach(control => control.disabled = openingMotion || actionBusy || sceneLoading || !session);
  if (session && session.qpos.length < 2) byId<HTMLButtonElement>('playBtn').disabled = true;
  if (!stableCutFrames().length) {
    byId<HTMLButtonElement>('prevCut').disabled = true;
    byId<HTMLButtonElement>('nextCut').disabled = true;
  }
  byId('scene').setAttribute('aria-busy', String(blocked));
  updateEpisodeBrowser();
}
function renderGeneration(job:Generation){
  if (session) session.generation = job;
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
  else status.innerHTML='<strong>Ready</strong><span>Contact-aware candidate · native validation required</span>';
  updateControls();
  if(running)pollGeneration();else stopGenerationPoll();
}

function setPlaying(next:boolean){
  playing=next;
  if(!playing)frameAccumulator=0;
  byId('playBtn').innerHTML=`<i data-lucide="${playing?'pause':'play'}"></i>`;
  refreshIcons();
}
byId('playBtn').onclick=()=>setPlaying(!playing);
byId('prevBtn').onclick=()=>{setPlaying(false);setFrame(frame-1);};byId('nextBtn').onclick=()=>{setPlaying(false);setFrame(frame+1);};
byId<HTMLInputElement>('frameInput').onchange=e=>setFrame(Number((e.target as HTMLInputElement).value));
async function runSessionAction(path: string, body?: unknown) {
  return exclusive(async () => {
    const next = await api<Session>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });
    await applySession(next);
    showStatus('Session updated');
    return next;
  });
}
byId('undoBtn').onclick=()=>{void runSessionAction('/api/session/undo');};byId('redoBtn').onclick=()=>{void runSessionAction('/api/session/redo');};
byId('saveBtn').onclick = () => { void exclusive(async () => {
  await syncOutputSettings();
  const result = await api<{ output_contact_layer: string; plan: Session['plan'] }>('/api/session/save', { method: 'POST' });
  if (session) session.plan = result.plan;
  if (result.plan) byId('planStatus').textContent = `${result.plan.status} · ${result.plan.edit_count} edits`;
  showStatus(`Saved ${result.output_contact_layer}`);
}); };
byId('focusBtn').onclick = () => focusScene();
byId('focusRobot').onclick = () => focusScene(true);
byId('terrainOpacity').oninput = applyDisplaySettings;
byId<HTMLInputElement>('terrainToggle').onchange = applyDisplaySettings;
byId<HTMLInputElement>('surfaceToggle').onchange=applyDisplaySettings;
byId<HTMLInputElement>('handleToggle').onchange=e=>contactHandleLayer.setVisible((e.target as HTMLInputElement).checked);byId<HTMLInputElement>('contactSampleToggle').onchange=e=>contactSampleGroup.visible=(e.target as HTMLInputElement).checked;byId<HTMLInputElement>('handleSize').oninput=()=>rebuildHandles();byId<HTMLInputElement>('forceScale').oninput=()=>updateContactSamples();
byId<HTMLInputElement>('rootPathToggle').onchange=e=>{if(rootPath)rootPath.visible=(e.target as HTMLInputElement).checked;};byId<HTMLInputElement>('guideToggle').onchange=e=>guideGroup.visible=(e.target as HTMLInputElement).checked;
byId<HTMLInputElement>('anchorSearch').oninput=e=>{anchorSearch=(e.target as HTMLInputElement).value;updateEpisodeFilters();};
byId<HTMLSelectElement>('statusFilter').onchange=e=>{statusFilter=(e.target as HTMLSelectElement).value;updateEpisodeFilters();};
byId<HTMLInputElement>('currentOnly').onchange=e=>{currentOnly=(e.target as HTMLInputElement).checked;updateEpisodeFilters();};
function selectRelativeAnchor(offset: number) {
  if (busy() || !session || session.read_only) return;
  // Frame visibility must not trap navigation inside the current contact interval.
  const items = matchingHandles(false);
  if (!items.length) return;
  const current = items.findIndex(item => item.handle_id === selectedHandle?.handle_id);
  let handle: EditHandle;
  if (current >= 0 && activeAt(items[current])) {
    handle = items[(current + offset + items.length) % items.length];
  } else {
    const ordered = offset > 0 ? items : items.slice().reverse();
    handle = ordered.find(activeAt)
      || ordered.find(item => offset > 0 ? item.start_frame >= frame : item.start_frame <= frame)
      || ordered[0];
  }
  jumpToEpisode(handle);
}
function jumpToEpisode(handle: EditHandle) {
  if (busy() || !session || session.read_only) return;
  setPlaying(false); contactDragController.cancel();
  // Move the playback clock before selecting so current-frame visibility agrees.
  setFrame(handle.start_frame); selectHandle(handle);
}
byId<HTMLSelectElement>('episodeSelect').onchange = event => {
  const id = (event.target as HTMLSelectElement).value;
  const handle = matchingHandles(false).find(item => item.handle_id === id);
  if (handle) jumpToEpisode(handle);
};

function selectRelativeCut(offset: number) {
  if (openingMotion || actionBusy || sceneLoading || !session) return;
  const cuts = stableCutFrames(); if (!cuts.length) return;
  setPlaying(false); contactDragController.cancel();
  const ordered = offset > 0 ? cuts : cuts.slice().reverse();
  setFrame(ordered.find(value => offset > 0 ? value > frame : value < frame) ?? ordered[0]);
}
byId('prevCut').onclick=()=>selectRelativeCut(-1);byId('nextCut').onclick=()=>selectRelativeCut(1);
function timelinePointer(event:PointerEvent,updateFrame=false,selectLane=false){
  if(!session)return;const rect=timeline.getBoundingClientRect(),m=timelineMetrics(),localX=event.clientX-rect.left,localY=event.clientY-rect.top,next=timelineXToFrame(localX,m);
  if(updateFrame&&localX>=m.labelW)setFrame(next);
  const lane=Math.floor((localY-m.rulerH)/m.rowH);
  if(selectLane&&lane>=0&&lane<session.contact_force.part_order.length){const name=session.contact_force.part_order[lane],body=partParent[name]||name,candidates=session.edit_handles.filter(handle=>handle.body===body&&activeAt(handle));if(candidates.length)selectHandle(candidates[0]);}
  const hover=byId('timelineHover'),part=lane>=0&&lane<session.contact_force.part_order.length?session.contact_force.part_order[lane]:'Timeline';hover.textContent=`${part} · ${formatTimelineTime(next/session.fps)} · frame ${next}`;hover.style.left=`${Math.max(m.labelW+44,Math.min(rect.width-72,localX))}px`;hover.classList.remove('hidden');
}
timeline.addEventListener('pointerdown',event=>{if(!session)return;setPlaying(false);scrubbingTimeline=true;timeline.setPointerCapture(event.pointerId);timeline.classList.add('scrubbing');timelinePointer(event,true,true);});
timeline.addEventListener('pointermove',event=>timelinePointer(event,scrubbingTimeline,false));
timeline.addEventListener('pointerup',event=>{if(!scrubbingTimeline)return;scrubbingTimeline=false;timeline.releasePointerCapture(event.pointerId);timeline.classList.remove('scrubbing');});
timeline.addEventListener('pointercancel',()=>{scrubbingTimeline=false;timeline.classList.remove('scrubbing');});
timeline.addEventListener('pointerleave',()=>{if(!scrubbingTimeline)byId('timelineHover').classList.add('hidden');});

document.querySelectorAll<HTMLInputElement>('#planPath,#outputMotion,#outputLayer,#outputMotionId,#registerMotion,#overwriteOutput').forEach(input=>{input.dataset.generationSetting='';input.addEventListener('change',()=>{byId<HTMLInputElement>('outputMotionId').disabled=!byId<HTMLInputElement>('registerMotion').checked;void syncOutputSettings().catch(e=>showStatus(String(e),true));});});
byId('validateBtn').onclick = () => { void exclusive(async () => {
  await syncOutputSettings();
  const result = await api<{plan:{status:string};warnings:string[]}>('/api/session/validate', { method: 'POST' });
  byId('planStatus').textContent = `${result.plan.status}${result.warnings.length ? ` · ${result.warnings.length} warnings` : ''}`;
  showStatus('ContactEditPlan validated');
}); };
byId('generateBtn').onclick = () => { void exclusive(async () => {
  await syncOutputSettings();
  // The saved settings are authoritative. GenerateRequest does not accept plan/draft paths.
  const job = await api<Generation>('/api/session/generate', { method: 'POST', body: JSON.stringify({}) });
  renderGeneration(job);
}); };
byId('reloadBtn').onclick=()=>{void runSessionAction('/api/session/reload');};byId('discardBtn').onclick=()=>{void runSessionAction('/api/session/discard');};

window.addEventListener('keydown', event => {
  if (event.code === 'Escape' && contactDragController.active) { event.preventDefault(); contactDragController.cancel(); return; }
  if (openingMotion || actionBusy || sceneLoading || byId<HTMLDialogElement>('motionPicker').open ||
      (event.target as HTMLElement).closest('input,select,textarea,button,[contenteditable=true]')) return;
  if (!['Space', 'ArrowLeft', 'ArrowRight', 'BracketLeft', 'BracketRight'].includes(event.code)) return;
  event.preventDefault();
  if (event.code === 'Space') byId<HTMLButtonElement>('playBtn').click();
  else if (event.code === 'ArrowLeft' || event.code === 'ArrowRight') {
    setPlaying(false); setFrame(frame + (event.code === 'ArrowLeft' ? -1 : 1) * (event.shiftKey ? 10 : 1));
  } else selectRelativeAnchor(event.code === 'BracketLeft' ? -1 : 1);
});

let resizeStartY=0,resizeStartHeight=0;
byId('timelineResizer').addEventListener('pointerdown',event=>{resizingTimeline=true;resizeStartY=event.clientY;resizeStartHeight=timelineHeight;byId('timelineResizer').setPointerCapture(event.pointerId);document.body.classList.add('resizing-timeline');});
byId('timelineResizer').addEventListener('pointermove',event=>{if(resizingTimeline)setTimelineHeight(resizeStartHeight+resizeStartY-event.clientY);});
byId('timelineResizer').addEventListener('pointerup',event=>{if(!resizingTimeline)return;resizingTimeline=false;byId('timelineResizer').releasePointerCapture(event.pointerId);document.body.classList.remove('resizing-timeline');setTimelineHeight(timelineHeight,true);});

function resize(){const r=sceneCanvas.getBoundingClientRect();if(r.width<=0||r.height<=0)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();drawTimeline();}
window.addEventListener('resize',resize);resize();
function updateSelectedHandleProjection(){
  contactHandleLayer.updateProjection(selectedHandle);
}
function animate(now:number){requestAnimationFrame(animate);const dt=Math.min(.1,Math.max(0,(now-lastTick)/1000));lastTick=now;if(playing&&session){frameAccumulator+=dt*playbackFps(false);if(frameAccumulator>=1){const step=Math.floor(frameAccumulator);frameAccumulator-=step;setFrame((frame+step)%session.qpos.length);}}controls.update();updateSelectedHandleProjection();renderer.render(scene,camera);sceneCanvas.dataset.geometryCount=String(renderer.info.memory.geometries);}requestAnimationFrame(animate);
function playbackFps(normalize = true) {
  const input = byId<HTMLInputElement>('fpsInput');
  const value = Number(input.value);
  const result = Number.isFinite(value) && value >= 1 ? Math.min(240, value) : Math.min(240, Math.max(1, session?.fps || 50));
  if (normalize) input.value = String(result);
  return result;
}
byId<HTMLInputElement>('fpsInput').onchange = () => { playbackFps(); };
byId('timelineResizer').addEventListener('pointercancel', () => {
  resizingTimeline = false; document.body.classList.remove('resizing-timeline');
});
byId('reviewOpenForm').onsubmit = event => {
  event.preventDefault();
  const path = byId<HTMLInputElement>('reviewPath').value.trim();
  if (!path || busy()) return;
  byId<HTMLDialogElement>('motionPicker').close();
  void openReview(path, byId<HTMLInputElement>('reviewTerrain').value.trim() || null);
};
loadMotions().catch(loadError);
