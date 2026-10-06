"""Brier direction, root/member distinction, exact snapshots and cutoff retention."""
import pytest

from acfqp.science.win_terminal_analysis_v325 import (
    BOOTSTRAP_SEED, CONTINUATION_SEED, GROUP_INDICES, PRIMARY, summarize,
)


def cohort():
    rows = []
    for life in range(16):
        initial, stages = {}, {'1': {}, '2': {}}
        for task in ('A', 'B'):
            teacher = dict(lifecycle=life, parent=life % 4, context_id=0 if task == 'A' else 1,
                file=f'v324/life_{life}/{task}/FIRST_LOCAL_v0.npz', arm='FIRST_LOCAL', version=0, base_file=None)
            initial[task] = dict(teacher_version=teacher,
                planning_belief=dict(estimated_p_four=.1 if task == 'A' else .5))
            versions = {}
            for arm in ('FACTUAL_WIN', 'QUERY_WIN'):
                v1 = dict(teacher, file=f'v324/life_{life}/{task}/{arm}_v1.npz', arm=arm, version=1,
                    base_file=teacher['file'])
                v2 = dict(v1, file=f'v324/life_{life}/{task}/{arm}_v2.npz', version=2, base_file=v1['file'])
                versions[arm] = (v1, v2)
            for number in ('1', '2'):
                arms = {}
                for arm in ('FACTUAL_WIN', 'QUERY_WIN'):
                    v1, v2 = versions[arm]
                    final_probability = .5 if arm == 'QUERY_WIN' else .125
                    groups = []
                    for index in GROUP_INDICES:
                        replicas = [dict(teacher_win=.75 if arm == 'QUERY_WIN' else .5,
                            actual_win=0, status='LOST',
                            seed=CONTINUATION_SEED+life*10000000+(1000000 if task == 'B' else 0)
                                +int(number)*100000+index*4+member,
                            score=2048, actions=member+1, new_raw_tiles=member) for member in range(4)]
                        groups.append(dict(index=index, predictions=dict(FIRST=.25,
                            before=.25 if number == '1' else final_probability,
                            after=final_probability, FINAL=final_probability), replicas=replicas))
                    arms[arm] = dict(groups=groups, prediction_versions=dict(FIRST=teacher,
                        before=teacher if number == '1' else v1, after=v1 if number == '1' else v2, FINAL=v2))
                stages[number][task] = dict(teacher_version=teacher, teacher_unchanged=True,
                    groups=64, replicas=4, selected_group_indices=GROUP_INDICES.copy(), arms=arms)
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial, stages=stages))
    return rows


def groups(rows, arm='QUERY_WIN', task=None, number=None):
    for row in rows:
        for r in ((number,) if number else ('1', '2')):
            for t in ((task,) if task else ('A', 'B')):
                yield from row['stages'][r][t]['arms'][arm]['groups']


def test_primary_brier_direction_and_separate_member_teacher_calibration():
    result = summarize(cohort(), draws=30)
    assert result['primary_contrast'] == PRIMARY
    assert result['primary']['mean'] == .1875
    assert result['primary']['ci95'] == [.1875, .1875]
    assert result['primary_status'] == 'SUPPORTED_WORSE_PREDICTION'
    assert result['updated_prediction_worse_supported'] and not result['updated_prediction_better_supported']
    overall = result['overall']
    assert overall['root_prediction']['QUERY_WIN']['FIRST']['signed_bias']['mean'] == .25
    assert overall['root_prediction']['QUERY_WIN']['FINAL']['signed_bias']['mean'] == .5
    assert overall['member_teacher']['QUERY_WIN']['signed_bias']['mean'] == .75
    assert overall['member_teacher']['QUERY_WIN']['brier']['mean'] == .5625
    assert overall['root_brier_change']['FACTUAL_WIN']['FINAL_minus_FIRST']['mean'] == -.046875
    assert overall['root_brier_change']['FACTUAL_WIN']['FINAL_minus_FIRST']['status95'] == 'SUPPORTED_BETTER_PREDICTION'
    assert result['physical_conditional_rollouts'] == 32768 and result['complete_terminal_endpoints']
    assert result['bootstrap_seed'] == BOOTSTRAP_SEED and result['bootstrap_draws'] == 30
    assert result['continuation_seed'] == CONTINUATION_SEED
    assert 'member information unavailable' in result['evidence_scope']
    assert 'whole-game utility or a causal explanation' in result['evidence_scope']


