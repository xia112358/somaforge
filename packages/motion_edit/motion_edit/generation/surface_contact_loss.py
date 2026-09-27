"""Optional surface-local contact optimization; never a contact truth classifier.

Tangential contact coordinates are the current FK point's surface coordinates,
so optimizing q optimizes landing positions without post-projecting the pose.
"""
import numpy as np


def contact_previous_slots(spec, compiled):
    """Match consecutive observations by body/shape/face, never packed slot ID.

    Nearest local-point assignment only tracks manifold points within an already
    verified contact pair; it does not classify contact or bridge inactive gaps.
    """
    from scipy.optimize import linear_sum_assignment
    rows = [[] for _ in range(spec.frame_count)]
    for contact in spec.contacts:
        key = (contact.body_label, tuple(sorted(set(contact.shape_labels))), contact.metadata['target_surface_id'])
        for frame in np.asarray(contact.frames)-spec.frame_start:
            rows[int(frame)].extend([key]*len(contact.points_local))
    previous = np.full(compiled.contact_weights.shape, -1, dtype=int)
    for frame in range(1, spec.frame_count):
        for key in set(rows[frame]) & set(rows[frame-1]):
            current = [i for i,k in enumerate(rows[frame]) if k == key]
            old = [i for i,k in enumerate(rows[frame-1]) if k == key]
            distances = np.linalg.norm(compiled.contact_points_local[frame,current,None,:]
                - compiled.contact_points_local[frame-1,old][None,:,:], axis=-1)
            a,b = linear_sum_assignment(distances)
            previous[frame,np.asarray(current)[a]] = np.asarray(old)[b]
    return previous


def contact_temporal_residual(correction, previous, previous_previous, velocity_mask, acceleration_mask, *, xp=np):
    """Extend the existing root correction velocity/acceleration penalties.

    Corrections are relative to the demonstration, preserving its rolling or
    sliding motion rather than forcing all observed contact points stationary.
    """
    return xp.concatenate((((correction-previous)*velocity_mask[:,None]*xp.sqrt(100.)).reshape(-1),
        ((correction-2*previous+previous_previous)*acceleration_mask[:,None]*xp.sqrt(400.)).reshape(-1)))


def convex_targets(logits, vertices, valid, *, xp=np):
    """Softmax barycentric coordinates; padding never participates."""
    full = xp.concatenate((logits, xp.zeros((*logits.shape[:-1], 1))), axis=-1)
    full = xp.where(valid, full, -1.e30)
    weights = xp.exp(full-xp.max(full, axis=-1, keepdims=True))*valid
    weights = weights/xp.sum(weights, axis=-1, keepdims=True)
    return xp.sum(weights[..., None]*vertices, axis=-2), weights


def bounded_face_targets(coordinates, vertices, valid, *, xp=np):
    """Two bounded coordinates, no redundant softmax or saturated logits.

    Ordered convex quadrilateral: bilinear vertex weights. Triangle: square-to-
    simplex weights. Both remain convex for coordinates in [0,1].
    """
    u,v=coordinates[...,0],coordinates[...,1]
    triangle=xp.sum(valid,axis=-1)==3
    quad=xp.stack(((1-u)*(1-v),u*(1-v),u*v,(1-u)*v),axis=-1)
    tri=xp.stack((1-u,u*(1-v),u*v,xp.zeros_like(u)),axis=-1)
    weights=xp.where(triangle[...,None],tri,quad)
    weights=xp.where((xp.sum(valid,axis=-1)>1)[...,None],weights,
        xp.stack((xp.ones_like(u),xp.zeros_like(u),xp.zeros_like(u),xp.zeros_like(u)),axis=-1))
    return xp.sum(weights[...,None]*vertices,axis=-2),weights


def compile_bounded_face_targets(spec,compiled):
    from scipy.optimize import least_squares
    vertices,valid,finite,_=compile_convex_targets(spec,compiled)
    if vertices.shape[-2]>4:
        raise ValueError('Bounded contact chart requires triangular/quadrilateral actual faces; triangulate explicitly first')
    if vertices.shape[-2]<4:
        vertices=np.pad(vertices,((0,0),(0,0),(0,4-vertices.shape[-2]),(0,0)))
        valid=np.pad(valid,((0,0),(0,0),(0,4-valid.shape[-1])))
    initial=np.full((*finite.shape,2),.5)
    for frame,slot in np.argwhere(finite):
        p=vertices[frame,slot]; mask=valid[frame,slot]; reference=compiled.contact_targets_w[frame,slot]
        result=least_squares(lambda uv:bounded_face_targets(uv,p,mask)[0]-reference,
            [.5,.5],bounds=([0.,0.],[1.,1.]),max_nfev=40)
        if not result.success:raise ValueError('Failed to initialize a face target coordinate')
        initial[frame,slot]=result.x
    return vertices,valid,finite,initial


