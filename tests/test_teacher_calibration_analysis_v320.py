"""Teacher bias direction, paired units, fixed-grid endpoints and HOLD behavior."""
import pytest

from acfqp.science.teacher_calibration_analysis_v320 import GROUP_INDICES, PRIMARY, summarize


def cohort():
    rows = []
    for life in range(16):
        initial, stages = {}, {'1':{}, '2':{}}
        for task in ('A', 'B'):
            teacher = dict(file=f'v317/life_{life}/{task}/FIRST_LOCAL_v0.npz', version=0)
            initial[task] = dict(teacher_version=teacher, planning_belief=dict(estimated_p_four=.1 if task == 'A' else .5))
            for number in ('1', '2'):
                arms = {}
                for arm in ('FACTUAL_LOCAL', 'QUERY_LOCAL'):
                    groups = []
                    for index in GROUP_INDICES:
                        replicas = []
                        for member in range(4):
                            reward = 1.+member
                            replicas.append(dict(teacher_reward=reward+(.5 if arm == 'QUERY_LOCAL' else .25),
                                teacher_win=.75 if arm == 'QUERY_LOCAL' else .5,
                                actual_reward=reward, actual_win=0, status='LOST',
                                seed=320000000000+life*1000000+int(number)*100000+(10000 if task == 'B' else 0)+index*4+member,
                                score=reward*2048., actions=member+1, new_raw_tiles=member))
                        groups.append(dict(index=index, replicas=replicas))
                    arms[arm] = dict(groups=groups)
                stages[number][task] = dict(teacher_version=teacher, teacher_unchanged=True,
                    groups=64, replicas=4, selected_group_indices=GROUP_INDICES.copy(), arms=arms)
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial, stages=stages))
    return rows


def replicas(row, task=None, number=None, arm=None):
    for r in ((number,) if number else ('1', '2')):
        for t in ((task,) if task else ('A', 'B')):
            for a in ((arm,) if arm else ('FACTUAL_LOCAL', 'QUERY_LOCAL')):
                for group in row['stages'][r][t]['arms'][a]['groups']:
                    yield from group['replicas']


def test_teacher_minus_terminal_direction_combined_rule_and_fixed_grid_counts():
    result = summarize(cohort(), draws=40)
    assert result['primary_contrast'] == PRIMARY
    assert result['primary']['mean'] == 2.25
    assert result['primary']['ci95'] == [2.25, 2.25]
    assert result['primary_status'] == 'SUPPORTED_MORE_OPTIMISTIC'
    assert result['differential_teacher_bias_supported']
    assert result['overall']['query_minus_factual']['reward']['mean'] == .25
    assert result['overall']['query_minus_factual']['win']['mean'] == .25
    assert result['overall']['own_signed_bias']['QUERY_LOCAL']['combined']['mean'] == 6.5
    assert result['overall']['own_signed_bias']['FACTUAL_LOCAL']['combined']['mean'] == 4.25
    assert result['physical_conditional_rollouts'] == 32768 and result['complete_terminal_endpoints']
    assert result['selected_group_indices'] == GROUP_INDICES
    assert result['selected_group_indices'][0] == 0 and result['selected_group_indices'][-1] == 16383
    assert result['bootstrap_seed'] == 32000001 and result['bootstrap_draws'] == 40
    assert result['bootstrap_unit'] == 'PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT'
    assert result['secondary_interval_scope'].startswith('NOMINAL_95')
    assert 'not an optimal-value error' in result['evidence_scope']
    assert 'No new fitting, learning benefit or causal explanation' in result['evidence_scope']


def test_equal_member_rootgroup_task_and_round_weights_keep_rare_cell_in_primary():
    rows = cohort()
    for row in rows:
        for replica in replicas(row, task='B', number='2', arm='QUERY_LOCAL'):
            replica['teacher_reward'] += 8.
    result = summarize(rows, draws=20)
    assert result['primary']['mean'] == 4.25
    assert result['by_task']['A']['query_minus_factual']['combined']['mean'] == 2.25
    assert result['by_task']['B']['query_minus_factual']['combined']['mean'] == 6.25
    assert result['by_round']['1']['query_minus_factual']['combined']['mean'] == 2.25
    assert result['by_round']['2']['query_minus_factual']['combined']['mean'] == 6.25
    assert result['by_stage']['R2_B']['query_minus_factual']['combined']['mean'] == 10.25


def test_pessimistic_difference_and_components_cancel_without_learning_gain_claim():
    rows = cohort()
    for row in rows:
        for replica in replicas(row, arm='QUERY_LOCAL'):
            replica['teacher_reward'] -= 3.
    result = summarize(rows, draws=20)
    assert result['primary_status'] == 'SUPPORTED_MORE_PESSIMISTIC'
    assert result['primary']['mean'] == -.75
    assert result['overall']['query_minus_factual']['win']['status95'] == 'SUPPORTED_MORE_OPTIMISTIC'
    assert result['overall']['own_signed_bias']['QUERY_LOCAL']['combined']['status95'] == 'SUPPORTED_OPTIMISTIC_BIAS'
    for row in rows:
        for replica in replicas(row, arm='QUERY_LOCAL'):
            replica['teacher_reward'] += .75
    result = summarize(rows, draws=20)
    assert result['primary_status'] == 'UNRESOLVED' and not result['differential_teacher_bias_supported']
    assert result['overall']['query_minus_factual']['reward']['mean'] == -2.
    assert result['overall']['query_minus_factual']['win']['mean'] == .25


