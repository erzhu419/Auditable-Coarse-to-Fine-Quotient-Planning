"""Concrete equal-update, terminal-label scope and prospective utility reader checks."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_terminal_win_v326 as audit
from test_verify_win_learning_v324 import fit_fixture, new_evaluation, records
from test_terminal_win_analysis_v326 import cohort, shift
from acfqp.science.terminal_win_analysis_v326 import summarize


def test_exact_new_learning_configuration_and_suffix_seeds_are_bound():
    from acfqp.science.terminal_win_run_v326 import configuration
    source = ROOT/'reports/fresh_source_v312/source_summary.json'
    assert audit.expected_configuration(source) == json.loads(json.dumps(configuration(source)))
    assert audit.training_seed(5, 'B0') == 3262050100000
    assert audit.post_seed(5, 'B', 2) == 3265051200000
    assert audit.continuation_seed(15, 'B', 2, 1023, 3) == 3267151204095


@pytest.fixture(scope='module')
def replay():
    old, arrays, head, _ = fit_fixture()
    n = audit.GROUPS
    roots = np.tile(arrays['roots'], (n//2, 1))
    labels = np.tile(arrays['targetwin'], (n//2, 1))
    arrays = dict(roots=roots, targetwin=labels, terminal_win=1.-labels)
    epochs = []
    for _ in range(audit.EPOCHS):
        receipt = deepcopy(old)
        for field in ('fitted_rootgroups', 'trained_afterstates', 'win_trained_afterstates'):
            receipt[field] = n
        for field in ('learning_counts', 'target_counts', 'normalization_counts', 'representation_counts'):
            for key, value in receipt[field].items():
                if key not in ('replica_noise_divisions', 'replica_noise_square_roots', 'native_workspace_bytes'):
                    receipt[field][key] = value*(n//2)
        receipt['last_sample']['rootgroup'] = n-1
        epochs.append(receipt)
    fit = dict(method='REPLAY_GROUPED_WIN_ONLY_LOCAL', alpha=.0025, distinct_rootgroups=n,
        epochs=audit.EPOCHS, fitted_rootgroups=n*audit.EPOCHS, replicates=4, reward_frozen=True,
        epoch_receipts=epochs, cpu_seconds=.02, seconds=.02)
    for field in ('learning_counts', 'target_counts', 'normalization_counts', 'representation_counts'):
        fit[field] = audit.sum_counts(epoch[field] for epoch in epochs)
    return fit, arrays, head


def test_all_replay_epochs_pay_prediction_target_averaging_and_actual_win_writes(replay):
    fit, arrays, head = replay
    writes = audit.check_replay_fit(fit, arrays, head, 'targetwin')
    assert writes == fit['learning_counts']['win_parameter_updates']


@pytest.mark.parametrize('case', ['wrong_label_field', 'unpaid_replay', 'unmatched_updates',
    'reward_write', 'changed_first_head', 'last_epoch_target'])
def test_label_substitution_missing_epochs_or_unpaid_reward_work_is_rejected(replay, case):
    original, arrays, head = replay; fit = deepcopy(original)
    target = 'targetwin'
    if case == 'wrong_label_field': target = 'terminal_win'
    elif case == 'unpaid_replay': fit['normalization_counts'] = fit['epoch_receipts'][-1]['normalization_counts']
    elif case == 'unmatched_updates': fit['fitted_rootgroups'] -= 1
    elif case == 'reward_write': fit['epoch_receipts'][7]['normalization_counts']['reward_parameter_writes'] = 1
    elif case == 'changed_first_head': fit['epoch_receipts'][0]['first_sample'].update(risk_probability=.75, risk_error=.25)
    else: fit['epoch_receipts'][-1]['first_sample']['risk_target'] = .125
    with pytest.raises(ValueError): audit.check_replay_fit(fit, arrays, head, target)


def test_actual_new_natural_endpoints_and_paired_stream_work_are_accepted():
    value = new_evaluation()
    for episode, game in enumerate(value['game_summaries']):
        game['seed'] = audit.evaluation_seed(0, 'A', episode)
    assert audit.check_evaluation(value, 0, 'A', value['estimated_p_four'], value['head_version']) == np.mean(
        [game['utility'] for game in value['game_summaries']])
    value['game_summaries'][0]['seed'] -= 1000000000
    with pytest.raises(ValueError, match='new V326 family'):
        audit.check_evaluation(value, 0, 'A', value['estimated_p_four'], value['head_version'])


@pytest.fixture(scope='module')
def complete():
    rows = cohort()
    return rows, records(rows), summarize(rows)


def test_primary_retention_and_same_root_mechanism_agree_with_all_actual_vectors(complete):
    rows, vectors, result = complete
    audit.check_analysis(result, vectors, rows)


@pytest.mark.parametrize('case', ['SOURCE_primary', 'equal_raw_claim', 'erased_terminal_members',
    'erased_adverse_history', 'independent_source_claim', 'changed_bootstrap', 'wrong_target_mechanism'])
def test_wrong_primary_budget_or_prospective_scope_is_rejected(complete, case):
    rows, vectors, original = complete; result = deepcopy(original)
    if case == 'SOURCE_primary': result['primary'] = result['final_ab_contrasts']['TERMINAL_WIN_minus_SOURCE']
    elif case == 'equal_raw_claim': result['equal_total_raw_efficiency_evaluated'] = True
    elif case == 'erased_terminal_members': result['physical_terminal_supervision_members'] -= 1
    elif case == 'erased_adverse_history': result['primary']['lifecycle_values'].pop('15')
    elif case == 'independent_source_claim': result['independent_SOURCE'] = True
    elif case == 'changed_bootstrap': result['bootstrap_seed'] -= 1
    else: result['terminal_target_contribution_status'] = 'UNRESOLVED'
    with pytest.raises(ValueError): audit.check_analysis(result, vectors, rows)


def test_a_task_loss_cannot_be_overridden_by_positive_average_or_better_targets():
    rows = cohort(); shift(rows, 'TERMINAL_WIN', 2., task='A'); shift(rows, 'TERMINAL_WIN', -3., task='B')
    result = summarize(rows)
    audit.check_analysis(result, records(rows), rows)
    assert not result['retained_improvement_supported']
    result['retained_improvement_supported'] = True
    with pytest.raises(ValueError, match='separate conditions'):
        audit.check_analysis(result, records(rows), rows)


def test_a_terminal_cutoff_prevents_learning_benefit_inference_even_if_evaluation_is_complete():
    rows = cohort(); rows[4]['rounds']['2']['B']['terminal_status_counts'].update(LOST=2047, CUTOFF=1)
    result = summarize(rows)
    audit.check_analysis(result, records(rows), rows)
    assert result['primary_status'] == 'HOLD_TERMINAL_CUTOFF' and result['primary'] is None
    result['bootstrap_executed'] = True
    with pytest.raises(ValueError): audit.check_analysis(result, records(rows), rows)
