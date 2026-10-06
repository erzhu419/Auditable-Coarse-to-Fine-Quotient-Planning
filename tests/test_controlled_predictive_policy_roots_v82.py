"""Frozen-reference semantics and complete heldout-cohort extraction."""
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import random

import pytest

from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES
from acfqp.science.controlled_predictive_policy_roots_v82 import prepare_roots
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports/controlled_predictive_policy_iteration_v81'
SPEC = importlib.util.spec_from_file_location('ranking_v81_for_roots_v82',
    ROOT / 'scripts/diagnose_controlled_predictive_advantage_ranking_v81.py')
RANKING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RANKING)
RULE = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')
BOARD = (1, 1) + (0,) * 13 + (3,)
LEDGER = Counter()


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_policy_roots_v82.checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append(dict(session_failures=request.session.testsfailed,
        scope='Synthetic cohort choices and all 24 retained V81 first-round heldout roots.',
        ground_calls=0, tree_fits=0, model_uniform_draws=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def leaf(value):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[value], samples=[16])


def fixture(tmp_path, value):
    policy = Policy(Policy.base(), {query: leaf(value) for query in QUERIES}, 1)
    entries = [dict(root=dict(query='reward', episode=episode, step=20,
        board=BOARD, reference_action='LEFT'), root_index=episode,
        censored_root=False, trajectories=8, ground_work={'sampled_transitions': 8},
        pair_deltas={action: [[1, 0, 0], [-3, 0, 0]]
                     for action in ('DOWN', 'RIGHT', 'UP')}) for episode in (0, 4)]
    folder = tmp_path / 'life_0/iteration_1'
    folder.mkdir(parents=True)
    (folder / 'root_logs.json').write_text(json.dumps(entries))
    (folder / 'current_policy.json').write_text(json.dumps(policy.to_payload()))
    return policy, entries


def forbid_decisions_and_rng(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('root freezing must not rerun a policy or consume RNG')
    monkeypatch.setattr(Policy, 'choose', forbidden)
    monkeypatch.setattr(random.Random, 'random', forbidden)


def test_recorded_reference_and_ties_match_retained_diagnostic(tmp_path, monkeypatch):
    policy, entries = fixture(tmp_path, [1, 0, 0])
    forbid_decisions_and_rng(monkeypatch)
    roots, log = prepare_roots(tmp_path, 0, RULE)
    LEDGER.update(log['counts'])
    row = entries[1]['root']
    reference = row['reference_action']
    rows = [dict(**row, root_index=4, action=action, target=[-1, 0, 0])
            for action in ('UP', 'RIGHT', 'DOWN')]
    expected = RANKING.diagnose_rows(rows, policy, RULE)['roots'][0]
    assert len(roots) == 1 and roots[0]['episode'] == 4
    assert roots[0]['reference_action'] == reference == 'LEFT'
    assert roots[0]['selected_action'] == expected['selected_action'] == 'DOWN'
    assert roots[0]['predicted_advantage'] == [1, 0, 0]
    assert roots[0]['old_observed_advantage'] == [-1, 0, 0]
    assert roots[0]['original_replica_deltas'] == [[1, 0, 0], [-3, 0, 0]]
    assert log['inherited_source']['trajectories'] == 8


def test_reference_kept_for_zero_advantage_and_single_legal_action(tmp_path, monkeypatch):
    fixture(tmp_path, [0, 0, 0])
    forbid_decisions_and_rng(monkeypatch)
    roots, log = prepare_roots(tmp_path, 0, RULE)
    LEDGER.update(log['counts'])
    assert roots[0]['selected_action'] == roots[0]['reference_action'] == 'LEFT'
    assert roots[0]['old_observed_advantage'] == [0, 0, 0]
    assert roots[0]['original_replica_deltas'] == [[0, 0, 0], [0, 0, 0]]
    class OneActionRule:
        def classify(self, board, work):
            return 'PLAYING', [('LEFT', board, 0)]
    roots, log = prepare_roots(tmp_path, 0, OneActionRule())
    LEDGER.update(log['counts'])
    assert len(roots) == 1 and roots[0]['selected_action'] == 'LEFT'
    assert roots[0]['legal_actions'] == ['LEFT']
    assert log['counts'].get('advantage_prediction_rows', 0) == 0


def test_censored_root_is_not_silently_removed(tmp_path):
    _, entries = fixture(tmp_path, [1, 0, 0])
    entries[1]['censored_root'] = True
    (tmp_path / 'life_0/iteration_1/root_logs.json').write_text(json.dumps(entries))
    with pytest.raises(ValueError, match='censored root'):
        prepare_roots(tmp_path, 0, RULE)


def test_all_24_actual_heldout_roots_match_preexisting_rankings(monkeypatch):
    forbid_decisions_and_rng(monkeypatch)
    rule = LearnedDynamics.from_payload(json.loads((SOURCE / 'supplied_dynamics.json').read_text()))
    diagnostic = json.loads((SOURCE / 'ranking_diagnostic.json').read_text())
    cohort = []
    for lifecycle in range(3):
        roots, log = prepare_roots(SOURCE, lifecycle, rule)
        LEDGER.update(log['counts'])
        expected = next(result for result in diagnostic['results']
                        if result['lifecycle'] == lifecycle and result['iteration'] == 1)
        indexed = {(root['query'], root['episode'], root['root_index']): root
                   for root in expected['roots'] if root['split'] == 'heldout'}
        assert len(roots) == 8
        assert log['roots_by_query'] == {'reward': 4, 'risk_goal': 4}
        for root in roots:
            previous = indexed[root['query'], root['episode'], root['root_index']]
            assert root['selected_action'] == previous['selected_action']
            assert root['reference_action'] == previous['reference_action']
            assert RANKING.utility(root['predicted_advantage'], QUERIES[root['query']]) == pytest.approx(
                previous['predicted_selected_advantage'])
            assert RANKING.utility(root['old_observed_advantage'], QUERIES[root['query']]) == pytest.approx(
                previous['observed_selected_advantage'])
        cohort.extend(roots)
    assert len(cohort) == 24
    LEDGER['actual_heldout_roots_verified'] += len(cohort)
