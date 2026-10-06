"""Fresh matched conditional trajectories with one type-allocation treatment."""
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
from acfqp.science import executable_trajectory_v254 as evidence
from acfqp.science import joint_unresolved_trajectory_v255 as core
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_persistent_evidence_v221 import query_score
from scripts.run_shared_probe_timing_v249 import activate_cold_caches

OUTPUT = ROOT/'reports/joint_unresolved_trajectory_v255'
LIVES, ARMS = (0, 1, 2), core.ARMS
TOTAL_CAPS, SOURCE_COST, SOURCE_BASE, TARGET_BASE, BATCH_CAP = (14144, 17072, 17168), 4608, 301000, 302000, 256
PUBLIC_COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
LABELS = ('SOURCE', 'SOURCE_PLUS_3072', 'FULL_CAP')
MODEL_SCOPES = ('type_selection', 'observation_updates', 'point_vectors', 'trajectory')


def filename(kind, life, arm):
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz'


def write_row(stream, row):
    begun = perf_counter()
    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
    stream.flush()
    return perf_counter()-begun


def rows(path):
    with gzip.open(path, 'rt') as stream:
        yield from (json.loads(line) for line in stream)


def case_for(life, arm, identity, cost_index):
    operating, retry = PUBLIC_COSTS[cost_index]
    return dict(id=f'v255_l{life:02d}_{arm}_t{identity}_c{cost_index}', operating=operating,
        retry_cost=retry, context='A', stage='QUERY_QUALIFICATION')


def public_roster(worlds):
    roster = []
    for life in LIVES:
        cases, _, identities, _ = worlds[life]
        for arm in ARMS:
            for label, cap in zip(LABELS, (SOURCE_COST, SOURCE_COST+3072, TOTAL_CAPS[life])):
                for identity in range(3):
                    for cost_index in range(4):
                        roster.append(dict(life=life, arm=arm, kind='CHECKPOINT', checkpoint_label=label,
                            checkpoint_samples=cap, identity=identity, cost_index=cost_index,
                            case=case_for(life, arm, identity, cost_index), index=None))
            for index in range(54, 78):
                case = deepcopy(cases[index])
                roster.append(dict(life=life, arm=arm, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP',
                    checkpoint_samples=TOTAL_CAPS[life], identity=identities[index],
                    cost_index=PUBLIC_COSTS.index((case['operating'], str(case['retry_cost']))), case=case, index=index))
    return roster


class PrimitiveSimulator:
    """Each arm physically draws its own paired source/acquisition prefixes."""
    def __init__(self, life, laws, work):
        self.life, self._laws, self.work = life, laws, work
        self._generators, self._offsets, self.phase_steps = {}, Counter(), Counter()

    def observe(self, phase, identity, operator):
        key = phase, identity, operator
        base = SOURCE_BASE if phase == 'SOURCE' else TARGET_BASE
        seed = base+(self.life*3+identity)*3+evidence.OPERATORS.index(operator)
        if key not in self._generators:
            self._generators[key] = random.Random(seed)
        start = self._offsets[key]
        increments = dict.fromkeys(evidence.ALPHABETS[operator], 0)
        progress = dict(draw_end=start, n=start)
        draw(self._generators[key], self._laws[identity], operator, increments, 1, self.work, progress)
        self._offsets[key] = progress['draw_end']
        self.phase_steps[phase] += 1
        return dict(seed=seed, draw_start=start, draw_end=progress['draw_end'],
            outcome=next(category for category, count in increments.items() if count),
            phase_step_index=self.phase_steps[phase])


