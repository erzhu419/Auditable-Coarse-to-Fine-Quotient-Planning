"""Independent global-null audit for the fixed V235 projected qualification.

The old independent weak-dual arithmetic checks denominator bounds.  This
audit supplies the genuinely projected mixture numerator and verifies that
the zero-count embedding preserves the complete query gap hypothesis.
"""
from collections import Counter
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence
from scripts import audit_kernel_query_profile_v232 as arithmetic

OUTPUT = ROOT/'reports/joint_query_qualification_v235'
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')


def embedded_counts(projected):
    result = {operator: dict.fromkeys(categories, 0)
              for operator, categories in evidence.ALPHABETS.items()}
    if 'S' in projected:
        result[evidence.S].update(projected['S'])
    if 'D_FULL' in projected:
        result[evidence.D].update(projected['D_FULL'])
    elif 'D_DEL' in projected:
        row = projected['D_DEL']
        result[evidence.D].update(DELIVERY=row['DELIVERY'], LOST=row['OTHER'])
    elif 'D_REC' in projected:
        row = projected['D_REC']
        result[evidence.D].update(RECOVERY=row['RECOVERY'], LOST=row['OTHER'])
    if 'R' in projected:
        result[evidence.R].update(projected['R'])
    return result


def embedded_kernel(projected):
    result = {evidence.S: {'DELIVERY': F(0), 'LOST': F(1)},
              evidence.D: {'DELIVERY': F(0), 'LOST': F(1), 'RECOVERY': F(0)},
              evidence.R: {'DELIVERY': F(0), 'LOST': F(1)}}
    for name, row in projected.items():
        if name == 'S':
            result[evidence.S] = row
        elif name == 'R':
            result[evidence.R] = row
        elif name == 'D_FULL':
            result[evidence.D] = row
        elif name == 'D_DEL':
            result[evidence.D] = dict(DELIVERY=row['DELIVERY'], LOST=row['OTHER'], RECOVERY=F(0))
        elif name == 'D_REC':
            result[evidence.D] = dict(DELIVERY=F(0), LOST=row['OTHER'], RECOVERY=row['RECOVERY'])
    return result


def preserved_gap(case, query, chosen, other, family):
    """All vertices suffice: route gaps are affine per row, bilinear in D/R."""
    empty = {operator: dict.fromkeys(categories, 0) for operator, categories in evidence.ALPHABETS.items()}
    for short, detour, retry in product((F(0), F(1)), evidence.ALPHABETS[evidence.D], (F(0), F(1))):
        kernel = {evidence.S: dict(DELIVERY=short, LOST=1-short),
                  evidence.D: {category: F(category == detour) for category in evidence.ALPHABETS[evidence.D]},
                  evidence.R: dict(DELIVERY=retry, LOST=1-retry)}
        _, projected = evidence.named_projection(family, empty, kernel)
        embedded = embedded_kernel(projected)
        before = evidence.utility(case, query, other, kernel)-evidence.utility(case, query, chosen, kernel)
        after = evidence.utility(case, query, other, embedded)-evidence.utility(case, query, chosen, embedded)
        if before != after:
            return False
    return True


