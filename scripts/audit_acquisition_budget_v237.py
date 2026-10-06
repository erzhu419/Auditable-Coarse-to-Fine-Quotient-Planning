"""Independent conditional testing bounds and matched acquisition fees.

No V237 producer or optimizer is imported. Exact V236 starting evidence is
recomputed by sequential prediction; an independent task reconstruction
supplies oracle laws solely for this diagnostic.
"""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_source_predictive_evidence_v236 as predictive
from scripts import audit_kernel_query_profile_v232 as arithmetic
from scripts.analyze_scoped_lifecycle_v229 import world

OUTPUT = ROOT/'reports/acquisition_budget_v237'
ROSTER = ((0, 58, 'ORACLE_GAP'), (1, 56, 'ORACLE_GAP'), (2, 55, 'ORACLE_GAP'))
THRESHOLD, TARGET_POWER, BATCH = 960, F(3, 4), 16


def categorical_kl(first, second):
    """Rational outer endpoints using independent 100-digit logarithms."""
    if set(first) != set(second) or sum(map(F, first.values())) != 1 or sum(map(F, second.values())) != 1:
        raise ValueError('matching categorical probability simplexes required')
    lower, upper = F(0), F(0)
    for category, value in first.items():
        p, q = F(value), F(second[category])
        if p < 0 or q <= 0:
            raise ValueError('this frozen diagnostic uses supported positive bad kernels')
        if p:
            lo, hi = arithmetic.logarithm(p/q)
            lower, upper = lower+p*lo, upper+p*hi
    return max(F(0), lower), max(F(0), upper)


def binary_kl(first, second):
    first, second = F(first), F(second)
    return categorical_kl({'YES': first, 'NO': 1-first}, {'YES': second, 'NO': 1-second})


def maximum_row_information(truth, bad):
    rows = {name: categorical_kl(values, bad[name]) for name, values in truth.items()}
    return rows, (max(bounds[0] for bounds in rows.values()), max(bounds[1] for bounds in rows.values()))


def valid_power_upper(probability, alpha, budget, information_upper):
    probability, alpha = F(probability), F(alpha)
    if not alpha <= probability <= 1:
        return False
    return probability == 1 or binary_kl(probability, alpha)[0] > budget*F(information_upper)


