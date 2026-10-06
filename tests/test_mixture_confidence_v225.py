from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from math import factorial, log
import json
from pathlib import Path

from acfqp.science import mixture_confidence_v225 as core
from scripts.run_conditioned_mechanisms_v205 import exact_json


CASE = dict(id='unit_03', operating='low', retry_cost='17/20')
ROOT = Path(__file__).resolve().parents[1]


def anchors():
    return [
        dict(SHORT_PASS=dict(DELIVERY=243, LOST=141),
             DETOUR_PASS=dict(DELIVERY=307, LOST=5, RECOVERY=88),
             RECOVERY_RETRY=dict(DELIVERY=157, LOST=211)),
        dict(SHORT_PASS=dict(DELIVERY=378, LOST=6),
             DETOUR_PASS=dict(DELIVERY=250, LOST=58, RECOVERY=76),
             RECOVERY_RETRY=dict(DELIVERY=334, LOST=50)),
        dict(SHORT_PASS=dict(DELIVERY=341, LOST=43),
             DETOUR_PASS=dict(DELIVERY=320, LOST=6, RECOVERY=58),
             RECOVERY_RETRY=dict(DELIVERY=95, LOST=289)),
    ]


def independent_log_e(k, n, p):
    # Exact integer half-beta identity, independent of producer lgamma.
    mixture = F(factorial(2*k)*factorial(2*(n-k)),
                4**n*factorial(k)*factorial(n-k)*factorial(n))
    return log(float(mixture))-k*log(float(p))-(n-k)*log(1-float(p))


def test_mixture_boundaries_match_independent_e_values_including_zero_and_all_success():
    grid = core.evidence.robust.GRID
    for threshold in (core.MEMBER_THRESHOLD, core.POOL_THRESHOLD):
        for k in (0, 1, 8, 16):
            lo, hi = core.interval(k, 16, Counter(), threshold)
            assert 0 <= lo <= F(k, 16) <= hi <= 1
            if k:
                assert independent_log_e(k, 16, lo) >= log(threshold)-1e-8
                assert independent_log_e(k, 16, lo+F(1, grid)) <= log(threshold)+1e-8
            else:
                assert lo == 0
            if k < 16:
                assert independent_log_e(k, 16, hi) >= log(threshold)-1e-8
                assert independent_log_e(k, 16, hi-F(1, grid)) <= log(threshold)+1e-8
            else:
                assert hi == 1
    assert core.interval(0, 0, Counter()) == (F(0), F(1))


def test_fixed_n_mixture_endpoints_are_monotone_for_subset_dp():
    for threshold in (core.MEMBER_THRESHOLD, core.POOL_THRESHOLD):
        rows = [core.interval(k, 32, Counter(), threshold) for k in range(33)]
        assert all(a[0] <= b[0] and a[1] <= b[1] for a, b in zip(rows, rows[1:]))
        assert all(core.interval(k, 32, Counter(), core.POOL_THRESHOLD)[0]
                   >= core.interval(k, 32, Counter(), core.MEMBER_THRESHOLD)[0]
                   for k in range(33))


def test_cs_arms_start_at_identical_source_and_initial_pool_intersection():
    source = anchors()
    fixed = core.prepare(source, 'FIXED_CS', Counter())
    learned = core.prepare(source, 'UNION_CS', Counter())
    assert fixed == learned
    expected = []
    for anchor in source:
        old = core.evidence.boxes(anchor, Counter())
        cs = core.boxes(anchor, Counter(), core.POOL_THRESHOLD)
        box = deepcopy(old)
        for op in core.OPERATORS:
            original = {cat: [max(old[op]['bounds'][cat][0], cs[op]['bounds'][cat][0]),
                               min(old[op]['bounds'][cat][1], cs[op]['bounds'][cat][1])]
                        for cat in core.ALPHABETS[op]}
            for cat in core.ALPHABETS[op]:
                others = [c for c in core.ALPHABETS[op] if c != cat]
                box[op]['bounds'][cat] = [
                    max(original[cat][0], 1-sum(original[c][1] for c in others)),
                    min(original[cat][1], 1-sum(original[c][0] for c in others))]
            box[op]['kind'] = 'initial_source_mixture'
        expected.append(box)
    assert fixed['bounds'] == expected
    assert core.make_plan(core.empty(), source, CASE, 'FIXED_CS', Counter(), fixed) == core.make_plan(
        core.empty(), source, CASE, 'UNION_CS', Counter(), learned)
    assert source == anchors()


