import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import URDFLoader from 'urdf-loader';
import { createIcons, Play, Pause, StepBack, StepForward, Undo2, Redo2, Save, RotateCcw, Focus, RefreshCw, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Trash2, FolderOpen } from 'lucide';
import './styles.css';

type Vec3 = [number, number, number];
type AssetItem = { motion_asset_id: string; motion_id: string; source: string; has_force: boolean; has_terrain: boolean };
type Anchor = {
  anchor_id: string; body: string; start_frame: number; end_frame: number;
  world_position: Vec3 | null; surface_id: string | null; object_id: string | null;
  surface_coordinates: { u: number; v: number } | null; metadata: Record<string, unknown>;
  surface_origin: Vec3 | null; surface_normal: Vec3 | null; surface_tangent_u: Vec3 | null; surface_tangent_v: Vec3 | null;
};
type Surface = {
  surface_id: string; origin: Vec3; normal: Vec3; tangent_u: Vec3; tangent_v: Vec3;
  bounds: { u: [number, number]; v: [number, number] }; metadata: Record<string, unknown>;
};
type Session = {
  motion_asset_id: string; motion_id: string; fps: number; qpos: number[][]; joint_names: string[];
  robot_urdf_url: string; terrain_obj_url: string | null;
  graph: { anchors: Anchor[]; transitions: Array<{start_frame:number;end_frame:number;metadata:Record<string,unknown>}> }; surfaces: Surface[];
  contact_force: { part_order: string[]; forces: Vec3[][]; masks: boolean[][]; positions: Vec3[][] };
  pending_edit_count: number; can_undo: boolean; can_redo: boolean;
  settings: { edit_plan_path: string; output_contact_layer: string; source_contact_layer: string };
  plan: { path:string; status:string; edit_count:number } | null;
};

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <header class="topbar">
    <div class="brand"><strong>Motion Edit</strong><span id="motionLabel">No motion</span></div>
    <div class="asset-picker"><select id="assetSelect" aria-label="Motion asset"></select><button id="loadBtn"><i data-lucide="folder-open"></i><span>Load</span></button></div>
    <div class="top-actions">
      <button class="icon" id="focusBtn" title="Frame scene"><i data-lucide="focus"></i></button>
      <button class="icon" id="undoBtn" title="Undo"><i data-lucide="undo-2"></i></button>
      <button class="icon" id="redoBtn" title="Redo"><i data-lucide="redo-2"></i></button>
      <button class="icon primary" id="saveBtn" title="Save contact edit plan"><i data-lucide="save"></i></button>
    </div>
  </header>
  <main class="workspace">
    <section class="viewport"><canvas id="scene"></canvas><div id="sceneStatus" class="scene-status">Select a motion asset</div></section>
    <aside class="inspector">
      <div class="inspector-tabs"><button data-tab="contact" class="active">Contact</button><button data-tab="display">Display</button><button data-tab="output">Output</button></div>
      <div class="tab-page active" data-page="contact">
        <div class="filter-grid"><input id="anchorSearch" placeholder="Filter body, surface, id" /><select id="statusFilter"><option value="all">All status</option><option value="bound">Bound</option><option value="edited">Edited</option><option value="clamped">Clamped</option><option value="suspicious">Suspicious</option><option value="failed">Failed</option><option value="unbound">Unbound</option></select></div>
        <label class="toggle"><input id="currentOnly" type="checkbox" checked /><span>Current frame only</span></label>
        <label class="field"><span>Boundary</span><select id="modeSelect"><option value="reject">Reject</option><option value="clamp">Clamp</option></select></label>
        <div class="anchor-nav"><button class="nav-command" id="prevAnchor" title="Previous matching contact"><i data-lucide="chevron-left"></i><span>Previous</span></button><button class="nav-command" id="nextAnchor" title="Next matching contact"><span>Next</span><i data-lucide="chevron-right"></i></button></div>
        <div id="selection" class="selection empty">None</div>
        <div class="precision-editor disabled" id="precisionEditor">
          <div class="precision-head"><div class="panel-title">Surface position</div><button class="quiet-command" id="restoreAnchor" title="Restore selected contact" disabled><i data-lucide="rotate-ccw"></i><span>Restore</span></button></div>
          <div class="surface-move">
            <div class="uv-pad" aria-label="Move on contact surface"><button data-du="0" data-dv="1" class="pad-up" title="Move +v" disabled><i data-lucide="arrow-up"></i></button><button data-du="-1" data-dv="0" class="pad-left" title="Move -u" disabled><i data-lucide="arrow-left"></i></button><div class="pad-center">u/v</div><button data-du="1" data-dv="0" class="pad-right" title="Move +u" disabled><i data-lucide="arrow-right"></i></button><button data-du="0" data-dv="-1" class="pad-down" title="Move -v" disabled><i data-lucide="arrow-down"></i></button></div>
            <div class="precision-values"><label>Step<input id="moveStep" type="number" value="0.01" min="0.001" step="0.001" disabled /></label><div class="number-grid"><label>u<input id="targetU" type="number" step="0.001" disabled /></label><label>v<input id="targetV" type="number" step="0.001" disabled /></label><button id="applyUv" title="Apply exact surface coordinates" disabled><i data-lucide="check"></i></button></div></div>
          </div>
        </div>
        <div class="stats"><span id="anchorCount">0 anchors</span><span id="editCount">0 edits</span></div>
      </div>
      <div class="tab-page" data-page="display">
        <label class="toggle"><input id="terrainToggle" type="checkbox" checked /><span>Terrain mesh</span></label>
        <label class="toggle"><input id="surfaceToggle" type="checkbox" /><span>Contact surfaces</span></label>
        <label class="toggle"><input id="anchorToggle" type="checkbox" checked /><span>Contact anchors</span></label>
        <label class="toggle"><input id="forceToggle" type="checkbox" checked /><span>Force vectors</span></label>
        <label class="toggle"><input id="rootPathToggle" type="checkbox" /><span>Root path</span></label>
        <label class="toggle"><input id="guideToggle" type="checkbox" checked /><span>Selection guides</span></label>
        <label class="slider-field"><span>Contact radius</span><input id="anchorSize" type="range" min="20" max="80" value="42" /></label>
        <label class="slider-field"><span>Force scale</span><input id="forceScale" type="range" min="25" max="300" value="100" /></label>
        <div class="panel-title">8-part channels</div><div id="partLegend" class="part-legend"></div>
      </div>
      <div class="tab-page" data-page="output">
        <label class="stack-field"><span>ContactEditPlan</span><input id="planPath" /></label>
        <label class="stack-field"><span>Output contact layer</span><input id="outputLayer" /></label>
        <label class="stack-field"><span>Source contact layer</span><input id="sourceLayer" disabled /></label>
        <div id="planStatus" class="plan-status">No plan saved</div>
        <div class="output-actions"><button id="applySettings">Apply</button><button id="validateBtn"><i data-lucide="check"></i><span>Validate</span></button></div>
        <div class="danger-actions"><button id="reloadBtn"><i data-lucide="refresh-cw"></i><span>Reload</span></button><button id="discardBtn"><i data-lucide="trash-2"></i><span>Discard</span></button></div>
      </div>
    </aside>
    <section class="timeline-panel">
      <div id="timelineResizer" class="timeline-resizer" title="Drag to resize timeline"><span></span></div>
      <div class="transport">
        <div class="toolbar-group cut-nav"><button class="icon" id="prevCut" title="Previous stable cut"><i data-lucide="chevrons-left"></i></button><button class="icon" id="nextCut" title="Next stable cut"><i data-lucide="chevrons-right"></i></button></div>
        <div class="toolbar-group playback-nav"><button class="icon" id="prevBtn" title="Previous frame"><i data-lucide="step-back"></i></button><button class="icon play" id="playBtn" title="Play or pause"><i data-lucide="play"></i></button><button class="icon" id="nextBtn" title="Next frame"><i data-lucide="step-forward"></i></button></div>
        <input id="frameInput" class="frame-input" type="number" min="0" value="0" /><span id="frameTotal">/ 0</span>
        <label class="fps">FPS <input id="fpsInput" type="number" min="1" max="240" value="50" /></label>
      </div>
      <div class="timeline-wrap"><canvas id="timeline"></canvas><div id="timelineHover" class="timeline-hover hidden"></div></div>
      <input id="frameSlider" type="range" min="0" max="0" value="0" />
    </section>
  </main>`;
createIcons({ icons: { Play, Pause, StepBack, StepForward, Undo2, Redo2, Save, RotateCcw, Focus, RefreshCw, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Trash2, FolderOpen } });

const sceneCanvas = document.querySelector<HTMLCanvasElement>('#scene')!;
const timeline = document.querySelector<HTMLCanvasElement>('#timeline')!;
const renderer = new THREE.WebGLRenderer({ canvas: sceneCanvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = false;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x17191c);
scene.up.set(0, 0, 1);
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
camera.up.set(0, 0, 1);
camera.position.set(3.2, -4.5, 2.7);
const controls = new OrbitControls(camera, sceneCanvas);
controls.target.set(0, 0, 0.9);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x30343a, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.8); sun.position.set(3, -4, 7); scene.add(sun);
const grid = new THREE.GridHelper(12, 24, 0x575d64, 0x34383d); grid.rotation.x = Math.PI / 2; scene.add(grid);

let session: Session | null = null;
let robot: any = null;
let terrain: THREE.Object3D | null = null;
let surfaceGroup = new THREE.Group(); scene.add(surfaceGroup);
let anchorGroup = new THREE.Group(); scene.add(anchorGroup);
let forceGroup = new THREE.Group(); scene.add(forceGroup);
let guideGroup = new THREE.Group(); scene.add(guideGroup);
let rootPath: THREE.Line | null = null;
let anchorMeshes = new Map<string, THREE.Mesh>();
let selectedAnchor: Anchor | null = null;
let frame = 0, playing = false, lastTick = performance.now(), frameAccumulator = 0;
let statusFilter = 'all', anchorSearch = '', currentOnly = true;
let dragPlane = new THREE.Plane(), dragging = false, dragPreview: THREE.Vector3 | null = null;
let resizingTimeline = false;
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const partColors = [0x18b6a4, 0x68d391, 0xf06449, 0xffb547, 0x4f8cff, 0xb678e6, 0x31a7d8, 0xe05a9d];
const bodyPart: Record<string, string> = { left_heel:'LHEE', left_toe:'LTOE', right_heel:'RHEE', right_toe:'RTOE', left_hand:'LH', right_hand:'RH', left_knee:'LK', right_knee:'RK' };
const partBody = Object.fromEntries(Object.entries(bodyPart).map(([body, part]) => [part, body]));

const byId = <T extends HTMLElement>(id: string) => document.querySelector<T>(`#${id}`)!;
const savedTimelineHeight=Number(localStorage.getItem('motion-edit.timeline-height'));
let timelineHeight=Number.isFinite(savedTimelineHeight)&&savedTimelineHeight>0?savedTimelineHeight:(window.innerWidth<=760?200:230);
function setTimelineHeight(value:number,persist=false){timelineHeight=Math.max(150,Math.min(window.innerHeight*.48,Math.round(value)));document.documentElement.style.setProperty('--timeline-height',`${timelineHeight}px`);if(persist)localStorage.setItem('motion-edit.timeline-height',String(timelineHeight));resize();}
setTimelineHeight(timelineHeight);
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!response.ok) { const detail = await response.json().catch(() => ({})); throw new Error(detail.detail || response.statusText); }
  return response.json();
}

