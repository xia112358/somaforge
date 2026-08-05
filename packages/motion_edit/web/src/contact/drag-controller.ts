import * as THREE from 'three';
import type { EditHandle, Session } from '../core/types';
import { ContactHandleLayer } from './handle-layer';

export const DRAG_START_THRESHOLD_PX = 8;
export const MIN_EDIT_DISTANCE_M = 0.002;

type DragInteraction = {
  kind: 'drag';
  pointerId: number;
  handle: EditHandle;
  startX: number;
  startY: number;
  plane: THREE.Plane;
  offset: THREE.Vector3;
  preview: THREE.Vector3 | null;
  dragging: boolean;
};

type RestoreInteraction = {
  kind: 'restore';
  pointerId: number;
  handle: EditHandle;
  startX: number;
  startY: number;
};

type PointerInteraction = DragInteraction | RestoreInteraction;

type Controls = { enabled: boolean };

type ContactDragControllerOptions = {
  canvas: HTMLCanvasElement;
  controls: Controls;
  layer: ContactHandleLayer;
  getSession: () => Session | null;
  getSelectedHandle: () => EditHandle | null;
  selectHandle: (handle: EditHandle) => void;
  updatePositionOffset: (handle: EditHandle, preview?: THREE.Vector3) => void;
  moveHandle: (handle: EditHandle, requestedPosition: THREE.Vector3) => Promise<boolean>;
  restoreHandle: (handle: EditHandle) => Promise<boolean>;
  rebuildHandles: () => void;
};

function pointerDistance(interaction: PointerInteraction, event: PointerEvent): number {
  return Math.hypot(event.clientX - interaction.startX, event.clientY - interaction.startY);
}

export class ContactDragController {
  private interaction: PointerInteraction | null = null;

  constructor(private readonly options: ContactDragControllerOptions) {
    const { canvas } = options;
    canvas.addEventListener('pointerdown', this.onPointerDown);
    canvas.addEventListener('pointermove', this.onPointerMove);
    canvas.addEventListener('pointerup', this.onPointerUp);
    canvas.addEventListener('pointercancel', () => this.cancel());
    canvas.addEventListener('pointerleave', () => {
      if (this.interaction) this.cancel();
    });
  }

  get active(): boolean {
    return this.interaction !== null;
  }

  cancel(state = 'cancelled'): void {
    const interaction = this.interaction;
    if (interaction?.kind === 'drag') {
      this.options.layer.restorePosition(interaction.handle);
      this.options.updatePositionOffset(interaction.handle);
    }
    this.interaction = null;
    this.options.controls.enabled = true;
    this.options.canvas.style.cursor = 'default';
    this.setState(state);
    if (interaction) this.releasePointer(interaction.pointerId);
  }

  private readonly onPointerDown = (event: PointerEvent): void => {
    const { canvas, layer } = this.options;
    const session = this.options.getSession();
    if (!event.isPrimary || event.button !== 0 || session?.read_only || session?.generation.status === 'running') return;

    const selectedHandle = this.options.getSelectedHandle();
    const restoreHandle = layer.pickRestoreGhost(event, selectedHandle);
    if (restoreHandle) {
      this.options.selectHandle(restoreHandle);
      this.interaction = {
        kind: 'restore',
        pointerId: event.pointerId,
        handle: restoreHandle,
        startX: event.clientX,
        startY: event.clientY,
      };
      this.options.controls.enabled = false;
      canvas.style.cursor = 'pointer';
      this.setState('restore-armed');
      this.capturePointer(event.pointerId);
      return;
    }

    const handle = layer.pickHandle(event, session?.edit_handles ?? [], selectedHandle);
    this.setState(handle ? 'handle-hit' : 'miss');
    if (!handle) return;
    if (selectedHandle?.handle_id !== handle.handle_id) {
      this.options.selectHandle(handle);
      this.setState('selected');
      return;
    }

    const surface = session?.surfaces.find(item => item.surface_id === handle.surface_id);
    if (!surface) {
      this.setState('surface-missing');
      return;
    }
    const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(
      new THREE.Vector3(...surface.normal).normalize(),
      new THREE.Vector3(...surface.origin),
    );
    const planeHit = new THREE.Vector3();
    if (!layer.intersectPointerPlane(event, plane, planeHit)) {
      this.setState('plane-miss');
      return;
    }
    this.interaction = {
      kind: 'drag',
      pointerId: event.pointerId,
      handle,
      startX: event.clientX,
      startY: event.clientY,
      plane,
      offset: new THREE.Vector3(...handle.world_position).sub(planeHit),
      preview: null,
      dragging: false,
    };
    this.options.controls.enabled = false;
    canvas.style.cursor = 'grab';
    this.setState('armed');
    this.capturePointer(event.pointerId);
  };

