from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import bidirectional_pool_v243 as pool

S, D, R = pool.OPERATORS
MAPPING = (1, 2, 0)


def anchors(context):
    row = ({S: {'DELIVERY': 310, 'LOST': 74},
        D: {'DELIVERY': 340, 'RECOVERY': 36, 'LOST': 8},
        R: {'DELIVERY': 80, 'LOST': 304}} if context == 'A' else
        {S: {'DELIVERY': 40, 'LOST': 88},
         D: {'DELIVERY': 112, 'RECOVERY': 12, 'LOST': 4},
         R: {'DELIVERY': 20, 'LOST': 108}})
    result = []
    for identity in range(3):
        counts = deepcopy(row)
        for operator in pool.OPERATORS:
            counts[operator]['DELIVERY'] += identity
            counts[operator]['LOST'] -= identity
        result.append(counts)
    return result


def case(stage):
    return dict(context='B' if stage == 'B' else 'A', stage=stage,
                operating='low', retry_cost='17/20')


def increments(operator, number=16):
    return {category: number*int(category == 'DELIVERY')
            for category in pool.ALPHABETS[operator]}


def states(changed=S):
    result = {}
    for arm in pool.ARMS:
        state = pool.prepare(anchors('A'), 0, arm, Counter())
        for operator in pool.OPERATORS:
            pool.observe(state, case('A'), 1, operator, increments(operator))
        pool.begin_b(state, anchors('B'), changed, MAPPING, Counter())
        for identity in range(3):
            for operator in pool.OPERATORS:
                pool.observe(state, case('B'), identity, operator, increments(operator, 16*(identity+1)))
        result[arm] = state
    return result


def test_one_way_and_two_way_are_identical_before_return_and_rebuild_uses_native_b():
    all_states, member = states(), pool.empty()
    for stage, identity, index in [('A', 1, 3), ('B', 0, 30)]:
        one, two = (all_states[arm] for arm in ('ONE_WAY', 'TWO_WAY'))
        assert pool.point_counts(case(stage), one, identity) == pool.point_counts(case(stage), two, identity)
        assert pool.regions(member, case(stage), one, identity, index) == pool.regions(
            member, case(stage), two, identity, index)
        assert one['return_merge'] is two['return_merge'] is None
    native = all_states['REBUILD']['b']['pools'][0]
    assert pool.point_counts(case('B'), all_states['REBUILD'], 0) == native
    regions = pool.regions(member, case('B'), all_states['REBUILD'], 0, 30)
    assert all(len(row) == 3 for row in regions.values())


@pytest.mark.parametrize('changed', pool.OPERATORS)
def test_return_maps_native_b_once_excludes_changed_row_and_retains_existing_events(changed):
    all_states = states(changed)
    state, member = all_states['TWO_WAY'], pool.empty()
    before = deepcopy((state['a'], state['b'], state['a_at_switch']))
    counts = pool.point_counts(case('A_RETURN'), state, 1)
    a_native, b_native = state['a']['pools'][1], state['b']['pools'][0]
    for operator in pool.OPERATORS:
        expected = {category: value+(0 if operator == changed else b_native[operator][category])
                    for category, value in a_native[operator].items()}
        assert counts[operator] == expected
    # Adding B point counts would incorrectly add the inherited A row again.
    assert sum(sum(row.values()) for row in counts.values()) == 3*400+2*144
    constraints = pool.regions(member, case('A_RETURN'), state, 1, 54)
    assert (state['a'], state['b'], state['a_at_switch']) == before
    for operator in pool.OPERATORS:
        own = pool.regions(member, case('A_RETURN'), all_states['ONE_WAY'], 1, 54)[operator]
        assert constraints[operator][:3] == own
        if operator == changed:
            assert len(constraints[operator]) == 3
        else:
            assert constraints[operator][3:] == [
                dict(counts=state['b']['sources'][0][operator], threshold=720,
                     event=f'l0/B/pool0/{operator}'),
                dict(counts=state['b']['pools'][0][operator], threshold=720,
                     event=f'l0/B/pool0/{operator}')]
    ledger = state['return_merge']
    assert ledger['first_target_index'] == 54
    assert len(ledger['rows']) == 6
    assert ledger['total_source_samples'] == 6*128
    assert ledger['total_target_samples'] == 2*(16+32+48)
    assert ledger['total_samples'] == 960
    assert {(row['a_identity'], row['b_identity']) for row in ledger['rows']} == {(1, 0), (2, 1), (0, 2)}


def test_repeated_return_updates_native_a_only_and_merge_ledger_is_one_snapshot():
    state = states()['TWO_WAY']
    member = pool.empty()
    before = pool.point_counts(case('A_RETURN'), state, 1)
    pool.regions(member, case('A_RETURN'), state, 1, 54)
    b_before, switch_before = deepcopy(state['b']), deepcopy(state['a_at_switch'])
    ledger_before = deepcopy(state['return_merge'])
    for index in (54, 55):
        increment = increments(D)
        pool.observe(state, case('A_RETURN'), 1, D, increment)
        for category, number in increment.items():
            member[D][category] += number
        pool.regions(member, case('A_RETURN'), state, 1, index)
    after = pool.point_counts(case('A_RETURN'), state, 1)
    assert after[D]['DELIVERY'] == before[D]['DELIVERY']+32
    assert after[S] == before[S] and after[R] == before[R]
    assert state['b'] == b_before and state['a_at_switch'] == switch_before
    assert state['return_merge'] == ledger_before
    assert state['a']['pools'][1][D]['DELIVERY'] == anchors('A')[1][D]['DELIVERY']+16+32


def test_return_plan_forwards_counts_and_regions_to_the_unchanged_v242_engine(monkeypatch):
    state = states()['TWO_WAY']
    member, cache = pool.empty(), {}
    increment = increments(D)
    pool.observe(state, case('A_RETURN'), 1, D, increment)
    member[D] = increment
    calls = []

    def planner(constraints, observed, actual_case, actual_cache, work):
        assert actual_cache is cache
        calls.append((deepcopy(constraints), deepcopy(observed), deepcopy(actual_case)))
        return dict(evidence_counts=observed, joint_constraints=constraints)

    monkeypatch.setattr(pool.original, 'plan_from_evidence', planner)
    plan = pool.make_plan(member, case('A_RETURN'), state, 1, 54, cache, Counter())
    assert calls[0][1] == pool.point_counts(case('A_RETURN'), state, 1)
    assert sum(plan['evidence_counts'][D].values()) == 400+16+144
    assert plan['joint_constraints'][D][2]['counts'] == member[D]
    transfer = plan['return_transfer']
    assert transfer['a_identity'] == 1 and transfer['mapped_b_identity'] == 0
    assert tuple(transfer['operators']) == (D, R)
    assert transfer['total_samples'] == 2*144
    assert transfer['transferred_counts'] == {operator: state['b']['pools'][0][operator] for operator in (D, R)}
    pre_return = pool.make_plan(pool.empty(), case('B'), state, 0, 30, cache, Counter())
    assert pre_return['return_transfer'] is None
