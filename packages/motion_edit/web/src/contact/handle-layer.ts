import * as THREE from 'three';
import type { EditHandle } from '../core/types';

const HANDLE_LIFT_M = 0.008;
const RESTORE_GHOST_LIFT_M = 0.006;
const HANDLE_SCREEN_PICK_PX = 14;
const RESTORE_SCREEN_PICK_PX = 10;

type RebuildOptions = {
  handles: EditHandle[];
  visibleHandleIds: Set<string>;
  selectedHandle: EditHandle | null;
  radius: number;
};

export class ContactHandleLayer {
  readonly handles = new THREE.Group();
  readonly restoreGhosts = new THREE.Group();

  private readonly handleObjects = new Map<string, THREE.Group>();
  private readonly restoreGhostObjects = new Map<string, THREE.Group>();
  private readonly handleHitMeshes: THREE.Mesh[] = [];
  private readonly restoreGhostHitMeshes: THREE.Mesh[] = [];
  private readonly pointer = new THREE.Vector2();
  private readonly raycaster = new THREE.Raycaster();

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly camera: THREE.Camera,
  ) {}

  clear(): void {
    this.handles.clear();
    this.restoreGhosts.clear();
    this.handleObjects.clear();
    this.restoreGhostObjects.clear();
    this.handleHitMeshes.length = 0;
    this.restoreGhostHitMeshes.length = 0;
    this.canvas.dataset.restoreGhostCount = '0';
  }

  setVisible(visible: boolean): void {
    this.handles.visible = visible;
    this.restoreGhosts.visible = visible;
  }

  rebuild({ handles, visibleHandleIds, selectedHandle, radius }: RebuildOptions): void {
    this.clear();
    this.canvas.dataset.contactMarker = 'episode-handle';

    for (const handle of handles) {
      if (!visibleHandleIds.has(handle.handle_id) && handle.handle_id !== selectedHandle?.handle_id) continue;
      const selected = handle.handle_id === selectedHandle?.handle_id;
      const normal = new THREE.Vector3(...handle.surface_normal).normalize();
      const tangentU = new THREE.Vector3(...handle.surface_tangent_u).normalize();
      const tangentV = new THREE.Vector3(...handle.surface_tangent_v).normalize();
      const group = new THREE.Group();
      group.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(tangentU, tangentV, normal));
      group.position.set(...handle.world_position).addScaledVector(normal, HANDLE_LIFT_M);

      const status = String(handle.metadata.surface_editor_status || 'bound');
      const color = selected ? 0xffdd72 : status === 'edited' ? 0x63d69c : 0xe6edf3;
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(radius * 0.48, radius, 32),
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: selected ? 1 : 0.82,
          side: THREE.DoubleSide,
          depthTest: false,
          depthWrite: false,
        }),
      );
      ring.renderOrder = 8;
      group.add(ring);

      const center = new THREE.Mesh(
        new THREE.CircleGeometry(radius * 0.25, 24),
        new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, depthTest: false, depthWrite: false }),
      );
      center.position.z = 0.001;
      center.renderOrder = 9;
      group.add(center);

      const hit = new THREE.Mesh(
        new THREE.SphereGeometry(radius * 0.82, 16, 10),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
      );
      hit.userData.handle = handle;
      group.add(hit);
      this.handleHitMeshes.push(hit);

      if (selected) this.addSelectionAxes(group, radius);
      this.handles.add(group);
      this.handleObjects.set(handle.handle_id, group);
      if (handle.has_position_offset) this.addRestoreGhost(handle, group, normal, radius);
    }

    this.canvas.dataset.restoreGhostCount = String(this.restoreGhostObjects.size);
  }

  pickRestoreGhost(event: PointerEvent, selectedHandle: EditHandle | null): EditHandle | null {
    this.setPointerRay(event);
    const hit = this.raycaster.intersectObjects(this.restoreGhostHitMeshes, false)[0];
    if (hit) return hit.object.userData.restoreHandle as EditHandle;
    if (!selectedHandle?.has_position_offset) return null;

    const rect = this.canvas.getBoundingClientRect();
    const ghostX = Number(this.canvas.dataset.selectedRestoreGhostX) * rect.width;
    const ghostY = Number(this.canvas.dataset.selectedRestoreGhostY) * rect.height;
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    return Number.isFinite(ghostX)
      && Number.isFinite(ghostY)
      && Math.hypot(ghostX - localX, ghostY - localY) <= RESTORE_SCREEN_PICK_PX
      ? selectedHandle
      : null;
  }

  pickHandle(event: PointerEvent, handles: EditHandle[], selectedHandle: EditHandle | null): EditHandle | null {
    this.setPointerRay(event);
    const rect = this.canvas.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    const rayHits = this.raycaster.intersectObjects(this.handleHitMeshes, false);
    const selectedRayHit = rayHits.find(
      hit => (hit.object.userData.handle as EditHandle).handle_id === selectedHandle?.handle_id,
    );
    if (selectedRayHit) return selectedRayHit.object.userData.handle as EditHandle;

    if (selectedHandle) {
      const selectedX = Number(this.canvas.dataset.selectedHandleX) * rect.width;
      const selectedY = Number(this.canvas.dataset.selectedHandleY) * rect.height;
      if (
        Number.isFinite(selectedX)
        && Number.isFinite(selectedY)
        && Math.hypot(selectedX - localX, selectedY - localY) <= HANDLE_SCREEN_PICK_PX
      ) return selectedHandle;
    }
    if (rayHits[0]) return rayHits[0].object.userData.handle as EditHandle;

    let nearest: EditHandle | null = null;
    let nearestDistance = HANDLE_SCREEN_PICK_PX;
    for (const handle of handles) {
      const group = this.handleObjects.get(handle.handle_id);
      if (!group) continue;
      const projected = group.getWorldPosition(new THREE.Vector3()).project(this.camera);
      if (projected.z < -1 || projected.z > 1) continue;
      const x = (projected.x + 1) * 0.5 * rect.width;
      const y = (1 - projected.y) * 0.5 * rect.height;
      const distance = Math.hypot(x - localX, y - localY);
      if (distance <= nearestDistance) {
        nearest = handle;
        nearestDistance = distance;
      }
    }
    return nearest;
  }

  intersectPointerPlane(event: PointerEvent, plane: THREE.Plane, target: THREE.Vector3): boolean {
    this.setPointerRay(event);
    return this.raycaster.ray.intersectPlane(plane, target) !== null;
  }

  previewPosition(handle: EditHandle, position: THREE.Vector3): void {
    const group = this.handleObjects.get(handle.handle_id);
    if (!group) return;
    group.position.copy(position).addScaledVector(new THREE.Vector3(...handle.surface_normal), HANDLE_LIFT_M);
  }

  restorePosition(handle: EditHandle): void {
    this.previewPosition(handle, new THREE.Vector3(...handle.world_position));
  }

  updateProjection(selectedHandle: EditHandle | null): void {
    const group = selectedHandle ? this.handleObjects.get(selectedHandle.handle_id) : null;
    const ghost = selectedHandle ? this.restoreGhostObjects.get(selectedHandle.handle_id) : null;
    if (ghost) {
      const projected = ghost.getWorldPosition(new THREE.Vector3()).project(this.camera);
      this.canvas.dataset.selectedRestoreGhostX = String((projected.x + 1) / 2);
      this.canvas.dataset.selectedRestoreGhostY = String((1 - projected.y) / 2);
    } else {
      delete this.canvas.dataset.selectedRestoreGhostX;
      delete this.canvas.dataset.selectedRestoreGhostY;
    }
    if (!group) {
      delete this.canvas.dataset.selectedHandleX;
      delete this.canvas.dataset.selectedHandleY;
      delete this.canvas.dataset.selectedHandleId;
      return;
    }
    const projected = group.getWorldPosition(new THREE.Vector3()).project(this.camera);
    this.canvas.dataset.selectedHandleX = String((projected.x + 1) / 2);
    this.canvas.dataset.selectedHandleY = String((1 - projected.y) / 2);
    this.canvas.dataset.selectedHandleId = selectedHandle!.handle_id;
  }

  private setPointerRay(event: PointerEvent): void {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
  }

  private addSelectionAxes(group: THREE.Group, radius: number): void {
    const length = radius * 1.85;
    const arrowU = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), length, 0xf06449, radius * 0.42, radius * 0.22);
    const arrowV = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(), length, 0x68d391, radius * 0.42, radius * 0.22);
    for (const mesh of [arrowU.line, arrowU.cone, arrowV.line, arrowV.cone]) {
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      materials.forEach(material => {
        material.depthTest = false;
        material.depthWrite = false;
      });
    }
    group.add(arrowU, arrowV);
  }

  private addRestoreGhost(handle: EditHandle, source: THREE.Group, normal: THREE.Vector3, radius: number): void {
    const ghost = new THREE.Group();
    ghost.quaternion.copy(source.quaternion);
    ghost.position.set(...handle.initial_world_position).addScaledVector(normal, RESTORE_GHOST_LIFT_M);
    const materialOptions = {
      color: 0x9aabb9,
      transparent: true,
      side: THREE.DoubleSide,
      depthTest: false,
      depthWrite: false,
    };
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(radius * 0.5, radius * 0.92, 32),
      new THREE.MeshBasicMaterial({ ...materialOptions, opacity: 0.24 }),
    );
    ring.renderOrder = 7;
    ghost.add(ring);
    const center = new THREE.Mesh(
      new THREE.CircleGeometry(radius * 0.16, 20),
      new THREE.MeshBasicMaterial({ ...materialOptions, opacity: 0.2 }),
    );
    center.position.z = 0.001;
    center.renderOrder = 7;
    ghost.add(center);
    const hit = new THREE.Mesh(
      new THREE.SphereGeometry(radius * 0.78, 14, 8),
      new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
    );
    hit.userData.restoreHandle = handle;
    ghost.add(hit);
    this.restoreGhostHitMeshes.push(hit);
    this.restoreGhosts.add(ghost);
    this.restoreGhostObjects.set(handle.handle_id, ghost);
  }
}