async function loadAssets() {
  const data = await api<{ assets: AssetItem[] }>('/api/assets');
  const select = byId<HTMLSelectElement>('assetSelect');
  select.innerHTML = data.assets.filter(a => a.has_force && a.has_terrain).map(a => `<option value="${a.motion_asset_id}">${a.motion_id} · Newton 8-part</option>`).join('');
  try { const current = await api<Session>('/api/session'); select.value = current.motion_asset_id; await applySession(current, true); } catch { /* no initial asset */ }
}

async function applySession(next: Session, rebuildScene = false) {
  const selectedId = selectedAnchor?.anchor_id;
  session = next; selectedAnchor = selectedId ? next.graph.anchors.find(anchor => anchor.anchor_id === selectedId) || null : null; frame = Math.min(frame, next.qpos.length - 1);
  byId('motionLabel').textContent = next.motion_id;
  byId<HTMLInputElement>('fpsInput').value = String(next.fps);
  byId<HTMLInputElement>('frameSlider').max = String(Math.max(0, next.qpos.length - 1));
  byId('anchorCount').textContent = `${next.graph.anchors.length} anchors`;
  byId('editCount').textContent = `${next.pending_edit_count} edits`;
  byId<HTMLButtonElement>('undoBtn').disabled = !next.can_undo;
  byId<HTMLButtonElement>('redoBtn').disabled = !next.can_redo;
  byId<HTMLInputElement>('planPath').value = next.settings.edit_plan_path || '';
  byId<HTMLInputElement>('outputLayer').value = next.settings.output_contact_layer || '';
  byId<HTMLInputElement>('sourceLayer').value = next.settings.source_contact_layer || '';
  byId('planStatus').textContent = next.plan ? `${next.plan.status} · ${next.plan.edit_count} edits` : 'No plan saved';
  renderLegend(); drawTimeline();
  if (rebuildScene) await rebuild(next);
  else { rebuildAnchors(); if (selectedAnchor) selectAnchor(selectedAnchor); }
  setFrame(frame);
}

