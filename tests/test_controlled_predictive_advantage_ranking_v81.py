"""Retained-action ranking semantics, using synthetic labels only."""
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ranking_v81_test',
    ROOT / 'scripts/diagnose_controlled_predictive_advantage_ranking_v81.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LEDGER = Counter()
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')
BOARD = (1, 1) + (0,) * 13 + (3,)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_policy_advantage_v81.ranking_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append(dict(session_failures=request.session.testsfailed,
        scope='Synthetic retained labels and fixed leaf predictions only.',
        ground_calls=0, tree_fits=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def leaf(value):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[value], samples=[16])


def rows():
    return [dict(board=BOARD, query=query, episode=episode, root_index=episode,
        step=20, reference_action='LEFT', action='RIGHT', target=[reward, 0, 0])
        for query in QUERIES for episode, reward in ((0, 2), (4, -4))]


def test_observed_and_predicted_rankings_keep_training_and_holdout_separate(monkeypatch):
    def no_parent(*args, **kwargs):
        pytest.fail('retained ranking must not execute a parent decision')
    monkeypatch.setattr(Policy, 'choose', no_parent)
    policy = Policy(Policy.base(), {query: leaf([1, 0, 0]) for query in QUERIES}, 1)
    result = MODULE.diagnose_rows(rows(), policy, RULE)
    LEDGER.update(result['counts'])
    for query in QUERIES:
        training, heldout = (result['queries'][query][split] for split in ('training', 'heldout'))
        assert training['roots'] == heldout['roots'] == 1
        assert training['overrides'] == heldout['overrides'] == 1
        assert training['observed_selected_advantage_mean'] == 2
        assert heldout['observed_selected_advantage_mean'] == -4
        assert training['override_observed_positive'] == heldout['override_observed_negative'] == 1
        assert training['regret_to_best_retained_mean'] == 0
        assert heldout['regret_to_best_retained_mean'] == 4
    assert 'model_uniform_draws' not in result['counts']


def test_zero_and_negative_predictions_keep_exact_zero_reference():
    policy = Policy(Policy.base(), {'reward': leaf([0, 0, 0]),
                                  'risk_goal': leaf([-1, 0, 0])}, 1)
    result = MODULE.diagnose_rows(rows(), policy, RULE)
    LEDGER.update(result['counts'])
    for query in QUERIES:
        for split in ('training', 'heldout'):
            summary = result['queries'][query][split]
            assert summary['overrides'] == 0
            assert summary['predicted_selected_advantage_mean'] == 0
            assert summary['observed_selected_advantage_mean'] == 0
        assert result['queries'][query]['training']['best_retained_advantage_mean'] == 2
        assert result['queries'][query]['training']['regret_to_best_retained_mean'] == 2
    assert all(root['selected_action'] == root['reference_action'] == 'LEFT' for root in result['roots'])
