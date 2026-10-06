from collections import Counter
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_controlled_predictive_reference_feasibility_v199 as audit


def payload(reward, second_action=False):
    cells = [[0, 0, 'CUTOFF'], [1, 1, 'ACTIVE'], [2, 2, 'ACTIVE']]
    rows = [[1, 'DOWN', [[1, 1, 0, reward.numerator, reward.denominator]]],
            [2, 'DOWN', [[1, 1, 1, 0, 1]]]]
    if second_action:
        rows.append([1, 'UP', [[1, 1, 0, 0, 1]]])
    return dict(cells=cells, rows=rows, roots=[2])


QUERY = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)


def test_joint_policy_profiles_preserve_achievable_full_vectors_and_sorted_eps_choice():
    data = dict(cells=[[0, 0, 'CUTOFF'], [1, 0, 'WON'], [2, 0, 'LOST'], [3, 1, 'ACTIVE']], roots=[3],
        rows=[[3, 'UP', [[1, 2, 1, 0, 1], [1, 2, 2, 0, 1]]], [3, 'DOWN', [[1, 1, 0, 1, 10]]]])
    kernel = audit.read_kernel(data)
    reward = audit.exact_plan(kernel, QUERY)
    goal = audit.exact_plan(kernel, dict(reward_weight=0., failure_penalty=0., goal_bonus=1.))
    assert reward['policy'][3] == 'DOWN'
    assert reward['vectors'][3] == (Fraction(1, 10), Fraction(0), Fraction(0))
    assert goal['policy'][3] == 'UP'
    assert goal['vectors'][3] == (Fraction(0), Fraction(1, 2), Fraction(1, 2))
    assert reward['action_vectors'][3, 'UP'] == goal['action_vectors'][3, 'UP']
    data['rows'] = [[3, 'UP', [[1, 1, 0, 1000000000001, 10000000000000]]],
                    [3, 'DOWN', [[1, 1, 0, 1, 10]]]]
    assert audit.exact_plan(audit.read_kernel(data), QUERY)['policy'][3] == 'DOWN'


def test_shared_closed_average_and_lifted_policy_replay_on_both_roots():
    inputs = {'case00': payload(Fraction(1, 10)), 'case01': payload(Fraction(1, 5))}
    full = audit.disjoint_union(inputs)
    oracle = {'q': audit.exact_plan(full, QUERY)}
    record, quotient, mapping = audit.reference_record(full, oracle, Fraction(1), Counter())
    assert quotient['roots'][0] == quotient['roots'][1]
    assert record['metrics']['active_cells'] == 2
    solution = audit.exact_plan(quotient, QUERY)
    lifted = {state: solution['policy'][mapping[state]] for state in full['actions']}
    actual = audit.policy_replay(full, lifted)
    assert solution['vectors'][quotient['roots'][0]][0] == Fraction(3, 20)
    assert [actual[root][0] for root in full['roots']] == [Fraction(1, 10), Fraction(1, 5)]
    assert record['metrics']['max_reward_spread'] == .1
    assert record['metrics']['max_successor_tv'] == 0.
    exact_record, exact, exact_mapping = audit.reference_record(full, oracle, Fraction(0), Counter())
    exact_plan = audit.exact_plan(exact, QUERY)
    exact_actual = audit.policy_replay(full, {state: exact_plan['policy'][exact_mapping[state]] for state in full['actions']})
    assert all(exact_actual[state] == oracle['q']['vectors'][state] for state in full['cells'])
    assert exact_record['metrics']['active_cells'] == 4


def test_quantization_keeps_layer_status_legal_mask_and_exact_bin_boundaries():
    inputs = {'below': payload(Fraction(255, 65536)), 'boundary': payload(Fraction(1, 256)),
              'different_mask': payload(Fraction(1, 256), second_action=True)}
    full = audit.disjoint_union(inputs)
    oracle = {'q': audit.exact_plan(full, QUERY)}
    mapping, members = audit.group_states(full, oracle, Fraction(1, 256))
    assert len({mapping[root] for root in full['roots']}) == 2
    children = [state for state, origin in full['origins'].items() if origin['native_state'] == 1]
    assert len({mapping[child] for child in children}) == 3
    for states in members.values():
        assert len({full['cells'][state] for state in states}) == 1
        assert len({full['actions'].get(state, ()) for state in states}) == 1
    assert mapping == audit.group_states(full, dict(reversed(list(oracle.items()))), Fraction(1, 256))[0]


def test_full_curve_positive_control_routing_and_saved_native_model_policy_tampering():
    data = audit.reconstruct({'case00': payload(Fraction(1, 10)), 'case01': payload(Fraction(1, 5))}, {'q': QUERY})
    assert len(data['compiled']['models']) == len(data['choices']['width_records']) == len(data['summary']['curve']) == 6
    assert data['summary']['positive_control_valid']
    assert data['summary']['routing']['qualifying_widths'] == []
    assert all(row['max_active_regret'] == 0. for row in data['summary']['curve'])
    assert data['summary']['curve'][-1]['max_active_prediction_error'] == [.05, 0., 0.]
    saved = deepcopy(data)
    saved['compiled']['models'][0]['model']['rows'][0][2][0][3] += 1
    assert not audit.same(saved['compiled'], data['compiled'])
    saved = deepcopy(data)
    saved['choices']['width_records'][0]['queries'][0]['policy'][0][1] = 'UP'
    assert not audit.same(saved['choices'], data['choices'])
    saved = deepcopy(data)
    saved['summary']['curve'][-1]['qualifies'] = True
    assert not audit.same(saved['summary'], data['summary'])
