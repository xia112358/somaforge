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
  FolderOpen,
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
      <button class="icon" id="openMotionBtn" title="打开轨迹／回放／报告" aria-label="打开轨迹／回放／报告"><i data-lucide="folder-open"></i></button>
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
    <div class="shortcut-hint"><span>Space</span> Play <span>← →</span> Frame <span class="episode-shortcut"><span>[ ]</span> Episode</span></div>
    <div id="sceneStatus" class="scene-status">Select a motion asset</div>
    <button id="retryLoad" class="retry-load" hidden>Retry loading</button>
  </section>`;

const contactPanel = () => `
  <div class="tab-page active" data-page="contact">
    <div class="page-heading"><strong id="contactHeading">Contacts</strong><div class="heading-stats"><span id="anchorCount">0 handles</span><span id="editCount">0 edits</span></div></div>
    <section id="collectionPanel" hidden>
      <label class="stack-field"><span>案例</span><select id="reviewCase" aria-label="案例"></select></label>
      <label class="stack-field"><span>参考轨迹</span><select id="reviewReference" aria-label="参考轨迹"></select></label>
      <label class="stack-field"><span>对比方式</span><select id="reviewLayout" aria-label="对比方式"><option value="beside">并排：参考在 −Y，当前在 +Y</option><option value="overlay">原坐标叠加：蓝色为参考</option></select></label>
      <p id="comparisonClock"></p>
      <label class="stack-field"><span>片段</span><select id="reviewSegment" aria-label="片段"></select></label>
      <p id="reviewMetrics"></p><button id="reviewWorst">定位最大穿透帧</button>
    </section>
    <section id="reviewPanel" hidden></section>
    <p id="playbackNotice" class="playback-notice" hidden>只读轨迹：接触状态以已验证的 Newton 数据为准；无接触层时不显示编辑手柄。</p>
    <div class="anchor-browser">
      <label class="stack-field"><span>接触段 · 跳到起始帧</span><select id="episodeSelect" aria-label="选择接触段"><option value="">选择接触段</option></select></label>
      <div id="episodeBrowseStatus" class="episode-browse-status" role="status" aria-live="polite">No matching episodes</div>
      <details id="episodeOptions" class="compact-options"><summary>筛选与拖动设置</summary>
        <div class="filter-grid"><input id="anchorSearch" aria-label="Filter contact episodes" placeholder="Filter body, surface, id" /><select id="statusFilter" aria-label="Contact episode status"><option value="all">All status</option><option value="bound">Bound</option><option value="edited">Edited</option></select></div>
        <div class="browse-options"><label class="toggle" title="仅控制三维视窗中手柄的显示范围"><input id="currentOnly" type="checkbox" checked /><span>Current frame only</span></label><label class="field" title="How dragging handles beyond the bound surface is handled"><span>Boundary</span><select id="modeSelect" aria-label="Drag boundary behavior"><option value="reject">Reject</option><option value="clamp">Clamp</option></select></label></div>
      </details>
    </div>
    <div id="selection" class="selection empty">None</div>
    <div class="position-offset disabled" id="positionOffset">
      <div class="panel-title">Position offset</div>
      <dl><div><dt>Δu</dt><dd id="offsetU">—</dd></div><div><dt>Δv</dt><dd id="offsetV">—</dd></div></dl>
    </div>
  </div>`;

const displayPanel = () => `
  <div class="tab-page" data-page="display">
    <div class="page-heading"><strong>Display</strong></div>
    <section class="display-section"><div class="section-heading">Scene</div><div class="layer-list">
      <label class="toggle"><input id="terrainToggle" type="checkbox" checked /><span>Terrain mesh</span></label><label class="toggle"><input id="surfaceToggle" type="checkbox" /><span>Contact surfaces</span></label><label class="toggle"><input id="contactSampleToggle" type="checkbox" checked /><span>Contact point + force</span></label><label class="toggle edit-only"><input id="handleToggle" type="checkbox" checked /><span>Edit handles</span></label><label class="toggle"><input id="rootPathToggle" type="checkbox" /><span>Root path</span></label>
    </div></section>
    <section class="display-section"><div class="section-heading">Camera / Terrain</div>
      <button id="focusRobot">聚焦机器人</button>
      <label class="toggle"><input id="followRobot" type="checkbox" /><span>跟随当前机器人</span></label>
      <label class="slider-field"><span>地形透明度</span><input id="terrainOpacity" aria-label="地形透明度" type="range" min="0.05" max="1" step="0.05" value="1" /></label>
    </section>
    <details id="displayOptions" class="compact-options"><summary>显示细节</summary>
      <label class="toggle edit-only"><input id="guideToggle" type="checkbox" checked /><span>Selection guides</span></label>
      <label class="slider-field edit-only"><span>Handle size</span><input id="handleSize" type="range" min="70" max="180" value="110" /></label>
      <label class="slider-field"><span>Force scale</span><input id="forceScale" type="range" min="25" max="300" value="100" /></label>
      <div id="partLegend" class="part-legend"></div>
    </details>
  </div>`;

const outputPanel = () => `
  <div class="tab-page" data-page="output">
    <div class="page-heading"><strong>Output</strong></div>
    <div id="generationStatus" class="generation-status idle"><strong>Ready</strong><span>Candidate · native validation required</span></div>
    <div id="planStatus" class="plan-status">No plan saved</div>
    <div class="pipeline-actions"><button id="validateBtn" class="secondary-command"><i data-lucide="check"></i><span>Validate</span></button><button id="generateBtn" class="generate-command"><i data-lucide="wand-sparkles"></i><span>Generate</span></button></div>
    <details class="output-settings"><summary>Advanced settings</summary><label class="stack-field"><span>Edit plan</span><input id="planPath" /></label><label class="stack-field"><span>Generated motion</span><input id="outputMotion" /></label><label class="stack-field"><span>Edited contact draft</span><input id="outputLayer" /></label><label class="stack-field"><span>Motion ID</span><input id="outputMotionId" /></label><label class="toggle"><input id="registerMotion" type="checkbox" checked /><span>Register motion</span></label><label class="toggle"><input id="overwriteOutput" type="checkbox" /><span>Replace existing output</span></label></details>
    <div class="source-reference"><span>Source contact layer</span><code id="sourceLayer"></code></div>
    <div class="session-actions"><button id="reloadBtn"><i data-lucide="refresh-cw"></i><span>Reload</span></button><button id="discardBtn"><i data-lucide="trash-2"></i><span>Discard edits</span></button></div>
  </div>`;

const inspector = () => `
  <aside class="inspector">
    <div class="inspector-tabs"><button data-tab="contact" class="active">Contact</button><button data-tab="display">Display</button><button data-tab="output">Output</button></div>
    <div class="inspector-pages">${contactPanel()}${displayPanel()}${outputPanel()}</div>
    <details class="recent-motion-dock" aria-label="Motions opened this session"><summary class="recent-motion-head"><span>最近打开</span><small id="recentMotionCount">0</small></summary><div id="recentMotionList" class="recent-motion-list"></div></details>
  </aside>`;

const timeline = () => `
  <section class="timeline-panel">
    <div id="timelineResizer" class="timeline-resizer" title="Drag to resize timeline"><span></span></div>
    <div class="transport"><div class="toolbar-group cut-nav" role="group" aria-label="切分点导航"><button class="icon" id="prevCut" title="上一切分点（到开头后循环）" aria-label="上一切分点"><i data-lucide="chevrons-left"></i></button><span>切分点</span><button class="icon" id="nextCut" title="下一切分点（到末尾后循环）" aria-label="下一切分点"><i data-lucide="chevrons-right"></i></button></div><div class="transport-main"><div class="toolbar-group playback-nav"><button class="icon" id="prevBtn" title="Previous frame"><i data-lucide="step-back"></i></button><button class="icon play" id="playBtn" title="Play or pause"><i data-lucide="play"></i></button><button class="icon" id="nextBtn" title="Next frame"><i data-lucide="step-forward"></i></button></div><div class="frame-readout"><input id="frameInput" class="frame-input" type="number" min="0" value="0" /><span id="frameTotal">/ 0</span></div></div><label class="fps">FPS <input id="fpsInput" type="number" min="1" max="240" value="50" /></label></div>
    <div class="timeline-wrap"><canvas id="timeline" aria-label="Contact timeline"></canvas><div id="timelineHover" class="timeline-hover hidden"></div></div>
  </section>`;

export function mountAppShell(root: HTMLElement): void {
  const template = document.createElement('template');
  template.innerHTML = `${topbar()}<main class="workspace">${viewport()}${inspector()}${timeline()}</main>
    <dialog id="motionPicker" aria-labelledby="motionPickerTitle"><div class="motion-picker-head"><strong id="motionPickerTitle">打开轨迹／回放／报告</strong><button id="closeMotionPicker" aria-label="Close motion picker">关闭</button></div>
      <form id="reviewOpenForm" class="review-open-form"><label for="reviewPath">文件路径</label><input id="reviewPath" required aria-label="回放或案例清单路径" placeholder="NPZ / 报告 / manifest.json / cases.json" /><input id="reviewTerrain" aria-label="地形路径" placeholder="地形 OBJ 路径（可选）" /><button id="reviewOpen" type="submit">打开文件</button></form>
      <label for="motionSearch">已注册轨迹 · 搜索名称或 ID</label><input id="motionSearch" type="search" autocomplete="off" placeholder="搜索轨迹" /><div id="motionPickerList"></div>
    </dialog>`;
  root.replaceChildren(template.content.cloneNode(true));
  refreshIcons();
}

export function refreshIcons(): void {
  createIcons({ icons: { Play, Pause, StepBack, StepForward, Undo2, Redo2, Save, RotateCcw, Focus, FolderOpen, RefreshCw, Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Trash2, WandSparkles, LoaderCircle } });
}
