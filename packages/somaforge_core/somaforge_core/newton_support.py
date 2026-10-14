"""Force-bearing support motion from one MJWarp constraint evaluation.

Contact activation is supplied separately. A positive normal force localizes
load within already verified contacts; it never invents contact truth. Body
net forces or zero-filled Newton raw forces cannot replace per-constraint force.
"""
import numpy as np

SUPPORT_SCHEMA = 'newton_mjwarp_force_bearing_point_motion_v3'
SUPPORT_FIELDS = ('force_on_body1_w', 'torque_on_body1_w', 'point_velocity0_w', 'point_velocity1_w',
                  'pre_point_velocity0_w', 'pre_point_velocity1_w',
                  'application_point0_local', 'application_point1_local')


def observed_support(snapshot, binding, body_labels, num_envs):
    """Assess a complete native solve; zero load and missing evidence differ.

    This is a passive read. It does not change physics, poses, margins or policy.
    The six-part arrays retain solve sampling, not post-integration pose time.
    """
    selected = select_support_contacts(snapshot, binding, body_labels)
    measured = support_motion(snapshot, eligible=selected['eligible'],
                              robot_side=selected['robot_side'], groups=selected['groups'],
                              group_count=num_envs * 6)
    return {key: np.asarray(measured[key]).reshape(num_envs, 6) for key in
            ('contact_activated', 'load_known', 'load_bearing', 'load_state',
             'normal_force_n', 'loaded_motion_known', 'rms_tangent_speed_m_s', 'slip_state')}


def select_support_contacts(snapshot, binding, body_labels):
    """Resolve actual force application points to native primary mesh faces.

This attributes an existing active constraint, never creates contact from
distance. All faces, including sides, compete before shared face eligibility.
"""
    from .contact_schema import CONTACT_BODY_NAMES_BY_PART
    from .contact_face_selection import select_contact_pairs
    from .newton_contacts import PARTS, actual_contact_faces, constraint_decision
    n=int(snapshot['count']);body_env={int(k):v for k,v in binding['body_env'].items()}
    shape_faces={int(k):v for k,v in binding['shape_surface'].items()}
    active,allocated=constraint_decision(snapshot['dist'],snapshot['includemargin'],
        snapshot['type'],snapshot['efc_address'],n,snapshot['constraint_rows'])
    if not np.array_equal(active[:n],snapshot['active'][:n]) or not np.array_equal(allocated[:n],snapshot['constraint_allocated'][:n]):
        raise ValueError('Inconsistent saved solver activation/allocation')
    side=np.full(n,-1,int);group=np.full(n,-1,int);surface=np.full(n,-1,int);records=[]
    for i in np.flatnonzero(active[:n]):
        if not allocated[i]:raise ValueError('Unallocated active support constraint')
        bodies=[int(snapshot[f'body{k}'][i]) for k in (0,1)]
        robot=[k for k in (0,1) if bodies[k] in body_env]
        if len(robot)!=1:continue  # self and cross-robot contact are not terrain
        k=robot[0]
        if body_env[bodies[k]]!=int(snapshot['worldid'][i]):continue
        body=body_labels[bodies[k]].rsplit('/',1)[-1]
        part=next((p for p,name in enumerate(PARTS) if body in CONTACT_BODY_NAMES_BY_PART[name]),None)
        if part is None:continue
        external=int(snapshot[f'shape{1-k}'][i])
        if external not in shape_faces:raise ValueError('Unknown actual external shape')
        position=np.asarray(snapshot['position_w'][i]);normal=np.asarray(snapshot['frame_w'][i,0])*(1 if k==1 else -1)
        faces=actual_contact_faces(position,normal,shape_faces[external])
        face=faces[0];side[i]=k;group[i]=int(snapshot['worldid'][i])*6+part;surface[i]=int(face['surface'])
        records.append(dict(row=i,part=part,surface=int(face['surface']),allocated=True,
            position_w=position.tolist(),dist=float(snapshot['dist'][i]),
            includemargin=float(snapshot['includemargin'][i]),
            position_semantics='solver_force_application_point',surface_attribution='native_finite_triangle_primary_at_force_application_point'))
    selected=select_contact_pairs([records],binding['surface_catalog'])
    eligible=np.zeros(n,bool)
    eligible[[p['row'] for p in selected['contact_pairs'][0]]]=True
    return dict(eligible=eligible,robot_side=side,groups=group,surfaces=surface,
                excluded_rows=[p['row'] for p in selected['abnormal_contact_pairs'][0]])


