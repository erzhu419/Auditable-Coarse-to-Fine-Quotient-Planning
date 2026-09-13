"""Decision membership and execution metrics must survive ties and bad continuations."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v76_test_decision_audit', ROOT /
    'src/acfqp/science/controlled_predictive_decision_audit_v76.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
LEDGER = dict(choice_evaluations=0, standalone_query_evaluations=0)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_decision_v76.audit_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope='Three tiny native-contract fixtures only; no source or target boards.',
        ground_calls=0, model_builds=0, fit_calls=0, production_solver_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def evaluated(*args, **kwargs):
    LEDGER['choice_evaluations'] += 1
    return AUDIT.evaluate_choice(*args, **kwargs)


def test_tied_selected_action_is_optimal_even_with_different_failure():
    nested = (('LEFT', ((('TERMINAL', 'LOST'), Fraction(1), Fraction(1)),)),
              ('RIGHT', ((('TERMINAL', 'CUTOFF'), Fraction(1), Fraction(1)),)))
    result = evaluated(nested, dict(reward_weight=1.0, failure_penalty=0.0), 'RIGHT', [])
    assert result['reference_action'] == 'LEFT'
    assert result['optimal_actions'] == ['LEFT', 'RIGHT']
    assert result['root_action_optimal_membership'] and result['execution_verified']
    assert result['total_regret'] == 0.0 and result['failure_delta'] == -1.0
    assert result['actual_metrics']['value'] == 1.0


def test_wrong_or_missing_h1_action_is_never_replaced_by_oracle():
    child = (('LEFT', 4096, (('LOST', Fraction(1)),)),
             ('RIGHT', 2048, (('CUTOFF', Fraction(1)),)))
    nested = (('UP', ((('H1', child), Fraction(0), Fraction(1)),)),)
    query = dict(reward_weight=1.0, failure_penalty=3.0)
    wrong = evaluated(nested, query, 'UP', [(child, 'LEFT')])
    assert wrong['root_action_optimal_membership']
    assert wrong['selected_action_oracle_metrics']['value'] == 1.0
    assert wrong['actual_metrics'] == dict(reward=2.0, failure=1.0, success=0.0, value=-1.0)
    assert wrong['total_regret'] == wrong['continuation_regret'] == 2.0
    assert not wrong['continuation_optimal'] and wrong['execution_verified']
    missing = evaluated(nested, query, 'UP')
    assert not missing['execution_verified']
    assert missing['actual_metrics'] is None and missing['total_regret'] is None
    assert missing['errors'] == {'missing_continuation_action': 1}


def test_ground_q_combines_root_reward_and_h1_failure_success_exactly():
    child = (('LEFT', 2048, (('CUTOFF', Fraction(3, 4)), ('WON', Fraction(1, 4)))),
             ('RIGHT', 0, (('CUTOFF', Fraction(1)),)))
    nested = (('UP', ((('H1', child), Fraction(1, 2), Fraction(1, 2)),
                     (('TERMINAL', 'LOST'), Fraction(1, 2), Fraction(1, 2)))),
              ('DOWN', ((('TERMINAL', 'WON'), Fraction(0), Fraction(1)),)))
    LEDGER['standalone_query_evaluations'] += 1
    result = AUDIT.query_metrics(nested, dict(reward_weight=1.0, failure_penalty=2.0, goal_bonus=4.0))
    assert result['actions']['UP'] == dict(reward=1.0, failure=0.5, success=0.125, value=0.5)
    assert result['actions']['DOWN']['value'] == 4.0
    assert result['optimal_actions'] == ['DOWN']
    assert result['h1'][0]['action'] == 'LEFT'
    assert result['counts']['h1_contracts_evaluated'] == 1
