"""Independent integration audit; reuse valid V239/V240 proofs without reruns."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence

OUTPUT = ROOT/'reports/convex_query_qualification_v241'
V239 = ROOT/'reports/life_end_joint_evidence_v239'
V240 = ROOT/'reports/convex_query_null_v240'
ENGINE = 'V239_with_V240_fixed_comparisons'
WORK_FIELDS = ('unique_profile_calls', 'profile_cache_hits', 'model_seconds')


def key(row):
    return row['life'], row['index'], row['arm']


def comparison_key(row, query, cert):
    return (*key(row), query, cert['chosen'], cert['other'], cert['family'])


def audit_replacement(original, query, previous, diagnostic, index, certificate, check):
    check('replacement_matches_original_identity_case_costs_and_counts', all(
        diagnostic[field] == original[field] for field in
        ('life', 'index', 'arm', 'kind', 'case', 'identity', 'certificate_index', 'fees'))
        and (diagnostic['query'], diagnostic['chosen'], diagnostic['other'], diagnostic['family'])
        == (query, previous['chosen'], previous['other'], previous['family'])
        and diagnostic['projected_counts'] == previous['projected_counts']
        and diagnostic['result']['projected_counts'] == previous['projected_counts']
        and diagnostic['result']['family'] == previous['family'] and not previous['certified']
        and diagnostic['result']['threshold'] == previous['threshold'] == 960
        and F(diagnostic['result']['regret_threshold']) == F(previous['regret_threshold']) == F(1, 20))
    classification = diagnostic['result']
    certified = (classification['status'] == 'global_bad_null_excluded'
                 and classification['global_tangent']['certified'])
    expected = {field: previous[field] for field in
        ('query', 'chosen', 'other', 'family', 'projected_counts', 'threshold', 'regret_threshold')}
    expected.update(classification_status=classification['status'],
        status='certified' if certified else 'unknown', certified=certified,
        proof_reference=dict(artifact='reports/convex_query_null_v240/records.json', record_index=index,
            field='result.global_tangent' if classification['status'] == 'global_bad_null_excluded'
                  else 'result.repaired_witness' if classification['status'] == 'admitted_bad_kernel' else 'result'))
    if classification['status'] == 'admitted_bad_kernel':
        expected['admitted_witness'] = classification['repaired_witness']
    check('replacement_uses_exact_validated_proof_and_exclusion_only_decision', certificate == expected)
    return certified


def audit_reused_comparison(certificate, previous, check):
    check('unreplaced_comparison_is_exact_validated_v239_certificate', certificate == previous)
    return previous['certified']


def audit_and(decision, comparisons, check):
    check('complete_alternative_and', len(comparisons) == 3 and decision['certified'] == all(comparisons))


def audit_row_and(row, decisions, check):
    check('complete_three_query_and', set(decisions) == {'reward', 'goal', 'risk'}
          and row['query_ready'] == all(decisions.values()))


def run():
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    previous = evidence.read_rows(V239/'records.jsonl.gz')
    diagnostics = evidence.load(V240/'records.json')
    previous_summary = evidence.load(V239/'summary.json')
    previous_audit, convex_audit = evidence.load(V239/'analysis.json'), evidence.load(V240/'analysis.json')
    check('both_settled_input_audits_valid', previous_audit['valid'] and previous_audit['records'] == 24
          and convex_audit['valid'] and convex_audit['records'] == 9)
    metadata, references, rows, scores, summary = (evidence.load(OUTPUT/name) for name in
        ('run.json', 'input_references.json', 'records.json', 'scores.json', 'summary.json'))
    expected_references = dict(previous_records=str(V239/'records.jsonl.gz'), previous_audit=str(V239/'analysis.json'),
        previous_summary=str(V239/'summary.json'), paid_tapes=str(V239/'tapes.jsonl.gz'),
        convex_records=str(V240/'records.json'), convex_audit=str(V240/'analysis.json'),
        convex_summary=str(V240/'summary.json'), saved_truth=str(ROOT/'reports/paired_query_score_v233/scores.json'),
        spec=str(ROOT/'specs/CONVEX_QUERY_QUALIFICATION_V241.md'))
    check('settled_inputs_are_referenced_without_new_tape_or_cost_acquisition', references == expected_references)
    check('fixed_roster_and_order', len(rows) == len(previous) == len({key(row) for row in rows}) == 24
        and [key(row) for row in rows] == [key(row) for row in previous]
        and metadata['selected'] == [{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                                      for row in previous])
    check('fixed_evidence_budget_and_truth_after_certificate_freeze', metadata['complete'] and metadata['engine'] == ENGINE
        and metadata['stream_count'] == 48 and metadata['threshold'] == 960
        and metadata['regret_threshold'] == metadata['delta_per_life_arm'] == '1/20'
        and metadata['certification_index'] == 77 and metadata['qualification_only']
        and not metadata['scientific_gate_changed']
        and metadata['optimizer_calls'] == metadata['new_observations'] == metadata['new_paid_samples'] == 0
        and metadata['phases'] == ['protocol_frozen', 'input_references_frozen', 'certificates_frozen',
                                  'saved_truth_evaluated', 'complete'])
    expected_keys = []
    for row in previous:
        if row['query_ready']:
            continue
        chosen = next(cert for other in ('SHORT', 'DETOUR_RETRY')
                      for cert in row['queries']['risk']['comparisons'] if cert['other'] == other and not cert['certified'])
        expected_keys.append(comparison_key(row, 'risk', chosen))
    routes = {comparison_key(row, row['query'], row): (index, row) for index, row in enumerate(diagnostics)}
    check('exact_nine_frozen_diagnostic_routes', len(routes) == len(diagnostics) == 9
          and list(routes) == expected_keys)
    total, routed, reused, used_routes = 0, 0, 0, []
    for index, (row, original) in enumerate(zip(rows, previous)):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        preserved = set(original)-{'queries', 'query_ready', *WORK_FIELDS}
        check('all_original_metadata_policies_and_ready_references', all(row[field] == original[field] for field in preserved)
            and row['v239_query_ready'] == original['query_ready']
            and not any(field in row for field in WORK_FIELDS)
            and row['queries']['reward'] == original['queries']['reward'])
        decisions, indexes = {'reward': original['queries']['reward']['certified']}, []
        for query in ('goal', 'risk'):
            decision, prior_decision = row['queries'][query], original['queries'][query]
            check('original_policy_and_complete_alternative_order', set(decision) == set(prior_decision)
                and all(decision[field] == value for field, value in prior_decision.items()
                        if field not in ('certified', 'comparisons'))
                and len(decision['comparisons']) == len(prior_decision['comparisons']) == 3
                and [cert['other'] for cert in decision['comparisons']]
                    == [cert['other'] for cert in prior_decision['comparisons']])
            ready = []
            for certificate, prior_cert in zip(decision['comparisons'], prior_decision['comparisons']):
                location.update(query=query, chosen=prior_cert['chosen'], other=prior_cert['other'])
                route = comparison_key(original, query, prior_cert)
                if route in routes:
                    source_index, diagnostic = routes[route]
                    ready.append(audit_replacement(original, query, prior_cert, diagnostic, source_index, certificate, check))
                    indexes.append(source_index)
                    used_routes.append(route)
                    routed += 1
                else:
                    ready.append(audit_reused_comparison(certificate, prior_cert, check))
                    reused += 1
                total += 1
            audit_and(decision, ready, check)
            decisions[query] = all(ready)
        audit_row_and(row, decisions, check)
        check('exact_provenance_and_old_work_is_not_new_work', row['qualification_provenance'] == dict(
            engine=ENGINE, v239_record_index=index, v240_record_indexes=indexes,
            reused_comparisons=6-len(indexes), replaced_comparisons=len(indexes),
            v239_work={field: original[field] for field in WORK_FIELDS}))
    check('all_and_only_nine_replacements_and_135_reused_proofs', total == 144 and routed == 9 and reused == 135
          and len(set(used_routes)) == 9 and set(used_routes) == set(routes))
    truth = {key(row): row for row in evidence.load(ROOT/'reports/paired_query_score_v233/scores.json')}
    check('complete_frozen_truth_score_roster', len(scores) == 24
          and [key(row) for row in scores] == [key(row) for row in rows] and set(truth) == {key(row) for row in rows})
    false_certificates = 0
    for row, score in zip(rows, scores):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        regrets = truth[key(row)]['regrets']
        false = sum(row['queries'][query]['certified'] and F(value) > F(1, 20) for query, value in regrets.items())
        check('saved_original_policy_regrets_scored_after_freeze', score == dict(
            life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=regrets, false_certificates=false))
        false_certificates += false
    groups = {}
    for kind in ('failure', 'positive'):
        subset = [row for row in rows if row['kind'] == kind]
        blockers = Counter(cert['family'] for row in subset for query in ('goal', 'risk')
                           for cert in row['queries'][query]['comparisons'] if not cert['certified'])
        groups[kind] = dict(targets=len(subset),
            **{field: sum(row[field] for row in subset) for field in
               ('old_query_ready', 'v235_query_ready', 'v238_query_ready', 'v239_query_ready', 'query_ready')},
            queries={query: sum(row['queries'][query]['certified'] for row in subset) for query in ('reward', 'goal', 'risk')},
            blockers_by_family=dict(blockers), arms={arm: dict(targets=sum(row['arm'] == arm for row in subset),
                query_ready=sum(row['arm'] == arm and row['query_ready'] for row in subset))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    stage = groups['failure']['query_ready'] > 0 and groups['positive']['query_ready'] == 12 and false_certificates == 0
    location = {}
    check('stage_condition_and_group_totals', summary['complete'] and summary['records'] == 24
          and summary['groups'] == groups and summary['stage_condition_met'] == stage
          and summary['false_certificates'] == false_certificates)
    check('same_life_cost_reference_and_no_new_optimizer_or_acquisition', summary['life_costs'] == previous_summary['life_costs']
        and summary['total_comparisons'] == total and summary['routed_comparisons'] == routed
        and summary['reused_comparisons'] == reused and summary['engine'] == ENGINE
        and summary['certification_index'] == 77 and summary['qualification_only']
        and not summary['scientific_gate_changed']
        and summary['optimizer_calls'] == summary['new_observations'] == summary['new_paid_samples'] == 0
        and not any(field in summary for field in WORK_FIELDS))
    result = dict(valid=not failures, complete=True, records=24, total_comparisons=total,
        routed_comparisons=routed, reused_comparisons=reused, groups=groups,
        stage_condition_met=stage, false_certificates=false_certificates,
        settled_v239_and_v240_audits_reused=True, new_observations=0, new_paid_samples=0,
        optimizer_calls=0, checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
