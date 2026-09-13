"""Check guarded H2 binding inside H3 construction against the V74 kernel."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOARDS = (
    (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10),
    (10, 10, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10),
)
LEDGER = dict(builds=[], rule_compilations=0, routing_calls=0)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def science(filename, name):
    return module(ROOT / 'src/acfqp/science' / filename, name)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_parametric_v75.integration_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope='Two retained dense development fixtures at H3; no main-cohort roots.',
        ground_calls=0, fit_calls=0, planning_calls=0, model_builds=len(LEDGER['builds']), **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def active_encoding(build):
    return {key: cell for key, cell in build.encoding.items() if build.model.terminal[cell] == 'ACTIVE'}


def test_parametric_h2_keeps_exact_kernel_ids_and_high_labels_in_both_arms():
    contract = science('controlled_predictive_compositional_contract_v69.py', 'v75_test_contract')
    dynamics = science('controlled_predictive_relational_dynamics_v69.py', 'v75_test_dynamics')
    terminal_module = science('controlled_predictive_symbolic_successors_v71.py', 'v75_test_terminal')
    baseline_module = science('controlled_predictive_effect_builder_v74.py', 'v75_test_baseline')
    candidate_module = science('controlled_predictive_parametric_builder_v75.py', 'v75_test_candidate')
    rule = dynamics.LearnedDynamics.from_payload(json.loads((ROOT /
        'reports/controlled_predictive_composition_v69/learned_rule.json').read_text()))
    terminal = terminal_module.compile_rule(rule)
    LEDGER['rule_compilations'] += 1
    for board_index, board in enumerate(BOARDS):
        baseline = baseline_module.build_model(board, 3, rule, terminal, share_successors=True)
        LEDGER['builds'].append(dict(method='V74_SHARED', board_index=board_index, board=list(board),
            horizon=3, counts=baseline.counts, elapsed_seconds=baseline.elapsed_seconds))
        for reuse in (False, True):
            candidate = candidate_module.build_model(board, 3, rule, terminal, reuse=reuse, max_states=200000)
            LEDGER['builds'].append(dict(method='V75_REUSE' if reuse else 'V75_COMPILE_EACH',
                board_index=board_index, board=list(board), horizon=3,
                counts=candidate.counts, elapsed_seconds=candidate.elapsed_seconds))
            assert contract.model_payload(candidate) == contract.model_payload(baseline)
            assert active_encoding(candidate) == active_encoding(baseline)
            assert all(h > 2 for h, _ in candidate.encoding)
    assert len(LEDGER['builds']) == 6
