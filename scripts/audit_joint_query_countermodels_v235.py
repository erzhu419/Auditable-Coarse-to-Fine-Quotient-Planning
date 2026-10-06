"""Independent exact checks for the seven frozen post-V235 countermodels.

The optimizer and producer are never imported.  Accepted witnesses establish
only membership in the selected comparison's fixed canonical terminal region.
"""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence
from scripts import audit_joint_query_qualification_v235 as qualification
from scripts import audit_kernel_query_profile_v232 as arithmetic

OUTPUT = ROOT/'reports/joint_query_qualification_v235'
ROSTER = ((0, 58, 'ORACLE_BALANCED'), (0, 58, 'ORACLE_GAP'),
          (1, 56, 'ORACLE_BALANCED'), (1, 56, 'ORACLE_GAP'),
          (2, 55, 'ORACLE_BALANCED'), (2, 55, 'ORACLE_GAP'), (2, 44, 'ORACLE_GAP'))
COORDINATES = {'S_D_FULL': (('S', 'DELIVERY'), ('D_FULL', 'DELIVERY'), ('D_FULL', 'RECOVERY')),
               'D_REC_R': (('D_REC', 'RECOVERY'), ('R', 'DELIVERY'))}


def witness_values(case, query, chosen, other, counts, parameters):
    """Return exact validity, gap and ratio for one sufficient parameter map."""
    family = evidence.relevant_family(query, chosen, other)
    if set(counts) != {evidence.ROW_NAMES[row] for row in evidence.FAMILY_ROWS[family]}:
        return False, None, None
    if set(parameters) != set(counts):
        return False, None, None
    for name, row in counts.items():
        if set(parameters[name]) != set(row):
            return False, None, None
        probabilities = list(map(F, parameters[name].values()))
        if min(probabilities) < 0 or sum(probabilities) != 1:
            return False, None, None
    projected = {name: {category: F(value) for category, value in row.items()}
                 for name, row in parameters.items()}
    kernel = qualification.embedded_kernel(projected)
    gap = evidence.utility(case, query, other, kernel)-evidence.utility(case, query, chosen, kernel)
    ratio = F(1)
    for name, row in counts.items():
        value = evidence.likelihood_ratio(tuple(row.values()), tuple(projected[name][category] for category in row))
        if value is None:
            return False, gap, None
        ratio *= value
    return gap > evidence.REGRET and ratio <= evidence.THRESHOLD, gap, ratio


def likelihood_geometry(counts, parameters):
    mle_bounds, bad_bounds, mixture_bounds, row_kl = [F(0), F(0)], [F(0), F(0)], [F(0), F(0)], {}
    for name, row in counts.items():
        n, empirical_bounds, parameter_bounds = sum(row.values()), [F(0), F(0)], [F(0), F(0)]
        for category, count in row.items():
            if count:
                empirical_log = arithmetic.logarithm(F(count, n))
                parameter_log = arithmetic.logarithm(F(parameters[name][category]))
                for endpoint in (0, 1):
                    empirical_bounds[endpoint] += count*empirical_log[endpoint]
                    parameter_bounds[endpoint] += count*parameter_log[endpoint]
        row_kl[name] = ((empirical_bounds[0]-parameter_bounds[1])/n,
                        (empirical_bounds[1]-parameter_bounds[0])/n) if n else (F(0), F(0))
        mixture_log = arithmetic.logarithm(evidence.predictive_weight(tuple(row.values())))
        for endpoint in (0, 1):
            mle_bounds[endpoint] += empirical_bounds[endpoint]
            bad_bounds[endpoint] += parameter_bounds[endpoint]
            mixture_bounds[endpoint] += mixture_log[endpoint]
    return dict(log_mle=tuple(mle_bounds), log_bad=tuple(bad_bounds), log_mixture=tuple(mixture_bounds),
        mle_minus_bad=(mle_bounds[0]-bad_bounds[1], mle_bounds[1]-bad_bounds[0]),
        mle_minus_mixture=(mle_bounds[0]-mixture_bounds[1], mle_bounds[1]-mixture_bounds[0]), row_kl=row_kl)


