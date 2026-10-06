"""Saved WIN supervision and actual snapshots against fresh FIRST terminal truth."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .native_teacher_calibration_v320 import continue_targets
from .natural_model_revision_v281 import load_leaf
from .query_supervision_run_v319 import _restore_first, _artifact, _compact, _save
from .reward_targets_run_v321 import _apply_delta
from .teacher_calibration_run_v320 import _read_groups, _groups_json
from .win_terminal_analysis_v325 import summarize
from .win_terminal_prediction_v325 import predict_win

TASKS, ARMS = ('A', 'B'), ('FACTUAL_WIN', 'QUERY_WIN')
GROUPS, MEMBERS, OLD_GROUPS = 64, 4, 16384
SNAPSHOTS = ('FIRST', 'v1', 'v2')
OUTCOME_FIELDS = ('scores', 'actions', 'status', 'new_raw_tiles', 'final_boards', 'reward_return', 'win', 'utility')


def group_indices():
    return np.linspace(0, OLD_GROUPS-1, GROUPS, dtype=np.int64)


def rollout_seed(life, task, number, group, member):
    return 325500000000+life*10000000+TASKS.index(task)*1000000+number*100000+int(group)*4+member


def configuration(source):
    return dict(schema='acfqp.win_terminal_freeze.v325', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/WIN_TERMINAL_V325.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS), arms=list(ARMS), rounds=[1,2],
        original_groups=OLD_GROUPS, groups=GROUPS, members=MEMBERS, selected_group_indices=group_indices().tolist(),
        selection='PREDECLARED_COMMON_EQUIDISTANT_ORIGINAL_GROUP_POSITIONS',
        teacher='ACTUAL_IMMUTABLE_V324_FIRST_LOCAL_V0', planning_belief='ACTUAL_IMMUTABLE_V324_FIRST_BANK_BELIEF',
        true_probabilities={'A':.1,'B':.5}, targets='V324_SAVED_FIRST_ONE_STEP_DIRECT_WIN',
        continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2',
        prediction='ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_UNCHANGED_STABLE_SIGMOID',
        prediction_snapshots=list(SNAPSHOTS), prediction_reads='THREE_UNIQUE_SNAPSHOTS_PER_CELL_BEFORE_AFTER_FINAL_ALIASES',
        own_versions='SOURCE_THEN_ACTUAL_FIRST_V0_THEN_OWN_WIN_V1_THEN_V2_REWARD_UNCHANGED',
        terminal_truth='COMMON_FROZEN_FIRST_POLICY_MEMBER_WIN_NOT_UPDATED_POLICY_VALUE',
        return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
        spawn='NEW_SPAWN_AFTER_EVERY_EXECUTED_ACTION_INCLUDING_WIN', max_steps=8192,
        seed_continuation=325500000000, life_stride=10000000, task_stride=1000000,
        round_stride=100000, group_stride=4, seed_pairing='SAME_ORIGINAL_GROUP_MEMBER_SEEDS_BOTH_ARMS',
        expected_rollouts=16*2*2*2*GROUPS*MEMBERS, fit_updates=0,
        primary='FINAL_QUERY_WIN_MINUS_FIRST_BRIER_ON_QUERY_ROOTS', primary_direction='LOWER_IS_BETTER',
        bootstrap_draws=20000, bootstrap_seed=32500001,
        stop_rule='ANY_CUTOFF_WHOLE_COHORT_HOLD_NO_REPLACEMENT_OR_TERMINAL_WIN_IMPUTATION',
        evidence_scope='FIXED_V324_TRAINING_ROOTS_FRESH_SUFFIXES_FIRST_POLICY_PREDICTION_DIAGNOSTIC_NOT_LEARNING_CAUSAL_TEST')


def _versions(first, old, task, arm, number):
    v1 = old['rounds']['1'][task]['arms'][arm]['head_version']
    v2 = old['rounds']['2'][task]['arms'][arm]['head_version']
    return dict(FIRST=first, before=first if number == 1 else v1, after=v1 if number == 1 else v2, FINAL=v2)


def _run_life(template, source, old, runtime, out):
    life = old['lifecycle']; indices = group_indices()
    initial, setups, stages = {}, {}, {'1':{}, '2':{}}
    for task in TASKS:
        original = old['initial'][task]; version = original['head_version']
        first, setup = _restore_first(template,version,runtime)
        initial[task] = dict(teacher_version=deepcopy(version),planning_belief=deepcopy(original['planning_belief']))
        setups[task] = {'FIRST':setup,'arms':{}}
        p_model = original['planning_belief']['estimated_p_four']; p_true = .1 if task == 'A' else .5
        for number in (1,2):
            stages[str(number)][task] = dict(teacher_version=deepcopy(version),teacher_unchanged=True,
                groups=GROUPS,replicas=MEMBERS,selected_group_indices=indices.tolist(),arms={})
        for arm in ARMS:
            selected, reads, predictions = {}, {}, {}
            for number in (1,2):
                receipt = old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']
                selected[number], reads[number] = _read_groups(receipt,indices)
                predictions[number] = {'FIRST':predict_win(first,selected[number]['roots'])}
            learner, learner_setup = _new_head(template,'LOCAL_RISK',runtime,first); learner.freeze()
            learner_setup['delta_restores'] = []
            for snapshot, number in (('v1',1),('v2',2)):
                actual = old['rounds'][str(number)][task]['arms'][arm]['head_version']
                if actual['reward_indices_count'] != 0:
                    raise ValueError('V325 actual WIN-only versions cannot contain reward writes')
                learner_setup['delta_restores'].append(_apply_delta(learner,actual))
                if not np.array_equal(learner.reward_weights,first.reward_weights):
                    raise ValueError('V325 full actual reward table must remain FIRST across the WIN chain')
                for stage_number in (1,2):
                    predictions[stage_number][snapshot] = predict_win(learner,selected[stage_number]['roots'])
            setups[task]['arms'][arm] = learner_setup
            del learner
            for number in (1,2):
                data = selected[number]
                seeds = np.asarray([[rollout_seed(life,task,number,g,m) for m in range(MEMBERS)] for g in indices],dtype=np.uint64)
                directory = out/'continuations'/f'life_{life}'/task
                trace = directory/f'{arm}_R{number}_trace.npz'
                result = continue_targets(first,data['roots'],data['spawn_cells'],data['spawn_ranks'],
                    data['selected_action'],data['targetkind'],seeds,runtime,trace,
                    p_model=p_model,p_true=p_true,max_steps=8192)
                if first.updates != version['updates'] or first.reward_weights.flags.writeable or first.risk_weights.flags.writeable:
                    raise ValueError('V325 continuations changed the actual FIRST teacher')
                prediction_versions = _versions(version,old,task,arm,number)
                metadata = dict(schema='acfqp.win_terminal_outcome.v325',lifecycle=life,parent=source['parent'],
                    task=task,round=number,arm=arm,groups=GROUPS,members=MEMBERS,selected_group_indices=indices.tolist(),
                    source_group_file=old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']['file'],
                    teacher_version=deepcopy(version),prediction_snapshots=list(SNAPSHOTS),prediction_versions=prediction_versions,
                    p_model=p_model,p_true=p_true,max_steps=8192,
                    return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
                    continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
                probabilities = np.vstack([predictions[number][name]['probabilities'] for name in SNAPSHOTS])
                logits = np.vstack([predictions[number][name]['logits'] for name in SNAPSHOTS])
                artifact = _artifact(directory/f'{arm}_R{number}_outcome.npz',metadata,
                    original_group_indices=indices,rollout_seeds=seeds,
                    **{k:result[k] for k in OUTCOME_FIELDS},prediction_probabilities=probabilities,prediction_logits=logits)
                groups = _groups_json(data,result,indices,seeds)
                aliases = dict(FIRST=0,before=0 if number == 1 else 1,after=number,FINAL=2)
                for local, group in enumerate(groups):
                    group['predictions'] = {key:float(probabilities[index,local]) for key,index in aliases.items()}
                stages[str(number)][task]['arms'][arm] = dict(
                    source_group_artifact=old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact'],
                    source_read=reads[number],continuation=_compact(result),outcome_artifact=artifact,groups=groups,
                    prediction_versions=prediction_versions,
                    prediction_receipts={name:_compact(predictions[number][name]) for name in SNAPSHOTS})
                print(json.dumps(dict(event='win_terminal_cell_complete',lifecycle=life,task=task,round=number,arm=arm,
                    rollouts=GROUPS*MEMBERS,new_raw_tiles=int(result['new_raw_tiles'].sum()),
                    cutoffs=int(np.count_nonzero(result['status']==0)))),flush=True)
        del first
    row = dict(lifecycle=life,parent=source['parent'],initial=initial,head_setups=setups,stages=stages)
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    return row


def _run_parent(source, previous, out):
    cpu, started, compiler = process_time(), perf_counter(), _child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    rows = [_run_life(template,source,old,runtime,out) for old in previous['by_lifecycle'] if old['parent'] == source['parent']]
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,cpu_seconds=process_time()-cpu,
        compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def accounting(lives, parents, cpu, wall, inherited):
    perarm = {}
    for arm in ARMS:
        cells = [row['stages'][r][t]['arms'][arm] for row in lives for r in ('1','2') for t in TASKS]
        replicas = [rep for cell in cells for group in cell['groups'] for rep in group['replicas']]
        predictions = [p for c in cells for p in c['prediction_receipts'].values()]
        perarm[arm] = dict(rollouts=len(replicas),new_raw_tiles=sum(rep['new_raw_tiles'] for rep in replicas),
            reused_first_spawns=len(replicas),actions=sum(rep['actions'] for rep in replicas),
            terminal_counts={s:sum(rep['status']==s for rep in replicas) for s in ('WON','LOST','CUTOFF')},
            environment_counts=sum_counts(c['continuation']['environment_counts'] for c in cells),
            planning_counts=sum_counts(c['continuation']['planning_counts'] for c in cells),
            representation_counts=sum_counts(c['continuation']['representation_counts'] for c in cells),
            continuation_counts=sum_counts(c['continuation']['counts'] for c in cells),
            source_files_read=len(cells),source_file_bytes_referenced=sum(c['source_read']['source_file_bytes'] for c in cells),
            source_read_cpu_seconds=sum(c['source_read']['cpu_seconds'] for c in cells),
            continuation_cpu_seconds=sum(c['continuation']['cpu_seconds'] for c in cells),
            prediction_counts=sum_counts(p['counts'] for p in predictions),
            prediction_representation_counts=sum_counts(p['representation_counts'] for p in predictions),
            prediction_cpu_seconds=sum(p['cpu_seconds'] for p in predictions),unique_snapshot_cells=len(predictions),
            trace_files=len(cells),trace_saved_bytes=sum(c['continuation']['trace_artifact']['compressed_bytes'] for c in cells),
            outcome_files=len(cells),outcome_saved_bytes=sum(c['outcome_artifact']['saved_bytes'] for c in cells))
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    component = worker+compiler+cpu
    return dict(new_raw_tiles=sum(p['new_raw_tiles'] for p in perarm.values()),rollouts=sum(p['rollouts'] for p in perarm.values()),
        reused_first_spawns=sum(p['reused_first_spawns'] for p in perarm.values()),per_arm=perarm,
        fit_updates=0,new_head_files=0,new_evaluation_games=0,source_training_repeated=False,
        first_adaptation_repeated=False,prior_full_audit_repeated=False,
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_calibration_component_cpu_seconds=component,wall_seconds=wall,
        inherited_successful_source_v324_full_cpu_seconds=inherited,
        economic_source_v324_and_calibration_component_cpu_seconds=inherited+component,
        scope='Successful SOURCE/V324 inherited once. No old fitting/first spawns/whole-game evaluation/prior audit repeated. '
            'All actual reads/restores/three snapshot predictions/variable suffixes/IO/compiler/coordinator work once; '
            'full execution adds final serialization/shutdown. Audit separate; historical dynamics and failed-attempt CPU unknown.')


def run(source_summary, output):
    cpu, started = process_time(), perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V325 is already frozen')
    source_path = Path(source_summary).resolve(); previous = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    execution = json.loads((source_path.parent/'execution.json').read_text())
    if previous['status'] != 'EXPERIMENT_COMPLETE' or not audit['independent_valid'] or execution['exit_code'] != 0:
        raise ValueError('V325 requires the audited completed V324 learning history')
    inherited = json.loads((source_path.parent/'audit_costs.json').read_text())['full_economic_source_and_experiment_cpu_seconds']
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,previous,out) for s in previous['source_provenance']['parents']]):
            result = job.result(); parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k != 'lifecycles'})
    parents.sort(key=lambda p:p['parent'])
    lives = sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.win_terminal.v325',status='DIAGNOSTIC_COMPLETE' if analysis['complete_terminal_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='WIN_TERMINAL_CALIBRATION_NOT_LEARNING_OR_U006_GATE',settings=settings,source_summary=str(source_path),
        source_provenance=previous['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k != 'lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(lives,parents,process_time()-cpu,perf_counter()-started,inherited))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='win_terminal_complete',status=result['status'],primary=analysis['primary_status'])),flush=True)
    return result
