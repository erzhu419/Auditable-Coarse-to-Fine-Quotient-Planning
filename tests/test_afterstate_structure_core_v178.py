"""Pure structural-predicate and unchanged-learning counterexamples."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_afterstate_structure_v178 as core
from acfqp.science import controlled_predictive_exact_h3_v177 as exact


def feature_index(action, kind, **fields):
    return next(row['index'] for row in core.FEATURE_VOCABULARY
                if row['action'] == action and row['kind'] == kind and
                all(row.get(key) == value for key, value in fields.items()))


def data(kind='signal'):
    rows = []
    for source in range(12):
        for index in range(4):
            side = int(index >= 2)
            board = [9 if side else 8, 9 if side else 8, 10, 0]+[0]*12
            root = exact.root_from_case(dict(name=f'root:{source:02}:{index}', board=board, horizon=3),
                                        source*4+index, 'SOURCE')
            features = core.feature_from_root(root)
            root['structural_features'] = features
            preferred = 'LEFT' if side else 'UP'
            if kind == 'reversed_folds' and source % 2:
                preferred = 'UP' if side else 'LEFT'
            if kind == 'same_action':
                preferred = 'LEFT'
            good = {'LEFT', 'RIGHT'} if preferred == 'LEFT' else {'UP'}
            root['action_components'] = {action: [root['immediate_rewards'][action], 0., 1.]
                if action in good else [root['immediate_rewards'][action], 1., 0.]
                for action in root['legal_actions']}
            rows.append(root)
    return rows


def test_catalog_has_the_frozen_action_goal_vacancy_and_line_order():
    catalog = core.FEATURE_VOCABULARY
    assert len(catalog) == 264 and len({row['feature_id'] for row in catalog}) == 264
    assert catalog[0]['feature_id'] == 'DOWN:legal'
    assert catalog[1]['feature_id'] == 'DOWN:goal_reached'
    assert catalog[2]['feature_id'] == 'DOWN:vacancy:0'
    assert catalog[17]['feature_id'] == 'DOWN:vacancy:15'
    assert catalog[18]['feature_id'] == 'DOWN:row:0:pair:0:positive_equal'
    assert catalog[19]['feature_id'] == 'DOWN:row:0:pair:0:goal_pair'
    assert catalog[65]['feature_id'] == 'DOWN:col:3:pair:2:goal_pair'
    assert catalog[66]['feature_id'] == 'LEFT:legal'
    assert catalog[-1]['feature_id'] == 'UP:col:3:pair:2:goal_pair'


def test_goal_already_reached_and_next_goal_pair_are_distinct_afterstate_information():
    reached = core.feature_from_root(dict(canonical_board=[10, 10, 0, 0]+[0]*12))
    pending = core.feature_from_root(dict(canonical_board=[9, 9, 10, 0]+[0]*12))
    goal_bit = feature_index('RIGHT', 'goal_reached')
    pair_bit = feature_index('RIGHT', 'goal_pair', axis='row', line=0, pair=0)
    equal_bit = feature_index('RIGHT', 'positive_equal', axis='row', line=0, pair=0)
    assert reached[goal_bit] == 1 and reached[pair_bit] == 0
    assert pending[goal_bit] == 0 and pending[pair_bit] == pending[equal_bit] == 1


def test_illegal_action_is_all_zero_and_work_counts_only_inspect_legal_afterstates():
    counts = Counter()
    features = core.feature_from_root(dict(canonical_board=[1, 0, 0, 0]+[0]*12), counts)
    assert features[66:132] == [0]*66  # LEFT is unchanged.
    assert features[198:264] == [0]*66  # UP is unchanged.
    assert features[0] == features[132] == 1
    assert counts['structural_ground_swipe_calls'] == 4
    assert counts['structural_goal_tile_reads'] == counts['structural_vacancy_tile_reads'] == 32
    assert counts['structural_line_tile_reads'] == 64
    assert counts['structural_adjacent_slots_inspected'] == 48
    assert counts['structural_illegal_feature_zero_assignments'] == 132


def test_structural_equalities_compress_vacancies_and_keep_overlapping_adjacencies():
    board = [1, 1, 0, 0]*3+[0]*4
    features = core.feature_from_root(dict(canonical_board=board))
    assert features[feature_index('RIGHT', 'positive_equal', axis='col', line=3, pair=0)] == 1
    assert features[feature_index('RIGHT', 'positive_equal', axis='col', line=3, pair=1)] == 1
    assert features[feature_index('RIGHT', 'positive_equal', axis='col', line=3, pair=2)] == 0
    low = core.feature_from_root(dict(canonical_board=[1, 1, 0, 0]+[0]*12))
    high = core.feature_from_root(dict(canonical_board=[7, 7, 0, 0]+[0]*12))
    assert low == high  # Raw rank shifts below the goal do not define predicates.


def test_exact_learning_selects_structural_policy_difference_and_preserves_native_training_board():
    rows = data()
    fitted = core.fit_partition(rows)
    node = fitted['nodes'][0]
    assert node['kind'] == 'split' and node['threshold'] == 0
    assert node['cell'] == feature_index('LEFT', 'positive_equal', axis='row', line=3, pair=0)
    assert node['feature_id'] == core.FEATURE_VOCABULARY[node['cell']]['feature_id']
    selected = next(record for record in fitted['candidate_records'] if record['selected'])
    assert selected['comparable'] and selected['score'] > 0.
    assert len(fitted['candidate_records']) == 264
    assert fitted['feature_counts']['structural_feature_cache_hits'] == 48
    assert 'structural_ground_swipe_calls' not in fitted['feature_counts']
    for raw, outcome in zip(rows, fitted['training_outcomes']):
        assert outcome['canonical_board'] == raw['canonical_board'] and len(outcome['canonical_board']) == 16
        assert outcome['structural_features'] == raw['structural_features'] and len(outcome['structural_features']) == 264
        assert outcome['action_components'] == raw['action_components'] and 'suffix_trials' not in outcome
    for row in (rows[0], rows[2]):
        decision = core.choose_action(fitted, row)
        assert not decision['fallback']
        assert decision['canonical_action'] == ('LEFT' if row is rows[2] else 'UP')


def test_source_crossfit_still_rejects_reversed_holdout_effect_instead_of_full_data_geometry_fit():
    fitted = core.fit_partition(data('reversed_folds'))
    candidate = next(record for record in fitted['candidate_records']
                     if record['cell'] == feature_index('LEFT', 'positive_equal', axis='row', line=3, pair=0))
    assert candidate['comparable'] and candidate['score'] < 0.
    assert fitted['nodes'] == [dict(node_id=0, kind='leaf', leaf_id=0)]


def test_cached_deployment_routes_264_features_without_repeating_ground_work(monkeypatch):
    rows = data()
    fitted = core.fit_partition(rows)
    def forbidden(*args, **kwargs):
        raise AssertionError('cached decision repeated its ground feature computation')
    monkeypatch.setattr(core.ground, 'swipe_board_v1', forbidden)
    counts = Counter()
    decision = core.choose_action(fitted, rows[2], counts)
    assert decision['canonical_action'] == 'LEFT'
    assert decision['feature_work'] == dict(structural_feature_cache_hits=1, structural_cached_feature_reads=264)
    assert counts['partition_feature_threshold_tests'] == 1
    assert counts['structural_feature_cache_hits'] == 1 and 'structural_ground_swipe_calls' not in counts


def test_deployment_fallback_and_exact_reward_parameter_do_not_use_oracle_labels():
    rows = data()
    fitted = core.fit_partition(rows)
    root = deepcopy(rows[0])
    before = core.choose_action(fitted, root)
    root['oracle_action'], root['teacher_action'] = 'LEFT', 'LEFT'
    root['action_components'] = {action: [100000., 0., 1.] for action in root['legal_actions']}
    assert core.choose_action(fitted, root) == before
    root['immediate_rewards']['LEFT'] += 100.
    assert core.choose_action(fitted, root)['canonical_action'] == 'LEFT'
    root.update(legal_actions=['DOWN', 'LEFT'], fallback_action='DOWN',
                immediate_rewards=dict(DOWN=7., LEFT=0.), action_map=dict(DOWN='DOWN', LEFT='LEFT'))
    decision = core.choose_action(fitted, root)
    assert decision['fallback'] and decision['canonical_action'] == 'DOWN'
    assert decision['reason'] == 'insufficient_action_support'
