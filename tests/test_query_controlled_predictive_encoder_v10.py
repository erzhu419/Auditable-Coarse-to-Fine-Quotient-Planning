import json
import os
from pathlib import Path
import subprocess
import sys

from acfqp.science.controlled_predictive_encoder_io_v7 import freeze_artifact_payload, write_encoder_artifact
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, RuleEncoder
from acfqp.science.controlled_predictive_quotient_v1 import Cell, CompiledModel, Outcome, Query, plan


def test_fresh_query_process_uses_lazy_runtime_and_preserves_portable_model_result(tmp_path):
    """An accidental old encoder import would turn the V10 reload into an eager query."""
    board = (0,) * 5 + (1,) + (0,) * 10
    group = (1, "ACTIVE", ACTIONS)
    tree = {"feature": 0, "threshold": 14.5, "left": {"leaf": 9}, "right": {"leaf": 9}}
    encoder = RuleEncoder({group: tree})
    model = CompiledModel(
        {0: Cell(0, "CUTOFF", (100,)), 1: Cell(1, "ACTIVE", (101,))},
        {(1, action): (Outcome(1.0, 0, float(action == "RIGHT")),) for action in ACTIONS},
        (1,), {100: 0, 101: 1}, {},
    )
    code_map = {(0, "CUTOFF", (), 0): 0, (*group, 9): 1}
    payload = freeze_artifact_payload(encoder, model, code_map, example_board=board, example_horizon=1)
    artifact = tmp_path / "model.json"
    output = tmp_path / "query.json"
    write_encoder_artifact(artifact, payload)
    project = Path(__file__).resolve().parents[1]
    script = project / "scripts/query_controlled_predictive_encoder_v10.py"
    bootstrap = """
import runpy, sys
import acfqp.domains.standard_2048 as domain
import acfqp.science.controlled_predictive_encoder_v7 as eager
import acfqp.science.controlled_predictive_encoder_runtime_v8 as old_runtime
def forbidden(*args, **kwargs):
    raise AssertionError('V10 query called eager encoding or stochastic dynamics')
eager._profile = eager.RuleEncoder.encode = forbidden
old_runtime.profile = old_runtime.RuntimeEncoder.encode = forbidden
domain.step_v1 = domain.support_outcomes_v1 = forbidden
sys.modules['acfqp.science.controlled_predictive_2048_v1'] = None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", bootstrap, str(script), "--artifact", str(artifact),
         "--example-root", "--output", str(output)],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(project / "src")),
        check=True, capture_output=True, text=True,
    )
    assert not result.stderr
    query = json.loads(output.read_text())
    reference = plan(model, Query(1, .3, .2))
    assert query["runtime"] == "V10_LAZY"
    assert query["action"] == reference.policy[1] == "RIGHT"
    assert query["predicted_value"] == reference.values[1]
    assert query["planning_counts"] == reference.counts
    assert query["encoding_work_counts"]
    assert query["encoding_cache"]
    assert query["code"] == [1, "ACTIVE", list(ACTIONS), 9]
    assert not query["exact_model_or_state_lookup_used"]
