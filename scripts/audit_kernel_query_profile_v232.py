"""Independent weak-dual arithmetic for retained-kernel NULL certificates.

No producer module or optimizer is imported.  The audit reconstructs exact
route utilities, factorial mixture normalizers, and directed logarithm bounds.
"""
from collections import Counter
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
import gzip
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_gap_v230 as route
from scripts import audit_oracle_gap_lifecycle_v231 as previous
from scripts.audit_oracle_gap_countermodels_v231 import integrated_likelihood
from scripts.audit_joint_kernel_qualification_v231 import product_regions

OUTPUT = ROOT/'reports/kernel_query_profile_v232'
OPERATORS, ALPHABETS = route.OPERATORS, route.ALPHABETS
S, DETOUR, R = OPERATORS
THRESHOLD = F(1, 20)


def fractions(value):
    if isinstance(value, dict):
        return {key: fractions(item) for key, item in value.items()}
    if isinstance(value, list):
        return [fractions(item) for item in value]
    if isinstance(value, str):
        try:
            return F(value)
        except ValueError:
            pass
    return value


@lru_cache(maxsize=8192)
def logarithm(value):
    """Return exact rational outer endpoints for a positive rational log."""
    value = F(value)
    if value <= 0:
        raise ValueError('logarithm requires a positive argument')
    if value == 1:
        return F(0), F(0)
    with localcontext() as context:
        context.prec, context.rounding = 100, ROUND_FLOOR
        low = D(value.numerator)/D(value.denominator)
        context.rounding = ROUND_CEILING
        high = D(value.numerator)/D(value.denominator)
        return F(low.ln().next_minus()), F(high.ln().next_plus())


def mixture_lower(counts, operators):
    value = F(0)
    for operator in operators:
        n = tuple(counts[operator][cat] for cat in ALPHABETS[operator])
        value += logarithm(integrated_likelihood(n))[0]
    return value


def row_dual_upper(counts, coefficients, multiplier, nu):
    """Verify/evaluate a feasible simplex log-likelihood dual witness."""
    counts, coefficients, multiplier, nu = fractions(counts), fractions(coefficients), F(multiplier), F(nu)
    if multiplier < 0 or nu <= max(multiplier*c for c in coefficients.values()):
        raise ValueError('invalid nonnegative multiplier or strict row dual domain')
    upper = nu-sum(counts.values())
    for category, count in counts.items():
        if count:
            upper += count*logarithm(F(count)/(nu-multiplier*coefficients[category]))[1]
    return upper


def retry_likelihood_upper(counts, interval):
    """The exact binary empirical maximizer clamped to the retained cell."""
    lo, hi = map(F, interval)
    delivery, lost = counts['DELIVERY'], counts['LOST']
    total = delivery+lost
    if not total:
        return F(0)
    point = min(hi, max(lo, F(delivery, total)))
    upper = F(0)
    for probability, count in ((point, delivery), (1-point, lost)):
        if count:
            if probability == 0:
                raise ValueError('positive retry count has zero likelihood throughout cell')
            upper += count*logarithm(probability)[1]
    return upper


def corner_kernel(short, detour, retry):
    return {S: {'DELIVERY': F(short), 'LOST': 1-F(short)},
            DETOUR: {cat: F(cat == detour) for cat in ALPHABETS[DETOUR]},
            R: {'DELIVERY': F(retry), 'LOST': 1-F(retry)}}


def gap(case, query, chosen, alternative, kernel):
    pure = route.vectors(case, kernel)
    return (route.utility(pure[alternative], route.WEIGHTS[query])
            -route.utility(pure[chosen], route.WEIGHTS[query]))


def bilinear(case, query, chosen, alternative):
    return any(gap(case, query, chosen, alternative, corner_kernel(s, d, 0))
               != gap(case, query, chosen, alternative, corner_kernel(s, d, 1))
               for s, d in product((0, 1), ALPHABETS[DETOUR]))


def represented_gap(leaf, kernel):
    return F(leaf['gap_constant'])+sum(
        F(coefficient)*kernel[operator][category]
        for operator, row in leaf['gap_coefficients'].items()
        for category, coefficient in row.items())


