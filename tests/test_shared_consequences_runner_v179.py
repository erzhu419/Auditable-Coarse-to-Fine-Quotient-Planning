"""Full-vector comparisons and the optimistic feature-alias ceiling."""
import pytest
from scripts import run_controlled_predictive_shared_consequences_v179 as runner


def fixture():
    roots = {cohort: [dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT'],
        immediate_rewards={'DOWN': 0., 'LEFT': 0.},
        action_features={'DOWN': [0, 1, 0, 0, 0, 0], 'LEFT': [0, 2, 0, 0, 0, 0]})]
        for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort,
        action_components={'DOWN': [1., .5, 0.], 'LEFT': [1., 0., .5]})]
        for cohort in ('SOURCE', 'TARGET')}
    choices = {name: {cohort: [dict(root_id=cohort, mode=mode, canonical_action=action, fallback=False)
        for mode, action in (('TREE', selected), ('ONE', 'DOWN'), ('FALLBACK', 'DOWN'))]
        for cohort in ('SOURCE', 'TARGET')}
        for name, selected in (('SHARED', 'LEFT'), ('STRUCTURE', 'DOWN'), ('RAW', 'DOWN'))}
    models = {name: dict(nodes=[dict(kind='leaf')], candidate_records=[]) for name in ('STRUCTURE', 'RAW')}
    models['SHARED'] = dict(coefficients=[[0., 0., 0.]]*6)
    return roots, labels, choices, models


def test_full_vector_contrast_and_summary_adapter_is_not_a_tree():
    summary = runner.summarize(*fixture())
    target = summary['shared_minus_raw']['TARGET']
    assert target['aggregates']['ROOT_MEAN']['components'] == [0., -.5, .5]
    assert target['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(1.)
    assert target['diagnostics']['resolved_positive_regret_roots'] == 1
    assert target['diagnostics']['new_positive_regret_roots'] == 0
    assert summary['SHARED']['model_kind'] == 'SHARED'
    assert 'learned_splits' not in summary['SHARED']
    assert 'candidate_reasons' not in summary['SHARED']
    assert summary['feature_alias']['TARGET']['aggregates']['ROOT_MEAN']['restricted_minus_one_utility'] == pytest.approx(1.)


def test_alias_bound_respects_reward_ties_and_keeps_negative_difference():
    roots, labels, choices, models = fixture()
    for cohort in ('SOURCE', 'TARGET'):
        roots[cohort][0]['action_features']['LEFT'] = list(roots[cohort][0]['action_features']['DOWN'])
        next(row for row in choices['SHARED'][cohort] if row['mode'] == 'ONE')['canonical_action'] = 'LEFT'
    summary = runner.summarize(roots, labels, choices, models)
    bound = summary['feature_alias']['TARGET']
    assert bound['aggregates']['ROOT_MEAN']['restricted_minus_one_utility'] == pytest.approx(-1.)
    assert bound['aggregates']['ROOT_MEAN']['oracle_minus_restricted'] == pytest.approx(1.)
    assert bound['diagnostics'] == dict(identical_feature_pairs=1, roots_with_alias=1,
        conflicting_continuation_pairs=1, lost_headroom_roots=1)
    row = bound['root_records'][0]
    assert row['restricted_action'] == 'DOWN'
    assert row['same_feature_pairs'][0]['continuation_components'] == [0., .5, -.5]
    # A known larger first reward determines the representative even if its exact future is worse.
    roots['TARGET'][0]['immediate_rewards']['LEFT'] = .25
    changed = runner.summarize(roots, labels, choices, models)['feature_alias']['TARGET']['root_records'][0]
    assert changed['restricted_action'] == 'LEFT'
    assert changed['same_feature_pairs'][0]['continuation_components'] == [.25, .5, -.5]


def test_alias_group_mean_does_not_reweight_unequal_groups_by_roots():
    roots, labels, choices, models = fixture()
    from copy import deepcopy
    for number, gain in ((1, 1.), (2, 4.)):
        root = deepcopy(roots['SOURCE'][0]); root.update(root_id=f'SOURCE:{number}', source_id=f'design:{number//2}')
        roots['SOURCE'].append(root)
        labels['SOURCE'].append(dict(root_id=root['root_id'], action_components={'DOWN': [0., 0., 0.], 'LEFT': [gain, 0., 0.]}))
        for rows in choices.values():
            rows['SOURCE'].extend(dict(deepcopy(row), root_id=root['root_id']) for row in rows['SOURCE'][:3])
    result = runner.summarize(roots, labels, choices, models)['feature_alias']['SOURCE']
    assert result['aggregates']['ROOT_MEAN']['restricted_minus_one_utility'] == pytest.approx(2.)
    assert result['aggregates']['DESIGN_GROUP_MEAN']['restricted_minus_one_utility'] == pytest.approx(2.5)
