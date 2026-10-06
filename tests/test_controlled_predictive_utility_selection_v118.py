"""Paired roster validity, exact query protection and utility selection."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_utility_selection_v118 import select_utility

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_utility_selection_v118.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, tree_fits=0, neural_model_fits=0, optimizer_steps=0,
        scope='Synthetic retained utility rows; pure selection arithmetic, no games or model inference.'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def choose(rows):
    WORK['selector_calls'] += 1
    WORK['synthetic_utility_rows_read'] += len(rows)
    return select_utility(rows)


def roster(keep=(0., 0.), shared=(1., 1.), split=(2., 2.)):
    return [dict(candidate=name, query=query, replica=replica, seed=118000 + replica,
        result=dict(utility=values[index][replica] if isinstance(values[index], list) else values[index],
            status='WON' if replica % 2 else 'LOST'))
        for name, values in (('KEEP', keep), ('NEW_SHARED', shared), ('NEW_SPLIT', split))
        for index, query in enumerate(('reward', 'risk_goal')) for replica in range(4)]


def test_query_replica_means_are_paired_and_input_order_independent():
    rows = roster(keep=([0., 2., 4., 6.], [-4., -2., 0., 2.]),
        shared=(4., 0.), split=([2., 4., 6., 8.], 0.))
    original = deepcopy(rows)
    result = choose(list(reversed(rows)))
    assert result['selection_complete']
    assert result['summaries']['KEEP']['queries']['reward'] == dict(
        mean_utility=3., per_replica=[0., 2., 4., 6.])
    assert result['summaries']['KEEP']['mean_utility'] == 1.
    assert result['summaries']['NEW_SHARED']['mean_utility'] == 2.
    assert result['summaries']['NEW_SPLIT']['mean_utility'] == 2.5
    assert result['selected_candidate'] == 'NEW_SPLIT'
    assert rows == original


def test_missing_cutoff_duplicate_and_unpaired_rows_never_select_partial_means():
    rows = roster()
    missing = rows[:-1]
    cutoff = deepcopy(rows); cutoff[-1]['result']['status'] = 'CUTOFF'
    mismatched = deepcopy(rows); mismatched[-1]['seed'] += 100
    duplicated = rows + [deepcopy(rows[-1])]
    for invalid, problem in ((missing, 'missing_rows'), (cutoff, 'nonterminal_games'),
            (mismatched, 'unpaired_seeds'), (duplicated, 'duplicate_rows')):
        result = choose(invalid)
        assert result['selected_candidate'] == 'KEEP'
        assert not result['selection_complete'] and problem in result['reason']
        assert all(value['mean_utility'] is None for value in result['summaries'].values())
        assert not any(value['eligible'] for value in result['acceptance'].values())


def test_improved_pooled_utility_cannot_compensate_for_query_harm():
    result = choose(roster(keep=(0., 0.), shared=(100., -1.), split=(0., 0.)))
    assert result['summaries']['NEW_SHARED']['mean_utility'] > result['summaries']['KEEP']['mean_utility']
    assert result['acceptance']['NEW_SHARED'] == dict(eligible=False,
        improved_queries=['reward'], harmed_queries=['risk_goal'], equal_queries=[])
    assert result['selected_candidate'] == 'KEEP'


def test_exact_ties_preserve_keep_or_prefer_shared_and_tiny_improvement_counts():
    tied = choose(roster(keep=(1., 1.), shared=(1., 1.), split=(1., 1.)))
    assert tied['selected_candidate'] == 'KEEP'
    assert all(value['equal_queries'] == ['reward', 'risk_goal'] for value in tied['acceptance'].values())
    eligible_tie = choose(roster(keep=(0., 0.), shared=(2., 0.), split=(0., 2.)))
    assert eligible_tie['selected_candidate'] == 'NEW_SHARED'
    tiny = choose(roster(keep=(0., 0.), shared=(1e-15, 0.), split=(0., 0.)))
    assert tiny['selected_candidate'] == 'NEW_SHARED'
    assert tiny['acceptance']['NEW_SHARED']['equal_queries'] == ['risk_goal']