def audit_leaf(case, query, chosen, alternative, counts, leaf, check):
    """Check algebraic relaxation, independent likelihood UB, legal λ and ν."""
    leaf = fractions(leaf)
    lo, hi = leaf['retry_interval']
    endpoint = leaf['gap_endpoint']
    check('partition_probability_domain', F(0) <= lo < hi <= F(1))
    check('relaxed_gap_row_roster', set(leaf['gap_coefficients']) == {S, DETOUR}
          and all(set(leaf['gap_coefficients'][op]) == set(ALPHABETS[op]) for op in (S, DETOUR)))
    check('partition_endpoint', endpoint in (lo, hi))
    for short, detour in product((0, 1), ALPHABETS[DETOUR]):
        kernel = corner_kernel(short, detour, endpoint)
        expected = gap(case, query, chosen, alternative, kernel)
        check('exact_endpoint_gap', represented_gap(leaf, kernel) == expected)
        check('endpoint_relaxes_complete_retry_cell', all(
            expected >= gap(case, query, chosen, alternative, corner_kernel(short, detour, retry))
            for retry in (lo, hi)))
    maximum = F(leaf['gap_constant'])+sum(max(row.values()) for row in leaf['gap_coefficients'].values())
    check('exact_maximum_relaxed_gap', leaf['maximum_relaxed_gap'] == maximum)
    if leaf['kind'] == 'empty_bad_null':
        check('exact_empty_relaxed_null', maximum < THRESHOLD
              and leaf['log_bad_likelihood_upper'] is None)
        return None
    check('supported_likelihood_leaf', leaf['kind'] == 'likelihood_dual')
    multiplier = leaf['multiplier']
    check('legal_null_multiplier', multiplier >= 0)
    check('optimization_row_roster', set(leaf['row_witnesses']) == {S, DETOUR})
    total = multiplier*(F(leaf['gap_constant'])-THRESHOLD)
    valid = True
    for operator in (S, DETOUR):
        witness, coefficients = leaf['row_witnesses'][operator], leaf['gap_coefficients'][operator]
        if witness['kind'] == 'free_simplex':
            legal = sum(counts[operator].values()) == 0
            upper = max(multiplier*c for c in coefficients.values())
            check('empty_likelihood_row_simplex', legal)
            valid &= legal
        else:
            legal = witness['kind'] == 'simplex_likelihood_dual' and multiplier >= 0
            try:
                upper = row_dual_upper(counts[operator], coefficients, multiplier, witness['nu'])
            except ValueError:
                upper, legal = F(0), False
            check('legal_row_likelihood_dual', legal)
            valid &= legal
        check('outward_row_likelihood_upper', valid and witness['upper'] >= upper)
        total += witness['upper']
    retry_upper = retry_likelihood_upper(counts[R], (lo, hi))
    expected_probability = (F(counts[R]['DELIVERY'], sum(counts[R].values()))
                            if sum(counts[R].values()) else F(1, 2))
    expected_probability = min(hi, max(lo, expected_probability))
    retry = leaf['retry_likelihood']
    check('retry_interval_mle_probability', retry['probability'] == expected_probability)
    check('outward_retry_interval_likelihood_upper', retry['log_likelihood_upper'] >= retry_upper)
    total += retry['log_likelihood_upper']
    check('outward_complete_null_likelihood_upper', leaf['log_bad_likelihood_upper'] >= total)
    return leaf['log_bad_likelihood_upper']


