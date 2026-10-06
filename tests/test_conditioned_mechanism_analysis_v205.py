"""Four synthetic audits; no production source stream or lifecycle is run."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product

from scripts import analyze_conditioned_mechanisms_v205 as audit

F = Fraction


def synthetic_tables():
    source = {op: [] for op in audit.OPERATORS}; revision = {op: [] for op in audit.OPERATORS}
    values = {
        'normal': ((500, 12), (450, 4, 58), (128, 384)),
        'wet': ((510, 2), (300, 110, 102), (460, 52)),
        'blocked': ((330, 182), (410, 5, 97), (205, 307)),
    }
    for weather in values:
        for operating in ('low', 'high') if weather == 'normal' else ('high',):
            for retry in ('17/20', '19/20'):
                context = dict(id=f'synthetic_{weather}_{operating}_{retry}',
                               weather=weather, operating=operating, retry_cost=retry)
                for op, counts in zip(audit.OPERATORS, values[weather]):
                    row = dict(context=context, counts=dict(zip(audit.SUPPORT[op], counts)))
                    revision[op].append(row)
                    if weather == 'normal':
                        source[op].append(deepcopy(row))
    for tables in (source, revision):
        for rows in tables.values():
            rows.sort(key=lambda row: audit.projection(row['context']))
    return source, revision


def test_condition_revision_fixed_fields_and_identical_cold_pilot_rule():
    source_tables, revision_tables = synthetic_tables(); work = Counter()
    source = audit.fit_tables(source_tables, 'REVISED', work)
    revised = audit.fit_tables(revision_tables, 'REVISED', work)
    fixed = audit.fit_tables(revision_tables, 'FIXED', work, source['selected_fields'])
    cold = audit.fit_tables(revision_tables, 'FULL_CONTEXT', work)
    assert all(source['selected_fields'][op] == [] for op in audit.OPERATORS)
    assert all(revised['selected_fields'][op] == ['weather'] for op in audit.OPERATORS)
    assert fixed['selected_fields'] == source['selected_fields'] and fixed['tables'] == revised['tables']
    assert fixed['observations_used'] == revised['observations_used']
    case = dict(id='synthetic_new_wet_low', weather='wet', operating='low', retry_cost='17/20')
    original = deepcopy(revised); plan = audit.make_plan(revised, case, work)
    assert all(row['n'] == 0 for row in plan['envelopes'].values())
    assert not audit.choose(revised, case, plan, work)['pilot'] and revised == original
    choice = audit.choose(cold, case, audit.make_plan(cold, case, work), work)
    assert choice['pilot'] and choice['operator'] == 'SHORT_PASS' and choice['projection_counts']['SHORT_PASS'] == 0
    audit.update(cold, case, 'SHORT_PASS', dict(DELIVERY=16, LOST=0), work)
    choice = audit.choose(cold, case, audit.make_plan(cold, case, work), work)
    assert choice['pilot'] and choice['operator'] == 'DETOUR_PASS'
    assert all(type(n) is int for rows in cold['tables'].values() for row in rows for n in row['counts'].values())


def vertices(bounds):
    names = sorted(bounds); result = []
    for fixed in combinations(names, len(names)-1):
        remaining = next(name for name in names if name not in fixed)
        for endpoints in product(*(bounds[name] for name in fixed)):
            row = dict(zip(fixed, endpoints)); row[remaining] = 1-sum(endpoints)
            if bounds[remaining][0] <= row[remaining] <= bounds[remaining][1]:
                result.append(row)
    return result


def test_raw_member_boxes_and_common_whole_policy_risk_goal_extrema():
    case = dict(operating='low', retry_cost='17/20'); work = Counter()
    assert audit.interval(0, 0, work) == (F(0), F(1))
    assert audit.interval(0, 128, work)[1] > F(1, 20)
    weights = [('WAIT', F(1, 10)), ('SHORT', F(1, 5)), ('DETOUR_RETURN', F(3, 10)), ('DETOUR_RETRY', F(2, 5))]
    for retry_min in (F(1, 5), F(3, 10)):
        envelope = {
            'SHORT_PASS': dict(bounds=dict(DELIVERY=(F(7, 10), F(9, 10)), LOST=(F(1, 10), F(3, 10)))),
            'DETOUR_PASS': dict(bounds=dict(DELIVERY=(F(3, 5), F(4, 5)), LOST=(F(1, 20), F(1, 5)), RECOVERY=(F(1, 10), F(3, 10)))),
            'RECOVERY_RETRY': dict(bounds=dict(DELIVERY=(retry_min, F(2, 5)), LOST=(F(3, 5), 1-retry_min))),
        }
        outcomes = [audit.joint(weights, audit.vectors(case, dict(zip(audit.OPERATORS, triplet))), work)
                    for triplet in product(*(vertices(envelope[op]['bounds']) for op in audit.OPERATORS))]
        assert sum(weight*audit.risk_bounds(envelope)[name] for name, weight in weights) == max(row[1] for row in outcomes)
        assert sum(weight*audit.goal_bounds(envelope, case)[name] for name, weight in weights) == min(audit.goal(row) for row in outcomes)


def test_paired_stream_prefix_and_certificate_budget_boundaries():
    work = Counter(); probabilities = dict(DELIVERY=F(1, 4), LOST=F(3, 4))
    stream = audit.generate_prefix(7, 32, probabilities, ('DELIVERY', 'LOST'), work)
    counts16 = Counter(stream[:16]); counts32 = Counter(stream)
    assert counts32 == counts16+Counter(stream[16:32]) and work['regenerated_consumed_samples'] == 32
    assert audit.stop_reason(dict(utility_lower=F(3, 2)), 368) is None
    assert audit.stop_reason(dict(utility_lower=F(3, 2)), 384) == 'budget'
    assert audit.stop_reason(dict(utility_lower=F(2)), 16) == 'certified'
    assert audit.stop_reason(dict(utility_lower=F(2)), 384) == 'certified'


def test_modified_fields_joint_decision_or_certificate_is_rejected():
    source, tables = synthetic_tables(); work = Counter(); model = audit.fit_tables(tables, 'REVISED', work)
    saved_model = audit.exact_json(model)
    assert audit.model_matches(saved_model, model)
    corrupted = deepcopy(saved_model); corrupted['selected_fields']['DETOUR_PASS'] = []
    assert not audit.model_matches(corrupted, model)
    case = dict(id='synthetic_wet_low', operating='low', retry_cost='17/20', weather='wet')
    plan = audit.make_plan(model, case, work); saved_plan = audit.exact_json(plan)
    assert audit.plan_matches(saved_plan, plan)
    corrupted = deepcopy(saved_plan); corrupted['utility_lower'] = '2'
    assert not audit.plan_matches(corrupted, plan)
    decision = audit.decision(model, 0, 'GUIDED', case, work)
    result = audit.decision_score(decision, case, audit.true_laws(case), work)
    corrupted = deepcopy(result); corrupted['queries']['goal']['actual_fractions'][1] = '1'
    assert not audit.equal_numbers(corrupted, result)
    actual = audit.vectors(case, audit.true_laws(case))[decision['queries']['goal']['pure_policy']]
    assert result['queries']['goal']['actual_fractions'] == audit.exact_json(actual)
