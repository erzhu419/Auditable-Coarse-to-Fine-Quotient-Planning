"""Independent rational concave-tangent and fixed bad-witness audit.

No V240 producer or optimizer is imported. The previous paid endpoint audit
remains authoritative; this audit checks the two fixed convex null shapes,
full-domain supports, outward likelihood bounds and exact memberships.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence
from scripts import audit_joint_query_qualification_v235 as projected
from scripts import audit_kernel_query_profile_v232 as arithmetic

OUTPUT = ROOT/'reports/convex_query_null_v240'
REGRET, MARGIN = F(1, 20), F(1, 1000000)
STATUSES = ('admitted_bad_kernel', 'global_bad_null_excluded', 'unknown')


def key(row):
    return row['life'], row['index'], row['arm']


def exact_parameters(parameters):
    return {name: {category: F(value) for category, value in row.items()} for name, row in parameters.items()}


def strict_simplex(parameters, counts):
    return (set(parameters) == set(counts) and all(set(parameters[name]) == set(row)
        and sum(parameters[name].values()) == 1 and min(parameters[name].values()) >= 0
        for name, row in counts.items()))


def gap(case, other, parameters):
    kernel = projected.embedded_kernel(parameters)
    return evidence.utility(case, 'risk', other, kernel)-evidence.utility(case, 'risk', 'DETOUR_RETURN', kernel)


def tangent_components(case, family, counts, parameters, multiplier):
    """Exact h/gradients/residual support and independent loglikelihood UB."""
    parameters, multiplier = exact_parameters(parameters), F(multiplier)
    if not strict_simplex(parameters, counts) or multiplier < 0 or any(
            probability <= 0 for row in parameters.values() for probability in row.values()):
        raise ValueError('tangent requires a legal nonnegative multiplier and an interior simplex point')
    likelihood_upper = F(0)
    for name, row in counts.items():
        for category, count in row.items():
            if count:
                likelihood_upper += count*arithmetic.logarithm(parameters[name][category])[1]
    if family == 'S_D_FULL':
        h = gap(case, 'SHORT', parameters)-REGRET
        h_gradient = {'S': {'DELIVERY': F(8), 'LOST': F(0)},
                      'D_FULL': {'DELIVERY': F(-4), 'RECOVERY': F(0), 'LOST': F(4)}}
        f_gradient = {name: {category: F(count)/parameters[name][category] for category, count in row.items()}
                      for name, row in counts.items()}
        residual = {name: {category: value+multiplier*h_gradient[name][category]
                          for category, value in row.items()} for name, row in f_gradient.items()}
        support = sum((max(row.values())-sum(value*parameters[name][category] for category, value in row.items())
                       for name, row in residual.items()), F(0))
    elif family == 'D_REC_R':
        d, r = parameters['D_REC']['RECOVERY'], parameters['R']['DELIVERY']
        b = REGRET/8
        h = r-(4+F(case['retry_cost']))/8-b/d
        f_gradient = {'D_REC': F(counts['D_REC']['RECOVERY'])/d-F(counts['D_REC']['OTHER'])/(1-d),
                      'R': F(counts['R']['DELIVERY'])/r-F(counts['R']['LOST'])/(1-r)}
        h_gradient = {'D_REC': b/d**2, 'R': F(1)}
        residual = {coordinate: value+multiplier*h_gradient[coordinate]
                    for coordinate, value in f_gradient.items()}
        support = sum((max(value, F(0))-value*coordinate
                       for value, coordinate in ((residual['D_REC'], d), (residual['R'], r))), F(0))
    else:
        raise ValueError('only the two actual frozen null families are supported')
    return dict(point=parameters, h_point=h, gradient_likelihood=f_gradient, gradient_h=h_gradient,
        residual_gradient=residual, residual_support=support, log_likelihood_upper=likelihood_upper,
        global_upper=likelihood_upper+multiplier*h+support)


def fixed_membership(counts, parameters):
    parameters = exact_parameters(parameters)
    if not strict_simplex(parameters, counts):
        return False, None
    mixture, likelihood = F(1), F(1)
    for name, row in counts.items():
        mixture *= evidence.predictive_weight(tuple(row.values()))
        for category, count in row.items():
            likelihood *= parameters[name][category]**count
    ratio = mixture/likelihood if likelihood else None
    return ratio is not None and ratio <= evidence.THRESHOLD, ratio


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    prior = ROOT/'reports/life_end_joint_evidence_v239'
    previous = evidence.read_rows(prior/'records.jsonl.gz')
    previous_summary = evidence.load(prior/'summary.json')
    metadata, inputs, rows, summary = (evidence.load(OUTPUT/name) for name in (
        'run.json', 'input_records.json', 'records.json', 'summary.json'))
    check('settled_prior_qualification_valid', evidence.load(prior/'analysis.json')['valid'])
    selected = []
    for old in previous:
        if old['query_ready']:
            continue
        risk = old['queries']['risk']
        candidate = next((cert for other in ('SHORT', 'DETOUR_RETRY')
                          for cert in risk['comparisons'] if cert['other'] == other and not cert['certified']), None)
        if risk['policy'] != 'DETOUR_RETURN' or candidate is None:
            check('supported_unresolved_risk_direction', False)
        else:
            selected.append((old, candidate))
    expected_selected = [dict(life=old['life'], index=old['index'], arm=old['arm'], query='risk',
        chosen='DETOUR_RETURN', other=cert['other'], family=cert['family']) for old, cert in selected]
    check('fixed_nine_unresolved_single_comparisons', len(rows) == len(inputs) == len(selected) == 9
        and [key(row) for row in rows] == [key(row) for row in inputs] == [key(old) for old, _ in selected]
        and metadata['selected'] == expected_selected)
    check('unchanged_event_budget_and_static_classification_scope', metadata['complete']
        and metadata['records'] == 9 and metadata['families'] == {'S_D_FULL': 6, 'D_REC_R': 3}
        and metadata['threshold'] == evidence.THRESHOLD and F(metadata['regret_threshold']) == REGRET
        and metadata['stream_count'] == 48 and metadata['delta_per_life_arm'] == '1/20'
        and metadata['certificate_index'] == 77 and metadata['classification_only']
        and not metadata['qualification_changed'] and not metadata['scientific_gate_changed']
        and metadata['new_observations'] == metadata['new_paid_samples'] == 0
        and metadata['phases'] == ['protocol_frozen', 'inputs_frozen', 'classifications_frozen', 'complete'])
    statuses, by_kind, by_family = Counter(), defaultdict(Counter), defaultdict(Counter)
    for row, frozen, (old, old_comparison) in zip(rows, inputs, selected):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        family, counts, case = old_comparison['family'], old_comparison['projected_counts'], old['case']
        check('original_case_counts_fees_and_prior_comparison', frozen['old_comparison'] == old_comparison
            and frozen['case'] == case and frozen['fees'] == old['fees']
            and frozen['projected_counts'] == counts and frozen['family'] == family
            and (frozen['query'], frozen['chosen'], frozen['other']) == ('risk', 'DETOUR_RETURN', old_comparison['other'])
            and all(row[field] == value for field, value in frozen.items() if field != 'old_comparison')
            and row['new_observations'] == row['new_paid_samples'] == 0)
        result = arithmetic.fractions(row['result'])
        check('classification_retains_all_paid_canonical_region', result['family'] == family
            and result['projected_counts'] == counts and result['threshold'] == evidence.THRESHOLD
            and result['regret_threshold'] == REGRET)
        optimizer = result['optimizer']
        start = ([F(9, 10), F(1, 10), F(1, 20), F(1, 10), F(17, 20)]
                 if family == 'S_D_FULL' else [F(1, 2), F(9, 10)])
        check('single_fixed_numerical_proposal', optimizer['method'] == 'SLSQP' and optimizer['start'] == start
            and optimizer['options'] == dict(maxiter=500, ftol=1e-12)
            and optimizer['bounds'] == [1e-9, 1-1e-9]
            and optimizer['objective_scaling'] == 'negative_log_likelihood_divided_by_projected_count_total'
            and isinstance(optimizer['success'], bool) and 0 <= optimizer['iterations'] <= 500)
        point = result['proposed_point']
        interior = point is not None and strict_simplex(point, counts) and all(
            probability > 0 for values in point.values() for probability in values.values())
        if not interior:
            check('invalid_proposal_preserves_unknown', result['status'] == 'unknown'
                  and result['repaired_witness'] is None and result['global_tangent'] is None)
        else:
            candidate = {name: dict(values) for name, values in point.items()}
            if family == 'S_D_FULL':
                repaired_s = point['S']['DELIVERY']+(REGRET+MARGIN-gap(case, 'SHORT', point))/8
                candidate['S'] = dict(DELIVERY=repaired_s, LOST=1-repaired_s)
            else:
                d = point['D_REC']['RECOVERY']
                repaired_r = (4+F(case['retry_cost'])+(REGRET+MARGIN)/d)/8
                candidate['R'] = dict(DELIVERY=repaired_r, LOST=1-repaired_r)
            witness = result['repaired_witness']
            feasible = strict_simplex(candidate, counts)
            check('fixed_strict_bad_parameter_repair', witness['parameters'] == candidate and witness['feasible'] == feasible)
            admitted = False
            if feasible:
                measured_gap = gap(case, old_comparison['other'], candidate)
                check('exact_strict_bad_gap', witness['gap'] == measured_gap == REGRET+MARGIN and measured_gap > REGRET)
                admitted, ratio = fixed_membership(counts, candidate)
                evidence.audit_membership(ratio, row['result']['repaired_witness']['membership'], check)
            else:
                check('infeasible_repair_cannot_be_a_bad_witness', witness['gap'] is None and witness['membership'] is None)
            tangent = result['global_tangent']
            multiplier = tangent['multiplier']
            check('legal_nonnegative_multiplier_and_original_tangent_point', multiplier >= 0 and tangent['point'] == point)
            expected = tangent_components(case, family, counts, point, multiplier)
            check('exact_concave_constraint_and_likelihood_gradients', tangent['h_point'] == expected['h_point']
                and tangent['gradient_likelihood'] == expected['gradient_likelihood']
                and tangent['gradient_h'] == expected['gradient_h']
                and tangent['residual_gradient'] == expected['residual_gradient'])
            fixed_multiplier = (max(F(0), (expected['gradient_likelihood']['S']['LOST']
                -expected['gradient_likelihood']['S']['DELIVERY'])/8) if family == 'S_D_FULL'
                else max(F(0), -expected['gradient_likelihood']['R']))
            check('fixed_legal_multiplier_rule', multiplier == fixed_multiplier)
            check('complete_domain_support_and_outward_tangent_upper', tangent['residual_support'] == expected['residual_support']
                and tangent['log_likelihood_upper'] >= expected['log_likelihood_upper']
                and tangent['global_upper'] == tangent['log_likelihood_upper']+multiplier*tangent['h_point']+tangent['residual_support']
                and tangent['global_upper'] >= expected['global_upper'])
            minimum = sum((arithmetic.logarithm(evidence.predictive_weight(tuple(values.values())))[0]
                           for values in counts.values()), F(0))
            check('outward_all_paid_mixture_and_event_threshold', tangent['log_mixture_lower'] <= minimum
                and tangent['log_threshold_upper'] >= arithmetic.logarithm(evidence.THRESHOLD)[1]
                and tangent['log_e_lower'] == tangent['log_mixture_lower']-tangent['global_upper'])
            excluded = tangent['log_e_lower'] > tangent['log_threshold_upper']
            check('strict_global_exclusion_and_exact_final_status', tangent['certified'] == excluded
                and not (admitted and excluded) and result['status'] == (
                    'admitted_bad_kernel' if admitted else 'global_bad_null_excluded' if excluded else 'unknown'))
        status = result['status']
        statuses[status] += 1
        by_kind[row['kind']][status] += 1
        by_family[family][status] += 1
    status_counts = {status: statuses[status] for status in STATUSES}
    groups = {kind: dict(records=sum(by_kind[kind].values()),
        statuses={status: by_kind[kind][status] for status in STATUSES}) for kind in ('failure', 'positive')}
    families = {family: dict(records=sum(by_family[family].values()),
        statuses={status: by_family[family][status] for status in STATUSES}) for family in ('S_D_FULL', 'D_REC_R')}
    check('exact_static_diagnostic_summary_and_unchanged_life_costs', summary['complete'] and summary['records'] == 9
        and summary['statuses'] == status_counts and summary['groups'] == groups and summary['families'] == families
        and summary['fixed_evidence_numerical_repair_ruled_out_cases'] == statuses['admitted_bad_kernel']
        and summary['global_bound_repair_cases'] == statuses['global_bad_null_excluded']
        and summary['unknown_cases'] == statuses['unknown'] and summary['life_costs'] == previous_summary['life_costs']
        and summary['model_seconds'] == sum(row['model_seconds'] for row in rows) and summary['optimizer_calls'] == 9
        and summary['classification_only'] and not summary['qualification_changed']
        and not summary['scientific_gate_changed'] and summary['new_observations'] == summary['new_paid_samples'] == 0)
    result = dict(valid=not failures, complete=True, records=9, statuses=status_counts, groups=groups, families=families,
        fixed_evidence_numerical_repair_ruled_out_cases=statuses['admitted_bad_kernel'],
        global_bound_repair_cases=statuses['global_bad_null_excluded'], unknown_cases=statuses['unknown'],
        settled_endpoint_audit_reused=True, scope='selected_fixed_canonical_region_only',
        new_observations=0, new_paid_samples=0, checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