def cap_batches(expected_lower):
    scaled = F(expected_lower)/BATCH
    return BATCH*((scaled.numerator+scaled.denominator-1)//scaled.denominator)


def contains_bounds(saved, expected):
    return F(saved['lower']) <= expected[0] and F(saved['upper']) >= expected[1]


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    load, key = predictive.evidence.load, predictive.key
    protocol, inputs, oracle_inputs, rows, summary = (load(OUTPUT/name) for name in (
        'protocol.json', 'inputs.json', 'oracle_inputs.json', 'records.json', 'summary.json'))
    prior = ROOT/'reports/source_predictive_evidence_v236'
    costs_directory = ROOT/'reports/oracle_gap_lifecycle_v231'
    check('fixed_inputs_previously_audited', load(prior/'analysis.json')['valid']
          and load(costs_directory/'analysis.json')['valid'])
    original = {key(row): row for row in load(prior/'records.json') if row['origin'] == 'V235_countermodel'}
    costs = {(row['life'], row['arm']): row for row in load(costs_directory/'summary.json')['life_summaries']}
    check('three_fixed_gap_lives', tuple(map(key, inputs)) == tuple(map(key, oracle_inputs))
          == tuple(map(key, rows)) == ROSTER and len(rows) == 3
          and protocol['selected'] == [{field: row[field] for field in ('life', 'index', 'arm')} for row in rows])
    check('frozen_inputs_precede_oracle_truth', protocol['complete'] and protocol['phases'] == [
        'protocol_frozen', 'inputs_frozen', 'oracle_truth_loaded', 'bounds_frozen', 'complete']
        and all('truth_parameters' not in row and 'bounds' not in row for row in inputs))
    check('fixed_probability_cost_and_claim_scope', protocol['threshold'] == THRESHOLD
        and protocol['target_power'] == str(TARGET_POWER) and protocol['event_count_per_life_arm'] == 48
        and protocol['batch'] == BATCH and protocol['bisection_steps'] == 64
        and protocol['cost_scope'] == 'fresh_suffix_added_to_fixed_lifecycle_costs'
        and protocol['probability_scope'] == 'conditional_fixed_bad_witness_exclusion_not_whole_query'
        and protocol['oracle_truth_scope'] == 'diagnostic_bound_only_not_learner_or_acquisition'
        and not protocol['matched_rebuild_reference_available']
        and protocol['new_observations'] == protocol['new_paid_samples'] == 0
        and not protocol['scientific_gate_changed'] and not protocol['query_certificates_obtained'])
    expected_sum, headroom_sum, insufficient_lives = F(0), 0, []
    expected_totals = {0: (14144, 12112), 1: (17072, 17024), 2: (17168, 16352)}
    for frozen, oracle, row in zip(inputs, oracle_inputs, rows):
        snapshot, life = key(row), row['life']
        location = dict(life=life, index=row['index'], arm=row['arm'])
        source = original[snapshot]
        fields = ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'query',
                  'chosen', 'other', 'family', 'training_counts', 'validation_counts', 'parameters')
        check('unchanged_original_snapshot_and_bad_witness', all(
            row[field] == oracle[field] == frozen[field] == source[field] for field in fields)
            and source['membership']['exact_inside'] and row['query'] == 'risk'
            and row['family'] == 'S_D_FULL' and row['chosen'] == 'DETOUR_RETURN' and row['other'] == 'SHORT')
        balanced, gap = (costs[(life, arm)] for arm in ('ORACLE_BALANCED', 'ORACLE_GAP'))
        reference = dict(source_paid_samples_per_arm=4608,
            balanced_total=balanced['total_samples'], gap_total=gap['total_samples'],
            headroom=balanced['total_samples']-gap['total_samples'],
            scope='same_V231_life_GAP_vs_BALANCED_both_reuse_not_REBUILD')
        check('matched_life_total_fees_source_included', frozen['budget_reference'] == oracle['budget_reference']
            == row['budget_reference'] == reference and balanced['source_samples'] == gap['source_samples'] == 4608
            and (balanced['total_samples'], gap['total_samples']) == expected_totals[life])
        cases, laws, identities, _ = world(life)
        index = row['index']
        truth = {'S': laws[index][predictive.evidence.S], 'D_FULL': laws[index][predictive.evidence.D]}
        check('independent_oracle_world_and_necessary_rows', cases[index] == row['case']
            and identities[index] == row['identity'] and row['case']['stage'] == 'A_RETURN'
            and {name: {cat: F(value) for cat, value in values.items()}
                 for name, values in row['truth_parameters'].items()} == truth
            and row['truth_parameters'] == oracle['truth_parameters'])
        values = predictive.predictive_values(source['training_counts'], source['validation_counts'], source['parameters'])
        e0, alpha = values['conditional_ratio'], values['conditional_ratio']/THRESHOLD
        bounds = row['bounds']
        check('independent_sequential_starting_wealth_and_alpha', F(0) < alpha < TARGET_POWER
            and contains_bounds(bounds['log_e0'], arithmetic.logarithm(e0))
            and contains_bounds(bounds['log_alpha'], arithmetic.logarithm(alpha))
            and F(bounds['alpha_bounds']['lower']) <= alpha <= F(bounds['alpha_bounds']['upper']))
        row_information, maximum_information = maximum_row_information(truth, source['parameters'])
        check('independent_directional_row_kl_bounds', set(bounds['per_row_kl']) == set(truth)
            and all(contains_bounds(bounds['per_row_kl'][name], value) for name, value in row_information.items()))
        imax = F(bounds['imax_upper'])
        budget, budget_information = reference['headroom'], F(bounds['information_budget_upper'])
        check('optimistic_maximum_row_information_and_paid_cap', imax == max(F(value['upper'])
            for value in bounds['per_row_kl'].values()) and imax >= maximum_information[1]
            and budget_information == budget*imax and bounds['available_samples'] == budget
            and bounds['target'] == str(TARGET_POWER))
        need, required = F(bounds['information_need_lower']), F(bounds['expected_samples_lower'])
        check('conservative_expected_sample_and_batch_cap_lower_bound',
            F(0) < need <= binary_kl(TARGET_POWER, alpha)[0]
            and required == need/imax and bounds['required_batch_cap'] == cap_batches(required))
        insufficient = budget_information < need
        check('strict_necessary_budget_decision', bounds['budget_insufficient'] == insufficient)
        power = F(bounds['power_upper'])
        check('certified_power_upper_and_dyadic_resolution', valid_power_upper(power, alpha, budget, imax)
            and power.denominator <= 2**64 and (power.denominator & (power.denominator-1)) == 0
            and bounds['power_bisection_steps'] == 64
            and F(bounds['power_upper_bounds']['lower']) <= power <= F(bounds['power_upper_bounds']['upper']))
        if power < 1:
            witness_lower = F(bounds['power_upper_kl_lower'])
            check('outward_power_boundary_kl_witness', budget_information < witness_lower
                  <= binary_kl(power, alpha)[0])
        else:
            check('unit_probability_trivial_upper', bounds['power_upper_kl_lower'] is None)
        check('row_scope_and_fixed_suffix_interpretation', bounds['scope'] ==
            'oracle_necessary_suffix_budget_not_a_sampling_strategy_or_certificate'
            and row['interpretation'] == ('fixed_suffix_budget_insufficient_for_planned_power'
                if insufficient else 'not_ruled_out_by_necessary_bound')
            and row['new_observations'] == row['new_paid_samples'] == 0)
        expected_sum += required
        headroom_sum += budget
        if insufficient:
            insufficient_lives.append(life)
    check('distinct_life_sum_and_each_case_planning_requirement', summary['complete'] and summary['records'] == 3
        and summary['budget_insufficient_lives'] == insufficient_lives
        and F(summary['necessary_expected_samples_lower_sum']) == expected_sum
        and summary['matched_total_headroom'] == headroom_sum == 2896
        and summary['total_budget_insufficient'] == (expected_sum > headroom_sum)
        and summary['planning_requirement'] == 'each_fixed_case_exclusion_probability_at_least_3/4')
    check('summary_scientific_and_cost_scope', not summary['matched_rebuild_reference_available']
        and summary['new_observations'] == summary['new_paid_samples'] == 0
        and not summary['query_certificates_obtained'] and not summary['scientific_gate_changed']
        and summary['qualification_only']
        and summary['scope'] == 'necessary_bound_for_fixed_suffix_not_redesigned_lifecycle')
    result = dict(valid=not failures, complete=True, records=3,
        independent_starting_wealth_checks=3, independent_oracle_world_checks=3,
        exact_matched_headroom=headroom_sum, budget_insufficient_lives=insufficient_lives,
        necessary_expected_samples_lower_sum=str(expected_sum),
        total_budget_insufficient=expected_sum > headroom_sum,
        oracle_diagnostic_only=True, new_observations=0, new_paid_samples=0,
        scope='fixed_suffix_with_other_original_costs_preserved', checks=dict(checks), failures=failures,
        seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