def test_original_plans_choices_and_fixed_retention_are_unchanged():
    libraries = json.loads((ROOT/'reports/persistent_evidence_v221/libraries.json').read_text())
    rows = json.loads((ROOT/'reports/persistent_evidence_v221/records.json').read_text())
    rows = [row for row in rows if row['arm'] == 'FROZEN']
    retained = [next(row for row in rows if row['life']==0 and row['index']==3),
                next(row for row in rows if row['stop']=='query_set'),
                next(row for row in rows if row['fallback'])]
    saved = lambda value: json.loads(json.dumps(exact_json(value)))
    for row in retained:
        source, member, work = libraries[row['life']]['anchors'], core.empty(), Counter()
        state = core.prepare(source, 'ORIGINAL', work)
        before = deepcopy(state)
        plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state)
        assert saved(plan) == row['initial_plan']
        for batch in row['batches']:
            choice = core.choose(member, source, row['case'], 'ORIGINAL', plan,
                                 batch['spent']-16, work, state)
            assert saved(choice) == batch['choice']
            for cat, count in batch['increments'].items():
                member[batch['operator']][cat] += count
            plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state)
            assert saved(plan) == batch['plan']
        assert core.choose(member, source, row['case'], 'ORIGINAL', plan,
                           row['spent'], work, state) is None
        if row['fallback']:
            plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state, True)
        assert saved(plan) == row['terminal_plan']
        assert core.advance(state, member, source, 'ORIGINAL', work) is None and state == before
    state = core.prepare(source, 'FIXED_CS', Counter())
    before = deepcopy(state)
    assert core.advance(state, member, source, 'FIXED_CS', Counter()) is None and state == before


def test_persistence_is_delayed_and_retains_failed_and_ambiguous_targets():
    source, work = anchors(), Counter()
    state = core.prepare(source, 'UNION_CS', work)
    failed = core.empty()
    before = deepcopy(state)
    decision = core.make_plan(failed, source, CASE, 'UNION_CS', work, state, True)
    assert decision['utility_lower'] < 2 and state == before
    core.advance(state, failed, source, 'UNION_CS', work)
    ambiguous = core.empty()
    ambiguous['SHORT_PASS'].update(DELIVERY=15, LOST=1)
    problem = core.raw_problem(source, [ambiguous], Counter())
    assert len(problem['masks'][0]) > 1
    before = deepcopy(state)
    core.make_plan(ambiguous, source, CASE, 'UNION_CS', work, state)
    assert state == before
    core.advance(state, ambiguous, source, 'UNION_CS', work)
    assert state['members'] == [failed, ambiguous]
    ambiguous['SHORT_PASS']['DELIVERY'] += 1
    assert state['members'][1]['SHORT_PASS']['DELIVERY'] == 15
    assert work['union_retained_targets'] == 2 and work['union_retained_samples'] == 16
    assert work['controlled_samples'] == 0
    # New targets' point estimates still use original source counts, not retained counts.
    current = core.empty()
    plan = core.make_plan(current, source, CASE, 'UNION_CS', Counter(), state)
    means = [core.evidence.posterior(source[i]) for i in plan['candidates']]
    average = {op: {cat: sum(mean[op][cat] for mean in means)/len(means)
                    for cat in core.ALPHABETS[op]} for op in core.OPERATORS}
    assert plan['pure_vectors'] == core.vectors(CASE, average)


def test_outer_mixture_envelope_contains_every_feasible_full_assignment():
    source = anchors()
    members = [core.empty(), core.empty()]
    members[0]['SHORT_PASS'].update(DELIVERY=15, LOST=1)
    members[1]['SHORT_PASS'].update(DELIVERY=8, LOST=8)
    problem = core.raw_problem(source, members, Counter())
    outer = core.outer_union(problem, source, members, Counter())
    feasible = 0
    for assignment in product(*problem['masks']):
        branch = []
        for index, anchor in enumerate(source):
            pooled = deepcopy(anchor)
            assigned = []
            for j, chosen in enumerate(assignment):
                if chosen == index:
                    assigned.append(problem['member_boxes'][j])
                    for op in core.OPERATORS:
                        for cat in core.ALPHABETS[op]:
                            pooled[op][cat] += members[j][op][cat]
            block = core.union._intersection(problem['source_boxes'][index],
                         assigned+[core.boxes(pooled, Counter(), core.POOL_THRESHOLD)])
            if block is None:
                break
            branch.append(block)
        if len(branch) != len(source):
            continue
        feasible += 1
        assert not outer['no_feasible']
        assert all(index in outer['masks'][j] for j, index in enumerate(assignment))
        for index, box in enumerate(branch):
            for op in core.OPERATORS:
                for cat, (lo, hi) in box[op]['bounds'].items():
                    outer_lo, outer_hi = outer['bounds'][index][op]['bounds'][cat]
                    assert outer_lo <= lo <= hi <= outer_hi
    assert feasible > 1
