"""Vector comparisons and SOURCE vocabulary coverage, without physical games."""
from copy import deepcopy

import pytest
from scripts import run_controlled_predictive_rank_layout_consequences_v182 as runner


def fixture():
    roots = {cohort: [dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT'])]
             for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort, action_components={
        'DOWN': [1., .5, 0.], 'LEFT': [1., 0., .5]})] for cohort in roots}
    choices = {name: {cohort: [dict(root_id=cohort, mode=mode,
        canonical_action=action, fallback=False, decision=dict(coverage={
            'DOWN': dict(known_tokens=40, unknown_tokens=0, total_tokens=40),
            'LEFT': dict(known_tokens=38, unknown_tokens=2, total_tokens=40)}))
        for mode, action in (('TREE', 'LEFT' if name == 'LAYOUT' else 'DOWN'),
                             ('ONE', 'DOWN'), ('FALLBACK', 'DOWN'))] for cohort in roots}
        for name in ('LAYOUT', 'SHARED', 'RAW', 'STRUCTURE')}
    return roots, labels, choices


def test_relative_full_vector_benefit_is_not_only_reward_or_tree_growth():
    summary = runner.summarize(*fixture())
    comparison = summary['layout_minus_shared']['TARGET']
    assert comparison['aggregates']['ROOT_MEAN']['components'] == [0., -.5, .5]
    assert comparison['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(1.)
    assert comparison['diagnostics']['resolved_positive_regret_roots'] == 1
    assert summary['LAYOUT']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']['headroom_closed_fraction'] == 1.
    assert summary['LAYOUT']['model_kind'] == 'LAYOUT'
    assert 'learned_splits' not in summary['LAYOUT']
    assert summary['new_predictors_fitted'] == 1


def test_coverage_counts_all_legal_action_tokens_and_ignores_baseline_rows():
    choices = fixture()[2]['LAYOUT']
    coverage = runner.feature_coverage(choices)['TARGET']
    assert {key: coverage[key] for key in ('roots', 'actions', 'known_tokens', 'unknown_tokens',
           'total_tokens', 'roots_all_tokens_seen')} == dict(roots=1, actions=2,
           known_tokens=78, unknown_tokens=2, total_tokens=80, roots_all_tokens_seen=0)
    assert coverage['root_records'][0]['all_tokens_seen'] is False


def test_design_group_mean_remains_distinct_from_root_mean():
    roots, labels, choices = fixture()
    for number, gain in ((1, 1.), (2, 4.)):
        root = dict(root_id=f'SOURCE:{number}', source_id=f'design:{number//2}',
                    legal_actions=['DOWN', 'LEFT'])
        roots['SOURCE'].append(root)
        labels['SOURCE'].append(dict(root_id=root['root_id'], action_components={
            'DOWN': [0., 0., 0.], 'LEFT': [gain, 0., 0.]}))
        for rows in choices.values():
            rows['SOURCE'].extend(dict(deepcopy(row), root_id=root['root_id'])
                                  for row in rows['SOURCE'][:3])
    comparison = runner.summarize(roots, labels, choices)['layout_minus_shared']['SOURCE']
    assert comparison['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(2.)
    assert comparison['aggregates']['DESIGN_GROUP_MEAN']['utility'] == pytest.approx(2.5)
