"""Two fixed H2 boards verify construction order and exact model preservation."""
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_compositional_contract_v69 import (
    build_model as concrete_build, model_payload,
)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_symbolic_contract_v71 import build_model as symbolic_build
from acfqp.science.controlled_predictive_symbolic_successors_v71 import compile_rule


ROOT = Path(__file__).resolve().parents[1]
BOARDS = (
    (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10),
    (10, 10, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10),
)
LEDGER = dict(builds=[], rule_compilations=0)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_symbolic_v71.integration_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope='Two fixed dense development boards at H2; no main-cohort cases.',
        ground_calls=0, fit_calls=0, planning_calls=0, source_acquisition_calls=0,
        model_builds=len(LEDGER['builds']), **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def active_encoding(build):
    return {key: state for key, state in build.encoding.items()
            if build.model.terminal[state] == 'ACTIVE'}


def test_symbolic_build_keeps_exact_cells_joint_rows_and_active_encoding():
    rule_payload = json.loads((ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json').read_text())
    rule = LearnedDynamics.from_payload(rule_payload)
    compiled = compile_rule(rule)
    LEDGER['rule_compilations'] += 1
    for board_index, board in enumerate(BOARDS):
        for variant in ('FULL', 'COMPOSED'):
            baseline = concrete_build(board, 2, rule, variant)
            LEDGER['builds'].append(dict(board_index=board_index, board=list(board), horizon=2,
                method='V69', variant=variant, counts=baseline.counts,
                elapsed_seconds=baseline.elapsed_seconds))
            candidate = symbolic_build(board, 2, rule, compiled, variant)
            LEDGER['builds'].append(dict(board_index=board_index, board=list(board), horizon=2,
                method='V71', variant=variant, counts=candidate.counts,
                elapsed_seconds=candidate.elapsed_seconds))
            assert model_payload(candidate) == model_payload(baseline)
            assert active_encoding(candidate) == active_encoding(baseline)
            assert candidate.encoding == active_encoding(candidate)
            assert candidate.counts['h0_boards_generated'] == 0
            assert candidate.counts['concrete_h0_states'] == 0
            assert baseline.counts['h0_boards_generated'] > 0
            assert candidate.counts['concrete_states'] < baseline.counts['concrete_states']
