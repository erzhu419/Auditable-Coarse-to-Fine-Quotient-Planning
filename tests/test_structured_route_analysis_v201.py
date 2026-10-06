"""Small analytic fixtures; neither the producer nor its output is opened."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_structured_route_task_v201 as audit


F = Fraction


def test_delivery_requires_finish_and_h2_cannot_complete_root_goal():
    case = audit.context('normal', 'low', F(17, 20))
    rows = audit.route_rows(case)
    delay = audit.graph_delay(rows)
    assert delay['WON'] == 3 and delay['LOST'] == 2
    assert delay['RECOVERY'] == 2 and delay['ABORT'] == 2
    assert set(audit.finite_actions(case, 'START', 1, 'goal').values()) == {audit.ZERO}
    assert audit.finite_vector(case, 'DELIVERY', 0, 'goal') == audit.ZERO
    assert audit.finite_vector(case, 'DELIVERY', 1, 'goal') == (F(0), F(0), F(1))
    assert audit.finite_actions(case, 'RECOVERY', 1, 'goal')['RETRY'][2] == 0
    assert audit.finite_actions(case, 'RECOVERY', 2, 'goal')['RETRY'][2] == F(1, 4)
    for query in ('goal', 'risk'):
        h2 = lambda state, remaining: audit.select(audit.finite_actions(case, state, min(2, remaining), query), query)
        assert h2('START', 4) == 'WAIT'
        assert audit.replay(rows, h2) == audit.ZERO


def test_hard_constraint_upper_hull_mixes_complete_feasible_vectors():
    vectors = dict(WAIT=audit.ZERO, SAFE=(-F(1, 2), F(0), F(3, 5)),
        RISK=(-F(1), F(1, 5), F(4, 5)), DOMINATED=(-F(1), F(1, 10), F(3, 5)))
    work = Counter()
    bound = audit.constrained_frontier(vectors, work=work)
    assert audit.select(vectors, 'goal') == 'RISK' and vectors['RISK'][1] > audit.DELTA
    assert bound['vector'] == (-F(5, 8), F(1, 20), F(13, 20))
    assert bound['utility'] == F(79, 40) > audit.value(vectors['SAFE'], 'goal')
    saved = dict(delta='1/20', vector=[str(x) for x in bound['vector']], utility=str(bound['utility']),
        mix=[dict(policy=name, weight=str(weight)) for name, weight in bound['mix']])
    assert audit.certify_mixture(saved, vectors, bound)
    saved['vector'] = ['0', '0', '4/5']  # independent component maxima are unattainable
    assert not audit.certify_mixture(saved, vectors, bound)
    assert work['frontier_orientation_checks'] > 0 and work['frontier_edge_checks'] > 0


def test_return_and_retry_have_distinct_achievable_joint_continuations():
    case = audit.context('blocked', 'low', F(17, 20))
    rows = audit.route_rows(case)
    vectors = audit.full_policy_vectors(case)
    returned = audit.replay(rows, audit.pure_policy('DETOUR_RETURN', rows))
    retried = audit.replay(rows, audit.pure_policy('DETOUR_RETRY', rows))
    assert returned == vectors['DETOUR_RETURN'] and retried == vectors['DETOUR_RETRY']
    assert retried[1] > returned[1] and retried[2] > returned[2]
    assert audit.value(retried, 'goal') > audit.value(returned, 'goal')
    assert audit.value(retried, 'risk') < audit.value(returned, 'risk')
    truncated = audit.replay(rows, audit.pure_policy('DETOUR_RETRY', rows), remaining=3)
    assert truncated[2] == case['detour_success']
    assert truncated[1] == retried[1] and truncated[0] == retried[0]
    assert audit.select(audit.finite_actions(case, 'RECOVERY', 2, 'goal'), 'goal') == 'RETRY'
    assert audit.select(audit.finite_actions(case, 'RECOVERY', 2, 'risk'), 'risk') == 'RETURN'


def test_handwritten_saved_policy_fixture_detects_changed_joint_result():
    case = audit.context('normal', 'low', F(17, 20))
    rows = audit.route_rows(case)
    expected = audit.reconstruct(case)
    query = 'goal'
    values, actions, policy = [], [], []
    for remaining in range(5):
        for state in sorted(audit.STATES):
            choices = audit.finite_actions(case, state, remaining, query)
            values.append([state, remaining, [str(x) for x in audit.finite_vector(case, state, remaining, query)]])
            actions.append([state, remaining, {name: [str(x) for x in vector] for name, vector in choices.items()}])
            if choices:
                policy.append([state, remaining, audit.select(choices, query)])
    # All fields come from this one tiny analytic fixture, not runner.run().
    saved = dict(oracle=dict(vector=['-1/10', '1/10', '9/10'], utility='7/2', root_action='SHORT',
        recovery_action='RETRY', values=values, action_vectors=actions, policy=policy,
        root_action_vectors={name: [str(x) for x in vector] for name, vector in audit.finite_actions(case, 'START', 4, query).items()}),
        native_h2=dict(vector=['0', '0', '0'], utility='0', root_action='WAIT',
            policy=[['START', 4, 'WAIT'], ['WAIT_ENTRY', 3, 'WAIT']]))
    assert audit.check_query_record(case, rows, saved, expected, query, Counter())
    tampered = deepcopy(saved)
    tampered['oracle']['vector'][2] = '1'
    assert not audit.check_query_record(case, rows, tampered, expected, query, Counter())
    tampered = deepcopy(saved)
    tampered['native_h2']['policy'][0][2] = 'SHORT'
    assert not audit.check_query_record(case, rows, tampered, expected, query, Counter())
