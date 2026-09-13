import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.science.controlled_predictive_history_io_v13 import (
    RecordedHistoryPolicy, freeze_history_payload, replay_all_histories,
)


def fixture_payload():
    board = lambda rank: [rank] + [0] * 15
    terminal = {"key": [0, board(4)], "status": "CUTOFF"}
    def node(h, rank, action, children):
        return {"key": [h, board(rank)], "action": action,
                "children": [{"probability": 1 / len(children), "reward": 0, "node": child}
                             for child in children]}
    left = node(2, 2, "UP", [node(1, 4, "RIGHT", [terminal])])
    right = node(2, 3, "DOWN", [node(1, 4, "LEFT", [terminal])])
    trace = node(3, 1, "RIGHT", [left, right])
    return freeze_history_payload({"risk_1": {"reward_weight": 1, "failure_penalty": 1, "goal_bonus": 0}},
                                  {"risk_1": trace}, {"fixture": True})


def test_same_board_at_same_horizon_can_choose_different_actions_by_history():
    payload = json.loads(json.dumps(fixture_payload()))
    policy = RecordedHistoryPolicy(payload)
    key = lambda h, rank: (h, (rank,) + (0,) * 15)
    assert policy.action("risk_1", (key(3, 1), key(2, 2), key(1, 4))) == "RIGHT"
    assert policy.action("risk_1", (key(3, 1), key(2, 3), key(1, 4))) == "LEFT"
    assert policy.action("risk_1", (key(3, 1), key(2, 2), key(1, 4), key(0, 4))) is None
    with pytest.raises(ValueError, match="outside"):
        policy.action("risk_1", (key(3, 1), key(2, 5)))
    with pytest.raises(KeyError):
        policy.action("undeclared", (key(3, 1),))
    assert "probability" not in json.dumps(payload)
    assert "observed_rows" not in json.dumps(payload)


def test_fresh_process_replays_all_histories_without_dynamics_or_acquisition(tmp_path):
    payload = fixture_payload()
    artifact, output = tmp_path / "history.json", tmp_path / "replay.json"
    artifact.write_text(json.dumps(payload))
    project = Path(__file__).resolve().parents[1]
    bootstrap = """
import runpy, sys
import acfqp.domains.standard_2048 as domain
def forbidden(*args, **kwargs):
    raise AssertionError('history replay requested stochastic dynamics')
domain.step_v1 = domain.support_outcomes_v1 = forbidden
for name in ['acfqp.science.controlled_predictive_partial_v12',
             'acfqp.science.controlled_predictive_execution_v13']:
    sys.modules[name] = None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    process = subprocess.run([sys.executable, "-c", bootstrap,
        str(project / "scripts/replay_controlled_predictive_history_v13.py"),
        "--artifact", str(artifact), "--output", str(output)],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(project / "src")),
        capture_output=True, text=True, check=True)
    assert not process.stderr
    actual = json.loads(output.read_text())
    expected = replay_all_histories(payload)
    for field, value in expected.items():
        assert actual[field] == value
    assert actual["decision_count"] == 5
    assert actual["terminal_history_count"] == 2