def test_better_prediction_and_exact_zero_are_not_interpreted_as_learning_utility():
    rows = cohort()
    for group in groups(rows):
        group['predictions']['FINAL'] = .0
    for group in groups(rows, number='2'):
        group['predictions']['after'] = .0
    result = summarize(rows, draws=20)
    assert result['primary']['mean'] == -.0625
    assert result['primary_status'] == 'SUPPORTED_BETTER_PREDICTION' and result['updated_prediction_better_supported']
    for group in groups(rows):
        group['predictions']['FINAL'] = .25
    for group in groups(rows, number='2'):
        group['predictions']['after'] = .25
    result = summarize(rows, draws=20)
    assert result['primary']['mean'] == 0.
    assert result['primary_status'] == 'UNRESOLVED'
    assert not result['updated_prediction_worse_supported'] and not result['updated_prediction_better_supported']


def test_round_task_and_member_weights_keep_a_single_changed_cell():
    rows = cohort()
    for group in groups(rows, task='B', number='2'):
        group['predictions'].update(FINAL=1., after=1.)
    result = summarize(rows, draws=20)
    assert result['primary']['mean'] == .375
    assert result['by_task']['A']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .1875
    assert result['by_task']['B']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .5625
    assert result['by_round']['1']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .1875
    assert result['by_round']['2']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .5625
    assert result['by_stage']['R2_B']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .9375
    # One of four member wins is weighted 1/4, never substituted by majority truth.
    for group in groups(rows, task='A', number='1'):
        group['replicas'][0].update(actual_win=1, status='WON')
    result = summarize(rows, draws=20)
    cell = result['by_stage']['R1_A']
    assert cell['terminal_win_rate']['QUERY_WIN']['mean'] == .25
    assert cell['root_prediction']['QUERY_WIN']['FIRST']['brier']['mean'] == .1875
    assert cell['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .0625


def test_own_before_after_error_is_separate_from_final_vs_first():
    result = summarize(cohort(), draws=20)
    assert result['by_round']['1']['root_brier_change']['QUERY_WIN']['after_minus_before']['mean'] == .1875
    assert result['by_round']['2']['root_brier_change']['QUERY_WIN']['after_minus_before']['mean'] == 0.
    assert result['overall']['root_brier_change']['QUERY_WIN']['after_minus_before']['mean'] == .09375
    assert result['overall']['root_signed_bias_change']['QUERY_WIN']['after_minus_before']['mean'] == .125
    assert result['overall']['root_signed_bias_change']['QUERY_WIN']['FINAL_minus_FIRST']['mean'] == .25


def test_first_root_error_can_be_pessimistic_with_individually_optimistic_teacher():
    rows = cohort()
    for group in groups(rows):
        for member, replica in enumerate(group['replicas']):
            replica.update(actual_win=int(member < 2), status='WON' if member < 2 else 'LOST')
    result = summarize(rows, draws=20)
    assert result['overall']['root_prediction']['QUERY_WIN']['FIRST']['signed_bias']['mean'] == -.25
    assert result['overall']['root_prediction']['QUERY_WIN']['FIRST']['signed_bias']['status95'] == 'SUPPORTED_PESSIMISTIC_BIAS'
    assert result['overall']['member_teacher']['QUERY_WIN']['signed_bias']['mean'] == .25
    assert result['primary']['mean'] == -.0625


def test_bootstrap_keeps_fixed_parent_weights_and_exact_pairing():
    rows = cohort()
    for row in rows:
        final = .125*(row['parent']+1)
        for group in groups([row]):
            group['predictions']['FINAL'] = final
        for group in groups([row], number='2'):
            group['predictions']['after'] = final
    result = summarize(list(reversed(rows)), draws=40)
    expected = {str(parent): (.125*(parent+1))**2-.25**2 for parent in range(4)}
    mean = sum(expected.values())/4
    assert result['primary']['parent_mean_values'] == expected
    assert result['primary']['mean'] == mean and result['primary']['ci95'] == [mean, mean]
    assert result['bootstrap_unit'].startswith('PAIRED_EXISTING_V324_TARGET_LEARNING_LIFECYCLE')
    assert result['primary']['interval_scope'].endswith('64_FIXED_EQUIDISTANT_V324_ROOTGROUPS')


def test_one_cutoff_retains_all_outcomes_and_holds_all_terminal_statistics(monkeypatch):
    rows = cohort()
    group = rows[7]['stages']['2']['B']['arms']['QUERY_WIN']['groups'][9]
    replica = group['replicas'][3]
    replica.update(status='CUTOFF', actual_win=None)
    def no_bootstrap(*_):
        pytest.fail('A cutoff must not execute any bootstrap')
    monkeypatch.setattr('acfqp.science.win_terminal_analysis_v325._samples', no_bootstrap)
    result = summarize(rows, draws=20)
    assert result['primary_status'] == 'HOLD_CUTOFF'
    assert result['primary'] is None and not result['bootstrap_executed']
    assert all(result[name] is None for name in ('overall', 'by_task', 'by_round', 'by_stage'))
    assert result['physical_conditional_rollouts'] == 32768 and len(result['by_lifecycle']) == 16
    assert result['by_lifecycle'][7]['cells']['R2_B']['QUERY_WIN'] is None
    assert result['by_lifecycle'][0]['cells']['R1_A']['FACTUAL_WIN'] is None
    assert result['by_lifecycle'][7]['retained_endpoint_counts']['R2_B']['QUERY_WIN'] == dict(
        rootgroups=64, replicas=256, WON=0, LOST=255, CUTOFF=1)
    assert result['cutoffs'] == [dict(lifecycle=7, task='B', round=2, arm='QUERY_WIN',
        group_index=group['index'], member=3, seed=replica['seed'])]


@pytest.mark.parametrize('case', ['teacher', 'grid', 'member', 'root', 'seed', 'both_old_seeds', 'win',
    'endpoint', 'cutoff_truth', 'probability', 'teacher_probability', 'before_prediction', 'final_prediction',
    'after_version', 'final_version', 'own_lineage', 'bank', 'missing_snapshot'])
def test_changed_grid_outcome_probability_or_snapshot_contract_is_rejected(case):
    rows = cohort()
    stage = rows[0]['stages']['2']['B']
    item = stage['arms']['QUERY_WIN']
    group = item['groups'][0]
    replica = group['replicas'][0]
    if case == 'teacher':
        stage['teacher_version'] = dict(stage['teacher_version'], file='updated_teacher.npz')
        message = 'immutable FIRST teacher'
    elif case == 'grid':
        stage['selected_group_indices'] = list(range(64))
        message = 'equidistant rootgroup indices'
    elif case == 'member':
        group['replicas'].pop()
        message = 'complete paired rootgroup'
    elif case == 'root':
        item['groups'].pop()
        message = 'complete paired rootgroup'
    elif case in ('seed', 'both_old_seeds'):
        replica['seed'] += 1
        if case == 'both_old_seeds':
            stage['arms']['FACTUAL_WIN']['groups'][0]['replicas'][0]['seed'] += 1
        message = 'declared fresh suffix seed'
    elif case == 'win':
        replica['actual_win'] = 1
        message = 'terminal WIN labels'
    elif case == 'endpoint':
        replica['status'] = 'ACTIVE'
        message = 'explicit natural or cutoff'
    elif case == 'cutoff_truth':
        replica['status'] = 'CUTOFF'
        message = 'no fabricated terminal WIN'
    elif case in ('probability', 'teacher_probability'):
        if case == 'probability':
            group['predictions']['FIRST'] = 1.1
        else:
            replica['teacher_win'] = float('nan')
        message = 'finite WIN probabilities'
    elif case == 'before_prediction':
        rows[0]['stages']['1']['B']['arms']['QUERY_WIN']['groups'][0]['predictions']['before'] = .1
        message = 'identical saved snapshots'
    elif case == 'final_prediction':
        group['predictions']['FINAL'] = .1
        message = 'identical saved snapshots'
    elif case == 'after_version':
        item['prediction_versions']['after'] = dict(item['prediction_versions']['after'], version=1)
        message = 'declared own checkpoints'
    elif case == 'final_version':
        item['prediction_versions']['FINAL'] = dict(item['prediction_versions']['FINAL'], arm='FACTUAL_WIN')
        message = 'declared own checkpoints'
    elif case == 'own_lineage':
        item['prediction_versions']['before'] = dict(item['prediction_versions']['before'], file='different_v1.npz')
        message = 'saved own update lineage'
    elif case == 'bank':
        item['prediction_versions']['before'] = dict(item['prediction_versions']['before'], context_id=0)
        message = 'actual lifecycle and bank'
    else:
        group['predictions'].pop('before')
        message = 'all four common-root'
    with pytest.raises(ValueError, match=message):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'parent', 'draws'])
def test_missing_cohort_or_invalid_resampling_cannot_create_selected_results(case):
    rows = cohort()
    draws = 2
    if case == 'missing':
        rows.pop()
    elif case == 'duplicate':
        rows[-1] = rows[-2]
    elif case == 'parent':
        rows[0]['parent'] = 1
    else:
        draws = 1
    with pytest.raises(ValueError, match='bootstrap requires' if case == 'draws' else 'all sixteen V324'):
        summarize(rows, draws=draws)
