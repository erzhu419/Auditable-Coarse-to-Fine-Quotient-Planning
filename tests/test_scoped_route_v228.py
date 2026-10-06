from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import scoped_queries_v228 as queries
from acfqp.science import latent_mechanisms_v213 as mechanics
from acfqp.science import structured_route_task_v201 as oracle


def box_for(law, radius=F(0)):
    return {op: dict(bounds={cat: [max(F(0), probability-radius), min(F(1), probability+radius)]
                             for cat, probability in row.items()}) for op, row in law.items()}


def query_for(case, law):
    return mechanics.queries(dict(pure_vectors=mechanics.vectors(case, law)))


def test_public_scopes_have_fresh_cases_balanced_types_and_only_one_changed_row():
    for life in range(3):
        cases, laws, identities, metadata = task.world(life)
        assert len(cases) == len(laws) == len(identities) == 78
        assert len({case['id'] for case in cases}) == 78
        assert all(set(case) == {'id', 'operating', 'retry_cost', 'context', 'stage'} for case in cases)
        assert metadata['changed_operator'] == task.OPERATORS[life]
        for stage, (start, end) in metadata['stage_ranges'].items():
            assert Counter(identities[start:end]) == {0: 8, 1: 8, 2: 8}
            assert set(Counter((case['operating'], case['retry_cost']) for case in cases[start:end]).values()) == {6}
            assert {case['context'] for case in cases[start:end]} == ({'B'} if stage == 'B' else {'A'})
            for index in range(start, end):
                a_identity = metadata['b_to_a'][identities[index]] if stage == 'B' else identities[index]
                base = laws[a_identity]
                changed = [op for op in task.OPERATORS if laws[index][op] != base[op]]
                assert changed == ([metadata['changed_operator']] if stage == 'B' else [])
                assert all(sum(row.values()) == 1 for row in laws[index].values())


def test_paid_b_source_order_has_hidden_mapping_and_return_reuses_only_a_laws():
    for life in range(12):
        cases, laws, identities, metadata = task.world(life)
        assert metadata['source_indexes'] == [0, 1, 2]
        assert metadata['b_source_indexes'] == [27, 28, 29]
        assert metadata['stage_ranges'] == dict(A=[3, 27], B=[30, 54], A_RETURN=[54, 78])
        assert sorted(metadata['b_to_a']) == [0, 1, 2]
        assert metadata['b_to_a'] != [0, 1, 2]
        for b_identity, index in enumerate(metadata['b_source_indexes']):
            assert identities[index] == b_identity
            a_identity = metadata['b_to_a'][b_identity]
            assert laws[index] == task.changed_law(laws[a_identity], metadata['changed_operator'])
            assert cases[index]['stage'] == 'B_SOURCE' and cases[index]['context'] == 'B'
            assert set(cases[index]) == {'id', 'operating', 'retry_cost', 'context', 'stage'}
        for index in range(*metadata['stage_ranges']['B']):
            assert laws[index] == laws[metadata['b_source_indexes'][identities[index]]]
        for index in range(*metadata['stage_ranges']['A_RETURN']):
            assert laws[index] == laws[identities[index]]
        assert not ({case['id'] for case in cases[3:27]} & {case['id'] for case in cases[54:78]})


def test_changed_law_does_not_mutate_the_retained_a_kernel():
    _, laws, _, _ = task.world(0)
    base = deepcopy(laws[0])
    altered = task.changed_law(laws[0], 'DETOUR_PASS')
    assert laws[0] == base
    assert altered['DETOUR_PASS']['LOST'] == base['DETOUR_PASS']['LOST']
    assert altered['DETOUR_PASS']['DELIVERY'] == base['DETOUR_PASS']['RECOVERY']


