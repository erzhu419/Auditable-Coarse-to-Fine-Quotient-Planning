"""Fresh conditional-continuation qualification with a common paid tape."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import executable_trajectory_v254 as core
from acfqp.science import online_joint_query_v242 as row_joint
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan
from scripts.run_persistent_evidence_v221 import query_score
from scripts.run_shared_probe_timing_v249 import activate_cold_caches

OUTPUT = ROOT/'reports/executable_trajectory_v254'
LIVES, METHODS = (0, 1, 2), ('ROW_JOINT', 'TRAJECTORY')
TOTAL_CAPS, SOURCE_COST, SOURCE_BASE, TARGET_BASE = (14144, 17072, 17168), 4608, 299000, 300000
PUBLIC_COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
LABELS = ('SOURCE', 'SOURCE_PLUS_3072', 'FULL_CAP')
MODEL_SCOPES = ('observation_updates', 'point_vectors', 'row_joint', 'trajectory')


def filename(kind, life):
    return OUTPUT/f'{kind}_life_{life:02d}.jsonl.gz'


def write_row(stream, row):
    begun = perf_counter()
    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
    stream.flush()
    return perf_counter()-begun


def public_roster(worlds):
    roster = []
    for life in LIVES:
        cases, _, identities, _ = worlds[life]
        for label, budget in zip(LABELS, (SOURCE_COST, SOURCE_COST+3072, TOTAL_CAPS[life])):
            for identity in range(3):
                for cost_index, (operating, retry) in enumerate(PUBLIC_COSTS):
                    case = dict(id=f'v254_l{life:02d}_{label.lower()}_t{identity}_c{cost_index}',
                        operating=operating, retry_cost=retry, context='A', stage='QUERY_QUALIFICATION')
                    roster.append(dict(life=life, kind='CHECKPOINT', checkpoint_label=label,
                        checkpoint_samples=budget, identity=identity, cost_index=cost_index, case=case, index=None))
        for index in range(54, 78):
            case = deepcopy(cases[index])
            roster.append(dict(life=life, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP',
                checkpoint_samples=TOTAL_CAPS[life], identity=identities[index],
                cost_index=PUBLIC_COSTS.index((case['operating'], str(case['retry_cost']))), case=case, index=index))
    return roster


class PrimitiveSimulator:
    """Probability access remains in this environment-side sampling object."""
    def __init__(self, life, laws, work):
        self.life, self._laws, self.work = life, laws, work
        self._generators, self._offsets, self.phase_steps = {}, Counter(), Counter()

    def observe(self, phase, identity, operator):
        key = phase, identity, operator
        base = SOURCE_BASE if phase == 'SOURCE' else TARGET_BASE
        seed = base+(self.life*3+identity)*3+core.OPERATORS.index(operator)
        if key not in self._generators:
            self._generators[key] = random.Random(seed)
        start = self._offsets[key]
        increments = dict.fromkeys(core.ALPHABETS[operator], 0)
        progress = dict(draw_end=start, n=start)
        draw(self._generators[key], self._laws[identity], operator, increments, 1, self.work, progress)
        self._offsets[key] = progress['draw_end']
        self.phase_steps[phase] += 1
        outcome = next(category for category, count in increments.items() if count)
        return dict(seed=seed, draw_start=start, draw_end=progress['draw_end'], outcome=outcome,
            phase_step_index=self.phase_steps[phase])


def sample_segment(life, segment, target, states, simulator, step, round_id, cursor, tape, rounds, work):
    phase = 'SOURCE' if segment == 0 else 'ACQUISITION'
    observation_seconds, model_seconds, output_seconds = 0., 0., 0.

    def primitive(identity, operator, active_round, role):
        nonlocal step, observation_seconds, output_seconds
        begun = perf_counter()
        observed = simulator.observe(phase, identity, operator)
        observation_seconds += perf_counter()-begun
        step += 1
        row = dict(life=life, phase=phase, segment=segment, step_index=step,
            identity=identity, operator=operator, round_id=active_round, role=role, **observed)
        output_seconds += write_row(tape, row)
        return row

    while step < target:
        identity = cursor % 3
        if target-step < 3:
            row = primitive(identity, core.S, None, 'tail_S')
            begun = process_time()
            core.observe_tail_s(states[identity], row['outcome'])
            model_seconds += process_time()-begun
            cursor += 1
            work['standalone_S_tails'] += 1
            continue
        round_id += 1
        short = primitive(identity, core.S, round_id, 'S')
        detour = primitive(identity, core.D, round_id, 'D')
        retry = primitive(identity, core.R, round_id, 'R') if detour['outcome'] == 'RECOVERY' else None
        outcomes = {core.S: short['outcome'], core.D: detour['outcome'], core.R: retry['outcome'] if retry else None}
        record = dict(life=life, round_id=round_id, phase=phase, segment=segment, identity=identity,
            primitive_steps=[row['step_index'] for row in (short, detour, retry) if row is not None],
            outcomes=outcomes, start_step=short['step_index'], end_step=step)
        begun = process_time()
        core.observe_round(states[identity], outcomes, round_id)
        model_seconds += process_time()-begun
        output_seconds += write_row(rounds, record)
        cursor += 1
        work['complete_conditional_rounds'] += 1
    return dict(step=step, round_id=round_id, cursor=cursor, observation_seconds=observation_seconds,
        model_seconds=model_seconds, output_seconds=output_seconds)


def qualify(roster_row, state, row_cache, score_cache, work, profiles, profile_ids):
    case = roster_row['case']
    timings = {}
    begun = process_time()
    vectors = core.pure_vectors(state, case)
    queries = core.point_queries(vectors)
    timings['point_vectors'] = process_time()-begun
    begun = process_time()
    row = row_joint.certificates(state['native_counts'], case, queries, row_cache, work)
    timings['row_joint'] = process_time()-begun
    begun = process_time()
    trajectory = core.trajectory_certificates(state['rounds'], case, queries, score_cache, work)
    timings['trajectory'] = process_time()-begun
    begun = perf_counter()
    retained = retain_plan(dict(case=case, queries=queries, query_ready=row['all_ready'], query_evidence=row), profiles, profile_ids)
    output_seconds = perf_counter()-begun
    budget = roster_row['checkpoint_samples']
    return dict(deepcopy(roster_row), native_counts=deepcopy(state['native_counts']),
        complete_rounds=len(state['rounds']), joint_outcome_counts=deepcopy(state['joint_outcome_counts']),
        native_n_by_operator={op: sum(counts.values()) for op, counts in state['native_counts'].items()},
        tail_s_samples=state['tail_s_samples'], round_prefix_last_id=state['round_prefix_last_id'],
        source_paid_samples=SOURCE_COST, acquisition_paid_samples=budget-SOURCE_COST,
        total_paid_samples=budget, pure_vectors=vectors, queries=queries,
        row_joint=retained, trajectory=trajectory, model_seconds=timings, output_seconds=output_seconds)


def run_life(life, laws, roster):
    begun = perf_counter()
    normalizers, row_cache, score_cache, profile_ids, work = activate_cold_caches(), {}, {}, {}, Counter()
    states = [core.new_type_state() for _ in range(3)]
    simulator = PrimitiveSimulator(life, laws, work)
    step, round_id, cursor, observation_seconds, output_seconds = 0, 0, 0, 0., 0.
    timings = dict.fromkeys(MODEL_SCOPES, 0.)
    records, full = [], {}
    with (gzip.open(filename('tapes', life), 'wt') as tape, gzip.open(filename('rounds', life), 'wt') as rounds,
          gzip.open(filename('records', life), 'wt') as stream, gzip.open(filename('profiles', life), 'wt') as profiles):
        for segment, (label, cap) in enumerate(zip(LABELS, (SOURCE_COST, SOURCE_COST+3072, TOTAL_CAPS[life]))):
            sampled = sample_segment(life, segment, cap, states, simulator, step, round_id, cursor, tape, rounds, work)
            step, round_id, cursor = sampled['step'], sampled['round_id'], sampled['cursor']
            observation_seconds += sampled['observation_seconds']
            timings['observation_updates'] += sampled['model_seconds']
            output_seconds += sampled['output_seconds']
            for item in roster:
                if item['kind'] != 'CHECKPOINT' or item['checkpoint_label'] != label:
                    continue
                record = qualify(item, states[item['identity']], row_cache, score_cache, work, profiles, profile_ids)
                for scope, seconds in record['model_seconds'].items():
                    timings[scope] += seconds
                output_seconds += record['output_seconds']+write_row(stream, record)
                records.append(record)
                if label == 'FULL_CAP':
                    full[item['identity'], item['cost_index']] = record
            print(f'life={life} checkpoint={label} paid={step} complete_rounds={round_id}', flush=True)
        for item in roster:
            if item['kind'] != 'RETURN_PROJECTION':
                continue
            record = deepcopy(full[item['identity'], item['cost_index']])
            record.update(deepcopy(item), selected_full_cap_record=dict(life=life, identity=item['identity'], cost_index=item['cost_index']),
                model_seconds=dict.fromkeys(('point_vectors', 'row_joint', 'trajectory'), 0.), output_seconds=0.)
            record['row_joint']['case'] = deepcopy(item['case'])
            output_seconds += write_row(stream, record)
            records.append(record)
    artifact = dict(life=life, records=records, final_native_counts=[state['native_counts'] for state in states],
        final_joint_outcome_counts=[state['joint_outcome_counts'] for state in states],
        primitive_samples=step, source_samples=SOURCE_COST, acquisition_samples=step-SOURCE_COST,
        complete_rounds=round_id, tail_s_samples=sum(state['tail_s_samples'] for state in states),
        timings=timings, observation_seconds=observation_seconds, output_seconds=output_seconds,
        worker_wall_seconds=perf_counter()-begun, work=work,
        cache_statistics=dict(row_V235=len(row_cache.get('V235', {})), row_convex=len(row_cache.get('convex_tangent', {})),
            direct_score_prefixes=len(score_cache), row_profiles=len(profile_ids),
            normalizers={name: function.cache_info()._asdict() for name, function in normalizers.items()}))
    save(OUTPUT/f'worker_artifacts_life_{life:02d}.json', {key: value for key, value in artifact.items() if key != 'records'})
    return artifact


def method_evidence(record, method):
    return record['row_joint']['query_evidence'] if method == 'ROW_JOINT' else record['trajectory']


def score_record(record, law):
    queries = query_score(record['queries'], law, record['case'])
    return dict(**{key: record[key] for key in ('life', 'kind', 'checkpoint_samples', 'identity', 'cost_index', 'index', 'case')},
        queries=queries, false_certificates={method: sum(decision['certified'] and queries[q]['regret'] > F(1, 20)
            for q, decision in method_evidence(record, method)['queries'].items()) for method in METHODS})


def group(records, method):
    evidence = [method_evidence(row, method) for row in records]
    critical = [comparison for item in evidence for comparison in item['queries']['goal'].get('comparisons', [])
        if item['queries']['goal']['policy'] == 'SHORT' and comparison['other'] == 'DETOUR_RETRY']
    return dict(pairs=len(records), query_ready=sum(item['all_ready'] for item in evidence),
        certified_by_query={query: sum(item['queries'][query]['certified'] for item in evidence) for query in ('reward', 'goal', 'risk')},
        critical_short_retry=dict(comparisons=len(critical), certified=sum(item['certified'] for item in critical)))


def paired(records):
    result = {}
    for metric in ('query_ready', 'reward', 'goal', 'risk'):
        gains, losses, changes = 0, 0, []
        for record in records:
            evidence = [method_evidence(record, method) for method in METHODS]
            before, after = [item['all_ready'] if metric == 'query_ready' else item['queries'][metric]['certified'] for item in evidence]
            gains += after and not before
            losses += before and not after
            if before != after:
                changes.append(dict(life=record['life'], identity=record['identity'], cost_index=record['cost_index'],
                    index=record['index'], before=before, after=after))
        result[metric] = dict(gains=gains, losses=losses, unchanged=len(records)-gains-losses, changes=changes)
    return result


def summarize(records, scores, artifacts):
    terminal = [row for row in records if row['kind'] == 'RETURN_PROJECTION']
    methods = {method: dict(checkpoint_groups={label: group([row for row in records if row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label], method)
        for label in LABELS}, terminal=group(terminal, method), false_certificates=sum(row['false_certificates'][method] for row in scores)) for method in METHODS}
    return dict(complete=True, records=len(records), checkpoint_pairs=sum(row['kind'] == 'CHECKPOINT' for row in records),
        terminal_pairs=len(terminal), methods=methods,
        paired_checkpoint_groups={label: paired([row for row in records if row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label]) for label in LABELS},
        terminal_paired=paired(terminal),
        life_summaries=[dict(life=life, methods={method: dict(checkpoint_groups={label: group([row for row in records if row['life'] == life and row['kind'] == 'CHECKPOINT' and row['checkpoint_label'] == label], method)
            for label in LABELS}, terminal=group([row for row in terminal if row['life'] == life], method)) for method in METHODS}) for life in LIVES],
        physical_observations=sum(item['primitive_samples'] for item in artifacts),
        physical_source_samples=sum(item['source_samples'] for item in artifacts),
        physical_acquisition_samples=sum(item['acquisition_samples'] for item in artifacts),
        fee_ledger=[dict(life=item['life'], source_samples=item['source_samples'], acquisition_samples=item['acquisition_samples'], total_samples=item['primitive_samples']) for item in artifacts],
        model_seconds=sum(sum(item['timings'].values()) for item in artifacts),
        model_timings={scope: sum(item['timings'][scope] for item in artifacts) for scope in MODEL_SCOPES},
        model_seconds_scope='summed_process_CPU_native_updates_shared_point_vectors_ROW_proofs_and_TRAJECTORY_proofs_once',
        observation_seconds=sum(item['observation_seconds'] for item in artifacts),
        output_seconds=sum(item['output_seconds'] for item in artifacts),
        cache_statistics=[dict(life=item['life'], **item['cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'], **item['work']) for item in artifacts],
        positive_qualification_signal=(methods['TRAJECTORY']['terminal']['certified_by_query']['goal'] > methods['ROW_JOINT']['terminal']['certified_by_query']['goal']
            and all(methods[method]['false_certificates'] == 0 for method in METHODS)),
        qualification_only=True, complete_lifecycle_test=False, scientific_gate_changed=False,
        evidence_unit='one_controlled_categorical_operator_observation', source_allocation='conditional_rounds_and_standalone_S_tails')


def capture():
    from scripts import audit_executable_trajectory_v254
    paths = {'src/acfqp/science/executable_trajectory_v254.py', 'scripts/run_executable_trajectory_v254.py',
        'scripts/audit_executable_trajectory_v254.py', 'tests/test_executable_trajectory_v254_core.py',
        'tests/test_executable_trajectory_v254_runner.py', 'tests/test_executable_trajectory_v254_audit.py',
        'specs/EXECUTABLE_TRAJECTORY_V254.md'}
    for module in tuple(sys.modules.values()):
        source = getattr(module, '__file__', None)
        if source:
            path = Path(source).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(paths))


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    worlds = {life: task.world(life) for life in LIVES}
    roster = public_roster(worlds)
    protocol = dict(lives=LIVES, methods=METHODS, source_budget=SOURCE_COST, total_caps=TOTAL_CAPS,
        checkpoints=LABELS, source_seed_base=SOURCE_BASE, acquisition_seed_base=TARGET_BASE,
        cursor='advance_after_complete_round_or_standalone_S_tail_never_reset',
        source_allocation='complete_actual_S_D_conditional_R_rounds_and_S_tails',
        acquisition_offsets='continuous_across_7680_checkpoint', row_events=48, row_active_A_events=24,
        row_threshold=960, trajectory_streams=216, trajectory_active_A_streams=108, trajectory_threshold=4320,
        delta_per_life_fixed_method='1/20', combined_method_claim=False,
        checkpoint_pairs=108, terminal_projection_pairs=72, roster=roster,
        score_rule='original_V233_ScoreSpec_predictable_bets_evaluate_on_complete_actual_rounds',
        policy_rule='shared_raw_joint_trajectory_means_with_lexical_ties',
        cost_unit='one_controlled_categorical_operator_observation', deterministic_graph_transitions='local_mechanics_zero_new_observations',
        no_offpath_R=True, no_execution_planner=True, new_lifecycle_test=False,
        cache_scope='private_cold_per_life_ROW_and_TRAJECTORY', scientific_gate_changed=False, qualification_only=True)
    capture()
    save(OUTPUT/'public_roster.json', roster)
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_and_roster_frozen', 'source_captured']))
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_life, life, worlds[life][1][:3], [row for row in roster if row['life'] == life]) for life in LIVES]
        artifacts = [future.result() for future in futures]
    records = [row for item in artifacts for row in item['records']]
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_and_roster_frozen', 'source_captured', 'all_180_decision_pairs_frozen']))
    scores, scoring_seconds = [], 0.
    for life in LIVES:
        with gzip.open(filename('scores', life), 'wt') as stream:
            for record in records:
                if record['life'] != life:
                    continue
                started = perf_counter()
                score = score_record(record, worlds[life][1][record['identity']])
                scoring_seconds += perf_counter()-started
                write_row(stream, score)
                scores.append(score)
    summary = dict(summarize(records, scores, artifacts), scoring_seconds=scoring_seconds,
        elapsed_seconds=perf_counter()-begun,
        worker_wall_seconds={item['life']: item['worker_wall_seconds'] for item in artifacts})
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, complete=True,
        phases=['protocol_and_roster_frozen', 'source_captured', 'all_180_decision_pairs_frozen', 'posthoc_truth_scored', 'complete']))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