def sample_batch(life, arm, batch_id, target, eligible, states, simulator, step, round_id,
                 cursor, acquisition_paid_by_type, tape, rounds, work):
    phase = 'SOURCE' if batch_id == 0 else 'ACQUISITION'
    selection_seconds, observation_seconds, update_seconds, output_seconds = 0., 0., 0., 0.
    before = dict(step=step, cursor=cursor, round_id=round_id, tails=sum(state['tail_s_samples'] for state in states))

    def primitive(identity, operator, active_round, role, selection_cursor):
        nonlocal step, observation_seconds, output_seconds
        begun = perf_counter()
        observed = simulator.observe(phase, identity, operator)
        observation_seconds += perf_counter()-begun
        step += 1
        if phase == 'ACQUISITION':
            acquisition_paid_by_type[identity] += 1
        row = dict(life=life, arm=arm, phase=phase, batch_id=batch_id, step_index=step,
            identity=identity, operator=operator, round_id=active_round, role=role,
            cursor_before=selection_cursor, **observed)
        output_seconds += write_row(tape, row)
        return row

    while step < target:
        selection_cursor = cursor
        begun = process_time()
        identity, cursor = core.select_type(cursor, eligible)
        selection_seconds += process_time()-begun
        if target-step < 3:
            short = primitive(identity, evidence.S, None, 'tail_S', selection_cursor)
            begun = process_time()
            evidence.observe_tail_s(states[identity], short['outcome'])
            update_seconds += process_time()-begun
            work['standalone_S_tails'] += 1
            continue
        round_id += 1
        short = primitive(identity, evidence.S, round_id, 'S', selection_cursor)
        detour = primitive(identity, evidence.D, round_id, 'D', selection_cursor)
        retry = primitive(identity, evidence.R, round_id, 'R', selection_cursor) if detour['outcome'] == 'RECOVERY' else None
        outcomes = {evidence.S: short['outcome'], evidence.D: detour['outcome'], evidence.R: retry['outcome'] if retry else None}
        begun = process_time()
        evidence.observe_round(states[identity], outcomes, round_id)
        update_seconds += process_time()-begun
        output_seconds += write_row(rounds, dict(life=life, arm=arm, round_id=round_id, phase=phase,
            batch_id=batch_id, identity=identity, primitive_steps=[row['step_index'] for row in (short, detour, retry) if row],
            outcomes=outcomes, start_step=short['step_index'], end_step=step))
        work['complete_conditional_rounds'] += 1
    return dict(step=step, cursor=cursor, round_id=round_id, selection_seconds=selection_seconds,
        observation_seconds=observation_seconds, update_seconds=update_seconds, output_seconds=output_seconds,
        batch=dict(life=life, arm=arm, phase=phase, batch_id=batch_id, eligible_types_frozen=list(eligible),
            start_step=before['step'], end_step=step, actual_samples=step-before['step'], target_step=target,
            cursor_before=before['cursor'], cursor_after=cursor, complete_rounds=round_id-before['round_id'],
            standalone_S_tails=sum(state['tail_s_samples'] for state in states)-before['tails'],
            acquisition_paid_by_type=list(acquisition_paid_by_type)))


def check_case(life, arm, check_id, identity, cost_index, state, paid, cache, work):
    case = case_for(life, arm, identity, cost_index)
    begun = process_time()
    vectors = evidence.pure_vectors(state, case)
    queries = evidence.point_queries(vectors)
    point_seconds = process_time()-begun
    begun = process_time()
    trajectory = evidence.trajectory_certificates(state['rounds'], case, queries, cache, work)
    proof_seconds = process_time()-begun
    return dict(life=life, arm=arm, kind='INTERMEDIATE_CHECK', check_id=check_id, identity=identity,
        cost_index=cost_index, case=case, index=None, native_counts=deepcopy(state['native_counts']),
        complete_rounds=len(state['rounds']), joint_outcome_counts=deepcopy(state['joint_outcome_counts']),
        native_n_by_operator={op: sum(counts.values()) for op, counts in state['native_counts'].items()},
        tail_s_samples=state['tail_s_samples'], round_prefix_last_id=state['round_prefix_last_id'],
        source_paid_samples=SOURCE_COST, acquisition_paid_samples=paid-SOURCE_COST, total_paid_samples=paid,
        pure_vectors=vectors, queries=queries, trajectory=trajectory,
        model_seconds=dict(point_vectors=point_seconds, trajectory=proof_seconds))