async function rebuild(data: Session) {
  byId('sceneStatus').textContent = 'Loading scene'; byId('sceneStatus').classList.remove('hidden');
  if (robot) scene.remove(robot); if (terrain) scene.remove(terrain);
  surfaceGroup.clear(); surfaceGroup.visible=byId<HTMLInputElement>('surfaceToggle').checked; anchorGroup.clear(); forceGroup.clear(); guideGroup.clear(); anchorMeshes.clear(); selectedAnchor = null;
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
    terrain.traverse((obj: any) => { if (obj.isMesh) obj.material = new THREE.MeshStandardMaterial({ color: 0x737a81, roughness: .82, metalness: .04 }); });
    scene.add(terrain);
  }
  buildSurfaces(); buildRootPath(); rebuildAnchors(); buildForces(); focusScene();
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

function anchorStatus(a: Anchor) {
  if(a.metadata.surface_binding_failed)return 'failed';
  const bindings=a.metadata.surface_bindings;if(Array.isArray(bindings)&&bindings.length&&bindings[bindings.length-1]?.clamped)return 'clamped';
  if(a.metadata.surface_binding_suspicious)return 'suspicious';
  return String(a.metadata.surface_editor_status || (a.surface_id ? 'bound' : 'unbound'));
}
function activeAt(a: Anchor) { return frame >= a.start_frame && frame < a.end_frame; }
function matchingAnchors() {
  if (!session) return [];
  const query = anchorSearch.trim().toLowerCase();
  return session.graph.anchors.filter(anchor => {
    const status = anchorStatus(anchor);
    if (currentOnly && !activeAt(anchor)) return false;
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    return !query || `${anchor.anchor_id} ${anchor.body} ${anchor.surface_id || ''} ${anchor.object_id || ''}`.toLowerCase().includes(query);
  });
}
function rebuildAnchors() {
  if (!session) return; anchorGroup.clear(); anchorMeshes.clear();sceneCanvas.dataset.contactMarker='surface-disk';
  anchorGroup.visible = byId<HTMLInputElement>('anchorToggle').checked;
  const visible = new Set(matchingAnchors().map(anchor => anchor.anchor_id));
  for (const anchor of session.graph.anchors) {
    if (!anchor.world_position) continue;
    if (!visible.has(anchor.anchor_id) && anchor.anchor_id !== selectedAnchor?.anchor_id) continue;
    const status = anchorStatus(anchor);
    const part = Math.max(0, session.contact_force.part_order.indexOf(bodyPart[anchor.body] || anchor.body));
    const color = anchor.anchor_id === selectedAnchor?.anchor_id ? 0xffde59 : status === 'edited' ? 0x36d399 : status === 'unbound' ? 0xef4444 : partColors[part % partColors.length];
    const radius = Number(byId<HTMLInputElement>('anchorSize').value) / 1000;
    const material=new THREE.MeshBasicMaterial({color,transparent:true,opacity:activeAt(anchor)?0.96:0.72,side:THREE.DoubleSide,depthWrite:false});
    const mesh = new THREE.Mesh(new THREE.CircleGeometry(radius, 24), material);
    const normal=new THREE.Vector3(...(anchor.surface_normal||[0,0,1] as Vec3)).normalize();
    mesh.position.set(...anchor.world_position).addScaledVector(normal,.004);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),normal);mesh.userData.anchor = anchor;
    if(anchor.anchor_id===selectedAnchor?.anchor_id){const ring=new THREE.Mesh(new THREE.RingGeometry(radius*1.18,radius*1.48,28),new THREE.MeshBasicMaterial({color:0xffde59,side:THREE.DoubleSide,depthTest:false}));ring.position.z=.001;ring.renderOrder=5;mesh.add(ring);}
    mesh.renderOrder=4;anchorGroup.add(mesh); anchorMeshes.set(anchor.anchor_id, mesh);
  }
}

