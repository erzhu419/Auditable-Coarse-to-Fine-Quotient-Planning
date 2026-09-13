"""Hand-solvable exact planning and independent V43 eligible-edge enumeration."""
from collections import Counter, defaultdict
from itertools import product
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_exact_v52 import ExactAIMSolver, METHODS


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    solvers, environment = [], Counter()
    original_init = ExactAIMSolver.__init__
    original_transition = AIMEnvironment.transition
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        solvers.append(solver)

    def transition(env, state, action, rng, **kwargs):
        result = original_transition(env, state, action, rng, **kwargs)
        environment.update(oracle_day_transitions=1, oracle_seed_exposures=len(action),
                           oracle_propagation_draws=result[2]['propagation_draws'])
        return result

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(AIMEnvironment, 'transition', transition):
        yield
    analytic = Counter()
    for solver in solvers:
        analytic.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_exact_v52.development_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_exact_v52.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters=dict(environment), exact_solver_counters=dict(analytic),
        solver_instances=len(solvers), wall_seconds=perf_counter() - started,
        scope='Hand-solvable graphs and independent scripted V43 transition enumeration; no main-panel evaluation, gradients or learned models.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def graph(n, edges):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    return result


def initial_record(solver, statuses, budget, days):
    return next(row for row in solver.records() if row['statuses'] == list(statuses)
                and row['remaining_budget'] == budget and row['remaining_days'] == days)


def test_long_horizon_chain_beats_score_and_myopic_but_one_day_prefers_star():
    g = graph(7, [(0, 1), (1, 2), (2, 3), (4, 5), (4, 6)])
    state = (0,) * 7
    for method, expected in [('AVERAGE_SCORE', 3.), ('AVERAGE_MYOPIC', 3.),
                             ('AVERAGE_OPTIMAL', 4.), ('JOINT_OPTIMAL', 4.)]:
        solver = ExactAIMSolver(g, method)
        assert solver.value(state, 1, 3) == expected
        assert initial_record(solver, state, 1, 3)['selected'] == ([4] if expected == 3 else [0])
        assert solver.value(state, 1, 1) == 3.
        assert initial_record(solver, state, 1, 1)['selected'] == [4]


def test_overlapping_parents_zero_budget_and_old_activity_not_recounted():
    solver = ExactAIMSolver(graph(3, [(0, 2), (1, 2)]), 'JOINT_OPTIMAL')
    state = (1, 1, 0)
    distribution = {next_state: (probability, reward)
                    for probability, next_state, reward in solver.kernel(state, ())}
    assert distribution == {(2, 2, 0): (.25, 0.), (2, 2, 1): (.75, 1.)}
    assert solver.value(state, 0, 2) == .75
    assert solver.value(state, 0, 0) == 0.
    assert all(row['remaining_days'] > 0 for row in solver.records())
    assert any(row['remaining_budget'] == 0 and row['remaining_days'] == 1
               for row in solver.records())
    assert solver.counters['dp_states'] == len(solver.records())


def test_average_score_recomputes_after_each_real_selection():
    solver = ExactAIMSolver(graph(6, [(0, 4), (0, 5), (1, 0), (2, 3)]), 'AVERAGE_SCORE')
    state = (0,) * 6
    assert solver.value(state, 2, 1) == 5.
    # Node 1 loses its target when node 0 is selected; the next seed must be 2.
    assert initial_record(solver, state, 2, 1)['selected'] == [0, 2]
    assert solver.counters['score_node_evaluations'] == 11


class ScriptedRNG:
    def __init__(self, values):
        self.values = iter(values)
        self.draws = 0

    def random(self):
        self.draws += 1
        return next(self.values)


def test_target_kernel_matches_independent_eligible_edge_enumeration():
    g = graph(4, [(0, 2), (0, 3), (1, 2), (1, 3)])
    state, action = (0, 0, 0, 0), (0, 1)
    solver = ExactAIMSolver(g, 'JOINT_OPTIMAL')
    exact = {(next_state, reward): probability
             for probability, next_state, reward in solver.kernel(state, action)}
    assert solver.kernel(state, tuple(reversed(action))) is solver.kernel(state, action)
    env = AIMEnvironment(g, budget=2, horizon=1, seed=52001)
    seeded = list(state)
    for node in action:
        seeded[node] = 1
    probabilities = [1. / g.in_degree(target)
                     for source in range(len(g)) if seeded[source] == 1
                     for target in sorted(g.successors(source)) if seeded[target] == 0]
    independently_enumerated = defaultdict(list)
    for successes in product((False, True), repeat=len(probabilities)):
        probability = math.prod(p if success else 1. - p
                                for success, p in zip(successes, probabilities))
        rng = ScriptedRNG([0. if success else (1. + p) / 2.
                           for success, p in zip(successes, probabilities)])
        next_state, reward, info = env.transition(state, action, rng)
        assert rng.draws == info['propagation_draws'] == 4
        independently_enumerated[(tuple(next_state), reward)].append(probability)
    expected = {key: math.fsum(values) for key, values in independently_enumerated.items()}
    assert exact == pytest.approx(expected)
    assert math.fsum(exact.values()) == 1.
    assert len(exact) == 4
    assert exact[((2, 2, 1, 1), 4.)] == 9. / 16.


def test_oracle_policy_classes_contain_their_controls():
    g = graph(5, [(0, 2), (1, 2), (2, 3), (3, 4), (0, 4)])
    state = (0,) * 5
    values = {method: ExactAIMSolver(g, method).value(state, 2, 3) for method in METHODS}
    assert values['AVERAGE_OPTIMAL'] >= values['AVERAGE_SCORE'] - 1e-12
    assert values['AVERAGE_OPTIMAL'] >= values['AVERAGE_MYOPIC'] - 1e-12
    assert values['SCORE_OPTIMAL_BUDGET'] >= values['AVERAGE_SCORE'] - 1e-12
    assert all(values['JOINT_OPTIMAL'] >= value - 1e-12 for value in values.values())