def run_life_arm(life, arm, laws, roster):
    begun = perf_counter()
    normalizers, cache, work = activate_cold_caches(), {}, Counter()
    states, simulator = [evidence.new_type_state() for _ in range(3)], PrimitiveSimulator(life, laws, work)
    step, round_id, cursor, batch_id, acquisition_paid_by_type = 0, 0, 0, 0, [0, 0, 0]
    timings, observation_seconds, output_seconds = dict.fromkeys(MODEL_SCOPES, 0.), 0., 0.
    selected, current, checks_count = {}, None, 0
    with (gzip.open(filename('tapes', life, arm), 'wt') as tape,
          gzip.open(filename('rounds', life, arm), 'wt') as rounds,
          gzip.open(filename('batches', life, arm), 'wt') as batches,
          gzip.open(filename('checks', life, arm), 'wt') as checks,
          gzip.open(filename('check_meta', life, arm), 'wt') as meta_stream):
        while True:
            eligible = list(range(3)) if current is None else core.eligible_types(arm, current['ready_by_type'])
            target = SOURCE_COST if current is None else min(step+BATCH_CAP, SOURCE_COST+3072 if step<SOURCE_COST+3072 else TOTAL_CAPS[life])
            sampled = sample_batch(life, arm, batch_id, target, eligible, states, simulator,
                step, round_id, cursor, acquisition_paid_by_type, tape, rounds, work)
            step, round_id, cursor = sampled['step'], sampled['round_id'], sampled['cursor']
            observation_seconds += sampled['observation_seconds']
            output_seconds += sampled['output_seconds']
            timings['type_selection'] += sampled['selection_seconds']
            timings['observation_updates'] += sampled['update_seconds']
            sampled['batch']['prior_check_id'] = None if current is None else current['check_id']
            output_seconds += write_row(batches, sampled['batch'])
            check_records = [check_case(life, arm, batch_id, identity, cost_index, states[identity], step, cache, work)
                for identity in range(3) for cost_index in range(4)]
            for record in check_records:
                for scope, seconds in record['model_seconds'].items():
                    timings[scope] += seconds
                output_seconds += write_row(checks, record)
            checks_count += 12
            readiness = core.ready_by_type(check_records)
            current = dict(life=life, arm=arm, check_id=batch_id, primitive_samples=step,
                source_paid_samples=SOURCE_COST, acquisition_paid_samples=step-SOURCE_COST,
                acquisition_paid_by_type=list(acquisition_paid_by_type), cursor=cursor, round_id=round_id,
                ready_by_type=readiness, all_ready=all(readiness),
                case_refs=[dict(check_id=batch_id, identity=row['identity'], cost_index=row['cost_index']) for row in check_records])
            output_seconds += write_row(meta_stream, current)
            if batch_id == 0:
                selected['SOURCE'] = check_records
            if step == SOURCE_COST+3072:
                selected['SOURCE_PLUS_3072'] = check_records
            if current['all_ready'] or step == TOTAL_CAPS[life]:
                stop_reason = 'all_ready' if current['all_ready'] else 'full_cap'
                selected.setdefault('SOURCE_PLUS_3072', check_records)
                selected['FULL_CAP'] = check_records
                break
            batch_id += 1
    records = []
    with gzip.open(filename('records', life, arm), 'wt') as stream:
        for item in roster:
            original = next(row for row in selected[item['checkpoint_label']]
                if row['identity']==item['identity'] and row['cost_index']==item['cost_index'])
            record = deepcopy(original)
            record.update(deepcopy(item), selected_check_id=original['check_id'],
                checkpoint_reached=original['total_paid_samples']>=item['checkpoint_samples'],
                model_seconds=dict(point_vectors=0., trajectory=0.))
            output_seconds += write_row(stream, record)
            records.append(record)
    artifact = dict(life=life, arm=arm, records=records, intermediate_records=checks_count,
        final_native_counts=[state['native_counts'] for state in states],
        final_joint_outcome_counts=[state['joint_outcome_counts'] for state in states],
        primitive_samples=step, source_samples=SOURCE_COST, acquisition_samples=step-SOURCE_COST,
        acquisition_paid_by_type=acquisition_paid_by_type, acquisition_batches=batch_id,
        complete_rounds=round_id, tail_s_samples=sum(state['tail_s_samples'] for state in states),
        final_cursor=cursor, final_check_id=current['check_id'], final_ready_by_type=current['ready_by_type'], stop_reason=stop_reason,
        timings=timings, observation_seconds=observation_seconds, output_seconds=output_seconds,
        worker_wall_seconds=perf_counter()-begun, work=work,
        cache_statistics=dict(direct_score_prefixes=len(cache),
            normalizers={name: function.cache_info()._asdict() for name, function in normalizers.items()}))
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json', {key:value for key,value in artifact.items() if key!='records'})
    print(f'life={life} arm={arm} paid={step} stop={stop_reason} ready={current["ready_by_type"]}', flush=True)
    return artifact


def score_record(record, law):
    queries = query_score(record['queries'], law, record['case'])
    return dict(**{key:record[key] for key in ('life','arm','kind','identity','cost_index','index','case')},
        check_id=record['check_id'], queries=queries, false_certificates=sum(decision['certified'] and queries[query]['regret']>F(1,20)
            for query,decision in record['trajectory']['queries'].items()))