def audit_certificate(case, query, chosen, alternative, prefix, certificate, check):
    """Independently verify every global weak-dual certificate or unknown."""
    cert, prefix = fractions(certificate), fractions(prefix)
    operators = prefix['operators']
    counts = {op: {cat: prefix['counts'][op][cat] if op in operators else 0
                   for cat in ALPHABETS[op]} for op in OPERATORS}
    check('certificate_uses_fixed_comparison', (cert['query'], cert['chosen'], cert['alternative'])
          == (query, chosen, alternative))
    check('certificate_uses_declared_prefix', cert['counts'] == counts and cert['operators'] == operators
          and cert['threshold'] == prefix['threshold'] and cert['regret_threshold'] == THRESHOLD)
    minimum = mixture_lower(counts, operators)
    check('outward_exact_product_mixture_lower', cert['log_mixture_lower'] <= minimum)
    check('outward_event_threshold_upper', cert['log_threshold_upper'] >= logarithm(prefix['threshold'])[1])
    kind = cert['witness_kind']
    if kind == 'bad_null_mle':
        kernel = cert['bad_null_kernel']
        mle = {op: {cat: F(n, sum(row.values())) if sum(row.values()) else F(1, len(row))
                    for cat, n in row.items()} for op, row in counts.items()}
        expected_gap = gap(case, query, chosen, alternative, mle)
        check('bad_null_mle_is_exact_prefix_maximizer', kernel == mle)
        check('bad_null_mle_inside_region', prefix['threshold'] >= 1)
        check('bad_null_mle_really_in_null', cert['bad_null_gap'] == expected_gap >= THRESHOLD)
        check('mle_unknown_not_intersection_impossibility', cert['status'] == 'unknown'
              and not cert['leaves'] and cert['partitions'] == 0
              and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
        return False
    nonlinear = bilinear(case, query, chosen, alternative)
    count = 32 if nonlinear else 1
    leaves = cert['leaves']
    expected_intervals = [[F(j, count), F(j+1, count)] for j in range(count)]
    check('fixed_partition_covers_full_retry_simplex', cert['partitions'] == count
          and [leaf['retry_interval'] for leaf in leaves] == expected_intervals)
    expected_slope = (gap(case, query, chosen, alternative, corner_kernel(0, 'RECOVERY', 1))
                      -gap(case, query, chosen, alternative, corner_kernel(0, 'RECOVERY', 0)))
    check('exact_retry_interaction_slope', cert['retry_slope'] == expected_slope)
    uppers = [audit_leaf(case, query, chosen, alternative, counts, leaf, check) for leaf in leaves]
    finite = [upper for upper in uppers if upper is not None]
    if not finite:
        certified = kind == 'empty_global_bad_null'
        check('complete_empty_global_null', certified and len(leaves) == count
              and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
    else:
        upper = max(finite)
        check('global_likelihood_bound_covers_all_cells', kind == 'global_likelihood_dual'
              and cert['log_bad_likelihood_upper'] >= upper)
        lower = cert['log_mixture_lower']-cert['log_bad_likelihood_upper']
        check('outward_global_likelihood_ratio_lower', cert['log_e_lower'] <= lower)
        certified = cert['log_e_lower'] > cert['log_threshold_upper']
    check('strict_global_null_exclusion_status', cert['status'] == ('certified' if certified else 'unknown'))
    return certified


def phase(index):
    return 'late_B' if 42 <= index < 54 else ('A_RETURN' if 54 <= index < 78 else None)


def select(original):
    failed, controls, selected = {}, set(), {}
    for row in sorted(original.values(), key=lambda r: (r['life'], r['index'], r['arm'])):
        region = phase(row['index'])
        if region is None:
            continue
        key = row['life'], row['index'], row['arm']
        group = row['life'], row['arm'], region, row['identity']
        if row['spent'] == 384 and not row['terminal_plan']['query_ready'] and group not in failed:
            failed[group] = key
            selected[key] = ('failure', region)
        control = row['life'], row['arm'], region
        if row['terminal_plan']['query_ready'] and control not in controls:
            controls.add(control)
            selected[key] = ('positive', region)
    return selected


def prefixes(record):
    """Reconstruct from audited V231 counts and the fixed new allocation."""
    regions = product_regions(record)
    order = ('pool', 'inherited_pool', 'source', 'inherited_source', 'member')
    return [dict(name=name, **regions[name], operators=list(regions[name]['counts']))
            for name in order if name in regions]


def classify_truth(prefix, kernel):
    normalizer, likelihood = F(1), F(1)
    for op in prefix['operators']:
        counts = prefix['counts'][op]
        normalizer *= integrated_likelihood(tuple(counts[cat] for cat in ALPHABETS[op]))
        for cat, count in counts.items():
            likelihood *= kernel[op][cat]**count
    return normalizer <= prefix['threshold']*likelihood


def read_gzip(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def run():
    started, checks, expected = perf_counter(), Counter(), Counter()

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    read = lambda name: json.loads((OUTPUT/name).read_text())
    metadata, summary = read('run.json'), read('summary.json')
    old_audit = json.loads((previous.OUTPUT/'analysis.json').read_text())
    check('old_input_records_independently_audited', old_audit['valid'] and old_audit['complete']
          and old_audit['records'] == 432)
    check('zero_observation_qualification', metadata['complete'] and summary['complete']
          and metadata['qualification_only'] and summary['qualification_only']
          and metadata['new_observations'] == metadata['new_paid_samples'] == 0
          and summary['new_observations'] == summary['new_paid_samples'] == 0
          and not metadata['scientific_gate_changed'] and not summary['scientific_gate_changed'])
    check('post_certificate_truth_phase', metadata['phases'] ==
          ['inputs_frozen', 'certificates_frozen', 'oracle_evaluated', 'complete'])
    originals = {(r['life'], r['index'], r['arm']): r
                 for life in previous.LIVES for r in previous.records_for(life)}
    selected = select(originals)
    inputs, results = read_gzip(OUTPUT/'inputs.jsonl.gz'), read_gzip(OUTPUT/'records.jsonl.gz')
    keys = lambda rows: [(r['life'], r['index'], r['arm']) for r in rows]
    check('all_fixed_failures_and_controls_once', set(keys(inputs)) == set(keys(results)) == set(selected)
          and len(inputs) == len(results) == len(selected) == 24
          and Counter(kind for kind, _ in selected.values()) == {'failure': 12, 'positive': 12})
    check('frozen_input_selection_manifest', metadata['selected'] == [
        dict(life=r['life'], index=r['index'], arm=r['arm'], kind=r['kind'], phase=r['phase']) for r in inputs])
    for record in inputs:
        key = record['life'], record['index'], record['arm']
        old = originals[key]
        check('retained_input_equals_original', {k: v for k, v in record.items() if k not in ('kind', 'phase')} == old)
        check('fixed_selection_kind_and_phase', (record['kind'], record['phase']) == selected[key])
    scores = {(r['life'], r['index'], r['arm']): r for r in read('scores.json')}
    coverage, certificate_count, leaf_count, all_false = [], 0, 0, 0
    for result in results:
        key = result['life'], result['index'], result['arm']
        original = originals[key]
        case = original['case']
        _, laws, _, _ = previous.world(result['life'])
        kernel, groups = laws[result['index']], prefixes(original)
        check('unchanged_case_and_old_decisions', result['case'] == case
              and result['old_queries'] == original['terminal_plan']['query_certificates']
              and result['old_query_ready'] == original['terminal_plan']['query_ready'])
        check('complete_unchanged_prefix_roster', result['prefixes'] == groups)
        covered = [classify_truth(prefix, kernel) for prefix in groups]
        coverage.append(dict(life=result['life'], index=result['index'], arm=result['arm'],
                             all_inside=all(covered), prefixes=dict(zip((r['name'] for r in groups), covered))))
        check('all_selected_true_kernels_inside', all(covered))
        check('all_three_queries_once', set(result['queries']) == set(route.WEIGHTS))
        for query, decision in result['queries'].items():
            chosen = original['terminal_plan']['queries'][query]['policy']
            check('unchanged_selected_pure_policy', decision['policy'] == chosen)
            check('complete_comparison_roster', [c['other'] for c in decision['comparisons']] ==
                  [p for p in route.POLICIES if p != chosen])
            for comparison in decision['comparisons']:
                attempts = comparison['attempts']
                names = [item['prefix'] for item in attempts]
                check('ordered_prefix_short_circuit', bool(attempts)
                      and names == [prefix['name'] for prefix in groups[:len(attempts)]])
                flags = []
                for attempted, prefix in zip(attempts, groups):
                    proof = attempted['certificate']
                    certified = audit_certificate(case, query, chosen, comparison['other'], prefix, proof, check)
                    flags.append(certified)
                    certificate_count += 1
                    leaf_count += len(proof['leaves'])
                    check('certified_truth_not_in_bad_null', not certified or
                          gap(case, query, chosen, comparison['other'], kernel) < THRESHOLD)
                first = names[flags.index(True)] if any(flags) else None
                check('valid_used_prefix_and_comparison_decision', comparison['used_prefix'] == first
                      and comparison['certified'] == (first is not None)
                      and not any(flags[:-1]) and (any(flags) or len(attempts) == len(groups)))
            check('query_and_all_comparators', decision['certified'] ==
                  all(c['certified'] for c in decision['comparisons']))
        ready = all(q['certified'] for q in result['queries'].values())
        check('query_ready_all_three_queries', result['query_ready'] == ready and result['new_observations'] == 0)
        regrets = route.actual_regrets(case, kernel, result['queries'])
        false = sum(result['queries'][q]['certified'] and regret > THRESHOLD for q, regret in regrets.items())
        all_false += false
        check('independent_true_regrets', fractions(scores[key]['regrets']) == regrets
              and scores[key]['false_certificates'] == false)
        print(f'audit profile life={key[0]} index={key[1]} arm={key[2]} '
              f'query_ready={ready}', flush=True)
    aggregates = {}
    for kind in ('failure', 'positive'):
        rows = [r for r in results if r['kind'] == kind]
        aggregates[kind] = dict(targets=len(rows), old_query_ready=sum(r['old_query_ready'] for r in rows),
            query_ready=sum(r['query_ready'] for r in rows),
            queries={q: sum(r['queries'][q]['certified'] for r in rows) for q in route.WEIGHTS},
            arms={arm: dict(targets=sum(r['arm'] == arm for r in rows),
                          query_ready=sum(r['query_ready'] and r['arm'] == arm for r in rows))
                  for arm in previous.ARMS})
    check('summary_counts', summary['groups'] == aggregates and summary['records'] == len(results)
          and summary['false_certificates'] == all_false)
    result = dict(valid=all(checks[name] == n for name, n in expected.items()), complete=True,
        records=len(results), certificates=certificate_count, partition_leaves=leaf_count,
        true_kernels_inside=sum(r['all_inside'] for r in coverage), false_certificates=all_false,
        checks=dict(checks), expected=dict(expected),
        failures={name: n-checks[name] for name, n in expected.items() if n != checks[name]},
        truth_coverage=coverage, new_observations=0, seconds=perf_counter()-started)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'expected', 'truth_coverage')}), flush=True)
    return result


if __name__ == '__main__':
    run()