function buildForces() {
  if (!session) return; forceGroup.clear();
  session.contact_force.part_order.forEach((name, i) => {
    const group=new THREE.Group();const material=new THREE.MeshBasicMaterial({color:partColors[i],depthTest:true});
    const shaft=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,1,8),material);const head=new THREE.Mesh(new THREE.ConeGeometry(.022,.055,10),material);
    group.add(shaft,head);group.name=name;group.userData.shaft=shaft;group.userData.head=head;forceGroup.add(group);
  });
}

function updateForces() {
  if (!session) return;
  forceGroup.visible = byId<HTMLInputElement>('forceToggle').checked;
  forceGroup.children.forEach((obj, i) => {
    const glyph=obj as THREE.Group, visible = !!session!.contact_force.masks[frame]?.[i];
    glyph.visible = visible; if (!visible) return;
    const f = new THREE.Vector3(...session!.contact_force.forces[frame][i]); const mag = f.length();
    const scale = Number(byId<HTMLInputElement>('forceScale').value) / 100;
    const length=Math.min(.9,(.04+mag/1200)*scale),headLength=Math.min(.055,length*.35),shaftLength=Math.max(.001,length-headLength);
    const body=partBody[session!.contact_force.part_order[i]],activeAnchor=session!.graph.anchors.find(anchor=>anchor.body===body&&activeAt(anchor)&&anchor.world_position);
    glyph.position.set(...(activeAnchor?.world_position||session!.contact_force.positions[frame][i]));if(activeAnchor?.surface_normal)glyph.position.addScaledVector(new THREE.Vector3(...activeAnchor.surface_normal),.008);if(mag>1e-5)glyph.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),f.normalize());
    const shaft=glyph.userData.shaft as THREE.Mesh,head=glyph.userData.head as THREE.Mesh;shaft.scale.set(1,shaftLength,1);shaft.position.set(0,shaftLength/2,0);head.scale.set(1,headLength/.055,1);head.position.set(0,shaftLength+headLength/2,0);
  });
}