def group(records):
    return dict(records=len(records), query_ready=sum(row['trajectory']['all_ready'] for row in records),
        certified_by_query={query:sum(row['trajectory']['queries'][query]['certified'] for row in records) for query in ('reward','goal','risk')})


def paired(records):
    before = {(row['life'],row['kind'],row['checkpoint_label'],row['identity'],row['cost_index'],row['index']):row
        for row in records if row['arm']=='DIRECT_RR'}
    result = {}
    for metric in ('query_ready','reward','goal','risk'):
        gains, losses, changes = 0, 0, []
        for row in records:
            if row['arm']!='DIRECT_JOINT_UNRESOLVED':
                continue
            old = before[row['life'],row['kind'],row['checkpoint_label'],row['identity'],row['cost_index'],row['index']]
            a,b = [item['trajectory']['all_ready'] if metric=='query_ready' else item['trajectory']['queries'][metric]['certified'] for item in (old,row)]
            gains += b and not a
            losses += a and not b
            if a!=b:
                changes.append(dict(life=row['life'],identity=row['identity'],cost_index=row['cost_index'],index=row['index'],before=a,after=b))
        result[metric] = dict(gains=gains,losses=losses,unchanged=len(before)-gains-losses,changes=changes)
    return result


def summarize(records, public_scores, check_scores, artifacts):
    methods = {}
    for arm in ARMS:
        own = [row for row in records if row['arm']==arm]
        jobs = [item for item in artifacts if item['arm']==arm]
        methods[arm] = dict(checkpoint_groups={label:group([row for row in own if row['kind']=='CHECKPOINT' and row['checkpoint_label']==label]) for label in LABELS},
            terminal=group([row for row in own if row['kind']=='RETURN_PROJECTION']),
            false_public_certificates=sum(row['false_certificates'] for row in public_scores if row['arm']==arm),
            false_intermediate_certificates=sum(row['false_certificates'] for row in check_scores if row['arm']==arm),
            total_samples=sum(item['primitive_samples'] for item in jobs), source_samples=sum(item['source_samples'] for item in jobs),
            acquisition_samples=sum(item['acquisition_samples'] for item in jobs))
        methods[arm]['false_certificates'] = methods[arm]['false_public_certificates']+methods[arm]['false_intermediate_certificates']
    return dict(complete=True, records=len(records), checkpoint_records=sum(row['kind']=='CHECKPOINT' for row in records),
        terminal_records=sum(row['kind']=='RETURN_PROJECTION' for row in records), public_pairs=len(records)//2,
        intermediate_records=sum(item['intermediate_records'] for item in artifacts), methods=methods,
        paired_checkpoint_groups={label:paired([row for row in records if row['kind']=='CHECKPOINT' and row['checkpoint_label']==label]) for label in LABELS},
        terminal_paired=paired([row for row in records if row['kind']=='RETURN_PROJECTION']),
        life_summaries=[dict(life=life,arm=arm,terminal=group([row for row in records if row['life']==life and row['arm']==arm and row['kind']=='RETURN_PROJECTION']),
            **{key:next(item[key] for item in artifacts if item['life']==life and item['arm']==arm)
                for key in ('primitive_samples','source_samples','acquisition_samples','acquisition_paid_by_type','stop_reason','final_ready_by_type','acquisition_batches')}) for life in LIVES for arm in ARMS],
        physical_observations=sum(item['primitive_samples'] for item in artifacts), physical_source_samples=sum(item['source_samples'] for item in artifacts),
        physical_acquisition_samples=sum(item['acquisition_samples'] for item in artifacts),
        fee_ledger=[{key:item[key] for key in ('life','arm','primitive_samples','source_samples','acquisition_samples','acquisition_paid_by_type')} for item in artifacts],
        model_seconds=sum(sum(item['timings'].values()) for item in artifacts),
        model_timings={scope:sum(item['timings'][scope] for item in artifacts) for scope in MODEL_SCOPES},
        model_seconds_scope='summed_process_CPU_type_selection_native_updates_shared_point_vectors_and_direct_proofs_once',
        observation_seconds=sum(item['observation_seconds'] for item in artifacts), output_seconds=sum(item['output_seconds'] for item in artifacts),
        cache_statistics=[dict(life=item['life'],arm=item['arm'],**item['cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'],arm=item['arm'],**item['work']) for item in artifacts],
        positive_qualification_signal=(methods[ARMS[1]]['terminal']['query_ready']>methods[ARMS[0]]['terminal']['query_ready']
            and methods[ARMS[1]]['total_samples']<=methods[ARMS[0]]['total_samples'] and all(methods[arm]['false_certificates']==0 for arm in ARMS)),
        qualification_only=True, complete_lifecycle_test=False, scientific_gate_changed=False,
        evidence_unit='one_controlled_categorical_operator_observation', source_allocation='conditional_rounds_and_standalone_S_tails_physically_drawn_by_each_arm')


