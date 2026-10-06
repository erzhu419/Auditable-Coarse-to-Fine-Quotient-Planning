"""Check observable freezing and informative exact headroom arithmetic."""
from copy import deepcopy
import pytest
from scripts import run_controlled_predictive_exact_h3_v177 as runner


def fixture():
    roots = {cohort: [dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT'])]
        for cohort in ('SOURCE', 'TARGET')}
    labels = {cohort: [dict(root_id=cohort, action_components={'DOWN': [1., .5, 0.], 'LEFT': [1., 0., .5]})]
        for cohort in ('SOURCE', 'TARGET')}
    choices = {cohort: [dict(root_id=cohort, mode=mode, canonical_action=action, fallback=False)
        for mode, action in (('TREE', 'LEFT'), ('ONE', 'DOWN'), ('FALLBACK', 'DOWN'))]
        for cohort in ('SOURCE', 'TARGET')}
    models = {'TREE': dict(nodes=[dict(kind='leaf')], candidate_records=[])}
    return roots, labels, choices, models


def test_complete_vector_headroom_and_signed_improvement():
    data = fixture(); before = deepcopy(data)
    summary = runner.summarize(*data)
    stat = summary['cohorts']['TARGET']['aggregates']['ROOT_MEAN']
    assert stat['headroom'] == pytest.approx(1.)
    assert stat['tree_minus_one'] == pytest.approx(1.)
    assert stat['headroom_closed_fraction'] == pytest.approx(1.)
    assert stat['metrics']['ORACLE']['components'] == [1., 0., .5]
    assert data == before


def test_no_headroom_is_uninformative_even_when_actions_differ():
    roots, labels, choices, models = fixture()
    for rows in labels.values():
        rows[0]['action_components']['LEFT'] = [1., .5, 0.]
    summary = runner.summarize(roots, labels, choices, models)
    stat = summary['cohorts']['TARGET']['aggregates']['ROOT_MEAN']
    assert not stat['informative'] and stat['headroom_closed_fraction'] is None
    diagnostics = summary['cohorts']['TARGET']['diagnostics']
    assert diagnostics['tree_one_action_changes'] == 1
    assert diagnostics['tree_same_value_roots'] == 1
    assert diagnostics['positive_regret_roots']['TREE'] == 0


def test_label_action_transport_and_reward_binding():
    root = dict(root_id='r', action_map={'DOWN': 'LEFT', 'LEFT': 'UP'},
        immediate_rewards={'DOWN': .5, 'LEFT': 0.})
    native = dict(status='ACTIVE', horizon=3, legal_actions=['LEFT', 'UP'],
        immediate_rewards={'LEFT': .5, 'UP': 0.}, action_components={'LEFT': [.7, 0., .2], 'UP': [.1, .3, 0.]},
        root_cell=7, root_index=2, teacher_action='UP')
    label = runner.canonical_labels(root, native, {'query': runner.QUERY})
    assert label['action_components']['DOWN'] == [.7, 0., .2]
    assert label['action_components']['LEFT'] == [.1, .3, 0.]
    assert 'suffix_trials' not in label
    native['immediate_rewards']['LEFT'] = .6
    with pytest.raises(ValueError, match='reward'):
        runner.canonical_labels(root, native, {})
