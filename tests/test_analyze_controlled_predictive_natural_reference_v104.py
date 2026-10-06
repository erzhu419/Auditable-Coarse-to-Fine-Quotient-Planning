"""Same-root weights, retained decisions, partial references, and physical new work."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('natural_reference_analysis_v104',
    ROOT / 'scripts/analyze_controlled_predictive_natural_reference_v104.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def fixture():
    roots, references = [], []
    for life in (9, 10):
        for query in ('reward', 'risk_goal'):
            for episode in range(8):
                inherited = episode < 2
                seed = 10390000 + life * 100 + episode
                root = dict(id=f'life_{life}_{query}_{episode}', life=life, query=query, episode=episode,
                    board=[0] * 6 + [2] * 10, step=3, source_seed=seed,
                    reference_origin='inherited' if inherited else 'new', predictions={}, natural={})
                for method in A.METHODS:
                    choice = (0 if method in ('H2_ONLY', 'PREFIX_ONLY_DIRECT') else
                              3 if method.endswith('_FROZEN_HALF') else 1 if '_H4_' in method else 2)
                    score = 1000 + 100 * choice + 10 * episode
                    root['natural'][method] = dict(seed=seed, replica=episode, query=query, score=score,
                        utility=score / 2048 - (4 if query == 'risk_goal' else 0), status='LOST', steps=100,
                        selected_option=A.OPTIONS[choice] if method != 'H2_ONLY' else None,
                        initiation_step=3 if method != 'H2_ONLY' else None)
                    if method != 'H2_ONLY':
                        scores = [0.] * 5
                        if choice:
                            scores[choice] = 1.
                        root['predictions'][method] = dict(board=root['board'], step=3, option=A.OPTIONS[choice],
                            predictions={option: dict(value=value) for option, value in zip(A.OPTIONS, scores)},
                            score_semantics='prefix_utility' if method == 'PREFIX_ONLY_DIRECT' else 'rank_score')
                utility = [0., 1., 0., 2., 3.] if inherited else [0., 0., 1., 2., 3.]
                log = dict(trajectories=160, censored_root=False, ground_work={'sampled_transitions': 1600},
                    planning_counts={'model_uniform_draws': 6400, 'model_spawn_predictions': 1600},
                    outcomes={'LOST': 160}, seconds=.1,
                    pair_deltas={option: [[utility[index], 0., 0.] for _ in range(32)]
                        for index, option in enumerate(A.OPTIONS) if index})
                if inherited:
                    root['inherited_reference'] = dict(root={name: root[name] for name in
                        ('life', 'query', 'episode', 'board', 'step', 'source_seed')},
                        predictions=deepcopy(root['predictions']), terminal_log=log,
                        reference_complete=True, paired_reference=deepcopy(log['pair_deltas']))
                else:
                    root['inherited_reference'] = None
                    references.append(dict(root_id=root['id'], log=log, checks={'execution_matches': True}, seconds=.1))
                roots.append(root)
    methods, contrasts = list(A.METHODS), [list(pair) for pair in A.CONTRASTS]
    counts = dict.fromkeys(A.ZERO_COHORT_WORK, 0)
    counts.update(source_natural_games=832, retained_prediction_events=800, raw_rows_read=832,
        roots=32, inherited_reference_roots=8, new_reference_roots=24)
    return dict(status='complete', settings=dict(methods=methods, contrasts=contrasts,
        lifecycles=[9, 10], queries=['reward', 'risk_goal'], validation_roots_per_query=8,
        reference_replicas=32, reference_block_size=16), cohort=dict(roots=roots, log=dict(counts=counts,
        methods=methods, contrasts=contrasts, source_terminal=True, seconds=.1,
        inherited_v103_work={'newly_sampled_environment_transitions': 999999})),
        references=references, actual_wall_seconds=1.)


def contrast(result, origin=None):
    cohort = result['matched'] if origin is None else result['descriptive_subcohorts'][origin]
    return cohort['comparisons']['R4_H4_REPLICA_DIRECT_minus_R4_H16_REPLICA_DIRECT']['reward']


def test_only_new_reference_work_is_charged_and_reference_planning_is_retained():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    cost = result['actual_executed_work']
    assert cost['new_reference_work']['trajectories'] == 3840
    assert cost['inherited_reference_work']['trajectories'] == 1280
    assert cost['newly_sampled_environment_transitions'] == 38400
    assert cost['inherited_reference_work']['ground_work']['sampled_transitions'] == 12800
    assert cost['new_reference_work']['planning_counts']['model_spawn_predictions'] == 38400
    assert cost['new_natural_transitions'] == cost['new_training_environment_transitions'] == 0
    assert cost['new_model_prefix_transitions'] == cost['new_neural_model_fits'] == cost['new_neural_candidate_predictions'] == 0
    assert result['inherited_v103_total_work']['newly_sampled_environment_transitions'] == 999999


def test_full_cohort_weights_old_two_and_new_six_roots_one_quarter_three_quarters():
    result = A.analyze_run(fixture())
    full = contrast(result)['primary']
    old = contrast(result, 'inherited')['primary']
    new = contrast(result, 'new')['primary']
    assert full['references']['pooled']['selected_utility_delta'] == -.5
    assert old['references']['pooled']['selected_utility_delta'] == 1.
    assert new['references']['pooled']['selected_utility_delta'] == -1.
    assert full['natural_mean_score_delta'] == -100
    assert full['natural_mean_utility_delta'] == -100 / 2048
    assert len(result['matched']['comparisons']) == 40
    assert all(row['roots'] == row['paired_reference_roots'] == 8 for row in contrast(result)['lifecycles'])


def test_a_b_reference_blocks_change_only_their_own_independent_suffix_estimates():
    run = fixture()
    for record in run['references']:
        values = record['log']['pair_deltas']['SPACE_1']
        for index in range(16, 32):
            values[index] = [2., 0., 0.]
    result = A.analyze_run(run)
    values = contrast(result)['primary']['references']
    assert values['A']['selected_utility_delta'] == -.5
    assert values['B']['selected_utility_delta'] == 1.
    assert values['pooled']['selected_utility_delta'] == .25
    h2 = result['matched']['methods']['H2_ONLY']['reward']['primary']['references']['pooled']
    assert h2['selected_reference_utility'] == 0 and h2['pairwise_weighted_error'] is None
    assert 'utility_mse' not in result['roots'][0]['reference_metrics']['pooled']['R4_H4_REPLICA_DIRECT']


def test_censored_new_reference_keeps_natural_roster_and_cost_but_not_primary_estimate():
    run = fixture()
    log = run['references'][0]['log']
    log.update(censored_root=True, outcomes={'LOST': 159, 'CUTOFF': 1}, pair_deltas={})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete']
    assert len(result['roots']) == 32 and result['matched']['root_records'] == 32
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 38400
    row = contrast(result)
    assert row['primary'] is None
    assert row['lifecycles'][0]['roots'] == 8 and row['lifecycles'][0]['paired_reference_roots'] == 7
    assert row['available']['natural_mean_score_delta'] == -100
    assert contrast(result, 'inherited')['primary'] is not None


def test_missing_roots_or_changed_decisions_cannot_pass_as_the_frozen_full_cohort():
    run = fixture()
    run['references'].pop()
    result = A.analyze_run(run)
    assert not result['complete'] and not result['primary_complete']
    assert result['cohort']['roots'] == 32 and len(result['cohort']['missing_or_censored_reference_roots']) == 1
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 36800
    run = fixture()
    root = run['cohort']['roots'][0]
    root['predictions']['R4_H4_REPLICA_DIRECT']['option'] = 'H2'
    result = A.analyze_run(run)
    assert not result['checks']['frozen_prediction_events_match']
    assert not result['checks']['inherited_reference_binding']
    run = fixture()
    run['cohort']['roots'][-1]['episode'] = 6
    assert not A.analyze_run(run)['checks']['frozen_full_root_roster']


def test_extra_scoring_or_wrong_reference_work_is_not_a_zero_work_replay():
    run = fixture()
    run['cohort']['log']['counts']['neural_candidate_predictions'] = 5
    run['references'][0]['log']['planning_counts']['model_uniform_draws'] += 4
    result = A.analyze_run(run)
    assert not result['checks']['no_new_training_natural_prefix_or_candidate_scoring']
    assert not result['checks']['reference_work_accounted']