function applyRobotFrame() {
  if (!session || !robot) return; const q = session.qpos[frame];
  robot.position.set(q[0],q[1],q[2]); robot.quaternion.set(q[4],q[5],q[6],q[3]);
  session.joint_names.forEach((name,i) => robot.setJointValue?.(name,q[7+i]));
}

function setFrame(value: number) {
  if (!session) return; frame = Math.max(0, Math.min(session.qpos.length - 1, Math.round(value)));
  byId<HTMLInputElement>('frameSlider').value = String(frame); byId<HTMLInputElement>('frameInput').value = String(frame); byId('frameTotal').textContent = `/ ${session.qpos.length - 1}`;
  applyRobotFrame(); updateForces(); rebuildAnchors(); drawTimeline();
}

function drawTimeline() {
  const ctx = timeline.getContext('2d')!; const rect = timeline.getBoundingClientRect(); const dpr = window.devicePixelRatio;
  timeline.width = Math.max(1, rect.width*dpr); timeline.height = Math.max(1, rect.height*dpr); ctx.scale(dpr,dpr); ctx.clearRect(0,0,rect.width,rect.height);
  if (!session) return; const rows = session.contact_force.part_order.length, rulerH = 18, labelW = 48, rowH = (rect.height-rulerH) / rows, plotW=rect.width-labelW;
  ctx.fillStyle='#202328'; ctx.fillRect(0,0,rect.width,rect.height);
  ctx.font='10px ui-monospace';ctx.textBaseline='middle';session.contact_force.part_order.forEach((name,i)=>{ctx.fillStyle='#aeb4bc';ctx.fillText(name,4,rulerH+i*rowH+rowH/2);});
  for(let i=0;i<=10;i++){const f=Math.round((session.qpos.length-1)*i/10),x=labelW+plotW*i/10;ctx.fillStyle='#858c95';ctx.fillText(String(f),x+2,8);ctx.strokeStyle='#343940';ctx.beginPath();ctx.moveTo(x,rulerH);ctx.lineTo(x,rect.height);ctx.stroke();}
  session.contact_force.masks.forEach((mask,t) => mask.forEach((on,i) => { if(on){ctx.fillStyle=`#${partColors[i].toString(16).padStart(6,'0')}`; ctx.fillRect(labelW+t/session!.qpos.length*plotW,rulerH+i*rowH,Math.max(1,plotW/session!.qpos.length+1),rowH-1);}}));
  if(selectedAnchor){const part=bodyPart[selectedAnchor.body]||selectedAnchor.body,lane=session.contact_force.part_order.indexOf(part);if(lane>=0){const x0=labelW+selectedAnchor.start_frame/session.qpos.length*plotW,x1=labelW+selectedAnchor.end_frame/session.qpos.length*plotW;ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.strokeRect(x0,rulerH+lane*rowH+1,Math.max(2,x1-x0),Math.max(2,rowH-3));ctx.lineWidth=1;}}
  for(const cut of stableCutFrames()){const x=labelW+cut/Math.max(1,session.qpos.length-1)*plotW;ctx.strokeStyle='#f4d35e';ctx.globalAlpha=.55;ctx.beginPath();ctx.moveTo(x,rulerH);ctx.lineTo(x,rect.height);ctx.stroke();}
  ctx.strokeStyle='#ffffff'; ctx.globalAlpha=.9; const x=labelW+frame/Math.max(1,session.qpos.length-1)*plotW; ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,rect.height);ctx.stroke();ctx.globalAlpha=1;
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

