"""Small analytic regressions for the Phase III audit and certificate paths."""
import math
from types import SimpleNamespace

import numpy as np
import pytest
from scipy import sparse as sp

from learned_portal_phase3.baselines_and_contracts import (
    evaluate_posterior_pac_policy_upper_bound,
    evaluate_row_stochastic_simplex_posterior_diagnostic,
)
from learned_portal_phase3.spql_core import (
    EmpiricalTrajectoryDataset, UnknownDiscreteKLEnv, build_pac_mmatrix_pair,
    higham_verify_lower_supersolution, higham_verify_upper_subsolution,
    verify_and_bind_deployed_policy_csr,
)


def environment(P, q):
    q = np.array(q, dtype=float)
    return UnknownDiscreteKLEnv("analytic", len(q), sp.csr_matrix(P, dtype=float),
                                q, min(q), max(q), 1.0, 0.0)


@pytest.mark.parametrize("q", [720.0, 800.0])
def test_ground_truth_value_survives_desirability_underflow(q):
    env = environment([[.25, .25, .5], [0, 0, 1], [0, 0, 1]], [q, 1.3, 1])
    z, v = env.true_desirability_and_value([False, False, True], phi_goal=-2)
    expected = q - math.log(.25 * math.exp(-1.3) + .5) + math.log1p(-.25 * math.exp(-q))
    assert v[0] == pytest.approx(expected - 2, abs=1e-11)
    assert z[0] == pytest.approx(math.exp(-expected), rel=1e-11, abs=5e-324)
    assert v[1] == pytest.approx(-.7)


@pytest.mark.parametrize("q", [20.0, 720.0, 800.0])
def test_exact_simplex_uses_cost_independent_probability_bounds(q):
    ds = EmpiricalTrajectoryDataset(2, 200, np.array([100, 100]),
                                    sp.csr_matrix([[0, 100], [0, 100]]),
                                    np.array([100 * q, 100 * q]), q, q, 1.0)
    pac = build_pac_mmatrix_pair(ds, max_degree_bound=2)
    pi = sp.csr_matrix([[0, 1]])
    args = (pac, pi, [False, True], 0.0, 0, 1.0)
    bound = evaluate_row_stochastic_simplex_posterior_diagnostic
    assert bound(*args) == pytest.approx(q, abs=1e-11)
    assert bound(*args, q_hi_override=np.array([3., 3.])) == pytest.approx(3)
    assert bound(*args, known_observed_support=False) == pytest.approx(q - math.log(pac.P_lo[0, 1]))
    if q == 800:
        assert pac.M_pes[0, 1] == 0
        assert math.isinf(evaluate_posterior_pac_policy_upper_bound(*args))


def test_matrix_only_coordinatewise_surrogate_and_normalized_policy():
    pac = SimpleNamespace(M_pes=sp.csr_matrix(math.exp(-1) * np.array([[.1, .1], [0, 1]])))
    args = (pac, sp.csr_matrix([[.5, .5]]) * (1 + 5e-12), [False, True], 0.0, 0, 1.0)
    assert evaluate_posterior_pac_policy_upper_bound(*args) == pytest.approx(2 * (1 + math.log(5)), abs=1e-13)


def test_true_cost_is_from_start_and_rejects_invalid_reachable_rows():
    env = environment([[0, 0, 1], [0, 1, 0], [0, 0, 1]], [4, 2, 1])
    goal = [False, False, True]
    pi = sp.csr_matrix([[0, 0, 1 + 5e-12], [1, 0, 0]])
    assert env.evaluate_deployed_policy_true_cost(pi, goal, -1, 0) == pytest.approx(3)
    assert math.isinf(env.evaluate_deployed_policy_true_cost(pi, goal, -1, 1))
    for invalid in ([-.1, 0, 1.1], [0, 0, 1.1], [0, 0, np.nan]):
        bad = sp.csr_matrix([invalid, [0, 0, 0]])
        assert math.isinf(env.evaluate_deployed_policy_true_cost(bad, goal, 0, 0))


def test_true_cost_retains_log_of_minimum_positive_passive_probability():
    p = np.nextafter(0., 1.)
    env = environment([[1, p], [0, 1]], [1, 1])
    pi = sp.csr_matrix([[0, 1]])
    assert env.evaluate_deployed_policy_true_cost(pi, [False, True], 0, 0) == pytest.approx(1 - math.log(p))


def test_terminal_query_returns_boundary_value_with_nonempty_exterior():
    M = sp.csr_matrix([[0, .3], [0, 0]])
    args = (np.array([.3, 1]), [False, True], 1, -2.0, 1.0, 1.0)
    assert higham_verify_lower_supersolution(M, np.zeros(2), *args) == (True, -2., 0., 0.)
    assert higham_verify_upper_subsolution(M, *args) == (True, -2., 0., 0.)


@pytest.mark.parametrize("z,edge,q_min", [([np.nan, 1], .5, 1), ([.5, 1], np.nan, 1), ([.5, 1], .5, 0)])
def test_deployed_certificate_rejects_invalid_drift_inputs(z, edge, q_min):
    result = verify_and_bind_deployed_policy_csr(
        sp.csr_matrix([[0, edge], [0, 0]]), np.array(z), sp.csr_matrix([[0, 1]]),
        np.array([False, True]), 0, 0.0, 1.0, q_min, 1., 0.)
    assert not result[0]
    assert math.isinf(result[1])


@pytest.mark.parametrize("downstream_cost", [1.0, 720.0, 800.0])
@pytest.mark.parametrize("cycle_length", [1, 2])
def test_oracle_preserves_rare_exit_in_almost_absorbing_cycle(downstream_cost, cycle_length):
    p = 2.0 ** -52
    q = 1e-18
    if cycle_length == 1:
        P = [[1-p, p, 0], [0, 0, 1], [0, 0, 1]]
    else:
        P = [[0, 1, 0, 0], [1-p, 0, p, 0], [0, 0, 0, 1], [0, 0, 0, 1]]
    env = environment(P, [q] * cycle_length + [downstream_cost, 1])
    _, value = env.true_desirability_and_value(np.arange(len(P)) == len(P) - 1)
    expected = downstream_cost + math.log1p(math.expm1(cycle_length * q) / p)
    assert value[0] == pytest.approx(expected, abs=1e-11)


def test_unreachable_almost_absorbing_class_does_not_poison_reachable_values():
    env = environment([[0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
                      [740., 740., 1e-18, .1])
    z, v = env.true_desirability_and_value([False, False, False, True])
    np.testing.assert_allclose(v, [1480., 740., np.inf, 0.], rtol=0., atol=1e-11)
    assert z[0] == z[2] == 0