def compile_convex_targets(spec, compiled):
    """Build target domains, and initialize coefficients near the weak reference."""
    from scipy.optimize import nnls
    rows = [[] for _ in range(spec.frame_count)]
    for contact in spec.contacts:
        geometry = contact.metadata['target_surface_geometry']
        face_edges(geometry)  # validate the actual convex face, not its bounding box
        polygon = geometry.get('polygon_world')
        for frame in np.asarray(contact.frames)-spec.frame_start:
            rows[int(frame)].extend([polygon]*len(contact.points_local))
    width=max(3,max((len(p) for row in rows for p in row if p is not None),default=3))
    shape=compiled.contact_weights.shape
    vertices=np.zeros((*shape,width,3)); valid=np.zeros((*shape,width),bool)
    valid[...,0]=True
    finite=np.zeros(shape,bool); logits=np.zeros((*shape,width-1))
    for frame,row in enumerate(rows):
        for slot,polygon in enumerate(row):
            if polygon is None:continue
            p=np.asarray(polygon,float); count=len(p)
            vertices[frame,slot,:count]=p;valid[frame,slot,:count]=True;finite[frame,slot]=True
            # Initialization of target coordinates only; robot q is never projected.
            center=p.mean(axis=0); scale=max(np.linalg.norm(p-center,axis=-1).max(),1.e-6)
            matrix=np.vstack(((p-center).T/scale,np.ones(count)))
            target=np.r_[(compiled.contact_targets_w[frame,slot]-center)/scale,1.]
            weights=nnls(matrix,target)[0]
            weights=np.maximum(weights,1.e-3);weights/=weights.sum()
            full=np.zeros(width);full[:count]=np.log(weights)
            full-=full[count-1]
            logits[frame,slot]=np.clip(full[:-1],-19.,19.)
    return vertices,valid,finite,logits


def face_edges(surface):
    normal = np.asarray(surface['normal'], dtype=float)
    if normal.shape != (3,) or not np.isfinite(normal).all() or not np.isclose(np.linalg.norm(normal), 1.):
        raise ValueError('Surface needs a finite unit normal')
    polygon = surface.get('polygon_world')
    if polygon is None:
        if surface['surface_type'] != 'plane':
            raise ValueError('Finite contact face requires its actual polygon')
        return normal, np.zeros((0, 3)), np.zeros(0)
    p = np.asarray(polygon, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError('Invalid face polygon')
    if np.max(np.abs((p-p[0])@normal)) > 1.e-6:
        raise ValueError('Non-planar face polygon')
    edges = np.roll(p, -1, axis=0)-p
    lengths = np.linalg.norm(edges, axis=-1)
    if np.any(lengths < 1.e-12):
        raise ValueError('Degenerate polygon edge')
    outward = np.cross(edges, normal)/lengths[:, None]
    if np.mean(np.sum((p.mean(axis=0)-p)*outward, axis=-1)) > 0:
        outward = -outward
    offsets = np.sum(outward*p, axis=-1)
    if np.max(p@outward.T-offsets) > 1.e-6:
        raise ValueError('Contact loss requires a convex actual face; no bounding-box fallback')
    return normal, outward, offsets


def compile_surface_faces(spec, compiled, link_names):
    from .pyroki_taskspace import resolve_link_index
    rows = [[] for _ in range(spec.frame_count)]
    for contact in spec.contacts:
        link = resolve_link_index(link_names, contact.body_label, (contact.body_label,))
        if link is None:
            raise ValueError('Free contact has unresolved robot link')
        face = face_edges(contact.metadata['target_surface_geometry'])
        for frame in np.asarray(contact.frames)-spec.frame_start:
            rows[int(frame)].extend([(link, face)]*len(contact.points_local))
    max_edges = max(1, max((len(face[1]) for row in rows for _, face in row), default=0))
    shape = compiled.contact_weights.shape
    normals = np.zeros((*shape, 3)); edges = np.zeros((*shape, max_edges, 3)); offsets = np.zeros((*shape, max_edges))
    for frame, row in enumerate(rows):
        if len(row) != np.count_nonzero(compiled.contact_weights[frame]):
            raise ValueError('Surface/compiled contact slot mismatch')
        for slot, (link, (normal, edge, offset)) in enumerate(row):
            if compiled.contact_link_indices[frame, slot] != link:
                raise ValueError('Surface/robot contact slot mismatch')
            normals[frame, slot] = normal
            edges[frame, slot, :len(edge)] = edge
            offsets[frame, slot, :len(edge)] = offset
    return normals, edges, offsets


def surface_residual(points, references, normals, edges, offsets, sqrt_weight, reference_ratio, *, xp=np):
    error = points-references
    signed = xp.sum(error*normals, axis=-1)
    tangent = error-signed[:, None]*normals
    outside = xp.maximum(xp.sum(points[:, None, :]*edges, axis=-1)-offsets, 0.)
    return xp.concatenate(((signed*sqrt_weight).reshape(-1),
        (tangent*sqrt_weight[:, None]*xp.sqrt(reference_ratio)).reshape(-1),
        (outside*sqrt_weight[:, None]).reshape(-1)))


def endpoint_surface_residual(points, references, normals, edges, offsets,
                              sqrt_weight, support_weight, reference_ratio, *, xp=np):
    """One normal and one tangent task per sample, plus finite-face containment.

    During support the stronger episode task replaces, rather than adds to,
    the weak surface reference. This is an optimization residual, not contact
    activation. Reference clearance and source material motion are preserved.
    """
    supported = support_weight > 0
    normal_weight = xp.where(supported, support_weight, sqrt_weight)
    tangent_weight = xp.where(supported, support_weight,
                              sqrt_weight * xp.sqrt(reference_ratio))
    error = points - references
    signed = xp.sum(error * normals, axis=-1)
    tangent = error - signed[:, None] * normals
    outside = xp.maximum(xp.sum(points[:, None, :] * edges, axis=-1) - offsets, 0.)
    return xp.concatenate(((signed * normal_weight).reshape(-1),
                           (tangent * tangent_weight[:, None]).reshape(-1),
                           (outside * sqrt_weight[:, None]).reshape(-1)))