function selectAnchor(anchor: Anchor | null) {
  selectedAnchor=anchor; const box=byId('selection');
  const precision=byId('precisionEditor');
  if(!anchor){box.className='selection empty';box.textContent='None';precision.classList.add('disabled');precision.querySelectorAll<HTMLInputElement|HTMLButtonElement>('input,button').forEach(item=>item.disabled=true);guideGroup.clear();drawTimeline();return;}
  precision.classList.remove('disabled');precision.querySelectorAll<HTMLInputElement|HTMLButtonElement>('input,button').forEach(item=>item.disabled=false);
  box.className='selection'; box.innerHTML=`<strong>${anchor.body}</strong><code>${anchor.anchor_id}</code><dl><dt>Frames</dt><dd>${anchor.start_frame}–${anchor.end_frame}</dd><dt>Surface</dt><dd>${anchor.surface_id || 'unbound'}</dd><dt>Status</dt><dd>${anchorStatus(anchor)}</dd></dl>`;
  byId<HTMLInputElement>('targetU').value = anchor.surface_coordinates ? String(anchor.surface_coordinates.u.toFixed(4)) : '';
  byId<HTMLInputElement>('targetV').value = anchor.surface_coordinates ? String(anchor.surface_coordinates.v.toFixed(4)) : '';
  renderSelectionGuides(anchor);
  rebuildAnchors();drawTimeline();
}

function renderSelectionGuides(anchor:Anchor){
  guideGroup.clear();guideGroup.visible=byId<HTMLInputElement>('guideToggle').checked;if(!anchor.world_position)return;
  const origin=new THREE.Vector3(...anchor.world_position);const vectors:[[Vec3|null,number],[Vec3|null,number],[Vec3|null,number]]=[[anchor.surface_tangent_u,0xf06449],[anchor.surface_tangent_v,0x68d391],[anchor.surface_normal,0x4f8cff]];
  for(const [raw,color] of vectors){if(!raw)continue;const v=new THREE.Vector3(...raw).normalize().multiplyScalar(.14);const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([origin.clone().addScaledVector(v,-1),origin.clone().add(v)]),new THREE.LineBasicMaterial({color}));guideGroup.add(line);}
}

function pointerRay(event: PointerEvent) { const r=sceneCanvas.getBoundingClientRect();pointer.x=((event.clientX-r.left)/r.width)*2-1;pointer.y=-((event.clientY-r.top)/r.height)*2+1;raycaster.setFromCamera(pointer,camera); }
sceneCanvas.addEventListener('pointerdown', event => {
  pointerRay(event); const hit=raycaster.intersectObjects([...anchorMeshes.values()],false)[0]; if(!hit)return;
  const anchor=hit.object.userData.anchor as Anchor; selectAnchor(anchor); if(!anchor.surface_id)return;
  const surface=session?.surfaces.find(s=>s.surface_id===anchor.surface_id); if(!surface)return;
  dragPlane.setFromNormalAndCoplanarPoint(new THREE.Vector3(...surface.normal).normalize(),new THREE.Vector3(...surface.origin)); dragging=true; controls.enabled=false;sceneCanvas.style.cursor='grabbing'; sceneCanvas.setPointerCapture(event.pointerId);
});
sceneCanvas.addEventListener('pointermove', event => { pointerRay(event);if(!dragging||!selectedAnchor){sceneCanvas.style.cursor=raycaster.intersectObjects([...anchorMeshes.values()],false).length?'grab':'default';return;}const p=new THREE.Vector3();if(raycaster.ray.intersectPlane(dragPlane,p)){dragPreview=p;anchorMeshes.get(selectedAnchor.anchor_id)?.position.copy(p);} });
sceneCanvas.addEventListener('pointerup', async event => { if(!dragging)return;dragging=false;controls.enabled=true;sceneCanvas.style.cursor='default';sceneCanvas.releasePointerCapture(event.pointerId);if(!selectedAnchor||!dragPreview)return;try{showStatus('Applying contact edit');const next=await api<Session>('/api/session/move',{method:'POST',body:JSON.stringify({anchor_id:selectedAnchor.anchor_id,requested_world_position:dragPreview.toArray(),mode:byId<HTMLSelectElement>('modeSelect').value})});selectedAnchor=next.graph.anchors.find(a=>a.anchor_id===selectedAnchor!.anchor_id)||null;await applySession(next);}catch(e){showStatus(String(e),true);rebuildAnchors();}dragPreview=null;});

function focusScene(){const box=new THREE.Box3();if(robot)box.expandByObject(robot);if(terrain)box.expandByObject(terrain);if(box.isEmpty())return;const sphere=box.getBoundingSphere(new THREE.Sphere());controls.target.copy(sphere.center);camera.position.copy(sphere.center).add(new THREE.Vector3(sphere.radius*1.8,-sphere.radius*2.4,sphere.radius*1.35));controls.update();}
function showStatus(text:string,error=false){const el=byId('sceneStatus');el.textContent=text;el.classList.remove('hidden');el.classList.toggle('error',error);setTimeout(()=>el.classList.add('hidden'),3000);}

