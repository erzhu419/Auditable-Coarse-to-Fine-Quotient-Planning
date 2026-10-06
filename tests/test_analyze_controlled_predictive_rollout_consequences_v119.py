"""Synthetic retained-record checks; no games, model inference, fits or builds."""
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('analysis_v119',
    ROOT / 'scripts/analyze_controlled_predictive_rollout_consequences_v119.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def fixture():
    inherited = dict(source_environment={'sampled_transitions': 100}, tree_fitting={'tree_fits': 96},
        utility_validation_environment={'sampled_transitions': 50}, source_seconds=2., scope='synthetic')
    capsule = dict(schema='acfqp.rollout_source.v119', inherited_costs=inherited,
        snapshots=[dict(life=life, phase='A_RETURN', module_id=0, rule={}, model={},
            selected_origin={'batch': 2, 'mode': 'SHARED'}, source_choices=['NEW_SHARED', 'KEEP', 'NEW_SHARED'])
            for life in A.LIVES])
    run = dict(schema='acfqp.rollout_consequences.v119.run', status='complete', seconds=1.,
        settings=dict(lifecycles=list(A.LIVES), methods=list(A.METHODS), queries=deepcopy(A.QUERIES),
            replicas=A.REPLICAS, phase='A_RETURN', max_steps=2000, version_base=A.BASE,
            planner_offset=A.PLANNER_OFFSET, rollout_offset=A.ROLLOUT_OFFSET),
        inherited_costs=deepcopy(inherited), lifecycles=[])
    raw = []
    for life in A.LIVES:
        history = dict(life=life, games=[], seconds=.25)
        run['lifecycles'].append(history)
        for index, method in enumerate(A.METHODS):
            for query in A.QUERIES:
                for replica in range(A.REPLICAS):
                    seed = A.BASE + 3_000_000 + life * 100000 + replica
                    score = 128 + 16 * index * (life + 1) + 8 * replica
                    work = dict(sampled_transitions=2, initial_spawns=2, environment_random_draws=8,
                        ground_explicit_swipe_calls=2, ground_state_status_calls=3)
                    result = dict(score=score, status='LOST', steps=2, environment_counts=work,
                        planning_counts={'model_spawn_samples': 4},
                        consequence_counts={'model_spawn_samples': 3 * int(method[2:])} if method.startswith('MC') else {},
                        setup_counts={'cpp_compilations': 1} if method == 'MC4' else {},
                        seconds=.1, setup_seconds=.01 if method.startswith('MC') else 0., source_unchanged=True)
                    result['utility'] = A.utility(result, query)
                    row = dict(life=life, method=method, query=query, replica=replica, seed=seed,
                        planner_seed=seed + A.PLANNER_OFFSET,
                        rollout_seed=seed + A.ROLLOUT_OFFSET if method.startswith('MC') else None,
                        result=result)
                    history['games'].append(row)
                    initial = [1, 1] + [0] * 14
                    mid, final = [1] + [0] * 15, [0, 1] + [0] * 14
                    steps = [dict(board=initial, action='LEFT', afterstate=[0] * 16, next_board=mid,
                        score=score // 2, status='ACTIVE', spawned_cell=0, spawned_rank=1),
                        dict(board=mid, action='DOWN', afterstate=[0] * 16, next_board=final,
                        score=score - score // 2, status='LOST', spawned_cell=1, spawned_rank=1)]
                    episode = dict(seed=seed, initial_board=initial, initial_spawns=[], final_board=final,
                        status='LOST', return_score=score, steps_count=2, steps=steps, work=deepcopy(work), seconds=.1)
                    decisions = [dict(action=step['action'], value=1., action_values={step['action']: {'value': 1.}})
                                 for step in steps]
                    raw.append(dict(**deepcopy(row), episode=episode, decisions=decisions))
    return run, capsule, raw


def test_complete_equal_lifecycle_means_and_separated_actual_costs(tmp_path):
    run, capsule, raw = fixture()
    (tmp_path / 'run.json').write_text(json.dumps(run))
    (tmp_path / 'source_capsule.json').write_text(json.dumps(capsule))
    for life in A.LIVES:
        folder = tmp_path / f'life_{life}'
        folder.mkdir()
        with gzip.open(folder / 'control_games.jsonl.gz', 'wt') as stream:
            for row in raw:
                if row['life'] == life:
                    stream.write(json.dumps(row) + '\n')
    actual = A.analyze_directory(tmp_path)
    assert actual['primary_complete'], actual['checks']
    comparison = actual['control']['comparisons']['MC4_minus_TREE']['reward']
    assert comparison['mean_deltas']['score'] == 40.
    assert [x['deltas']['score'] for x in comparison['lifecycles']] == [16., 32., 48., 64.]
    assert comparison['utility_signs'] == dict(positive=4, negative=0, equal=0, missing=0)
    costs = actual['actual_executed_work']
    assert costs['total']['games'] == 64
    assert costs['newly_sampled_environment_transitions'] == 128
    assert costs['imagined_model_spawn_samples'] == 64 * 4 + 16 * (12 + 48)
    assert costs['methods']['MC4']['setup'] == {'cpp_compilations': 16}
    assert costs['methods']['MC16']['consequence']['model_spawn_samples'] == 16 * 48
    assert costs['new_tree_fits'] == costs['new_router_observations'] == 0
    assert actual['inherited_source_work'] == capsule['inherited_costs']


def test_missing_summary_does_not_refund_retained_cost_or_impute_effect():
    run, capsule, raw = fixture()
    run['lifecycles'][0]['games'].pop(0)
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['complete'] and not actual['checks']['summary_roster']
    assert actual['actual_executed_work']['total']['games'] == 64
    assert actual['control']['comparisons']['TREE_minus_H2_ONLY']['reward']['mean_deltas']['utility'] is None


def test_mismatched_paired_seed_invalidates_primary_and_pair():
    run, capsule, raw = fixture()
    run['lifecycles'][0]['games'][0]['seed'] += 10
    raw[0]['seed'] += 10
    raw[0]['episode']['seed'] += 10
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['checks']['fresh_paired_streams'] and not actual['primary_complete']
    assert actual['control']['comparisons']['MC4_minus_H2_ONLY']['reward']['mean_deltas']['utility'] is None


def test_miscomputed_utility_is_not_used_even_when_both_records_agree():
    run, capsule, raw = fixture()
    run['lifecycles'][0]['games'][0]['result']['utility'] += .25
    raw[0]['result']['utility'] += .25
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['checks']['utility_recomputed'] and not actual['primary_complete']
    assert actual['control']['methods']['H2_ONLY']['reward']['lifecycle_mean']['utility'] is None


def test_truncated_raw_history_and_cutoff_stay_in_costs():
    run, capsule, raw = fixture()
    raw[0]['episode']['steps'].pop()
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['checks']['retained_action_histories'] and not actual['primary_complete']
    assert actual['actual_executed_work']['newly_sampled_environment_transitions'] == 128
    run, capsule, raw = fixture()
    run['lifecycles'][0]['games'][0]['result']['status'] = raw[0]['result']['status'] = 'CUTOFF'
    raw[0]['episode']['status'] = 'CUTOFF'
    raw[0]['episode']['steps'][-1]['status'] = 'ACTIVE'
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['checks']['terminal_games'] and not actual['primary_complete']
    assert actual['actual_executed_work']['total']['games'] == 64


def test_source_mutation_and_new_fit_work_are_visible():
    run, capsule, raw = fixture()
    for row in (run['lifecycles'][0]['games'][0], raw[0]):
        row['result']['source_unchanged'] = False
        row['result']['consequence_counts']['tree_fits'] = 1
    actual = A.analyze_run(run, capsule, raw)
    assert not actual['checks']['source_read_only'] and not actual['checks']['no_new_training']
    assert actual['actual_executed_work']['new_tree_fits'] == 1
