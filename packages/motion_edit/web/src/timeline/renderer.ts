import type { EditHandle, Session } from '../core/types';

export type TimelineMetrics = {
  width: number;
  height: number;
  labelW: number;
  rulerH: number;
  rowH: number;
  plotW: number;
  rows: number;
};

type TimelineRenderState = {
  canvas: HTMLCanvasElement;
  session: Session | null;
  frame: number;
  selectedHandle: EditHandle | null;
  stableCuts: number[];
  partColors: number[];
};

const handleParts: Record<string, string[]> = {
  left_foot: ['LHEE', 'LTOE'],
  right_foot: ['RHEE', 'RTOE'],
  left_hand: ['LH'],
  right_hand: ['RH'],
  left_knee: ['LK'],
  right_knee: ['RK'],
};

export function getTimelineMetrics(canvas: HTMLCanvasElement, rows = 8): TimelineMetrics {
  const rect = canvas.getBoundingClientRect();
  const laneCount = Math.max(1, rows);
  const labelW = rect.width < 560 ? 54 : 68;
  const rulerH = 28;
  return {
    width: rect.width,
    height: rect.height,
    labelW,
    rulerH,
    rowH: Math.max(1, (rect.height - rulerH) / laneCount),
    plotW: Math.max(1, rect.width - labelW),
    rows: laneCount,
  };
}

export function frameToX(value: number, metrics: TimelineMetrics, frameCount: number): number {
  return metrics.labelW + value / Math.max(1, frameCount - 1) * metrics.plotW;
}

export function xToFrame(value: number, metrics: TimelineMetrics, frameCount: number): number {
  const ratio = Math.max(0, Math.min(1, (value - metrics.labelW) / metrics.plotW));
  return Math.round(ratio * Math.max(0, frameCount - 1));
}

function niceStep(raw: number): number {
  const power = 10 ** Math.floor(Math.log10(Math.max(raw, 1e-6)));
  const scaled = raw / power;
  return (scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10) * power;
}

export function formatTimelineTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return minutes
    ? `${minutes}:${rest.toFixed(rest < 10 ? 1 : 0).padStart(rest < 10 ? 4 : 2, '0')}`
    : `${rest.toFixed(rest < 10 ? 1 : 0)}s`;
}

