"""Independent conditional-trajectory, primitive-fee and certificate audit.

The producer and its new trajectory module are not imported. Complete paired
rounds provide directly observed policy vectors; source/target primitive tapes
and each retained proof are independently reconstructed.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import json
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_paired_query_score_v233 as trajectory
from scripts import audit_bidirectional_lifecycle_v243 as row_math

OUTPUT = ROOT/'reports/executable_trajectory_v254'
LIVES, METHODS = (0, 1, 2), ('ROW_JOINT', 'TRAJECTORY')
LIFE_CAPS, SOURCE_BASE, TARGET_BASE = (14144, 17072, 17168), 299000, 300000
OPERATORS, ALPHABETS = row_math.OPERATORS, row_math.ALPHABETS
POLICIES, QUERIES = trajectory.POLICIES, ('reward', 'goal', 'risk')
S, DETOUR, R = OPERATORS
REGRET, SOURCE_COST, MIDDLE_COST = F(1, 20), 4608, 7680
load, exact = trajectory.load, row_math.fractions
CHECKPOINTS = ('SOURCE', 'SOURCE_PLUS_3072', 'FULL_CAP')
COSTS = tuple((operating, retry) for operating in ('low', 'high') for retry in ('17/20', '19/20'))
OUTCOME_KEYS = ('DELIVERY|DELIVERY|NONE', 'DELIVERY|LOST|NONE', 'DELIVERY|RECOVERY|DELIVERY',
    'DELIVERY|RECOVERY|LOST', 'LOST|DELIVERY|NONE', 'LOST|LOST|NONE',
    'LOST|RECOVERY|DELIVERY', 'LOST|RECOVERY|LOST')


def round_vectors(observations, case):
    """Actual complete policy outcomes, including the conditional retry cost."""
    short_cost, detour_cost = trajectory.COSTS[case['operating']]
    short, detour = observations[S], observations[DETOUR]
    recovery = detour == 'RECOVERY'
    retry = observations[R] if recovery else None
    return dict(WAIT=[F(0)]*3,
        SHORT=[-short_cost, F(short == 'LOST'), F(short == 'DELIVERY')],
        DETOUR_RETURN=[-detour_cost, F(detour == 'LOST'), F(detour == 'DELIVERY')],
        DETOUR_RETRY=[-detour_cost-(F(case['retry_cost']) if recovery else 0),
                      F(detour == 'LOST' or recovery and retry == 'LOST'),
                      F(detour == 'DELIVERY' or recovery and retry == 'DELIVERY')])


def empirical_vectors(rounds, case):
    totals = {policy: [F(0)]*3 for policy in POLICIES}
    for observations in rounds:
        for policy, vector in round_vectors(observations, case).items():
            for coordinate, value in enumerate(vector):
                totals[policy][coordinate] += value
    return {policy: [value/len(rounds) for value in vector] for policy, vector in totals.items()}


def point_queries(vectors):
    return {query: min(POLICIES, key=lambda policy: (-trajectory.utility(vectors[policy], weights), policy))
            for query, weights in trajectory.WEIGHTS.items()}


def direct_scores(rounds, query, chosen, other, retry_cost):
    needed, table, lower, upper = trajectory.specification(query, chosen, other, retry_cost)
    scores = [trajectory.atom_score(other, observations, query, retry_cost)
              -trajectory.atom_score(chosen, observations, query, retry_cost) for observations in rounds]
    return needed, scores, lower, upper


def audit_row_certificate(counts, case, chosen, saved, profiles, decisions, used, check):
    """Validate the old row engine at the common directly observed choice."""
    check('row_engine_original_threshold_and_analytic_reward', saved['threshold'] == 960
          and saved['queries']['reward'] == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost'))
    ready = dict(reward=True)
    for query in ('goal', 'risk'):
        decision, policy = saved['queries'][query], chosen[query]
        alternatives = [other for other in POLICIES if other != policy]
        references = decision['comparisons']
        check('row_original_all_alternatives_at_shared_joint_mean_choice', decision['policy'] == policy
              and [reference['other'] for reference in references] == alternatives)
        certified = []
        for reference, other in zip(references, alternatives):
            identifier = reference['profile_id']
            used.add(identifier)
            proof = decisions[identifier]
            row_math.audit_reference(profiles[identifier], reference, counts, case,
                                     query, policy, other, proof, check)
            certified.append(proof)
        ready[query] = len(certified) == 3 and all(certified)
        check('row_three_alternatives_AND', decision['certified'] == ready[query])
    check('row_all_queries_AND', saved['all_ready'] == all(ready.values()))
    return ready


def audit_trajectory_certificate(rounds, case, chosen, saved, check):
    check('direct_original_threshold_and_analytic_reward', saved['threshold'] == 4320
          and saved['queries']['reward'] == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost'))
    ready, cache, comparisons = dict(reward=True), {}, []
    for query in ('goal', 'risk'):
        decision, policy = saved['queries'][query], chosen[query]
        alternatives = [other for other in POLICIES if other != policy]
        check('direct_fixed_ordered_streams_at_shared_joint_mean_choice', decision['policy'] == policy
              and [comparison['other'] for comparison in decision['comparisons']] == alternatives)
        certified = [audit_direct_comparison(rounds, case, query, policy, other, comparison, check, cache)
                     for other, comparison in zip(alternatives, decision['comparisons'])]
        comparisons.extend(decision['comparisons'])
        ready[query] = len(certified) == 3 and all(certified)
        check('direct_three_alternatives_AND', decision['certified'] == ready[query])
    check('direct_all_queries_AND_and_comparison_records',
          saved['all_ready'] == all(ready.values()) and saved['comparison_records'] == comparisons)
    return ready


def score_queries(queries, case, law):
    pure = trajectory.vectors(case, law)
    result = {}
    for query, weights in trajectory.WEIGHTS.items():
        policy = queries[query]['policy']
        value = trajectory.utility(pure[policy], weights)
        result[query] = dict(policy=policy, actual=pure[policy], utility=value,
            regret=max(trajectory.utility(vector, weights) for vector in pure.values())-value)
    return result


def posthoc_scores_equal(saved, independently_scored):
    return exact(saved) == exact(independently_scored)


def audit_direct_comparison(rounds, case, query, chosen, other, saved, check, cache):
    key = query, chosen, other, F(case['retry_cost']) if 'DETOUR_RETRY' in (chosen, other) else None
    if key not in cache:
        needed, scores, lower, upper = direct_scores(rounds, query, chosen, other, case['retry_cost'])
        cache[key] = needed, scores, lower, upper, trajectory.predictable_bets(scores, lower, upper)
    needed, scores, lower, upper, bets = cache[key]
    units = [int(score*20) for score in scores]
    check('complete_conditional_round_score_statistics_without_row_minimum',
          saved['query'] == query and saved['chosen'] == chosen and saved['other'] == other
          and (F(saved['retry_cost']) if saved['retry_cost'] is not None else None) == key[-1]
          and saved['required_rows'] == list(needed) and list(map(F, saved['score_bounds'])) == [lower, upper]
          and saved['n'] == len(rounds) == len(scores)
          and {int(score): count for score, count in saved['score_histogram'].items()} == dict(Counter(units))
          and saved['score_sum_units'] == sum(units)
          and saved['score_square_sum_units'] == sum(value*value for value in units)
          and saved['zero_bets'] == sum(bet == 0 for bet in bets)
          and saved['score_source'] == 'actual_complete_conditional_rounds')
    constant = trajectory.operating_constant(case, chosen, other)
    theta = REGRET-constant
    check('frozen_conditional_score_support_null_and_event_threshold',
          F(saved['constant_gap']) == constant and F(saved['theta']) == theta and saved['threshold'] == 4320
          and all(lower <= score <= upper for score in scores)
          and all(0 <= bet <= 1/(upper-lower) for bet in bets))
    if theta >= upper:
        kind, certified = 'score_range', True
    elif theta < lower:
        kind, certified = 'below_score_range', False
    else:
        kind = 'bounded_mean_bet'
        logs = trajectory.independent_logs(scores, bets, theta)
        value = logs[-1] if logs else D(0)
        saved_log, saved_product = D(saved['log_e_lower']), D(saved['e_lower'])
        with localcontext() as context:
            context.prec = 100
            check('direct_outward_lower_log_product_and_threshold',
                saved_log <= value+D('1e-85') and saved_product >= 0
                and (saved_product == 0 if not value.is_finite() else saved_product.ln() <= value+D('1e-85'))
                and D(saved['log_threshold_upper']) >= D(4320).ln()-D('1e-85'))
        certified = saved_log > D(saved['log_threshold_upper'])
    if kind != 'bounded_mean_bet':
        check('direct_analytic_support_without_evidence_product',
              all(saved[field] is None for field in ('log_e_lower', 'e_lower', 'log_threshold_upper')))
    check('direct_exact_certification_status', saved['kind'] == kind and saved['certified'] == certified)
    return certified


def replay_life(life, tape, round_records, check):
    """Reconstruct actual primitive calls and all three exact budget prefixes."""
    _, laws, _, _ = trajectory.world(life)
    native = [row_math.empty() for _ in range(3)]
    complete, tails, last_ids = [[] for _ in range(3)], [0]*3, [None]*3
    prefixes, global_step, round_id, cursor, round_position = {}, 0, 0, 0, 0
    phase_step = dict(SOURCE=0, ACQUISITION=0)
    generators = {phase: {(identity, operator): random.Random(base+(life*3+identity)*3+j)
        for identity in range(3) for j, operator in enumerate(OPERATORS)}
        for phase, base in (('SOURCE', SOURCE_BASE), ('ACQUISITION', TARGET_BASE))}
    offsets = {phase: Counter() for phase in ('SOURCE', 'ACQUISITION')}
    for segment, cap in enumerate((SOURCE_COST, MIDDLE_COST, LIFE_CAPS[life])):
        phase, base = ('SOURCE', SOURCE_BASE) if segment == 0 else ('ACQUISITION', TARGET_BASE)
        while global_step < cap:
            identity, tail = cursor%3, cap-global_step < 3
            next_id = None if tail else round_id+1
            observations, steps, start = {operator: None for operator in OPERATORS}, [], global_step+1

            def draw(operator, role):
                nonlocal global_step
                key = identity, operator
                outcome = trajectory._draw(generators[phase][key], laws[identity], operator, 1)[0]
                expected = dict(life=life, phase=phase, segment=segment, step_index=global_step+1,
                    phase_step_index=phase_step[phase]+1, identity=identity, operator=operator,
                    seed=base+(life*3+identity)*3+OPERATORS.index(operator),
                    draw_start=offsets[phase][key], draw_end=offsets[phase][key]+1,
                    outcome=outcome, round_id=next_id, role=role)
                check('fresh_actual_conditional_primitive_seed_phase_offset_and_fee', tape[global_step] == expected)
                offsets[phase][key] += 1
                phase_step[phase] += 1
                global_step += 1
                steps.append(global_step)
                native[identity][operator][outcome] += 1
                observations[operator] = outcome

            draw(S, 'tail_S' if tail else 'S')
            if tail:
                tails[identity] += 1
            else:
                draw(DETOUR, 'D')
                if observations[DETOUR] == 'RECOVERY':
                    draw(R, 'R')
                round_id += 1
                expected_round = dict(life=life, round_id=round_id, phase=phase, segment=segment,
                    identity=identity, primitive_steps=steps, outcomes=observations, start_step=start, end_step=global_step)
                check('actual_complete_round_trace_conditional_R_and_primitive_refs',
                      round_records[round_position] == expected_round)
                round_position += 1
                complete[identity].append(observations)
                last_ids[identity] = round_id
            cursor += 1
        prefixes[cap] = dict(native_counts=deepcopy(native), rounds=[list(values) for values in complete],
            tail_s_samples=list(tails), round_prefix_last_ids=list(last_ids),
            source_paid_samples=SOURCE_COST, acquisition_paid_samples=cap-SOURCE_COST,
            total_paid_samples=cap, type_cursor=cursor)
        check('exact_checkpoint_charge_matches_actual_native_row_observations',
              sum(sum(row.values()) for bank in native for row in bank.values()) == cap)
    check('all_fresh_primitives_and_complete_rounds_retained_once',
          global_step == len(tape) == LIFE_CAPS[life] and round_position == len(round_records)
          and phase_step == dict(SOURCE=SOURCE_COST, ACQUISITION=LIFE_CAPS[life]-SOURCE_COST))
    return prefixes


def joint_histogram(rounds):
    counts = dict.fromkeys(OUTCOME_KEYS, 0)
    for observations in rounds:
        key = '|'.join(observations[operator] if observations[operator] is not None else 'NONE' for operator in OPERATORS)
        counts[key] += 1
    return counts


def audit_checkpoint(saved, prefix, profiles, decisions, used, check):
    identity, case = saved['identity'], saved['case']
    native, rounds = prefix['native_counts'][identity], prefix['rounds'][identity]
    vectors = empirical_vectors(rounds, case)
    chosen = point_queries(vectors)
    queries = {query: dict(policy=policy) for query, policy in chosen.items()}
    check('same_actual_paid_prefix_native_counts_joint_rounds_and_tails',
        saved['native_counts'] == native and saved['complete_rounds'] == len(rounds)
        and saved['joint_outcome_counts'] == joint_histogram(rounds)
        and saved['native_n_by_operator'] == {operator: sum(row.values()) for operator, row in native.items()}
        and saved['tail_s_samples'] == prefix['tail_s_samples'][identity]
        and saved['round_prefix_last_id'] == prefix['round_prefix_last_ids'][identity]
        and saved['source_paid_samples'] == prefix['source_paid_samples'] == SOURCE_COST
        and saved['acquisition_paid_samples'] == prefix['acquisition_paid_samples']
        and saved['total_paid_samples'] == saved['checkpoint_samples'] == prefix['total_paid_samples'])
    check('shared_raw_complete_trajectory_mean_vectors_and_policy_choices',
        exact(saved['pure_vectors']) == vectors and saved['queries'] == queries
        and saved['row_joint']['case'] == case and saved['row_joint']['queries'] == queries)
    row_ready = audit_row_certificate(native, case, chosen, saved['row_joint']['query_evidence'],
                                     profiles, decisions, used, check)
    direct_ready = audit_trajectory_certificate(rounds, case, chosen, saved['trajectory'], check)
    check('both_fixed_method_ready_flags_match_independent_all_queries',
          saved['row_joint']['query_ready'] == all(row_ready.values())
          and saved['trajectory']['all_ready'] == all(direct_ready.values()))
    check('per_checkpoint_actual_model_CPU_and_retention_wall_nonnegative',
          set(saved['model_seconds']) == {'point_vectors', 'row_joint', 'trajectory'}
          and all(value >= 0 for value in saved['model_seconds'].values()) and saved['output_seconds'] >= 0)
    return dict(ROW_JOINT=row_ready, TRAJECTORY=direct_ready)


def public_roster():
    roster = []
    for life in LIVES:
        cases, _, identities, _ = trajectory.world(life)
        for label, cap in zip(CHECKPOINTS, (SOURCE_COST, MIDDLE_COST, LIFE_CAPS[life])):
            for identity in range(3):
                for cost_index, (operating, retry) in enumerate(COSTS):
                    case = dict(id=f'v254_l{life:02d}_{label.lower()}_t{identity}_c{cost_index}',
                        operating=operating, retry_cost=retry, context='A', stage='QUERY_QUALIFICATION')
                    roster.append(dict(life=life, kind='CHECKPOINT', checkpoint_label=label,
                        checkpoint_samples=cap, identity=identity, cost_index=cost_index, case=case, index=None))
        for index in range(54, 78):
            case = deepcopy(cases[index])
            roster.append(dict(life=life, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP',
                checkpoint_samples=LIFE_CAPS[life], identity=identities[index],
                cost_index=COSTS.index((case['operating'], str(case['retry_cost']))), case=case, index=index))
    return roster


def projected_record(original, roster):
    result = deepcopy(original)
    result.update(deepcopy(roster), selected_full_cap_record=dict(life=roster['life'], identity=roster['identity'],
        cost_index=roster['cost_index']), model_seconds=dict.fromkeys(('point_vectors', 'row_joint', 'trajectory'), 0.),
        output_seconds=0.)
    result['row_joint']['case'] = deepcopy(roster['case'])
    return result


def method_evidence(record, method):
    return record['row_joint']['query_evidence'] if method == 'ROW_JOINT' else record['trajectory']


def audit_life(life):
    begun, checks, failures, location = perf_counter(), Counter(), [], dict(life=life)

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    tape, rounds, records, profiles = (trajectory.read_rows(OUTPUT/f'{kind}_life_{life:02d}.jsonl.gz')
                                      for kind in ('tapes', 'rounds', 'records', 'profiles'))
    prefixes = replay_life(life, tape, rounds, check)
    check('private_ROW_profile_ids_complete_once', [row['profile_id'] for row in profiles] == list(range(len(profiles))))
    decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, profile_id=profile['profile_id'])
        decisions[profile['profile_id']] = row_math.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    roster = [row for row in public_roster() if row['life'] == life]
    check('all_36_checkpoint_and_24_original_return_projections_in_frozen_order',
          len(records) == len(roster) == 60
          and [{field: row[field] for field in item} for row, item in zip(records, roster)] == roster)
    used, full, work, convex_keys, score_keys = set(), {}, Counter(), set(), {}
    for record, item in zip(records, roster):
        location = {field: item[field] for field in ('life', 'kind', 'checkpoint_samples', 'identity', 'cost_index', 'index')}
        if item['kind'] == 'RETURN_PROJECTION':
            check('original_public_return_projection_exactly_reuses_full_cap_decision_without_new_certificate',
                  record == projected_record(full[item['identity'], item['cost_index']], item))
            continue
        prefix = prefixes[item['checkpoint_samples']]
        audit_checkpoint(record, prefix, profiles, decisions, used, check)
        if item['checkpoint_label'] == 'FULL_CAP':
            full[item['identity'], item['cost_index']] = record
        work['online_query_comparison_calls'] += 6
        work['trajectory_certificate_evaluations'] += 6
        actual_rounds = prefix['rounds'][item['identity']]
        actual_prefix = tuple(tuple(outcomes[operator] for operator in OPERATORS) for outcomes in actual_rounds)
        for query in ('goal', 'risk'):
            for reference in record['row_joint']['query_evidence']['queries'][query]['comparisons']:
                cert = profiles[reference['profile_id']]['certificate']
                if cert.get('engine') == 'convex_tangent':
                    work['online_convex_certificate_calls'] += 1
                    convex_keys.add((cert['family'], query, cert['chosen'], cert['other'], F(cert['relevant_cost']),
                                     row_math.freeze(cert['projected_counts'])))
                else:
                    work['projected_certificate_calls'] += 1
            for comparison in record['trajectory']['queries'][query]['comparisons']:
                retry = F(record['case']['retry_cost']) if 'DETOUR_RETRY' in (comparison['chosen'], comparison['other']) else None
                score_keys[query, comparison['chosen'], comparison['other'], retry, actual_prefix] = len(actual_rounds)
        print(f'audit life={life} checkpoint={item["checkpoint_label"]} identity={item["identity"]} cost={item["cost_index"]}', flush=True)
    nonconvex = [profile for profile in profiles if profile['certificate'].get('engine') != 'convex_tangent']
    work.update(online_convex_proposal_calls=len(convex_keys),
        online_convex_certificate_cache_hits=work['online_convex_certificate_calls']-len(convex_keys),
        projected_certificate_cache_hits=work['projected_certificate_calls']-len(nonconvex),
        projected_bad_null_mle=sum(row['certificate']['witness_kind'] == 'bad_null_mle' for row in nonconvex),
        projected_partition_leaves=sum(len(row['certificate'].get('leaves', ())) for row in nonconvex),
        trajectory_unique_score_prefixes=len(score_keys), trajectory_score_cache_hits=work['trajectory_certificate_evaluations']-len(score_keys),
        trajectory_complete_score_evaluations=sum(score_keys.values()), complete_conditional_rounds=len(rounds),
        standalone_S_tails=sum(row['role'] == 'tail_S' for row in tape))
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        work[field] = len(tape)
    threshold_work = sum(ALPHABETS[row['operator']].index(row['outcome'])+1 for row in tape)
    work['sampling_threshold_accumulations'] = work['sampling_threshold_comparisons'] = threshold_work
    artifact = load(OUTPUT/f'worker_artifacts_life_{life:02d}.json')
    check('all_new_ROW_profiles_used_once_in_private_life_file', used == set(range(len(profiles))))
    final = prefixes[LIFE_CAPS[life]]
    check('final_native_joint_counts_exact_actual_primitive_source_and_acquisition_fees',
          artifact['life'] == life and artifact['final_native_counts'] == final['native_counts']
          and artifact['final_joint_outcome_counts'] == [joint_histogram(values) for values in final['rounds']]
          and artifact['primitive_samples'] == LIFE_CAPS[life] and artifact['source_samples'] == SOURCE_COST
          and artifact['acquisition_samples'] == LIFE_CAPS[life]-SOURCE_COST
          and artifact['complete_rounds'] == len(rounds) and artifact['tail_s_samples'] == sum(final['tail_s_samples']))
    for field, count in work.items():
        check('actual_primitive_score_and_independent_private_cache_work', artifact['work'].get(field, 0) == count)
    statistics = artifact['cache_statistics']
    check('private_life_row_and_direct_cache_sizes', statistics['row_V235'] == len(nonconvex)
          and statistics['row_convex'] == len(convex_keys) and statistics['direct_score_prefixes'] == len(score_keys)
          and statistics['row_profiles'] == len(profiles))
    for name, capacity in (('execution', 4096), ('query', 256)):
        stats = statistics['normalizers'][name]
        check('private_normalizer_actual_cache_statistics', stats['maxsize'] == capacity
              and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    for scope in ('point_vectors', 'row_joint', 'trajectory'):
        check('actual_checkpoint_process_CPU_by_scope', artifact['timings'][scope]
              == sum(row['model_seconds'][scope] for row in records))
    check('actual_native_update_CPU_observation_and_retention_wall', artifact['timings']['observation_updates'] >= 0
          and artifact['observation_seconds'] >= 0 and artifact['worker_wall_seconds'] >= 0
          and artifact['output_seconds'] >= sum(row['output_seconds'] for row in records))
    _, laws, _, _ = trajectory.world(life)
    saved_scores = trajectory.read_rows(OUTPUT/f'scores_life_{life:02d}.jsonl.gz')
    scores = []
    for row in records:
        queries = score_queries(row['queries'], row['case'], laws[row['identity']])
        score = dict(**{field: row[field] for field in ('life', 'kind', 'checkpoint_samples', 'identity', 'cost_index', 'index', 'case')},
            queries=queries, false_certificates={method: sum(decision['certified'] and queries[query]['regret'] > REGRET
                for query, decision in method_evidence(row, method)['queries'].items()) for method in METHODS})
        scores.append(score)
    check('postfreeze_exact_truth_scores_and_false_certificate_counts_for_all_fixed_methods', posthoc_scores_equal(saved_scores, scores))
    return dict(life=life, records=records, scores=scores, artifact=artifact, profiles=len(profiles), leaves=leaves,
        checks=checks, failures=failures, elapsed_seconds=perf_counter()-begun)


def group_summary(records, method):
    evidence = [method_evidence(row, method) for row in records]
    critical = [comparison for item in evidence for comparison in item['queries']['goal'].get('comparisons', ())
                if item['queries']['goal']['policy'] == 'SHORT' and comparison['other'] == 'DETOUR_RETRY']
    return dict(pairs=len(records), query_ready=sum(item['all_ready'] for item in evidence),
        certified_by_query={query: sum(item['queries'][query]['certified'] for item in evidence) for query in QUERIES},
        critical_short_retry=dict(comparisons=len(critical), certified=sum(item['certified'] for item in critical)))


def paired_summary(records):
    result = {}
    for metric in ('query_ready',)+QUERIES:
        gains, losses, changes = 0, 0, []
        for row in records:
            evidence = [method_evidence(row, method) for method in METHODS]
            before, after = [item['all_ready'] if metric == 'query_ready' else item['queries'][metric]['certified'] for item in evidence]
            gains += after and not before
            losses += before and not after
            if before != after:
                changes.append(dict(life=row['life'], identity=row['identity'], cost_index=row['cost_index'],
                                    index=row['index'], before=before, after=after))
        result[metric] = dict(gains=gains, losses=losses, unchanged=len(records)-gains-losses, changes=changes)
    return result


def summarize(records, scores, artifacts):
    terminal = [row for row in records if row['kind'] == 'RETURN_PROJECTION']
    methods = {method: dict(checkpoint_groups={label: group_summary([row for row in records
        if row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label], method) for label in CHECKPOINTS},
        terminal=group_summary(terminal, method), false_certificates=sum(row['false_certificates'][method] for row in scores)) for method in METHODS}
    scopes = ('observation_updates', 'point_vectors', 'row_joint', 'trajectory')
    return dict(complete=True, records=len(records), checkpoint_pairs=sum(row['kind'] == 'CHECKPOINT' for row in records),
        terminal_pairs=len(terminal), methods=methods,
        paired_checkpoint_groups={label: paired_summary([row for row in records
            if row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label]) for label in CHECKPOINTS},
        terminal_paired=paired_summary(terminal),
        life_summaries=[dict(life=life, methods={method: dict(checkpoint_groups={label: group_summary([row for row in records
            if row['life'] == life and row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label], method) for label in CHECKPOINTS},
            terminal=group_summary([row for row in terminal if row['life'] == life], method)) for method in METHODS}) for life in LIVES],
        physical_observations=sum(item['primitive_samples'] for item in artifacts),
        physical_source_samples=sum(item['source_samples'] for item in artifacts),
        physical_acquisition_samples=sum(item['acquisition_samples'] for item in artifacts),
        fee_ledger=[dict(life=item['life'], source_samples=item['source_samples'], acquisition_samples=item['acquisition_samples'],
            total_samples=item['primitive_samples']) for item in artifacts],
        model_seconds=sum(sum(item['timings'].values()) for item in artifacts),
        model_timings={scope: sum(item['timings'][scope] for item in artifacts) for scope in scopes},
        model_seconds_scope='summed_process_CPU_native_updates_shared_point_vectors_ROW_proofs_and_TRAJECTORY_proofs_once',
        observation_seconds=sum(item['observation_seconds'] for item in artifacts),
        output_seconds=sum(item['output_seconds'] for item in artifacts),
        cache_statistics=[dict(life=item['life'], **item['cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'], **item['work']) for item in artifacts],
        positive_qualification_signal=(methods['TRAJECTORY']['terminal']['certified_by_query']['goal']
            > methods['ROW_JOINT']['terminal']['certified_by_query']['goal']
            and all(methods[method]['false_certificates'] == 0 for method in METHODS)),
        qualification_only=True, complete_lifecycle_test=False, scientific_gate_changed=False,
        evidence_unit='one_controlled_categorical_operator_observation', source_allocation='conditional_rounds_and_standalone_S_tails')


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name))

    protocol, summary = (load(OUTPUT/name) for name in ('run.json', 'summary.json'))
    roster = public_roster()
    check('frozen_fresh_conditional_round_scope_seeds_costs_and_all_public_decisions', protocol['complete']
        and protocol['lives'] == list(LIVES) and protocol['methods'] == list(METHODS)
        and protocol['source_budget'] == SOURCE_COST and protocol['total_caps'] == list(LIFE_CAPS)
        and protocol['checkpoints'] == list(CHECKPOINTS) and protocol['source_seed_base'] == SOURCE_BASE
        and protocol['acquisition_seed_base'] == TARGET_BASE
        and protocol['cursor'] == 'advance_after_complete_round_or_standalone_S_tail_never_reset'
        and protocol['source_allocation'] == 'complete_actual_S_D_conditional_R_rounds_and_S_tails'
        and protocol['acquisition_offsets'] == 'continuous_across_7680_checkpoint'
        and protocol['row_events'] == 48 and protocol['row_active_A_events'] == 24 and protocol['row_threshold'] == 960
        and protocol['trajectory_streams'] == 216 and protocol['trajectory_active_A_streams'] == 108
        and protocol['trajectory_threshold'] == 4320 and protocol['delta_per_life_fixed_method'] == '1/20'
        and not protocol['combined_method_claim'] and F(48, 960) == F(216, 4320) == REGRET
        and protocol['checkpoint_pairs'] == 108 and protocol['terminal_projection_pairs'] == 72
        and protocol['roster'] == load(OUTPUT/'public_roster.json') == roster
        and protocol['score_rule'] == 'original_V233_ScoreSpec_predictable_bets_evaluate_on_complete_actual_rounds'
        and protocol['policy_rule'] == 'shared_raw_joint_trajectory_means_with_lexical_ties'
        and protocol['cost_unit'] == 'one_controlled_categorical_operator_observation'
        and protocol['deterministic_graph_transitions'] == 'local_mechanics_zero_new_observations'
        and protocol['no_offpath_R'] and protocol['no_execution_planner'] and not protocol['new_lifecycle_test']
        and protocol['cache_scope'] == 'private_cold_per_life_ROW_and_TRAJECTORY'
        and not protocol['scientific_gate_changed'] and protocol['qualification_only']
        and protocol['phases'] == ['protocol_and_roster_frozen', 'source_captured', 'all_180_decision_pairs_frozen',
                                  'posthoc_truth_scored', 'complete'])
    manifest = load(OUTPUT/'source_manifest.json')
    required = ('src/acfqp/science/executable_trajectory_v254.py', 'scripts/run_executable_trajectory_v254.py',
        'scripts/audit_executable_trajectory_v254.py', 'tests/test_executable_trajectory_v254_core.py',
        'tests/test_executable_trajectory_v254_runner.py', 'tests/test_executable_trajectory_v254_audit.py',
        'specs/EXECUTABLE_TRAJECTORY_V254.md')
    check('captured_all_frozen_source_spec_new_core_producer_and_independent_tests', all(name in manifest for name in required))
    for relative in manifest:
        check('captured_frozen_source_bytes_equal_current_audited_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    with ProcessPoolExecutor(max_workers=3) as executor:
        groups = list(executor.map(audit_life, LIVES))
    records, scores, artifacts = [], [], []
    for result in groups:
        records.extend(result['records'])
        scores.extend(result['scores'])
        artifacts.append(result['artifact'])
        checks.update(result['checks'])
        failures.extend(result['failures'])
    independently_summarized = summarize(records, scores, artifacts)
    check('all_108_checkpoint_72_return_pairs_and_actual_full_primitive_source_charges',
          len(records) == len(scores) == 180 and independently_summarized['checkpoint_pairs'] == 108
          and independently_summarized['terminal_pairs'] == 72
          and independently_summarized['physical_observations'] == sum(LIFE_CAPS) == 48384
          and independently_summarized['physical_source_samples'] == 13824)
    check('independent_paired_readiness_critical_gaps_false_certificates_costs_and_signal_summary',
          all(summary[field] == value for field, value in independently_summarized.items())
          and summary['scoring_seconds'] >= 0 and summary['elapsed_seconds'] >= 0
          and summary['worker_wall_seconds'] == {str(item['life']): item['worker_wall_seconds'] for item in artifacts})
    analysis = dict(valid=not failures, records=len(records), checkpoint_pairs=108, terminal_pairs=72,
        physical_observations=independently_summarized['physical_observations'],
        independently_checked_profiles=sum(result['profiles'] for result in groups),
        independently_checked_global_leaves=sum(result['leaves'] for result in groups),
        independently_checked_complete_rounds=sum(item['complete_rounds'] for item in artifacts),
        independently_checked_direct_comparisons=checks['direct_exact_certification_status'],
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun,
        life_elapsed_seconds={result['life']: result['elapsed_seconds'] for result in groups},
        **{field: independently_summarized[field] for field in ('methods', 'paired_checkpoint_groups', 'terminal_paired',
            'fee_ledger', 'positive_qualification_signal', 'qualification_only', 'complete_lifecycle_test', 'scientific_gate_changed')})
    (OUTPUT/'analysis.json').write_text(json.dumps(analysis, default=str, indent=2)+'\n')
    print(json.dumps({key: value for key, value in analysis.items() if key not in ('checks', 'failures')}, default=str), flush=True)
    return analysis


if __name__ == '__main__':
    if not run()['valid']:
        raise SystemExit(1)
