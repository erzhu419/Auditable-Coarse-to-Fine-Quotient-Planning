"""SOURCE-only selection metadata and complete-vector target comparisons."""
from copy import deepcopy

import pytest
from scripts import run_controlled_predictive_source_regularization_v183 as runner


def fixture():
    roots = {cohort: [dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT'])]
             for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort, action_components={
        'DOWN': [1., .5, 0.], 'LEFT': [1., 0., .5]})] for cohort in roots}
    choices = {name: {cohort: [dict(root_id=cohort, mode=mode,
        canonical_action=action, fallback=False, decision=dict(coverage={
            'DOWN': dict(known_tokens=40, unknown_tokens=0, total_tokens=40),
            'LEFT': dict(known_tokens=39, unknown_tokens=1, total_tokens=40)}))
        for mode, action in (('TREE', 'LEFT' if name == 'RIDGE' else 'DOWN'),
                             ('ONE', 'DOWN'), ('FALLBACK', 'DOWN'))] for cohort in roots}
        for name in ('RIDGE', 'LAYOUT', 'SHARED', 'RAW')}
    selection = dict(selected_lambda=.01, candidates=[dict(lambda_value=.01,
        utility=.25, group_records=[dict(source_id='fit_group', utility=.25)])])
    return roots, labels, choices, selection


def test_summary_keeps_SOURCE_selection_separate_from_TARGET_action_utility():
    summary = runner.summarize(*fixture())
    assert summary['selected_lambda'] == .01
    assert summary['source_selection'][0]['utility'] == .25
    row = summary['ridge_minus_layout']['TARGET']
    assert row['aggregates']['ROOT_MEAN']['components'] == [0., -.5, .5]
    assert row['aggregates']['ROOT_MEAN']['utility'] == 1.
    assert row['diagnostics']['resolved_positive_regret_roots'] == 1
    assert summary['RIDGE']['model_kind'] == 'RIDGE'
    assert 'learned_splits' not in summary['RIDGE']
    assert summary['feature_coverage']['TARGET']['unknown_tokens'] == 1
    assert summary['new_predictors_fitted'] == 13


def test_design_group_mean_is_not_replaced_with_root_weighted_selection():
    roots, labels, choices, selection = fixture()
    for number, gain in ((1, 1.), (2, 4.)):
        root = dict(root_id=f'SOURCE:{number}', source_id=f'design:{number//2}',
                    legal_actions=['DOWN', 'LEFT'])
        roots['SOURCE'].append(root)
        labels['SOURCE'].append(dict(root_id=root['root_id'], action_components={
            'DOWN': [0., 0., 0.], 'LEFT': [gain, 0., 0.]}))
        for rows in choices.values():
            rows['SOURCE'].extend(dict(deepcopy(row), root_id=root['root_id'])
                                  for row in rows['SOURCE'][:3])
    comparison = runner.summarize(roots, labels, choices, selection)['ridge_minus_layout']['SOURCE']
    assert comparison['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(2.)
    assert comparison['aggregates']['DESIGN_GROUP_MEAN']['utility'] == pytest.approx(2.5)
