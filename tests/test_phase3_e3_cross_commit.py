"""Regression cases for borrowing continuous rollout outcomes across planner revisions."""
import numpy as np
import pytest
from scipy.sparse import csr_matrix

from learned_portal_phase3.e3_policy_comparison import INPUTS, METHODS, compare_event, index_events, require_inputs


def test_borrowing_uses_row_l1_and_the_actual_old_policy():
    old = csr_matrix([[0.25, 0.25, 0.25, 0.25]])
    new = csr_matrix([[0.25 + 4e-13, 0.25 - 4e-13, 0.25 + 4e-13, 0.25 - 4e-13]])
    identity = dict(start_landmark=2, goal_landmark_count=2, goal_sha256="mask", goal_center=[1., 2.],
                    policy_present=True, fallback_used=False, fallback_method=None)
    result = compare_event(identity, identity, old, new)
    assert result["max_abs_entry_diff"] < 1e-12 < result["matrix_infinity_norm_diff"]
    assert not result["equivalent"]
    missing = compare_event(None, identity, None, new)
    assert not missing["equivalent"] and missing["max_abs_entry_diff"] is None
    assert compare_event(identity, identity, old, old)["equivalent"]
    for changed in (dict(start_landmark=1), dict(goal_center=[0.,2.]), dict(goal_sha256="other"),
                    dict(fallback_used=True), dict(policy_present=False)):
        assert not compare_event(identity, {**identity, **changed}, old, old)["equivalent"]
    with pytest.raises(ValueError, match="non-finite"):
        compare_event(identity, identity, old, csr_matrix([[np.nan,0.,0.,0.]]))


def test_short_or_duplicate_event_roster_is_not_a_completed_seed():
    rows = [dict(task_index=i, method_id=m) for i in range(12) for m in METHODS]
    assert len(index_events(rows, 6000)) == 84
    for invalid in (rows[:-1], rows[:-1]+[rows[0]], rows+[rows[0]]):
        with pytest.raises(ValueError, match="roster"):
            index_events(invalid, 6000)


def test_inputs_are_compared_byte_for_byte():
    data = {key: np.array([0.0]) for key in INPUTS}
    require_inputs(data, data, 6000)
    for changed in (np.array([-0.0]), np.array([0], dtype=np.int64), np.array([[0.0]])):
        with pytest.raises(ValueError, match="unequal q_obs"):
            require_inputs(data, {**data, "q_obs": changed}, 6000)
