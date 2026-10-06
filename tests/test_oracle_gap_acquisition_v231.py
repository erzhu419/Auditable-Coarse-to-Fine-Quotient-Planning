from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import oracle_gap_acquisition_v231 as acquisition


def empty():
    return {op: dict.fromkeys(categories, 0)
            for op, categories in acquisition.ALPHABETS.items()}


def plan(goal=F(1), risk=F(1), utility=F(2)):
    posterior = {op: {cat: F(1, len(categories)) for cat in categories}
                 for op, categories in acquisition.ALPHABETS.items()}
    return dict(
        utility_lower=utility, goal_impossible=False,
        query_ready=max(goal, risk) <= acquisition.THRESHOLD,
        query_certificates={
            q: dict(policy='SHORT', regret_upper=gap,
                    certified=gap <= acquisition.THRESHOLD)
            for q, gap in (('goal', goal), ('risk', risk))},
        posterior=posterior, case=dict(operating='high', retry_cost='17/20'),
        envelopes={op: dict(bounds={cat: [F(0), F(1)] for cat in categories})
                   for op, categories in acquisition.ALPHABETS.items()},
        query_gap_bounds={q: {policy: gap for policy in acquisition.POLICIES}
                          for q, gap in (('goal', goal), ('risk', risk))},
        effective_n=dict.fromkeys(acquisition.OPERATORS, 0))


def test_nonmax_query_can_drive_acquisition_and_no_evidence_is_mutated():
    member, initial, work = empty(), plan(goal=F(1), risk=F(1, 2)), Counter()
    initial['query_gap_bounds']['goal'] = {
        'WAIT': F(0), 'SHORT': F(0), 'DETOUR_RETURN': F(1), 'DETOUR_RETRY': F(0)}
    initial['query_gap_bounds']['risk'] = {
        'WAIT': F(0), 'SHORT': F(0), 'DETOUR_RETURN': F(0), 'DETOUR_RETRY': F(1, 2)}
    initial['effective_n'].update(SHORT_PASS=100000, DETOUR_PASS=100000)
    before = deepcopy((member, initial))

    result = acquisition.choose(member, initial, 0, work)
    # The worst goal query cannot depend on recovery.  The unresolved risk
    # comparison nevertheless receives acquisition weight instead of vanishing.
    assert result['query_influence']['RECOVERY_RETRY'] > 0
    assert result['operator'] == 'RECOVERY_RETRY'
    assert (member, initial) == before
    assert work['oracle_gap_direct_choices'] == 1
    assert 'oracle_gap_computed_forecasts' not in work
    assert 'environment_random_draws' not in work and 'controlled_samples' not in work


def test_gap_influence_targets_uncertain_blocking_operator():
    initial = plan(goal=F(1), risk=F(0))
    initial['query_gap_bounds']['goal'] = {
        'WAIT': F(0), 'SHORT': F(0), 'DETOUR_RETURN': F(0), 'DETOUR_RETRY': F(1)}
    for op in ('SHORT_PASS', 'RECOVERY_RETRY'):
        initial['envelopes'][op]['bounds'] = {
            cat: [F(49, 100), F(51, 100)] for cat in acquisition.ALPHABETS[op]}
    member = empty()
    member['DETOUR_PASS']['DELIVERY'] = 16

    result = acquisition.choose(member, initial, 16, Counter())
    assert result['operator'] == 'DETOUR_PASS'
    assert result['query_influence']['DETOUR_PASS'] > result['query_influence']['SHORT_PASS']


def test_pooled_sample_count_changes_acquisition_without_changing_gap_width():
    initial = plan(goal=F(1), risk=F(0))
    initial['query_gap_bounds']['goal'] = {
        'WAIT': F(0), 'SHORT': F(0), 'DETOUR_RETURN': F(1), 'DETOUR_RETRY': F(0)}
    initial['effective_n']['SHORT_PASS'] = 1024
    member = empty()
    member['DETOUR_PASS']['DELIVERY'] = 16

    result = acquisition.choose(member, initial, 16, Counter())
    assert result['query_influence']['SHORT_PASS'] == result['query_influence']['DETOUR_PASS']
    assert result['contraction']['SHORT_PASS'] < result['contraction']['DETOUR_PASS']
    assert result['operator'] == 'DETOUR_PASS'


def test_execution_deficit_remains_active_after_all_query_certificates():
    initial = plan(F(0), F(0), utility=F(1))
    initial['effective_n']['SHORT_PASS'] = 1024
    result = acquisition.choose(empty(), initial, 0, Counter())
    assert result['operator'] == 'DETOUR_PASS'
    assert all(value == 0 for value in result['query_influence'].values())
    assert any(value > 0 for value in result['execution_influence'].values())
    initial['goal_impossible'] = True
    assert acquisition.choose(empty(), initial, 0, Counter()) is None


def test_stop_performs_no_acquisition_and_zero_gap_ties_use_actual_member_counts():
    work = Counter()
    assert acquisition.choose(empty(), plan(F(0), F(0)), 0, work) is None
    assert acquisition.choose(empty(), plan(), 384, work) is None
    assert work == Counter()
    initial = plan()
    initial['envelopes'] = {
        op: dict(bounds={cat: [value, value] for cat, value in row.items()})
        for op, row in initial['posterior'].items()}
    member = empty()
    member['SHORT_PASS']['DELIVERY'] = 16
    result = acquisition.choose(member, initial, 16, work)
    assert not any(result['scores'].values())
    assert result['operator'] == 'DETOUR_PASS'