def snapshot_support(solver, snapshot):
    """Read force and both incoming/resolved velocities at solve geometry."""
    import warp as wp
    import mujoco_warp as mjw
    m,d=solver.mjw_model,solver.mjw_data
    count=int(snapshot['count']); capacity=len(snapshot['dist'])
    result={name:np.zeros((capacity,3),np.float32) for name in SUPPORT_FIELDS}
    if count==0:return result
    # mjw.contact_force decodes the actual pyramidal/elliptic efc rows. Newton
    # raw rigid_contact_force is not populated by this constraint solver.
    device=d.contact.pos.device
    ids=wp.array(np.arange(count,dtype=np.int32),dtype=wp.int32,device=device)
    wrench=wp.zeros(count,dtype=wp.spatial_vector,device=device)
    mjw.contact_force(m,d,ids,True,wrench)
    values=wrench.numpy()
    if values.shape!=(count,6) or not np.isfinite(values).all():
        raise ValueError('Invalid MJWarp per-contact wrench')
    result['force_on_body1_w'][:count]=values[:,:3]
    result['torque_on_body1_w'][:count]=values[:,3:]
    geom=d.contact.geom.numpy()[:count]
    world=np.asarray(snapshot['worldid'][:count],int)
    geom_body=m.geom_bodyid.numpy();root=m.body_rootid.numpy()
    # cvel is rotation:translation, centered at the root subtree COM. It is
    # retained from the velocity evaluation that constructed these constraints.
    velocity=d.cvel.numpy();com=d.subtree_com.numpy()
    # Integration updates qvel after cvel was evaluated. Reconstruct the same
    # body spatial Jacobian using actual ancestry and cdof, without mutating the
    # policy's solver Data or rerunning any physics/kinematic kernel.
    cache=getattr(solver,'_somaforge_support_velocity_tree',None)
    if cache is None or cache[0]!=id(m):
        parent=m.body_parentid.numpy();dof_body=m.dof_bodyid.numpy()
        ancestry=np.zeros((len(parent),len(dof_body)),bool)
        for b in range(1,len(parent)):
            j=b;seen=set()
            while j:
                if j in seen:raise ValueError('Cyclic MJWarp body tree')
                seen.add(j);ancestry[b] |= dof_body==j;j=int(parent[j])
        cache=(id(m),ancestry);solver._somaforge_support_velocity_tree=cache
    resolved=np.einsum('bv,wv,wvj->wbj',cache[1],d.qvel.numpy(),d.cdof.numpy(),optimize=True)
    point=np.asarray(snapshot['position_w'][:count])
    # MuJoCo body frames are copied directly into Newton body_q by the solver's
    # convert_body_xforms_to_warp_kernel. Read the retained solve transform,
    # not the post-integration state used by the trajectory recorder.
    body_position=d.xpos.numpy();body_rotation=d.xmat.numpy().reshape(*body_position.shape[:2],3,3)
    body_mapping=solver.mjc_body_to_newton.numpy()
    for side in (0,1):
        body=geom_body[geom[:,side]]
        if not np.array_equal(body_mapping[world,body],snapshot[f'body{side}'][:count]):
            raise ValueError('Support point body frame mapping differs from Newton shape body')
        result[f'application_point{side}_local'][:count]=np.einsum(
            'nji,nj->ni',body_rotation[world,body],point-body_position[world,body])
        spatial=velocity[world,body]
        origin=com[world,root[body]]
        result[f'pre_point_velocity{side}_w'][:count]=spatial[:,3:]+np.cross(spatial[:,:3],point-origin)
        spatial=resolved[world,body]
        result[f'point_velocity{side}_w'][:count]=spatial[:,3:]+np.cross(spatial[:,:3],point-origin)
    return result


def support_motion(snapshot, *, eligible, robot_side, groups, group_count):
    """Force-weighted RMS slip speed at actual force application points.

eligible must already verify activation, allocation and task primary faces.
RMS of local velocities is intentional: motion at different loaded points must
not cancel at a fictitious center of pressure. Zero load is known unloaded;
motion of loaded points is then unknown, never an automatic static certificate.
"""
    count=int(snapshot['count']);eligible=np.asarray(eligible,bool)
    side=np.asarray(robot_side,int);groups=np.asarray(groups,int)
    if any(x.shape!=(count,) for x in (eligible,side,groups)):
        raise ValueError('Support mapping dimensions differ from contact count')
    if np.any(eligible & ~np.isin(side,[0,1])) or np.any(eligible & ((groups<0)|(groups>=group_count))):
        raise ValueError('Invalid robot side/support group')
    if not all(key in snapshot for key in SUPPORT_FIELDS):
        raise ValueError('Missing per-constraint support force/velocity; support location unknown')
    normal=np.asarray(snapshot['frame_w'][:count,0],float)
    force=np.asarray(snapshot['force_on_body1_w'][:count],float)
    relative=np.asarray(snapshot['point_velocity1_w'][:count],float)-np.asarray(snapshot['point_velocity0_w'][:count],float)
    if not np.isfinite(np.concatenate((normal,force,relative))).all():
        raise ValueError('Nonfinite solver support fields')
    if not np.allclose(np.linalg.norm(normal[eligible],axis=-1),1.,atol=1.e-6):
        raise ValueError('Invalid constraint normals')
    if np.any(eligible & (~np.asarray(snapshot['active'][:count],bool) |
                          ~np.asarray(snapshot['constraint_allocated'][:count],bool))):
        raise ValueError('Support includes inactive or unallocated constraint')
    load=np.maximum(np.einsum('ij,ij->i',force,normal),0.)
    tangent=relative-np.einsum('ij,ij->i',relative,normal)[:,None]*normal
    speed=np.linalg.norm(tangent,axis=-1)
    select=eligible & (load>0)
    from .contact_motion import loaded_motion_statistics
    statistics=loaded_motion_statistics(speed[select],load[select],groups[select],group_count)
    from .support_semantics import assess_support
    contact=np.zeros(group_count,bool)
    contact[groups[eligible]]=True
    assessment=assess_support(contact,statistics['normal_force_n'],statistics['rms_tangent_speed_m_s'],
                              load_known=np.ones(group_count,bool))
    return dict(schema=SUPPORT_SCHEMA,**statistics,
                assessment_schema=assessment['schema'],contact_activated=assessment['contact_activated'],
                load_known=assessment['load_known'],load_state=assessment['load_state'],slip_state=assessment['slip_state'],
                loaded_contact_rows=np.flatnonzero(select),point_tangent_speed_m_s=speed[select],
                point_normal_force_n=load[select],point_positions_w=np.asarray(snapshot['position_w'][:count])[select])
