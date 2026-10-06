"""Independent retained-evidence audit of complete and outer assignment unions.

The V222 producer is never imported. Short-prefix union branches and full-prefix
subset sums are reconstructed from original counts and frozen KL constants.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
import json
from math import ceil, floor, inf, log, log1p
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_latent_mechanisms_v213 as prior

OUTPUT = ROOT/'reports/assignment_union_v222'
OPERATORS, SUPPORT = prior.OPERATORS, prior.SUPPORT
GRID = 2**40
RAW_BETA = log(2*5544/.025)
POOL_BETA = log(2*13608/.025)
CHECKPOINTS = (4, 8, 12, 24)


def kl(x, p):
    if x == 0:
        return inf if p == 1 else -log1p(-p)
    if x == 1:
        return inf if p == 0 else -log(p)
    if p in (0, 1):
        return inf
    return x*log(x/p)+(1-x)*log((1-x)/(1-p))


@lru_cache(maxsize=None)
def interval(k, n, beta):
    if n == 0:
        return F(0), F(1)
    x = k/n
    left = 0.
    if k:
        a, b = 0., x
        for _ in range(64):
            mid = (a+b)/2
            if n*kl(x, mid) > beta:
                a = mid
            else:
                b = mid
        left = a
    right = 1.
    if k < n:
        a, b = x, 1.
        for _ in range(64):
            mid = (a+b)/2
            if n*kl(x, mid) > beta:
                b = mid
            else:
                a = mid
        right = b
    return [F(floor(left*GRID), GRID), F(ceil(right*GRID), GRID)]


def boxes(counts, beta=RAW_BETA):
    return {op: dict(n=sum(counts[op].values()), counts=dict(counts[op]),
                    bounds={cat: list(interval(k, sum(counts[op].values()), beta))
                            for cat, k in counts[op].items()}) for op in OPERATORS}


def intersect(left, right):
    result = deepcopy(left)
    for op in OPERATORS:
        for cat in SUPPORT[op]:
            a, b = left[op]['bounds'][cat], right[op]['bounds'][cat]
            result[op]['bounds'][cat] = [max(a[0], b[0]), min(a[1], b[1])]
    return project_simplex(result) if feasible(result) else None


def project_simplex(box):
    for op in OPERATORS:
        original = deepcopy(box[op]['bounds'])
        for cat in SUPPORT[op]:
            others = [c for c in SUPPORT[op] if c != cat]
            lo, hi = original[cat]
            box[op]['bounds'][cat] = [max(lo, 1-sum(original[c][1] for c in others)),
                                       min(hi, 1-sum(original[c][0] for c in others))]
    return box


def feasible(box):
    if box is None:
        return False
    for op in OPERATORS:
        bounds = box[op]['bounds'].values()
        if any(lo > hi for lo, hi in bounds):
            return False
        if sum(pair[0] for pair in bounds) > 1 or sum(pair[1] for pair in bounds) < 1:
            return False
    return True


def raw_problem(anchors, members):
    source = [project_simplex(boxes(a)) for a in anchors]
    raw = [project_simplex(boxes(m)) for m in members]
    return dict(source_boxes=source, member_boxes=raw,
                masks=[[i for i, a in enumerate(source) if intersect(a, m) is not None]
                       for m in raw])


def union_envelope(branches, source):
    if not branches:
        return []
    bounds = deepcopy(source)
    for i in range(len(source)):
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                bounds[i][op]['bounds'][cat] = [
                    min(branch[i][op]['bounds'][cat][0] for branch in branches),
                    max(branch[i][op]['bounds'][cat][1] for branch in branches)]
    return bounds


def exact_union(problem, anchors, members):
    branches, admitted = [], []
    masks = [set() for _ in members]
    assignments = 0
    for assignment in product(*problem['masks']):
        assignments += 1
        cumulative, block = deepcopy(anchors), deepcopy(problem['source_boxes'])
        for j, i in enumerate(assignment):
            if block[i] is not None:
                block[i] = intersect(block[i], problem['member_boxes'][j])
            for op in OPERATORS:
                for cat in SUPPORT[op]:
                    cumulative[i][op][cat] += members[j][op][cat]
        block = [intersect(b, boxes(c, POOL_BETA)) if b is not None else None
                 for b, c in zip(block, cumulative)]
        if all(feasible(b) for b in block):
            branches.append(block)
            admitted.append(assignment)
            for j, i in enumerate(assignment):
                masks[j].add(i)
    bounds = union_envelope(branches, problem['source_boxes'])
    for b in bounds:
        for op in OPERATORS:
            b[op]['kind'] = 'exact_assignment_union'
    return dict(bounds=bounds, no_feasible=not branches,
                masks=[sorted(v) for v in masks], assignments=assignments,
                feasible_assignments=len(branches), admitted=admitted)


def subset_extrema(initial_n, initial_k, additions):
    """Map each attainable total n to its exact smallest/largest count k."""
    states = {initial_n: (initial_k, initial_k)}
    for add_n, add_k in additions:
        following = dict(states)
        for n, (lo, hi) in states.items():
            next_n, a, b = n+add_n, lo+add_k, hi+add_k
            if next_n in following:
                old = following[next_n]
                following[next_n] = (min(a, old[0]), max(b, old[1]))
            else:
                following[next_n] = (a, b)
        states = following
    return states


def projection(problem, anchors, members, masks):
    bounds = deepcopy(problem['source_boxes'])
    max_states = 0
    for i, anchor in enumerate(anchors):
        mandatory = [j for j, mask in enumerate(masks) if mask == [i]]
        optional = [j for j, mask in enumerate(masks) if i in mask and len(mask) > 1]
        bounds[i] = intersect(bounds[i], boxes(prior.empty()))
        for j in mandatory:
            if bounds[i] is not None:
                bounds[i] = intersect(bounds[i], problem['member_boxes'][j])
        if bounds[i] is None:
            return [], max_states
        for op in OPERATORS:
            n = sum(anchor[op].values())+sum(sum(members[j][op].values()) for j in mandatory)
            for cat in SUPPORT[op]:
                k = anchor[op][cat]+sum(members[j][op][cat] for j in mandatory)
                choices = [(sum(members[j][op].values()), members[j][op][cat]) for j in optional]
                states = subset_extrema(n, k, choices)
                max_states = max(max_states, len(states))
                lo = min(interval(a, total, POOL_BETA)[0] for total, (a, b) in states.items())
                hi = max(interval(b, total, POOL_BETA)[1] for total, (a, b) in states.items())
                old = bounds[i][op]['bounds'][cat]
                bounds[i][op]['bounds'][cat] = [max(old[0], lo), min(old[1], hi)]
        if not feasible(bounds[i]):
            return [], max_states
        bounds[i] = project_simplex(bounds[i])
    return bounds, max_states


def outer_union(problem, anchors, members):
    masks = deepcopy(problem['masks'])
    iterations, max_states = 0, 0
    while True:
        iterations += 1
        if any(not m for m in masks):
            return dict(bounds=[],masks=[[] for _ in members],no_feasible=True,
                        iterations=iterations,max_dp_states=max_states)
        bounds, states = projection(problem, anchors, members, masks)
        max_states = max(max_states, states)
        if not bounds:
            return dict(bounds=[],masks=[[] for _ in members],no_feasible=True,
                        iterations=iterations,max_dp_states=max_states)
        following = [[i for i in mask if feasible(intersect(bounds[i], problem['member_boxes'][j]))]
                     for j, mask in enumerate(masks)]
        if following == masks:
            for b in bounds:
                for op in OPERATORS:
                    b[op]['kind'] = 'outer_assignment_union'
            return dict(bounds=bounds, masks=masks,no_feasible=False,
                        iterations=iterations, max_dp_states=max_states)
        masks = following


def contains(outer, inner):
    if not inner:
        return True
    if not outer:
        return False
    return all(outer[i][op]['bounds'][cat][0] <= inner[i][op]['bounds'][cat][0]
               <= inner[i][op]['bounds'][cat][1] <= outer[i][op]['bounds'][cat][1]
               for i in range(len(inner)) for op in OPERATORS for cat in SUPPORT[op])


def plan(member, anchors, case, source):
    raw = boxes(member)
    candidates, blocks = [], {}
    for i, reference in enumerate(source):
        block = intersect(raw, reference)
        if feasible(block):
            candidates.append(i)
            blocks[i] = block
    if candidates:
        risks = [prior.settled.risk_bounds(b) for b in blocks.values()]
        goals = [prior.settled.goal_bounds(b, case) for b in blocks.values()]
        upper = {p: max(r[p] for r in risks) for p in risks[0]}
        lower = {p: min(g[p] for g in goals) for p in goals[0]}
        means = [prior.posterior({op: {cat: member[op][cat]+anchors[i][op][cat]
                                      for cat in SUPPORT[op]} for op in OPERATORS}) for i in candidates]
        probabilities = {op: {cat: sum(p[op][cat] for p in means)/len(means)
                              for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                envelope[op]['bounds'][cat] = [min(b[op]['bounds'][cat][0] for b in blocks.values()),
                                               max(b[op]['bounds'][cat][1] for b in blocks.values())]
        mode = 'library'
    else:
        envelope, mode = raw, 'member'
        upper = prior.settled.risk_bounds(raw)
        lower = prior.settled.goal_bounds(raw, case)
        probabilities = prior.posterior(member)
    pure = prior.settled.vectors(case, probabilities)
    result = dict(prior.settled.optimize(pure, upper, lower, Counter()), envelopes=envelope,
                  risks=upper, goals_lower=lower, pure_vectors=pure, candidates=candidates,
                  candidate_envelopes=blocks, mode=mode)
    regrets = []
    chosen = prior.queries(result)
    for i in candidates:
        combined = {op: {cat: member[op][cat]+anchors[i][op][cat] for cat in SUPPORT[op]}
                    for op in OPERATORS}
        individual = prior.settled.vectors(case, prior.posterior(combined))
        values = []
        for name, weights in prior.QUERY_WEIGHTS.items():
            value = lambda v: sum(v[j]*weights[j]*(1 if j != 1 else -1) for j in range(3))
            values.append(max(value(v) for v in individual.values())-value(individual[chosen[name]['policy']]))
        regrets.append(sum(values)/3)
    proxy = max(regrets) if regrets else None
    result['query_proxy'] = proxy
    result['query_ready'] = mode == 'library' and result['utility_lower'] >= 2 and proxy is not None and proxy <= F(1,20)
    return result


def fractions(value):
    if isinstance(value, dict):
        return {k: fractions(v) for k, v in value.items()}
    if isinstance(value, list):
        return [fractions(v) for v in value]
    if isinstance(value, str):
        try:
            return F(value)
        except ValueError:
            return value
    return value


def coverage(bounds, laws):
    return bool(bounds) and all(
        bounds[i][op]['bounds'][cat][0] <= laws[i][op][cat] <= bounds[i][op]['bounds'][cat][1]
        for i in range(3) for op in OPERATORS for cat in SUPPORT[op])


def widths(bounds):
    if not bounds:
        return None
    return {op: float(sum(bounds[i][op]['bounds'][cat][1]-bounds[i][op]['bounds'][cat][0]
                         for i in range(3) for cat in SUPPORT[op])) for op in OPERATORS}


def probe(plan, law, case):
    if plan is None:
        return None
    actual = prior.settled.joint(plan['mix'], prior.settled.vectors(case, law), Counter())
    return dict(certified=plan['utility_lower'] >= 2, risk=float(actual[1]),
                utility=float(actual[0]+4*actual[2]), utility_lower=float(plan['utility_lower']),
                risk_upper=float(plan['risk_upper']), coverage=all(
                    lo <= law[op][cat] <= hi for op in OPERATORS
                    for cat, (lo, hi) in plan['envelopes'][op]['bounds'].items()))


def summarize(evidence, rows):
    checkpoints = []
    failures = Counter(dict(no_feasible=0,coverage=0,true_masks=0,containment=0,probe_risk=0,probe_coverage=0))
    first_certificates, observations = [], []
    for row in rows:
        e = row['evaluation']
        failures['no_feasible'] += row['outer']['no_feasible'] or (row['exact'] is not None and row['exact']['no_feasible'])
        failures['coverage'] += not e['source_coverage'] or not e['outer_coverage'] or e['exact_coverage'] is False
        failures['true_masks'] += not e['outer_true_masks'] or e['exact_true_masks'] is False
        failures['containment'] += e['outer_contains_exact'] is False
        for ps in [e['probe'],*e['member_probes']]:
            for kind in ('source','outer','exact'):
                if ps[kind] is not None:
                    failures['probe_risk'] += ps[kind]['risk'] > .05
                    failures['probe_coverage'] += not ps[kind]['coverage']
        observations.extend(e['member_probes'])
        if row['case'] is not None:
            first = {kind:next((item['spent'] for item in e['member_probes']
                                if item[kind] is not None and item[kind]['certified']),None)
                     for kind in ('source','outer','exact')}
            first_certificates.append(dict(life=row['life'],prefix=row['prefix'],**first))
    for prefix in CHECKPOINTS:
        subset = [r for r in rows if r['prefix'] == prefix]
        means = {kind:{op:sum(r['evaluation']['widths'][kind][op] for r in subset)/len(subset)
                      for op in OPERATORS} for kind in ('source','outer')
                 if all(r['evaluation']['widths'][kind] for r in subset)}
        checkpoints.append(dict(prefix=prefix,lives=len(subset),width_means=means,
            observed_samples={op:sum(r['evaluation']['observed_samples'][op] for r in subset) for op in OPERATORS},
            source_certified=sum(r['evaluation']['probe']['source'] is not None and r['evaluation']['probe']['source']['certified'] for r in subset),
            outer_certified=sum(r['evaluation']['probe']['outer'] is not None and r['evaluation']['probe']['outer']['certified'] for r in subset),
            raw_ambiguous=sum(len(mask)>1 for r in subset for mask in r['raw_problem']['masks']),
            outer_ambiguous=sum(len(mask)>1 for r in subset for mask in r['outer']['masks']),
            max_dp_states=max(r['outer']['max_dp_states'] for r in subset),iterations=max(r['outer']['iterations'] for r in subset)))
    gained = sum(p['outer'] is not None and p['outer']['certified'] and not p['source']['certified'] for p in observations)
    lost = sum(p['source']['certified'] and (p['outer'] is None or not p['outer']['certified']) for p in observations)
    earlier = sum(f['outer'] is not None and f['source'] is not None and f['outer'] < f['source'] for f in first_certificates)
    same = sum(f['outer'] is not None and f['source'] is not None and f['outer'] == f['source'] for f in first_certificates)
    later = sum(f['outer'] is not None and f['source'] is not None and f['outer'] > f['source'] for f in first_certificates)
    new = sum(f['outer'] is not None and f['source'] is None for f in first_certificates)
    last = checkpoints[-1]
    narrowed = bool(last['width_means'].get('outer')) and any(
        last['observed_samples'][op]>0 and last['width_means']['outer'][op] < last['width_means']['source'][op] for op in OPERATORS)
    decision = ('CUMULATIVE_UNION_INCONSISTENT' if any(failures.values()) else
                'CUMULATIVE_UNION_READY_FOR_FRESH_TEST' if narrowed and gained>0 and lost==0 else 'CUMULATIVE_UNION_LIMITED')
    return dict(complete=True,mode=evidence['mode'],new_environment_samples=0,
        historical_source_samples=sum(l['source_samples'] for l in evidence['lives']),
        historical_target_samples=sum(t['spent'] for l in evidence['lives'] for t in l['targets']),
        confidence=dict(scope='per_lifecycle',raw_delta=.025,pool_delta=.025,raw_family=5544,pool_family=13608),
        failures=dict(failures),checkpoints=checkpoints,gained_certified_probes=gained,
        lost_certified_probes=lost,observed_intervals_narrowed=narrowed,earlier_certified_targets=earlier,
        same_certified_targets=same,later_certified_targets=later,newly_certified_targets=new,
        member_probe_count=len(observations),first_certificates=first_certificates,decision=decision)


def analyze():
    begun = perf_counter()
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
    def read(path):
        return json.loads(path.read_text())
    try:
        evidence = read(OUTPUT/'evidence.json')
        records = read(OUTPUT/'records.json')
        summary = read(OUTPUT/'summary.json')
        sources = read(ROOT/evidence['source_path'])
        retained = [r for r in read(ROOT/evidence['target_path']) if r['arm'] == 'FROZEN']
        expected = []
        for life in range(12):
            targets = []
            for row in retained:
                if row['life'] != life:
                    continue
                target = {k:row[k] for k in ('index','case','member','spent','stop','certified')}
                member = prior.empty()
                prefixes = [dict(spent=0,member=deepcopy(member))]
                for batch in row['batches']:
                    for cat,count in batch['increments'].items():
                        member[batch['operator']][cat] += count
                    prefixes.append(dict(spent=batch['spent'],member=deepcopy(member)))
                target['prefixes'] = prefixes
                targets.append(target)
            expected.append(dict(life=life,anchors=sources[life]['anchors'],source_samples=3456,targets=targets))
        check('original_complete_source_and_all_frozen_targets', evidence['lives'] == expected
              and evidence['arm'] == 'FROZEN' and evidence['mode'] == 'retained_evidence_diagnostic')
        check('complete_checkpoint_roster', len(records) == 48 and
              {(r['life'],r['prefix']) for r in records} == {(i,p) for i in range(12) for p in CHECKPOINTS})
        reconstructed = []
        for row in records:
            i, prefix = row['life'], row['prefix']
            anchors = expected[i]['anchors']
            targets = expected[i]['targets']
            members = [t['member'] for t in targets[:prefix]]
            problem = raw_problem(anchors, members)
            outer = outer_union(problem, anchors, members)
            exact = exact_union(problem, anchors, members) if prefix in (4,8) else None
            stem = f'life{i}_prefix{prefix}'
            check(stem+'_raw_confidence_and_all_members', prior.same(row['raw_problem'], problem))
            check(stem+'_outer_full_dp_fixedpoint', prior.same(row['outer'], outer))
            if exact is not None:
                check(stem+'_complete_assignment_union', prior.same(row['exact'],
                    {k:v for k,v in exact.items() if k != 'admitted'}))
                check(stem+'_outer_contains_every_feasible_branch',
                      contains(outer['bounds'], exact['bounds']) and
                      all(all(index in outer['masks'][j] for j,index in enumerate(a)) for a in exact['admitted']))
            else:
                check(stem+'_no_exponential_fullprefix_oracle', row['exact'] is None and row['exact_plan'] is None)
            case = targets[prefix]['case'] if prefix < 24 else None
            check(stem+'_chronological_next_target_case', row['case'] == case)
            expected_plans = dict(source_plan=plan(prior.empty(),anchors,case,problem['source_boxes']) if case else None,
                                  outer_plan=plan(prior.empty(),anchors,case,outer['bounds']) if case and outer['bounds'] else None,
                                  exact_plan=plan(prior.empty(),anchors,case,exact['bounds']) if case and exact and exact['bounds'] else None)
            check(stem+'_safety_and_frozen_points', all(prior.same(row[key],value) for key,value in expected_plans.items()))
            cases, laws, identities = prior.world(i)
            identity = identities[3:3+prefix]
            member_probes, probe_scores = [], []
            if case:
                for item in targets[prefix]['prefixes']:
                    probe_plans = dict(source_plan=plan(item['member'],anchors,case,problem['source_boxes']),
                        outer_plan=plan(item['member'],anchors,case,outer['bounds']) if outer['bounds'] else None,
                        exact_plan=plan(item['member'],anchors,case,exact['bounds']) if exact and exact['bounds'] else None)
                    member_probes.append(dict(spent=item['spent'],member=item['member'],**probe_plans))
                    probe_scores.append(dict(spent=item['spent'],**{
                        kind:probe(probe_plans[kind+'_plan'],laws[3+prefix],case) for kind in ('source','outer','exact')}))
            check(stem+'_all_existing_next_member_prefixes', prior.same(row['member_probes'],member_probes))
            score = dict(source_coverage=coverage(problem['source_boxes'], laws[:3]),
                         outer_coverage=coverage(outer['bounds'], laws[:3]),
                         outer_true_masks=all(a in mask for a,mask in zip(identity,outer['masks'])),
                         exact_coverage=coverage(exact['bounds'], laws[:3]) if exact else None,
                         exact_true_masks=all(a in mask for a,mask in zip(identity,exact['masks'])) if exact else None,
                         outer_contains_exact=contains(outer['bounds'],exact['bounds']) if exact else None,
                         widths=dict(source=widths(problem['source_boxes']),outer=widths(outer['bounds']),
                                     exact=widths(exact['bounds']) if exact else None),
                         observed_samples={op:sum(sum(m[op].values()) for m in members) for op in OPERATORS},
                         probe={kind:probe(expected_plans[kind+'_plan'],laws[3+prefix],case) if case else None
                                for kind in ('source','outer','exact')},member_probes=probe_scores)
            check(stem+'_delayed_truth_and_width_scoring', prior.same(row['evaluation'],score))
            reconstructed.append(dict(life=i,prefix=prefix,case=case,raw_problem=problem,outer=outer,exact=exact,evaluation=score))
        check('independent_summary_and_decision',prior.same(summary,summarize(evidence,reconstructed)))
        check('decision_before_truth_phases',read(OUTPUT/'run.json')['phases'] ==
              ['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
    except Exception as exc:
        checks.append(dict(name='audit_exception',passed=False,error=f'{type(exc).__name__}: {exc}'))
    passed = sum(c['passed'] for c in checks)
    result = dict(valid=passed == len(checks), complete=True, passed=passed,total=len(checks),
                  checks=checks,seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'checks'},indent=2))
    return result


if __name__ == '__main__':
    result = analyze()
    raise SystemExit(0 if result['valid'] else 1)
