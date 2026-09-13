from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.science.controlled_predictive_partial_v12 import (
    FrozenPolicy, PartialCheckpoint, RootInterval, profile,
)
from acfqp.science.controlled_predictive_partial_io_v12 import freeze_policy_payload, restore_policy_payload
from acfqp.science.controlled_predictive_quotient_v1 import Query


def fixture_payload():
    root = (1, (1, 1) + (0,) * 14)
    terminal = (0, (2,) + (0,) * 15)
    profiles = {key: profile(key, Counter()) for key in (root, terminal)}
    policies = {"risk_1": {root: "RIGHT"}, "risk_0": {root: "DOWN"}}
    intervals = {name: RootInterval(-1, 1, row[root]) for name, row in policies.items()}
    checkpoint = PartialCheckpoint(budget=8, known_rows={}, profiles=profiles,
        frozen_policy=FrozenPolicy(policies, profiles), root_intervals=intervals,
        work_counts={}, provider_counts={}, prior_diagnostics={}, provider_seconds=0,
        prior_seconds=0, checkpoint_copy_seconds=0, elapsed_seconds=0, stop_reason="ROW_BUDGET")
    return root, terminal, freeze_policy_payload(checkpoint,
        {"risk_1": Query(1, 1, 0), "risk_0": Query()}, root)


def test_roundtrip_preserves_actions_terminals_and_fallback_without_new_observations(monkeypatch):
    root, terminal, payload = fixture_payload()
    restored = restore_policy_payload(json.loads(json.dumps(payload)))
    assert restored.action(root, "risk_1") == "RIGHT"
    assert restored.action(root, "risk_0") == "DOWN"
    assert restored.action(terminal, "risk_1") is None
    assert restored.work_counts["fallback_calls"] == 0
    import acfqp.science.controlled_predictive_partial_v12 as core
    def forbidden(*args, **kwargs):
        raise AssertionError("policy execution tried to observe stochastic dynamics")
    monkeypatch.setattr(core, "_step_v1", forbidden)
    unseen = (2, root[1])
    assert restored.action(unseen, "risk_1") == "LEFT"
    assert restored.work_counts["fallback_calls"] == 1
    assert restored.work_counts["deterministic_swipe_calls"] == 4
    with pytest.raises(KeyError):
        restored.action(root, "undeclared_query")


def test_new_process_cli_executes_unseen_board_fallback_without_closure(tmp_path):
    root, _, payload = fixture_payload()
    artifact = tmp_path / "policy.json"
    artifact.write_text(json.dumps(payload))
    output = tmp_path / "execution.json"
    project = Path(__file__).resolve().parents[1]
    bootstrap = """
import runpy, sys
import acfqp.domains.standard_2048 as domain
def forbidden(*args, **kwargs):
    raise AssertionError('portable partial policy read exact stochastic dynamics')
domain.step_v1 = domain.support_outcomes_v1 = forbidden
sys.modules['acfqp.science.controlled_predictive_2048_v1'] = None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    process = subprocess.run([sys.executable, "-c", bootstrap,
        str(project / "scripts/query_controlled_predictive_partial_v12.py"),
        "--artifact", str(artifact), "--output", str(output), "--remaining-horizon", "2",
        "--board", *(str(rank) for rank in root[1])],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(project / "src")),
        capture_output=True, text=True, check=True)
    assert not process.stderr
    result = json.loads(output.read_text())
    assert result["query_actions"] == {"risk_1": "LEFT", "risk_0": "LEFT"}
    assert result["work_counts"]["fallback_calls"] == 2
    assert result["work_counts"]["deterministic_swipe_calls"] == 8
    assert result["stochastic_observations_requested"] == 0
