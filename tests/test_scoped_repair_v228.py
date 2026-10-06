from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import scoped_repair_v228 as core
from acfqp.science import scoped_route_task_v228 as task


def counts(law, n):
    result = core.empty()
    for op, row in law.items():
        for cat, p in row.items():
            amount = n*p
            assert amount.denominator == 1
            result[op][cat] = int(amount)
    return result


def setup(arm, life=0):
    cases, laws, identities, metadata = task.world(life)
    work = Counter()
    state = core.prepare([counts(laws[i], 10000) for i in range(3)], arm, work)
    a_case = cases[3]; a_member = counts(laws[3], 100)
    a_plan = core.make_plan(a_member, a_case, state, work)
    core.advance(state, a_member, a_case, a_plan, work)
    core.begin_b(state, [counts(laws[i], 10000) for i in (27, 28, 29)], work)
    return state, work, cases, laws, identities, metadata


def test_matched_rebuild_retains_all_b_members_and_repair_covers_hidden_mapping():
    for life in range(3):
        states = [setup(arm, life) for arm in core.ARMS]
        for state, work, cases, laws, identities, metadata in states:
            before = deepcopy(state['a'])
            case, member = cases[30], counts(laws[30], 100)
            plan = core.make_plan(member, case, state, work)
            assert plan['mode'] == 'library'
            assert {label['index'] for label in plan['candidate_labels'].values()} == {identities[30]}
            if state['arm'] != 'REBUILD_CS':
                true = metadata['changed_operator']+':'+''.join(map(str, metadata['b_to_a']))
                assert true in state['b'] and not state['b'][true]['no_feasible']
                box = plan['candidate_envelopes'][true+'/'+str(identities[30])]
                assert all(lo <= laws[30][op][cat] <= hi for op, row in box.items()
                           for cat, (lo, hi) in row['bounds'].items())
            core.advance(state, member, case, plan, work)
            assert all(bank['members'] == [member] for bank in state['b'].values())
            assert state['a'] == before
        repair, rebuild = states[0][0], states[1][0]
        assert next(iter(repair['b'].values()))['anchor_counts'] == rebuild['b']['rebuild']['anchor_counts']


def test_parameter_point_commits_do_not_reestimate_confidence_or_mix_a_counts():
    state, work, cases, laws, identities, _ = setup('PARAM')
    case, member = cases[30], counts(laws[30], 100)
    plan = core.make_plan(member, case, state, work)
    initial = {name: deepcopy(bank['bounds']) for name, bank in state['b'].items()}
    points = deepcopy(state['b_points'])
    event = core.advance(state, member, case, plan, work)
    assert event['point_commit'] == dict(index=identities[30], samples=300)
    assert state['b_points'][identities[30]] == core._plus(points[identities[30]], member)
    for name, bank in state['b'].items():
        if not bank['no_feasible']:
            assert bank['bounds'] == initial[name]
        assert bank['anchor_counts'] == points


def test_b_acquisition_forecasts_are_read_only_and_return_a_keeps_b_separate():
    state, work, cases, laws, _, _ = setup('REPAIR_CS')
    member = core.empty(); plan = core.make_plan(member, cases[30], state, work)
    before = deepcopy(state)
    choice = core.choose(member, cases[30], state, plan, 0, work)
    if choice is not None:
        assert choice['operator'] in core.OPERATORS
    assert state == before and member == core.empty()
    assert core.choose(member, cases[30], state, plan, core.TARGET_CAP, work) is None
    b_before = deepcopy(state['b']); a_before = deepcopy(state['a']['members'])
    returned = counts(laws[54], 100)
    plan = core.make_plan(returned, cases[54], state, work)
    core.advance(state, returned, cases[54], plan, work)
    assert state['a']['members'] == a_before+[returned]
    assert state['b'] == b_before


def test_query_and_goal_eligibility_remain_separate_and_regret_is_covered():
    for arm in core.ARMS:
        state, work, cases, laws, _, _ = setup(arm)
        for index in (30, 54):
            plan = core.make_plan(counts(laws[index], 100), cases[index], state, work)
            result = core.finish(plan)
            assert result['execution_plan'] is result['knowledge_plan'] is plan
            assert result['query_certified'] == plan['query_ready']
            assert result['execution_certified'] == (plan['utility_lower'] >= 2)
            assert result['goal_impossible'] == (plan['goal_upper'] < 2)
            pure = core.mechanics.vectors(cases[index], laws[index])
            for query, weights in core.query_bounds.WEIGHTS.items():
                chosen = plan['queries'][query]['policy']
                values = {name: core.query_bounds.utility(vector, weights) for name, vector in pure.items()}
                regret = max(values.values())-values[chosen]
                assert F(0) <= regret <= plan['query_certificates'][query]['regret_upper']


def test_declared_b_goal_can_be_proven_impossible_without_lowering_the_threshold():
    state, work, cases, laws, identities, _ = setup('REPAIR_CS')
    index = next(i for i in range(30,54)
                 if laws[i]['SHORT_PASS']['DELIVERY']==F(1,100))
    plan = core.make_plan(counts(laws[index], 100), cases[index], state, work)
    assert plan['goal_impossible'] and plan['goal_upper'] < 2
    assert not core.finish(plan)['execution_certified']
    if plan['query_ready']:
        assert core.choose(counts(laws[index],100), cases[index], state, plan,300,work) is None


def test_point_prediction_uses_source_types_without_hypothesis_multiplicity_weights():
    cases, laws, _, _ = task.world(0)
    work = Counter()
    state = core.prepare([counts(laws[i],10000) for i in range(3)], 'REPAIR_CS', work)
    core.begin_b(state,[counts(laws[i],100) for i in (27,28,29)],work)
    member = core.empty()
    plan = core.make_plan(member,cases[30],state,work)
    indices = {label['index'] for label in plan['candidate_labels'].values()}
    assert len(indices) > 1
    means = [core.mechanics.posterior(state['b_points'][i]) for i in sorted(indices)]
    expected = {op:{cat:sum(mean[op][cat] for mean in means)/len(means)
                    for cat in core.ALPHABETS[op]} for op in core.OPERATORS}
    assert plan['posterior'] == expected
