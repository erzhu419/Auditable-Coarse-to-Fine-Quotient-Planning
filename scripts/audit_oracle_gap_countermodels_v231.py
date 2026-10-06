"""Independent exact checks of V231 terminal-region ranking countermodels."""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
import json
from math import factorial
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_oracle_gap_lifecycle_v231 as audit
from scripts import audit_joint_gap_v230 as arithmetic

OUTPUT = audit.OUTPUT


@lru_cache(maxsize=None)
def integrated_likelihood(counts):
    """Reconstruct exact half-integer Gamma ratios, independently of producer."""
    n, categories = sum(counts), len(counts)
    numerator = 1
    for count in counts:
        numerator *= factorial(2*count)//factorial(count)
    if categories == 2:
        denominator = 4**n*factorial(n)
    elif categories == 3:
        numerator *= 2*factorial(n+1)
        denominator = factorial(2*n+2)
    else:
        raise ValueError('only the supported route alphabets occur')
    return F(numerator, denominator)


def run():
    begun, checks, expected = perf_counter(), Counter(), Counter()

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    read = lambda name: json.loads((OUTPUT/name).read_text())
    main, witnesses, summary = read('analysis.json'), read('countermodels.json'), read('countermodel_summary.json')
    check('terminal_constraints_audited', main['valid'] and main['complete'] and main['records'] == 432)
    selected = {}
    for life in audit.LIVES:
        for row in audit.records_for(life):
            index = row['index']
            phase = 'late_B' if 42 <= index < 54 else ('A_RETURN' if index >= 54 else None)
            if phase is None or row['spent'] != 384 or row['terminal_plan']['query_ready']:
                continue
            key = life, row['arm'], phase, row['identity']
            selected.setdefault(key, row)
    grouped, constraint_checks, exact_gaps = {}, 0, []
    for row in witnesses:
        key = row['life'], row['arm'], row['phase'], row['identity']
        original = selected[key]
        plan, case = original['terminal_plan'], original['case']
        query = max(plan['query_certificates'], key=lambda q: F(plan['query_certificates'][q]['regret_upper']))
        policy = row['chosen_policy']
        check('frozen_selected_failure', row['index'] == original['index'] and row['query'] == query)
        check('supported_pure_policy', policy in arithmetic.POLICIES)
        grouped.setdefault(key, []).append(row)
        if not row['found']:
            check('unfound_is_not_evidence', not row['valid'] and row['reason'] == 'no_verified_regret_witness')
            continue
        kernel = {op: {cat: F(value) for cat, value in probabilities.items()}
                  for op, probabilities in row['kernel'].items()}
        check('complete_kernel_alphabets', set(kernel) == set(audit.OPERATORS)
              and all(set(kernel[op]) == set(audit.ALPHABETS[op]) for op in audit.OPERATORS))
        for op, probabilities in kernel.items():
            check('simplex_kernel', sum(probabilities.values()) == 1
                  and all(F(0) <= probability <= F(1) for probability in probabilities.values()))
            for region in plan['joint_constraints'][op]:
                counts = tuple(region['counts'][cat] for cat in audit.ALPHABETS[op])
                likelihood = F(1)
                for cat, count in region['counts'].items():
                    likelihood *= probabilities[cat]**count
                check('exact_complete_region_membership', integrated_likelihood(counts)
                      <= region['threshold']*likelihood)
                constraint_checks += 1
        alternative = row['alternative_policy']
        check('different_supported_alternative', alternative in arithmetic.POLICIES and alternative != policy)
        vectors = arithmetic.vectors(case, kernel)
        weights = arithmetic.WEIGHTS[query]
        gap = arithmetic.utility(vectors[alternative], weights)-arithmetic.utility(vectors[policy], weights)
        check('exact_reported_gap', gap == F(row['regret']))
        check('strict_query_threshold_counterexample', gap > F(1, 20) and F(row['threshold']) == F(1, 20))
        check('found_counterexample_valid', row['valid'] and row['feasibility']['valid'])
        check('complete_declared_constraint_checks', len(row['feasibility']['checks'])
              == sum(len(regions) for regions in plan['joint_constraints'].values()))
        exact_gaps.append(gap)
    check('all_selected_cases_attempted', set(grouped) == set(selected))
    for rows in grouped.values():
        check('all_four_pure_policies_attempted', len(rows) == 4
              and {row['chosen_policy'] for row in rows} == set(arithmetic.POLICIES))
        check('one_query_per_case', len({row['query'] for row in rows}) == 1)
    complete_impossibilities = sum(all(row['found'] for row in rows) for rows in grouped.values())
    check('countermodel_summary_counts', summary['selected_targets'] == len(grouped)
          and summary['attempted'] == len(witnesses)
          and summary['found'] == len(exact_gaps)
          and summary['no_pure_query_certificate'] == complete_impossibilities
          and summary['new_observations'] == 0)
    result = dict(valid=all(checks[name] == count for name, count in expected.items()), complete=True,
        targets=len(grouped), attempts=len(witnesses), verified_countermodels=len(exact_gaps),
        exact_region_constraints=constraint_checks, all_pure_policies_excluded=complete_impossibilities,
        minimum_exact_gap=str(min(exact_gaps)), checks=dict(checks), expected=dict(expected),
        failures={name: count-checks[name] for name, count in expected.items() if count != checks[name]},
        new_observations=0, seconds=perf_counter()-begun)
    (OUTPUT/'countermodel_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'expected')}), flush=True)
    return result


if __name__ == '__main__':
    run()