def test_centered_replica_dispersion_is_separate_from_signed_bias_and_root_heterogeneity():
    rows = cohort()
    for row in rows:
        for number in ('1', '2'):
            for task in ('A', 'B'):
                for group in row['stages'][number][task]['arms']['QUERY_LOCAL']['groups']:
                    for member, replica in enumerate(group['replicas']):
                        replica['teacher_reward'] += group['index']+(-1. if member < 2 else 1.)
    result = summarize(rows, draws=20)
    calibration = result['by_lifecycle'][0]['cells']['R1_A']['QUERY_LOCAL']
    assert calibration['centered_replica_error_rms']['reward'] == 1.
    assert calibration['centered_replica_error_rms']['combined'] == 1.
    assert calibration['centered_replica_error_rms']['win'] == 0.
    assert calibration['rms_error']['reward'] > calibration['centered_replica_error_rms']['reward']
    assert 'NOT_EXACT_POPULATION_VARIANCE' in result['centered_replica_error_definition']


def test_one_cutoff_retains_every_observation_and_holds_all_terminal_bias_inference():
    rows = cohort()
    group = rows[6]['stages']['2']['B']['arms']['QUERY_LOCAL']['groups'][9]
    replica = group['replicas'][3]
    replica.update(status='CUTOFF', actual_win=None, actual_reward=None, score=204800.)
    result = summarize(rows, draws=20)
    assert not result['complete_terminal_endpoints']
    assert result['physical_conditional_rollouts'] == 32768 and len(result['by_lifecycle']) == 16
    assert result['primary_status'] == 'HOLD_CUTOFF' and not result['differential_teacher_bias_supported']
    assert result['cutoffs'] == [dict(lifecycle=6, task='B', round=2, arm='QUERY_LOCAL',
        group_index=group['index'], member=3, seed=replica['seed'])]
    assert result['primary'] is None and not result['bootstrap_executed']
    assert all(result[key] is None for key in ('overall', 'by_task', 'by_round', 'by_stage'))
    assert result['by_lifecycle'][6]['cells']['R2_B']['QUERY_LOCAL'] is None
    assert result['by_lifecycle'][6]['retained_endpoint_counts']['R2_B']['QUERY_LOCAL'] == dict(rootgroups=64, replicas=256, cutoff=1)


def test_fixed_parent_bootstrap_does_not_resample_source_population():
    rows = cohort()
    for row in rows:
        for replica in replicas(row, arm='QUERY_LOCAL'):
            replica['teacher_reward'] += row['parent']
    result = summarize(list(reversed(rows)), draws=40)
    assert result['primary']['mean'] == 3.75 and result['primary']['ci95'] == [3.75, 3.75]
    assert result['primary']['parent_mean_values'] == {str(parent):2.25+parent for parent in range(4)}
    assert result['primary']['interval_scope'].endswith('64_FIXED_EQUIDISTANT_V319_ROOTGROUPS')


@pytest.mark.parametrize('case', ['teacher', 'grid', 'member', 'root', 'seed', 'reward', 'win', 'endpoint', 'cutoff_truth'])
def test_changed_teacher_grid_pairing_or_terminal_contract_is_rejected(case):
    rows = cohort()
    stage = rows[0]['stages']['2']['B']
    groups = stage['arms']['QUERY_LOCAL']['groups']
    replica = groups[0]['replicas'][0]
    if case == 'teacher':
        stage['teacher_version'] = dict(stage['teacher_version'], file='v319/query_updated_v2.npz')
        message = 'immutable FIRST teacher'
    elif case == 'grid':
        stage['selected_group_indices'] = list(range(64))
        message = 'equidistant rootgroup indices'
    elif case == 'member':
        groups[0]['replicas'].pop()
        message = 'complete paired rootgroup'
    elif case == 'root':
        groups.pop()
        message = 'complete paired rootgroup'
    elif case == 'seed':
        replica['seed'] += 1
        message = 'paired suffix seeds'
    elif case == 'reward':
        replica['actual_reward'] += 1.
        message = 'terminal reward includes'
    elif case == 'win':
        replica['actual_win'] = 1
        message = 'terminal WIN labels'
    elif case == 'endpoint':
        replica['status'] = 'ACTIVE'
        message = 'explicit natural or cutoff'
    else:
        replica['status'] = 'CUTOFF'
        message = 'no fabricated terminal reward'
    with pytest.raises(ValueError, match=message):
        summarize(rows, draws=2)


def test_missing_lifecycle_does_not_create_an_outcome_selected_subset():
    with pytest.raises(ValueError, match='all sixteen FIRST lifecycles'):
        summarize(cohort()[:-1], draws=2)
