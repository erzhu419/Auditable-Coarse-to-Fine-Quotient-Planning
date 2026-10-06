"""Diagnose cumulative latent-assignment confidence on fixed V221 observations."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import assignment_union_v222 as core
from acfqp.science import latent_route_task_v213 as task
from scripts.run_conditioned_mechanisms_v205 import save

OUTPUT = ROOT/'reports/assignment_union_v222'
LIBRARIES = ROOT/'reports/persistent_evidence_v221/libraries.json'
HISTORY = ROOT/'reports/persistent_evidence_v221/records.json'
PREFIXES = (4, 8, 12, 24)
SOURCE_FILES = (
    'src/acfqp/science/assignment_union_v222.py',
    'tests/test_assignment_union_v222.py',
    'scripts/run_assignment_union_v222.py',
    'scripts/analyze_assignment_union_v222.py',
    'specs/ASSIGNMENT_UNION_V222.md',
    'reports/v222_runtime_tmp/run_stage.py',
)


def extract():
    libraries = json.loads(LIBRARIES.read_text())
    rows = json.loads(HISTORY.read_text())
    lives = []
    for library in libraries:
        targets = []
        for row in rows:
            if row['life'] != library['life'] or row['arm'] != 'FROZEN':
                continue
            member = core.empty()
            prefixes = [dict(spent=0, member=deepcopy(member))]
            for batch in row['batches']:
                for cat, count in batch['increments'].items():
                    member[batch['operator']][cat] += count
                prefixes.append(dict(spent=batch['spent'], member=deepcopy(member)))
            targets.append(dict(index=row['index'], case=row['case'], member=row['member'],
                spent=row['spent'], stop=row['stop'], certified=row['certified'], prefixes=prefixes))
        lives.append(dict(life=library['life'], anchors=library['anchors'],
                          targets=targets, source_samples=3456))
    return dict(mode='retained_evidence_diagnostic', source_path=str(LIBRARIES.relative_to(ROOT)),
                target_path=str(HISTORY.relative_to(ROOT)), arm='FROZEN', lives=lives)


def contains(outer, inner):
    return len(outer) == len(inner) == 3 and all(
        outer[i][op]['bounds'][cat][0] <= inner[i][op]['bounds'][cat][0]
        <= inner[i][op]['bounds'][cat][1] <= outer[i][op]['bounds'][cat][1]
        for i in range(3) for op in core.OPERATORS for cat in core.ALPHABETS[op])


def widths(bounds):
    if not bounds:
        return None
    return {op: sum(float(box[op]['bounds'][cat][1]-box[op]['bounds'][cat][0])
                    for box in bounds for cat in core.ALPHABETS[op])
            for op in core.OPERATORS}


def covered(bounds, laws):
    return len(bounds) == 3 and all(lo <= laws[i][op][cat] <= hi
        for i, box in enumerate(bounds) for op in core.OPERATORS
        for cat, (lo, hi) in box[op]['bounds'].items())


def probe(plan, law, case):
    if plan is None:
        return None
    vectors = core.vectors(case, law)
    actual = [sum(weight*vectors[name][j] for name, weight in plan['mix']) for j in range(3)]
    return dict(certified=plan['utility_lower'] >= 2,
                risk=float(actual[1]), utility=float(actual[0]+4*actual[2]),
                utility_lower=float(plan['utility_lower']), risk_upper=float(plan['risk_upper']),
                coverage=all(lo <= law[op][cat] <= hi for op in core.OPERATORS
                             for cat, (lo, hi) in plan['envelopes'][op]['bounds'].items()))


def evaluate(record, life):
    _, laws, identities = task.world(record['life'])
    prefix = record['prefix']
    result = dict(source_coverage=covered(record['raw_problem']['source_boxes'], laws),
                  outer_coverage=covered(record['outer']['bounds'], laws),
                  outer_true_masks=all(identities[3+i] in mask
                                       for i, mask in enumerate(record['outer']['masks'])),
                  exact_coverage=None, exact_true_masks=None, outer_contains_exact=None,
                  widths=dict(source=widths(record['raw_problem']['source_boxes']),
                              outer=widths(record['outer']['bounds']), exact=None),
                  observed_samples={op: sum(sum(t['member'][op].values())
                                             for t in life['targets'][:prefix])
                                    for op in core.OPERATORS},
                  probe=dict(source=None, outer=None, exact=None), member_probes=[])
    if record['exact'] is not None:
        result.update(exact_coverage=covered(record['exact']['bounds'], laws),
                      exact_true_masks=all(identities[3+i] in mask
                                           for i, mask in enumerate(record['exact']['masks'])),
                      outer_contains_exact=contains(record['outer']['bounds'], record['exact']['bounds']))
        result['widths']['exact'] = widths(record['exact']['bounds'])
    if record['case'] is not None:
        for kind in ('source', 'outer', 'exact'):
            result['probe'][kind] = probe(record[kind+'_plan'], laws[3+prefix], record['case'])
        for item in record['member_probes']:
            result['member_probes'].append(dict(spent=item['spent'], **{
                kind: probe(item[kind+'_plan'], laws[3+prefix], record['case'])
                for kind in ('source', 'outer', 'exact')}))
    return result


def summarize(evidence, records, work, seconds):
    failures = dict(no_feasible=sum(r['outer']['no_feasible'] or
                                  (r['exact'] is not None and r['exact']['no_feasible']) for r in records),
                    coverage=sum(not r['evaluation']['source_coverage'] or
                                 not r['evaluation']['outer_coverage'] or
                                 r['evaluation']['exact_coverage'] is False for r in records),
                    true_masks=sum(not r['evaluation']['outer_true_masks'] or
                                   r['evaluation']['exact_true_masks'] is False for r in records),
                    containment=sum(r['evaluation']['outer_contains_exact'] is False for r in records),
                    probe_risk=sum(p is not None and p['risk'] > .05 for r in records
                                   for row in [r['evaluation']['probe'], *r['evaluation']['member_probes']]
                                   for kind, p in row.items() if kind in ('source', 'outer', 'exact')),
                    probe_coverage=sum(p is not None and not p['coverage'] for r in records
                                       for row in [r['evaluation']['probe'], *r['evaluation']['member_probes']]
                                       for kind, p in row.items() if kind in ('source', 'outer', 'exact')))
    checkpoints = []
    for prefix in PREFIXES:
        rows = [r for r in records if r['prefix'] == prefix]
        width_means = {kind: {op: sum(r['evaluation']['widths'][kind][op] for r in rows)/len(rows)
                             for op in core.OPERATORS}
                       for kind in ('source', 'outer') if all(r['evaluation']['widths'][kind] for r in rows)}
        checkpoints.append(dict(prefix=prefix, lives=len(rows), width_means=width_means,
            observed_samples={op: sum(r['evaluation']['observed_samples'][op] for r in rows)
                              for op in core.OPERATORS},
            source_certified=sum(r['evaluation']['probe']['source'] is not None and
                                 r['evaluation']['probe']['source']['certified'] for r in rows),
            outer_certified=sum(r['evaluation']['probe']['outer'] is not None and
                                r['evaluation']['probe']['outer']['certified'] for r in rows),
            raw_ambiguous=sum(len(mask)>1 for r in rows for mask in r['raw_problem']['masks']),
            outer_ambiguous=sum(len(mask)>1 for r in rows for mask in r['outer']['masks']),
            max_dp_states=max(r['outer']['max_dp_states'] for r in rows),
            iterations=max(r['outer']['iterations'] for r in rows)))
    probes = [p for r in records for p in r['evaluation']['member_probes']]
    gained = sum(p['outer'] is not None and p['outer']['certified'] and not p['source']['certified'] for p in probes)
    lost = sum(p['source']['certified'] and (p['outer'] is None or not p['outer']['certified']) for p in probes)
    earlier, same, later, newly_certified = 0, 0, 0, 0
    first_certificates = []
    for record in records:
        if record['case'] is None:
            continue
        first = {kind: next((p['spent'] for p in record['evaluation']['member_probes']
                            if p[kind] is not None and p[kind]['certified']), None)
                 for kind in ('source', 'outer', 'exact')}
        if first['outer'] is not None and first['source'] is None:
            newly_certified += 1
        elif first['outer'] is not None and first['source'] is not None:
            earlier += first['outer'] < first['source']
            same += first['outer'] == first['source']
            later += first['outer'] > first['source']
        first_certificates.append(dict(life=record['life'], prefix=record['prefix'], **first))
    last = checkpoints[-1]
    narrowed = bool(last['width_means'].get('outer')) and any(
        last['observed_samples'][op] > 0 and last['width_means']['outer'][op] < last['width_means']['source'][op]
        for op in core.OPERATORS)
    decision = ('CUMULATIVE_UNION_INCONSISTENT' if any(failures.values()) else
                'CUMULATIVE_UNION_READY_FOR_FRESH_TEST' if narrowed and gained > 0 and lost == 0 else
                'CUMULATIVE_UNION_LIMITED')
    return dict(complete=True, mode=evidence['mode'], new_environment_samples=0,
                historical_source_samples=sum(l['source_samples'] for l in evidence['lives']),
                historical_target_samples=sum(t['spent'] for l in evidence['lives'] for t in l['targets']),
                confidence=dict(scope='per_lifecycle', raw_delta=.025, pool_delta=.025,
                                raw_family=5544, pool_family=13608),
                failures=failures, checkpoints=checkpoints, gained_certified_probes=gained,
                lost_certified_probes=lost, observed_intervals_narrowed=narrowed,
                earlier_certified_targets=earlier, same_certified_targets=same,
                later_certified_targets=later, newly_certified_targets=newly_certified,
                member_probe_count=len(probes), first_certificates=first_certificates,
                decision=decision, work=work, seconds=seconds)


def run():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        destination = OUTPUT/'source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    evidence = extract()
    save(OUTPUT/'evidence.json', evidence)
    work, records = Counter(), []
    core.clear_cache()
    begun = perf_counter()
    for life in evidence['lives']:
        for prefix in PREFIXES:
            anchors = life['anchors']
            members = [t['member'] for t in life['targets'][:prefix]]
            start = perf_counter()
            problem = core.raw_problem(anchors, members, work)
            raw_seconds = perf_counter()-start
            start = perf_counter()
            outer = core.outer_union(problem, anchors, members, work)
            outer_seconds = perf_counter()-start
            exact, exact_seconds = None, 0.
            if prefix in (4, 8):
                start = perf_counter()
                exact = core.exact_union(problem, anchors, members, work)
                exact_seconds = perf_counter()-start
            case = life['targets'][prefix]['case'] if prefix < 24 else None
            plans = dict(source_plan=None, outer_plan=None, exact_plan=None)
            member_probes = []
            if case is not None:
                plans['source_plan'] = core.plan(core.empty(), anchors, case, problem['source_boxes'], work)
                if not outer['no_feasible']:
                    plans['outer_plan'] = core.plan(core.empty(), anchors, case, outer['bounds'], work)
                if exact is not None and not exact['no_feasible']:
                    plans['exact_plan'] = core.plan(core.empty(), anchors, case, exact['bounds'], work)
                for item in life['targets'][prefix]['prefixes']:
                    member = item['member']
                    member_probes.append(dict(spent=item['spent'], member=member,
                        source_plan=core.plan(member, anchors, case, problem['source_boxes'], work),
                        outer_plan=core.plan(member, anchors, case, outer['bounds'], work)
                            if not outer['no_feasible'] else None,
                        exact_plan=core.plan(member, anchors, case, exact['bounds'], work)
                            if exact is not None and not exact['no_feasible'] else None))
            records.append(dict(life=life['life'], prefix=prefix, case=case,
                                raw_problem=problem, outer=outer, exact=exact, **plans,
                                member_probes=member_probes,
                                seconds=dict(raw=raw_seconds, outer=outer_seconds, exact=exact_seconds)))
        print(json.dumps(dict(life=life['life'], records=len(records), seconds=perf_counter()-begun)), flush=True)
    save(OUTPUT/'records.json', records)
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen', 'all_decisions_frozen'], work=work))
    # Truth is accessed only after every union and planning probe is frozen.
    for record in records:
        record['evaluation'] = evaluate(record, evidence['lives'][record['life']])
    summary = summarize(evidence, records, work, perf_counter()-begun)
    save(OUTPUT/'records.json', records)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'], work=work))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    run()