def capture():
    from scripts import audit_joint_unresolved_trajectory_v255
    paths = {'src/acfqp/science/joint_unresolved_trajectory_v255.py','scripts/run_joint_unresolved_trajectory_v255.py',
        'scripts/audit_joint_unresolved_trajectory_v255.py','tests/test_joint_unresolved_trajectory_v255_core.py',
        'tests/test_joint_unresolved_trajectory_v255_runner.py','tests/test_joint_unresolved_trajectory_v255_audit.py',
        'specs/JOINT_UNRESOLVED_TRAJECTORY_V255.md'}
    for module in tuple(sys.modules.values()):
        source = getattr(module,'__file__',None)
        if source:
            path = Path(source).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,destination)
    save(OUTPUT/'source_manifest.json',sorted(paths))


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    worlds = {life:task.world(life) for life in LIVES}
    roster = public_roster(worlds)
    protocol = dict(lives=LIVES,arms=ARMS,source_budget=SOURCE_COST,total_caps=TOTAL_CAPS,batch_cap=BATCH_CAP,
        source_seed_base=SOURCE_BASE,acquisition_seed_base=TARGET_BASE,checkpoints=LABELS,roster=roster,
        type_rule='cyclic_cursor_skipping_current_joint_ready_types_only_in_DIRECT_JOINT_UNRESOLVED',
        cursor='after_each_complete_round_or_standalone_S_tail_set_selected_type_plus_one_continuous_from_source',
        eligibility='frozen_from_previous_all12_current_decisions_for_entire_acquisition_batch',
        source_allocation='each_arm_physically_draws_own_identical_seed_conditional_rounds_and_S_tails',
        check_rule='all12_current_three_query_AND_at_source_and_every_batch_end',stop_rule='all12_current_ready_or_full_cap',
        checkpoint_stop_projection='retained_last_check_zero_new_observations_and_certificates_actual_paid_fee',
        trajectory_streams=216,trajectory_active_A_streams=108,trajectory_threshold=4320,
        delta_per_life_fixed_arm='1/20',combined_arm_claim=False,public_records=360,public_pairs=180,
        no_offpath_R=True,no_execution_planner=True,new_lifecycle_test=False,
        cache_scope='private_cold_per_life_arm_original_direct_score_prefixes',
        cost_unit='one_controlled_categorical_operator_observation',deterministic_graph_transitions='local_mechanics_zero_new_observations',
        false_certificate_scope='all_intermediate_and_public_decisions',scientific_gate_changed=False,qualification_only=True)
    capture()
    save(OUTPUT/'public_roster.json',roster)
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['protocol_and_roster_frozen','source_captured']))
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_life_arm,life,arm,worlds[life][1][:3],
            [row for row in roster if row['life']==life and row['arm']==arm]) for life in LIVES for arm in ARMS]
        artifacts = [future.result() for future in futures]
    records = [row for item in artifacts for row in item['records']]
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['protocol_and_roster_frozen','source_captured','all_intermediate_and_360_public_records_frozen']))
    public_scores, check_scores, scoring_seconds = [], [], 0.
    for item in artifacts:
        life,arm = item['life'],item['arm']
        for kind,source,destination in (('scores',item['records'],public_scores),('check_scores',rows(filename('checks',life,arm)),check_scores)):
            with gzip.open(filename(kind,life,arm),'wt') as stream:
                for record in source:
                    started = perf_counter()
                    score = score_record(record,worlds[life][1][record['identity']])
                    scoring_seconds += perf_counter()-started
                    write_row(stream,score)
                    destination.append(score)
    summary = dict(summarize(records,public_scores,check_scores,artifacts),scoring_seconds=scoring_seconds,
        elapsed_seconds=perf_counter()-begun,worker_wall_seconds={f'{item["life"]}:{item["arm"]}':item['worker_wall_seconds'] for item in artifacts})
    save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(protocol,complete=True,phases=['protocol_and_roster_frozen','source_captured','all_intermediate_and_360_public_records_frozen','posthoc_truth_scored','complete']))
    print(json.dumps(exact_json(summary)),flush=True)
    return summary


if __name__=='__main__':
    run()
