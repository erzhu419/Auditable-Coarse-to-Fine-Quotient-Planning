import json

import numpy as np
import pytest

from learned_portal_phase3 import run_phase3_r7a_sidecar_audit as sidecar
from learned_portal_phase3.run_phase3_r675_targeted_audit import _all_surrogate_ordered, _goal_sha1


@pytest.fixture
def ledger():
    return json.loads((sidecar.ROOT / "learned_portal_phase3" / "p3_v4_r675_verified_results.json").read_text())


def test_frozen_pac_and_control_denominators(ledger):
    counts = sidecar._event_accounting(ledger)
    assert counts["total_saved_method_events_in_v4"] == 1952
    assert counts["discrete_pac_four_inequality_events"] == 960
    assert counts["uncertified_plugin_ce_control_events"] == 320
    assert counts["tier4_empirical_continuous_surrogate_events"] == 672
    assert counts["discrete_pac_zero_slack_violations"] == counts["discrete_pac_within_requested_eps_count"] == 0


def test_event_accounting_rejects_duplicate_and_wrong_bound_flag(ledger):
    rows = ledger["block_e2_curved_3d_linear_mf_and_4level"]["task_events"]
    row = rows[0]
    row["pac_violation_zero_slack"] = True
    with pytest.raises(ValueError, match="flag"):
        sidecar._event_accounting(ledger)
    row["pac_violation_zero_slack"] = False
    rows[-1] = row
    with pytest.raises(ValueError, match="duplicate"):
        sidecar._event_accounting(ledger)


def test_missing_posterior_and_unmatched_task_cannot_verify_ordering():
    key = dict(seed=3, task_index=0, start_state=1, goal_sha1="123")
    pac = dict(key, method_id="pac", hi=4.0)
    ce = dict(key, method_id="ce", posterior_pac_upper_bound_on_policy=5.0)
    def ordered():
        return _all_surrogate_ordered([pac, ce], "pac", "ce", 1, 1e-9)
    assert ordered()
    ce["posterior_pac_upper_bound_on_policy"] = None
    assert not ordered()
    ce.update(posterior_pac_upper_bound_on_policy=5.0, goal_sha1="456")
    assert not ordered()


def test_ce_replay_requires_actual_cost_and_task_identity():
    gm = np.array([False, True])
    solution = dict(Pi_ext_csr=object(), pred_val=2.0, global_lu_rhs=1)
    ref = dict(start_state=0, goal_sha1=_goal_sha1(gm), proper_policy=True,
               deployed_policy_J=10.0, ce_overoptimism_violation=True)
    class Environment:
        def evaluate_deployed_policy_true_cost(self, policy, mask, phi, start):
            assert policy is solution["Pi_ext_csr"] and mask is gm
            return 10.0
    def replay():
        return sidecar._verified_ce_event("test", 3, 0, Environment(), solution, 0, gm, ref)
    assert replay()["global_lu_rhs"] == 1
    # A wrong saved cost gives the same optimism flag as the correct one.
    ref["deployed_policy_J"] = 11.0
    with pytest.raises(ValueError, match="cost mismatch"):
        replay()
    ref["goal_sha1"] = "other"
    with pytest.raises(ValueError, match="identity"):
        replay()


def test_freeze_verifies_phase1_results_and_phase2_release_report(tmp_path):
    source = sidecar._verify_frozen_roster(sidecar.ROOT)
    for name in source["files"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(sidecar.ROOT / name)
    for name in ("green_response/exp1_results.json", "quotient_phase2/m232_release_verification_report.json"):
        target = tmp_path / name
        target.unlink()
        target.write_bytes(b"{}")
        with pytest.raises(ValueError, match="manifest mismatch"):
            sidecar._verify_frozen_roster(tmp_path)
        target.unlink()
        target.symlink_to(sidecar.ROOT / name)
