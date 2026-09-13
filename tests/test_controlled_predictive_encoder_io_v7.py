import json
import os
from pathlib import Path
import subprocess
import sys

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_encoder_io_v7 import (
    artifact_inventory, freeze_artifact_payload, restore_artifact_payload, write_encoder_artifact,
)
from acfqp.science.controlled_predictive_encoder_v7 import TrainingModel, compile_encoded, fit_encoder
from acfqp.science.controlled_predictive_quotient_v1 import Query, plan, sample_model


def _learned_fixture():
    boards = {"small": (1, 1, *([0] * 14)), "large": (2, 2, *([0] * 14))}
    closure = build_development_closure(boards=boards, horizon=1, max_nodes=1000)
    empirical = sample_model(closure.model, 16, seed=20)
    fit = fit_encoder([TrainingModel("fixture", empirical, closure.boards)], max_depth=2, min_leaf=1)
    build = compile_encoded(empirical, closure.boards, fit.encoder)
    payload = freeze_artifact_payload(fit.encoder, build.compiled, build.code_to_cell,
                                      example_board=boards["large"], example_horizon=1)
    return closure, fit.encoder, build, payload


def test_learned_tree_and_all_dynamics_survive_without_original_state_inventory(tmp_path):
    """Losing rules or rows during export would make reload a different model."""
    closure, encoder, build, payload = _learned_fixture()
    assert any("feature" in tree for tree in encoder.trees.values())
    restored, model, code_map = restore_artifact_payload(json.loads(json.dumps(payload)))
    assert restored.to_payload() == encoder.to_payload()
    assert model.rows == build.compiled.rows
    assert model.roots == build.compiled.roots
    assert code_map == build.code_to_cell
    assert not model.state_to_cell
    assert all(not cell.members for cell in model.cells.values())
    for state, board in closure.boards.items():
        assert restored.encode(board, closure.model.layers[state]) == encoder.encode(board, closure.model.layers[state])
    serialized = json.dumps(payload)
    assert "state_to_cell" not in serialized
    assert "members" not in serialized
    assert "boards" not in serialized
    assert "training" not in serialized
    destination = tmp_path / "encoder.json"
    write_encoder_artifact(destination, payload)
    assert destination.stat().st_size == artifact_inventory(payload)["artifact_total_bytes"]


def test_fresh_process_encodes_unlisted_board_without_fitting_or_stochastic_dynamics(tmp_path):
    """A hidden lookup or runtime kernel reconstruction would fail on this new input."""
    closure, encoder, build, payload = _learned_fixture()
    board = (3, 3, *([0] * 14))
    assert board not in closure.boards.values()
    assert list(board) != payload["example_input"]["board"]
    code = encoder.encode(board, 1)
    query = Query(1.0, 0.3, 0.2)
    expected = plan(build.compiled, query)
    artifact = tmp_path / "encoder.json"
    output = tmp_path / "query.json"
    write_encoder_artifact(artifact, payload)
    project = Path(__file__).resolve().parents[1]
    script = project / "scripts/query_controlled_predictive_encoder_v7.py"
    bootstrap = """
import runpy, sys
import acfqp.domains.standard_2048 as domain
import acfqp.science.controlled_predictive_encoder_v7 as encoder
def forbidden(*args, **kwargs):
    raise AssertionError('portable query tried to fit or reconstruct stochastic dynamics')
domain.step_v1 = domain.support_outcomes_v1 = forbidden
encoder.fit_encoder = encoder.compile_encoded = forbidden
sys.modules['acfqp.science.controlled_predictive_2048_v1'] = None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    env = dict(os.environ, PYTHONPATH=str(project / "src"))
    process = subprocess.run(
        [sys.executable, "-c", bootstrap, str(script), "--artifact", str(artifact),
         "--output", str(output), "--remaining-horizon", "1", "--board", *map(str, board)],
        cwd=tmp_path, env=env, text=True, capture_output=True, check=True,
    )
    assert not process.stderr
    result = json.loads(output.read_text())
    cell = build.code_to_cell[code]
    assert result["resolved_cell"] == cell
    assert result["action"] == expected.policy[cell]
    assert result["predicted_value"] == expected.values[cell]
    assert result["policy_count"] == len(expected.policy)
    assert not result["exact_model_or_state_lookup_used"]