export function renderTimeline(state: TimelineRenderState): void {
  const { canvas, session, frame, selectedHandle, stableCuts, partColors } = state;
  const metrics = getTimelineMetrics(canvas, session?.contact_force.part_order.length ?? 8);
  const context = canvas.getContext('2d');
  if (!context) return;

  const dpr = Math.min(window.devicePixelRatio, 2);
  canvas.width = Math.max(1, Math.round(metrics.width * dpr));
  canvas.height = Math.max(1, Math.round(metrics.height * dpr));
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, metrics.width, metrics.height);
  context.fillStyle = '#0b1117';
  context.fillRect(0, 0, metrics.width, metrics.height);
  if (!session) return;

  const frameCount = session.qpos.length;
  context.fillStyle = '#0d141b';
  context.fillRect(0, 0, metrics.labelW, metrics.height);
  context.fillStyle = '#111923';
  context.fillRect(metrics.labelW, 0, metrics.plotW, metrics.rulerH);

  for (let lane = 0; lane < metrics.rows; lane++) {
    const y = metrics.rulerH + lane * metrics.rowH;
    context.fillStyle = lane % 2 === 0 ? '#121a22' : '#0f171f';
    context.fillRect(metrics.labelW, y, metrics.plotW, metrics.rowH);
    context.strokeStyle = '#22303c';
    context.beginPath();
    context.moveTo(0, Math.round(y) + 0.5);
    context.lineTo(metrics.width, Math.round(y) + 0.5);
    context.stroke();
    context.fillStyle = `#${partColors[lane % partColors.length].toString(16).padStart(6, '0')}`;
    context.fillRect(8, y + metrics.rowH / 2 - 3, 6, 6);
    context.fillStyle = '#aebbc7';
    context.font = '600 10px ui-monospace,monospace';
    context.textBaseline = 'middle';
    context.fillText(session.contact_force.part_order[lane] || '', 20, y + metrics.rowH / 2);
  }

  const duration = Math.max(1, frameCount - 1) / session.fps;
  const majorSeconds = niceStep(duration / Math.max(2, Math.floor(metrics.plotW / 92)));
  const majorFrames = Math.max(1, Math.round(majorSeconds * session.fps));
  const minorFrames = Math.max(1, Math.round(majorFrames / 5));
  for (let tick = 0; tick < frameCount; tick += minorFrames) {
    const x = Math.round(frameToX(tick, metrics, frameCount)) + 0.5;
    const major = tick % majorFrames === 0;
    context.strokeStyle = major ? '#344451' : '#1d2a34';
    context.globalAlpha = major ? 0.9 : 0.65;
    context.beginPath();
    context.moveTo(x, major ? metrics.rulerH - 7 : metrics.rulerH - 4);
    context.lineTo(x, metrics.height);
    context.stroke();
    context.globalAlpha = 1;
    if (major) {
      context.fillStyle = '#aeb5bd';
      context.font = '10px ui-monospace,monospace';
      context.fillText(formatTimelineTime(tick / session.fps), Math.min(x + 4, metrics.width - 38), 10);
      context.fillStyle = '#6f7780';
      context.font = '9px ui-monospace,monospace';
      context.fillText(String(tick), Math.min(x + 4, metrics.width - 32), 21);
    }
  }
  context.fillStyle = '#7e8790';
  context.font = '9px ui-monospace,monospace';
  context.fillText('TIME', 8, 9);
  context.fillText('FRAME', 8, 21);

  for (let lane = 0; lane < metrics.rows; lane++) {
    let start = -1;
    for (let tick = 0; tick <= frameCount; tick++) {
      const active = tick < frameCount && Boolean(session.contact_force.masks[tick]?.[lane]);
      if (active && start < 0) start = tick;
      if (!active && start >= 0) {
        const x0 = frameToX(start, metrics, frameCount);
        const x1 = frameToX(Math.max(start, tick - 1), metrics, frameCount) + Math.max(1, metrics.plotW / frameCount);
        context.fillStyle = `#${partColors[lane % partColors.length].toString(16).padStart(6, '0')}`;
        context.globalAlpha = 0.78;
        context.beginPath();
        context.roundRect(x0, metrics.rulerH + lane * metrics.rowH + 3, Math.max(2, x1 - x0), Math.max(2, metrics.rowH - 6), 2);
        context.fill();
        context.globalAlpha = 1;
        start = -1;
      }
    }
  }

  if (selectedHandle) {
    const selectedParts = handleParts[selectedHandle.body] || [selectedHandle.body];
    const x0 = frameToX(selectedHandle.start_frame, metrics, frameCount);
    const x1 = frameToX(Math.max(selectedHandle.start_frame, selectedHandle.end_frame - 1), metrics, frameCount);
    for (const part of selectedParts) {
      const lane = session.contact_force.part_order.indexOf(part);
      if (lane < 0) continue;
      context.strokeStyle = '#b7fff1';
      context.lineWidth = 1.5;
      context.strokeRect(x0 + 0.5, metrics.rulerH + lane * metrics.rowH + 2.5, Math.max(3, x1 - x0), Math.max(3, metrics.rowH - 5));
      context.lineWidth = 1;
    }
  }

  context.setLineDash([3, 3]);
  for (const cut of stableCuts) {
    const x = Math.round(frameToX(cut, metrics, frameCount)) + 0.5;
    context.strokeStyle = '#d9b96e';
    context.globalAlpha = 0.38;
    context.beginPath();
    context.moveTo(x, metrics.rulerH);
    context.lineTo(x, metrics.height);
    context.stroke();
  }
  context.setLineDash([]);
  context.globalAlpha = 1;

  const cursorX = Math.round(frameToX(frame, metrics, frameCount)) + 0.5;
  context.strokeStyle = '#72ead3';
  context.lineWidth = 1.5;
  context.beginPath();
  context.moveTo(cursorX, 0);
  context.lineTo(cursorX, metrics.height);
  context.stroke();
  context.fillStyle = '#72ead3';
  context.beginPath();
  context.moveTo(cursorX - 5, 0);
  context.lineTo(cursorX + 5, 0);
  context.lineTo(cursorX, 7);
  context.closePath();
  context.fill();
  context.lineWidth = 1;
}
