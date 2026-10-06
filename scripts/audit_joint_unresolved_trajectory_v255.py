"""Independent filtered-cyclic acquisition and direct-trajectory audit.

Only the established independent V254 score arithmetic is reused. Every arm's
own primitive calls, current certificate checks, stopping and charges are
replayed; unchanged actual-prefix proofs are compared exactly after one audit.
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
from scripts import audit_executable_trajectory_v254 as mathematics

OUTPUT = ROOT/'reports/joint_unresolved_trajectory_v255'
LIVES, ARMS = (0, 1, 2), ('DIRECT_RR', 'DIRECT_JOINT_UNRESOLVED')
CAPS, SOURCE_COST, MID_COST, BATCH = (14144, 17072, 17168), 4608, 7680, 256
SOURCE_BASE, ACQUISITION_BASE = 301000, 302000
OPERATORS, ALPHABETS = mathematics.OPERATORS, mathematics.ALPHABETS
POLICIES, QUERIES = mathematics.POLICIES, ('reward', 'goal', 'risk')
S, D, R = OPERATORS
COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
LABELS = ('SOURCE', 'SOURCE_PLUS_3072', 'FULL_CAP')
load, exact = mathematics.load, mathematics.exact
rows = mathematics.trajectory.read_rows


def choose_type(cursor, eligible):
    return next((cursor+offset)%3 for offset in range(3) if (cursor+offset)%3 in eligible)


def acquisition_end(paid, cap):
    return min(paid+BATCH, MID_COST if paid < MID_COST else cap, cap)


def current_ready_by_type(check_records):
    return [all(record['trajectory']['all_ready'] for record in check_records if record['identity'] == identity)
            for identity in range(3)]


def audit_direct_evidence(identity, rounds, case, chosen, saved, proof_cache, check):
    # The surrounding replay appends immutable rounds to this own worker/type.
    # A fixed identity and prefix length therefore denote the full actual tape.
    key = identity, len(rounds), case['operating'], F(case['retry_cost']), tuple(chosen[query] for query in QUERIES)
    if key in proof_cache:
        original, ready = proof_cache[key]
        check('same_actual_prefix_cost_and_direction_reuses_exact_audited_direct_proof', saved == original)
        return ready
    ready = mathematics.audit_trajectory_certificate(rounds, case, chosen, saved, check)
    proof_cache[key] = deepcopy(saved), ready
    return ready


def independent_score(record, laws):
    queries = mathematics.score_queries(record['queries'], record['case'], laws[record['identity']])
    return queries, sum(decision['certified'] and queries[query]['regret'] > F(1, 20)
                        for query, decision in record['trajectory']['queries'].items())


def case_for(life, arm, identity, cost_index):
    operating, retry = COSTS[cost_index]
    return dict(id=f'v255_l{life:02d}_{arm}_t{identity}_c{cost_index}', operating=operating,
                retry_cost=retry, context='A', stage='QUERY_QUALIFICATION')


def public_roster():
    result = []
    for life in LIVES:
        cases, _, identities, _ = mathematics.trajectory.world(life)
        for arm in ARMS:
            for label, cap in zip(LABELS, (SOURCE_COST, MID_COST, CAPS[life])):
                for identity in range(3):
                    for cost_index in range(4):
                        result.append(dict(life=life, arm=arm, kind='CHECKPOINT', checkpoint_label=label,
                            checkpoint_samples=cap, identity=identity, cost_index=cost_index,
                            case=case_for(life, arm, identity, cost_index), index=None))
            for index in range(54, 78):
                case = deepcopy(cases[index])
                result.append(dict(life=life, arm=arm, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP',
                    checkpoint_samples=CAPS[life], identity=identities[index],
                    cost_index=COSTS.index((case['operating'], str(case['retry_cost']))), case=case, index=index))
    return result


def initial_state(life):
    generators = {(phase, identity, operator): random.Random(base+(life*3+identity)*3+j)
        for phase, base in (('SOURCE', SOURCE_BASE), ('ACQUISITION', ACQUISITION_BASE))
        for identity in range(3) for j, operator in enumerate(OPERATORS)}
    return dict(step=0, cursor=0, round_id=0, round_position=0, phase_steps=Counter(), offsets=Counter(),
        generators=generators, native=[mathematics.row_math.empty() for _ in range(3)],
        complete=[[] for _ in range(3)], tails=[0]*3, last_ids=[None]*3, acquisition_paid_by_type=[0]*3)


def replay_batch(life, arm, batch_id, target, eligible, state, tape, round_records, laws, check):
    phase = 'SOURCE' if batch_id == 0 else 'ACQUISITION'
    base = SOURCE_BASE if batch_id == 0 else ACQUISITION_BASE
    before_step, before_cursor, before_rounds, before_tails = (state['step'], state['cursor'], state['round_id'], sum(state['tails']))
    while state['step'] < target:
        selection_cursor = state['cursor']
        identity = choose_type(selection_cursor, eligible)
        state['cursor'] = identity+1
        tail = target-state['step'] < 3
        round_id = None if tail else state['round_id']+1
        observations, steps, start = dict.fromkeys(OPERATORS), [], state['step']+1

        def draw(operator, role):
            key = phase, identity, operator
            offset = state['offsets'][key]
            outcome = mathematics.trajectory._draw(state['generators'][key], laws[identity], operator, 1)[0]
            expected = dict(life=life, arm=arm, phase=phase, batch_id=batch_id, step_index=state['step']+1,
                identity=identity, operator=operator, round_id=round_id, role=role, cursor_before=selection_cursor,
                seed=base+(life*3+identity)*3+OPERATORS.index(operator), draw_start=offset, draw_end=offset+1,
                outcome=outcome, phase_step_index=state['phase_steps'][phase]+1)
            check('own_actual_primitive_seed_continuous_offset_filtered_cursor_and_conditional_path', tape[state['step']] == expected)
            state['step'] += 1
            state['phase_steps'][phase] += 1
            state['offsets'][key] += 1
            state['native'][identity][operator][outcome] += 1
            if phase == 'ACQUISITION':
                state['acquisition_paid_by_type'][identity] += 1
            observations[operator] = outcome
            steps.append(state['step'])

        draw(S, 'tail_S' if tail else 'S')
        if tail:
            state['tails'][identity] += 1
        else:
            draw(D, 'D')
            if observations[D] == 'RECOVERY':
                draw(R, 'R')
            state['round_id'] += 1
            expected = dict(life=life, arm=arm, round_id=state['round_id'], phase=phase, batch_id=batch_id,
                identity=identity, primitive_steps=steps, outcomes=observations, start_step=start, end_step=state['step'])
            check('complete_conditional_round_actual_primitive_refs_no_tail_or_offpath_R',
                  round_records[state['round_position']] == expected)
            state['round_position'] += 1
            state['complete'][identity].append(observations)
            state['last_ids'][identity] = state['round_id']
    return dict(life=life, arm=arm, phase=phase, batch_id=batch_id, eligible_types_frozen=list(eligible),
        start_step=before_step, end_step=state['step'], actual_samples=state['step']-before_step, target_step=target,
        cursor_before=before_cursor, cursor_after=state['cursor'], complete_rounds=state['round_id']-before_rounds,
        standalone_S_tails=sum(state['tails'])-before_tails, acquisition_paid_by_type=list(state['acquisition_paid_by_type']),
        prior_check_id=None if batch_id == 0 else batch_id-1)


def audit_check(life, arm, check_id, records, state, proof_cache, point_cache, score_keys, check):
    check('all12_current_cost_type_checks_in_literal_order', len(records) == 12
          and [(row['identity'], row['cost_index']) for row in records] == [(identity, cost) for identity in range(3) for cost in range(4)])
    histograms = [mathematics.joint_histogram(complete) for complete in state['complete']]
    prefixes = [tuple(tuple(observation[operator] for operator in OPERATORS) for observation in complete)
                for complete in state['complete']]
    for record in records:
        identity, cost_index = record['identity'], record['cost_index']
        case, native, complete = case_for(life, arm, identity, cost_index), state['native'][identity], state['complete'][identity]
        point_key = identity, len(complete), case['operating'], F(case['retry_cost'])
        if point_key not in point_cache:
            point_cache[point_key] = mathematics.empirical_vectors(complete, case)
        vectors = point_cache[point_key]
        chosen = mathematics.point_queries(vectors)
        check('current_check_own_native_prefix_joint_rounds_tails_fees_and_shared_choices',
            record['life'] == life and record['arm'] == arm and record['kind'] == 'INTERMEDIATE_CHECK'
            and record['check_id'] == check_id and record['index'] is None and record['case'] == case
            and record['native_counts'] == native and record['complete_rounds'] == len(complete)
            and record['joint_outcome_counts'] == histograms[identity]
            and record['native_n_by_operator'] == {operator: sum(row.values()) for operator, row in native.items()}
            and record['tail_s_samples'] == state['tails'][identity] and record['round_prefix_last_id'] == state['last_ids'][identity]
            and record['source_paid_samples'] == SOURCE_COST and record['acquisition_paid_samples'] == state['step']-SOURCE_COST
            and record['total_paid_samples'] == state['step'] and exact(record['pure_vectors']) == vectors
            and record['queries'] == {query: dict(policy=policy) for query, policy in chosen.items()})
        ready = audit_direct_evidence(identity, complete, case, chosen, record['trajectory'], proof_cache, check)
        check('current_three_query_ready_not_latched_from_earlier_check', record['trajectory']['all_ready'] == all(ready.values()))
        check('actual_check_point_and_direct_proof_CPU_nonnegative', set(record['model_seconds']) == {'point_vectors', 'trajectory'}
              and all(value >= 0 for value in record['model_seconds'].values()))
        prefix = prefixes[identity]
        for query in ('goal', 'risk'):
            for comparison in record['trajectory']['queries'][query]['comparisons']:
                retry = F(case['retry_cost']) if 'DETOUR_RETRY' in (comparison['chosen'], comparison['other']) else None
                score_keys[query, comparison['chosen'], comparison['other'], retry, prefix] = len(complete)
    readiness = current_ready_by_type(records)
    return dict(life=life, arm=arm, check_id=check_id, primitive_samples=state['step'], source_paid_samples=SOURCE_COST,
        acquisition_paid_samples=state['step']-SOURCE_COST, acquisition_paid_by_type=list(state['acquisition_paid_by_type']),
        cursor=state['cursor'], round_id=state['round_id'], ready_by_type=readiness, all_ready=all(readiness),
        case_refs=[dict(check_id=check_id, identity=row['identity'], cost_index=row['cost_index']) for row in records])


def project(original, public_case):
    result = deepcopy(original)
    result.update(deepcopy(public_case), selected_check_id=original['check_id'],
        checkpoint_reached=original['total_paid_samples'] >= public_case['checkpoint_samples'],
        model_seconds=dict(point_vectors=0., trajectory=0.))
    return result


def score_rows(records, saved_scores, laws, check):
    independent = []
    for record in records:
        queries, false_certificates = independent_score(record, laws)
        independent.append(dict(**{field: record[field] for field in ('life', 'arm', 'kind', 'identity', 'cost_index', 'index', 'case')},
            check_id=record['check_id'], queries=queries, false_certificates=false_certificates))
    check('normalized_postfreeze_truth_queries_and_all_false_certificate_counts', mathematics.posthoc_scores_equal(saved_scores, independent))
    return independent


def audit_life_arm(job):
    life, arm = job
    begun, counts, failures, location = perf_counter(), Counter(), [], dict(life=life, arm=arm)

    def check(name, condition):
        counts[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    read = lambda kind: rows(OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz')
    tape, round_records, batches, check_records, metadata, records = (read(kind)
        for kind in ('tapes', 'rounds', 'batches', 'checks', 'check_meta', 'records'))
    _, laws, _, _ = mathematics.trajectory.world(life)
    state, current, selected, proof_cache, point_cache, score_keys = initial_state(life), None, {}, {}, {}, {}
    check('one_source_and_all_batch_end_check_frames_retained', len(metadata) == len(batches)
          and len(check_records) == len(batches)*12)
    for batch_id, saved_batch in enumerate(batches):
        location = dict(life=life, arm=arm, batch_id=batch_id)
        if current is None:
            eligible, target = [0, 1, 2], SOURCE_COST
        else:
            check('no_acquisition_after_all12_current_ready_or_full_cap', not current['all_ready'] and state['step'] < CAPS[life])
            eligible = [0, 1, 2] if arm == ARMS[0] else [identity for identity in range(3) if not current['ready_by_type'][identity]]
            target = acquisition_end(state['step'], CAPS[life])
        expected_batch = replay_batch(life, arm, batch_id, target, eligible, state, tape, round_records, laws, check)
        check('literal_batch_frozen_current_eligibility_clamp_cursor_and_actual_type_fees', saved_batch == expected_batch)
        own_checks = check_records[batch_id*12:(batch_id+1)*12]
        current = audit_check(life, arm, batch_id, own_checks, state, proof_cache, point_cache, score_keys, check)
        check('actual_current_ready_by_type_all12_AND_and_paid_check_meta', metadata[batch_id] == current)
        if batch_id == 0:
            selected['SOURCE'] = own_checks
        if state['step'] == MID_COST:
            selected['SOURCE_PLUS_3072'] = own_checks
        if current['all_ready'] or state['step'] == CAPS[life]:
            selected.setdefault('SOURCE_PLUS_3072', own_checks)
            selected['FULL_CAP'] = own_checks
            check('stop_at_first_current_all12_ready_or_full_cap', batch_id == len(batches)-1)
        print(f'audit life={life} arm={arm} batch={batch_id} paid={state["step"]} ready={current["ready_by_type"]}', flush=True)
    check('all_actual_primitives_rounds_source_and_stop_retained_once',
          state['step'] == len(tape) and state['round_position'] == len(round_records)
          and SOURCE_COST <= state['step'] <= CAPS[life] and state['phase_steps']['SOURCE'] == SOURCE_COST
          and state['phase_steps']['ACQUISITION'] == state['step']-SOURCE_COST
          and sum(state['acquisition_paid_by_type']) == state['step']-SOURCE_COST
          and (current['all_ready'] or state['step'] == CAPS[life]))
    roster = [item for item in public_roster() if item['life'] == life and item['arm'] == arm]
    expected_records = []
    for item in roster:
        original = next(record for record in selected[item['checkpoint_label']]
                        if record['identity'] == item['identity'] and record['cost_index'] == item['cost_index'])
        expected_records.append(project(original, item))
    check('all60_public_projections_reference_own_actual_paid_check_without_new_evidence', records == expected_records)
    artifact = load(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json')
    final_fields = dict(life=life, arm=arm, intermediate_records=len(check_records),
        final_native_counts=state['native'], final_joint_outcome_counts=[mathematics.joint_histogram(values) for values in state['complete']],
        primitive_samples=state['step'], source_samples=SOURCE_COST, acquisition_samples=state['step']-SOURCE_COST,
        acquisition_paid_by_type=state['acquisition_paid_by_type'], acquisition_batches=len(batches)-1,
        complete_rounds=len(round_records), tail_s_samples=sum(state['tails']), final_cursor=state['cursor'],
        final_check_id=current['check_id'], final_ready_by_type=current['ready_by_type'],
        stop_reason='all_ready' if current['all_ready'] else 'full_cap')
    check('actual_final_native_joint_counts_complete_source_charge_and_current_stop',
          all(artifact[field] == value for field, value in final_fields.items()))
    work = Counter(complete_conditional_rounds=len(round_records), standalone_S_tails=sum(state['tails']),
        trajectory_certificate_evaluations=len(check_records)*6, trajectory_unique_score_prefixes=len(score_keys),
        trajectory_score_cache_hits=len(check_records)*6-len(score_keys), trajectory_complete_score_evaluations=sum(score_keys.values()))
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        work[field] = state['step']
    threshold_work = sum(ALPHABETS[row['operator']].index(row['outcome'])+1 for row in tape)
    work['sampling_threshold_accumulations'] = work['sampling_threshold_comparisons'] = threshold_work
    for field, value in work.items():
        check('own_arm_actual_controlled_draw_and_fixed_score_cache_work', artifact['work'].get(field, 0) == value)
    check('own_arm_original_direct_score_prefix_cache_size', artifact['cache_statistics']['direct_score_prefixes'] == len(score_keys))
    for name, capacity in (('execution', 4096), ('query', 256)):
        stats = artifact['cache_statistics']['normalizers'][name]
        check('own_arm_normalizer_cache_statistics', stats['maxsize'] == capacity
              and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    for scope in ('point_vectors', 'trajectory'):
        check('actual_intermediate_check_process_CPU', artifact['timings'][scope]
              == sum(record['model_seconds'][scope] for record in check_records))
    check('actual_type_selection_native_update_CPU_and_observation_output_wall',
          artifact['timings']['type_selection'] >= 0 and artifact['timings']['observation_updates'] >= 0
          and artifact['observation_seconds'] >= 0 and artifact['output_seconds'] >= 0 and artifact['worker_wall_seconds'] >= 0)
    public_scores = score_rows(records, read('scores'), laws, check)
    check_scores = score_rows(check_records, read('check_scores'), laws, check)
    source_signature = [{field: row[field] for field in row if field != 'arm'} for row in tape[:SOURCE_COST]]
    return dict(life=life, arm=arm, records=records, public_scores=public_scores, check_scores=check_scores,
        artifact=artifact, source_signature=source_signature, checks=counts, failures=failures,
        unique_direct_evidence=len(proof_cache), retained_direct_comparisons=len(check_records)*6, elapsed_seconds=perf_counter()-begun)


def group_summary(records):
    return dict(records=len(records), query_ready=sum(record['trajectory']['all_ready'] for record in records),
        certified_by_query={query: sum(record['trajectory']['queries'][query]['certified'] for record in records) for query in QUERIES})


def paired_summary(records):
    before = {(row['life'], row['kind'], row['checkpoint_label'], row['identity'], row['cost_index'], row['index']): row
              for row in records if row['arm'] == ARMS[0]}
    result = {}
    for metric in ('query_ready',)+QUERIES:
        gains, losses, changes = 0, 0, []
        for row in records:
            if row['arm'] != ARMS[1]:
                continue
            old = before[row['life'], row['kind'], row['checkpoint_label'], row['identity'], row['cost_index'], row['index']]
            a, b = [item['trajectory']['all_ready'] if metric == 'query_ready' else item['trajectory']['queries'][metric]['certified']
                    for item in (old, row)]
            gains += b and not a
            losses += a and not b
            if a != b:
                changes.append(dict(life=row['life'], identity=row['identity'], cost_index=row['cost_index'], index=row['index'], before=a, after=b))
        result[metric] = dict(gains=gains, losses=losses, unchanged=len(before)-gains-losses, changes=changes)
    return result


def summarize(records, public_scores, check_scores, artifacts):
    methods = {}
    for arm in ARMS:
        own, jobs = [row for row in records if row['arm'] == arm], [item for item in artifacts if item['arm'] == arm]
        methods[arm] = dict(checkpoint_groups={label: group_summary([row for row in own if row['kind'] == 'CHECKPOINT'
            and row['checkpoint_label'] == label]) for label in LABELS}, terminal=group_summary([row for row in own if row['kind'] == 'RETURN_PROJECTION']),
            false_public_certificates=sum(row['false_certificates'] for row in public_scores if row['arm'] == arm),
            false_intermediate_certificates=sum(row['false_certificates'] for row in check_scores if row['arm'] == arm),
            total_samples=sum(item['primitive_samples'] for item in jobs), source_samples=sum(item['source_samples'] for item in jobs),
            acquisition_samples=sum(item['acquisition_samples'] for item in jobs))
        methods[arm]['false_certificates'] = methods[arm]['false_public_certificates']+methods[arm]['false_intermediate_certificates']
    return dict(complete=True, records=len(records), checkpoint_records=sum(row['kind'] == 'CHECKPOINT' for row in records),
        terminal_records=sum(row['kind'] == 'RETURN_PROJECTION' for row in records), public_pairs=len(records)//2,
        intermediate_records=sum(item['intermediate_records'] for item in artifacts), methods=methods,
        paired_checkpoint_groups={label: paired_summary([row for row in records if row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label]) for label in LABELS},
        terminal_paired=paired_summary([row for row in records if row['kind'] == 'RETURN_PROJECTION']),
        life_summaries=[dict(life=life, arm=arm, terminal=group_summary([row for row in records if row['life'] == life and row['arm'] == arm and row['kind'] == 'RETURN_PROJECTION']),
            **{field: next(item[field] for item in artifacts if item['life'] == life and item['arm'] == arm)
                for field in ('primitive_samples', 'source_samples', 'acquisition_samples', 'acquisition_paid_by_type', 'stop_reason', 'final_ready_by_type', 'acquisition_batches')})
            for life in LIVES for arm in ARMS],
        physical_observations=sum(item['primitive_samples'] for item in artifacts), physical_source_samples=sum(item['source_samples'] for item in artifacts),
        physical_acquisition_samples=sum(item['acquisition_samples'] for item in artifacts),
        fee_ledger=[{field: item[field] for field in ('life', 'arm', 'primitive_samples', 'source_samples', 'acquisition_samples', 'acquisition_paid_by_type')} for item in artifacts],
        model_seconds=sum(sum(item['timings'].values()) for item in artifacts),
        model_timings={scope: sum(item['timings'][scope] for item in artifacts) for scope in ('type_selection', 'observation_updates', 'point_vectors', 'trajectory')},
        model_seconds_scope='summed_process_CPU_type_selection_native_updates_shared_point_vectors_and_direct_proofs_once',
        observation_seconds=sum(item['observation_seconds'] for item in artifacts), output_seconds=sum(item['output_seconds'] for item in artifacts),
        cache_statistics=[dict(life=item['life'], arm=item['arm'], **item['cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'], arm=item['arm'], **item['work']) for item in artifacts],
        positive_qualification_signal=(methods[ARMS[1]]['terminal']['query_ready'] > methods[ARMS[0]]['terminal']['query_ready']
            and methods[ARMS[1]]['total_samples'] <= methods[ARMS[0]]['total_samples'] and all(methods[arm]['false_certificates'] == 0 for arm in ARMS)),
        qualification_only=True, complete_lifecycle_test=False, scientific_gate_changed=False,
        evidence_unit='one_controlled_categorical_operator_observation', source_allocation='conditional_rounds_and_standalone_S_tails_physically_drawn_by_each_arm')


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name))

    protocol, saved_summary = load(OUTPUT/'run.json'), load(OUTPUT/'summary.json')
    roster = public_roster()
    expected_protocol = dict(lives=list(LIVES), arms=list(ARMS), source_budget=SOURCE_COST, total_caps=list(CAPS), batch_cap=BATCH,
        source_seed_base=SOURCE_BASE, acquisition_seed_base=ACQUISITION_BASE, checkpoints=list(LABELS), roster=roster,
        type_rule='cyclic_cursor_skipping_current_joint_ready_types_only_in_DIRECT_JOINT_UNRESOLVED',
        cursor='after_each_complete_round_or_standalone_S_tail_set_selected_type_plus_one_continuous_from_source',
        eligibility='frozen_from_previous_all12_current_decisions_for_entire_acquisition_batch',
        source_allocation='each_arm_physically_draws_own_identical_seed_conditional_rounds_and_S_tails',
        check_rule='all12_current_three_query_AND_at_source_and_every_batch_end', stop_rule='all12_current_ready_or_full_cap',
        checkpoint_stop_projection='retained_last_check_zero_new_observations_and_certificates_actual_paid_fee',
        trajectory_streams=216, trajectory_active_A_streams=108, trajectory_threshold=4320,
        delta_per_life_fixed_arm='1/20', combined_arm_claim=False, public_records=360, public_pairs=180,
        no_offpath_R=True, no_execution_planner=True, new_lifecycle_test=False,
        cache_scope='private_cold_per_life_arm_original_direct_score_prefixes',
        cost_unit='one_controlled_categorical_operator_observation', deterministic_graph_transitions='local_mechanics_zero_new_observations',
        false_certificate_scope='all_intermediate_and_public_decisions', scientific_gate_changed=False, qualification_only=True,
        complete=True, phases=['protocol_and_roster_frozen', 'source_captured',
            'all_intermediate_and_360_public_records_frozen', 'posthoc_truth_scored', 'complete'])
    check('literal_frozen_filtered_RR_protocol_all_current_checks_event_scope_and_truth_freeze', protocol == expected_protocol)
    check('all360_public_case_projections_literal_roster_frozen_before_sampling', load(OUTPUT/'public_roster.json') == roster)
    manifest = load(OUTPUT/'source_manifest.json')
    required = {'src/acfqp/science/joint_unresolved_trajectory_v255.py', 'scripts/run_joint_unresolved_trajectory_v255.py',
        'scripts/audit_joint_unresolved_trajectory_v255.py', 'tests/test_joint_unresolved_trajectory_v255_core.py',
        'tests/test_joint_unresolved_trajectory_v255_runner.py', 'tests/test_joint_unresolved_trajectory_v255_audit.py',
        'specs/JOINT_UNRESOLVED_TRAJECTORY_V255.md'}
    check('captured_all_declared_new_sources_tests_and_frozen_spec', required <= set(manifest))
    for relative in manifest:
        check('captured_source_exact_bytes_unchanged', (ROOT/relative).read_bytes() == (OUTPUT/'source_code'/relative).read_bytes())
    jobs = [(life, arm) for life in LIVES for arm in ARMS]
    with ProcessPoolExecutor(max_workers=6) as executor:
        groups = list(executor.map(audit_life_arm, jobs))
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
    for life in LIVES:
        matched = [group for group in groups if group['life'] == life]
        check('paired_sources_identical_potential_observations_both_arms_physically_charged',
              matched[0]['source_signature'] == matched[1]['source_signature']
              and all(group['artifact']['source_samples'] == SOURCE_COST for group in matched))
    records = [row for group in groups for row in group['records']]
    public_scores = [row for group in groups for row in group['public_scores']]
    check_scores = [row for group in groups for row in group['check_scores']]
    artifacts = [group['artifact'] for group in groups]
    summary = summarize(records, public_scores, check_scores, artifacts)
    check('independent_actual_fees_all_intermediate_errors_paired_gains_and_qualification_summary',
          saved_summary == dict(summary, scoring_seconds=saved_summary['scoring_seconds'], elapsed_seconds=saved_summary['elapsed_seconds'],
              worker_wall_seconds={f'{item["life"]}:{item["arm"]}': item['worker_wall_seconds'] for item in artifacts}))
    check('actual_parent_scoring_elapsed_and_six_worker_wall_costs_nonnegative',
          saved_summary['scoring_seconds'] >= 0 and saved_summary['elapsed_seconds'] >= 0)
    check('all_public_and_intermediate_decision_incidents_scored_after_freeze', len(records) == 360 and len(public_scores) == 360
          and summary['checkpoint_records'] == 216 and summary['terminal_records'] == 144 and summary['public_pairs'] == 180
          and summary['intermediate_records'] == len(check_scores))
    check('physical_own_source_fees_and_total_primitive_caps', summary['physical_source_samples'] == 27648
          and summary['physical_observations'] <= 96768
          and summary['physical_observations'] == summary['physical_source_samples']+summary['physical_acquisition_samples'])
    result = dict(valid=not failures, complete=True, records=len(records), public_pairs=180,
        intermediate_records=len(check_scores), life_arm_jobs=len(groups),
        complete_rounds=sum(item['complete_rounds'] for item in artifacts),
        retained_direct_comparisons=sum(group['retained_direct_comparisons'] for group in groups),
        unique_actual_prefix_evidence=sum(group['unique_direct_evidence'] for group in groups),
        independently_evaluated_direct_comparisons=checks['direct_exact_certification_status'],
        exact_prefix_evidence_reuses=checks['same_actual_prefix_cost_and_direction_reuses_exact_audited_direct_proof'],
        physical_observations=summary['physical_observations'], physical_source_samples=summary['physical_source_samples'],
        physical_acquisition_samples=summary['physical_acquisition_samples'], methods=summary['methods'],
        terminal_paired=summary['terminal_paired'], positive_qualification_signal=summary['positive_qualification_signal'],
        qualification_only=True, scientific_gate_changed=False, checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if run()['valid'] else 1)
