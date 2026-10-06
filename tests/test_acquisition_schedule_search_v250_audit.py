from collections import Counter
from copy import deepcopy
from io import StringIO
import json
import random

from scripts import audit_acquisition_schedule_search_v250 as audit


def test_literal_roster_order_and_full_context_quotas():
    plans = audit.literal_plans()
    assert [plan['candidate'] for plan in plans] == [
        'SD128_B0', 'SD128_B384', 'SD512_B0', 'SD512_B384',
        'SD1024_B0', 'SD1024_B384', 'ALL512_B0', 'ALL512_B384']
    assert [plan['order'] for plan in plans] == list(range(8))
    assert [plan['quota_samples'] for plan in plans] == [768, 1920, 3072, 4224, 6144, 7296, 4608, 5760]
    assert sum(plan['quota_samples'] for plan in plans)*3 == 101376
    assert plans[0]['a_row_samples']['RECOVERY_RETRY'] == 0
    assert plans[6]['a_row_samples']['RECOVERY_RETRY'] == 512


def test_pre_A_actual_source_cost_and_pending_B_are_reserved_once():
    early = audit.budget_values(0, 'SD1024_B384', 3, 0, 6144)
    assert early == dict(source_paid=3456, quota=7296, available=2240,
        pending_probe=1152, future_source=1152, reference_paid=9600, adaptive_after=2240)
    later = audit.budget_values(0, 'SD1024_B384', 30, 128, 7296, 16)
    assert later['available'] == 2112 and later['adaptive_after'] == 2096
    assert later['pending_probe'] == later['future_source'] == 0
    assert later['reference_paid'] == 4608+7296+128+16


def test_contextual_probe_seed_operator_index_and_continuing_prefix():
    _, laws, _, _ = audit.paid.world(0)
    operator = 'DETOUR_PASS'
    short = audit.expected_probe_batches(0, 'A', 1, {operator: 128}, laws[1])
    long = audit.expected_probe_batches(0, 'A', 1, {operator: 512}, laws[1])
    assert short == long[:8]
    assert [row['draw_start'] for row in long] == list(range(0, 512, 16))
    assert all(row['seed'] == 294004 for row in long)
    generator = random.Random(294004)
    assert [row['increments'] for row in long] == [audit.paid.draw(generator, laws[1], operator) for _ in range(32)]
    b_rows = audit.expected_probe_batches(0, 'B', 1, {operator: 128}, laws[28])
    assert all(row['seed'] == 294013 and row['context'] == 'B' for row in b_rows)


def test_actual_producer_probe_tapes_replay_A_then_changed_native_B():
    from scripts import run_acquisition_schedule_search_v250 as producer
    life, candidate = 0, 'SD128_B384'
    sources = next(row for row in json.loads((audit.SOURCE/'source_evidence.json').read_text()) if row['life'] == life)
    cases, laws, identities, metadata = audit.paid.world(life)
    spec = next(plan for plan in producer.PLANS if plan['candidate'] == candidate)
    bundle = dict(cases=cases, laws=laws, identities=identities, metadata=metadata)
    work, stream, generators, offsets = Counter(), StringIO(), {}, {}
    state = producer.core.prepare(sources['a'], life, 'ONE_WAY', work)
    independent = dict(a=deepcopy(sources['a']), b=None, a_switch=None)
    original_sources, member = deepcopy(sources), audit.paid.empty()
    result = producer.context_probes(life, spec, 'A', state, bundle, 0, 0,
                                    work, stream, generators, offsets)
    records = iter(json.loads(line) for line in stream.getvalue().splitlines())
    checks, paid = [], 0
    check = lambda name, valid: checks.append((name, valid))
    for trigger, context, identity, amounts in audit.probe_schedule(candidate, metadata['changed_operator']):
        if context == 'A':
            paid = audit.replay_probe_group(records, life, candidate, context, identity, trigger,
                amounts, independent, laws[identity], 0, paid, check)
    assert next(records, None) is None and all(valid for _, valid in checks)
    assert paid == result['paid_samples'] == 768 and state['a']['pools'] == independent['a']
    assert state['a']['sources'] == original_sources['a'] and state['b'] is None
    producer.core.begin_b(state, sources['b'], metadata['changed_operator'], metadata['b_to_a'], work)
    independent['a_switch'], independent['b'] = deepcopy(independent['a']), deepcopy(sources['b'])
    frozen_switch = deepcopy(state['a_at_switch'])
    stream = StringIO()
    result = producer.context_probes(life, spec, 'B', state, bundle, 32, paid,
                                    work, stream, generators, offsets)
    records = iter(json.loads(line) for line in stream.getvalue().splitlines())
    for trigger, context, identity, amounts in audit.probe_schedule(candidate, metadata['changed_operator']):
        if context == 'B':
            paid = audit.replay_probe_group(records, life, candidate, context, identity, trigger,
                amounts, independent, laws[27+identity], 32, paid, check)
    assert next(records, None) is None and all(valid for _, valid in checks)
    assert paid == result['paid_samples'] == 1920
    assert state['b']['pools'] == independent['b'] and state['b']['sources'] == original_sources['b']
    assert state['a_at_switch'] == frozen_switch and state['a']['sources'] == original_sources['a']
    assert audit.paid.samples(member) == 0 and sources == original_sources
    observed = audit.prior.evidence_counts(independent, cases[30], identities[30], 'ONE_WAY', metadata)
    assert observed == producer.core.point_counts(cases[30], state, identities[30])
    assert observed[metadata['changed_operator']] == independent['b'][identities[30]][metadata['changed_operator']]


