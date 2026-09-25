import torch

from climb00_pipeline.next_interaction import structural_pose_loss
from climb00_pipeline.neural_infiller import CanonicalG1ForwardKinematics, _matrix_from_rotation6d


def supervision(fk, q):
    position, rotation6d = fk(q[:, None])
    return position[:, 0], _matrix_from_rotation6d(rotation6d[:, 0]), {
        'q': q.clone(),
        'body_position': position[:, 0].clone(),
    }


def test_structural_pose_is_zero_at_demonstrated_pose():
    fk = CanonicalG1ForwardKinematics()
    q = torch.zeros(1, 36); q[:, 2] = .8; q[:, 3] = 1
    position, rotation, target = supervision(fk, q)
    loss, metrics = structural_pose_loss(type('Model', (), {'fk': fk})(), q, position, rotation, target)
    torch.testing.assert_close(loss, torch.zeros_like(loss))
    assert all(float(value.max()) == 0 for value in metrics.values())


def test_one_bad_joint_is_not_diluted_by_joint_count():
    fk = CanonicalG1ForwardKinematics()
    target_q = torch.zeros(1, 36); target_q[:, 2] = .8; target_q[:, 3] = 1
    _, _, target = supervision(fk, target_q)
    predicted_q = target_q.clone(); predicted_q[:, 10] = 1.0
    position6d, rotation6d = fk(predicted_q[:, None])
    position = position6d[:, 0]; rotation = _matrix_from_rotation6d(rotation6d[:, 0])
    loss, metrics = structural_pose_loss(type('Model', (), {'fk': fk})(), predicted_q, position, rotation, target)
    # The explicit worst-joint component alone is (1 / 0.5)^2 == 4.
    assert float(loss) >= 4.0
    torch.testing.assert_close(metrics['joint_error_max_rad'], torch.ones(1))
