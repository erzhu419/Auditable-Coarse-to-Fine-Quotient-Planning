"""Independent exact product-prefix and action-gap audit of V232 bad kernels.

The primal optimizer is not imported or rerun.  Every accepted kernel must
satisfy every original prefix simultaneously, with an exact regret above .05.
"""
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_kernel_query_profile_v232 as arithmetic

OUTPUT = arithmetic.OUTPUT
QUERY_ORDER = ('risk', 'goal', 'reward')


def run():
    started, checks, expected = perf_counter(), Counter(), Counter()

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    read = lambda name: json.loads((OUTPUT/name).read_text())
    main = read('analysis.json')
    check('original_certificates_already_audited', main['valid'] and main['complete'] and main['records'] == 24)
    protocol, witnesses, summary = read('countermodel_protocol.json'), read('countermodels.json'), read('countermodel_summary.json')
    records = arithmetic.read_gzip(OUTPUT/'records.jsonl.gz')
    selected = [record for record in records if record['kind'] == 'failure' or not record['query_ready']]
    identity = lambda row: {k: row[k] for k in ('life', 'index', 'arm', 'kind', 'phase')}
    key = lambda row: (row['life'], row['index'], row['arm'])
    check('frozen_complete_failure_selection', protocol['selected'] == [identity(r) for r in selected]
          and len(selected) == len(witnesses) == 13
          and [key(r) for r in witnesses] == [key(r) for r in selected])
    check('fixed_primal_proposal_protocol', protocol['query_order'] == list(QUERY_ORDER)
          and protocol['alternative_order'] == list(arithmetic.route.POLICIES)
          and protocol['initial_order'] == ['truth', 'pool_mle']
          and protocol['optimizer'] == 'SLSQP' and protocol['maxiter'] == 200
          and protocol['failure_to_find'] == 'unknown')
    check('no_new_observations_or_gate_changes', protocol['new_observations'] == summary['new_observations']
          == summary['new_paid_samples'] == 0 and not protocol['scientific_gate_changed']
          and not summary['scientific_gate_changed'])
    originals = {(r['life'], r['index'], r['arm']): r
                 for life in arithmetic.previous.LIVES for r in arithmetic.previous.records_for(life)}
    verified, constraints, exact_gaps = [], 0, []
    for record, witness in zip(selected, witnesses):
        original = originals[key(record)]
        query = next(q for q in QUERY_ORDER if not record['queries'][q]['certified'])
        chosen = original['terminal_plan']['queries'][query]['policy']
        check('fixed_first_unresolved_query_and_policy', witness['query'] == query
              and witness['chosen_policy'] == chosen and identity(witness) == identity(record))
        alternatives = [p for p in arithmetic.route.POLICIES if p != chosen]
        attempts = witness['attempts']
        expected_attempts = [(other, initial) for other in alternatives for initial in ('truth', 'pool_mle')]
        check('ordered_fixed_primal_attempts', bool(attempts) and
              [(a['alternative'], a['initial']) for a in attempts] == expected_attempts[:len(attempts)]
              and all(0 <= a['iterations'] <= 200 for a in attempts))
        check('zero_observation_witness', witness['new_observations'] == 0)
        if not witness['found']:
            check('unknown_without_negative_inference', not witness['valid'] and len(attempts) == len(expected_attempts))
            continue
        kernel = arithmetic.fractions(witness['kernel'])
        check('complete_exact_kernel_simplex', set(kernel) == set(arithmetic.OPERATORS)
              and all(set(kernel[op]) == set(arithmetic.ALPHABETS[op])
                      and sum(row.values()) == 1 and all(F(0) <= p <= 1 for p in row.values())
                      for op, row in kernel.items()))
        groups = arithmetic.prefixes(original)
        check('complete_same_kernel_prefix_roster', record['prefixes'] == groups
              and [item['prefix'] for item in witness['feasibility']] == [prefix['name'] for prefix in groups])
        for prefix, declared in zip(groups, witness['feasibility']):
            inside = arithmetic.classify_truth(prefix, kernel)
            check('exact_intersection_region_membership', inside and declared['exact_inside'])
            constraints += 1
        alternative = witness['alternative_policy']
        check('different_supported_alternative', alternative in alternatives and attempts[-1]['alternative'] == alternative)
        actual_gap = arithmetic.gap(original['case'], query, chosen, alternative, kernel)
        check('exact_reported_query_gap', actual_gap == F(witness['regret'])
              and F(witness['threshold']) == arithmetic.THRESHOLD)
        check('strict_bad_null_witness', actual_gap > arithmetic.THRESHOLD and witness['valid'])
        exact_gaps.append(actual_gap)
        verified.append(identity(witness))
    groups = {kind: dict(cases=sum(r['kind'] == kind for r in witnesses),
                        found=sum(r['kind'] == kind and r['found'] for r in witnesses))
              for kind in ('failure', 'positive')}
    check('countermodel_summary', summary['cases'] == len(witnesses)
          and summary['found'] == len(verified) and summary['groups'] == groups
          and summary['exact_prefix_checks'] == constraints)
    result = dict(valid=all(checks[name] == n for name, n in expected.items()), complete=True,
        cases=len(witnesses), verified_countermodels=len(verified), exact_prefix_constraints=constraints,
        groups=groups, unknown_cases=[identity(r) for r in witnesses if not r['found']],
        minimum_exact_gap=str(min(exact_gaps)) if exact_gaps else None,
        scope='selected pure policy and fixed unresolved query in the full applicable product-prefix intersection',
        checks=dict(checks), expected=dict(expected),
        failures={name: n-checks[name] for name, n in expected.items() if n != checks[name]},
        new_observations=0, seconds=perf_counter()-started)
    (OUTPUT/'countermodel_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'expected')}), flush=True)
    return result


if __name__ == '__main__':
    run()
