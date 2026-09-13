"""Small independent replay and stratified uncertainty examples; no planner calls."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('trajectory_analysis_v61', ROOT/'scripts/analyze_lmta_trajectory_v61.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
WORK = Counter()


@pytest.fixture(scope='session', autouse=True)
def ledger():
    yield
    path = ROOT/'reports/lmta_trajectory_v61.analysis_checks.json'
    report = json.loads(path.read_text()) if path.exists() else dict(schema='acfqp.lmta_trajectory_analysis_checks.v61')
    accumulated = Counter({k:v for k,v in report.get('development_work',{}).items() if isinstance(v,int)})
    accumulated.update(WORK)
    report['development_work'] = dict(accumulated,new_graphs=0,new_planner_calls=0,new_full_policy_evaluations=0,
        new_RL_updates=0,new_MCTS_calls=0,
        scope='Hand-authored trajectory replay; counted validation draws are not main environment samples.')
    path.write_text(json.dumps(report,indent=2)+'\n')


def checked(row, graph, certificates):
    result = A.replay(row, graph, certificates)
    WORK['independent_trajectory_replays'] += 1
    WORK.update(result['verification'])
    return result


def fixture(duplicate=False):
    # With duplicate=True, day two has three successful edges to one inactive target.
    nodes = 5 if duplicate else 4
    edges = [[0,2],[0,3],[1,4],[2,4],[3,4]] if duplicate else [[0,2],[1,3]]
    states = [[0]*nodes, [2,0,1,1,0], [2,2,2,2,1], [2]*nodes] if duplicate else [
        [0]*nodes,[2,0,1,0],[2,2,2,1],[2]*nodes]
    activations = [2,1,0] if duplicate else [1,1,0]
    attempts = [2,3,0] if duplicate else [1,1,0]
    row = dict(graph_id=580000,method=A.METHODS[0],replicate=0,seed=641000000,status='complete',
        stop_reason=None,return_=nodes,decisions=[])
    row['return'] = row.pop('return_')
    certificates = {}
    for day, selected in enumerate(([0],[1],[])):
        work = dict(planner_calls=1, action_value_evaluations=0, forced_choice=int(day==2))
        decision = dict(statuses=states[day],remaining_budget=2-day,remaining_days=3-day,
            selected=selected,planned_value=None,root_action_values=[],decision_work=work,decision_seconds=.1,
            next_statuses=states[day+1],reward=len(selected)+activations[day],environment_seconds=.01,
            environment_work=dict(environment_calls=1,rng_draws=len(edges),eligible_edge_attempts=attempts[day],
                successful_edge_attempts=attempts[day],seeded_nodes=len(selected),activated_targets=activations[day]))
        row['decisions'].append(decision)
        certificates[A.key(dict(decision,graph_id=row['graph_id'],method=row['method']))] = deepcopy(decision)
    return row, dict(graph_id=580000,nodes=nodes,edges=edges), certificates


def test_independent_seeded_replay_and_wrong_transition_detection():
    inputs = fixture()
    result = checked(*inputs)
    assert not result['errors'] and result['verification']['verification_random_draws'] == 6
    inputs[0]['decisions'][1]['next_statuses'] = [2,2,2,0]
    assert checked(*inputs)['errors'] == {'independent_transition_replay':1}


def test_every_edge_drawn_duplicate_successes_count_one_activation(monkeypatch):
    seeds = []
    class ZeroRandom:
        def __init__(self, seed): seeds.append(seed)
        def random(self): return 0.
    monkeypatch.setattr(A, 'Random', ZeroRandom)
    inputs = fixture(duplicate=True)
    result = checked(*inputs)
    assert not result['errors'], result
    assert result['environment_work']['successful_edge_attempts'] == 5
    assert result['environment_work']['activated_targets'] == 3
    assert result['environment_work']['rng_draws'] == 15 and seeds == [641000000]
    inputs[0]['decisions'][1]['environment_work']['activated_targets'] = 3
    assert checked(*inputs)['errors']['independent_transition_replay'] == 1


def test_partial_charges_last_decision_without_drawing_and_detects_certificate_mismatch():
    row, graph, certificates = fixture()
    row.update(status='resource_limit',stop_reason='max_planner_action_values',decisions=row['decisions'][:1])
    row['return'] = None
    row['decisions'][0].update(next_statuses=None,reward=None,environment_seconds=0.,environment_work=dict.fromkeys(A.ENV,0))
    result = checked(row, graph, certificates)
    assert not result['errors'] and result['decision_work']['planner_calls'] == 1
    assert result['verification'].get('verification_random_draws',0) == 0
    row['decisions'][0]['decision_work']['planner_calls'] = 0
    assert checked(row,graph,certificates)['errors']['policy_or_work_certificate'] == 1
    row['decisions'][0]['environment_work']['rng_draws'] = 2
    assert checked(row,graph,certificates)['errors']['partial_decision_environment'] == 1


def test_stratified_paired_uncertainty_uses_within_graph_variance():
    left, right = [[0.,2.],[10.,12.]], [[1.,3.],[11.,13.]]
    estimate = A.estimate(left, 6.)
    assert estimate['mean'] == 6. and estimate['standard_error'] == pytest.approx(2**-.5)
    paired = A.estimate([[b-a for a,b in zip(xs,ys)] for xs,ys in zip(left,right)],1.)
    assert paired['standard_error'] == 0. and paired['simultaneous_contains_exact']
    inconsistent = A.estimate([[1.,1.],[1.,1.]],1.1)
    assert inconsistent['simultaneous_contains_exact'] is False
    assert A.ZSIM > A.Z95


def test_one_day_counter_aggregation_preserves_zero_outcome_meaning():
    block = Counter(action_value_evaluations=128,transition_outcomes=0,target_probability_evaluations=256)
    aggregate = dict(sum((block for _ in range(16)), Counter()))
    assert 'transition_outcomes' not in aggregate
    result = A.compare_work(aggregate,dict(action_value_evaluations=16.,transition_outcomes=0.,target_probability_evaluations=32.))
    assert result['transition_outcomes'] == dict(actual=0,exact_expected=0.,actual_over_expected=None)
    assert result['action_value_evaluations'] == dict(actual=2048,exact_expected=2048.,actual_over_expected=1.)
    assert result['target_probability_evaluations']['actual_over_expected'] == 1.
