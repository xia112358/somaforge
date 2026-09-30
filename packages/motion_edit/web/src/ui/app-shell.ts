import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Focus,
  LoaderCircle,
  Pause,
  Play,
  Redo2,
  RefreshCw,
  RotateCcw,
  Save,
  StepBack,
  StepForward,
  Trash2,
  Undo2,
  WandSparkles,
  createIcons,
} from 'lucide';

const topbar = () => `
  <header class="topbar">
    <div class="brand"><div><strong>Motion Edit</strong><span id="motionLabel">No motion</span></div></div>
    <div class="top-actions">
      <button class="icon" id="focusBtn" title="Frame scene"><i data-lucide="focus"></i></button>
      <button class="icon" id="undoBtn" title="Undo"><i data-lucide="undo-2"></i></button>
      <button class="icon" id="redoBtn" title="Redo"><i data-lucide="redo-2"></i></button>
      <button class="icon primary" id="saveBtn" title="Save contact edit plan"><i data-lucide="save"></i></button>
    </div>
  </header>`;

const viewport = () => `
  <section class="viewport">
    <canvas id="scene"></canvas>
    <div class="viewport-hud"><strong id="viewportMotion">No motion loaded</strong><span id="viewportFrame">Frame 0</span><span id="viewportTime">0.00 s</span></div>
    <div class="shortcut-hint"><span>Space</span> Play <span>← →</span> Frame <span>[ ]</span> Contact</div>
    <div id="sceneStatus" class="scene-status">Select a motion asset</div>
  </section>`;

const contactPanel = () => `
  <div class="tab-page active" data-page="contact">
    <div class="page-heading"><strong>Contacts</strong><div class="heading-stats"><span id="anchorCount">0 handles</span><span id="editCount">0 edits</span></div></div>
    <section id="reviewPanel" hidden></section>
    <div id="selection" class="selection empty">None</div>
    <div class="position-offset disabled" id="positionOffset">
      <div class="panel-title">Position offset</div>
      <dl><div><dt>Δu</dt><dd id="offsetU">—</dd></div><div><dt>Δv</dt><dd id="offsetV">—</dd></div></dl>
    </div>
    <div class="anchor-browser">
      <div class="browser-heading">Browse contact episodes</div>
      <div class="anchor-nav"><button class="nav-command" id="prevAnchor" title="Previous matching contact"><i data-lucide="chevron-left"></i><span>Previous</span></button><button class="nav-command" id="nextAnchor" title="Next matching contact"><span>Next</span><i data-lucide="chevron-right"></i></button></div>
      <div class="filter-grid"><input id="anchorSearch" placeholder="Filter body, surface, id" /><select id="statusFilter"><option value="all">All status</option><option value="bound">Bound</option><option value="edited">Edited</option><option value="clamped">Clamped</option><option value="suspicious">Suspicious</option><option value="failed">Failed</option><option value="unbound">Unbound</option></select></div>
      <div class="browse-options"><label class="toggle"><input id="currentOnly" type="checkbox" checked /><span>Current frame only</span></label><label class="field"><span>Boundary</span><select id="modeSelect"><option value="reject">Reject</option><option value="clamp">Clamp</option></select></label></div>
    </div>
  </div>`;

const displayPanel = () => `
  <div class="tab-page" data-page="display">
    <div class="page-heading"><strong>Display</strong></div>
    <section class="display-section"><div class="section-heading">Scene</div><div class="layer-list">
      <label class="toggle"><input id="terrainToggle" type="checkbox" checked /><span>Terrain mesh</span></label><label class="toggle"><input id="surfaceToggle" type="checkbox" /><span>Contact surfaces</span></label><label class="toggle"><input id="contactSampleToggle" type="checkbox" checked /><span>Contact point + force</span></label><label class="toggle"><input id="handleToggle" type="checkbox" checked /><span>Edit handles</span></label><label class="toggle"><input id="rootPathToggle" type="checkbox" /><span>Root path</span></label><label class="toggle"><input id="guideToggle" type="checkbox" checked /><span>Selection guides</span></label>
    </div></section>
    <section class="display-section"><div class="section-heading">Appearance</div><label class="slider-field"><span>Handle size</span><input id="handleSize" type="range" min="70" max="180" value="110" /></label><label class="slider-field"><span>Force scale</span><input id="forceScale" type="range" min="25" max="300" value="100" /></label></section>
    <section class="display-section"><div class="section-heading">Channels</div><div id="partLegend" class="part-legend"></div></section>
  </div>`;

