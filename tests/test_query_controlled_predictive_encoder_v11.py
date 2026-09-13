import json
import os
from pathlib import Path
import subprocess
import sys

from acfqp.science.controlled_predictive_encoder_io_v7 import freeze_artifact_payload, write_encoder_artifact
from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, RuleEncoder
from acfqp.science.controlled_predictive_quotient_v1 import Cell, CompiledModel, Outcome, Query, plan


def test_fresh_process_executes_one_feature_block_without_earlier_runtime_or_board_cache(tmp_path):
    """The delivered command must run V11 blocks, not an older eager or cached encoder."""
    board = (0,) * 5 + (1,) + (0,) * 10
    group = (1, "ACTIVE", ACTIONS)
    encoder = RuleEncoder({group: {"feature": 0, "threshold": 14.5,
                                   "left": {"leaf": 9}, "right": {"leaf": 9}}})
    model = CompiledModel(
        {0: Cell(0, "CUTOFF", (100,)), 1: Cell(1, "ACTIVE", (101,))},
        {(1, action): (Outcome(1.0, 0, float(action == "RIGHT")),) for action in ACTIONS},
        (1,), {100: 0, 101: 1}, {},
    )
    payload = freeze_artifact_payload(encoder, model, {(0, "CUTOFF", (), 0): 0, (*group, 9): 1},
                                      example_board=board, example_horizon=1)
    artifact, output = tmp_path / "model.json", tmp_path / "query.json"
    write_encoder_artifact(artifact, payload)
    project = Path(__file__).resolve().parents[1]
    script = project / "scripts/query_controlled_predictive_encoder_v11.py"
    bootstrap = """
import runpy, sys
import acfqp.domains.standard_2048 as domain
import acfqp.science.controlled_predictive_encoder_v7 as eager
import acfqp.science.controlled_predictive_encoder_runtime_v8 as old_runtime
import acfqp.science.controlled_predictive_encoder_runtime_v10 as cached_runtime
def forbidden(*args, **kwargs):
    raise AssertionError('V11 query called an older encoder, board cache or stochastic dynamics')
eager._profile = eager.RuleEncoder.encode = forbidden
old_runtime.profile = old_runtime.RuntimeEncoder.encode = forbidden
cached_runtime.FeatureCache = cached_runtime.RuntimeEncoder.encode = forbidden
domain.step_v1 = domain.support_outcomes_v1 = forbidden
sys.modules['acfqp.science.controlled_predictive_2048_v1'] = None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    process = subprocess.run(
        [sys.executable, "-c", bootstrap, str(script), "--artifact", str(artifact),
         "--example-root", "--output", str(output)], cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(project / "src")), check=True, capture_output=True, text=True,
    )
    assert not process.stderr
    result = json.loads(output.read_text())
    expected = plan(model, Query(1, .3, .2))
    assert result["runtime"] == "V11_FIXED_FEATURE_BLOCKS"
    assert result["action"] == expected.policy[1] == "RIGHT"
    assert result["predicted_value"] == expected.values[1]
    assert result["planning_counts"] == expected.counts
    assert result["encoding_feature_work"]["feature_blocks_computed"] == 1
    assert result["encoding_feature_work"]["scalar_feature_values_computed"] == 7
    assert result["encoding_feature_work"]["terminal_feature_contexts_created"] == 0
    assert result["code"] == [1, "ACTIVE", list(ACTIONS), 9]
    assert not result["exact_model_or_state_lookup_used"]
