"""Independent fixed choices and SOURCE-weighted paired suffix inference."""
from copy import deepcopy
from statistics import mean, variance

import pytest

from acfqp.science import controlled_predictive_fixed_board_replication_v175 as core
from scripts import analyze_controlled_predictive_fixed_board_replication_v175 as audit
from test_confirmed_partition_core_v173 import leaf

ROWS = []


def fixture():
    models = {}
    for life in audit.LIVES:
        tree = dict(life=life, mode='PART_UTILITY_UNPRUNED', nodes=[dict(node_id=0, kind='leaf', leaf_id=0)],
            groups={}, leaves=[leaf(0, 'LEFT')])
        one = dict(life=life, mode='ONE_LATE', nodes=[], groups={'ALL': 0}, leaves=[leaf(0, 'DOWN')])
        models[life] = dict(TREE=tree, ONE=one)
    roots = []
    for cohort, sources in (('TRAIN', 12), ('FRESH', 8)):
        for life in audit.LIVES:
            ordinal = 0
            for source in range(sources):
                # Half the SOURCE denominators include an unsampled, same-action root.
                for index in range(1 + source % 2):
                    source_id = f'{cohort}:{life}:{source:02}'
                    roots.append(dict(cohort=cohort, root_id=f'{source_id}:{index}', life=life, source_id=source_id,
                        ordinal=ordinal, canonical_board=[1] + [0] * 15, legal_actions=['DOWN', 'LEFT'],
                        immediate_rewards={'DOWN': 2. if index else 0., 'LEFT': 0.},
                        actions=[dict(canonical_action=action, actual_action=action) for action in ('DOWN', 'LEFT')],
                        reference_trials=[dict(suffix=suffix, seed=100000 + life * 10000 + source * 100 + index * 10 + suffix,
                            action_components={'LEFT': [source + 5. + suffix % 2, 0., 1.], 'DOWN': [1., 1., 0.]}) for suffix in range(4)]))
                    ordinal += 1
    frozen = audit.freeze_selections(roots, models)
    outcomes = []
    for phase in ('TRAIN_REPL', 'FRESH_REPL'):
        for plan in audit.branch_roster(roots, frozen, phase):
            source = int(plan['source_id'].split(':')[-1])
            if plan['cohort'] == 'TRAIN':
                vector = [source + 3. + plan['suffix'] % 2, 0., 1.] if plan['canonical_action'] == 'LEFT' else [1., 1., 0.]
            else:
                vector = [0., 1., 0.] if plan['canonical_action'] == 'LEFT' else [source + 3. + plan['suffix'] % 2, 0., 1.]
            outcomes.append(dict(plan, components=vector, status='WON' if vector[2] else 'LOST'))
    return roots, models, frozen, outcomes


def test_independent_fixed_policy_support_reference_and_work_preserve_same_action_roots():
    roots, models, frozen, _ = fixture()
    assert audit._equal(core.freeze_selections(roots, models), frozen)
    assert frozen['complete'] and len(frozen['choices']) == 120
    assert sum(row['changed'] for row in frozen['choices']) == 80
    assert frozen['work']['reference_trials_read'] == 120 * 4
    assert frozen['work']['reference_terminal_vector_reads'] == 80 * 4 * 2
    assert frozen['work']['reference_same_action_suffixes_zeroed'] == 40 * 4
    assert all(row['old_difference_components'] == [0., 0., 0.] for row in frozen['choices'] if not row['changed'])
    root = deepcopy(roots[0]); root['legal_actions'] = ['DOWN']; root['immediate_rewards'] = {'DOWN': 0.}
    unsupported = deepcopy(models)
    unsupported[0]['TREE']['leaves'][0]['action_root_ids']['DOWN'] = ['a', 'b', 'c']
    expected = audit.freeze_selections([root], unsupported)
    assert audit._equal(core.freeze_selections([root], unsupported), expected)
    assert not expected['complete'] and expected['choices'][0]['decisions']['TREE']['canonical_action'] is None
    assert expected['choices'][0]['old_difference_components'] is None
    assert 'teacher_action' not in root