def contains_bounds(saved, expected):
    lo, hi = F(saved['lower']), F(saved['upper'])
    return lo <= expected[0] and hi >= expected[1]


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    protocol, inputs, rows, summary = (evidence.load(OUTPUT/name) for name in (
        'countermodel_protocol.json', 'countermodel_inputs.json', 'countermodels.json', 'countermodel_summary.json'))
    key = lambda row: (row['life'], row['index'], row['arm'])
    tapes = {key(row): row for row in evidence.read_rows(OUTPUT/'tapes.jsonl.gz')}
    qualification_rows = {key(row): row for row in evidence.read_rows(OUTPUT/'records.jsonl.gz')}
    old = {key(row): row for row in evidence.load(ROOT/'reports/kernel_query_profile_v232/countermodels.json') if row['found']}
    rectangles = {key(row): row for row in evidence.load(ROOT/'reports/shared_prefix_score_v234/diagnosis.json')[
        'terminal_rectangle_witnesses']}
    check('prior_complete_certificates_already_audited', evidence.load(OUTPUT/'analysis.json')['valid'])
    check('fixed_seven_post_qualification_comparisons', len(rows) == len(inputs) == 7
          and tuple(map(key, rows)) == tuple(map(key, inputs)) == ROSTER
          and protocol['selected'] == [{field: row[field] for field in (
              'life', 'index', 'arm', 'kind', 'phase', 'query', 'chosen', 'other', 'family')} for row in inputs])
    check('fixed_proposal_scope_and_numeric_limits', protocol['complete']
          and protocol['phases'] == ['protocol_frozen', 'inputs_frozen', 'witnesses_checked', 'complete']
          and protocol['optimizer'] == 'SLSQP' and protocol['maxiter'] == 200
          and protocol['ftol'] == protocol['mle_smoothing'] == 1e-12
          and protocol['proposal_margin'] == 1e-8
          and protocol['coordinate_bounds'] == [1e-12, 1-1e-12]
          and protocol['full_detour_sum_upper'] == 1-1e-12
          and protocol['objective_scaling'] == 'negative_log_likelihood_divided_by_required_sample_total'
          and protocol['initial_order'] == 'projected_mle_smoothed_then_saved_bad_witness_or_uniform'
          and protocol['accept'] == 'exact_simplex_AND_gap_gt_1/20_AND_M_le_960L'
          and protocol['failure_to_find'] == 'unknown' and protocol['scope'] == 'canonical_terminal_only'
          and protocol['new_observations'] == protocol['new_paid_samples'] == 0
          and not protocol['scientific_gate_changed'])
    accepted, attempts_total, gaps, groups = 0, 0, [], {'failure': [], 'positive': []}
    for row, frozen in zip(rows, inputs):
        snapshot, tape = key(row), tapes[key(row)]
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        query, chosen = 'risk', 'DETOUR_RETURN'
        other = 'DETOUR_RETRY' if snapshot == ROSTER[-1] else 'SHORT'
        family = evidence.relevant_family(query, chosen, other)
        uniform = {operator: {category: F(1, len(categories)) for category in categories}
                   for operator, categories in evidence.ALPHABETS.items()}
        raw = {operator: dict(Counter(values)) for operator, values in tape['operators'].items()}
        counts, _ = evidence.named_projection(family, raw, uniform)
        unresolved = qualification_rows[snapshot]['queries']['risk']
        comparison = next(cert for cert in unresolved['comparisons'] if cert['other'] == other)
        check('unchanged_unresolved_original_comparison', unresolved['policy'] == chosen and not comparison['certified']
              and all(row[field] == frozen[field] == tape[field] for field in (
                  'life', 'index', 'arm', 'kind', 'phase', 'case'))
              and (row['query'], row['chosen'], row['other'], row['family']) == (query, chosen, other, family)
              and (frozen['query'], frozen['chosen'], frozen['other'], frozen['family']) == (query, chosen, other, family)
              and row['projected_counts'] == frozen['projected_counts'] == counts)
        if snapshot == ROSTER[-1]:
            original = rectangles[snapshot]
            p, q = F(original['p']), F(original['q'])
            prior = {'D_REC': {'RECOVERY': p, 'OTHER': 1-p}, 'R': {'DELIVERY': q, 'LOST': 1-q}}
            second_name = 'saved_bad_witness'
        elif snapshot in old:
            _, prior = evidence.named_projection(family, raw, old[snapshot]['kernel'])
            second_name = 'saved_bad_witness'
        else:
            prior = {name: {category: F(1, len(values)) for category in values} for name, values in counts.items()}
            second_name = 'uniform'
        coordinates = COORDINATES[family]
        expected_first = [(float(F(counts[name][category], sum(counts[name].values())))+1e-12)/
                          (1+len(counts[name])*1e-12) for name, category in coordinates]
        expected_second = [float(prior[name][category]) for name, category in coordinates]
        check('two_frozen_initial_vectors', [{name: {cat: F(p) for cat, p in values.items()}
              for name, values in frozen['saved_initial_parameters'].items()}] == [prior]
              and frozen['initials'] == [dict(name='projected_mle_smoothed', coordinates=expected_first),
                                          dict(name=second_name, coordinates=expected_second)])
        attempts = row['attempts']
        check('fixed_order_and_bounded_proposals', 1 <= len(attempts) <= 2
              and [attempt['initial'] for attempt in attempts] == ['projected_mle_smoothed', second_name][:len(attempts)]
              and all(0 <= attempt['iterations'] <= 200 and isinstance(attempt['optimizer_success'], bool) for attempt in attempts))
        check('post_diagnostic_claim_scope', row['scope'] == 'canonical_terminal_only'
              and row['new_observations'] == row['new_paid_samples'] == 0)
        attempts_total += len(attempts)
        if not row['found']:
            check('failure_to_find_stays_unknown', not row['valid'] and len(attempts) == 2
                  and 'parameters' not in row and 'gap' not in row and 'membership' not in row and 'geometry' not in row)
            groups[row['kind']].append(False)
            continue
        valid, gap, ratio = witness_values(tape['case'], query, chosen, other, counts, row['parameters'])
        check('exact_bad_simplex_gap_and_region', valid and row['valid'] and F(row['gap']) == gap)
        evidence.audit_membership(ratio, row['membership'], check)
        geometry, saved_geometry = likelihood_geometry(counts, row['parameters']), row['geometry']
        check('conditional_likelihood_geometry_bounds', contains_bounds(saved_geometry['log_mle_minus_log_bad'], geometry['mle_minus_bad'])
              and contains_bounds(saved_geometry['log_mle_minus_log_mixture'], geometry['mle_minus_mixture'])
              and saved_geometry['scope'] == 'conditional_observed_geometry_not_true_KL_or_new_sample_guarantee')
        check('conditional_per_row_kl_bounds', set(saved_geometry['per_row_kl_empirical_to_bad']) == set(counts)
              and all(saved_geometry['per_row_kl_empirical_to_bad'][name]['n'] == sum(counts[name].values())
                      and contains_bounds(saved_geometry['per_row_kl_empirical_to_bad'][name], bounds)
                      for name, bounds in geometry['row_kl'].items()))
        accepted += 1
        gaps.append(gap)
        groups[row['kind']].append(True)
    expected_groups = {kind: dict(cases=len(values), found=sum(values)) for kind, values in groups.items()}
    check('exact_countermodel_summary', summary['cases'] == 7 and summary['found'] == accepted
          and summary['unknown'] == 7-accepted and summary['groups'] == expected_groups
          and summary['attempts'] == attempts_total and summary['scope'] == 'canonical_terminal_only'
          and summary['new_observations'] == summary['new_paid_samples'] == 0
          and not summary['scientific_gate_changed'])
    result = dict(valid=not failures, complete=True, cases=7, accepted=accepted, unknown=7-accepted,
        groups=expected_groups, attempts=attempts_total, minimum_exact_gap=str(min(gaps)) if gaps else None,
        scope='canonical_terminal_only', new_observations=0, new_paid_samples=0,
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'countermodel_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
