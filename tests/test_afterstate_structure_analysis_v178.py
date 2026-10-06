"""Observable feature checks and independent Boolean utility-tree reconstruction."""
from collections import Counter
from copy import deepcopy
import pytest

from acfqp.science import controlled_predictive_afterstate_structure_v178 as core
from scripts import analyze_controlled_predictive_afterstate_structure_v178 as audit
from scripts import run_controlled_predictive_afterstate_structure_v178 as runner


def test_local_swipe_features_goal_overlap_illegal_and_cached_costs():
    root = dict(canonical_board=[10, 10, 10, 0]+[0]*12)
    own_work, core_work = Counter(), Counter()
    actual = audit.feature_from_root(root, own_work)
    expected = core.feature_from_root(root, core_work)
    assert actual == expected and own_work == core_work
    assert audit.FEATURE_VOCABULARY == core.FEATURE_VOCABULARY
    by_name = {row['feature_id']: row['index'] for row in audit.FEATURE_VOCABULARY}
    assert actual[by_name['LEFT:goal_reached']] == 1
    assert actual[by_name['DOWN:goal_reached']] == 0
    assert actual[by_name['DOWN:row:3:pair:0:goal_pair']] == 1
    assert actual[by_name['DOWN:row:3:pair:1:goal_pair']] == 1
    assert actual[198:] == [0]*66  # UP is illegal, including all its vacancy bits.
    cached = dict(root, structural_features=actual, action_components={'LEFT': [1000., 0., 1.]})
    own_cached, core_cached = Counter(), Counter()
    assert audit.feature_from_root(cached, own_cached) == core.feature_from_root(cached, core_cached)
    assert own_cached == core_cached == Counter(structural_feature_cache_hits=1, structural_cached_feature_reads=264)


def examples():
    rows = []
    for ordinal in range(48):
        if ordinal == 15:
            continue
        bit = int(ordinal % 4 >= 2); features = [0]*264; features[8] = features[9] = bit
        rows.append(dict(root_id=f'r:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{ordinal//4:02d}',
            canonical_board=[9]*16, structural_features=features, legal_actions=['DOWN', 'LEFT'],
            immediate_rewards={'DOWN': 0., 'LEFT': 0.},
            action_components={'DOWN': [0., float(not bit), float(bit)], 'LEFT': [0., float(bit), float(not bit)]},
            provenance={'kind': 'exact H3'}))
    return rows


def test_boolean_search_reconstructs_candidates_counts_and_original_boards():
    rows = examples(); original = deepcopy(rows)
    actual, expected = audit.fit_partition(rows), core.fit_partition(rows)
    assert audit.previous._equal(actual, expected) and audit.previous._equal(expected, actual)
    assert actual['nodes'][0]['cell'] == 8 and actual['nodes'][0]['threshold'] == 0
    assert len(actual['candidate_records']) == 264
    for key in ('fit_counts', 'node_fit_counts', 'utility_search_counts', 'feature_counts'):
        assert actual[key] == expected[key]
    assert all(row['canonical_board'] == [9]*16 for row in actual['training_outcomes'])
    assert actual['feature_counts'] == {'structural_feature_cache_hits': 47, 'structural_cached_feature_reads': 47*264}
    root = dict(rows[0], fallback_action='DOWN', action_map={'DOWN': 'UP', 'LEFT': 'RIGHT'})
    decision, reference = audit.choose_action(actual, root), core.choose_action(expected, root)
    assert audit.previous._equal(decision, reference) and audit.previous._equal(reference, decision)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['feature_work'] == {'structural_feature_cache_hits': 1, 'structural_cached_feature_reads': 264}
    root['action_components'] = {'DOWN': [1000., 0., 1.], 'LEFT': [-1000., 1., 0.]}
    assert audit.choose_action(actual, root) == decision
    assert rows == original


def test_nested_baselines_and_new_regret_use_paired_vectors_and_group_weights():
    roots, labels = {}, {}
    choices = {'STRUCTURE': {}, 'RAW': {}}
    for cohort in ('SOURCE', 'TARGET'):
        roots[cohort] = [dict(root_id=f'{cohort}:{i}', source_id='large' if i < 2 else 'small', legal_actions=['DOWN', 'LEFT']) for i in range(3)]
        vectors = [dict(DOWN=[0., 1., 0.], LEFT=[0., 0., 1.]), dict(DOWN=[0., 1., 0.], LEFT=[0., 0., 0.]), dict(DOWN=[0., 0., 0.], LEFT=[0., 0., 0.])]
        labels[cohort] = [dict(root_id=root['root_id'], action_components=vectors[i]) for i, root in enumerate(roots[cohort])]
        for name, actions in (('STRUCTURE', ['LEFT', 'DOWN', 'LEFT']), ('RAW', ['DOWN', 'LEFT', 'DOWN'])):
            choices[name][cohort] = [dict(root_id=root['root_id'], mode=mode, canonical_action=actions[i] if mode == 'TREE' else 'DOWN', fallback=False)
                                     for i, root in enumerate(roots[cohort]) for mode in ('TREE', 'ONE', 'FALLBACK')]
    models = {name: dict(nodes=[dict(kind='leaf')], candidate_records=[]) for name in ('STRUCTURE', 'RAW')}
    expected = runner.summarize(roots, labels, choices, models); actual = audit.summarize(roots, labels, choices, models)
    assert audit.previous._equal(actual, expected) and audit.previous._equal(expected, actual)
    contrast = actual['structure_minus_raw']['SOURCE']
    assert contrast['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(1/3)
    assert contrast['aggregates']['DESIGN_GROUP_MEAN']['utility'] == pytest.approx(.25)
    assert contrast['diagnostics'] == dict(improved_roots=1, worsened_roots=1, equal_value_roots=1, action_changes=3,
                                           new_positive_regret_roots=1, resolved_positive_regret_roots=1)
    assert actual['STRUCTURE']['cohorts']['SOURCE']['aggregates']['DESIGN_GROUP_MEAN']['headroom_closed_fraction'] == pytest.approx(2/3)
