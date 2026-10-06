"""Independent zero-observation classification under proposed product CSs.

Excluding old ranking countermodels is qualification only, never a query
certificate or a reclassification of the frozen V231 lifecycle result.
"""
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_oracle_gap_lifecycle_v231 as audit
from scripts.audit_oracle_gap_countermodels_v231 import integrated_likelihood

OUTPUT = audit.OUTPUT


def product_regions(row):
    constraints, context = row['terminal_plan']['joint_constraints'], row['case']['context']
    current_ops = tuple(audit.OPERATORS)
    threshold = 480 if context == 'A' else 240
    result = dict(
        member=dict(threshold=2880, counts={op: constraints[op][2]['counts'] for op in current_ops}),
        source=dict(threshold=threshold, counts={op: constraints[op][0]['counts'] for op in current_ops}),
        pool=dict(threshold=threshold, counts={op: constraints[op][1]['counts'] for op in current_ops}))
    if context == 'B':
        inherited = tuple(op for op in current_ops if len(constraints[op]) == 5)
        result.update(
            inherited_source=dict(threshold=480, counts={op: constraints[op][3]['counts'] for op in inherited}),
            inherited_pool=dict(threshold=480, counts={op: constraints[op][4]['counts'] for op in inherited}))
    return result


def classify(regions, kernel):
    """Exact normalizer and joint likelihood products decide each inequality."""
    inside = {}
    for name, region in regions.items():
        normalizer, likelihood = F(1), F(1)
        for op, counts in region['counts'].items():
            normalizer *= integrated_likelihood(tuple(counts[cat] for cat in audit.ALPHABETS[op]))
            for cat, count in counts.items():
                likelihood *= F(kernel[op][cat])**count
        inside[name] = normalizer <= region['threshold']*likelihood
    return dict(all_inside=all(inside.values()), constraints=inside)


def run():
    begun, checks, expected = perf_counter(), Counter(), Counter()

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    read = lambda name: json.loads((OUTPUT/name).read_text())
    candidate = read('joint_kernel_qualification.json')
    previous = read('countermodel_analysis.json')
    check('old_countermodels_independently_verified', previous['valid']
          and previous['verified_countermodels'] == 47)
    check('qualification_only', candidate['new_environment_observations'] == candidate['new_paid_samples'] == 0
          and not candidate['query_null_support_implemented']
          and not candidate['query_certificates_obtained'] and not candidate['v231_reclassified'])
    allocations = [(row['family'], row['streams'], F(row['family_delta']), row['threshold'])
                   for row in candidate['candidate']['allocations']]
    expected_allocations = [('member_full', 72, F(1, 40), 2880), ('A_full', 3, F(1, 160), 480),
                           ('A_unchanged', 3, F(1, 160), 480), ('B_full', 3, F(1, 80), 240)]
    check('proposed_event_allocation', allocations == expected_allocations
          and sum(row[2] for row in allocations) == F(1, 20)
          and all(F(streams, threshold) == delta for _, streams, delta, threshold in allocations))
    old = [row for row in read('countermodels.json') if row['found']]
    keys = {(row['life'], row['index'], row['arm']) for row in old}
    original = {}
    for life in audit.LIVES:
        for row in audit.records_for(life):
            key = row['life'], row['index'], row['arm']
            if key in keys:
                original[key] = row
    old_by_key = {(row['life'], row['index'], row['arm'], row['query'], row['chosen_policy']): row for row in old}
    seen, counts, actual_counts = set(), Counter(), Counter()

    def verify(saved, kernel, record):
        regions = product_regions(record)
        classification = classify(regions, kernel)
        label = 'inside' if classification['all_inside'] else 'excluded'
        family = 'A_full' if record['case']['context'] == 'A' else 'B_full'
        metadata = dict(member=('member_full', 'current_prefix'), source=(family, 'source_prefix'),
                        pool=(family, 'current_prefix'), inherited_source=('A_unchanged', 'source_prefix'),
                        inherited_pool=('A_unchanged', 'switch_prefix'))
        declared = {(item['family'], item['prefix']): item for item in saved['checks']}
        check('complete_prefix_constraint_roster', set(declared) == {metadata[name] for name in regions}
              and len(declared) == len(saved['checks']))
        for name, region in regions.items():
            item = declared[metadata[name]]
            check('fixed_operator_subset_and_threshold', item['operators'] == list(region['counts'])
                  and item['threshold'] == region['threshold'])
            check('exact_product_likelihood_classification', item['membership'] ==
                  ('inside' if classification['constraints'][name] else 'excluded'))
        check('correct_snapshot_status', saved['status'] == label)
        return label

    for saved in candidate['witnesses']:
        key = saved['life'], saved['index'], saved['arm'], saved['query'], saved['candidate_policy']
        witness = old_by_key[key]
        seen.add(key)
        record = original[key[:3]]
        label = verify(saved, witness['kernel'], record)
        is_actual = record['terminal_plan']['queries'][saved['query']]['policy'] == saved['candidate_policy']
        check('correct_actual_terminal_policy_flag', saved['actual_terminal_selected_policy'] == is_actual)
        counts[label] += 1
        if is_actual:
            actual_counts[label] += 1
    check('all_old_countermodels_classified_once', seen == set(old_by_key)
          and len(candidate['witnesses']) == len(old_by_key))
    truths, truth_counts = set(), Counter()
    for saved in candidate['true_kernel_coverage']['snapshots']:
        key = saved['life'], saved['index'], saved['arm']
        truths.add(key)
        _, laws, _, _ = audit.world(saved['life'])
        label = verify(saved, laws[saved['index']], original[key])
        check('true_kernel_coverage_flag', saved['coverage'] == (label == 'inside'))
        truth_counts[label] += 1
    check('all_selected_true_kernels_once', truths == set(original)
          and len(candidate['true_kernel_coverage']['snapshots']) == len(original))
    summary = candidate['summary']
    check('classification_summary', summary['tested'] == 47
          and summary['excluded'] == counts['excluded'] and summary['inside'] == counts['inside']
          and summary['ambiguous'] == 0
          and summary['actual_terminal_selected_policy_found'] == sum(actual_counts.values())
          and summary['actual_terminal_selected_policy'] == dict(actual_counts))
    coverage = candidate['true_kernel_coverage']
    check('true_kernel_summary', coverage['selected_terminal_snapshots'] == len(original)
          and coverage['inside'] == truth_counts['inside'] and coverage['excluded'] == truth_counts['excluded']
          and coverage['ambiguous'] == coverage['new_environment_observations'] == 0)
    result = dict(valid=all(checks[name] == count for name, count in expected.items()), complete=True,
        old_countermodels=47, classifications=dict(counts), actual_chosen_countermodels=dict(actual_counts),
        true_kernels=len(original), true_kernel_classifications=dict(truth_counts),
        checks=dict(checks), expected=dict(expected),
        failures={name: count-checks[name] for name, count in expected.items() if count != checks[name]},
        new_observations=0, query_certificate_obtained=False, seconds=perf_counter()-begun)
    (OUTPUT/'joint_kernel_qualification_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'expected')}), flush=True)
    return result


if __name__ == '__main__':
    run()

