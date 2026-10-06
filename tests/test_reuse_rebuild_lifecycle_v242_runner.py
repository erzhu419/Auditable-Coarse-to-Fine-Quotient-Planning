"""Synthetic checks for the separate member and complete-life paid budgets."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from io import StringIO

from scripts import run_reuse_rebuild_lifecycle_v242 as runner


def setup(monkeypatch, stop_after):
    calls, reads = [], []
    state = dict(a=dict(pools=[runner.core.empty() for _ in range(3)]))
    case = dict(id='synthetic', context='A', stage='A', operating='high', retry_cost='19/20')

    def make_plan(member, case, state, identity, index, cache, work):
        n = sum(sum(row.values()) for row in member.values())
        pool_n = sum(sum(row.values()) for row in state['a']['pools'][identity].values())
        calls.append((n, pool_n))
        certified = n >= stop_after
        decisions = {'reward': dict(policy='WAIT', certified=True)}
        for query in ('goal', 'risk'):
            decisions[query] = dict(policy='WAIT', certified=certified, comparisons=[
                dict(query=query, chosen='WAIT', other=other, family='S',
                    projected_counts={'S': {'DELIVERY': n, 'LOST': 0}}, certified=certified)
                for other in ('SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')])
        return dict(case=case, mix=[('WAIT', F(1))], utility_lower=F(2 if certified else 0),
            goal_impossible=False, query_ready=certified,
            query_evidence=dict(queries=decisions, all_ready=certified, threshold=960))

    def draw(generator, law, operator, increments, number, work, progress):
        reads.append((operator, number))
        increments['DELIVERY'] += number
        progress['draw_end'] += number

    monkeypatch.setattr(runner.core, 'make_plan', make_plan)
    monkeypatch.setattr(runner, 'draw', draw)
    monkeypatch.setattr(runner.acquisition, 'choose', lambda member, plan, spent, work:
        dict(operator=runner.OPERATORS[spent//16 % 3], reason='synthetic'))
    return state, case, calls, reads


def target(state, case, history, profiles, ids):
    return runner.run_target(0, 3, case, 0, state, 'REUSE', object(), Counter(),
        3456, history, {}, profiles, ids)


def test_life_budget_stops_real_reads_before_member_cap_and_updates_once(monkeypatch):
    state, case, calls, reads = setup(monkeypatch, 10000)
    profiles, ids = StringIO(), {}
    row = target(state, case, 9504, profiles, ids)
    assert row['spent'] == row['new_paid_samples'] == 32
    assert row['life_budget_remaining_before'] == 32 and row['life_budget_remaining_after'] == 0
    assert row['budget_exhausted'] and not row['member_cap_exhausted']
    assert calls == [(0, 0), (16, 16), (32, 32)] and len(reads) == 2
    assert row['total_reference_paid_samples'] == 3456+9504+32
    assert row['fallback'] and row['executed_mix'] == [('WAIT', F(1))]
    assert row['terminal_plan'] == row['batches'][-1]['plan']
    assert row['initial_plan']['query_evidence']['queries']['goal']['comparisons'][0]['profile_id'] == 0
    assert len(profiles.getvalue().splitlines()) == len(ids) == 18


def test_exhausted_life_still_retains_current_plan_without_new_reads(monkeypatch):
    state, case, calls, reads = setup(monkeypatch, 10000)
    row = target(state, case, 9536, StringIO(), {})
    assert calls == [(0, 0)] and reads == []
    assert row['spent'] == 0 and row['batches'] == []
    assert row['terminal_plan'] == row['initial_plan']
    assert row['budget_exhausted'] and not row['query_certified']
    assert row['pooled_before'] == row['pooled_after']


def test_initial_certificate_stops_and_proof_retention_does_not_charge_observations(monkeypatch):
    state, case, calls, reads = setup(monkeypatch, 0)
    profiles, ids = StringIO(), {}
    row = target(state, case, 0, profiles, ids)
    saved = deepcopy(row)
    again = target(state, case, 0, profiles, ids)
    assert reads == [] and calls == [(0, 0), (0, 0)]
    assert row['joint_completed'] and not row['fallback'] and row['spent'] == 0
    for recorded in (again, saved):
        recorded.pop('model_seconds')
        recorded.pop('observation_seconds')
    assert again == saved
    assert len(profiles.getvalue().splitlines()) == len(ids) == 6
    assert row['total_reference_paid_samples'] == 3456


def test_wait_fallback_records_wait_bounds_and_preserves_planned_certificate(monkeypatch):
    plan = dict(mix=[('SHORT', F(1))], utility_lower=F(2), risk_upper=F(1, 20),
        goal_upper=F(3), goal_impossible=False,
        queries={query: dict(policy='SHORT') for query in ('reward', 'goal', 'risk')},
        query_certificates={query: dict(certified=False) for query in ('reward', 'goal', 'risk')})
    row = dict(life=0, index=3, arm='REUSE', case=dict(stage='A'), spent=0,
        initial_plan=plan, terminal_plan=plan, batches=[], model_seconds=0.,
        execution_certified=True, goal_impossible=False, query_certified=False,
        joint_completed=False, budget_exhausted=False, fallback=True, executed_mix=[('WAIT', '1')])
    before = deepcopy(row)
    monkeypatch.setattr(runner, 'restored_plan', deepcopy)
    monkeypatch.setattr(runner, 'oracle_goal', lambda *args: F(3))
    monkeypatch.setattr(runner, 'query_score', lambda *args: {
        query: dict(regret=F(0)) for query in ('reward', 'goal', 'risk')})

    def score(active, law, case, spent):
        return dict(actual_utility=F(0) if active['mix'][0][0] == 'WAIT' else F(3),
            utility_lower=active['utility_lower'], risk_upper=active['risk_upper'], violation=False)

    monkeypatch.setattr(runner, 'score', score)
    result = runner.evaluate(row, object())
    assert result['executed']['actual_utility'] == result['executed']['utility_lower'] == 0
    assert result['executed']['risk_upper'] == 0
    assert result['history'][0]['utility_lower'] == 2
    assert row == before
