export type Vec3 = [number, number, number];

export type AssetItem = {
  motion_asset_id: string;
  motion_id: string;
  source: string;
  has_force: boolean;
  has_terrain: boolean;
};

export type RecentMotion = {
  key: string;
  label: string;
  motion_id: string;
  motion_asset_id: string;
  motion_version_id: string | null;
  kind: 'source' | 'generated';
  active: boolean;
  last_opened_at: string | null;
};

export type Anchor = {
  anchor_id: string;
  body: string;
  start_frame: number;
  end_frame: number;
  world_position: Vec3 | null;
  surface_id: string | null;
  object_id: string | null;
  surface_coordinates: { u: number; v: number } | null;
  metadata: Record<string, unknown>;
  surface_origin: Vec3 | null;
  surface_normal: Vec3 | null;
  surface_tangent_u: Vec3 | null;
  surface_tangent_v: Vec3 | null;
};

export type EditHandle = {
  handle_id: string;
  motion_id: string;
  body: string;
  start_frame: number;
  end_frame: number;
  member_anchor_ids: string[];
  world_position: Vec3;
  surface_id: string;
  object_id: string | null;
  surface_coordinates: { u: number; v: number };
  surface_origin: Vec3;
  surface_normal: Vec3;
  surface_tangent_u: Vec3;
  surface_tangent_v: Vec3;
  surface_bounds: { u: [number, number]; v: [number, number] } | null;
  initial_world_position: Vec3;
  position_offset: { u: number; v: number };
  has_position_offset: boolean;
  metadata: Record<string, unknown>;
};

export type Surface = {
  surface_id: string;
  origin: Vec3;
  normal: Vec3;
  tangent_u: Vec3;
  tangent_v: Vec3;
  bounds: { u: [number, number]; v: [number, number] };
  metadata: Record<string, unknown>;
};

export type Generation = {
  status: 'idle' | 'running' | 'succeeded' | 'failed';
  stage: string | null;
  output_motion_path: string | null;
  output_motion_version_id: string | null;
  warnings: string[];
  error: string | null;
  started_at: number | null;
  finished_at: number | null;
};

export type Session = {
  motion_asset_id: string;
  motion_version_id: string | null;
  motion_key: string;
  motion_id: string;
  fps: number;
  qpos: number[][];
  joint_names: string[];
  robot_urdf_url: string;
  terrain_obj_url: string | null;
  graph: {
    anchors: Anchor[];
    transitions: Array<{ start_frame: number; end_frame: number; metadata: Record<string, unknown> }>;
  };
  edit_handles: EditHandle[];
  surfaces: Surface[];
  contact_force: {
    part_order: string[];
    forces: Vec3[][];
    masks: boolean[][];
    positions: Vec3[][];
    position_valid: boolean[][];
    sample_points: Vec3[][];
    sample_forces: Vec3[][];
  };
  pending_edit_count: number;
  can_undo: boolean;
  can_redo: boolean;
  settings: {
    edit_plan_path: string;
    output_contact_layer: string;
    source_contact_layer: string;
    output_motion_path: string;
    output_segment_layer: string;
    output_motion_version_id: string;
    register_motion_version: boolean;
    overwrite: boolean;
  };
  plan: { path: string; status: string; edit_count: number } | null;
  generation: Generation;
};