byId('loadBtn').onclick=async()=>{try{const next=await api<Session>('/api/session/load',{method:'POST',body:JSON.stringify({motion_asset_id:byId<HTMLSelectElement>('assetSelect').value})});await applySession(next,true);}catch(e){showStatus(String(e),true);}};
byId('playBtn').onclick=()=>{playing=!playing;byId('playBtn').innerHTML=`<i data-lucide="${playing?'pause':'play'}"></i>`;createIcons({icons:{Play,Pause}});};
byId('prevBtn').onclick=()=>setFrame(frame-1);byId('nextBtn').onclick=()=>setFrame(frame+1);byId<HTMLInputElement>('frameSlider').oninput=e=>setFrame(Number((e.target as HTMLInputElement).value));
byId<HTMLInputElement>('frameInput').onchange=e=>setFrame(Number((e.target as HTMLInputElement).value));
async function runSessionAction(path:string, body?:unknown){try{const next=await api<Session>(path,{method:'POST',body:body===undefined?undefined:JSON.stringify(body)});await applySession(next);return next;}catch(e){showStatus(String(e),true);return null;}}
byId('undoBtn').onclick=()=>{void runSessionAction('/api/session/undo');};byId('redoBtn').onclick=()=>{void runSessionAction('/api/session/redo');};
byId('saveBtn').onclick=async()=>{try{const result=await api<{output_contact_layer:string;plan:{status:string;edit_count:number}|null}>('/api/session/save',{method:'POST'});if(result.plan)byId('planStatus').textContent=`${result.plan.status} · ${result.plan.edit_count} edits`;showStatus(`Saved ${result.output_contact_layer}`);}catch(e){showStatus(String(e),true);}};
byId('focusBtn').onclick=focusScene;byId<HTMLInputElement>('terrainToggle').onchange=e=>{if(terrain)terrain.visible=(e.target as HTMLInputElement).checked;surfaceGroup.visible=(e.target as HTMLInputElement).checked;};
byId<HTMLInputElement>('surfaceToggle').onchange=e=>surfaceGroup.visible=(e.target as HTMLInputElement).checked;
byId<HTMLInputElement>('anchorToggle').onchange=()=>rebuildAnchors();byId<HTMLInputElement>('anchorSize').oninput=()=>rebuildAnchors();byId<HTMLInputElement>('forceScale').oninput=()=>updateForces();
byId<HTMLInputElement>('rootPathToggle').onchange=e=>{if(rootPath)rootPath.visible=(e.target as HTMLInputElement).checked;};byId<HTMLInputElement>('guideToggle').onchange=e=>guideGroup.visible=(e.target as HTMLInputElement).checked;
byId<HTMLInputElement>('anchorSearch').oninput=e=>{anchorSearch=(e.target as HTMLInputElement).value;rebuildAnchors();};
byId<HTMLSelectElement>('statusFilter').onchange=e=>{statusFilter=(e.target as HTMLSelectElement).value;rebuildAnchors();};
byId<HTMLInputElement>('currentOnly').onchange=e=>{currentOnly=(e.target as HTMLInputElement).checked;rebuildAnchors();};
document.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button=>button.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(item=>item.classList.remove('active'));document.querySelectorAll('[data-page]').forEach(item=>item.classList.remove('active'));button.classList.add('active');document.querySelector(`[data-page="${button.dataset.tab}"]`)?.classList.add('active');});

function selectRelativeAnchor(offset:number){const items=matchingAnchors();if(!items.length)return;const current=Math.max(0,items.findIndex(item=>item.anchor_id===selectedAnchor?.anchor_id));const anchor=items[(current+offset+items.length)%items.length];selectAnchor(anchor);setFrame(anchor.start_frame);}
byId('prevAnchor').onclick=()=>selectRelativeAnchor(-1);byId('nextAnchor').onclick=()=>selectRelativeAnchor(1);
byId('restoreAnchor').onclick=()=>{if(selectedAnchor)void runSessionAction('/api/session/restore-anchor',{anchor_id:selectedAnchor.anchor_id,mode:byId<HTMLSelectElement>('modeSelect').value});};
byId('applyUv').onclick=()=>{if(selectedAnchor)void runSessionAction('/api/session/move',{anchor_id:selectedAnchor.anchor_id,target_uv:[Number(byId<HTMLInputElement>('targetU').value),Number(byId<HTMLInputElement>('targetV').value)],mode:byId<HTMLSelectElement>('modeSelect').value});};
document.querySelectorAll<HTMLButtonElement>('[data-du]').forEach(button=>button.onclick=()=>{if(!selectedAnchor)return;const step=Number(byId<HTMLInputElement>('moveStep').value);void runSessionAction('/api/session/move',{anchor_id:selectedAnchor.anchor_id,tangent_delta:[Number(button.dataset.du)*step,Number(button.dataset.dv)*step],mode:byId<HTMLSelectElement>('modeSelect').value});});

