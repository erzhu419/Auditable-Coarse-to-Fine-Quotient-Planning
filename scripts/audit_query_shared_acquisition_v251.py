"""Independent query-preview, shared allocation and full-lifecycle audit.

The producer is not imported. Query-only previews use the retained native A
counts and established independent certificate mathematics, with no execution
or member event. Actual shared observations and released reservations are
replayed chronologically before the unchanged ordinary target audit.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import json
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_query_allocation_lifecycle_v245 as allocation

prior, paid, evidence = allocation.prior, allocation.paid, allocation.evidence
fractions = allocation.fractions
OUTPUT = ROOT/'reports/query_shared_acquisition_v251'
LIVES, TARGETS = (0, 1, 2), prior.TARGETS
ARMS = ('UNIFORM_SHARED', 'QUERY_FIXED', 'QUERY_SHARED')
OPERATORS, ALPHABETS = allocation.OPERATORS, allocation.ALPHABETS
COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 295000, 296000, 297000
LIFE_CAPS, SOURCE_COST, BATCH, CAP = (14144, 17072, 17168), 4608, 16, 384
A_CAP, B_QUOTA, PROBE_CAP = 3072, 1152, 4224
REGRET, THRESHOLD = F(1, 20), 960


def source_replay(rows, check):
    sources, cursor = {}, 0
    for life in LIVES:
        _, laws, _, _ = paid.world(life)
        sources[life] = {}
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            anchors = []
            for local, index in enumerate(indexes):
                slot = local if context == 'A' else local+3
                anchor = paid.empty()
                for j, operator in enumerate(OPERATORS):
                    seed = SOURCE_BASE+(life*6+slot)*3+j
                    generator = random.Random(seed)
                    for offset in range(0, size, BATCH):
                        increments = paid.draw(generator, laws[index], operator)
                        expected = dict(life=life, context=context, index=index, slot=slot,
                            operator=operator, seed=seed, draw_start=offset,
                            draw_end=offset+BATCH, increments=increments)
                        check('fresh_source_actual_batch_and_offset',
                              cursor < len(rows) and rows[cursor] == expected)
                        cursor += 1
                        for category, count in increments.items():
                            anchor[operator][category] += count
                anchors.append(anchor)
            sources[life][context.lower()] = anchors
    check('all_physical_source_batches_once', cursor == len(rows) == 864)
    return sources


def budget_values(life, index, history, probe_paid, released, spent=0):
    """Unspent B quota remains reserved; released A quota becomes available."""
    source = 3456 if index < 30 else SOURCE_COST
    pending = PROBE_CAP-probe_paid-released
    available = LIFE_CAPS[life]-SOURCE_COST-history-probe_paid-pending
    return dict(source_paid=source, available=available, pending_probe=pending,
        released=released, future_source=SOURCE_COST-source,
        reference_paid=source+history+probe_paid+spent,
        adaptive_after=available-spent)


def original_query_choice(shared_by_row, ready_by_type, fixed):
    """Focused unready types; fixed arm uses all-six-row balancing when ready."""
    unresolved = [identity for identity in range(3) if not ready_by_type[identity]]
    if unresolved:
        identity = min(unresolved, key=lambda i: (sum(shared_by_row[i].values()), i))
        operator = min(OPERATORS[:2], key=lambda op: (shared_by_row[identity][op], OPERATORS.index(op)))
        return dict(identity=identity, operator=operator, reason='unresolved_type_balanced_row',
                    unresolved_types=unresolved, all_ready=False)
    if not fixed:
        return None
    identity, operator = min(((i, op) for i in range(3) for op in OPERATORS[:2]),
                            key=lambda pair: (shared_by_row[pair[0]][pair[1]], pair[0], OPERATORS.index(pair[1])))
    return dict(identity=identity, operator=operator, reason='all_ready_balanced_all_rows',
                unresolved_types=[], all_ready=True)


def proof_work(query_evidence, profiles, work, convex_keys):
    """Count every actual comparison, including shared-preview reads."""
    work['online_query_comparison_calls'] += 6
    for query in ('goal', 'risk'):
        for reference in query_evidence['queries'][query]['comparisons']:
            certificate = profiles[reference['profile_id']]['certificate']
            if certificate.get('engine') == 'convex_tangent':
                work['online_convex_certificate_calls'] += 1
                convex_keys.add((certificate['family'], query, certificate['chosen'],
                    certificate['other'], F(certificate['relevant_cost']),
                    prior.freeze(certificate['projected_counts'])))


def audit_preview(saved, identity, cost_index, state, profiles, decisions,
                  used_profiles, work, convex_keys, check):
    """Read one native-A query snapshot without constructing execution regions."""
    point = fractions(saved)
    operating, retry = COSTS[cost_index]
    case = point['case']
    counts = deepcopy(state['a'][identity])
    posterior = paid.posterior(counts)
    selected = paid.point_queries(case, posterior)
    check('query_only_auxiliary_schema_without_member_or_execution_plan', set(saved) == {
        'life', 'arm', 'preview_id', 'identity', 'cost_index', 'after_probe_batch',
        'case', 'evidence_counts', 'posterior', 'pure_vectors', 'queries',
        'query_evidence', 'query_ready'})
    check('auxiliary_public_cost_native_counts_and_original_posterior_selection',
        (case['operating'], F(case['retry_cost'])) == (operating, F(retry))
        and saved['identity'] == identity and saved['cost_index'] == cost_index
        and case['context'] == 'A' and point['evidence_counts'] == counts
        and point['posterior'] == posterior
        and point['pure_vectors'] == prior.joint.vectors(case, posterior)
        and all(point['queries'][query]['policy'] == policy for query, policy in selected.items()))
    query_evidence = point['query_evidence']
    check('auxiliary_analytic_reward_and_original_query_threshold',
        query_evidence['threshold'] == THRESHOLD and query_evidence['queries']['reward']
        == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost'))
    ready = {'reward': True}
    for query in ('goal', 'risk'):
        choice = selected[query]
        record = query_evidence['queries'][query]
        alternatives = [policy for policy in prior.joint.POLICIES if policy != choice]
        check('auxiliary_complete_original_query_alternative_roster',
            record['policy'] == choice
            and [reference['other'] for reference in record['comparisons']] == alternatives)
        certified = []
        for reference, other in zip(record['comparisons'], alternatives):
            profile_id = reference['profile_id']
            used_profiles.add(profile_id)
            result = decisions[profile_id]
            prior.audit_reference(profiles[profile_id], reference, counts, saved['case'],
                                  query, choice, other, result, check)
            certified.append(result)
        ready[query] = all(certified)
        check('auxiliary_three_alternatives_and', len(certified) == 3
              and record['certified'] == ready[query])
    all_ready = all(ready.values())
    check('auxiliary_all_query_stop_mark_matches_original_proofs',
        query_evidence['all_ready'] == point['query_ready'] == all_ready)
    proof_work(query_evidence, profiles, work, convex_keys)
    work['aux_query_previews'] += 1
    return all_ready


def actual_query_scores(saved, law):
    """Posthoc query regret only; there is no auxiliary execution result."""
    point, queries = fractions(saved), {}
    pure = prior.joint.vectors(point['case'], law)
    for query, weights in prior.joint.WEIGHTS.items():
        policy = point['queries'][query]['policy']
        value = prior.joint.utility(pure[policy], weights)
        queries[query] = dict(policy=policy, actual=pure[policy], utility=value,
            regret=max(prior.joint.utility(vector, weights) for vector in pure.values())-value)
    false = sum(point['query_evidence']['queries'][query]['certified']
                and queries[query]['regret'] > REGRET for query in queries)
    return queries, false


def conditions(methods):
    query = methods['QUERY_SHARED']
    result = dict(late_b_quality=query['late_b']['query_certified'] >= 27,
                  a_return_quality=query['a_return']['query_certified'] >= 54)
    for arm in ('QUERY_FIXED', 'UNIFORM_SHARED'):
        name, control = arm.lower(), methods[arm]
        result.update({
            f'matched_{name}_late_b_quality': query['late_b']['query_certified'] >= control['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': query['a_return']['query_certified'] >= control['a_return']['query_certified'],
            f'matched_{name}_joint_quality': query['joint_completed'] >= control['joint_completed']})
    result['actual_acquisition_saving_vs_uniform_shared'] = query['total_samples'] < methods['UNIFORM_SHARED']['total_samples']
    result['actual_acquisition_nondegrading_vs_query_fixed'] = query['total_samples'] <= methods['QUERY_FIXED']['total_samples']
    result['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
        for field in ('false_query_certificates', 'aux_false_query_certificates',
                      'false_execution_certificates', 'false_impossible_certificates',
                      'false_goal_uppers', 'risk_violations', 'executed_risk_violations'))
    return result


def ledger(paid_samples, released=0):
    return dict(cap_samples=PROBE_CAP, paid_samples=paid_samples,
                pending_samples=PROBE_CAP-paid_samples-released, released_samples=released)


def replay_probe(saved, life, arm, context, identity, operator, sequence,
                 state, law, generator, offset, history, probe_paid, released, check):
    """One actual shared batch enters only the corresponding native pool."""
    seed = PROBE_BASE+(life*6+(0 if context == 'A' else 3)+identity)*3+OPERATORS.index(operator)
    increments = paid.draw(generator, law, operator)
    pool = state[context.lower()][identity][operator]
    before = deepcopy(pool)
    for category, count in increments.items():
        pool[category] += count
    record = dict(life=life, arm=arm, context=context, identity=identity,
        source_index=identity if context == 'A' else 27+identity,
        operator=operator, seed=seed, draw_start=offset, draw_end=offset+BATCH,
        increments=increments, trigger_index=3 if context == 'A' else 30,
        timing='before_target', pool_before=before, pool_after=deepcopy(pool),
        probe_sequence=sequence, probe_paid_before=probe_paid, probe_paid_after=probe_paid+BATCH,
        pending_probe_reserved_before=PROBE_CAP-probe_paid-released,
        pending_probe_reserved_after=PROBE_CAP-probe_paid-released-BATCH,
        released_samples_before=released, released_samples_after=released,
        ordinary_history_paid_samples=history,
        source_paid_samples=3456 if context == 'A' else SOURCE_COST)
    check('shared_actual_stream_offset_native_pool_and_paid_pending_released_ledger', saved == record)
    return probe_paid+BATCH


def audit_shared_phase(phase, probes, previews, life, arm, state, laws,
                       profiles, decisions, used_profiles, work, convex_keys, check):
    """Reconstruct every A allocation/preview and release, without optimization."""
    shared = [{operator: 0 for operator in OPERATORS[:2]} for _ in range(3)]
    ready, latest, preview_cursor = [], [], 0
    generators = {(identity, operator): random.Random(PROBE_BASE+(life*6+identity)*3+j)
                  for identity in range(3) for j, operator in enumerate(OPERATORS[:2])}
    is_query = arm != 'UNIFORM_SHARED'

    def preview_type(identity, references, after):
        nonlocal preview_cursor
        expected_ids = list(range(preview_cursor, preview_cursor+4))
        check('auxiliary_four_fixed_cost_preview_ids_in_actual_order', references == expected_ids)
        all_costs = []
        for cost_index in range(4):
            row = previews[preview_cursor]
            check('auxiliary_native_identity_and_actual_after_batch_prefix',
                row['life'] == life and row['arm'] == arm and row['preview_id'] == preview_cursor
                and row['after_probe_batch'] == after)
            all_costs.append(audit_preview(row, identity, cost_index, state, profiles,
                decisions, used_profiles, work, convex_keys, check))
            preview_cursor += 1
        return all(all_costs), expected_ids

    if is_query:
        expected_initial = list(range(12))
        check('initial_full_three_type_four_public_cost_roster', phase['initial_previews'] == expected_initial)
        for identity in range(3):
            current, references = preview_type(identity, expected_initial[identity*4:(identity+1)*4], 0)
            ready.append(current)
            latest.append(references)
    else:
        check('uniform_control_has_no_auxiliary_query_preview', phase['initial_previews'] == [] and previews == [])
    first_ready = 0 if is_query and all(ready) else None
    probe_paid, steps = 0, 0
    for saved in phase['batches']:
        check('A_shared_cap_and_certificate_stop_before_each_actual_batch',
              probe_paid+BATCH <= A_CAP and (arm != 'QUERY_SHARED' or not all(ready)))
        if is_query:
            choice = original_query_choice(shared, ready, arm == 'QUERY_FIXED')
        else:
            identity, j = divmod(steps//32, 2)
            choice = dict(identity=identity, operator=OPERATORS[j], reason='uniform_fixed_allocation',
                          unresolved_types=[], all_ready=None)
        work['shared_acquisition_choices'] += 1
        check('original_focused_type_row_ties_and_fixed_all_ready_continuation',
              saved['batch_index'] == steps+1 and saved['probe_sequence'] == steps+1 and saved['choice'] == choice)
        identity, operator = choice['identity'], choice['operator']
        probe_paid = replay_probe(next(probes), life, arm, 'A', identity, operator, steps+1,
            state, laws[identity], generators[identity, operator], shared[identity][operator],
            0, probe_paid, 0, check)
        shared[identity][operator] += BATCH
        steps += 1
        check('actual_shared_payment_by_native_type_and_operator', saved['paid_by_type_op_after'] == shared)
        if is_query:
            ready[identity], latest[identity] = preview_type(identity, saved['updated_previews'], steps)
            if first_ready is None and all(ready):
                first_ready = probe_paid
        else:
            check('uniform_batches_have_no_updated_query_preview', saved['updated_previews'] == [])
    released = A_CAP-probe_paid
    expected_reason = 'all_ready' if arm == 'QUERY_SHARED' and all(ready) else 'cap'
    check('exact_shared_certificate_stop_or_fixed_A_cap',
        (arm == 'QUERY_SHARED' and (all(ready) or probe_paid == A_CAP)
         or arm != 'QUERY_SHARED' and probe_paid == A_CAP)
        and phase['life'] == life and phase['arm'] == arm and phase['cap_samples'] == A_CAP
        and phase['stop_reason'] == expected_reason and phase['a_paid_samples'] == probe_paid
        and phase['released_delta'] == released and phase['first_all_ready_paid'] == first_ready
        and phase['final_ready_by_type'] == ready and phase['latest_preview_ids'] == latest)
    check('phase_exit_releases_only_unused_A_keeps_B_reserved',
        phase['ledger_before_release'] == ledger(probe_paid)
        and phase['ledger_after_release'] == ledger(probe_paid, released)
        and ledger(probe_paid, released)['pending_samples'] == B_QUOTA
        and preview_cursor == len(previews))
    return probe_paid, released


def replay_fixed_b(probes, life, arm, state, laws, interface, history, probe_paid, released, check):
    operator = interface['changed_operator']
    sequence = probe_paid//BATCH+1
    for identity in range(3):
        seed = PROBE_BASE+(life*6+3+identity)*3+OPERATORS.index(operator)
        generator = random.Random(seed)
        for offset in range(0, 384, BATCH):
            probe_paid = replay_probe(next(probes), life, arm, 'B', identity, operator, sequence,
                state, laws[27+identity], generator, offset, history, probe_paid, released, check)
            sequence += 1
    return probe_paid


def audit_life_arm(arguments):
    life, arm, sources, cases_saved, interface_saved, state_saved, profile_total = arguments
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    cases, laws, identities, interface = paid.world(life)
    check('predeclared_public_world_and_interface', cases_saved == cases
          and interface_saved == dict(life=life, identities=identities, metadata=interface))
    name = f'life_{life:02d}_{arm}'
    profiles = evidence.read_rows(OUTPUT/f'profiles_{name}.jsonl.gz')
    check('complete_local_profile_numbering',
          [row['profile_id'] for row in profiles] == list(range(len(profiles))))
    profile_decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, arm=arm, profile_id=profile['profile_id'])
        profile_decisions[profile['profile_id']] = prior.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    state = dict(a=deepcopy(sources['a']), b=None, a_switch=None)
    projection_cache, used_profiles, convex_keys = {}, set(), set()
    results = evidence.read_rows(OUTPUT/f'results_{name}.jsonl.gz')
    records = evidence.read_rows(OUTPUT/f'records_{name}.jsonl.gz')
    probes_saved = [json.loads(line) for line in (OUTPUT/f'probes_{name}.jsonl').read_text().splitlines()]
    probes = iter(probes_saved)
    phase = evidence.load(OUTPUT/f'a_phase_{name}.json')
    previews = evidence.read_rows(OUTPUT/f'previews_{name}.jsonl.gz')
    preview_results = evidence.read_rows(OUTPUT/f'preview_results_{name}.jsonl.gz')
    history, probe_paid, released, plans, projections = 0, 0, 0, 0, 0
    observations, acquisitions, work, scored, seen = 0., 0., Counter(), [], set()
    check('complete_fresh_full_lifecycle_records_and_results', len(records) == len(results) == 72)
    for position, index in enumerate(TARGETS):
        location = dict(life=life, arm=arm, index=index)
        if index == 30:
            state['a_switch'], state['b'] = deepcopy(state['a']), deepcopy(sources['b'])
        if index == 3:
            probe_paid, released = audit_shared_phase(phase, probes, previews, life, arm, state, laws,
                profiles, profile_decisions, used_profiles, work, convex_keys, check)
        if index == 30:
            probe_paid = replay_fixed_b(probes, life, arm, state, laws, interface,
                                        history, probe_paid, released, check)
        row, case, identity = records[position], cases[index], identities[index]
        seen.add((life, index, arm))
        context, pool_arm = case['context'].lower(), 'ONE_WAY'
        pool = state[context][identity]
        check('chronological_target_native_pool_before_and_public_case',
              (row['life'], row['index'], row['arm']) == (life, index, arm)
              and row['case'] == case
              and row['identity'] == identity and row['pooled_before'] == pool
              and (context != 'b' or state['a'] == state['a_switch']))
        check('nonnegative_model_acquisition_observation_and_output_times',
              all(row[field] >= 0 for field in ('model_seconds', 'acquisition_seconds', 'observation_seconds', 'output_seconds'))
              and row['acquisition_seconds'] <= row['model_seconds'])
        observations += row['observation_seconds']
        acquisitions += row['acquisition_seconds']
        seeds = {operator: TARGET_BASE+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
        check('fresh_paired_target_seed_independent_from_probe_streams', row['seeds'] == seeds)
        generators = {operator: random.Random(seed) for operator, seed in seeds.items()}
        member, spent = paid.empty(), 0
        budget = budget_values(life, index, history, probe_paid, released)
        available = budget['available']

        def plan_check(saved):
            nonlocal plans, projections
            counts = prior.evidence_counts(state, case, identity, pool_arm, interface)
            constraints = prior.execution_constraints(life, index, case, identity,
                sources, state, member, pool_arm, interface)
            previous = checks['terminal_projected_detour_box']
            prior.audit_plan(saved, case, counts, constraints, profiles, profile_decisions,
                             projection_cache, used_profiles, check)
            check('same_native_query_stream_without_B_return_import', saved['return_transfer'] is None)
            projections += checks['terminal_projected_detour_box']-previous
            plans += 1
            work['online_query_comparison_calls'] += 6
            for query in ('goal', 'risk'):
                for reference in saved['query_evidence']['queries'][query]['comparisons']:
                    certificate = profiles[reference['profile_id']]['certificate']
                    if certificate.get('engine') == 'convex_tangent':
                        work['online_convex_certificate_calls'] += 1
                        convex_keys.add((certificate['family'], query, certificate['chosen'],
                            certificate['other'], F(certificate['relevant_cost']),
                            prior.freeze(certificate['projected_counts'])))

        current = row['initial_plan']
        plan_check(current)
        for batch in row['batches']:
            check('joint_stop_member_cap_and_full_source_probe_reservation',
                  spent+BATCH <= min(CAP, available) and not prior.ready(current))
            choice = allocation.original_choice(member, current)
            work['oracle_gap_direct_choices'] += 1
            check('unchanged_exact_V231_allocation_all_fields', fractions(batch['choice']) == choice)
            operator, offset = choice['operator'], sum(member[choice['operator']].values())
            increments = paid.draw(generators[operator], laws[index], operator)
            check('actual_target_outcomes_own_offsets_and_paid_prefix', batch['operator'] == operator
                  and batch['draw_start'] == offset and batch['draw_end'] == offset+BATCH
                  and batch['increments'] == increments)
            for category, count in increments.items():
                member[operator][category] += count
                pool[operator][category] += count
            spent += BATCH
            check('ordinary_current_target_paid_batch_total', batch['spent'] == spent)
            current = batch['plan']
            plan_check(current)
        terminal, completed = row['terminal_plan'], prior.ready(current)
        check('frozen_terminal_is_last_plan_and_exact_stop',
              terminal == current and prior.terminal_stop(spent, available, terminal))
        expected_mix = fractions(terminal['mix']) if completed else [['WAIT', F(1)]]
        check('terminal_member_pool_and_decisions_before_deferred_probe', row['member'] == member
              and row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == spent == paid.samples(member)
              and row['pooled_after'] == pool and row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
              and row['goal_impossible'] == terminal['goal_impossible'] and row['query_certified'] == terminal['query_ready']
              and row['joint_completed'] == completed and row['fallback'] == (not completed)
              and fractions(row['executed_mix']) == expected_mix)
        check('separate_actual_probe_payment_and_future_reserved_samples',
              row['source_paid_samples'] == budget['source_paid']
              and row['history_paid_samples'] == row['ordinary_history_paid_samples'] == history
              and row['actual_probe_paid_before'] == probe_paid
              and row['pending_probe_reserved'] == budget['pending_probe']
              and row['future_B_source_reserved'] == budget['future_source']
              and row['probe_cap_samples'] == PROBE_CAP
              and row['probe_quota_samples'] == PROBE_CAP
              and row['released_probe_samples'] == released
              and row['total_reference_paid_samples'] == budget['reference_paid']+spent
              and row['life_budget_remaining_before'] == available
              and row['life_budget_remaining_after'] == available-spent
              and row['budget_exhausted'] == (available-spent < BATCH)
              and row['member_cap_exhausted'] == (spent == CAP)
              and 0 <= spent <= min(CAP, available) and spent % BATCH == 0)
        independent = prior.score_history(row, laws[index])
        independent.update(identity=identity)
        check('posthoc_truth_scores_all_original_frozen_plans', fractions(results[position]) == independent)
        scored.append(independent)
        history += spent
        print(f'audit life={life} arm={arm} target={index} target_paid={spent} probe_paid={probe_paid}', flush=True)
    check('all_fixed_probe_batches_paid_once_and_no_extra_probe', next(probes, None) is None
          and len(probes_saved)*BATCH == probe_paid and probe_paid+released == PROBE_CAP)
    check('all_profiles_referenced_and_complete_local_cohort', len(seen) == 72
          and used_profiles == set(range(len(profiles))) and profile_total == len(profiles))
    check('final_native_banks_sources_switch_and_own_arm', state_saved == dict(
        life=life, arm=pool_arm, a=dict(sources=sources['a'], pools=state['a']),
        b=dict(sources=sources['b'], pools=state['b']),
        a_at_switch=dict(sources=sources['a'], pools=state['a_switch']),
        changed_operator=interface['changed_operator'], b_to_a=interface['b_to_a'], return_merge=None))
    check('whole_lifecycle_actual_cost_respects_full_budget', SOURCE_COST+history+probe_paid <= LIFE_CAPS[life])
    auxiliary = []
    for preview in previews:
        queries, false = actual_query_scores(preview, laws[preview['identity']])
        result = {field: preview[field] for field in ('life', 'arm', 'preview_id', 'identity',
                                                     'cost_index', 'after_probe_batch', 'case')}
        result.update(queries=queries,
            certified_by_query={query: preview['query_evidence']['queries'][query]['certified']
                                for query in queries}, false_aux_query_certificates=false)
        auxiliary.append(result)
    check('all_auxiliary_posthoc_actual_query_scores_without_execution', fractions(preview_results) == fractions(auxiliary))
    work['online_convex_proposal_calls'] = len(convex_keys)
    work['online_convex_certificate_cache_hits'] = work['online_convex_certificate_calls']-len(convex_keys)
    return dict(life=life, arm=arm, checks=checks, failures=failures, scored=scored,
        ordinary_paid=history, probe_paid=probe_paid, released=released, phase=phase,
        previews=previews, auxiliary=auxiliary, probe_batches=probes_saved,
        observations=observations, acquisitions=acquisitions, work=work,
        profiles=len(profiles), leaves=leaves, plans=plans, projections=projections,
        elapsed_seconds=perf_counter()-begun)


def split_return(rows):
    first, later, seen = [], [], set()
    for row in sorted(rows, key=lambda item: (item['life'], item['index'])):
        key = (row['life'], row['identity'])
        (later if key in seen else first).append(row)
        seen.add(key)
    return first, later


def summaries(rows, timings, ledgers, auxiliary):
    scopes = ('planning', 'initialization', 'begin_b', 'probe_pool_updates',
              'query_previews', 'shared_acquisition')
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        own_auxiliary = [row for row in auxiliary if row['arm'] == arm]
        own_ledgers = [row for row in ledgers if row['arm'] == arm]
        probe_samples = sum(row['paid_samples'] for row in own_ledgers)
        returns = [row for row in selected if row['stage'] == 'A_RETURN']
        first, later = split_return(returns)
        methods[arm] = dict(prior.aggregate(selected), source_samples=13824,
            probe_samples=probe_samples,
            a_shared_samples=sum(row['by_context']['A'] for row in own_ledgers),
            b_fixed_samples=sum(row['by_context']['B'] for row in own_ledgers),
            released_probe_samples=sum(row['released_samples'] for row in own_ledgers),
            total_samples=13824+probe_samples+sum(row['spent'] for row in selected),
            aux_preview_records=len(own_auxiliary),
            aux_false_query_certificates=sum(row['false_aux_query_certificates'] for row in own_auxiliary),
            late_b=prior.aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=prior.aggregate(returns), first_return=prior.aggregate(first), later_return=prior.aggregate(later))
        for scope in scopes+('acquisition',):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        methods[arm]['model_seconds'] = sum(timings[scope][arm][str(life)] for scope in scopes for life in LIVES)
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            current = next(row for row in own_ledgers if row['life'] == life)
            own_auxiliary_life = [row for row in own_auxiliary if row['life'] == life]
            first, later = split_return([row for row in subset if row['stage'] == 'A_RETURN'])
            total = SOURCE_COST+current['paid_samples']+sum(row['spent'] for row in subset)
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                probe_samples=current['paid_samples'], a_shared_samples=current['by_context']['A'],
                b_fixed_samples=current['by_context']['B'], released_probe_samples=current['released_samples'],
                total_samples=total, budget_valid=total <= LIFE_CAPS[life],
                aux_preview_records=len(own_auxiliary_life),
                aux_false_query_certificates=sum(row['false_aux_query_certificates'] for row in own_auxiliary_life),
                model_seconds=sum(timings[scope][arm][str(life)] for scope in scopes),
                stages={stage: prior.aggregate([row for row in subset if row['stage'] == stage])
                        for stage in ('A', 'B', 'A_RETURN')},
                first_return=prior.aggregate(first), later_return=prior.aggregate(later)))
    paired = []
    for life in LIVES:
        selected = {row['arm']: row for row in life_summaries if row['life'] == life}
        uniform, fixed, query = (selected[arm] for arm in ARMS)
        paired.append(dict(life=life,
            query_fixed_minus_uniform_shared_samples=fixed['total_samples']-uniform['total_samples'],
            query_shared_minus_query_fixed_samples=query['total_samples']-fixed['total_samples'],
            return_query_shared_minus_query_fixed_query_certified=query['stages']['A_RETURN']['query_certified']-fixed['stages']['A_RETURN']['query_certified'],
            return_query_fixed_minus_uniform_shared_query_certified=fixed['stages']['A_RETURN']['query_certified']-uniform['stages']['A_RETURN']['query_certified']))
    return methods, life_summaries, conditions(methods), paired


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=dict(scope='cohort')))

    read = lambda name: evidence.load(OUTPUT/name)
    metadata, summary = read('run.json'), read('summary.json')
    prerequisite = ROOT/'reports/acquisition_schedule_search_v250'
    check('complete_valid_frozen_finite_search_prerequisite',
        evidence.load(prerequisite/'run.json')['complete'] and evidence.load(prerequisite/'analysis.json')['valid'])
    check('frozen_fresh_full_lifecycle_and_all_target_auxiliary_truth_freeze', metadata['complete']
        and metadata['lives'] == list(LIVES) and metadata['arms'] == list(ARMS)
        and metadata['targets_per_life'] == 72 and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['source_seed_base'] == SOURCE_BASE and metadata['target_seed_base'] == TARGET_BASE
        and metadata['probe_seed_base'] == PROBE_BASE
        and metadata['per_life_total_budgets'] == list(LIFE_CAPS)
        and metadata['source_samples_per_life'] == SOURCE_COST
        and metadata['query_stream_count'] == 48 and metadata['query_threshold'] == THRESHOLD
        and metadata['query_delta_per_life_arm'] == metadata['execution_delta_per_life_arm'] == '1/20'
        and metadata['combined_delta_upper'] == '1/10' and not metadata['scientific_gate_changed']
        and metadata['qualification_only'] and metadata['pool_core_arm'] == 'ONE_WAY'
        and metadata['prerequisites'] == dict(v250_complete=True, v250_independent_valid=True)
        and metadata['phases'] == ['protocol_frozen', 'all_decisions_and_previews_frozen', 'oracle_evaluated', 'complete']
        and metadata['execution'] == dict(independent_life_arm_processes=9, max_workers=9,
            posthoc_scoring='after_all_648_decisions_and_all_previews_frozen')
        and metadata['worker_jobs'] == [dict(life=life, arm=arm) for life in LIVES for arm in ARMS]
        and metadata['model_seconds_clock'] == 'process_time'
        and metadata['observation_output_scoring_seconds_clock'] == 'perf_counter')
    check('unconditional_complete_life_arm_confidence_scope_and_declared_information',
        metadata['delta_scope'] == 'unconditional_complete_life_arm_process'
        and metadata['oracle_information'] == ['type identity', 'B changed operator', 'B-to-A correspondence'])
    check('single_A_query_only_phase_frozen_caps_costs_and_fixed_B_visibility',
        metadata['shared_cap_samples'] == PROBE_CAP
        and metadata['a_shared_cap_samples'] == A_CAP and metadata['b_fixed_samples'] == B_QUOTA
        and metadata['public_preview_costs'] == [list(cost) for cost in COSTS]
        and metadata['probe_timing'] == dict(A='before_target3', B='after_begin_b_before_target30'))
    check('original_anytime_event_budget_without_preview_or_member_reset', F(48, THRESHOLD) == REGRET
          and F(216, 8640)+F(9, 720)+F(9, 720) == REGRET and 2*REGRET == F(1, 10))
    check('isolated_per_life_arm_computation_cache_scope', metadata['computation_cache_scope']
          == summary['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE)
    captured = read('source_manifest.json')
    check('captured_new_runner_auditor_tests_and_fixed_query_protocol', all(relative in captured for relative in (
        'scripts/run_query_shared_acquisition_v251.py', 'scripts/audit_query_shared_acquisition_v251.py',
        'tests/test_query_shared_acquisition_v251_runner.py', 'tests/test_query_shared_acquisition_v251_audit.py',
        'specs/QUERY_SHARED_ACQUISITION_V251.md')))
    for relative in captured:
        check('captured_source_matches_current_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = source_replay(read('source_records.json'), check)
    check('all_fresh_physical_sources_once_admitted_by_correct_context', read('source_evidence.json')
          == [dict(life=life, **sources[life]) for life in LIVES])
    check('physical_source_environment_work_counted_once',
        all(summary['source_work'][field] == 13824
            for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws')))
    cases = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    states = {(row['life'], row['arm']): row['state'] for row in read('final_states.json')}
    arguments = [(life, arm, sources[life], cases[life], interfaces[life], states[life, arm],
                  summary['profiles'][arm][str(life)]) for life in LIVES for arm in ARMS]
    with ProcessPoolExecutor(max_workers=9) as executor:
        jobs = list(executor.map(audit_life_arm, arguments))
    for job in jobs:
        checks.update(job['checks'])
        failures.extend(job['failures'])
    scored = [row for job in jobs for row in job['scored']]
    auxiliary = [row for job in jobs for row in job['auxiliary']]
    ledgers = []
    for job in jobs:
        ledgers.append(dict(life=job['life'], arm=job['arm'], cap_samples=PROBE_CAP,
            paid_samples=job['probe_paid'], pending_reserved_samples=0, released_samples=job['released'],
            probe_batches=len(job['probe_batches']),
            by_context=dict(A=job['probe_paid']-B_QUOTA, B=B_QUOTA)))
    methods, life_summaries, science_conditions, paired = summaries(scored, summary['timings'], ledgers, auxiliary)
    probe_samples, ordinary_samples = sum(job['probe_paid'] for job in jobs), sum(row['spent'] for row in scored)
    check('complete_648_targets_all_auxiliary_scores_11_conditions_and_actual_fees',
        summary['complete'] and summary['records'] == len(scored) == 648
        and summary['aux_preview_records'] == len(auxiliary)
        and summary['methods'] == methods and summary['life_summaries'] == life_summaries
        and summary['paired'] == paired and summary['conditions'] == science_conditions
        and len(science_conditions) == 11 and summary['stage_condition_met'] == all(science_conditions.values())
        and summary['qualification_only'] and not summary['scientific_gate_changed']
        and summary['physical_source_samples'] == summary['source_samples_charged_per_arm'] == 13824
        and summary['physical_probe_samples'] == probe_samples
        and summary['new_environment_observations'] == 13824+probe_samples+ordinary_samples
        and summary['risk_violation_scope'] == 'all_retained_plans'
        and summary['validity_scope'] == 'all_retained_plans_and_auxiliary_query_previews')
    check('complete_actual_paid_pending_released_ledgers', read('probe_ledgers.json') == summary['probe_ledgers'] == ledgers)
    phase_summaries = [dict(life=job['life'], arm=job['arm'], **{key: job['phase'][key]
        for key in ('a_paid_samples', 'released_delta', 'stop_reason', 'final_ready_by_type', 'first_all_ready_paid')})
        for job in jobs]
    check('exact_all_A_phase_exit_summaries_and_preview_counts',
        read('a_phase_summaries.json') == summary['a_phase_summaries'] == phase_summaries
        and summary['previews'] == {arm: {str(job['life']): len(job['previews'])
            for job in jobs if job['arm'] == arm} for arm in ARMS})
    check('model_subtimings_include_auxiliary_queries_and_shared_selection',
        summary['model_seconds_scope'] == 'summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_begin_b_probe_pool_updates_query_previews_and_shared_acquisition'
        and summary['acquisition_seconds_scope'] == 'full_choose_process_CPU_subset_of_planning_model_time'
        and summary['output_seconds_scope'] == 'summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary'
        and summary['life_arm_wall_seconds_scope'] == 'worker_entry_through_all_decisions_probes_and_previews_retained_before_artifact_write')
    for life in LIVES:
        potential_prefix = {}
        for job in (job for job in jobs if job['life'] == life):
            for row in job['probe_batches']:
                key = (row['context'], row['identity'], row['operator'], row['draw_start'])
                value = (row['seed'], row['draw_end'], row['increments'])
                check('paired_potential_shared_prefixes_actual_distinct_arm_payments',
                      key not in potential_prefix or potential_prefix[key] == value)
                potential_prefix[key] = value
        fixed, query = (next(job for job in jobs if job['life'] == life and job['arm'] == arm)
                        for arm in ('QUERY_FIXED', 'QUERY_SHARED'))
        prefix_count = len(query['phase']['batches'])
        check('query_methods_same_allocation_and_outcomes_through_shared_stop',
            fixed['phase']['initial_previews'] == query['phase']['initial_previews']
            and fixed['phase']['batches'][:prefix_count] == query['phase']['batches']
            and fixed['previews'][:len(query['previews'])] == [dict(row, arm='QUERY_FIXED') for row in query['previews']])
    for arm in ARMS:
        method, own_jobs = methods[arm], [job for job in jobs if job['arm'] == arm]
        expected_work = sum((job['work'] for job in own_jobs), Counter())
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_target_and_shared_environment_work', summary['work'][arm][field]
                  == method['target_samples']+method['probe_samples'])
        for field in ('oracle_gap_direct_choices', 'online_query_comparison_calls', 'online_convex_certificate_calls',
                      'online_convex_proposal_calls', 'online_convex_certificate_cache_hits'):
            check('original_and_auxiliary_proof_work_without_optimizer_audit', summary['work'][arm].get(field, 0) == expected_work[field])
        check('actual_shared_batches_samples_and_preview_roster_work',
            summary['work'][arm].get('shared_probe_batches', 0) == method['probe_samples']//BATCH
            and summary['work'][arm].get('shared_probe_samples', 0) == method['probe_samples']
            and summary['work'][arm].get('aux_query_previews', 0) == method['aux_preview_records']
            and summary['work'][arm].get('shared_acquisition_choices', 0) == expected_work['shared_acquisition_choices'])
        for job in own_jobs:
            life = str(job['life'])
            check('ordinary_cpu_acquisition_and_observation_actual_sums',
                summary['timings']['planning'][arm][life] == sum(row['model_seconds'] for row in job['scored'])
                and summary['timings']['acquisition'][arm][life] == job['acquisitions']
                and summary['timings']['observation'][arm][life] == job['observations'])
            for scope in ('initialization', 'begin_b', 'probe_pool_updates', 'probe_draw', 'query_previews', 'shared_acquisition'):
                check('nonnegative_model_query_selection_and_shared_observation_cpu', summary['timings'][scope][arm][life] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][arm][life][name]
                check('per_job_normalizer_cache_statistics', stats['maxsize'] == capacity
                      and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    result = dict(valid=not failures, complete=True, records=len(scored), auxiliary_previews=len(auxiliary),
        probe_batches=sum(len(job['probe_batches']) for job in jobs),
        plans=sum(job['plans'] for job in jobs), independently_checked_profiles=sum(job['profiles'] for job in jobs),
        independently_checked_global_leaves=sum(job['leaves'] for job in jobs),
        independently_checked_execution_projections=sum(job['projections'] for job in jobs),
        methods=methods, conditions=science_conditions, stage_condition_met=all(science_conditions.values()),
        physical_source_samples=13824, physical_probe_samples=probe_samples,
        physical_observations=13824+ordinary_samples+probe_samples,
        risk_violation_scope='all_retained_plans',
        validity_scope='all_retained_plans_and_auxiliary_query_previews', qualification_only=True,
        binary_projection_comparison_tolerance=0, independent_life_arm_processes=9,
        life_arm_elapsed_seconds={f'{job["life"]}/{job["arm"]}': job['elapsed_seconds'] for job in jobs},
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
