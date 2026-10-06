"""Small retained-data fixtures for balanced crossed-history diagnostics."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('crossed_analysis_v106', ROOT / 'scripts/analyze_controlled_predictive_crossed_ranking_v106.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def event(option):
    scores = {name: dict(value=float(name == option)) for name in A.OPTIONS}
    return dict(option=option, value=scores[option]['value'], predictions=scores, score_semantics='rank_score')


def fixture():
    lives = [11, 12, 13, 14]
    settings = dict(lifecycles=lives, training_lifecycles=lives, methods=list(A.METHODS),
        contrasts=[list(pair) for pair in A.CONTRASTS], queries=['reward'], validation_roots_per_query=2,
        reference_replicas=32, reference_block_size=16)
    roots, decisions, models = [], [], []
    for life in lives:
        for method in A.LEARNED:
            models.append(dict(training_life=life, method=method,
                metadata=dict(hidden=4 if '_H4_' in method else 16)))
    for cohort in lives:
        for episode in range(2):
            root_id = f'life_{cohort}_reward_{episode}'
            originals = {method: event(A.OPTIONS[1] if '_H4_' in method else 'H2') for method in A.METHODS[1:]}
            originals['PREFIX_ONLY_DIRECT']['score_semantics'] = 'prefix_utility'
            log = dict(pair_deltas={option: [[cohort - 10 + episode, 0, 0]] * 32 for option in A.OPTIONS[1:]},
                trajectories=160, outcomes={'LOST': 160}, censored_root=False,
                ground_work={'sampled_transitions': 100}, planning_counts={'model_uniform_draws': 400}, seconds=.01)
            roots.append(dict(root_id=root_id, life=cohort, query='reward', episode=episode,
                original_predictions=originals, reference_log=log, reference_audit={'paired': True}, reference_complete=True))
            for training_life in lives:
                for method in A.LEARNED:
                    decisions.append(dict(root_id=root_id, training_life=training_life, method=method,
                        event=deepcopy(originals[method])))
    scoring_counts = dict(model_payloads_loaded=16, model_root_scores=128, diagonal_model_root_scores=32,
        neural_candidate_predictions=640, neural_hidden_activations=6400, neural_model_fits=0, optimizer_steps=0,
        new_environment_transitions=0, new_synthetic_transitions=0, model_prefix_trajectories=0)
    return dict(status='complete', settings=settings, cohort=dict(roots=roots,
        log=dict(counts={name: 0 for name in A.ZERO_DATA}, checks={'source_complete': True}, seconds=.01)),
        models=models, decisions=decisions, scoring_log=dict(counts=scoring_counts, checks={'diagonal_scores_exact': True}, seconds=.02),
        inherited_v105_work=dict(newly_sampled_environment_transitions=7492903, new_model_prefix_transitions=324480),
        actual_wall_seconds=.03)


def test_balanced_matrix_decomposition_is_additive_and_reports_no_inferential_replicates():
    result = A.matrix_summary([[3., 1.], [3., 5.]], [11, 12], [11, 12])
    assert result['row_means'] == [2., 4.] and result['column_means'] == [3., 3.]
    assert result['grand_mean'] == 3. and result['diagonal']['mean'] == 4.
    decomposition = result['decomposition']
    assert decomposition['sum_of_squares'] == dict(total=8., model=4., cohort=0., interaction=4.)
    assert decomposition['shares'] == dict(model=.5, cohort=0., interaction=.5)
    assert decomposition['identity_residual'] == 0.
    constant = A.matrix_summary([[2., 2.], [2., 2.]], [11, 12], [11, 12])
    assert all(value is None for value in constant['decomposition']['shares'].values())


def test_root_means_then_equal_history_weights_and_original_diagonal_match():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    contrast = A.CONTRASTS[0][0] + '_minus_' + A.CONTRASTS[0][1]
    row = result['comparisons'][contrast]['reward']['pooled']
    matrix = row['selected_utility_delta']
    assert matrix['cells'] == [[1.5, 2.5, 3.5, 4.5]] * 4
    assert matrix['row_means'] == [3.] * 4 and matrix['column_means'] == [1.5, 2.5, 3.5, 4.5]
    assert matrix['grand_mean'] == 3. and matrix['diagonal'] == row['original_v105_diagonal']
    h2 = result['methods']['H2_ONLY']['reward']['pooled']
    assert h2['selected_reference_utility']['grand_mean'] == 0.
    assert h2['pairwise_weighted_error']['grand_mean'] is None


def test_missing_decision_does_not_drop_a_root_or_fill_from_original_diagonal():
    run = fixture()
    run['decisions'].pop(0)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_decision_roster']
    assert not result['checks']['frozen_diagonal_matches']
    matrix = result['methods'][A.LEARNED[0]]['reward']['pooled']['selected_reference_utility']
    assert matrix['cells'][0][0] is None and matrix['row_means'][0] is None
    assert matrix['grand_mean'] is None and matrix['decomposition'] is None
    assert result['cohort']['unique_reference_roots'] == 8


def test_censored_reference_keeps_cost_and_root_while_blocking_full_matrix():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    assert result['cohort']['missing_or_censored_reference_roots'] == [root['root_id']]
    assert result['inherited_reference_work']['trajectories'] == 1280
    matrix = result['methods'][A.LEARNED[0]]['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None


def test_inherited_reference_cost_is_once_and_scoring_cost_tracks_actual_widths():
    run = fixture()
    result = A.analyze_run(run)
    cost = result['actual_executed_work']
    assert cost['newly_sampled_environment_transitions'] == cost['new_model_prefix_transitions'] == 0
    assert cost['new_neural_model_fits'] == cost['new_optimizer_steps'] == 0
    assert cost['new_neural_candidate_predictions'] == 640
    assert result['inherited_reference_work']['ground_work']['sampled_transitions'] == 800
    assert result['inherited_reference_work']['trajectories'] == 1280
    assert result['inherited_v105_total_work']['newly_sampled_environment_transitions'] == 7492903
    run['scoring_log']['counts']['neural_hidden_activations'] += 1
    assert not A.analyze_run(run)['checks']['new_scoring_work_accounted']


def test_changed_diagonal_score_or_audit_cannot_pass_frozen_reference_replication():
    run = fixture()
    row = run['decisions'][0]
    row['event']['predictions']['H2']['value'] += .5
    run['cohort']['roots'][0]['reference_audit']['paired'] = False
    result = A.analyze_run(run)
    assert not result['checks']['frozen_diagonal_matches']
    assert not result['checks']['reference_audits_pass'] and not result['primary_complete']