def method_fixture(candidate, cost, joint=132):
    method = dict(candidate=candidate, order=audit.PLAN_IDS.index(candidate), total_samples=cost,
                  joint_completed=joint, late_b=dict(query_certified=27), a_return=dict(query_certified=54))
    method.update(dict.fromkeys(('false_query_certificates', 'false_execution_certificates',
        'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations'), 0))
    quality, qualification = audit.conditions(method, [True]*3)
    method.update(budget_quality_feasible=all(quality.values()), qualification_witness=all(qualification.values()))
    return method


def test_two_winners_are_independent_and_quality_is_not_rejected_by_cost_reference():
    methods = [method_fixture('SD128_B0', 48000), method_fixture('SD512_B0', 47700, 131),
               method_fixture('ALL512_B0', 47790)]
    assert all(method['budget_quality_feasible'] for method in methods)
    assert [method['qualification_witness'] for method in methods] == [False, False, True]
    assert audit.winner(methods, 'budget_quality_feasible') == 'SD512_B0'
    assert audit.winner(methods, 'qualification_witness') == 'ALL512_B0'
    quality, qualification = audit.conditions(methods[0], [True, False, True])
    assert not quality['per_life_budget_valid'] and not all(qualification.values())
    methods[0]['false_goal_uppers'] = 1
    assert not audit.conditions(methods[0], [True]*3)[0]['valid_certificates_and_execution']


def test_winner_uses_cost_then_joint_then_literal_declaration_and_empty_set():
    methods = [method_fixture('SD512_B0', 40000, 141), method_fixture('SD128_B384', 40000, 141),
               method_fixture('SD128_B0', 40000, 140)]
    assert audit.winner(methods, 'qualification_witness') == 'SD128_B384'
    methods[-1]['total_samples'] -= 16
    assert audit.winner(methods, 'qualification_witness') == 'SD128_B0'
    assert audit.winner([], 'qualification_witness') is None


def test_summary_matches_actual_producer_schema_for_complete_candidate_roster():
    from scripts import run_acquisition_schedule_search_v250 as producer
    records = []
    for life in audit.LIVES:
        cases, _, identities, _ = audit.paid.world(life)
        for candidate in audit.PLAN_IDS:
            for index in audit.TARGETS:
                point = dict(false_query_certificates=0, false_execution_certificate=False,
                    false_impossible_certificate=False, goal_upper_ok=True, violation=False, coverage=True)
                records.append(dict(life=life, index=index, arm=candidate, candidate=candidate,
                    identity=identities[index], stage=cases[index]['stage'], spent=16,
                    query_certified=True, joint_completed=True, execution_certified=True,
                    goal_impossible=False, fallback=False, budget_exhausted=False, model_seconds=.01,
                    history=[point], executed=dict(violation=False, actual_utility=3)))
    scopes = ('planning', 'initialization', 'begin_b', 'probe_pool_updates', 'acquisition', 'observation', 'probe_draw')
    timings = {scope: {candidate: {life: 0. for life in audit.LIVES} for candidate in audit.PLAN_IDS} for scope in scopes}
    actual = producer.summarize(records, timings)
    saved_timings = {scope: {candidate: {str(life): value for life, value in values.items()}
                            for candidate, values in candidates.items()} for scope, candidates in timings.items()}
    candidates, lives = audit.summaries(records, saved_timings)
    assert actual['candidates'] == candidates and actual['life_summaries'] == lives
    assert actual['selected'] == audit.winner(candidates, 'qualification_witness')
    assert actual['budget_quality_witness'] == audit.winner(candidates, 'budget_quality_feasible')
    assert actual['physical_probe_samples'] == 101376
    assert actual['new_environment_observations'] == 101376+1728*16
