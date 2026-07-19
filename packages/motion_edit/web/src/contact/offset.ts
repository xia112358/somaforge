import * as THREE from 'three';
import type { EditHandle } from '../core/types';

export const POSITION_OFFSET_EPSILON_M = 1e-6;

export function contactPositionOffset(handle: EditHandle, position?: THREE.Vector3): { u: number; v: number } {
  const delta = (position?.clone() ?? new THREE.Vector3(...handle.world_position))
    .sub(new THREE.Vector3(...handle.initial_world_position));
  return {
    u: delta.dot(new THREE.Vector3(...handle.surface_tangent_u)),
    v: delta.dot(new THREE.Vector3(...handle.surface_tangent_v)),
  };
}

export function formatPositionOffset(value: number): string {
  const normalized = Math.abs(value) < 5e-7 ? 0 : value;
  return `${normalized >= 0 ? '+' : ''}${normalized.toFixed(3)} m`;
}
