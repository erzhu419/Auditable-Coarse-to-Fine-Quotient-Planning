"""Independent current-endpoint full-region witnesses after V247.

Only retained observations, proof parameters, public costs and interfaces are
read. No world, producer, optimizer or saved truth-based outcome is imported.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_goal_joint_region_v244 as witness

SOURCE = ROOT/'reports/joint_prediction_return_v247'
PREFIX = ROOT/'reports/query_allocation_lifecycle_v245'
OUTPUT = ROOT/'reports/endpoint_regions_v248'
LIVES, ARMS, VARIANTS = (0, 1, 2), ('ONE_WAY', 'JOINT_PREDICTION'), ('RETAINED', 'R_CENTERED')
PREFIX_TARGETS = tuple(range(3, 27))+tuple(range(30, 54))
TARGETS, LIFE_CAPS, HISTORY = tuple(range(54, 78)), (14144, 17072, 17168), (6768, 9216, 7952)
OPERATORS, ALPHABETS, S, D, R = witness.OPERATORS, witness.ALPHABETS, witness.S, witness.D, witness.R
load, rows, exact, empty = witness.load, witness.rows, witness.exact, witness.empty


def observe_record(row, pool, check):
    check('native_pool_before_own_paid_target', row['pooled_before'] == pool)
    member, spent = empty(), 0
    for batch in row['batches']:
        operator, increments = batch['operator'], batch['increments']
        start = sum(member[operator].values())
        check('own_paid_literal_batch_offsets_and_increments', set(increments) == set(ALPHABETS[operator])
              and all(isinstance(count, int) and count >= 0 for count in increments.values())
              and sum(increments.values()) == 16 and batch['draw_start'] == start
              and batch['draw_end'] == start+16 and batch['spent'] == spent+16)
        for category, count in increments.items():
            member[operator][category] += count
            pool[operator][category] += count
        spent += 16
    check('actual_native_pool_member_and_paid_target_after', row['pooled_after'] == pool
          and row['member'] == member and row['spent'] == spent)
    return member, spent


def common_prefix(life, sources, identities, check):
    pools, seen, paid = deepcopy(sources), [], 0
    for row in rows(PREFIX/f'records_life_{life:02d}.jsonl.gz'):
        if row['arm'] != 'ONE_WAY' or row['index'] >= 54:
            continue
        index, identity = row['index'], row['identity']
        context = 'a' if index < 30 else 'b'
        check('historical_one_way_public_identity_and_native_context', row['life'] == life
              and identity == identities[index] and row['case']['context'].lower() == context
              and row['history_paid_samples'] == paid)
        _, spent = observe_record(row, pools[context][identity], check)
        seen.append(index)
        paid += spent
    check('complete_shared_prefix_excludes_other_arms_and_old_returns',
          seen == list(PREFIX_TARGETS) and paid == HISTORY[life])
    return pools


def terminal_snapshots(life, sources, interface, check):
    identities = interface['identities']
    prefix = common_prefix(life, sources, identities, check)
    pools, fees, seen, selected = {arm: deepcopy(prefix) for arm in ARMS}, dict.fromkeys(ARMS, HISTORY[life]), [], []
    for position, row in enumerate(rows(SOURCE/f'records_life_{life:02d}.jsonl.gz')):
        index, arm, identity = row['index'], row['arm'], row['identity']
        target_position = position//len(ARMS)
        offset = (life+target_position) % len(ARMS)
        order = ARMS[offset:]+ARMS[:offset]
        check('actual_own_return_suffix_chronology_and_public_identity',
              index == TARGETS[target_position] and arm == order[position % len(ARMS)]
              and row['life'] == life and identity == identities[index]
              and row['case']['context'] == 'A' and row['case']['stage'] == 'A_RETURN')
        expected_seeds = {operator: 286000+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
        check('fresh_v247_suffix_seeds_without_redrawing_settled_stream', row['seeds'] == expected_seeds)
        pool = pools[arm]['a'][identity]
        member, spent = observe_record(row, pool, check)
        available = LIFE_CAPS[life]-4608-fees[arm]
        check('original_source_past_and_new_fees_and_total_budget', row['source_paid_samples'] == 4608
              and row['history_paid_samples'] == fees[arm]
              and row['current_paid_samples'] == row['new_paid_samples'] == spent
              and row['total_reference_paid_samples'] == 4608+fees[arm]+spent
              and row['life_budget_remaining_before'] == available
              and row['life_budget_remaining_after'] == available-spent
              and row['budget_exhausted'] == (available-spent < 16)
              and row['member_cap_exhausted'] == (spent == 384)
              and 0 <= spent <= min(384, available))
        constraints = witness.original_constraints(life, index, identity, sources, pool, member)
        terminal = row['terminal_plan']
        check('current_native_terminal_queries_execution_events_and_no_B_import',
              terminal['evidence_counts'] == pool and terminal['joint_constraints'] == constraints
              and terminal['return_transfer'] is None and pools[arm]['b'] == prefix['b'])
        goal = terminal['query_evidence']['queries']['goal']
        reference = next((item for item in goal['comparisons'] if item['other'] == 'DETOUR_RETRY'), None)
        if goal['policy'] == 'SHORT' and reference is not None and not reference['certified']:
            check('selected_goal_reference_is_failed_query_terminal', not row['query_certified'] and not terminal['query_ready'])
            selected.append(dict(record={field: deepcopy(row[field]) for field in
                ('life', 'index', 'arm', 'case', 'identity', 'spent', 'source_paid_samples', 'history_paid_samples',
                 'current_paid_samples', 'new_paid_samples', 'total_reference_paid_samples',
                 'life_budget_remaining_before', 'life_budget_remaining_after', 'budget_exhausted',
                 'member_cap_exhausted')}, reference=deepcopy(reference),
                evidence_counts=deepcopy(pool), joint_constraints=constraints, member=member))
        fees[arm] += spent
        seen.append((index, arm))
    check('all_paid_return_targets_once_per_arm', len(seen) == 48
          and {arm: [index for index, name in seen if name == arm] for arm in ARMS}
              == {arm: list(TARGETS) for arm in ARMS})
    check('actual_full_life_fees_remain_within_original_caps', all(4608+fee <= LIFE_CAPS[life] for fee in fees.values()))
    return selected, fees


def centered_candidate(original, counts, case):
    result = dict(kind='r_centered_fixed_d', parent_kind=original['kind'], leaf_index=original['leaf_index'],
        original_retry_probability=None, recovered_kernel=None, short_delivery_unclipped=None,
        repair_applied=False, kernel=None, gap=None, reason=None)
    recovered = original['recovered_kernel']
    if recovered is None or not witness.simplex(recovered):
        result['reason'] = original['reason']
        return result
    recovered = deepcopy(recovered)
    result['original_retry_probability'] = recovered[R]['DELIVERY']
    retry = F(counts[R]['DELIVERY'], sum(counts[R].values()))
    recovered[R] = dict(DELIVERY=retry, LOST=1-retry)
    result['recovered_kernel'] = recovered
    sc, dc = witness.costs(case)
    short = (sc-dc+4*recovered[D]['DELIVERY']
             +recovered[D]['RECOVERY']*(4*retry-F(case['retry_cost']))-witness.STRICT_GAP)/4
    result.update(short_delivery_unclipped=short, repair_applied=True)
    if not 0 <= short <= 1:
        result['reason'] = 'short_delivery_outside_simplex'
        return result
    kernel = deepcopy(recovered)
    kernel[S] = dict(DELIVERY=short, LOST=1-short)
    gap = witness.goal_gap(case, kernel)
    if not witness.simplex(kernel) or gap <= witness.REGRET:
        result.update(gap=gap, reason='repair_not_strict_bad_kernel')
        return result
    result.update(kernel=kernel, gap=gap)
    return result


def empirical_rows(counts):
    return {operator: {category: F(count, sum(row.values())) for category, count in row.items()}
            for operator, row in counts.items()}


def distances(candidate, empirical):
    return {operator: (sum(abs(F(candidate['kernel'][operator][category])-empirical[operator][category])
                           for category in ALPHABETS[operator])/2 if candidate['kernel'] is not None else None)
            for operator in OPERATORS}


def endpoint(snapshot):
    row = snapshot['record']
    fields = ('source_paid_samples', 'history_paid_samples', 'current_paid_samples',
              'total_reference_paid_samples', 'life_budget_remaining_before', 'life_budget_remaining_after')
    return dict(life=row['life'], index=row['index'], arm=row['arm'], identity=row['identity'],
        case=row['case'], profile_id=snapshot['reference']['profile_id'],
        evidence_counts=snapshot['evidence_counts'], joint_constraints=snapshot['joint_constraints'],
        member=snapshot['member'], retained_fees={field: row[field] for field in fields},
        spent=row['spent'], budget_exhausted=row['budget_exhausted'], member_cap_exhausted=row['member_cap_exhausted'])


def audit_variant(saved, candidate, counts, constraints, case, check):
    check('prespecified_candidate_recovery_R_choice_and_one_SHORT_repair', exact(saved['candidate']) == candidate)
    empirical = empirical_rows(counts)
    check('descriptive_empirical_rows_and_per_row_TV_only', exact(saved['empirical_rows']) == empirical
          and exact(saved['distances']) == distances(candidate, empirical))
    expected = dict(saved, candidate=candidate, empirical_rows=empirical, distances=distances(candidate, empirical))
    if candidate['kernel'] is None:
        check('unavailable_candidate_preserves_unknown_and_no_region_membership', saved['status'] == 'unknown'
            and all(saved[field] is None for field in ('canonical_inside', 'all_query_inside', 'all_execution_inside'))
            and saved['query_regions'] == {} and saved['execution_regions'] == [])
        expected.update(canonical_inside=None, all_query_inside=None, all_execution_inside=None,
                        query_regions={}, execution_regions=[], status='unknown')
        return expected
    kernel = candidate['kernel']
    check('exact_strict_bad_simplex_kernel', witness.simplex(kernel)
          and candidate['gap'] == witness.goal_gap(case, kernel) == witness.STRICT_GAP > witness.REGRET)
    query = witness.family_memberships(counts, kernel)
    check('all_eight_original_query_families_once', set(saved['query_regions']) == set(witness.FAMILIES))
    for family, (decision, ratio) in query.items():
        witness.audit_membership(saved['query_regions'][family], decision, ratio, check)
    execution = witness.execution_memberships(constraints, kernel)
    check('all_nine_original_full_categorical_execution_events_once', len(saved['execution_regions']) == len(execution) == 9)
    for retained, (event, ratio) in zip(saved['execution_regions'], execution):
        check('literal_original_execution_event_labels_counts_positions_thresholds',
            all(retained[field] == event[field] for field in ('operator', 'position', 'event', 'counts', 'threshold')))
        witness.audit_membership(retained['membership'], event['membership'], ratio, check)
    canonical = query['S_D_FULL_R'][0]['exact_inside']
    all_query = all(item[0]['exact_inside'] for item in query.values())
    all_execution = all(item[0]['membership']['exact_inside'] for item in execution)
    label = witness.status(candidate, canonical, all_query, all_execution)
    check('bad_point_exclusion_and_full_region_status_never_add_certificate',
          saved['canonical_inside'] is canonical and saved['all_query_inside'] is all_query
          and saved['all_execution_inside'] is all_execution and saved['status'] == label
          and 'query_certified' not in saved and 'certificate' not in saved)
    expected.update(canonical_inside=canonical, all_query_inside=all_query, all_execution_inside=all_execution,
        status=label, query_regions={family: value[0] for family, value in query.items()},
        execution_regions=[event for event, _ in execution])
    return expected


def audit_life(arguments):
    life, snapshots, saved_records, profiles = arguments
    begun, checks, failures, location, recomputed = perf_counter(), Counter(), [], {}, []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    for snapshot in snapshots:
        row, reference = snapshot['record'], snapshot['reference']
        location = dict(life=life, index=row['index'], arm=row['arm'], profile_id=reference['profile_id'])
        profile, case = profiles[reference['profile_id']], row['case']
        certificate = exact(profile['certificate'])
        counts, constraints = snapshot['evidence_counts'], snapshot['joint_constraints']
        uniform = {operator: dict.fromkeys(categories, F(1, len(categories))) for operator, categories in ALPHABETS.items()}
        projected, _ = witness.projection('S_D_FULL_R', counts, uniform)
        check('actual_retained_canonical_goal_profile_direction_costs_and_native_counts',
              (certificate['query'], certificate['chosen'], certificate['other'], certificate['family'])
                == ('goal', 'SHORT', 'DETOUR_RETRY', 'S_D_FULL_R')
              and certificate['threshold'] == 960 and certificate['regret_threshold'] == witness.REGRET
              and certificate['projected_counts'] == projected and certificate['embedded_counts'] == counts
              and certificate['certified'] is False and profile['case']['operating'] == case['operating']
              and F(profile['case']['retry_cost']) == F(case['retry_cost']))
        original = witness.reconstruct_candidate(certificate, case)
        candidates = dict(RETAINED=original, R_CENTERED=centered_candidate(original, counts, case))
        for variant in VARIANTS:
            location['variant'] = variant
            saved = saved_records[row['life'], row['index'], row['arm'], variant]
            check('original_frozen_endpoint_identity_member_counts_constraints_and_fees',
                  all(saved[field] == value for field, value in endpoint(snapshot).items()))
            recomputed.append(audit_variant(saved, candidates[variant], counts, constraints, case, check))
        print(f'audit life={life} index={row["index"]} arm={row["arm"]} variants=2', flush=True)
    return dict(life=life, checks=checks, failures=failures, records=recomputed,
                elapsed_seconds=perf_counter()-begun)


def group_summary(records):
    statuses, query_rejections, execution_rejections = Counter(), Counter(), Counter()
    for row in records:
        statuses[row['status']] += 1
        query_rejections.update(family for family, decision in row['query_regions'].items()
                                if not decision['exact_inside'])
        execution_rejections.update(f'{("source", "pool", "member")[event["position"]]}:{event["operator"]}'
            for event in row['execution_regions'] if not event['membership']['exact_inside'])
    return dict(records=len(records), status_counts={status: statuses[status] for status in witness.STATUSES},
        canonical_admitted=sum(row['canonical_inside'] is True for row in records),
        all_query_admitted=sum(row['all_query_inside'] is True for row in records),
        all_execution_admitted=sum(row['all_execution_inside'] is True for row in records),
        query_rejection_counts=dict(sorted(query_rejections.items())),
        execution_rejection_counts=dict(sorted(execution_rejections.items())))


def paired_statuses(records, arms):
    indexed = {(row['life'], row['index'], row['arm'], row['variant']): row for row in records}
    identities = sorted({(row['life'], row['index']) for row in records})
    summaries = []
    for group in (VARIANTS if arms else ARMS):
        transitions, changes = Counter(), []
        for life, index in identities:
            keys = ([(life, index, arm, group) for arm in ARMS] if arms
                    else [(life, index, group, variant) for variant in VARIANTS])
            before, after = (indexed[key]['status'] for key in keys)
            transitions[f'{before}->{after}'] += 1
            if before != after:
                changes.append(dict(life=life, index=index, before=before, after=after))
        summaries.append(dict(group=group, pairs=len(identities), status_transitions=dict(sorted(transitions.items())),
                              status_changes=changes))
    return summaries


def summarize(records, fees):
    unions = []
    for arm in ARMS:
        identities = sorted({(row['life'], row['index']) for row in records
                             if row['arm'] == arm and row['status'] == 'full_region_bad_witness'})
        unions.append(dict(arm=arm, distinct_full_bad_endpoints=len(identities),
            endpoint_references=[dict(life=life, index=index) for life, index in identities],
            same_evidence_query_certificate_ceiling=72-len(identities), required_a_return_queries=54))
    return dict(complete=True, records=len(records), endpoints=len(records)//2,
        arms=list(ARMS), variants=list(VARIANTS), comparison=dict(query='goal', chosen='SHORT', other='DETOUR_RETRY'),
        status_counts=group_summary(records)['status_counts'],
        arm_variant_summaries=[dict(arm=arm, variant=variant,
            **group_summary([row for row in records if row['arm'] == arm and row['variant'] == variant]))
            for arm in ARMS for variant in VARIANTS],
        life_summaries=[dict(life=life, arm=arm, variant=variant,
            **group_summary([row for row in records
                             if row['life'] == life and row['arm'] == arm and row['variant'] == variant]))
            for life in LIVES for arm in ARMS for variant in VARIANTS],
        paired_arm_statuses=paired_statuses(records, True), within_arm_variant_statuses=paired_statuses(records, False),
        retained_fee_ledger=fees, arm_full_bad_endpoint_unions=unions,
        certificate_ceiling_scope='same_terminal_evidence_original_query_and_execution_regions_and_times',
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)


def run():
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    protocol, summary, records, saved_endpoints = (load(OUTPUT/name)
        for name in ('run.json', 'summary.json', 'records.json', 'endpoints.json'))
    check('complete_and_independently_valid_V247_prerequisite',
          load(SOURCE/'run.json')['complete'] and load(SOURCE/'analysis.json')['valid'])
    check('frozen_all_endpoint_two_variant_diagnostic', protocol['complete']
        and protocol['baseline'] == SOURCE.relative_to(ROOT).as_posix() and protocol['arms'] == list(ARMS)
        and protocol['variants'] == list(VARIANTS)
        and protocol['comparison'] == dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')
        and protocol['endpoints'] == 48 and protocol['expected_classifications'] == 96
        and protocol['query_threshold'] == 960 and F(protocol['strict_gap']) == witness.STRICT_GAP
        and protocol['execution_thresholds'] == 'retained_source720_pool720_member8640'
        and protocol['candidate_rule'] == 'two_frozen_variants_of_one_retained_maximum_dual_leaf_or_bad_null_mle'
        and protocol['repair'] == 'one_algebraic_SHORT_DELIVERY_update_without_clipping_per_variant'
        and protocol['data_access'] == 'retained_records_profiles_public_interfaces_common_prefix_states_prefix_ledgers_only'
        and protocol['prerequisites'] == dict(v247_complete=True, v247_independent_valid=True)
        and protocol['phases'] == ['protocol_frozen', 'roster_frozen', 'all_endpoints_diagnosed', 'complete'])
    check('no_optimizer_observation_score_certificate_or_gate_added',
          all(protocol[field] == 0 for field in ('new_observations', 'new_optimizer_calls',
              'new_query_certificates', 'posthoc_scoring_calls'))
          and not protocol['scientific_gate_changed'] and protocol['diagnostic_only'])
    captured = load(OUTPUT/'source_manifest.json')
    required = ('scripts/run_endpoint_regions_v248.py', 'scripts/audit_endpoint_regions_v248.py',
        'src/acfqp/science/endpoint_region_v248.py', 'tests/test_endpoint_regions_v248_audit.py',
        'specs/ENDPOINT_REGIONS_V248.md')
    check('captured_frozen_protocol_core_runner_and_independent_audit', all(name in captured for name in required))
    for relative in captured:
        check('captured_source_matches_current_audited_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = witness.source_banks(load(PREFIX/'source_records.json'), check)
    interfaces = {row['life']: row for row in load(PREFIX/'interfaces.json')}
    selected, fees = [], []
    for life in LIVES:
        location = dict(life=life)
        snapshots, totals = terminal_snapshots(life, sources[life], interfaces[life], check)
        selected.extend(snapshots)
        for arm in ARMS:
            fees.append(dict(life=life, arm=arm, source_samples=4608, inherited_target_samples=HISTORY[life],
                new_return_samples=totals[arm]-HISTORY[life], total_samples=4608+totals[arm]))
    selected.sort(key=lambda snapshot: (snapshot['record']['life'], snapshot['record']['index'],
                                       ARMS.index(snapshot['record']['arm'])))
    reconstructed_endpoints = [endpoint(snapshot) for snapshot in selected]
    roster = [{field: row[field] for field in ('life', 'index', 'arm', 'profile_id')} for row in reconstructed_endpoints]
    check('complete_48_paired_failed_endpoint_roster_before_candidate_recovery', len(selected) == len(saved_endpoints) == 48
        and Counter((row['life'], row['arm']) for row in reconstructed_endpoints)
            == Counter({(life, arm): 8 for life in LIVES for arm in ARMS})
        and {(row['life'], row['index']) for row in reconstructed_endpoints if row['arm'] == ARMS[0]}
            == {(row['life'], row['index']) for row in reconstructed_endpoints if row['arm'] == ARMS[1]}
        and protocol['roster'] == roster and saved_endpoints == reconstructed_endpoints)
    check('whole_paid_lifecycle_cost_not_only_failed_targets', protocol['retained_fee_ledger'] == fees)
    expected_order = [(row['life'], row['index'], row['arm'], variant)
                      for row in reconstructed_endpoints for variant in VARIANTS]
    actual_order = [(row['life'], row['index'], row['arm'], row['variant']) for row in records]
    check('exact_96_classifications_once_in_frozen_order', actual_order == expected_order and len(records) == 96)
    saved_records = dict(zip(actual_order, records))
    arguments = []
    for life in LIVES:
        needed = {row['profile_id'] for row in roster if row['life'] == life}
        profiles = {row['profile_id']: row for row in rows(SOURCE/f'profiles_life_{life:02d}.jsonl.gz')
                    if row['profile_id'] in needed}
        check('original_profiles_resolved_before_variant_recovery', set(profiles) == needed)
        arguments.append((life, [item for item in selected if item['record']['life'] == life], saved_records, profiles))
    with ProcessPoolExecutor(max_workers=3) as executor:
        groups = list(executor.map(audit_life, arguments))
    recomputed = []
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
        recomputed.extend(group['records'])
    independently_summarized = summarize(recomputed, fees)
    check('independent_groups_paired_changes_distinct_endpoint_unions_and_ceilings',
          all(summary[field] == value for field, value in independently_summarized.items())
          and summary['elapsed_seconds'] >= 0)
    analysis = dict(valid=not failures, records=len(recomputed), endpoints=len(selected), checks=dict(checks),
        failures=failures, elapsed_seconds=perf_counter()-begun,
        life_elapsed_seconds={group['life']: group['elapsed_seconds'] for group in groups},
        **{field: independently_summarized[field] for field in ('status_counts', 'arm_variant_summaries',
            'life_summaries', 'paired_arm_statuses', 'within_arm_variant_statuses', 'arm_full_bad_endpoint_unions')},
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)
    (OUTPUT/'analysis.json').write_text(json.dumps(analysis, default=str, indent=2)+'\n')
    print(json.dumps({key: value for key, value in analysis.items() if key not in ('checks', 'failures')}, default=str), flush=True)
    return analysis


if __name__ == '__main__':
    if not run()['valid']:
        raise SystemExit(1)
