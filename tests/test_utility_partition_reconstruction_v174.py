"""Independent reconstruction of SOURCE-fold candidate policies and costs."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_utility_partition_v174 as core
from scripts import analyze_controlled_predictive_utility_partition_v174 as audit


_fixture_spec = spec_from_file_location('utility_core_fixtures_v174',
    Path(__file__).with_name('test_utility_partition_core_v174.py'))
_fixtures = module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixtures)


def data(kind):
    rows = _fixtures.examples('signal' if kind == 'full_vector' else kind)
    if kind == 'full_vector':
        for root in rows:
            preferred = 'LEFT' if root['canonical_board'][0] == 0 else 'DOWN'
            for suffix in root['suffix_trials']:
                # Lower reward wins under risk1 because it succeeds rather than fails.
                suffix['action_components'] = {action: [2., 0., 1.] if action == preferred else [3., 1., 0.]
                                               for action in root['legal_actions']}
    return rows


def root_candidate(payload):
    return next(row for row in payload['candidate_records'] if row['candidate_id'] == '0:0:0')


def reconstructed(rows):
    actual = core.propose_partition(rows, 0)
    independent = audit.independent_utility_proposal(rows, 0)
    assert audit._equal(actual, independent)
    for field in ('fit_counts', 'utility_search_counts', 'node_fit_counts'):
        assert actual[field] == independent[field]
    return actual, independent


@pytest.mark.parametrize('kind,score', (('full_vector', .5), ('reversed_folds', -2.)))
def test_independent_fold_models_recover_whole_vector_policy_effects_and_actual_costs(kind, score):
    rows = data(kind)
    actual, independent = reconstructed(rows)
    candidate = root_candidate(actual)
    assert candidate['score'] == pytest.approx(score)
    assert actual['source_folds'] == [[f'source:{i:02}' for i in range(0, 12, 2)],
                                     [f'source:{i:02}' for i in range(1, 12, 2)]]
    assert actual['training_outcomes'] == independent['training_outcomes']
    assert all('teacher_action' not in row for row in rows)
    for direction in candidate['directions']:
        heldout = set(actual['source_folds'][direction['heldout_fold']])
        assert {row['source_id'] for row in direction['root_decisions']} == heldout
        assert len(direction['source_effects']) == 6
        assert all(row['parent']['support']['complete'] and row['child']['support']['complete']
                   for row in direction['root_decisions'])
        if kind == 'full_vector':
            assert direction['mean_components'] == pytest.approx([-.5, -.5, .5])
            assert candidate['selected']
        else:
            assert not candidate['selected'] and actual['nodes'][0]['kind'] == 'leaf'


def test_independent_support_reconstruction_rejects_whole_candidate_without_partial_scores():
    actual, independent = reconstructed(data('unsupported'))
    candidate = root_candidate(actual)
    assert candidate['reason'] == 'unsupported_heldout_policy'
    assert candidate['score'] is None and not candidate['comparable']
    assert all(direction['score'] is None and direction['source_effects'] == []
               for direction in candidate['directions'])
    unsupported = [(direction['fit_fold'], row['root_id']) for direction in candidate['directions']
                   for row in direction['root_decisions'] if not row['complete']]
    assert unsupported
    expected = [(direction['fit_fold'], row['root_id']) for direction in root_candidate(independent)['directions']
                for row in direction['root_decisions'] if not row['complete']]
    assert unsupported == expected


def test_independent_learning_separates_sse_prediction_gain_from_actual_action_gain():
    rows = data('sse_only')
    actual, independent = reconstructed(rows)
    sse = audit.previous.independent_proposal(rows, 0)
    assert sse['nodes'][0]['kind'] == 'split'
    assert actual['nodes'][0]['kind'] == independent['nodes'][0]['kind'] == 'leaf'
    assert root_candidate(actual)['score'] == 0.
    assert not root_candidate(actual)['selected']
    assert all(row['parent']['canonical_action'] == row['child']['canonical_action']
               for direction in root_candidate(actual)['directions'] for row in direction['root_decisions'])
