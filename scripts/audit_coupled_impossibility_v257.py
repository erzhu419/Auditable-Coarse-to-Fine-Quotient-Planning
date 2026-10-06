"""Independent same-event coupled impossibility audit; no V257 core import."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_trajectory_lifecycle_v256 as baseline

execution, paid = baseline.execution, baseline.paid
joint, math = execution.joint, execution.math
OPERATORS, POLICIES = joint.OPERATORS, joint.POLICIES
S, D, R = OPERATORS
LIVES, ARMS, TARGETS = baseline.LIVES, baseline.ARMS, baseline.TARGETS
PREDECESSOR = ROOT/'reports/trajectory_lifecycle_v256'
OUTPUT = ROOT/'reports/coupled_impossibility_v257'
RISK_LIMIT, GOAL_THRESHOLD = F(1, 20), F(2)
load, exact, rows = baseline.load, baseline.exact, baseline.rows


def rectangle_dual(rectangles):
    intersections = {F(0)}
    for first, second in combinations(POLICIES, 2):
        a, b = rectangles[first], rectangles[second]
        slope = a['risk_min']-b['risk_min']
        if slope:
            crossing = (a['goal_max']-b['goal_max'])/slope
            if crossing >= 0:
                intersections.add(crossing)
    candidates = [dict(lambda_value=lam, objective=lam*RISK_LIMIT+max(
        row['goal_max']-lam*row['risk_min'] for row in rectangles.values()))
        for lam in sorted(intersections)]
    winner = min(candidates, key=lambda row: (row['objective'], row['lambda_value']))
    lam = winner['lambda_value']
    maximum = max(row['goal_max']-lam*row['risk_min'] for row in rectangles.values())
    return dict(lambda_value=lam, value=winner['objective'], candidates=candidates,
        maximizing_policies=[policy for policy in POLICIES
            if rectangles[policy]['goal_max']-lam*rectangles[policy]['risk_min'] == maximum])


def box_proof(plan, case):
    vertices = math.box_vertices(plan['envelopes'])
    points = []
    for index, kernel in enumerate(vertices):
        vectors = joint.vectors(case, kernel)
        for policy in POLICIES:
            reward, risk, delivery = vectors[policy]
            points.append(dict(vertex_index=index, policy=policy, risk=risk, goal=reward+4*delivery))
    rectangles = {policy: dict(risk_min=min(row['risk'] for row in points if row['policy'] == policy),
        goal_max=max(row['goal'] for row in points if row['policy'] == policy)) for policy in POLICIES}
    dual = rectangle_dual(rectangles)
    lam = dual['lambda_value']
    maximum = max(row['goal']-lam*row['risk'] for row in points)
    paired = dict(upper=lam*RISK_LIMIT+maximum, vertices=vertices, points=points,
        maximizing_points=[dict(vertex_index=row['vertex_index'], policy=row['policy'])
            for row in points if row['goal']-lam*row['risk'] == maximum])
    return rectangles, dual, paired


def branch_coefficients(case, lam, retry_upper):
    return {
        'DETOUR_RETURN': dict(DELIVERY=F(4), LOST=-lam, RECOVERY=F(0)),
        'DETOUR_RETRY': dict(DELIVERY=F(4), LOST=-lam,
            RECOVERY=(4+lam)*retry_upper-F(case['retry_cost'])-lam)}


def audit_bound(saved, original, case, check):
    bound, plan = exact(saved), exact(original)
    rectangles, dual, paired = box_proof(plan, case)
    old, lam = F(plan['goal_upper']), dual['lambda_value']
    check('exact_original_four_rectangle_LP_dual_and_smallest_lambda_tie',
          bound['rectangles'] == rectangles and bound['old_dual'] == dual and dual['value'] == old
          and bound['old_goal_upper'] == old)
    check('same_lambda_complete_vertex_policy_paired_box_and_dominance',
          bound['paired_box'] == paired and paired['upper'] <= old)
    s, q = (plan['envelopes'][op]['bounds']['DELIVERY'][1] for op in (S, R))
    check('original_settled_binary_CS_upper_and_retry_monotonicity',
          bound['binary_upper'] == {S: s, R: q} and 0 <= s <= 1 and 0 <= q <= 1
          and lam >= 0 and 4+lam > 0)
    coefficients = branch_coefficients(case, lam, q)
    check('both_original_D_region_directions_only_at_fixed_old_lambda',
          set(bound['d_supports']) == {'DETOUR_RETURN', 'DETOUR_RETRY'})
    for policy in ('DETOUR_RETURN', 'DETOUR_RETRY'):
        support = bound['d_supports'][policy]
        check('exact_original_joint_D_support_coefficients', support['coefficients'] == coefficients[policy])
        check('outward_D_weak_dual_independent_100_digit_verification',
              joint.audit_support(plan['joint_constraints'][D], coefficients[policy], support['support']))
    short_cost, detour_cost = joint.COSTS[case['operating']]
    branches = dict(WAIT=F(0), SHORT=-short_cost-lam+(4+lam)*s,
        DETOUR_RETURN=-detour_cost+bound['d_supports']['DETOUR_RETURN']['support']['upper'],
        DETOUR_RETRY=-detour_cost+bound['d_supports']['DETOUR_RETRY']['support']['upper'])
    candidate = lam*RISK_LIMIT+max(branches.values())
    final = min(old, paired['upper'], candidate)
    check('exact_four_policy_branches_joint_candidate_and_minimum_three_safe_uppers',
          bound['risk_limit'] == RISK_LIMIT and bound['goal_threshold'] == GOAL_THRESHOLD
          and bound['branches'] == branches and bound['joint_candidate'] == candidate
          and bound['upper'] == final and bound['reduction'] == old-final and final <= old)
    check('strict_goal_impossibility_threshold_and_original_decision',
          bound['old_impossible'] == (old < GOAL_THRESHOLD) == plan['goal_impossible']
          and bound['new_impossible'] == (final < GOAL_THRESHOLD))
    return dict(old_goal_upper=old, upper=final, reduction=old-final,
                old_impossible=old < GOAL_THRESHOLD, new_impossible=final < GOAL_THRESHOLD)


def collect_snapshots():
    snapshots, terminals, histories, fees = [], [], [], []
    for life in LIVES:
        for arm in ARMS:
            filename = f'records_life_{life:02d}_{arm}.jsonl.gz'
            records = rows(PREDECESSOR/filename)
            if [row['index'] for row in records] != list(TARGETS):
                raise ValueError('the original complete chronological target roster is required')
            for position, row in enumerate(records):
                plans = [row['initial_plan']]+[batch['plan'] for batch in row['batches']]
                if plans[-1] != row['terminal_plan']:
                    raise ValueError('the terminal must be the final initial/member snapshot')
                identifiers = []
                for prefix, plan in enumerate(plans):
                    identifier = len(snapshots)
                    identifiers.append(identifier)
                    snapshots.append(dict(snapshot_id=identifier, life=life, arm=arm,
                        index=row['index'], identity=row['identity'], case=row['case'],
                        prefix_position=prefix, spent=0 if not prefix else row['batches'][prefix-1]['spent'],
                        plan=plan, is_terminal=prefix == len(plans)-1,
                        baseline_provenance=dict(directory='trajectory_lifecycle_v256', record_file=filename,
                            record_position=position, plan_path='initial_plan' if not prefix else f'batches[{prefix-1}].plan')))
                selected = arm == ARMS[0] and 30 <= row['index'] < 54 and row['query_certified'] and not row['execution_resolved']
                terminal = dict(snapshot_id=identifiers[-1], life=life, arm=arm, index=row['index'],
                    identity=row['identity'], case=row['case'], snapshot_ids=identifiers, primary=selected,
                    spent=row['spent'], query_certified=row['query_certified'], execution_certified=row['execution_certified'],
                    execution_resolved=row['execution_resolved'], old_goal_impossible=row['goal_impossible'],
                    joint_completed=row['joint_completed'], retained_budget_terminal=row['budget_terminal'],
                    retained_budget_after=row['budget_after'], baseline_provenance=snapshots[-1]['baseline_provenance'])
                terminals.append(terminal)
                if selected:
                    histories.append(dict(life=life, arm=arm, index=row['index'], identity=row['identity'],
                        snapshot_ids=identifiers, terminal_snapshot_id=identifiers[-1],
                        baseline_provenance=terminal['baseline_provenance'], retained_record=row))
            artifact_file = f'worker_artifacts_life_{life:02d}_{arm}.json'
            artifact = load(PREDECESSOR/artifact_file)
            fees.append(dict(life=life, arm=arm, fees=artifact['fees'], total_samples=sum(artifact['fees'].values()),
                baseline_provenance=dict(directory='trajectory_lifecycle_v256', worker_artifact_file=artifact_file)))
    return snapshots, terminals, histories, fees


def audit_original_events(snapshot, check):
    life, arm, index = (snapshot[field] for field in ('life', 'arm', 'index'))
    context, identity = snapshot['case']['context'], snapshot['identity']
    _, _, _, interface = paid.world(life)
    for operator, regions in snapshot['plan']['joint_constraints'].items():
        labels = [(f'l{life}/{context}/pool{identity}/{operator}', 720)]*2
        labels.append((f'l{life}/member{index}/{operator}', 8640))
        if arm == ARMS[0] and index >= 30 and operator != interface['changed_operator']:
            other = 'B' if context == 'A' else 'A'
            mapped = interface['b_to_a'].index(identity) if context == 'A' else interface['b_to_a'][identity]
            labels.extend([(f'l{life}/{other}/pool{mapped}/{operator}', 720)]*2)
        check('original_native_source_pool_member_and_compatible_event_labels_no_new_alpha',
              [(region['event'], region['threshold']) for region in regions] == labels)


def score(record, law):
    optimum = paid.oracle_goal(joint.vectors(record['case'], law))
    bound = record['bound']
    return dict(**{field: record[field] for field in ('snapshot_id', 'life', 'arm', 'index', 'identity',
        'prefix_position', 'is_terminal')}, true_optimum=optimum,
        false_old_upper=bound['old_goal_upper'] < optimum, false_new_upper=bound['upper'] < optimum,
        false_impossible_certificate=bound['new_impossible'] and optimum >= GOAL_THRESHOLD,
        truly_impossible=optimum < GOAL_THRESHOLD)


def audit_life_arm(arguments):
    life, arm, snapshots = arguments
    begun, checks, failures = perf_counter(), Counter(), []
    current = None

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, life=life, arm=arm, snapshot_id=current))

    saved = rows(OUTPUT/f'records_life_{life:02d}_{arm}.jsonl.gz')
    scores_saved = rows(OUTPUT/f'results_life_{life:02d}_{arm}.jsonl.gz')
    check('private_life_arm_all_original_snapshots_retained_once_in_chronology',
          [row['snapshot_id'] for row in saved] == [row['snapshot_id'] for row in snapshots])
    _, laws, _, _ = paid.world(life)
    records, results = [], []
    vertices, points, candidates = 0, 0, 0
    for snapshot, row in zip(snapshots, saved):
        current = snapshot['snapshot_id']
        check('immutable_original_paid_snapshot_case_prefix_plan_and_provenance',
              exact({field: row[field] for field in snapshot if field != 'plan'})
              == exact({field: value for field, value in snapshot.items() if field != 'plan'}))
        audit_original_events(snapshot, check)
        bound = audit_bound(row['bound'], snapshot['plan'], snapshot['case'], check)
        independent = dict(**{field: snapshot[field] for field in snapshot if field != 'plan'}, bound=bound)
        records.append(independent)
        results.append(score(independent, laws[snapshot['index']]))
        vertices += len(row['bound']['paired_box']['vertices'])
        points += len(row['bound']['paired_box']['points'])
        candidates += len(row['bound']['old_dual']['candidates'])
        check('actual_per_snapshot_model_CPU_nonnegative', row['model_seconds'] >= 0)
    check('all_frozen_snapshot_true_safe_optima_upper_validity_and_strict_impossibility_scores',
          exact(scores_saved) == exact(results))
    artifact = load(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json')
    check('actual_per_worker_bound_geometry_and_support_work',
          artifact['life'] == life and artifact['arm'] == arm and artifact['snapshots'] == len(snapshots)
          and artifact['model_seconds'] == sum(row['model_seconds'] for row in saved)
          and artifact['work']['coupled_impossibility_bounds'] == len(snapshots)
          and artifact['work']['coupled_box_vertices'] == vertices
          and artifact['work']['coupled_vertex_policy_pairs'] == points
          and artifact['work']['coupled_old_dual_candidates'] == candidates
          and artifact['work']['joint_support_calls'] == 2*len(snapshots))
    check('diagnostic_only_no_new_physical_observations_or_resets_in_work',
          all(artifact['work'].get(field, 0) == 0 for field in
              ('controlled_samples', 'controlled_resets', 'environment_random_draws')))
    check('actual_worker_CPU_output_wall_and_retained_private_normalizer_scopes',
          artifact['model_seconds'] >= 0 and artifact['output_seconds'] >= 0 and artifact['worker_wall_seconds'] >= 0
          and set(artifact['normalizer_cache_statistics']) == {'execution', 'query'})
    for name, size in (('execution', 4096), ('query', 256)):
        statistics = artifact['normalizer_cache_statistics'][name]
        check('private_cold_worker_normalizer_cache_statistics', statistics['maxsize'] == size
              and statistics['hits'] >= 0 and 0 <= statistics['currsize'] <= min(statistics['misses'], size))
    print(f'audit life={life} arm={arm} bounds={len(records)} D_supports={2*len(records)}', flush=True)
    return dict(life=life, arm=arm, records=records, results=results, artifact=artifact,
                checks=checks, failures=failures, elapsed_seconds=perf_counter()-begun)


def counts(records, results):
    scored = {row['snapshot_id']: row for row in results}
    reductions = [F(row['bound']['reduction']) for row in records]
    total = sum(reductions, F(0))
    result = dict(snapshots=len(records), old_impossible=sum(row['bound']['old_impossible'] for row in records),
        new_impossible=sum(row['bound']['new_impossible'] for row in records),
        newly_impossible=sum(row['bound']['new_impossible'] and not row['bound']['old_impossible'] for row in records),
        upper_strictly_reduced=sum(value > 0 for value in reductions), bound_reduction_sum=total,
        mean_bound_reduction=total/len(records) if records else F(0), max_bound_reduction=max(reductions, default=F(0)))
    for output, field in (('false_old_uppers', 'false_old_upper'), ('false_new_uppers', 'false_new_upper'),
                          ('false_impossible_certificates', 'false_impossible_certificate')):
        result[output] = sum(scored[row['snapshot_id']][field] for row in records)
    return result


def summarize(records, results, terminals, primary, fees, artifacts):
    indexed = {row['snapshot_id']: row for row in records}
    terminal_records = [indexed[row['snapshot_id']] for row in terminals]
    primary_records = [indexed[row['terminal_snapshot_id']] for row in primary]
    histories = []
    for history in primary:
        path = [indexed[identifier] for identifier in history['snapshot_ids']]
        first = next((row for row in path if row['bound']['new_impossible'] and not row['bound']['old_impossible']), None)
        histories.append(dict(life=history['life'], arm=history['arm'], index=history['index'], identity=history['identity'],
            terminal_snapshot_id=history['terminal_snapshot_id'], terminal_new_impossible=path[-1]['bound']['new_impossible'],
            earliest_newly_certified_prefix=None if first is None else dict(snapshot_id=first['snapshot_id'],
                prefix_position=first['prefix_position'], spent=first['spent'], upper=first['bound']['upper']),
            retained_terminal_member_samples=history['retained_record']['spent']))
    aggregate = counts(records, results)
    conditions = dict(all_primary_terminal_impossibilities=all(row['bound']['new_impossible'] for row in primary_records),
        nonlooser_bounds=all(row['bound']['upper'] <= row['bound']['old_goal_upper'] for row in records),
        valid_upper_bounds=aggregate['false_new_uppers'] == 0,
        valid_impossibility_certificates=aggregate['false_impossible_certificates'] == 0)
    grouped = []
    for life in LIVES:
        for arm in ARMS:
            for stage in ('A', 'B', 'A_RETURN'):
                for identity in range(3):
                    own = [row for row in records if (row['life'], row['arm'], row['case']['stage'], row['identity'])
                           == (life, arm, stage, identity)]
                    grouped.append(dict(life=life, arm=arm, stage=stage, identity=identity,
                        all_prefixes=counts(own, results), terminals=counts([row for row in own if row['is_terminal']], results)))
    return dict(complete=True, records=len(records), terminal_records=len(terminals), primary_terminals=len(primary),
        all_prefixes=aggregate, terminals=counts(terminal_records, results), primary=counts(primary_records, results),
        methods={arm: dict(all_prefixes=counts([row for row in records if row['arm'] == arm], results),
            terminals=counts([row for row in terminal_records if row['arm'] == arm], results)) for arm in ARMS},
        grouped_counts=grouped, primary_histories=histories, retained_fee_ledger=fees, conditions=conditions,
        method_condition_met=all(conditions.values()), independent_audit_required=True,
        model_seconds=sum(job['model_seconds'] for job in artifacts),
        model_seconds_scope='summed_process_CPU_box_vertices_exact_old_LP_dual_paired_reference_and_two_full_D_supports',
        output_seconds=sum(job['output_seconds'] for job in artifacts),
        worker_wall_seconds=[dict(life=job['life'], arm=job['arm'], seconds=job['worker_wall_seconds']) for job in artifacts],
        work=[dict(life=job['life'], arm=job['arm'], **job['work']) for job in artifacts],
        normalizer_cache_statistics=[dict(life=job['life'], arm=job['arm'], statistics=job['normalizer_cache_statistics'])
                                     for job in artifacts],
        new_environment_observations=0, new_event_allocations=0, lifecycle_cost_savings_measured=False,
        acquisition_and_execution_unchanged=True, scientific_gate_changed=False, u006_started=False, diagnostic_only=True)


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name))

    snapshots, terminals, primary, fees = collect_snapshots()
    check('immutable_V256_complete_and_independently_valid', load(PREDECESSOR/'run.json')['complete']
          and load(PREDECESSOR/'analysis.json')['valid'])
    check('all949_original_initial_member_snapshots432_unique_terminals_and16_observable_primary',
          len(snapshots) == 949 and len(terminals) == 432 and len(primary) == 16
          and sum(row['is_terminal'] for row in snapshots) == 432
          and len({(row['life'], row['arm'], row['index']) for row in terminals}) == 432)
    check('exact_original_snapshots_native_rows_regions_query_plans_mix_and_prefix_provenance',
          exact(rows(OUTPUT/'snapshots.jsonl.gz')) == exact(snapshots))
    check('exact_terminal_subset_and_full16_primary_histories_selected_without_oracle',
          exact(load(OUTPUT/'terminals.json')) == exact(terminals)
          and exact(rows(OUTPUT/'primary_histories.jsonl.gz')) == exact(primary))
    check('full_original_source_shared_member_execution_fees_unchanged_and_not_new_savings',
          all(row['fees']['source'] == 4608 and row['total_samples'] == sum(row['fees'].values())
              and row['total_samples'] <= baseline.CAPS[row['life']] for row in fees))
    check('same_original_execution_pool_member_confidence_allocation_no_new_events',
          F(18, 720)+F(216, 8640) == RISK_LIMIT)
    saved, summary_saved = load(OUTPUT/'run.json'), load(OUTPUT/'summary.json')
    protocol = dict(baseline='reports/trajectory_lifecycle_v256', lives=list(LIVES), arms=list(ARMS), snapshots=949,
        terminal_targets=432, primary_terminals=16, primary_rule='TRAJECTORY_REUSE_B_query_certified_and_not_execution_resolved',
        lambda_rule='exact_old_four_policy_LP_dual_minimum_smallest_lambda_on_ties',
        risk_limit='1/20', goal_threshold=2, strict_impossibility=True, pool_threshold=720, member_threshold=8640,
        confidence_scope='unchanged_V256_per_life_fixed_arm_execution_1/20_event_no_new_alpha',
        final_upper='minimum_of_retained_old_same_lambda_paired_box_and_original_full_D_joint_support',
        data_access='V256_settled_target_records_original_paid_row_regions_envelopes_cases_and_worker_fees_only_before_bounds_frozen',
        truth_scoring='only_after_all949_bounds_and_all432_terminal_references_frozen',
        retained_fee_ledger=fees, new_environment_observations=0, new_event_allocations=0, lifecycle_cost_savings_measured=False,
        scientific_gate_changed=False, u006_started=False, diagnostic_only=True,
        prerequisites=dict(v256_complete=True, v256_independent_valid=True), complete=True,
        phases=['source_captured', 'all_snapshots_and_primary_histories_frozen', 'all_bounds_frozen', 'posthoc_scored', 'complete'],
        elapsed_seconds=summary_saved['elapsed_seconds'], model_seconds=summary_saved['model_seconds'])
    check('frozen_same_evidence_protocol_all_bounds_before_posthoc_truth_barrier', exact(saved) == exact(protocol))
    required = {'src/acfqp/science/coupled_impossibility_v257.py', 'scripts/run_coupled_impossibility_v257.py',
        'scripts/audit_coupled_impossibility_v257.py', 'tests/test_coupled_impossibility_v257_core.py',
        'tests/test_coupled_impossibility_v257_runner.py', 'tests/test_coupled_impossibility_v257_audit.py',
        'specs/COUPLED_IMPOSSIBILITY_V257.md'}
    manifest = load(OUTPUT/'source_manifest.json')
    check('all_new_implementation_spec_and_focused_tests_captured_before_bounds', required <= set(manifest))
    for relative in manifest:
        check('captured_source_exact_bytes_unchanged', (ROOT/relative).read_bytes() == (OUTPUT/'source_code'/relative).read_bytes())
    arguments = [(life, arm, [row for row in snapshots if (row['life'], row['arm']) == (life, arm)])
                 for life in LIVES for arm in ARMS]
    with ProcessPoolExecutor(max_workers=6) as executor:
        groups = list(executor.map(audit_life_arm, arguments))
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
    records = [row for group in groups for row in group['records']]
    results = [row for group in groups for row in group['results']]
    artifacts = [group['artifact'] for group in groups]
    summary = summarize(records, results, terminals, primary, fees, artifacts)
    expected = dict(summary, elapsed_seconds=summary_saved['elapsed_seconds'])
    check('independent_all_prefix_terminal_primary_stage_type_history_fee_and_condition_summary',
          exact(summary_saved) == exact(expected))
    check('actual_parent_and_worker_elapsed_cost_nonnegative', summary_saved['elapsed_seconds'] >= 0)
    result = dict(valid=not failures, complete=True, records=len(records), terminal_records=len(terminals),
        primary_terminals=len(primary), life_arm_jobs=len(groups),
        independently_checked_D_supports=checks['outward_D_weak_dual_independent_100_digit_verification'],
        all_prefixes=summary['all_prefixes'], terminals=summary['terminals'], primary=summary['primary'],
        primary_histories=summary['primary_histories'], retained_fee_ledger=fees, conditions=summary['conditions'],
        method_condition_met=summary['method_condition_met'], new_environment_observations=0, new_event_allocations=0,
        lifecycle_cost_savings_measured=False, scientific_gate_changed=False, u006_started=False,
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun,
        life_arm_elapsed_seconds={f'{row["life"]}:{row["arm"]}': row['elapsed_seconds'] for row in groups})
    (OUTPUT/'analysis.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
    print(json.dumps(result, default=str), flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if run()['valid'] else 1)
