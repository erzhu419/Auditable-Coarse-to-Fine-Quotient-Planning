"""New seed context, WIN-only budget, actual endpoint and primary-scope reader checks."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_win_learning_v324 as audit


def test_real_initial_reader_uses_explicit_seed_context_and_preserves_default():
    # Only the first retained finite detector row is used as a literal-physics fixture.
    prior = json.loads((ROOT/'reports/greedy_targets_v317/summary.json').read_text())
    with gzip.open(prior['parent_receipts'][0]['trace_file'], 'rt') as stream:
        row = next(json.loads(line) for line in stream)
    assert row['kind'] == 'WARMUP'
    original = audit.InitialWorld(row['lifecycle'], row['phase'])
    original.warmup(deepcopy(row))
    changed = deepcopy(row); changed['lifecycle'] += 4
    explicit = audit.InitialWorld(changed['lifecycle'], changed['phase'],
        lambda life, stage, game: row['summary']['seed'], audit.training_seed)
    explicit.warmup(changed)
    assert explicit.warm_games == original.warm_games
    with pytest.raises(ValueError, match='fresh complete SOURCE detector'):
        audit.InitialWorld(changed['lifecycle'], changed['phase']).warmup(changed)


def fit_fixture():
    roots = np.zeros((2, 16), dtype=np.int32); roots[1, 0] = 1
    labels = np.asarray([[1., 1., 1., 1.], [0., 0., 0., 0.]])
    features = np.sort(audit.feature_addresses(roots), axis=1)
    writes = int(2+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    arrays = dict(roots=roots, targetwin=labels, mean_win=np.mean(labels, axis=1))
    fit = dict(method='GROUPED_WIN_ONLY_LOCAL', alpha=.0025, fitted_rootgroups=2, trained_afterstates=2,
        win_trained_afterstates=2, reward_trained_afterstates=0, replicates=4,
        frozen_rootgroup_predictions=True, reward_frozen=True,
        sampling_unit='ROOTGROUP_MEAN_OF_FIXED_TEACHER_ONE_STEP_REPLICAS',
        learning_counts=dict(rootgroup_updates=2, current_predictions=2, win_predictions=2,
            table_lookups=64, win_table_lookups=64, table_update_occurrences=64,
            table_updates=writes, win_parameter_updates=writes),
        target_counts=dict(rootgroups_targeted=2, win_replica_reads=16, win_target_mean_additions=8,
            target_mean_divisions=2, replica_noise_residuals=8, replica_noise_squares=8,
            replica_noise_accumulations=8, replica_noise_divisions=1, replica_noise_square_roots=1),
        normalization_counts=dict(rootgroups_processed=2, feature_extractions=2, feature_occurrences=64,
            feature_digit_reads=384, feature_address_multiply_adds=384, sort_calls=2, sort_items=64,
            sort_comparisons=100, denominator_occurrence_visits=64, rootgroup_unique_addresses=writes,
            win_gradient_products=writes, normalization_divisions=writes, parameter_update_multiplications=writes,
            rootgroup_parameter_commits=2, win_rootgroup_commits=2, win_parameter_writes=writes, native_workspace_bytes=512),
        representation_counts=dict(risk_sigmoid_evaluations=2, local_risk_table_lookups=64),
        replicate_noise=dict(win_replica_rms=0., definition='SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'),
        first_sample=dict(rootgroup=0, risk_target=1., risk_probability=.5, risk_error=.5),
        last_sample=dict(rootgroup=1, risk_target=0., risk_probability=.5, risk_error=-.5),
        cpu_seconds=.001, seconds=.001)
    zero = np.zeros(4*11**6)
    return fit, arrays, SimpleNamespace(reward=zero, terminal=zero), writes


def test_real_address_inventory_and_win_only_group_budget_are_accepted():
    fit, arrays, head, writes = fit_fixture()
    assert audit.check_win_fit(fit, arrays, head) == writes


@pytest.mark.parametrize('field', ['reward_read', 'reward_write', 'dual_table_read', 'label_mean', 'previous_head', 'write_inventory'])
def test_reward_work_fake_label_or_wrong_previous_head_is_rejected(field):
    fit, arrays, head, _ = fit_fixture()
    if field == 'reward_read': fit['learning_counts']['reward_predictions'] = 2
    elif field == 'reward_write': fit['normalization_counts']['reward_parameter_writes'] = 1
    elif field == 'dual_table_read': fit['learning_counts']['table_lookups'] *= 2
    elif field == 'label_mean': fit['first_sample']['risk_target'] = .25
    elif field == 'previous_head': fit['first_sample'].update(risk_probability=.75, risk_error=.25)
    else: fit['learning_counts']['win_parameter_updates'] += 1
    with pytest.raises(ValueError): audit.check_win_fit(fit, arrays, head)


def test_new_learning_configuration_matches_producer_and_excludes_old_target_costs():
    from acfqp.science.win_learning_run_v324 import configuration
    source = ROOT/'reports/fresh_source_v312/source_summary.json'
    assert audit.expected_configuration(source) == json.loads(json.dumps(configuration(source)))
    assert audit.training_seed(5, 'B0') == 324250100000
    assert audit.post_seed(5, 'B', 2) == 324551200000


def new_evaluation():
    # A real natural endpoint fixture exercises only new reader seed/cost binding.
    old = json.loads((ROOT/'reports/win_confirmation_v323/summary.json').read_text())
    value = deepcopy(old['by_lifecycle'][0]['evaluations']['A']['FIRST_LOCAL'])
    for episode, game in enumerate(value['game_summaries']): game['seed'] = audit.evaluation_seed(0, 'A', episode)
    return value


def test_new_natural_stream_cost_endpoint_and_head_are_bound():
    value = new_evaluation()
    assert audit.check_evaluation(value, 0, 'A', value['estimated_p_four'], value['head_version']) == np.mean(
        [game['utility'] for game in value['game_summaries']])
    changed = deepcopy(value); changed['game_summaries'][0]['seed'] -= 1000000000
    with pytest.raises(ValueError, match='new V324 family'):
        audit.check_evaluation(changed, 0, 'A', value['estimated_p_four'], value['head_version'])


def records(rows):
    result = []
    for row in rows:
        cells = {}
        for task in audit.TASKS:
            cells['FIRST_'+task] = {arm:float(np.mean([game['utility'] for game in value['game_summaries']]))
                for arm, value in row['initial'][task]['evaluations'].items()}
            for number in ('1', '2'):
                cells['ROUND'+number+'_'+task] = dict(cells['FIRST_'+task], **{arm:float(np.mean(
                    [game['utility'] for game in item['evaluations']['game_summaries']]))
                    for arm, item in row['rounds'][number][task]['arms'].items()})
        result.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells))
    return result


def test_new_learning_primary_and_all_task_retention_flags_match_actual_vectors():
    from test_win_learning_analysis_v324 import cohort
    from acfqp.science.win_learning_analysis_v324 import summarize
    rows = cohort(); result = summarize(rows)
    audit.check_analysis(result, records(rows), rows)
    wrong = deepcopy(result); wrong['primary'] = wrong['final_ab_contrasts']['QUERY_WIN_minus_SOURCE']
    with pytest.raises(ValueError, match='sole primary cannot'):
        audit.check_analysis(wrong, records(rows), rows)


def test_an_unresolved_task_cannot_be_reported_as_preserved():
    from test_win_learning_analysis_v324 import cohort, shift
    from acfqp.science.win_learning_analysis_v324 import summarize
    rows = cohort(); shift(rows, 'QUERY_WIN', -3., task='B')
    result = summarize(rows); audit.check_analysis(result, records(rows), rows)
    wrong = deepcopy(result); wrong['retained_improvement_supported'] = True
    with pytest.raises(ValueError, match='separate conditions'):
        audit.check_analysis(wrong, records(rows), rows)
