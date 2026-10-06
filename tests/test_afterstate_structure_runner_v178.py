"""Test complete-vector paired comparisons and new action-regret counts."""
import pytest
from scripts import run_controlled_predictive_afterstate_structure_v178 as runner


def fixture():
    roots = {cohort: [dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT'])]
        for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort,
        action_components={'DOWN': [1., .5, 0.], 'LEFT': [1., 0., .5]})]
        for cohort in ('SOURCE', 'TARGET')}
    choices = {}
    for name, selected in (('STRUCTURE', 'LEFT'), ('RAW', 'DOWN')):
        choices[name] = {cohort: [dict(root_id=cohort, mode=mode, canonical_action=action, fallback=False)
            for mode, action in (('TREE', selected), ('ONE', 'DOWN'), ('FALLBACK', 'DOWN'))]
            for cohort in ('SOURCE', 'TARGET')}
    models = {name: dict(nodes=[dict(kind='leaf')], candidate_records=[])
        for name in ('STRUCTURE', 'RAW')}
    return roots, labels, choices, models


def test_structure_raw_difference_preserves_all_components_and_resolved_regret():
    summary = runner.summarize(*fixture())
    target = summary['structure_minus_raw']['TARGET']
    assert target['aggregates']['ROOT_MEAN']['components'] == [0., -.5, .5]
    assert target['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(1.)
    assert target['diagnostics']['resolved_positive_regret_roots'] == 1
    assert target['diagnostics']['new_positive_regret_roots'] == 0
    assert summary['STRUCTURE']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']['headroom_closed_fraction'] == pytest.approx(1.)


def test_new_regret_is_distinct_from_harmless_action_ties():
    roots, labels, choices, models = fixture()
    choices['STRUCTURE'], choices['RAW'] = choices['RAW'], choices['STRUCTURE']
    result = runner.summarize(roots, labels, choices, models)['structure_minus_raw']['TARGET']
    assert result['diagnostics']['new_positive_regret_roots'] == 1
    assert result['aggregates']['ROOT_MEAN']['utility'] == pytest.approx(-1.)
    for rows in labels.values():
        rows[0]['action_components']['LEFT'] = list(rows[0]['action_components']['DOWN'])
    ties = runner.summarize(roots, labels, choices, models)['structure_minus_raw']['TARGET']
    assert ties['diagnostics']['action_changes'] == 1
    assert ties['diagnostics']['new_positive_regret_roots'] == 0
    assert ties['diagnostics']['equal_value_roots'] == 1