def test_vertex_regret_bound_contains_actual_kernel_regret():
    for life in range(3):
        cases, laws, _, _ = task.world(life)
        for index in (3, 30, 54):
            case, law = cases[index], laws[index]
            envelope = box_for(law, F(1, 10))
            selected = {query: dict(policy='WAIT') for query in queries.WEIGHTS}
            certificate = queries.certificates(case, envelope, selected, Counter())
            assert certificate['vertex_count'] <= 24
            pure = mechanics.vectors(case, law)
            for query, weights in queries.WEIGHTS.items():
                row = certificate['queries'][query]
                actual = {policy: queries.utility(vector, weights) for policy, vector in pure.items()}
                regret = max(actual.values()) - actual[row['policy']]
                assert 0 <= regret <= row['regret_upper']
                if query == 'goal':
                    assert regret > 0
                    assert not row['certified']
                for policy, value in actual.items():
                    low, high = row['utility_bounds'][policy]
                    assert low <= value <= high


def test_query_certificates_use_shared_kernel_and_need_no_execution_lower_bound():
    _, laws, _, _ = task.world(0)
    law = deepcopy(laws[0])
    law['DETOUR_PASS'] = dict(DELIVERY=F(3, 10), LOST=F(3, 5), RECOVERY=F(1, 10))
    law['SHORT_PASS'] = dict(DELIVERY=F(1, 10), LOST=F(9, 10))
    law['RECOVERY_RETRY'] = dict(DELIVERY=F(1), LOST=F(0))
    case = dict(operating='high', retry_cost='19/20')
    envelope = box_for(law)
    # Shared detour uncertainty cancels between RETURN and RETRY except for
    # recovery's improvement.  Its point goal utility is below the old 2 gate.
    envelope['DETOUR_PASS']['bounds'] = dict(DELIVERY=[F(3, 10), F(2, 5)],
                                            LOST=[F(1, 2), F(3, 5)],
                                            RECOVERY=[F(1, 10), F(1, 10)])
    points = query_for(case, law)
    certificate = queries.certificates(case, envelope, points)
    assert certificate['all_ready']
    row = certificate['queries']['goal']
    assert row['policy'] == 'DETOUR_RETRY' and row['regret_upper'] == 0
    assert row['utility_bounds']['DETOUR_RETRY'][1] < 2
    assert row['utility_bounds']['DETOUR_RETURN'][1] - row['utility_bounds']['DETOUR_RETRY'][0] > queries.THRESHOLD
    # WAIT is optimal for reward and certified independently of any goal LCB.
    assert certificate['queries']['reward']['policy'] == 'WAIT'


def test_vertices_cover_full_simplex_and_binary_support_endpoints():
    envelope = {op: dict(bounds={cat: [F(0), F(1)] for cat in task.ALPHABETS[op]})
                for op in task.OPERATORS}
    vertices = queries.box_vertices(envelope)
    assert len(vertices) == 12
    for vertex in vertices:
        assert all(sum(row.values()) == 1 for row in vertex.values())
        assert all(set(row.values()) <= {F(0), F(1)} for row in vertex.values())


def test_goal_upper_bounds_true_risk_constrained_optimum_and_point_box_is_exact():
    for life in range(3):
        cases, laws, _, metadata = task.world(life)
        for stage in task.STAGES:
            for index in range(*metadata['stage_ranges'][stage]):
                case, law = cases[index], laws[index]
                actual = oracle.hard_constraint(mechanics.vectors(case, law))['utility']
                assert queries.goal_upper(case, box_for(law)) == actual
                assert queries.goal_upper(case, box_for(law, F(1, 10))) >= actual


def test_true_b_goal_impossibility_is_resolved_without_lowering_the_goal():
    cases, laws, identities, metadata = task.world(0)
    wet_b_identity = metadata['b_source_labels'].index('wet')
    index = next(index for index in range(*metadata['stage_ranges']['B'])
                 if identities[index] == wet_b_identity)
    upper = queries.goal_upper(cases[index], box_for(laws[index]))
    assert upper < 2
    assert upper == oracle.hard_constraint(mechanics.vectors(cases[index], laws[index]))['utility']