def test_new_old_pairing_and_cross_cohort_variance_use_all_source_root_denominators():
    _, _, frozen, rows = fixture()
    expected = audit.summarize_replication(frozen, rows)
    assert audit._equal(core.summarize_replication(frozen, rows), expected)
    assert expected['complete'] and expected['physical_outcomes'] == 80 * 16 * 2
    train_values = [(source + 4.5) / (1 + source % 2) for source in range(12)]
    fresh_values = [(-source - 5.5) / (1 + source % 2) for source in range(8)]
    train = expected['cohorts']['TRAIN']['new']['metrics']['utility']
    fresh = expected['cohorts']['FRESH']['new']['metrics']['utility']
    assert train['mean'] == pytest.approx(mean(train_values))
    assert train['source_mean_variance'] == pytest.approx(variance(train_values) / (12 * 4))
    assert fresh['mean'] == pytest.approx(mean(fresh_values))
    paired = expected['cohorts']['TRAIN']['new_minus_old']['metrics']['utility']
    assert paired['mean'] == -1.5
    assert paired['source_mean_variance'] == pytest.approx(.25 / (11 * 4))
    # Pair first: summing independent old/new variances would discard their covariance.
    old = expected['cohorts']['TRAIN']['old']['metrics']['utility']
    assert paired['source_mean_variance'] < old['source_mean_variance'] + train['source_mean_variance']
    difference = expected['cross_cohort']['new']['metrics']['utility']
    assert difference['mean'] == pytest.approx(fresh['mean'] - train['mean'])
    assert difference['source_mean_variance'] == pytest.approx(fresh['source_mean_variance'] + train['source_mean_variance'])
    assert train['conditional_suffix_mean_variance'] == pytest.approx(1. / 4608)
    assert fresh['conditional_suffix_mean_variance'] == pytest.approx(1. / 3072)
    assert old['conditional_suffix_mean_variance'] == 0.
    assert paired['conditional_suffix_mean_variance'] == train['conditional_suffix_mean_variance']
    assert difference['conditional_suffix_mean_variance'] == pytest.approx(1. / 4608 + 1. / 3072)
    assert expected['work']['source_root_component_reads'] == 3 * 3 * 120
    missing = audit.summarize_replication(frozen, rows[:-1])
    assert audit._equal(core.summarize_replication(frozen, rows[:-1]), missing)
    assert not missing['complete'] and missing['cohorts'] == {} and missing['cross_cohort'] == {}


def test_suffix_utility_variance_preserves_joint_reward_and_terminal_event_covariance():
    _, _, frozen, rows = fixture()
    rows = deepcopy(rows)
    for row in rows:
        if row['cohort']!='TRAIN':
            continue
        source = int(row['source_id'].split(':')[-1])
        if row['canonical_action']=='LEFT':
            row['components'] = [source+5., 0., 1.] if row['suffix']%2 else [source+3., 1., 0.]
        else:
            row['components'] = [1., 0., 1.]
        row['status'] = 'WON' if row['components'][2] else 'LOST'
    expected = audit.summarize_replication(frozen, rows)
    assert audit._equal(core.summarize_replication(frozen, rows), expected)
    metrics = expected['cohorts']['TRAIN']['new']['metrics']
    actual = metrics['utility']['conditional_suffix_mean_variance']
    assert actual == pytest.approx(1. / 288)
    independent_sum = sum(metrics[metric]['conditional_suffix_mean_variance'] for metric in ('reward','failure','success'))
    assert actual > independent_sum
    assert expected['work']['suffix_root_metric_variances'] == 80*4
    assert expected['work']['suffix_utility_evaluations'] == 80*16


def test_new_suffix_roster_keeps_full_root_ordinals_and_pairs_only_changed_actions():
    from scripts import run_controlled_predictive_fixed_board_replication_v175 as runner
    roots, _, frozen, rows = fixture()
    for phase in ('TRAIN_REPL', 'FRESH_REPL'):
        plans = audit.branch_roster(roots, frozen, phase)
        assert plans == runner.branch_roster(roots, frozen, phase)
        for root in roots:
            if root['cohort'] != ('TRAIN' if phase == 'TRAIN_REPL' else 'FRESH'):
                continue
            local = [plan for plan in plans if plan['root_id'] == root['root_id']]
            if root['immediate_rewards']['DOWN']:
                assert local == []
            else:
                assert len(local) == 32
                assert {plan['ordinal'] for plan in local} == {root['ordinal']}
                for suffix in range(16):
                    pair = [plan for plan in local if plan['suffix'] == suffix]
                    assert len(pair) == 2 and pair[0]['seed'] == pair[1]['seed'] == audit.seed(phase, root, suffix)
                assert len({plan['seed'] for plan in local}) == 16
                assert {plan['seed'] for plan in local}.isdisjoint(trial['seed'] for trial in root['reference_trials'])
    assert audit.seed('TRAIN_REPL', roots[0], 0) != audit.seed('FRESH_REPL', roots[0], 0)
    assert len(rows) == 2560 and ROWS == []