  private readonly onPointerMove = (event: PointerEvent): void => {
    const { canvas, layer } = this.options;
    const interaction = this.interaction;
    if (!interaction) {
      const selected = this.options.getSelectedHandle();
      canvas.style.cursor = layer.pickRestoreGhost(event, selected)
        ? 'pointer'
        : layer.pickHandle(event, this.options.getSession()?.edit_handles ?? [], selected)
          ? 'grab'
          : 'default';
      return;
    }
    if (event.pointerId !== interaction.pointerId) return;
    if (interaction.kind === 'restore') {
      this.setState(pointerDistance(interaction, event) >= DRAG_START_THRESHOLD_PX ? 'restore-cancelled' : 'restore-armed');
      return;
    }
    if (!interaction.dragging && pointerDistance(interaction, event) < DRAG_START_THRESHOLD_PX) return;

    interaction.dragging = true;
    canvas.style.cursor = 'grabbing';
    this.setState('dragging');
    const position = new THREE.Vector3();
    if (!layer.intersectPointerPlane(event, interaction.plane, position)) return;
    interaction.preview = position.add(interaction.offset);
    layer.previewPosition(interaction.handle, interaction.preview);
    this.options.updatePositionOffset(interaction.handle, interaction.preview);
    this.setState('preview');
  };

  private readonly onPointerUp = async (event: PointerEvent): Promise<void> => {
    const interaction = this.interaction;
    if (!interaction || event.pointerId !== interaction.pointerId) return;
    this.interaction = null;
    this.options.controls.enabled = true;
    this.options.canvas.style.cursor = 'default';
    this.releasePointer(event.pointerId);

    if (interaction.kind === 'restore') {
      if (pointerDistance(interaction, event) >= DRAG_START_THRESHOLD_PX) {
        this.setState('restore-cancelled');
        return;
      }
      this.setState('restoring');
      this.setState(await this.options.restoreHandle(interaction.handle) ? 'restored' : 'error');
      return;
    }

    if (!interaction.dragging || !interaction.preview) {
      this.options.layer.restorePosition(interaction.handle);
      this.options.updatePositionOffset(interaction.handle);
      this.setState('selected');
      return;
    }
    const requested = interaction.preview.clone();
    if (requested.distanceTo(new THREE.Vector3(...interaction.handle.world_position)) < MIN_EDIT_DISTANCE_M) {
      this.options.layer.restorePosition(interaction.handle);
      this.options.updatePositionOffset(interaction.handle);
      this.setState('no-op');
      return;
    }

    this.setState('submitting');
    const moved = await this.options.moveHandle(interaction.handle, requested);
    this.setState(moved ? 'moved' : 'error');
    if (!moved) {
      this.options.layer.restorePosition(interaction.handle);
      this.options.updatePositionOffset(interaction.handle);
      this.options.rebuildHandles();
    }
  };

  private setState(state: string): void {
    this.options.canvas.dataset.dragState = state;
  }

  private capturePointer(pointerId: number): void {
    try {
      this.options.canvas.setPointerCapture(pointerId);
    } catch {
      // Synthetic and non-primary pointers may not support capture.
    }
  }

  private releasePointer(pointerId: number): void {
    try {
      if (this.options.canvas.hasPointerCapture(pointerId)) this.options.canvas.releasePointerCapture(pointerId);
    } catch {
      // Synthetic pointers may not support capture.
    }
  }
}
