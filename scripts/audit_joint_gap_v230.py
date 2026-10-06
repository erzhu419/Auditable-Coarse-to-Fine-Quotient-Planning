"""Independent likelihood, dual-witness and truth audit for V230 qualification.

The producer's joint likelihood/support code is not imported.  Half-integer
Gamma ratios are reconstructed as exact factorial ratios before taking logs.
These checks concern retained-input exploratory qualification, not a new Gate.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from math import factorial
import json
from pathlib import Path
import sys
from time import perf_counter

OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
ALPHABETS = {'SHORT_PASS': ('DELIVERY', 'LOST'),
             'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
             'RECOVERY_RETRY': ('DELIVERY', 'LOST')}
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
WEIGHTS = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
COSTS = {'low': (F(1, 10), F(1, 20)), 'high': (F(3, 25), F(7, 100))}
NUMERICAL_TOLERANCE = D('1e-85')


def decimal(value):
    value = F(value)
    return D(value.numerator)/D(value.denominator)


@lru_cache(maxsize=None)
def log_mixture(counts):
    """Jeffreys multinomial mixture likelihood via exact factorial identities."""
    n, categories = sum(counts), len(counts)
    numerator = 1
    for k in counts:
        numerator *= factorial(2*k)//factorial(k)
    if categories == 2:
        denominator = 4**n*factorial(n)
    elif categories == 3:
        numerator *= 2*factorial(n+1)
        denominator = factorial(2*n+2)
    else:
        raise ValueError('V230 has only two- or three-category operators')
    with localcontext() as context:
        context.prec = 100
        return D(numerator).ln()-D(denominator).ln()


def log_minimum(region):
    counts = tuple(region['counts'].values())
    with localcontext() as context:
        context.prec = 100
        return log_mixture(counts)-decimal(region['threshold']).ln()


def contains(region, probabilities):
    with localcontext() as context:
        context.prec = 100
        likelihood = D(0)
        for category, count in region['counts'].items():
            probability = decimal(probabilities[category])
            if count and probability == 0:
                return False
            if count:
                likelihood += count*probability.ln()
        return likelihood+NUMERICAL_TOLERANCE >= log_minimum(region)


def dual_upper(constraints, coefficients, witness):
    """Evaluate a feasible weak-dual witness independently at 100 digits."""
    if witness['kind'] == 'simplex':
        return decimal(max(map(F, coefficients.values())))
    lambdas = tuple(F(value) for value in witness['lambdas'])
    nu = F(witness['nu'])
    if len(lambdas) != len(constraints) or any(value < 0 for value in lambdas):
        raise ValueError('invalid likelihood-dual multipliers')
    if nu <= max(map(F, coefficients.values())):
        raise ValueError('dual nu must exceed every coefficient')
    with localcontext() as context:
        context.prec = 100
        value = decimal(nu)
        for multiplier, region in zip(lambdas, constraints):
            value -= decimal(multiplier)*log_minimum(region)
        for category, coefficient in coefficients.items():
            count = sum(multiplier*region['counts'][category]
                        for multiplier, region in zip(lambdas, constraints))
            if count:
                term = decimal(count)
                value += term*((term/decimal(nu-F(coefficient))).ln()-1)
        return value


def audit_support(constraints, coefficients, support):
    if support['witness']['kind'] == 'simplex':
        return F(support['upper']) >= max(map(F, coefficients.values()))
    bound = dual_upper(constraints, coefficients, support['witness'])
    with localcontext() as context:
        context.prec = 100
        claimed = decimal(support['upper'])
        return claimed+NUMERICAL_TOLERANCE >= bound


def binary_interval(constraints):
    """Independent outer bracket for the binary likelihood intersection."""
    lower, upper = D(0), D(1)
    with localcontext() as context:
        context.prec = 100
        for region in constraints:
            first, second = region['counts']['DELIVERY'], region['counts']['LOST']
            n = first+second
            if not n:
                continue
            minimum = log_minimum(region)
            point = D(first)/D(n)

            def feasible(probability):
                if (first and probability == 0) or (second and probability == 1):
                    return False
                value = (first*probability.ln() if first else D(0))
                value += second*(1-probability).ln() if second else D(0)
                return value >= minimum

            lo, hi = D(0), point
            if first:
                for _ in range(260):
                    mid = (lo+hi)/2
                    if feasible(mid):
                        hi = mid
                    else:
                        lo = mid
            lower = max(lower, lo)
            lo, hi = point, D(1)
            if second:
                for _ in range(260):
                    mid = (lo+hi)/2
                    if feasible(mid):
                        lo = mid
                    else:
                        hi = mid
            upper = min(upper, hi)
    return lower, upper


def vectors(case, kernel):
    short_cost, detour_cost = COSTS[case['operating']]
    retry_cost = F(case['retry_cost'])
    short, detour, retry = (kernel[op] for op in OPERATORS)
    recovery = detour['RECOVERY']
    return {'WAIT': [F(0)]*3,
            'SHORT': [-short_cost, short['LOST'], short['DELIVERY']],
            'DETOUR_RETURN': [-detour_cost, detour['LOST'], detour['DELIVERY']],
            'DETOUR_RETRY': [-detour_cost-recovery*retry_cost,
                             detour['LOST']+recovery*retry['LOST'],
                             detour['DELIVERY']+recovery*retry['DELIVERY']]}


def utility(vector, weights):
    reward, failure, goal = weights
    return reward*vector[0]-failure*vector[1]+goal*vector[2]


def actual_regrets(case, kernel, queries):
    pure = vectors(case, kernel)
    return {query: max(utility(vector, weights) for vector in pure.values())
            -utility(pure[queries[query]['policy']], weights)
            for query, weights in WEIGHTS.items()}


def comparison_weights(case, query, other, chosen, short_delivery, retry_delivery):
    """Express the complete policy difference as a linear DETOUR row value."""
    s, r = F(short_delivery), F(retry_delivery)
    kernel = {'SHORT_PASS': {'DELIVERY': s, 'LOST': 1-s},
              'RECOVERY_RETRY': {'DELIVERY': r, 'LOST': 1-r}}
    result = {}
    for category in ALPHABETS['DETOUR_PASS']:
        kernel['DETOUR_PASS'] = {cat: F(cat == category)
                                for cat in ALPHABETS['DETOUR_PASS']}
        pure = vectors(case, kernel)
        result[category] = utility(pure[other], WEIGHTS[query])-utility(pure[chosen], WEIGHTS[query])
    return result


def audit_certificates(case, constraints_by_op, certificate):
    """Verify each dual, corner coverage, coefficient and reported maximum."""
    checks = Counter()
    short_interval = binary_interval(constraints_by_op['SHORT_PASS'])
    retry_interval = binary_interval(constraints_by_op['RECOVERY_RETRY'])
    if certificate.get('empty', False):
        valid = short_interval[0] > short_interval[1] or retry_interval[0] > retry_interval[1]
        return dict(valid=valid, checks={'proven_empty_candidate': int(valid)},
                    expected={'proven_empty_candidate': 1})
    rows = certificate['support_records']
    for row in rows:
        expected = comparison_weights(case, row['query'], row['other'], row['chosen'],
                                      row['short_delivery'], row['retry_delivery'])
        checks['correct_coefficients'] += {cat: F(value) for cat, value in row['weights'].items()} == expected
        checks['valid_dual_bounds'] += audit_support(constraints_by_op['DETOUR_PASS'], expected, row['support'])
    for query, qrow in certificate['queries'].items():
        relevant = [row for row in rows if row['query'] == query]
        checks['correct_chosen_policy'] += all(row['chosen'] == qrow['policy'] for row in relevant)
        checks['correct_query_maximum'] += (F(qrow['regret_upper']) >= max(
            [F(0)]+[F(row['support']['upper']) for row in relevant]))
        checks['correct_threshold'] += qrow['certified'] == (F(qrow['regret_upper']) <= F(1, 20))
        for other in POLICIES:
            if other == qrow['policy']:
                continue
            corners = [row for row in relevant if row['other'] == other]
            s_values = {F(row['short_delivery']) for row in corners}
            r_values = {F(row['retry_delivery']) for row in corners}
            with localcontext() as context:
                context.prec = 100
                checks['binary_corner_coverage'] += (bool(corners)
                    and decimal(min(s_values)) <= short_interval[0]+NUMERICAL_TOLERANCE
                    and decimal(max(s_values))+NUMERICAL_TOLERANCE >= short_interval[1]
                    and decimal(min(r_values)) <= retry_interval[0]+NUMERICAL_TOLERANCE
                    and decimal(max(r_values))+NUMERICAL_TOLERANCE >= retry_interval[1]
                    and {(F(row['short_delivery']), F(row['retry_delivery'])) for row in corners}
                        == set(product(s_values, r_values)))
    checks['correct_all_ready'] += certificate['all_ready'] == all(
        row['certified'] for row in certificate['queries'].values())
    expected = dict(correct_coefficients=len(rows), valid_dual_bounds=len(rows),
                    correct_chosen_policy=3, correct_query_maximum=3,
                    correct_threshold=3, binary_corner_coverage=3*(len(POLICIES)-1),
                    correct_all_ready=1)
    return dict(valid=all(checks[key] == value for key, value in expected.items()),
                checks=dict(checks), expected=expected)


def audit_witnesses():
    """Independently verify explicitly feasible, conflicting joint-region kernels."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from scripts.analyze_scoped_lifecycle_v229 import world
    output, source_input = root/'reports/action_gap_v230', root/'reports/scoped_lifecycle_v229'
    read = lambda name: json.loads((output/name).read_text())
    records = {(row['life'], row['index']): row for row in read('records.json')}
    witnesses, summary = read('witnesses.json'), read('witness_summary.json')
    sources = {row['life']: row for row in json.loads((source_input/'source_evidence.json').read_text())}
    histories = {life: [row for line in (source_input/f'records_life_{life:02d}.jsonl').read_text().splitlines()
                  if (row := json.loads(line))['arm'] == 'REPAIR_CS']
                 for life, _ in records}
    checks, expected, grouped = Counter(), Counter(), {}

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    for witness in witnesses:
        record = records[witness['life'], witness['index']]
        check('oracle_diagnostic_scope', witness['method'] == 'ORACLE_CUMULATIVE_POOL'
              and record['role'] == 'failure')
        if not witness['found']:
            continue
        kernel = {op: {cat: F(value) for cat, value in row.items()}
                  for op, row in witness['kernel'].items()}
        check('simplex_kernel', set(kernel) == set(OPERATORS)
              and all(set(kernel[op]) == set(ALPHABETS[op])
                  and sum(kernel[op].values()) == 1
                  and all(F(0) <= value <= F(1) for value in kernel[op].values()) for op in OPERATORS))
        constraints = deepcopy(record['methods']['ORACLE_CUMULATIVE_POOL']['constraints'][str(record['true_index'])])
        inherited = {}
        if record['case']['context'] == 'B':
            _, _, identities, metadata = world(record['life'])
            a_index = metadata['b_to_a'][record['true_index']]
            source = sources[record['life']]['a'][a_index]
            pooled = deepcopy(source)
            for previous in histories[record['life']]:
                if previous['index'] < 27 and identities[previous['index']] == a_index:
                    for op in OPERATORS:
                        for category in ALPHABETS[op]:
                            pooled[op][category] += previous['member'][op][category]
            inherited = {op: [dict(counts=counts[op], threshold=720,
                                   event=f'l{record["life"]}/A/pool{a_index}/{op}')
                              for counts in (source, pooled)] for op in OPERATORS
                         if op != metadata['changed_operator']}
        check('independent_inherited_A_counts', witness['inherited_A_constraints'] == inherited)
        for op, regions in inherited.items():
            constraints[op].extend(regions)
        for op, regions in constraints.items():
            for region in regions:
                check('all_joint_constraints_satisfied', contains(region, kernel[op]))
        pure = vectors(record['case'], kernel)
        gap = (utility(pure[witness['alternative_policy']], WEIGHTS[witness['query']])
               -utility(pure[witness['chosen_policy']], WEIGHTS[witness['query']]))
        check('exact_conflicting_regret', gap == F(witness['regret']) > F(1, 20)
              and F(witness['threshold']) == F(1, 20))
        grouped.setdefault((witness['life'], witness['index'], witness['query']), set()).add(witness['chosen_policy'])
    for case in summary['cases']:
        policies = grouped.get((case['life'], case['index'], case['query']), set())
        check('all_pure_policy_inference', case['all_pure_policies_have_counterexample'] == (policies == set(POLICIES)))
    check('no_new_witness_observations', summary['new_observations'] == 0)
    check('attempt_count', summary['attempted'] == len(witnesses))
    check('found_count', summary['found'] == sum(row['found'] for row in witnesses))
    result = dict(valid=all(checks[key] == n for key, n in expected.items()),
                  attempted=len(witnesses), found=sum(row['found'] for row in witnesses),
                  cases=len(grouped), checks=dict(checks), expected=dict(expected), new_observations=0)
    (output/'witness_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def run():
    """Audit the small frozen retained qualification and write one result file."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    # The V229 auditor reconstructs the task independently of the producer.
    from scripts.analyze_scoped_lifecycle_v229 import world

    begun = perf_counter()
    input_path, output_path = root/'reports/scoped_lifecycle_v229', root/'reports/action_gap_v230'
    read = lambda path: json.loads(path.read_text())
    records, acquisition = read(output_path/'records.json'), read(output_path/'acquisition.json')
    sources = {row['life']: row for row in read(input_path/'source_evidence.json')}
    selected = read(output_path/'selection.json')
    checks, expected, evidence = Counter(), Counter(), []
    rows_by_life, worlds = {}, {}
    for life in {row['life'] for row in records}:
        rows_by_life[life] = {row['index']: row
            for line in (input_path/f'records_life_{life:02d}.jsonl').read_text().splitlines()
            if (row := json.loads(line))['arm'] == 'REPAIR_CS'}
        worlds[life] = world(life)

    def record_check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    record_check('complete_records', len(records) == len(selected) == 12)
    for row, selection in zip(records, selected):
        life, index = row['life'], row['index']
        cases, laws, identities, _ = worlds[life]
        old_row = rows_by_life[life][index]
        context, identity = cases[index]['context'], identities[index]
        anchors = sources[life]['a' if context == 'A' else 'b']
        member = {op: dict.fromkeys(ALPHABETS[op], 0) for op in OPERATORS}
        for batch in old_row['batches']:
            for category, count in batch['increments'].items():
                member[batch['operator']][category] += count
        pool = {op: dict(anchors[identity][op]) for op in OPERATORS}
        for previous_index, previous in rows_by_life[life].items():
            if previous_index <= index and cases[previous_index]['context'] == context and identities[previous_index] == identity:
                for op in OPERATORS:
                    for cat in ALPHABETS[op]:
                        pool[op][cat] += previous['member'][op][cat]
        record_check('selection_identity', {key: row[key] for key in ('life', 'index', 'role')} == selection)
        record_check('unchanged_retained_case', row['case'] == old_row['case'] == cases[index])
        record_check('unchanged_retained_counts', row['member'] == member == old_row['member'])
        record_check('unchanged_source_counts', row['source_counts'] == anchors)
        record_check('true_pool_counts', row['pooled_counts'] == pool)
        record_check('true_index', row['true_index'] == identity)
        record_check('same_chosen_queries', row['chosen'] == old_row['terminal_plan']['queries'])
        actual = actual_regrets(cases[index], laws[index], row['chosen'])
        record_check('actual_query_regret', {q: F(v) for q, v in row['actual_regrets'].items()} == actual)
        record_check('no_new_observations', row['new_observations'] == 0)
        record_check('retained_cost', row['retained_spent'] == old_row['spent'] == sum(sum(r.values()) for r in member.values()) <= 384)
        source_count = sum(sum(r.values()) for anchor in anchors for r in anchor.values())
        record_check('paid_source_evidence', row['source_paid_samples'] == source_count == (3456 if context == 'A' else 1152))
        per_method = {}
        for method, data in row['methods'].items():
            keys = ('0', '1', '2') if method == 'PUBLIC_SOURCE_MEMBER' else (str(identity),)
            record_check('candidate_scope', set(data['constraints']) == set(data['candidate_certificates']) == set(keys))
            for key, by_op in data['constraints'].items():
                source_index = int(key)
                for op, regions in by_op.items():
                    reference = [dict(counts=anchors[source_index][op], threshold=720,
                                      event=f'l{life}/{context}/pool{source_index}/{op}'),
                                 dict(counts=member[op], threshold=8640,
                                      event=f'l{life}/member{index}/{op}')]
                    if method == 'ORACLE_CUMULATIVE_POOL':
                        reference.append(dict(counts=pool[op], threshold=720,
                                              event=f'l{life}/{context}/pool{source_index}/{op}'))
                    record_check('scoped_cs_identities', regions == reference)
                    if source_index == identity:
                        for region in regions:
                            record_check('joint_truth_containment', contains(region, laws[index][op]))
                audited = audit_certificates(cases[index], by_op, data['candidate_certificates'][key])
                record_check('valid_candidate_duals', audited['valid'])
                for check, count in audited['checks'].items():
                    checks['certificate_'+check] += count
                for check, count in audited['expected'].items():
                    expected['certificate_'+check] += count
            aggregate = data['query_certificates']
            retained_certificates = [cert for cert in data['candidate_certificates'].values()
                                     if not cert.get('empty', False)]
            record_check('true_candidate_retained', not data['candidate_certificates'][str(identity)].get('empty', False))
            for query in WEIGHTS:
                bound = max(F(cert['queries'][query]['regret_upper'])
                            for cert in retained_certificates)
                record_check('query_union_maximum', F(aggregate[query]['regret_upper']) == bound)
                record_check('aggregate_policy', aggregate[query]['policy'] == row['chosen'][query]['policy'])
                record_check('aggregate_threshold', aggregate[query]['certified'] == (bound <= F(1, 20)))
                record_check('actual_regret_covered', actual[query] <= bound)
            record_check('aggregate_all_ready', data['query_ready'] == all(value['certified'] for value in aggregate.values()))
            per_method[method] = dict(query_ready=data['query_ready'],
                                     truth_covered=all(contains(region, laws[index][op])
                                         for op, regions in data['constraints'][str(identity)].items() for region in regions))
        evidence.append(dict(life=life, index=index, role=row['role'], methods=per_method))

    record_check('complete_acquisition', len(acquisition) == 6)
    for row in acquisition:
        old_row = rows_by_life[row['life']][row['index']]
        prefix = {op: dict.fromkeys(ALPHABETS[op], 0) for op in OPERATORS}
        for batch in old_row['batches']:
            for cat, count in batch['increments'].items():
                prefix[batch['operator']][cat] += count
            if batch['spent'] == 256:
                break
        record_check('acquisition_actual_prefix', row['spent'] == 256 and row['member'] == prefix)
        record_check('discarded_forecasts', row['immutable'] is True and row['new_observations'] == 0)
        choice = row['proposed']
        record_check('legal_selected_operator', choice['operator'] in OPERATORS)
        record_check('forecast_horizons', choice['horizons'] == [16, 64, 128])
        record_check('candidate_not_branch_weighted', choice['candidate_scenarios'] == len(row['candidate_posteriors']))
        record_check('forecast_not_paid_budget', sum(sum(r.values()) for r in prefix.values()) == 256)
    summary = read(output_path/'summary.json')
    record_check('exploratory_qualification_only', summary['new_observations'] == 0 and summary['fresh_gate_run'] is False)
    record_check('no_environment_work', not any(summary['work'].get(key, 0)
        for key in ('controlled_samples', 'environment_random_draws', 'resets')))
    result = dict(valid=all(checks[key] == count for key, count in expected.items()),
                  records=len(records), certificates=expected.get('valid_candidate_duals', 0),
                  checks=dict(checks), expected=dict(expected), evidence=evidence,
                  new_observations=0, fresh_gate_run=False, seconds=perf_counter()-begun)
    (output_path/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('evidence', 'checks', 'expected')}), flush=True)
    return result


if __name__ == '__main__':
    run()
