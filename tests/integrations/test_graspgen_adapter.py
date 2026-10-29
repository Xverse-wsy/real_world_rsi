"""Coordinate and protocol checks; no model weights or robot required."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np

PATH = Path(__file__).resolve().parents[2] / "capx/integrations/vision/graspgen.py"
spec = importlib.util.spec_from_file_location("graspgen_adapter", PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class GraspGenAdapterTests(unittest.TestCase):
    def test_rotated_tcp_roundtrip_matches_goto_pose(self):
        # Include tilted grasps: a world-Z offset would pass top-down-only tests.
        rng = np.random.default_rng(8)
        poses = np.repeat(np.eye(4)[None], 30, axis=0)
        quarter_turn = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        for pose in poses:
            q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
            q[:, 0] *= np.linalg.det(q)
            pose[:3, :3] = q
            pose[:3, 3] = rng.normal(size=3)
        original = poses.copy()
        tcp = adapter.panda_base_to_tcp(poses)
        hand_rotation = tcp[:, :3, :3] @ quarter_turn
        recovered_origin = tcp[:, :3, 3] + hand_rotation @ np.array([0., 0., -.097])
        np.testing.assert_allclose(recovered_origin, original[:, :3, 3], atol=1e-12)
        np.testing.assert_array_equal(poses, original)
        # Panda-hand Y (jaw axis) must be parallel to GraspGen X.
        np.testing.assert_allclose(hand_rotation[:, :, 1], -poses[:, :3, 0], atol=1e-12)

    def test_unknown_service_convention_is_rejected(self):
        response = Mock()
        response.json.return_value = {"pose_frame": "unknown"}
        with patch.object(adapter.requests, "post", return_value=response):
            with self.assertRaisesRegex(ValueError, "convention"):
                adapter.init_graspgen_point_clouds()(np.zeros((40, 3)), np.zeros((40, 3)))

    def test_client_preserves_candidate_scores_and_decodes_tcp(self):
        poses = np.repeat(np.eye(4)[None], 2, axis=0)
        poses[:, :3, 3] = [[.4, 0., .1], [.5, .2, .3]]
        response = Mock()
        response.json.return_value = {
            "pose_frame": "graspgen_panda_base",
            "grasps_base64": adapter.encode_array(poses),
            "scores_base64": adapter.encode_array(np.array([.8, .7])),
        }
        with patch.object(adapter.requests, "post", return_value=response):
            tcp, scores, _ = adapter.init_graspgen_point_clouds()(np.zeros((40, 3)), np.zeros((40, 3)))
        np.testing.assert_allclose(tcp[:, :3, 3], poses[:, :3, 3] + [0., 0., .097])
        np.testing.assert_allclose(scores, [.8, .7])


if __name__ == "__main__":
    unittest.main()
