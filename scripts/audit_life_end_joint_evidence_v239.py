"""Thin independent audit of all-paid V235 evidence on V238 endpoints.

The settled V238 endpoint audit supplies provenance and fees. The independent
V235 global-null auditor checks source-inclusive counts, mixture likelihood,
gap projections and all dual leaves. No V239 producer is imported.
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
from scripts import audit_joint_query_qualification_v235 as global_audit

OUTPUT = ROOT/'reports/life_end_joint_evidence_v239'
POLICIES = global_audit.POLICIES


def key(row):
    return row['life'], row['index'], row['arm']


def audit_comparison(tape, query, chosen, other, certificate, check):
    return global_audit.audit_certificate(tape['operators'], tape['case'], query,
                                         chosen, other, certificate, check)


def audit_query_and(decision, ready, check):
    check('complete_query_comparison_and', decision['certified'] == all(ready))


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    prior = ROOT/'reports/life_end_query_evidence_v238'
    original_directory = ROOT/'reports/kernel_query_profile_v232'
    early_directory = ROOT/'reports/joint_query_qualification_v235'
    metadata, summary = evidence.load(OUTPUT/'run.json'), evidence.load(OUTPUT/'summary.json')
    prior_summary, prior_audit = evidence.load(prior/'summary.json'), evidence.load(prior/'analysis.json')
    check('settled_endpoint_provenance_and_costs', prior_audit['valid'] and prior_audit['records'] == 24)
    check('unchanged_settled_endpoint_tape_copy', (OUTPUT/'tapes.jsonl.gz').read_bytes()
          == (prior/'tapes.jsonl.gz').read_bytes())
    check('frozen_same_endpoint_and_all_paid_engine', metadata['complete']
        and metadata['stream_count'] == 48 and metadata['threshold'] == evidence.THRESHOLD
        and metadata['partitions'] == 32 and metadata['delta_per_life_arm'] == '1/20'
        and metadata['certification_index'] == 77 and metadata['engine'] == 'V235_joint_all_paid'
        and metadata['qualification_only'] and not metadata['scientific_gate_changed']
        and metadata['new_observations'] == metadata['new_paid_samples'] == 0
        and metadata['phases'] == ['protocol_frozen', 'tapes_frozen', 'certificates_frozen',
                                  'saved_truth_evaluated', 'complete'])
    tapes, rows = evidence.read_rows(OUTPUT/'tapes.jsonl.gz'), evidence.read_rows(OUTPUT/'records.jsonl.gz')
    originals = {key(row): row for row in evidence.read_rows(original_directory/'inputs.jsonl.gz')}
    early = {key(row): row for row in evidence.read_rows(early_directory/'records.jsonl.gz')}
    previous = {key(row): row for row in evidence.read_rows(prior/'records.jsonl.gz')}
    truth = {key(row): row for row in evidence.load(ROOT/'reports/paired_query_score_v233/scores.json')}
    scores = {key(row): row for row in evidence.load(OUTPUT/'scores.json')}
    check('fixed_twenty_four_policy_case_roster', len(rows) == len(tapes) == 24
        and [key(row) for row in rows] == [key(row) for row in tapes] == list(originals)
        and metadata['selected'] == [{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                                     for row in tapes])
    cache, comparisons, leaves, false_certificates = set(), 0, 0, 0
    statuses, witness_kinds = Counter(), Counter()
    for tape, row in zip(tapes, rows):
        snapshot = key(row)
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        plan = originals[snapshot]['terminal_plan']
        check('same_original_case_full_life_fees_and_endpoint', all(row[field] == tape[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'early_fees',
            'endpoint_index', 'certificate_index', 'evidence_end_index'))
            and row['row_lengths'] == {operator: len(values) for operator, values in tape['operators'].items()}
            and row['old_query_ready'] == plan['query_ready']
            and row['v235_query_ready'] == early[snapshot]['query_ready']
            and row['v238_query_ready'] == previous[snapshot]['query_ready']
            and row['new_observations'] == row['new_paid_samples'] == 0)
        check('analytic_reward_wait_is_unchanged', row['queries']['reward']
            == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')
            and plan['queries']['reward']['policy'] == 'WAIT')
        before, row_comparisons = len(cache), 0
        for query in ('goal', 'risk'):
            chosen, decision = plan['queries'][query]['policy'], row['queries'][query]
            alternatives = [policy for policy in POLICIES if policy != chosen]
            check('original_policy_and_complete_alternative_roster', decision['policy'] == chosen
                  and [cert['other'] for cert in decision['comparisons']] == alternatives)
            ready = []
            for other, cert in zip(alternatives, decision['comparisons']):
                location.update(query=query, chosen=chosen, other=other)
                ready.append(audit_comparison(tape, query, chosen, other, cert, check))
                counts = tuple(sorted((name, tuple(sorted(values.items())))
                                     for name, values in cert['projected_counts'].items()))
                cache.add((tape['case']['operating'], F(tape['case']['retry_cost']), query,
                           chosen, other, cert['family'], counts, 32))
                comparisons += 1
                row_comparisons += 1
                leaves += len(cert['leaves'])
                statuses[cert['status']] += 1
                witness_kinds[cert['witness_kind']] += 1
            audit_query_and(decision, ready, check)
        check('three_queries_and_and_exact_cache_accounting', row['query_ready'] == all(
            decision['certified'] for decision in row['queries'].values())
            and row['unique_profile_calls'] == len(cache)-before
            and row['profile_cache_hits'] == row_comparisons-(len(cache)-before))
        expected_false = sum(row['queries'][query]['certified'] and F(regret) > evidence.REGRET
                             for query, regret in truth[snapshot]['regrets'].items())
        check('truth_scoring_uses_unchanged_original_policies', scores[snapshot]['regrets'] == truth[snapshot]['regrets']
            and scores[snapshot]['false_certificates'] == expected_false)
        false_certificates += expected_false
    groups = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in rows if row['kind'] == kind]
        blockers = Counter(cert['family'] for row in selected for query in ('goal', 'risk')
                           for cert in row['queries'][query]['comparisons'] if not cert['certified'])
        groups[kind] = dict(targets=len(selected), old_query_ready=sum(row['old_query_ready'] for row in selected),
            v235_query_ready=sum(row['v235_query_ready'] for row in selected),
            v238_query_ready=sum(row['v238_query_ready'] for row in selected),
            query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected) for query in ('reward', 'goal', 'risk')},
            blockers_by_family=dict(blockers), arms={arm: dict(targets=sum(row['arm'] == arm for row in selected),
                query_ready=sum(row['arm'] == arm and row['query_ready'] for row in selected))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    stage = groups['failure']['query_ready'] > 0 and groups['positive']['query_ready'] == 12 and false_certificates == 0
    check('same_settled_life_cost_reference', summary['life_costs'] == prior_summary['life_costs'])
    check('exact_summary_and_fixed_stage_condition', summary['complete'] and summary['records'] == 24
        and summary['groups'] == groups and summary['stage_condition_met'] == stage and summary['certification_index'] == 77
        and summary['unique_profile_calls'] == len(cache) and summary['profile_cache_hits'] == comparisons-len(cache)
        and summary['false_certificates'] == false_certificates
        and summary['model_seconds'] == sum(row['model_seconds'] for row in rows)
        and summary['new_observations'] == summary['new_paid_samples'] == 0
        and summary['qualification_only'] and not summary['scientific_gate_changed'])
    result = dict(valid=not failures, complete=True, records=24, comparisons=comparisons,
        independently_checked_leaves=leaves, unique_profile_calls=len(cache), statuses=dict(statuses),
        witness_kinds=dict(witness_kinds), groups=groups, stage_condition_met=stage,
        false_certificates=false_certificates, settled_endpoint_audit_reused=True,
        new_observations=0, new_paid_samples=0, checks=dict(checks), failures=failures,
        seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