def audit_certificate(queues, case, query, chosen, other, saved, check):
    cert = arithmetic.fractions(saved)
    family = evidence.relevant_family(query, chosen, other)
    raw = {operator: dict(Counter(values)) for operator, values in queues.items()}
    # Only the counts are needed; uniform parameters give the projection's
    # category roster without importing a producer.
    uniform = {operator: {cat: F(1, len(categories)) for cat in categories}
               for operator, categories in evidence.ALPHABETS.items()}
    counts, _ = evidence.named_projection(family, raw, uniform)
    embedding = embedded_counts(counts)
    check('canonical_full_paid_sufficient_counts', cert['family'] == family
          and cert['projected_counts'] == counts and cert['embedded_counts'] == embedding)
    check('original_fixed_comparison_and_event', (cert['query'], cert['chosen'], cert['other'])
          == (query, chosen, other) and cert['threshold'] == evidence.THRESHOLD
          and cert['regret_threshold'] == evidence.REGRET)
    check('global_gap_preserving_zero_count_embedding', preserved_gap(case, query, chosen, other, family))
    minimum = sum((arithmetic.logarithm(evidence.predictive_weight(tuple(row.values())))[0]
                   for row in counts.values()), F(0))
    check('outward_true_projected_mixture_numerator', cert['log_mixture_lower'] <= minimum)
    check('outward_fixed_event_threshold', cert['log_threshold_upper'] >= arithmetic.logarithm(evidence.THRESHOLD)[1])
    kind = cert['witness_kind']
    if kind == 'bad_null_mle':
        mle = {operator: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                         for cat, count in row.items()} for operator, row in embedding.items()}
        gap = evidence.utility(case, query, other, mle)-evidence.utility(case, query, chosen, mle)
        _, projected_mle = evidence.named_projection(family, raw, mle)
        likelihood = F(1)
        for name, row in counts.items():
            for category, count in row.items():
                likelihood *= projected_mle[name][category]**count
        mixture = F(1)
        for row in counts.values():
            mixture *= evidence.predictive_weight(tuple(row.values()))
        check('bad_null_mle_exact_and_projected_region_admitted', cert['bad_null_kernel'] == mle
              and cert['bad_null_gap'] == gap >= evidence.REGRET and mixture <= likelihood)
        check('mle_branch_preserves_unknown_scope', cert['status'] == 'unknown'
              and not cert['certified'] and cert['partitions'] == 0 and not cert['leaves']
              and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
        return False
    nonlinear = arithmetic.bilinear(case, query, chosen, other)
    count = 32 if nonlinear else 1
    leaves = cert['leaves']
    check('fixed_partition_covers_entire_retry_simplex', cert['partitions'] == count
          and [leaf['retry_interval'] for leaf in leaves] == [[F(i, count), F(i+1, count)] for i in range(count)])
    slope = (arithmetic.gap(case, query, chosen, other, arithmetic.corner_kernel(0, 'RECOVERY', 1))
             -arithmetic.gap(case, query, chosen, other, arithmetic.corner_kernel(0, 'RECOVERY', 0)))
    check('exact_query_retry_interaction_slope', cert['retry_slope'] == slope)
    uppers = [arithmetic.audit_leaf(case, query, chosen, other, embedding, leaf, check) for leaf in leaves]
    finite = [value for value in uppers if value is not None]
    if not finite:
        ready = kind == 'empty_global_bad_null'
        check('complete_global_bad_null_empty', ready and len(leaves) == count
              and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
    else:
        upper = max(finite)
        check('global_likelihood_upper_covers_every_cell', kind == 'global_likelihood_dual'
              and cert['log_bad_likelihood_upper'] >= upper)
        check('outward_projected_global_likelihood_ratio', cert['log_e_lower'] <=
              cert['log_mixture_lower']-cert['log_bad_likelihood_upper'])
        ready = cert['log_e_lower'] > cert['log_threshold_upper']
    check('strict_global_bad_null_certificate', cert['certified'] == ready
          and cert['status'] == ('certified' if ready else 'unknown'))
    return ready


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    shared, original = ROOT/'reports/shared_prefix_score_v234', ROOT/'reports/kernel_query_profile_v232'
    prerequisite = evidence.load(ROOT/'reports/joint_query_evidence_v235/analysis.json')
    metadata, summary = evidence.load(OUTPUT/'run.json'), evidence.load(OUTPUT/'summary.json')
    check('independent_fixed_witness_prerequisite_passed', prerequisite['valid']
          and prerequisite['full_qualification_allowed'] and prerequisite['main_risk_admitted'] == 0)
    check('frozen_full_qualification_event_scope', metadata['complete']
          and metadata['stream_count'] == 48 and metadata['threshold'] == evidence.THRESHOLD
          and metadata['partitions'] == 32 and metadata['delta_per_life_arm'] == '1/20'
          and metadata['qualification_only'] and not metadata['scientific_gate_changed']
          and metadata['new_observations'] == metadata['new_paid_samples'] == 0
          and metadata['phases'] == ['prerequisite_passed', 'protocol_frozen', 'tapes_frozen',
              'certificates_frozen', 'saved_truth_evaluated', 'complete'])
    key = lambda row: (row['life'], row['index'], row['arm'])
    tapes, rows = evidence.read_rows(shared/'tapes.jsonl.gz'), evidence.read_rows(OUTPUT/'records.jsonl.gz')
    originals = {key(row): row for row in evidence.read_rows(original/'inputs.jsonl.gz')}
    previous = {key(row): row for row in evidence.read_rows(shared/'records.jsonl.gz')}
    truth = {key(row): row for row in evidence.load(ROOT/'reports/paired_query_score_v233/scores.json')}
    scored = {key(row): row for row in evidence.load(OUTPUT/'scores.json')}
    check('same_audited_paid_tape_copy', (OUTPUT/'tapes.jsonl.gz').read_bytes() == (shared/'tapes.jsonl.gz').read_bytes())
    check('same_fixed_twenty_four_case_roster', len(rows) == 24
          and [key(row) for row in rows] == [key(row) for row in tapes] == list(originals)
          and metadata['selected'] == [{field: tape[field] for field in (
              'life', 'index', 'arm', 'kind', 'phase')} for tape in tapes])
    cache, false_certificates, comparison_count, leaf_count = set(), 0, 0, 0
    statuses, families, witness_kinds = Counter(), Counter(), Counter()
    for row, tape in zip(rows, tapes):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        snapshot = key(row)
        plan = originals[snapshot]['terminal_plan']
        check('original_paid_snapshot_and_costs', all(row[field] == tape[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees'))
            and row['row_lengths'] == {operator: len(values) for operator, values in tape['operators'].items()}
            and row['new_observations'] == row['new_paid_samples'] == 0
            and row['old_query_ready'] == plan['query_ready']
            and row['v234_query_ready'] == previous[snapshot]['query_ready'])
        reward = row['queries']['reward']
        check('exact_reward_wait_policy', reward == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')
              and plan['queries']['reward']['policy'] == 'WAIT')
        before, row_comparisons = len(cache), 0
        for query in ('goal', 'risk'):
            decision = row['queries'][query]
            chosen = plan['queries'][query]['policy']
            alternatives = [policy for policy in POLICIES if policy != chosen]
            check('original_query_policy_and_complete_alternatives', decision['policy'] == chosen
                  and [certificate['other'] for certificate in decision['comparisons']] == alternatives)
            ready = []
            for other, certificate in zip(alternatives, decision['comparisons']):
                location.update(query=query, chosen=chosen, other=other)
                ready.append(audit_certificate(tape['operators'], tape['case'], query, chosen, other, certificate, check))
                counts = certificate['projected_counts']
                cache_key = (tape['case']['operating'], F(tape['case']['retry_cost']), query,
                    chosen, other, certificate['family'], tuple(sorted(
                        (name, tuple(sorted(values.items()))) for name, values in counts.items())), 32)
                cache.add(cache_key)
                comparison_count += 1
                row_comparisons += 1
                leaf_count += len(certificate['leaves'])
                statuses[certificate['status']] += 1
                families[certificate['family']] += 1
                witness_kinds[certificate['witness_kind']] += 1
            check('exact_query_comparison_and', decision['certified'] == all(ready))
        check('exact_three_query_and', row['query_ready'] == all(
            decision['certified'] for decision in row['queries'].values()))
        check('exact_record_cache_accounting', row['unique_profile_calls'] == len(cache)-before
              and row['profile_cache_hits'] == row_comparisons-(len(cache)-before))
        expected_false = sum(row['queries'][query]['certified'] and F(regret) > evidence.REGRET
                             for query, regret in truth[snapshot]['regrets'].items())
        check('post_certificate_unchanged_truth_scoring', scored[snapshot]['regrets'] == truth[snapshot]['regrets']
              and scored[snapshot]['false_certificates'] == expected_false)
        false_certificates += expected_false
    groups = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in rows if row['kind'] == kind]
        blockers = Counter(certificate['family'] for row in selected for query in ('goal', 'risk')
                           for certificate in row['queries'][query]['comparisons'] if not certificate['certified'])
        groups[kind] = dict(targets=len(selected), old_query_ready=sum(row['old_query_ready'] for row in selected),
            v234_query_ready=sum(row['v234_query_ready'] for row in selected),
            query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected)
                     for query in ('reward', 'goal', 'risk')}, blockers_by_family=dict(blockers))
    check('exact_qualification_summary', summary['complete'] and summary['records'] == 24
          and summary['groups'] == groups and summary['unique_profile_calls'] == len(cache)
          and summary['profile_cache_hits'] == comparison_count-len(cache)
          and summary['false_certificates'] == false_certificates
          and summary['model_seconds'] == sum(row['model_seconds'] for row in rows)
          and summary['new_observations'] == summary['new_paid_samples'] == 0
          and summary['qualification_only'] and not summary['scientific_gate_changed'])
    result = dict(valid=not failures, complete=True, records=24, comparisons=comparison_count,
        independently_checked_leaves=leaf_count, statuses=dict(statuses), families=dict(families),
        witness_kinds=dict(witness_kinds), unique_profile_calls=len(cache),
        false_certificates=false_certificates, groups=groups,
        new_observations=0, new_paid_samples=0, checks=dict(checks), failures=failures,
        seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