function selectRelativeCut(offset:number){const cuts=stableCutFrames();if(!cuts.length)return;const ordered=offset>0?cuts:cuts.slice().reverse();const next=ordered.find(value=>offset>0?value>frame:value<frame) ?? ordered[0];setFrame(next);}
byId('prevCut').onclick=()=>selectRelativeCut(-1);byId('nextCut').onclick=()=>selectRelativeCut(1);
timeline.addEventListener('pointerdown',event=>{if(!session)return;const rect=timeline.getBoundingClientRect(),labelW=48,rulerH=18;const next=Math.round(Math.max(0,Math.min(1,(event.clientX-rect.left-labelW)/Math.max(1,rect.width-labelW)))*(session.qpos.length-1));setFrame(next);const lane=Math.floor((event.clientY-rect.top-rulerH)/Math.max(1,(rect.height-rulerH)/8));const body=partBody[session.contact_force.part_order[Math.max(0,Math.min(7,lane))]];const candidates=session.graph.anchors.filter(anchor=>anchor.body===body&&activeAt(anchor));if(candidates.length)selectAnchor(candidates[0]);});
timeline.addEventListener('pointermove',event=>{if(!session)return;const rect=timeline.getBoundingClientRect(),labelW=48,rulerH=18,hover=byId('timelineHover');const ratio=Math.max(0,Math.min(1,(event.clientX-rect.left-labelW)/Math.max(1,rect.width-labelW))),next=Math.round(ratio*(session.qpos.length-1)),lane=Math.floor((event.clientY-rect.top-rulerH)/Math.max(1,(rect.height-rulerH)/8)),part=session.contact_force.part_order[Math.max(0,Math.min(7,lane))];hover.textContent=`${part} · frame ${next}`;hover.style.left=`${Math.max(52,Math.min(rect.width-90,event.clientX-rect.left))}px`;hover.classList.remove('hidden');});
timeline.addEventListener('pointerleave',()=>byId('timelineHover').classList.add('hidden'));

byId('applySettings').onclick=async()=>{try{const next=await api<Session>('/api/session/settings',{method:'PUT',body:JSON.stringify({edit_plan_path:byId<HTMLInputElement>('planPath').value,output_contact_layer:byId<HTMLInputElement>('outputLayer').value})});await applySession(next);showStatus('Output settings applied');}catch(e){showStatus(String(e),true);}};
byId('validateBtn').onclick=async()=>{try{const result=await api<{plan:{status:string};warnings:string[]}>('/api/session/validate',{method:'POST'});byId('planStatus').textContent=`${result.plan.status}${result.warnings.length?` · ${result.warnings.length} warnings`:''}`;showStatus('ContactEditPlan validated');}catch(e){showStatus(String(e),true);}};
byId('reloadBtn').onclick=()=>{void runSessionAction('/api/session/reload');};byId('discardBtn').onclick=()=>{void runSessionAction('/api/session/discard');};

window.addEventListener('keydown',event=>{if((event.target as HTMLElement).matches('input,select,textarea'))return;if(event.code==='Space'){event.preventDefault();byId<HTMLButtonElement>('playBtn').click();}else if(event.code==='ArrowLeft')setFrame(frame-(event.shiftKey?10:1));else if(event.code==='ArrowRight')setFrame(frame+(event.shiftKey?10:1));else if(event.code==='BracketLeft')selectRelativeAnchor(-1);else if(event.code==='BracketRight')selectRelativeAnchor(1);});

let resizeStartY=0,resizeStartHeight=0;
byId('timelineResizer').addEventListener('pointerdown',event=>{resizingTimeline=true;resizeStartY=event.clientY;resizeStartHeight=timelineHeight;byId('timelineResizer').setPointerCapture(event.pointerId);document.body.classList.add('resizing-timeline');});
byId('timelineResizer').addEventListener('pointermove',event=>{if(resizingTimeline)setTimelineHeight(resizeStartHeight+resizeStartY-event.clientY);});
byId('timelineResizer').addEventListener('pointerup',event=>{if(!resizingTimeline)return;resizingTimeline=false;byId('timelineResizer').releasePointerCapture(event.pointerId);document.body.classList.remove('resizing-timeline');setTimelineHeight(timelineHeight,true);});

function resize(){const r=sceneCanvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();drawTimeline();}
window.addEventListener('resize',resize);resize();
function animate(now:number){requestAnimationFrame(animate);const dt=(now-lastTick)/1000;lastTick=now;if(playing&&session){frameAccumulator+=dt*Number(byId<HTMLInputElement>('fpsInput').value);if(frameAccumulator>=1){const step=Math.floor(frameAccumulator);frameAccumulator-=step;setFrame((frame+step)%session.qpos.length);}}controls.update();renderer.render(scene,camera);}requestAnimationFrame(animate);
loadAssets().catch(e=>showStatus(String(e),true));
