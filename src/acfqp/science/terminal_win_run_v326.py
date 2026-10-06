"""Terminal-grounded versus bootstrap WIN learning on shared fresh query roots."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .closed_loop_versions_v313 import snapshot_weights, save_version
from .confirmed_context_data_v309 import acquire_stage
from .confirmed_context_v309 import ConfirmedContexts
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .greedy_target_data_v317 import acquire_policy_data
from .native_query_supervision_v319 import query_roots, supervise
from .native_split_risk_v301 import fit_split, evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .native_win_learning_v324 import fit_win_supervision
from .native_teacher_calibration_v320 import continue_targets
from .natural_model_revision_v281 import load_leaf, MAX_STEPS, QUERY
from .query_facts_v319 import prepare_anchors
from .query_supervision_run_v319 import _artifact, _compact, _save
from .retained_critic_v287 import compact_dataset
from .terminal_win_analysis_v326 import summarize

TASKS = ('A', 'B')
UPDATING_ARMS = ('BOOTSTRAP_WIN', 'TERMINAL_WIN')
PROBABILITIES = {'A': .1, 'B': .5}
LIVES, INITIAL_RAW, ROUND_RAW, GROUPS, REPLICAS, EPISODES = 16, 131072, 65536, 1024, 4, 64
EPOCHS = 16
OUTCOME_FIELDS = ('scores', 'actions', 'status', 'new_raw_tiles', 'final_boards', 'reward_return', 'win', 'utility')


def stage_increment(life, task, number):
    return life*10000000+TASKS.index(task)*1000000+number*100000


def collection_seed(life, task, number):
    return 3265000000000+stage_increment(life, task, number)


def selection_seed(life, task, number):
    return 3263000000000+stage_increment(life, task, number)


def draw_seed(life, task, number):
    return 3266000000000+stage_increment(life, task, number)


def evaluation_seed(life, task, episode):
    return 3269000000000+life*1000000+TASKS.index(task)*100000+episode


def rollout_seed(life, task, number, group, member):
    return 3267000000000+stage_increment(life,task,number)+group*REPLICAS+member


def configuration(source):
    return dict(schema='acfqp.terminal_win_freeze.v326', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/TERMINAL_WIN_V326.md'),
        lifecycles=list(range(LIVES)), parents=4, workers=4, tasks=TASKS,
        arms=('SOURCE','FIRST_LOCAL')+UPDATING_ARMS, updating_arms=UPDATING_ARMS,
        rounds=(1,2), initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=ROUND_RAW,
        fit_fraction=.8, alpha=.0025, groups_per_task_round=GROUPS, replicas_per_group=REPLICAS,
        epochs=EPOCHS, rootgroup_updates_per_arm_task_round=GROUPS*EPOCHS,
        census_anchors_per_task_round=2*GROUPS, true_probabilities=PROBABILITIES, query=QUERY,
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        teacher='IMMUTABLE_NEW_FIRST_LOCAL_V0_ALL_ROUNDS_AND_BOTH_ARMS',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collector='FROZEN_NEW_FIRST_LOCAL_V0_SHARED_PHYSICALLY_CHARGED_PER_ARM',
        reward='ACTUAL_FIRST_REWARD_FROZEN_WITH_ZERO_WRITES_BOTH_ROUNDS',
        query_root='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        valid_selection='EQUIDISTANT_VALID_CENSUS_POSITIONS_SHARED_BETWEEN_ARMS',
        reset_access='ARBITRARY_AFTERSTATE_GENERATIVE_ACCESS_FOR_BOTH_ARMS',
        target_fields={'BOOTSTRAP_WIN':'targetwin','TERMINAL_WIN':'terminal_win'},
        bootstrap_target='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH_WIN_COMPONENT_ONLY',
        terminal_target='SAVED_DIRECT_THEN_FROZEN_FIRST_H2_TRUE_WORLD_TERMINAL_WIN',
        update='SIXTEEN_FIXED_ORDER_PASSES_CURRENT_WIN_PREDICTION_RECOMPUTED_PER_GROUP',
        optimization_comparison='SAME_ROOTS_MEMBERS_ALPHA_PASSES_ORDER_AND_UPDATE_COUNTS',
        cost_comparison='SAME_ROOT_LABEL_ABLATION_EXTRA_TERMINAL_RAW_CHARGED_NOT_EQUAL_TOTAL_RAW_EFFICIENCY',
        max_steps=MAX_STEPS, evaluation_games_per_cell=EPISODES,
        seed_initial_warmup=3261000000000, seed_initial_training=3262000000000,
        seed_collection=3265000000000, seed_selector=3263000000000, seed_ground=3266000000000,
        seed_continuation=3267000000000, continuation_group_stride=REPLICAS,
        collection_life_stride=10000000, collection_task_stride=1000000, collection_round_stride=100000,
        seed_evaluation=3269000000000, bootstrap_seed=32600001, bootstrap_draws=20000,
        primary='TERMINAL_WIN_minus_FIRST_LOCAL_FINAL_AB',
        terminal_target_contribution='TERMINAL_WIN_minus_BOOTSTRAP_WIN_FINAL_AB',
        retention='FINAL_TERMINAL_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_initial_training_raw_tiles=LIVES*2*INITIAL_RAW,
        expected_post_raw_physical=LIVES*2*2*ROUND_RAW,
        expected_shared_first_spawns=LIVES*2*2*GROUPS*REPLICAS,
        expected_terminal_rollouts=LIVES*2*2*GROUPS*REPLICAS,
        expected_updates_per_arm=LIVES*2*2*GROUPS*EPOCHS,
        expected_new_evaluation_games=LIVES*2*EPISODES*6,
        evidence_scope='NEW_TARGET_LEARNING_HISTORIES_UNDER_FOUR_FIXED_V312_SOURCES_SAME_ROOT_TERMINAL_LABEL_INTERVENTION',
        candidate_selection='V325_TASK_OPPOSED_FIRST_TEACHER_WIN_BIAS_AND_UNRESOLVED_V324_LEARNING_UTILITY',
        stop_rule='WHOLE_COHORT_HOLD_ON_BANK_CENSUS_ACQUISITION_EVALUATION_OR_TERMINAL_CUTOFF_NO_REPLACEMENT_OR_TUNING')


def fit_replay(leaf, roots, targets, runtime):
    started, cpu = perf_counter(), process_time()
    epochs = [fit_win_supervision(leaf, roots, targets, runtime, alpha=.0025) for _ in range(EPOCHS)]
    return dict(method='REPLAY_GROUPED_WIN_ONLY_LOCAL', alpha=.0025,
        distinct_rootgroups=len(roots), epochs=EPOCHS, fitted_rootgroups=len(roots)*EPOCHS,
        replicates=REPLICAS, reward_frozen=True, epoch_receipts=epochs,
        learning_counts=sum_counts(e['learning_counts'] for e in epochs),
        normalization_counts=sum_counts(e['normalization_counts'] for e in epochs),
        target_counts=sum_counts(e['target_counts'] for e in epochs),
        representation_counts=sum_counts(e['representation_counts'] for e in epochs),
        setup_counts=sum_counts(e['setup_counts'] for e in epochs),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    updates = leaf.updates
    seeds = [evaluation_seed(life, task, i) for i in range(EPISODES)]
    p = belief['estimated_p_four']
    result = (engine.evaluate_games(leaf, p, PROBABILITIES[task], seeds, depth=2, max_steps=MAX_STEPS)
        if version is None else evaluate_split(leaf, p, PROBABILITIES[task], seeds, runtime, max_steps=MAX_STEPS))
    if leaf.updates != updates:
        raise ValueError('V326 evaluation changed the frozen head')
    return dict(result, estimated_p_four=p, head_version=deepcopy(version), planner='H2', static_evaluation_valid=True)


class CohortHold(Exception):
    def __init__(self, kind, reason):
        self.kind = kind
        super().__init__(reason)


def _run_life(template, source, identity, runtime, out, engine, emit):
    initial, rounds, setups, heads, versions, contexts = {}, {}, {}, {}, {}, {}
    row = dict(lifecycle=identity, parent=source['parent'], initial=initial, rounds=rounds,
        head_setups=setups, final_head_versions=versions, initial_context_precondition_met=False)
    router = ConfirmedContexts()
    task, number = None, 0
    cutoff_seen = False

    def recorded(value):
        nonlocal cutoff_seen
        cutoff_seen |= value.get('summary', {}).get('status') == 'CUTOFF' or any(
            game['status'] == 'CUTOFF' for game in value.get('completed_games', ()))
        emit(value)

    try:
        for task in TASKS:
            index = TASKS.index(task)
            acquired = acquire_stage(template, identity, source['parent'], task+'0', router, recorded, runtime,
                p_four=PROBABILITIES[task], warmup_seed_base=3261000000000+index*100000,
                training_seed_base=3262000000000+index*100000, raw_budget=INITIAL_RAW)
            route, dataset = acquired['route'], acquired['dataset']
            if not route['created'] or dataset is None:
                initial[task] = dict(context_route=route, acquisition=acquired['acquisition'])
                raise CohortHold('HOLD_INITIAL_BANK', 'New target observations did not establish two distinct banks')
            contexts[task] = route['context_id']
            memory = SpawnMemory.from_payload(dataset['fit_memory'])
            belief = dict(memory=memory.to_payload(), estimated_p_four=memory.predict())
            first, setup = _new_head(template, 'LOCAL_RISK', runtime)
            fit = fit_split(first, dataset, runtime, alpha=.0025); first.freeze()
            directory = out/'models'/f'life_{identity}'/f'bank_{contexts[task]}'
            version = save_version(first, source, identity, contexts[task], 'FIRST_LOCAL', 0,
                directory/'FIRST_LOCAL_v0.npz')
            heads[task], versions[task], setups[task] = {'FIRST_LOCAL':first}, {arm:version for arm in UPDATING_ARMS}, {'FIRST_LOCAL':setup}
            for arm in UPDATING_ARMS:
                leaf, setup = _new_head(template, 'LOCAL_RISK', runtime, first); leaf.freeze()
                heads[task][arm] = leaf; setups[task][arm] = setup
            initial[task] = dict(context_route=route, context_id=contexts[task], planning_belief=belief,
                acquisition=acquired['acquisition'], dataset=compact_dataset(dataset),
                first_fits={'FIRST_LOCAL':fit}, head_versions={'FIRST_LOCAL':version}, head_version=version,
                evaluations={'SOURCE':_evaluate(template,identity,task,belief,runtime,engine),
                    'FIRST_LOCAL':_evaluate(first,identity,task,belief,runtime,engine,version)})
            recorded(dict(kind='INITIAL_HEADS', lifecycle=identity, parent=source['parent'], task=task,
                head_versions={'FIRST_LOCAL':version}))
            print(json.dumps(dict(event='win_learning_initial_complete',lifecycle=identity,task=task)),flush=True)
            del acquired, dataset
        row['initial_context_precondition_met'] = len(set(contexts.values())) == 2
        if not row['initial_context_precondition_met']:
            raise CohortHold('HOLD_INITIAL_BANK', 'New FIRST banks are not distinct')
        for number in (1, 2):
            rounds[str(number)] = {}
            for task in TASKS:
                other = 'B' if task == 'A' else 'A'
                inactive_before = deepcopy(versions[other])
                first, teacher_version = heads[task]['FIRST_LOCAL'], initial[task]['head_version']
                belief = initial[task]['planning_belief']; p = belief['estimated_p_four']
                acquired = acquire_policy_data(first, identity, source['parent'], 'FIXED_FIRST', p,
                    PROBABILITIES[task], collection_seed(identity,task,number), f'{task}_R{number}',
                    recorded, runtime, raw_budget=ROUND_RAW, actor_version=teacher_version, task=task)
                dataset = acquired['dataset']
                collector = dict(acquisition=acquired['acquisition'],
                    dataset={k:v for k,v in compact_dataset(dataset).items() if k != 'postspawn_boards'},
                    actor_version=deepcopy(teacher_version))
                stage = dict(groups=GROUPS, replicas=REPLICAS, teacher_version=deepcopy(teacher_version),
                    collectors={'FIXED_FIRST':collector}, arms={}, inactive_head_versions_before=inactive_before)
                rounds[str(number)][task] = stage
                try:
                    anchors = prepare_anchors(dataset, GROUPS)
                except ValueError as error:
                    if str(error) != 'V319 insufficient eligible complete FIT anchors for the frozen census': raise
                    raise CohortHold('HOLD_CENSUS', str(error)) from error
                queried = query_roots(first, anchors['preboards'], selection_seed(identity,task,number), runtime, p_model=p)
                if not np.array_equal(queried['chosen_afterstates'], anchors['natural_roots']):
                    raise ValueError('V326 actual FIRST H2 must reproduce every newly collected natural root')
                valid = np.flatnonzero(queried['validmask'])
                if len(valid) < GROUPS:
                    stage['census'] = dict(query=_compact(queried), anchor_counts=anchors['counts'],
                        anchor_cpu_seconds=anchors['cpu_seconds'], selected_groups=0, available_groups=len(valid))
                    raise CohortHold('HOLD_CENSUS', 'Insufficient valid new actual-query anchors')
                positions = valid[np.linspace(0,len(valid)-1,GROUPS,dtype=np.int64)]
                directory = out/'models'/f'life_{identity}'/f'bank_{contexts[task]}'
                metadata = dict(schema='acfqp.terminal_win_census.v326', lifecycle=identity, parent=source['parent'],
                    task=task, round=number, groups=GROUPS, anchors=2*GROUPS, teacher_version=teacher_version,
                    selection_seed=selection_seed(identity,task,number), planning_probability=p,
                    selection_rule=queried['selection_rule'], source_batch=dict(actor_version=teacher_version,
                        batch_id=f'{task}_R{number}', fit_step_end=dataset['fit_step_end'], fit_game_count=dataset['fit_game_count'],
                        stream_seed=collector['acquisition']['training']['before_stream']['stream_seed']))
                census = _artifact(directory/f'census_R{number}.npz',metadata,anchor_indices=anchors['indices'],
                    validmask=queried['validmask'], query_ordinals=queried['provenance'][:,4],
                    query_counts=queried['provenance'][:,5], selected_positions=positions,
                    selected_provenance=queried['provenance'][positions])
                census.update(anchor_counts=anchors['counts'],anchor_cpu_seconds=anchors['cpu_seconds'],
                    query=_compact(queried),selected_groups=GROUPS)
                stage['census'] = census
                roots = np.ascontiguousarray(queried['root_afterstates'][positions],dtype=np.int32)
                labels = supervise(first,roots,PROBABILITIES[task],draw_seed(identity,task,number),runtime,REPLICAS)
                stage['shared_supervision'] = _compact(labels)
                seeds = np.asarray([[rollout_seed(identity,task,number,g,m) for m in range(REPLICAS)]
                    for g in range(GROUPS)],dtype=np.uint64)
                continuation = continue_targets(first,roots,labels['spawn_cells'],labels['spawn_ranks'],
                    labels['selected_action'],labels['targetkind'],seeds,runtime,
                    directory/f'R{number}_terminal_trace.npz',p_model=p,p_true=PROBABILITIES[task],max_steps=MAX_STEPS)
                outcome_metadata = dict(schema='acfqp.terminal_win_outcome.v326',lifecycle=identity,parent=source['parent'],
                    task=task,round=number,groups=GROUPS,members=REPLICAS,teacher_version=teacher_version,
                    p_model=p,p_true=PROBABILITIES[task],max_steps=MAX_STEPS,
                    continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
                outcome = _artifact(directory/f'R{number}_terminal_outcome.npz',outcome_metadata,
                    rollout_seeds=seeds,**{k:continuation[k] for k in OUTCOME_FIELDS})
                stage['continuation'] = dict(_compact(continuation),outcome_artifact=outcome)
                stage['terminal_status_counts'] = {name:int(np.count_nonzero(continuation['status']==code))
                    for name,code in (('WON',1),('LOST',-1),('CUTOFF',0))}
                group_metadata = dict(schema='acfqp.terminal_win_groups.v326',lifecycle=identity,parent=source['parent'],
                    task=task,round=number,groups=GROUPS,replicas=REPLICAS,
                    sampling_unit='ROOTGROUP_FOUR_SHARED_FRESH_GROUND_SPAWNS',teacher_version=teacher_version,
                    draw_seed=draw_seed(identity,task,number),true_probability=PROBABILITIES[task],
                    census_file=census['file'],target_rule=labels['target_rule'])
                artifact = _artifact(directory/f'R{number}_shared_groups.npz',group_metadata,roots=roots,
                    **{k:labels[k] for k in ('targetreward','targetwin','selected_action','targetkind','spawn_cells','spawn_ranks')},
                    mean_reward=np.mean(labels['targetreward'],axis=1),mean_win=np.mean(labels['targetwin'],axis=1),
                    terminal_win=continuation['win'],mean_terminal_win=np.mean(continuation['win'],axis=1))
                stage['shared_supervision']['group_artifact'] = artifact
                if stage['terminal_status_counts']['CUTOFF']:
                    raise CohortHold('HOLD_TERMINAL_CUTOFF','A terminal WIN member remains active at the frozen horizon')
                print(json.dumps(dict(event='terminal_labels_complete',lifecycle=identity,task=task,round=number,
                    rollouts=GROUPS*REPLICAS,new_raw_tiles=int(continuation['new_raw_tiles'].sum()),
                    bootstrap_mean_win=float(labels['targetwin'].mean()),terminal_mean_win=float(continuation['win'].mean()))),flush=True)
                for arm in UPDATING_ARMS:
                    targets = labels['targetwin'] if arm == 'BOOTSTRAP_WIN' else continuation['win']
                    leaf = heads[task][arm]; before = leaf.updates; previous = snapshot_weights(leaf)
                    leaf.risk_weights.flags.writeable = True
                    fit = fit_replay(leaf,roots,targets,runtime); leaf.freeze()
                    reward_unchanged = np.array_equal(leaf.reward_weights,first.reward_weights)
                    if not reward_unchanged or leaf.updates-before != GROUPS*EPOCHS:
                        raise ValueError('V326 must update only private WIN with exactly the declared replay quota')
                    version = save_version(leaf,source,identity,contexts[task],arm,number,
                        directory/f'{arm}_v{number}.npz',base=versions[task][arm],previous=previous)
                    if version['reward_indices_count'] != 0:
                        raise ValueError('V326 sparse learned versions cannot contain reward writes')
                    del previous
                    versions[task][arm] = version
                    stage['arms'][arm] = dict(supervision=dict(group_artifact=artifact,
                        target_field='targetwin' if arm == 'BOOTSTRAP_WIN' else 'terminal_win'),fit=fit,
                        updates_before=before,updates_after=leaf.updates,head_version=version,reward_unchanged=reward_unchanged,
                        evaluations=_evaluate(leaf,identity,task,belief,runtime,engine,version))
                    recorded(dict(kind='CONSOLIDATED_HEAD',lifecycle=identity,parent=source['parent'],task=task,
                        round_index=number,arm=arm,quota=GROUPS*EPOCHS,head_version=version,fit=fit))
                stage['teacher_unchanged'] = first.updates == teacher_version['updates'] and not first.reward_weights.flags.writeable and not first.risk_weights.flags.writeable
                stage['inactive_head_versions_after'] = deepcopy(versions[other])
                if not stage['teacher_unchanged'] or versions[other] != inactive_before:
                    raise ValueError('V326 changed the immutable teacher or inactive task bank')
                print(json.dumps(dict(event='win_learning_round_complete',lifecycle=identity,task=task,round=number)),flush=True)
                del acquired, dataset
    except (CohortHold, ValueError) as error:
        if not isinstance(error,CohortHold) and not cutoff_seen:
            raise
        row['failure'] = dict(kind=error.kind if isinstance(error,CohortHold) else 'HOLD_TRAINING_CUTOFF',
            reason=str(error),task=task,round=number)
        recorded(dict(kind='COHORT_HOLD',lifecycle=identity,parent=source['parent'],failure=row['failure']))
    row['private_head_weight_bytes'] = sum(s['private_weight_bytes'] for values in setups.values() for s in values.values())
    return row


def _run_parent(source, out):
    cpu, started, compiler = process_time(), perf_counter(), _child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    engine = NativeValueStream(template,3268000000000+source['parent'],runtime)
    trace = out/f"parent_{source['parent']}_trace.jsonl.gz"
    rows, raw_by_phase, count = [], Counter(), 0
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(value):
                nonlocal count
                stream.write(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n'); count += 1
                raw_by_phase[value.get('phase','NONE')] += len(value.get('raw_spawns',()))
            for identity in range(source['parent'],LIVES,4):
                row = _run_life(template,source,identity,runtime,out,engine,emit)
                rows.append(row); stream.flush()
                _save(out/'lifecycle_receipts'/f'life_{identity}.json',row)
                if 'failure' in row: break
    finally:
        engine.close()
    return dict(parent=source['parent'],status='COHORT_HOLD' if any('failure' in r for r in rows) else 'COMPLETE',
        lifecycles=rows,source_setup=setup,canonical_rows=count,paid_raw_by_phase=dict(raw_by_phase),
        paid_factual_raw_tiles=sum(raw_by_phase.values()),trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def accounting(source_costs, lives, parents, cpu, wall):
    initial = [i for r in lives for i in r['initial'].values() if 'head_version' in i]
    stages = [s for r in lives for tasks in r['rounds'].values() for s in tasks.values()]
    evaluations = [e for i in initial for e in i['evaluations'].values()]
    evaluations += [i['evaluations'] for s in stages for i in s['arms'].values()]
    collectors = [s['collectors']['FIXED_FIRST'] for s in stages]
    census = [s['census'] for s in stages if 'census' in s]
    queries = [s['query'] for s in census]
    labels = [s['shared_supervision'] for s in stages if 'shared_supervision' in s]
    tails = [s['continuation'] for s in stages if 'continuation' in s]
    factual = sum(p['paid_factual_raw_tiles'] for p in parents)
    initial_raw = sum(sum(v for phase,v in p['paid_raw_by_phase'].items() if phase in ('A0','B0')) for p in parents)
    starts = sum(v['counts']['supervision_start_spawns'] for v in labels)
    tail_raw = sum(v['environment_counts'].get('raw_tile_productions',0) for v in tails)
    inherited_raw = source_costs['source_training_raw_tiles']+source_costs['dynamics_raw_tiles']
    perarm = {}
    for arm in UPDATING_ARMS:
        values = [s['arms'][arm] for s in stages if arm in s['arms']]
        perarm[arm] = dict(distinct_rootgroups=sum(v['fit']['distinct_rootgroups'] for v in values),
            rootgroup_updates=sum(v['fit']['fitted_rootgroups'] for v in values),
            economic_shared_factual_raw_tiles=factual,economic_shared_first_spawn_raw_tiles=starts,
            additional_terminal_raw_tiles=tail_raw if arm == 'TERMINAL_WIN' else 0,
            economic_training_raw_tiles=inherited_raw+factual+starts+(tail_raw if arm=='TERMINAL_WIN' else 0),
            fit_counts=sum_counts(v['fit']['learning_counts'] for v in values),
            normalization_counts=sum_counts(v['fit']['normalization_counts'] for v in values),
            target_counts=sum_counts(v['fit']['target_counts'] for v in values),
            fit_representation_counts=sum_counts(v['fit']['representation_counts'] for v in values),
            fit_cpu_seconds=sum(v['fit']['cpu_seconds'] for v in values))
    worker=sum(p['cpu_seconds'] for p in parents); compiler=sum(p['compiler_cpu_seconds'] for p in parents)
    component=worker+compiler+cpu
    updates=[v for s in stages for v in s['arms'].values()]
    versions=[i['head_version'] for i in initial]+[v['head_version'] for v in updates]
    groups=[v['group_artifact'] for v in labels if 'group_artifact' in v]
    return dict(inherited_source_costs=deepcopy(source_costs),source_training_repeated=False,
        old_target_data_reused=False,new_target_learning_histories=True,equal_total_raw_efficiency_test=False,
        new_initial_raw_tiles=initial_raw,new_post_factual_raw_tiles=factual-initial_raw,
        shared_first_spawn_raw_tiles=starts,additional_terminal_raw_tiles=tail_raw,
        terminal_rollouts=sum(v['counts'].get('rollouts_started',0) for v in tails),
        terminal_status_counts={name:sum(s.get('terminal_status_counts',{}).get(name,0) for s in stages)
            for name in ('WON','LOST','CUTOFF')},
        new_training_raw_tiles=factual+starts+tail_raw,per_arm=perarm,
        economic_training_raw_tiles_per_arm={'SOURCE':inherited_raw,'FIRST_LOCAL':inherited_raw+initial_raw,
            **{a:v['economic_training_raw_tiles'] for a,v in perarm.items()}},
        initial_fit_cpu_seconds=sum(i['first_fits']['FIRST_LOCAL']['cpu_seconds'] for i in initial),
        initial_acquisition_cpu_seconds=sum(i['acquisition']['cpu_seconds'] for i in initial),
        post_acquisition_cpu_seconds=sum(c['acquisition']['cpu_seconds'] for c in collectors),
        physical_census_query_counts=sum_counts(q['counts'] for q in queries),
        physical_census_planning_counts=sum_counts(q['planning_counts'] for q in queries),
        physical_census_representation_counts=sum_counts(q['representation_counts'] for q in queries),
        shared_supervision_counts=sum_counts(v['counts'] for v in labels),
        shared_supervision_environment_counts=sum_counts(v['environment_counts'] for v in labels),
        shared_supervision_planning_counts=sum_counts(v['planning_counts'] for v in labels),
        shared_supervision_representation_counts=sum_counts(v['representation_counts'] for v in labels),
        shared_supervision_cpu_seconds=sum(v['cpu_seconds'] for v in labels),
        continuation_environment_counts=sum_counts(v['environment_counts'] for v in tails),
        continuation_planning_counts=sum_counts(v['planning_counts'] for v in tails),
        continuation_representation_counts=sum_counts(v['representation_counts'] for v in tails),
        continuation_counts=sum_counts(v['counts'] for v in tails),
        continuation_cpu_seconds=sum(v['cpu_seconds'] for v in tails),
        new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),
        new_evaluation_planning_counts=sum_counts(e['counts']['planning'] for e in evaluations),
        split_evaluation_representation_counts=sum_counts(e.get('representation_counts',{}) for e in evaluations),
        representation_scope='SPLIT_HEADS_ONLY_SOURCE_HAS_PLANNING_COUNTS',
        new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),
        new_head_files=len(versions),new_head_saved_bytes=sum(v['saved_bytes'] for v in versions),
        group_files=len(groups),group_saved_bytes=sum(v['saved_bytes'] for v in groups),
        census_files=sum('file' in c for c in census),census_saved_bytes=sum(c.get('saved_bytes',0) for c in census),
        terminal_trace_files=len(tails),terminal_trace_saved_bytes=sum(v['trace_artifact']['compressed_bytes'] for v in tails),
        terminal_outcome_files=len(tails),terminal_outcome_saved_bytes=sum(v['outcome_artifact']['saved_bytes'] for v in tails),
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_experiment_component_cpu_seconds=component,wall_seconds=wall,
        inherited_successful_source_full_cpu_seconds=source_costs['fresh_source_compute']['full_source_cpu_seconds'],
        economic_source_and_experiment_component_cpu_seconds=source_costs['fresh_source_compute']['full_source_cpu_seconds']+component,
        cost_scope='All new acquisition/processing/labels/terminal suffixes/replay fits/restores/saves/evaluation/compiler/coordinator '
            'work once; complete execution adds serialization and shutdown. Shared facts/query/first spawns physical once, '
            'economically per learner; suffix raw only TERMINAL. Successful V312 SOURCE inherited once; previous target '
            'experiments excluded; audits and unknown historical dynamics separate. Label ablation, not equal-total-raw efficiency.')


def run(source_summary, output):
    cpu, started = process_time(), perf_counter()
    out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V326 is already frozen')
    source_path = Path(source_summary).resolve(); source = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    if source['status'] != 'SOURCE_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V326 requires the audited V312 frozen SOURCE')
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,p,out) for p in source['source_provenance']['parents']]):
            result = job.result(); parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k != 'lifecycles'})
    parents.sort(key=lambda p:p['parent'])
    lives = sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis = summarize(lives)
    failures = [r['failure'] for r in lives if 'failure' in r]
    status = 'COHORT_HOLD' if failures else 'EXPERIMENT_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF'
    result = dict(schema='acfqp.terminal_win.v326',status=status,
        scientific_gate='TERMINAL_TARGET_LEARNING_UNDER_FIXED_SOURCES_NOT_U006',settings=settings,
        source_summary=str(source_path),source_provenance=source['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k != 'lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(source['accounting']['inherited_costs_per_arm']['SOURCE'],lives,parents,
            process_time()-cpu,perf_counter()-started))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='win_learning_complete',status=status,primary=analysis['primary_status'],
        retained=analysis['retained_improvement_supported'])),flush=True)
    return result
