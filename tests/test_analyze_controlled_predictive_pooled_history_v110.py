"""Excluded-history evaluation, source-pool membership and actual work accounting."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('pooled_analysis_v110', ROOT / 'scripts/analyze_controlled_predictive_pooled_history_v110.py')
B = load('crossed_fixture_v110', ROOT / 'tests/test_analyze_controlled_predictive_crossed_ranking_v106.py')


def summary(train, heldout):
    return dict(records=len(train) + len(heldout), training_roots=len(train), heldout_roots=len(heldout),
        training_roster=train, heldout_roster=heldout)


def fixture():
    run = B.fixture()
    settings = run['settings']
    settings.update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS], widths=[4, 16],
        queries=['reward', 'risk_goal'], budgets=[256000, 512000], optimizer_steps=1000,
        l2_coefficient=.001 / 1968, l2_reference_parameters=1968)
    lives = settings['lifecycles']
    for original in list(run['cohort']['roots']):
        root = deepcopy(original)
        root.update(root_id=original['root_id'].replace('reward', 'risk_goal'), query='risk_goal')
        for vectors in root['reference_log']['pair_deltas'].values():
            for vector in vectors:
                vector[0] = -abs(vector[0])
        run['cohort']['roots'].append(root)
    run['cohort']['log']['counts']['new_synthetic_transitions'] = 123456
    histories, rosters, counts = [], {}, Counter()
    for life in lives:
        half_train = [[life, query, 0] for query in settings['queries']]
        heldout = [[life, query, 4] for query in settings['queries']]
        full_train = half_train + [[life, query, 1] for query in settings['queries']]
        rosters[str(life)] = dict(half=summary(half_train, heldout), full=summary(full_train, heldout))
        counters = dict(record_files_read=2, records_read=6, half_payload_files_read=2, files_read=4,
            **{key: 0 for key in A.ZERO_DATA})
        counts.update(counters)
        histories.append(dict(life=life, counts=counters, checks={'batch_bound': True}, seconds=.01))
    run.update(models=[], decisions=[], folds=[], bank_log=dict(histories=histories, rosters=rosters,
        counts=dict(counts), checks={'half_membership_from_original_batch': True}, seconds=.04),
        inherited_work={'V105': deepcopy(run['inherited_v105_work']), 'V109': {'new_neural_model_fits': 8}},
        runner_checks={'cached_cohort_exact': True, 'half_statistics_exact': True},
        acquisition_accounting=dict(unique_source_histories=lives, unique_inherited_training_transitions=2048000,
            per_history=[dict(life=life, half_transitions=256000, full_transitions=512000) for life in lives],
            per_fold=[dict(heldout_life=life, source_lives=[other for other in lives if other != life],
                half_transitions=768000, full_transitions=1536000) for life in lives]))
    for life in lives:
        sources = [other for other in lives if other != life]
        data = dict(source_lives=sources, heldout_life=life, checks={'half_membership_preserved': True}, seconds=.01)
        for stage in ('half', 'full'):
            data[stage] = summary([row for source in sources for row in rosters[str(source)][stage]['training_roster']],
                [row for source in sources for row in rosters[str(source)][stage]['heldout_roster']])
        fold = dict(heldout_life=life, source_lives=sources, data_log=data, fit_logs={}, model_metadata={})
        for hidden in A.WIDTHS:
            for stage, budget in zip(('HALF', 'FULL'), settings['budgets']):
                method, group = f'POOLED_H{hidden}_{stage}', data[stage.lower()]
                counters = dict(neural_model_fits=1, optimizer_steps=1000,
                    optimizer_root_passes=1000 * group['training_roots'],
                    optimizer_pair_passes=10000 * group['training_roots'], optimizer_parameter_updates=1000 * 123 * hidden,
                    diagnostic_candidate_predictions=5 * group['records'])
                fit = dict(stage=stage, source_lives=sources, training_roster=deepcopy(group['training_roster']),
                    heldout_roster=deepcopy(group['heldout_roster']), statistics_roster=deepcopy(data['half']['training_roster']),
                    family='UNIFORM_SHRINK', hidden=hidden, parameter_count=123 * hidden,
                    normalization_training_roots=6, conflict_mass_training_roots=6, uniform_gamma=.25,
                    checkpoint=budget, training_roots=group['training_roots'], heldout_roots=group['heldout_roots'],
                    training_replica_rows=4 * group['training_roots'], total_training_pairs=10 * group['training_roots'],
                    l2_coefficient=settings['l2_coefficient'], l2_reference_parameters=1968,
                    initialization='original_initialization' if stage == 'HALF' else 'half_parameters',
                    optimizer_state='reset_zero_moments', new_optimizer_steps=1000,
                    inherited_parameter_steps=0 if stage == 'HALF' else 1000,
                    parameter_lineage_steps=1000 if stage == 'HALF' else 2000,
                    counts=counters, checks={'bound': True}, seconds=.01,
                    models={'UNIFORM_SHRINK': dict(parameter_count=123 * hidden, counts=deepcopy(counters))})
                metadata = dict(hidden=hidden, family='UNIFORM_SHRINK', stage=stage, heldout_life=life,
                    source_lives=sources, checkpoint=budget, episode_cutoff=budget, budget=budget, parameter_count=123 * hidden)
                fold['fit_logs'][method], fold['model_metadata'][method] = fit, metadata
                run['models'].append(dict(heldout_life=life, method=method, metadata=metadata))
                for root in run['cohort']['roots']:
                    if root['life'] == life:
                        run['decisions'].append(dict(root_id=root['root_id'], heldout_life=life, method=method,
                            event=B.event(A.OPTIONS[1] if stage == 'FULL' else 'H2')))
        run['folds'].append(fold)
    run['scoring_log']['counts'].update(model_payloads_loaded=16, model_root_scores=64,
        neural_candidate_predictions=320, neural_hidden_activations=3200)
    return run


def test_equal_excluded_history_means_without_crossed_training_cells():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    contrast = 'POOLED_H4_FULL_minus_POOLED_H4_HALF'
    reward = result['comparisons'][contrast]['reward']['pooled']['selected_utility_delta']
    risk = result['comparisons'][contrast]['risk_goal']['pooled']['selected_utility_delta']
    assert reward['fold_means'] == [1.5, 2.5, 3.5, 4.5]
    assert reward['grand_mean'] == 3. and risk['grand_mean'] == -3.
    assert reward['directions']['positive'] == risk['directions']['negative'] == 4
    assert 'cells' not in reward and len(result['comparisons']) == 6 and len(result['methods']) == 5
    assert result['cohort']['new_model_root_decisions'] == 64


def test_shared_acquisition_and_bank_reads_are_not_multiplied_by_overlapping_folds():
    result = A.analyze_run(fixture())
    cost = result['actual_executed_work']
    assert cost['newly_sampled_environment_transitions'] == cost['new_model_prefix_transitions'] == 0
    assert cost['new_neural_model_fits'] == 16 and cost['new_optimizer_steps'] == 16000
    assert cost['new_optimizer_root_passes'] == 144000 and cost['new_optimizer_pair_passes'] == 1440000
    assert cost['new_optimizer_parameter_updates'] == 19680000
    assert cost['new_neural_candidate_predictions'] == 320 and cost['new_training_diagnostic_candidate_predictions'] == 1200
    assert cost['bank_counts']['record_files_read'] == 8 and cost['bank_counts']['records_read'] == 24
    assert cost['fold_data_counts']['pooled_record_references'] == 120
    assert result['inherited_acquisition_accounting']['unique_inherited_training_transitions'] == 2048000
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['inherited_cohort_extraction_work']['counts']['new_synthetic_transitions'] == 123456
    assert result['inherited_total_work']['V109']['new_neural_model_fits'] == 8


def test_training_and_scoring_on_the_excluded_history_cannot_pass():
    run = fixture()
    run['folds'][0]['fit_logs'][A.LEARNED[0]]['training_roster'][0][0] = 11
    run['decisions'][0]['heldout_life'] = 12
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['source_history_training_and_statistics_exclusion']
    assert not result['checks']['excluded_history_scoring_only']
    assert not result['checks']['full_root_model_and_decision_rosters']


def test_statistics_use_actual_first_batches_and_full_updates_reset_moments():
    run = fixture()
    fold = run['folds'][0]
    fit = fold['fit_logs']['POOLED_H4_FULL']
    # Episode 1 is below a plausible half cutoff but only occurs in the second batch.
    fit['statistics_roster'][-1][2] = 1
    fit['optimizer_state'] = 'continued_moments'
    result = A.analyze_training(run)
    assert not result['checks']['actual_first_batch_statistics_bound']
    assert not result['checks']['paired_continuation_and_reset_adam']


def test_missing_decision_and_censored_reference_preserve_costs_and_block_affected_means():
    run = fixture()
    run['decisions'].pop(0)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_root_model_and_decision_rosters']
    summary = result['methods'][A.LEARNED[0]]['reward']['pooled']['selected_reference_utility']
    assert summary['fold_means'][0] is None and summary['grand_mean'] is None
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['actual_executed_work']['new_neural_model_fits'] == 16
    assert result['methods']['H2_ONLY']['reward']['pooled']['selected_reference_utility']['grand_mean'] is None
