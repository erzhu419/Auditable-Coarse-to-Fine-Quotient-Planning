"""Independent own-time paid evidence and fixed return-view audit.

Settled V251 increments are replayed without redrawing or truth scoring. Original
ONE_WAY plans are compared to their audited records; only new TWO_WAY profiles
and plans receive the established independent proof arithmetic.
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
from scripts import audit_information_axes_v252 as timeline
from scripts import audit_bidirectional_lifecycle_v243 as prior

SOURCE = ROOT/'reports/query_shared_acquisition_v251'
OUTPUT = ROOT/'reports/paid_return_views_v253'
LIVES, ARMS, VIEWS = (0, 1, 2), ('UNIFORM_SHARED', 'QUERY_SHARED'), ('ONE_WAY', 'TWO_WAY')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
RETURN_TARGETS = tuple(range(54, 78))
LIFE_CAPS, SOURCE_BASE, TARGET_BASE = (14144, 17072, 17168), 295000, 296000
SOURCE_COST, SHARED_CAP, B_QUOTA = 4608, 4224, 1152
OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
load, rows, empty = timeline.load, timeline.rows, prior.empty
FEE_FIELDS = ('source_paid_samples', 'history_paid_samples', 'ordinary_history_paid_samples',
    'actual_probe_paid_before', 'pending_probe_reserved', 'released_probe_samples',
    'probe_cap_samples', 'probe_quota_samples', 'future_B_source_reserved', 'current_paid_samples',
    'new_paid_samples', 'total_reference_paid_samples', 'life_budget_remaining_before',
    'life_budget_remaining_after')
DELTA_SCOPE = 'separate_fixed_ONE_WAY_and_TWO_WAY_events_per_life_arm_not_OR_or_selected_union'
QUERIES = ('reward', 'goal', 'risk')
METRICS = ('query_ready', 'execution_certified', 'execution_resolved', 'goal_impossible', 'joint_ready')
RECORD_FIELDS = ('life', 'arm', 'index', 'identity', 'case', 'baseline_provenance',
                 'retained_fees', 'spent', 'retained_executed_mix', 'one_way_plan')


def terminal_snapshots(life, arm, sources, saved_cases, saved_interface, check):
    """Read every own native update, retaining all 24 return terminal times."""
    identities, interface = saved_interface['identities'], saved_interface['metadata']
    pools, switch = dict(a=deepcopy(sources['a']), b=None), None
    tape = [json.loads(line) for line in (SOURCE/f'probes_life_{life:02d}_{arm}.jsonl').read_text().splitlines()]
    phase = load(SOURCE/f'a_phase_life_{life:02d}_{arm}.json')
    ledger = next(row for row in load(SOURCE/'probe_ledgers.json') if row['life'] == life and row['arm'] == arm)
    cursor, probe_paid, released, history, a_paid = 0, 0, 0, 0, 0
    cursors, snapshots, seen = Counter(), [], []
    for row in rows(SOURCE/f'records_life_{life:02d}_{arm}.jsonl.gz'):
        index, identity, case = row['index'], row['identity'], row['case']
        context = case['context'].lower()
        if index == 30:
            switch, pools['b'] = deepcopy(pools['a']), deepcopy(sources['b'])
        if index in (3, 30):
            while cursor < len(tape) and tape[cursor]['context'].lower() == context:
                probe_paid = timeline.replay_probe(tape[cursor], life, arm, context.upper(), pools,
                                                   cursors, probe_paid, released, history, check)
                cursor += 1
            if index == 3:
                a_paid, released = probe_paid, 3072-probe_paid
                check('settled_A_release_keeps_future_B_quota', phase['a_paid_samples'] == a_paid
                    and phase['released_delta'] == released
                    and phase['ledger_before_release'] == dict(cap_samples=SHARED_CAP,
                        paid_samples=a_paid, pending_samples=SHARED_CAP-a_paid, released_samples=0)
                    and phase['ledger_after_release'] == dict(cap_samples=SHARED_CAP,
                        paid_samples=a_paid, pending_samples=B_QUOTA, released_samples=released))
        check('all_72_settled_targets_public_case_identity_and_native_chronology',
            row['life'] == life and row['arm'] == arm and index == TARGETS[len(seen)]
            and identity == identities[index] and case == saved_cases[index])
        member, spent = timeline.previous.observe_record(row, pools[context][identity], check)
        pending = SHARED_CAP-probe_paid-released
        source_paid = 3456 if index < 30 else SOURCE_COST
        available = LIFE_CAPS[life]-SOURCE_COST-history-probe_paid-pending
        expected_fees = dict(source_paid_samples=source_paid, history_paid_samples=history,
            ordinary_history_paid_samples=history, actual_probe_paid_before=probe_paid,
            pending_probe_reserved=pending, released_probe_samples=released,
            probe_cap_samples=SHARED_CAP, probe_quota_samples=SHARED_CAP,
            future_B_source_reserved=SOURCE_COST-source_paid, current_paid_samples=spent,
            new_paid_samples=spent, total_reference_paid_samples=source_paid+history+probe_paid+spent,
            life_budget_remaining_before=available, life_budget_remaining_after=available-spent)
        check('own_time_all_source_ordinary_probe_pending_released_and_member_fees',
            {field: row[field] for field in FEE_FIELDS} == expected_fees
            and row['budget_exhausted'] == (available-spent < 16)
            and row['member_cap_exhausted'] == (spent == 384)
            and 0 <= spent <= min(384, available))
        seeds = {operator: TARGET_BASE+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
        check('settled_target_seed_labels_without_redrawing_outcomes', row['seeds'] == seeds)
        counts = timeline.actual_counts(pools, switch, context, identity, interface)
        constraints = timeline.actual_constraints(life, index, identity, context, sources,
                                                  pools, switch, member, interface)
        terminal = row['terminal_plan']
        check('original_ONE_counts_and_execution_events_exact_at_own_terminal_time',
            terminal['evidence_counts'] == counts and terminal['joint_constraints'] == constraints
            and terminal['return_transfer'] is None
            and terminal == (row['batches'][-1]['plan'] if row['batches'] else row['initial_plan']))
        if case['stage'] == 'A_RETURN':
            b_identity = interface['b_to_a'].index(identity)
            snapshots.append(dict(life=life, arm=arm, index=index, identity=identity,
                case=deepcopy(case), member=member, a_source=deepcopy(sources['a'][identity]),
                a_pool=deepcopy(pools['a'][identity]), b_source=deepcopy(sources['b'][b_identity]),
                b_pool=deepcopy(pools['b'][b_identity]), mapped_b_identity=b_identity,
                interface={field: deepcopy(interface[field]) for field in ('changed_operator', 'b_to_a')},
                retained_executed_mix=deepcopy(row['executed_mix']), one_way_plan=deepcopy(terminal),
                baseline_provenance=dict(directory='query_shared_acquisition_v251',
                    record_file=f'records_life_{life:02d}_{arm}.jsonl.gz',
                    profile_file=f'profiles_life_{life:02d}_{arm}.jsonl.gz'),
                retained_fees=expected_fees, spent=spent))
        history += spent
        seen.append(index)
    check('complete_settled_lifecycle_and_final_paid_probe_ledger', seen == list(TARGETS)
        and cursor == len(tape) and probe_paid+released == SHARED_CAP
        and ledger == dict(life=life, arm=arm, cap_samples=SHARED_CAP, paid_samples=probe_paid,
            pending_reserved_samples=0, released_samples=released,
            by_context=dict(A=a_paid, B=B_QUOTA), probe_batches=len(tape))
        and SOURCE_COST+history+probe_paid <= LIFE_CAPS[life])
    check('all_return_endpoints_without_selection', [row['index'] for row in snapshots] == list(RETURN_TARGETS))
    fee = dict(life=life, arm=arm, source_samples=SOURCE_COST, ordinary_target_samples=history,
        a_probe_samples=a_paid, b_probe_samples=B_QUOTA, probe_samples=probe_paid,
        released_probe_samples=released, total_samples=SOURCE_COST+history+probe_paid)
    return snapshots, fee


def two_way_evidence(snapshot):
    """Add native B pool once, retaining separate original execution events."""
    life, index, identity = (snapshot[field] for field in ('life', 'index', 'identity'))
    interface = snapshot['interface']
    b_identity = interface['b_to_a'].index(identity)
    eligible = [operator for operator in OPERATORS if operator != interface['changed_operator']]
    counts, constraints = deepcopy(snapshot['a_pool']), {}
    for operator in OPERATORS:
        a_event = f'l{life}/A/pool{identity}/{operator}'
        constraints[operator] = [dict(counts=deepcopy(snapshot[field][operator]), threshold=720, event=a_event)
                                 for field in ('a_source', 'a_pool')]
        constraints[operator].append(dict(counts=deepcopy(snapshot['member'][operator]), threshold=8640,
                                         event=f'l{life}/member{index}/{operator}'))
        if operator in eligible:
            for category, count in snapshot['b_pool'][operator].items():
                counts[operator][category] += count
            b_event = f'l{life}/B/pool{b_identity}/{operator}'
            constraints[operator].extend(dict(counts=deepcopy(snapshot[field][operator]), threshold=720, event=b_event)
                                          for field in ('b_source', 'b_pool'))
    transferred = {operator: deepcopy(snapshot['b_pool'][operator]) for operator in eligible}
    transfer = dict(a_identity=identity, mapped_b_identity=b_identity, operators=eligible,
        transferred_counts=transferred, total_samples=sum(sum(row.values()) for row in transferred.values()))
    return counts, constraints, transfer


def original_record(saved, snapshot, check):
    check('original_ONE_plan_profile_namespace_actual_execution_and_fees_unchanged',
          all(saved[field] == snapshot[field] for field in RECORD_FIELDS))
    check('actual_new_planning_CPU_and_retention_wall_nonnegative',
          saved['model_seconds'] >= 0 and saved['output_seconds'] >= 0)


def audit_life_arm(arguments):
    life, arm, snapshots = arguments
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    saved_records = list(rows(OUTPUT/f'records_life_{life:02d}_{arm}.jsonl.gz'))
    profiles = list(rows(OUTPUT/f'profiles_life_{life:02d}_{arm}.jsonl.gz'))
    check('private_TWOWAY_profile_ids_complete_once',
          [profile['profile_id'] for profile in profiles] == list(range(len(profiles))))
    check('private_24_plans_in_original_return_order',
          [(row['life'], row['arm'], row['index']) for row in saved_records]
            == [(life, arm, index) for index in RETURN_TARGETS])
    decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, arm=arm, profile_id=profile['profile_id'])
        decisions[profile['profile_id']] = prior.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    projections, used, work, convex_keys = {}, set(), Counter(), set()
    for saved, snapshot in zip(saved_records, snapshots):
        location = {field: snapshot[field] for field in ('life', 'arm', 'index', 'identity')}
        original_record(saved, snapshot, check)
        counts, constraints, transfer = two_way_evidence(snapshot)
        plan = saved['two_way_plan']
        check('inverse_mapping_native_B_unchanged_rows_and_source_not_double_added',
              snapshot['mapped_b_identity'] == transfer['mapped_b_identity']
              and plan['return_transfer'] == transfer)
        prior.audit_plan(plan, snapshot['case'], counts, constraints, profiles, decisions,
                         projections, used, check)
        work['reuse_rebuild_joint_plans'] += 1
        work['online_query_comparison_calls'] += 6
        for query in ('goal', 'risk'):
            for reference in plan['query_evidence']['queries'][query]['comparisons']:
                cert = profiles[reference['profile_id']]['certificate']
                if cert.get('engine') == 'convex_tangent':
                    work['online_convex_certificate_calls'] += 1
                    convex_keys.add((cert['family'], query, cert['chosen'], cert['other'],
                                    F(cert['relevant_cost']), prior.freeze(cert['projected_counts'])))
        print(f'audit life={life} arm={arm} index={snapshot["index"]} fixed_views=2', flush=True)
    work['online_convex_proposal_calls'] = len(convex_keys)
    work['online_convex_certificate_cache_hits'] = work['online_convex_certificate_calls']-len(convex_keys)
    artifact = load(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json')
    check('all_new_private_profiles_used_only_by_TWOWAY_and_retained_once',
          used == set(range(len(profiles))) and artifact['profiles'] == len(profiles))
    check('worker_artifact_actual_plan_CPU_output_wall_and_identity', artifact['life'] == life and artifact['arm'] == arm
        and artifact['model_seconds'] == sum(row['model_seconds'] for row in saved_records)
        and artifact['output_seconds'] >= sum(row['output_seconds'] for row in saved_records)
        and artifact['worker_wall_seconds'] >= 0)
    for field, value in work.items():
        check('per_private_worker_actual_plan_and_convex_cache_work', artifact['work'].get(field, 0) == value)
    check('no_new_environment_observation_work', all(artifact['work'].get(field, 0) == 0
          for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws')))
    for name, capacity in (('execution', 4096), ('query', 256)):
        stats = artifact['normalizer_cache_statistics'][name]
        check('private_worker_normalizer_cache_statistics', stats['maxsize'] == capacity
              and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    return dict(life=life, arm=arm, records=saved_records, artifact=artifact, checks=checks, failures=failures,
        profiles=len(profiles), leaves=leaves, projections=checks['terminal_projected_detour_box'],
        elapsed_seconds=perf_counter()-begun)


def plan_state(plan):
    certified = F(plan['utility_lower']) >= 2
    impossible, query_ready = plan['goal_impossible'], plan['query_ready']
    resolved = certified or impossible
    return dict(query_ready=query_ready, execution_certified=certified, execution_resolved=resolved,
        goal_impossible=impossible, joint_ready=resolved and query_ready,
        certified_by_query={query: plan['query_evidence']['queries'][query]['certified'] for query in QUERIES},
        query_choices={query: plan['queries'][query]['policy'] for query in QUERIES},
        query_blockers=deepcopy(plan['query_blockers']))


def view_summary(records, view):
    states = [plan_state(row['one_way_plan' if view == 'ONE_WAY' else 'two_way_plan']) for row in records]
    return dict(targets=len(states), **{field: sum(state[field] for state in states) for field in METRICS},
        certified_by_query={query: sum(state['certified_by_query'][query] for state in states) for query in QUERIES},
        query_choice_counts={query: dict(sorted(Counter(state['query_choices'][query] for state in states).items()))
                            for query in QUERIES},
        query_blocker_counts={query: dict(sorted(Counter(other for state in states
            for other in state['query_blockers'][query]).items())) for query in QUERIES})


def paired_summary(records):
    pairs = [(row, plan_state(row['one_way_plan']), plan_state(row['two_way_plan'])) for row in records]
    result = {}
    for field in METRICS:
        gains = sum(new[field] and not old[field] for _, old, new in pairs)
        losses = sum(old[field] and not new[field] for _, old, new in pairs)
        changes = [dict(life=row['life'], index=row['index'], identity=row['identity'],
                        before=old[field], after=new[field]) for row, old, new in pairs if old[field] != new[field]]
        result[field] = dict(gains=gains, losses=losses, unchanged=len(records)-gains-losses, changes=changes)
    for category in ('certified_by_query', 'query_choices', 'query_blockers'):
        result[category] = {}
        for query in QUERIES:
            changes = [dict(life=row['life'], index=row['index'], identity=row['identity'],
                before=old[category][query], after=new[category][query]) for row, old, new in pairs
                if old[category][query] != new[category][query]]
            result[category][query] = dict(changed=len(changes), unchanged=len(records)-len(changes), changes=changes)
            if category == 'certified_by_query':
                result[category][query].update(gains=sum(row['after'] and not row['before'] for row in changes),
                    losses=sum(row['before'] and not row['after'] for row in changes))
    return result


def summarize(records, fees):
    def group(selected):
        return dict(views={view: view_summary(selected, view) for view in VIEWS}, paired=paired_summary(selected))
    return dict(complete=True, records=len(records), snapshots=len(records), views=list(VIEWS),
        arm_summaries=[dict(arm=arm, **group([row for row in records if row['arm'] == arm])) for arm in ARMS],
        life_summaries=[dict(life=life, arm=arm,
            **group([row for row in records if row['life'] == life and row['arm'] == arm])) for life in LIVES for arm in ARMS],
        retained_fee_ledger=fees, new_observations=0, new_plans=len(records), one_way_replans=0,
        new_truth_scoring_calls=0, adaptive_policy_changed=False, scientific_gate_changed=False,
        diagnostic_only=True, view_delta_scope=DELTA_SCOPE)


def run():
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    protocol, summary, saved_snapshots = (load(OUTPUT/name) for name in ('run.json', 'summary.json', 'snapshots.json'))
    jobs = [dict(life=life, arm=arm) for life in LIVES for arm in ARMS]
    check('complete_and_independently_valid_V251_settled_prerequisite',
          load(SOURCE/'run.json')['complete'] and load(SOURCE/'analysis.json')['valid']
          and protocol['prerequisites'] == dict(v251_complete=True, v251_independent_valid=True))
    check('frozen_144_all_return_endpoints_and_separate_fixed_view_protocol', protocol['complete']
        and protocol['baseline'] == SOURCE.relative_to(ROOT).as_posix()
        and protocol['arms'] == list(ARMS) and protocol['views'] == list(VIEWS) and protocol['snapshots'] == 144
        and protocol['one_way_rule'] == 'original_audited_terminal_plan_and_original_private_profile_references_unchanged'
        and protocol['two_way_rule'] == 'inverse_B_to_A_compatible_native_B_unchanged_rows_once_at_own_original_terminal_time'
        and protocol['query_events_per_life_arm_view'] == 48 and protocol['query_threshold'] == 960
        and protocol['execution_source_pool_threshold'] == 720 and protocol['execution_member_threshold'] == 8640
        and protocol['query_delta_per_life_arm_view'] == protocol['execution_delta_per_life_arm_view'] == '1/20'
        and protocol['combined_delta_per_fixed_view_upper'] == '1/10' and protocol['view_delta_scope'] == DELTA_SCOPE
        and protocol['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE
        and protocol['worker_jobs'] == jobs and protocol['max_workers'] == 6
        and protocol['profile_namespaces'] == dict(ONE_WAY='original_V251_private_life_arm_file',
                                                  TWO_WAY='new_V253_private_life_arm_file')
        and protocol['data_access'] == 'V251_settled_source_records_source_evidence_probe_tapes_probe_ledgers_A_phase_target_records_public_cases_and_interfaces_only'
        and protocol['phases'] == ['protocol_frozen', 'all_snapshots_frozen', 'all_fixed_views_planned', 'complete'])
    check('no_new_samples_ONE_replans_scoring_policy_or_scientific_gate_change',
          protocol['expected_new_plans'] == 144
          and all(protocol[field] == 0 for field in ('new_observations', 'one_way_replans', 'new_truth_scoring_calls'))
          and not protocol['adaptive_policy_changed'] and not protocol['scientific_gate_changed'] and protocol['diagnostic_only'])
    captured = load(OUTPUT/'source_manifest.json')
    required = ('src/acfqp/science/paid_return_views_v253.py', 'scripts/run_paid_return_views_v253.py',
        'scripts/audit_paid_return_views_v253.py', 'tests/test_paid_return_views_v253_core.py',
        'tests/test_paid_return_views_v253_runner.py', 'tests/test_paid_return_views_v253_audit.py',
        'specs/PAID_RETURN_VIEWS_V253.md')
    check('captured_frozen_core_protocol_producer_tests_and_independent_audit', all(name in captured for name in required))
    for relative in captured:
        check('captured_source_bytes_equal_audited_source',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    source_records = load(SOURCE/'source_records.json')
    sources = timeline.witness.source_banks(source_records, check)
    for row in source_records:
        check('settled_source_seed_labels_without_new_random_draws', row['seed']
              == SOURCE_BASE+(row['life']*6+row['slot'])*3+OPERATORS.index(row['operator']))
    check('settled_actual_source_banks_reused_without_new_fees_or_draws',
          load(SOURCE/'source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    cases = {row['life']: row['cases'] for row in load(SOURCE/'cases.json')}
    interfaces = {row['life']: row for row in load(SOURCE/'interfaces.json')}
    snapshots, fees, arguments = [], [], []
    for job in jobs:
        life, arm = job['life'], job['arm']
        location = job.copy()
        selected, fee = terminal_snapshots(life, arm, sources[life], cases[life], interfaces[life], check)
        snapshots.extend(selected)
        fees.append(fee)
        arguments.append((life, arm, selected))
    roster = [{field: row[field] for field in ('life', 'arm', 'index', 'identity')} for row in snapshots]
    check('all_144_paired_own_time_native_snapshots_frozen_before_planning',
          len(snapshots) == len(saved_snapshots) == 144 and saved_snapshots == snapshots
          and protocol['roster'] == roster and protocol['retained_fee_ledger'] == fees)
    with ProcessPoolExecutor(max_workers=6) as executor:
        groups = list(executor.map(audit_life_arm, arguments))
    records = []
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
        records.extend(group['records'])
    independently_summarized = summarize(records, fees)
    check('independent_fixed_view_gains_losses_choices_blockers_and_actual_fees',
          all(summary[field] == value for field, value in independently_summarized.items()))
    artifacts = [group['artifact'] for group in groups]
    expected_computation = dict(model_seconds=sum(item['model_seconds'] for item in artifacts),
        model_seconds_scope='summed_process_CPU_144_fixed_TWOWAY_evidence_assembly_and_plan_from_evidence_calls',
        output_seconds=sum(item['output_seconds'] for item in artifacts),
        output_seconds_scope='summed_worker_proof_retention_and_record_write_wall_calls',
        worker_wall_seconds=[dict(life=item['life'], arm=item['arm'], seconds=item['worker_wall_seconds']) for item in artifacts],
        normalizer_cache_statistics=[dict(life=item['life'], arm=item['arm'], statistics=item['normalizer_cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'], arm=item['arm'], counts=item['work']) for item in artifacts],
        profiles=[dict(life=item['life'], arm=item['arm'], profiles=item['profiles']) for item in artifacts])
    check('summed_actual_private_worker_model_and_retention_computation',
          all(summary[field] == value for field, value in expected_computation.items()) and summary['elapsed_seconds'] >= 0)
    analysis = dict(valid=not failures, records=len(records), snapshots=len(snapshots), new_plans=len(records),
        independently_checked_profiles=sum(group['profiles'] for group in groups),
        independently_checked_global_leaves=sum(group['leaves'] for group in groups),
        independently_checked_execution_projections=sum(group['projections'] for group in groups),
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun,
        worker_elapsed_seconds=[dict(life=group['life'], arm=group['arm'], seconds=group['elapsed_seconds']) for group in groups],
        arm_summaries=independently_summarized['arm_summaries'], life_summaries=independently_summarized['life_summaries'],
        retained_fee_ledger=fees, new_observations=0, one_way_replans=0, new_truth_scoring_calls=0,
        adaptive_policy_changed=False, scientific_gate_changed=False, diagnostic_only=True, view_delta_scope=DELTA_SCOPE)
    (OUTPUT/'analysis.json').write_text(json.dumps(analysis, default=str, indent=2)+'\n')
    print(json.dumps({key: value for key, value in analysis.items() if key not in ('checks', 'failures')}, default=str), flush=True)
    return analysis


if __name__ == '__main__':
    if not run()['valid']:
        raise SystemExit(1)