const outputPanel = () => `
  <div class="tab-page" data-page="output">
    <div class="page-heading"><strong>Output</strong></div>
    <div id="generationStatus" class="generation-status idle"><strong>Ready</strong><span>Formal edited reference</span></div>
    <div id="planStatus" class="plan-status">No plan saved</div>
    <div class="pipeline-actions"><button id="validateBtn" class="secondary-command"><i data-lucide="check"></i><span>Validate</span></button><button id="generateBtn" class="generate-command"><i data-lucide="wand-sparkles"></i><span>Generate</span></button></div>
    <details class="output-settings"><summary>Advanced settings</summary><label class="stack-field"><span>Edit plan</span><input id="planPath" /></label><label class="stack-field"><span>Generated motion</span><input id="outputMotion" /></label><div class="output-pair"><label class="stack-field"><span>Contact layer</span><input id="outputLayer" /></label><label class="stack-field"><span>Segment layer</span><input id="outputSegment" /></label></div><label class="stack-field"><span>Motion ID</span><input id="outputMotionId" /></label><label class="toggle"><input id="registerMotion" type="checkbox" checked /><span>Register motion</span></label><label class="toggle"><input id="overwriteOutput" type="checkbox" /><span>Replace existing output</span></label></details>
    <div class="source-reference"><span>Source contact layer</span><code id="sourceLayer"></code></div>
    <div class="session-actions"><button id="reloadBtn"><i data-lucide="refresh-cw"></i><span>Reload</span></button><button id="discardBtn"><i data-lucide="trash-2"></i><span>Discard edits</span></button></div>
  </div>`;

const inspector = () => `
  <aside class="inspector">
    <div class="inspector-tabs"><button data-tab="contact" class="active">Contact</button><button data-tab="display">Display</button><button data-tab="output">Output</button></div>
    <div class="inspector-pages">${contactPanel()}${displayPanel()}${outputPanel()}</div>
    <section class="recent-motion-dock" aria-label="Motions opened this session"><div class="recent-motion-head"><span>This session</span><small id="recentMotionCount">0</small></div><div id="recentMotionList" class="recent-motion-list"></div><details><summary>打开只读回放／实验报告</summary><input id="reviewPath" placeholder="项目内 NPZ / JSON 路径" /><input id="reviewTerrain" placeholder="地形 OBJ 路径（可选）" /><button id="reviewOpen">打开</button></details></section>
  </aside>`;

const timeline = () => `
  <section class="timeline-panel">
    <div id="timelineResizer" class="timeline-resizer" title="Drag to resize timeline"><span></span></div>
    <div class="transport"><div class="toolbar-group cut-nav"><button class="icon" id="prevCut" title="Previous stable cut"><i data-lucide="chevrons-left"></i></button><button class="icon" id="nextCut" title="Next stable cut"><i data-lucide="chevrons-right"></i></button></div><div class="transport-main"><div class="toolbar-group playback-nav"><button class="icon" id="prevBtn" title="Previous frame"><i data-lucide="step-back"></i></button><button class="icon play" id="playBtn" title="Play or pause"><i data-lucide="play"></i></button><button class="icon" id="nextBtn" title="Next frame"><i data-lucide="step-forward"></i></button></div><div class="frame-readout"><input id="frameInput" class="frame-input" type="number" min="0" value="0" /><span id="frameTotal">/ 0</span></div></div><label class="fps">FPS <input id="fpsInput" type="number" min="1" max="240" value="50" /></label></div>
    <div class="timeline-wrap"><canvas id="timeline" aria-label="Contact timeline"></canvas><div id="timelineHover" class="timeline-hover hidden"></div></div>
  </section>`;

export function mountAppShell(root: HTMLElement): void {
  const template = document.createElement('template');
  template.innerHTML = `${topbar()}<main class="workspace">${viewport()}${inspector()}${timeline()}</main>`;
  root.replaceChildren(template.content.cloneNode(true));
  refreshIcons();
}

export function refreshIcons(): void {
  createIcons({ icons: { Play, Pause, StepBack, StepForward, Undo2, Redo2, Save, RotateCcw, Focus, RefreshCw, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Trash2, WandSparkles, LoaderCircle } });
}
