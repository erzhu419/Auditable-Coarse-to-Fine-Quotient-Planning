"""Independent V251 retained-information-axis candidate and region audit.

Only settled source/probe/target observations, public cases and retained proof
parameters are read. No route world, truth scores, producer, new observations,
optimizer or new certificate is used.
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
from scripts import audit_endpoint_regions_v248 as previous

witness = previous.witness
SOURCE = ROOT/'reports/query_shared_acquisition_v251'
OUTPUT = ROOT/'reports/information_axes_v252'
LIVES, ARMS = (0, 1, 2), ('UNIFORM_SHARED', 'QUERY_SHARED')
VARIANTS = ('RETAINED', 'R_CENTERED', 'SD_CENTERED')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
LIFE_CAPS, SOURCE_BASE, TARGET_BASE, PROBE_BASE = (14144, 17072, 17168), 295000, 296000, 297000
SOURCE_COST, SHARED_CAP, B_QUOTA = 4608, 4224, 1152
OPERATORS, ALPHABETS, S, D, R = witness.OPERATORS, witness.ALPHABETS, witness.S, witness.D, witness.R
load, rows, exact, empty = witness.load, witness.rows, witness.exact, witness.empty
FEE_FIELDS = ('source_paid_samples', 'history_paid_samples', 'ordinary_history_paid_samples',
    'actual_probe_paid_before', 'pending_probe_reserved', 'released_probe_samples',
    'probe_cap_samples', 'probe_quota_samples', 'future_B_source_reserved', 'current_paid_samples',
    'new_paid_samples', 'total_reference_paid_samples', 'life_budget_remaining_before',
    'life_budget_remaining_after')
VARIANT_PAIRS = (('RETAINED', 'R_CENTERED'), ('RETAINED', 'SD_CENTERED'), ('R_CENTERED', 'SD_CENTERED'))


centered_candidate = previous.centered_candidate
empirical_rows, distances, audit_variant = previous.empirical_rows, previous.distances, previous.audit_variant


def endpoint(snapshot):
    row = snapshot['record']
    fields = FEE_FIELDS
    return dict(life=row['life'], index=row['index'], arm=row['arm'], identity=row['identity'],
        case=row['case'], profile_id=snapshot['reference']['profile_id'],
        evidence_counts=snapshot['evidence_counts'], joint_constraints=snapshot['joint_constraints'],
        member=snapshot['member'], retained_fees={field: row[field] for field in fields},
        spent=row['spent'], budget_exhausted=row['budget_exhausted'], member_cap_exhausted=row['member_cap_exhausted'])


def sd_centered_candidate(counts, case):
    """Fix the paid empirical S/D rows and solve R delivery exactly once."""
    empirical = empirical_rows(counts)
    fixed = {operator: deepcopy(empirical[operator]) for operator in (S, D)}
    result = dict(kind='sd_centered_analytic_r', fixed_rows=fixed,
        retry_delivery_unclipped=None, solve_applied=False, kernel=None, gap=None, reason=None)
    recovery = fixed[D]['RECOVERY']
    if not recovery:
        result['reason'] = 'zero_empirical_detour_recovery'
        return result
    short_cost, detour_cost = witness.costs(case)
    retry = (witness.STRICT_GAP-short_cost+detour_cost+4*fixed[S]['DELIVERY']
             -4*fixed[D]['DELIVERY']+recovery*F(case['retry_cost']))/(4*recovery)
    result.update(retry_delivery_unclipped=retry, solve_applied=True)
    if not 0 <= retry <= 1:
        result['reason'] = 'retry_delivery_outside_simplex'
        return result
    kernel = deepcopy(fixed)
    kernel[R] = dict(DELIVERY=retry, LOST=1-retry)
    result.update(kernel=kernel, gap=witness.goal_gap(case, kernel))
    return result


def actual_counts(pools, switch, context, identity, interface):
    counts = deepcopy(pools[context][identity])
    if context == 'b':
        inherited = switch[interface['b_to_a'][identity]]
        for operator in OPERATORS:
            if operator != interface['changed_operator']:
                for category, count in inherited[operator].items():
                    counts[operator][category] += count
    return counts


def actual_constraints(life, index, identity, context, sources, pools, switch, member, interface):
    result = {}
    for operator in OPERATORS:
        event = f'l{life}/{context.upper()}/pool{identity}/{operator}'
        result[operator] = [
            dict(counts=deepcopy(sources[context][identity][operator]), threshold=720, event=event),
            dict(counts=deepcopy(pools[context][identity][operator]), threshold=720, event=event),
            dict(counts=deepcopy(member[operator]), threshold=8640,
                 event=f'l{life}/member{index}/{operator}')]
        if context == 'b' and operator != interface['changed_operator']:
            a_identity = interface['b_to_a'][identity]
            a_event = f'l{life}/A/pool{a_identity}/{operator}'
            result[operator].extend(dict(counts=deepcopy(bank[a_identity][operator]),
                threshold=720, event=a_event) for bank in (sources['a'], switch))
    return result


def replay_probe(saved, life, arm, context, pools, cursors, probe_paid, released, history, check):
    identity, operator, increments = saved['identity'], saved['operator'], saved['increments']
    key = context, identity, operator
    offset = cursors[key]
    pool, before = pools[context.lower()][identity][operator], deepcopy(saved['pool_before'])
    seed = PROBE_BASE+(life*6+(0 if context == 'A' else 3)+identity)*3+OPERATORS.index(operator)
    check('settled_probe_actual_native_row_seed_offset_and_before',
        saved['life'] == life and saved['arm'] == arm and saved['context'] == context
        and saved['source_index'] == (identity if context == 'A' else 27+identity)
        and saved['seed'] == seed and saved['draw_start'] == offset and saved['draw_end'] == offset+16
        and saved['probe_sequence'] == probe_paid//16+1 and before == pool
        and set(increments) == set(ALPHABETS[operator])
        and all(isinstance(count, int) and count >= 0 for count in increments.values())
        and sum(increments.values()) == 16
        and saved['trigger_index'] == (3 if context == 'A' else 30) and saved['timing'] == 'before_target')
    for category, count in increments.items():
        pool[category] += count
    check('settled_probe_only_native_pool_and_full_paid_pending_released_fee',
        saved['pool_after'] == pool and saved['probe_paid_before'] == probe_paid
        and saved['probe_paid_after'] == probe_paid+16
        and saved['pending_probe_reserved_before'] == SHARED_CAP-probe_paid-released
        and saved['pending_probe_reserved_after'] == SHARED_CAP-probe_paid-released-16
        and saved['released_samples_before'] == saved['released_samples_after'] == released
        and saved['ordinary_history_paid_samples'] == history
        and saved['source_paid_samples'] == (3456 if context == 'A' else SOURCE_COST))
    cursors[key] += 16
    return probe_paid+16


def terminal_snapshots(life, arm, sources, saved_cases, saved_interface, check):
    """Replay settled observations to each terminal time; no random generator."""
    identities, interface = saved_interface['identities'], saved_interface['metadata']
    pools, switch = dict(a=deepcopy(sources['a']), b=None), None
    tape = [json.loads(line) for line in (SOURCE/f'probes_life_{life:02d}_{arm}.jsonl').read_text().splitlines()]
    phase = load(SOURCE/f'a_phase_life_{life:02d}_{arm}.json')
    saved_ledger = next(row for row in load(SOURCE/'probe_ledgers.json') if row['life'] == life and row['arm'] == arm)
    cursor, probe_paid, released, history, a_paid = 0, 0, 0, 0, 0
    cursors, selected, seen = Counter(), [], []
    for row in rows(SOURCE/f'records_life_{life:02d}_{arm}.jsonl.gz'):
        index, identity, case = row['index'], row['identity'], row['case']
        context = case['context'].lower()
        if index == 30:
            switch, pools['b'] = deepcopy(pools['a']), deepcopy(sources['b'])
        if index in (3, 30):
            while cursor < len(tape) and tape[cursor]['context'].lower() == context:
                probe_paid = replay_probe(tape[cursor], life, arm, context.upper(), pools,
                                          cursors, probe_paid, released, history, check)
                cursor += 1
            if index == 3:
                a_paid, released = probe_paid, 3072-probe_paid
                check('actual_A_phase_release_retains_fixed_future_B_quota',
                    phase['a_paid_samples'] == a_paid and phase['released_delta'] == released
                    and phase['ledger_before_release'] == dict(cap_samples=SHARED_CAP,
                        paid_samples=a_paid, pending_samples=SHARED_CAP-a_paid, released_samples=0)
                    and phase['ledger_after_release'] == dict(cap_samples=SHARED_CAP,
                        paid_samples=a_paid, pending_samples=B_QUOTA, released_samples=released))
        check('complete_actual_target_chronology_public_case_and_native_identity',
            row['life'] == life and row['arm'] == arm and index == TARGETS[len(seen)]
            and identity == identities[index] and case == saved_cases[index])
        member, spent = previous.observe_record(row, pools[context][identity], check)
        pending = SHARED_CAP-probe_paid-released
        source_paid = 3456 if index < 30 else SOURCE_COST
        available = LIFE_CAPS[life]-SOURCE_COST-history-probe_paid-pending
        check('all_paid_ordinary_probe_source_future_and_released_fees_at_own_target_time',
            row['source_paid_samples'] == source_paid
            and row['history_paid_samples'] == row['ordinary_history_paid_samples'] == history
            and row['current_paid_samples'] == row['new_paid_samples'] == spent
            and row['actual_probe_paid_before'] == probe_paid and row['pending_probe_reserved'] == pending
            and row['released_probe_samples'] == released
            and row['probe_cap_samples'] == row['probe_quota_samples'] == SHARED_CAP
            and row['future_B_source_reserved'] == SOURCE_COST-source_paid
            and row['total_reference_paid_samples'] == source_paid+history+probe_paid+spent
            and row['life_budget_remaining_before'] == available
            and row['life_budget_remaining_after'] == available-spent
            and row['budget_exhausted'] == (available-spent < 16)
            and row['member_cap_exhausted'] == (spent == 384) and 0 <= spent <= min(384, available))
        seeds = {operator: TARGET_BASE+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
        check('settled_target_potential_stream_labels_without_redrawing_outcomes', row['seeds'] == seeds)
        counts = actual_counts(pools, switch, context, identity, interface)
        constraints = actual_constraints(life, index, identity, context, sources, pools, switch, member, interface)
        terminal = row['terminal_plan']
        check('actual_terminal_counts_source_pool_member_events_no_B_return_import',
            terminal['evidence_counts'] == counts and terminal['joint_constraints'] == constraints
            and terminal['return_transfer'] is None
            and row['terminal_plan'] == (row['batches'][-1]['plan'] if row['batches'] else row['initial_plan']))
        goal = terminal['query_evidence']['queries']['goal']
        reference = next((item for item in goal.get('comparisons', ())
                          if item['other'] == 'DETOUR_RETRY' and not item['certified']), None)
        if case['stage'] == 'A_RETURN' and goal['policy'] == 'SHORT' and reference is not None:
            check('selected_original_failed_goal_terminal', not terminal['query_ready'] and not row['query_certified'])
            fields = FEE_FIELDS+('life', 'index', 'arm', 'case', 'identity', 'spent',
                                 'budget_exhausted', 'member_cap_exhausted')
            selected.append(dict(record={field: deepcopy(row[field]) for field in fields}, reference=deepcopy(reference),
                evidence_counts=counts, joint_constraints=constraints, member=member))
        history += spent
        seen.append(index)
    check('complete_actual_native_lifecycle_and_full_final_probe_ledger', seen == list(TARGETS)
        and cursor == len(tape) and probe_paid+released == SHARED_CAP
        and saved_ledger == dict(life=life, arm=arm, cap_samples=SHARED_CAP,
            paid_samples=probe_paid, pending_reserved_samples=0, released_samples=released,
            by_context=dict(A=a_paid, B=B_QUOTA), probe_batches=len(tape))
        and SOURCE_COST+history+probe_paid <= LIFE_CAPS[life])
    fee = dict(life=life, arm=arm, source_samples=SOURCE_COST, ordinary_target_samples=history,
        a_probe_samples=a_paid, b_probe_samples=B_QUOTA, probe_samples=probe_paid,
        released_probe_samples=released, total_samples=SOURCE_COST+history+probe_paid)
    return selected, fee


def provenance(snapshot, certificate):
    row = snapshot['record']
    return dict(directory='query_shared_acquisition_v251',
        file=f'profiles_life_{row["life"]:02d}_{row["arm"]}.jsonl.gz',
        profile_id=snapshot['reference']['profile_id'], query='goal', chosen='SHORT',
        other='DETOUR_RETRY', family='S_D_FULL_R', witness_kind=certificate['witness_kind'])


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
        profile, case = profiles[row['arm']][reference['profile_id']], row['case']
        certificate = exact(profile['certificate'])
        counts, constraints = snapshot['evidence_counts'], snapshot['joint_constraints']
        uniform = {operator: dict.fromkeys(categories, F(1, len(categories))) for operator, categories in ALPHABETS.items()}
        projected, _ = witness.projection('S_D_FULL_R', counts, uniform)
        check('actual_retained_goal_profile_own_arm_direction_costs_and_native_counts',
              (certificate['query'], certificate['chosen'], certificate['other'], certificate['family'])
                == ('goal', 'SHORT', 'DETOUR_RETRY', 'S_D_FULL_R')
              and certificate['threshold'] == 960 and certificate['regret_threshold'] == witness.REGRET
              and certificate['projected_counts'] == projected and certificate['embedded_counts'] == counts
              and certificate['certified'] is False and profile['case']['operating'] == case['operating']
              and F(profile['case']['retry_cost']) == F(case['retry_cost']))
        retained = witness.reconstruct_candidate(certificate, case)
        candidates = dict(RETAINED=retained, R_CENTERED=centered_candidate(retained, counts, case),
                          SD_CENTERED=sd_centered_candidate(counts, case))
        for variant in VARIANTS:
            location['variant'] = variant
            saved = saved_records[row['life'], row['index'], row['arm'], variant]
            check('original_frozen_endpoint_own_time_counts_member_events_and_all_fees',
                all(saved[field] == value for field, value in endpoint(snapshot).items()))
            check('retained_profile_provenance_resolves_own_arm_file_and_actual_original_kind',
                  saved['profile_provenance'] == provenance(snapshot, certificate))
            recomputed.append(audit_variant(saved, candidates[variant], counts, constraints, case, check))
        print(f'audit life={life} index={row["index"]} arm={row["arm"]} variants=3', flush=True)
    return dict(life=life, checks=checks, failures=failures, records=recomputed,
                elapsed_seconds=perf_counter()-begun)


def paired_statuses(records, axis):
    indexed = {(row['life'], row['index'], row['arm'], row['variant']): row for row in records}
    identities = sorted({(row['life'], row['index']) for row in records})
    groups = ([(variant, ARMS) for variant in VARIANTS] if axis == 'arms'
              else [(arm, pair) for arm in ARMS for pair in VARIANT_PAIRS])
    summaries = []
    for group, pair in groups:
        transitions, changes = Counter(), []
        for life, index in identities:
            keys = ([(life, index, arm, group) for arm in pair] if axis == 'arms'
                    else [(life, index, group, variant) for variant in pair])
            before, after = (indexed[key]['status'] for key in keys)
            transitions[f'{before}->{after}'] += 1
            if before != after:
                changes.append(dict(life=life, index=index, before=before, after=after))
        summaries.append(dict(group=group, pair=list(pair), pairs=len(identities),
            status_transitions=dict(sorted(transitions.items())), status_changes=changes))
    return summaries


def summarize(records, fees):
    groups = previous.group_summary
    unions = []
    for arm in ARMS:
        identities = sorted({(row['life'], row['index']) for row in records
            if row['arm'] == arm and row['status'] == 'full_region_bad_witness'})
        unions.append(dict(arm=arm, distinct_full_bad_endpoints=len(identities),
            endpoint_references=[dict(life=life, index=index) for life, index in identities],
            same_evidence_query_certificate_ceiling=72-len(identities), required_a_return_queries=54))
    return dict(complete=True, records=len(records), endpoints=len(records)//len(VARIANTS),
        arms=list(ARMS), variants=list(VARIANTS), comparison=dict(query='goal', chosen='SHORT', other='DETOUR_RETRY'),
        status_counts=groups(records)['status_counts'],
        arm_variant_summaries=[dict(arm=arm, variant=variant,
            **groups([row for row in records if row['arm'] == arm and row['variant'] == variant]))
            for arm in ARMS for variant in VARIANTS],
        life_summaries=[dict(life=life, arm=arm, variant=variant,
            **groups([row for row in records if row['life'] == life and row['arm'] == arm and row['variant'] == variant]))
            for life in LIVES for arm in ARMS for variant in VARIANTS],
        paired_arm_statuses=paired_statuses(records, 'arms'),
        within_arm_variant_statuses=paired_statuses(records, 'variants'), retained_fee_ledger=fees,
        arm_full_bad_endpoint_unions=unions,
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
    check('complete_and_independently_valid_V251_prerequisite',
          load(SOURCE/'run.json')['complete'] and load(SOURCE/'analysis.json')['valid'])
    check('frozen_all_48_endpoint_three_variant_information_axes_diagnostic', protocol['complete']
        and protocol['baseline'] == SOURCE.relative_to(ROOT).as_posix() and protocol['arms'] == list(ARMS)
        and protocol['variants'] == list(VARIANTS)
        and protocol['comparison'] == dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')
        and protocol['endpoints'] == 48 and protocol['expected_classifications'] == 144
        and protocol['query_threshold'] == 960 and F(protocol['strict_gap']) == witness.STRICT_GAP
        and protocol['execution_thresholds'] == 'retained_source720_pool720_member8640'
        and protocol['candidate_rules'] == dict(
            RETAINED='unchanged_V248_retained_recovery_and_one_SHORT_repair',
            R_CENTERED='unchanged_V248_empirical_R_same_recovered_D_and_one_SHORT_repair',
            SD_CENTERED='native_empirical_full_S_D_rows_and_one_analytic_R_DELIVERY_solve_without_clipping')
        and protocol['data_access'] == 'V251_retained_source_records_source_evidence_probe_tapes_probe_ledgers_A_phase_target_records_profiles_public_cases_and_interfaces_only'
        and protocol['prerequisites'] == dict(v251_complete=True, v251_independent_valid=True)
        and protocol['phases'] == ['protocol_frozen', 'roster_frozen', 'all_endpoints_diagnosed', 'complete'])
    check('no_optimizer_observation_score_certificate_or_gate_added',
          all(protocol[field] == 0 for field in ('new_observations', 'new_optimizer_calls',
              'new_query_certificates', 'posthoc_scoring_calls'))
          and not protocol['scientific_gate_changed'] and protocol['diagnostic_only'])
    captured = load(OUTPUT/'source_manifest.json')
    required = ('scripts/run_information_axes_v252.py', 'scripts/audit_information_axes_v252.py',
        'src/acfqp/science/information_axes_v252.py', 'tests/test_information_axes_v252_core.py',
        'tests/test_information_axes_v252_runner.py', 'tests/test_information_axes_v252_audit.py',
        'specs/INFORMATION_AXES_V252.md')
    check('captured_frozen_protocol_core_runner_tests_and_independent_audit', all(name in captured for name in required))
    for relative in captured:
        check('captured_source_matches_current_audited_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    source_records = load(SOURCE/'source_records.json')
    sources = witness.source_banks(source_records, check)
    for row in source_records:
        check('settled_source_seed_labels_without_redrawing_outcomes', row['seed']
            == SOURCE_BASE+(row['life']*6+row['slot'])*3+OPERATORS.index(row['operator']))
    check('settled_source_banks_complete_logical_fees_and_context_admission',
        load(SOURCE/'source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    interfaces = {row['life']: row for row in load(SOURCE/'interfaces.json')}
    cases = {row['life']: row['cases'] for row in load(SOURCE/'cases.json')}
    selected, fees = [], []
    for life in LIVES:
        location = dict(life=life)
        for arm in ARMS:
            snapshots, fee = terminal_snapshots(life, arm, sources[life], cases[life], interfaces[life], check)
            selected.extend(snapshots)
            fees.append(fee)
    selected.sort(key=lambda snapshot: (snapshot['record']['life'], snapshot['record']['index'],
                                       ARMS.index(snapshot['record']['arm'])))
    reconstructed_endpoints = [endpoint(snapshot) for snapshot in selected]
    roster = [{field: row[field] for field in ('life', 'index', 'arm', 'identity', 'profile_id')}
              for row in reconstructed_endpoints]
    check('complete_48_paired_failed_endpoint_roster_before_any_variant_recovery',
        len(selected) == len(saved_endpoints) == 48
        and Counter((row['life'], row['arm']) for row in reconstructed_endpoints)
            == Counter({(life, arm): 8 for life in LIVES for arm in ARMS})
        and {(row['life'], row['index']) for row in reconstructed_endpoints if row['arm'] == ARMS[0]}
            == {(row['life'], row['index']) for row in reconstructed_endpoints if row['arm'] == ARMS[1]}
        and protocol['roster'] == roster and saved_endpoints == reconstructed_endpoints)
    check('whole_paid_lifecycle_source_ordinary_shared_and_released_ledger', protocol['retained_fee_ledger'] == fees)
    expected_order = [(life, row['index'], arm, variant) for life in LIVES for arm in ARMS
                      for row in reconstructed_endpoints if row['life'] == life and row['arm'] == arm
                      for variant in VARIANTS]
    actual_order = [(row['life'], row['index'], row['arm'], row['variant']) for row in records]
    check('exact_144_original_profile_classifications_once_in_retained_order',
          actual_order == expected_order and len(records) == 144)
    saved_records = dict(zip(actual_order, records))
    arguments = []
    for life in LIVES:
        own_profiles = {}
        for arm in ARMS:
            needed = {row['profile_id'] for row in roster if row['life'] == life and row['arm'] == arm}
            own_profiles[arm] = {row['profile_id']: row
                for row in rows(SOURCE/f'profiles_life_{life:02d}_{arm}.jsonl.gz') if row['profile_id'] in needed}
            check('original_profiles_resolved_in_distinct_arm_file_before_recovery', set(own_profiles[arm]) == needed)
        arguments.append((life, [item for item in selected if item['record']['life'] == life], saved_records, own_profiles))
    with ProcessPoolExecutor(max_workers=3) as executor:
        groups = list(executor.map(audit_life, arguments))
    recomputed = []
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
        recomputed.extend(group['records'])
    independently_summarized = summarize(recomputed, fees)
    check('independent_three_variant_groups_all_pairs_distinct_unions_and_ceilings',
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
