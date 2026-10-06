"""Fixed V319 starts and DIRECT branches followed by frozen FIRST H2 to terminal."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu
from .natural_model_revision_v281 import load_leaf
from .query_supervision_run_v319 import _restore_first
from .native_teacher_calibration_v320 import continue_targets
from .teacher_calibration_analysis_v320 import summarize

TASKS = ('A','B')
ARMS = ('FACTUAL_LOCAL','QUERY_LOCAL')
GROUPS, MEMBERS, OLD_GROUPS = 64, 4, 16384
STATUS = {1:'WON', -1:'LOST', 0:'CUTOFF'}


def _save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def group_indices():
    return np.linspace(0, OLD_GROUPS-1, GROUPS, dtype=np.int64)


def rollout_seed(life, task, number, group, member):
    return 320500000000+life*10000000+TASKS.index(task)*1000000+number*100000+int(group)*4+member


def configuration(source):
    return dict(schema='acfqp.teacher_calibration_freeze.v320', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/TEACHER_CALIBRATION_V320.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS), arms=list(ARMS), rounds=[1,2],
        original_groups=OLD_GROUPS, groups=GROUPS, members=MEMBERS, selected_group_indices=group_indices().tolist(),
        selection='PREDECLARED_COMMON_EQUIDISTANT_ORIGINAL_GROUP_POSITIONS',
        prefix_proposal='NOT_RUN_REPLACED_BEFORE_ACQUISITION_BY_EQUIDISTANT_DIAGNOSTIC_POSITIONS',
        teacher='ACTUAL_IMMUTABLE_V317_FIRST_LOCAL_V0', planning_belief='ACTUAL_IMMUTABLE_V319_FIRST_BANK_BELIEF',
        true_probabilities={'A':.1,'B':.5}, targets='V319_SAVED_FIRST_ONE_STEP_DIRECT_R_AND_W',
        continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2',
        return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
        spawn='NEW_SPAWN_AFTER_EVERY_EXECUTED_ACTION_INCLUDING_WIN', max_steps=8192,
        seed_continuation=320500000000, life_stride=10000000, task_stride=1000000,
        round_stride=100000, group_stride=4, seed_pairing='SAME_ORIGINAL_GROUP_MEMBER_SEEDS_BOTH_ARMS',
        expected_rollouts=16*2*2*2*GROUPS*MEMBERS, fit_updates=0,
        primary='QUERY_MINUS_FACTUAL_SIGNED_COMBINED_TEACHER_ERROR', bootstrap_draws=20000, bootstrap_seed=32000001,
        stop_rule='ANY_CUTOFF_WHOLE_COHORT_HOLD_NO_REPLACEMENT_OR_TERMINAL_WIN_IMPUTATION',
        evidence_scope='FIXED_EXISTING_FIRST_COHORT_AND_COMMON_POSITION_GRID_TEACHER_CALIBRATION_NOT_LEARNING_CAUSAL_TEST')


def _read_groups(receipt, indices):
    started, cpu = perf_counter(), process_time()
    path = Path(receipt['file'])
    fields = ('roots','spawn_cells','spawn_ranks','selected_action','targetkind','targetreward','targetwin')
    with np.load(path, allow_pickle=False) as saved:
        metadata = json.loads(str(saved['metadata_json']))
        if metadata != receipt['metadata']: raise ValueError('V320 retained group metadata differs from audited V319')
        arrays = {key:np.ascontiguousarray(saved[key][indices]) for key in fields}
    return arrays, dict(file=str(path), source_file_bytes=path.stat().st_size,
        selected_array_bytes=sum(a.nbytes for a in arrays.values()), new_raw_tiles=0,
        cpu_seconds=process_time()-cpu, wall_seconds=perf_counter()-started)


def _outcome(path, arrays, indices, seeds, metadata):
    started, cpu = perf_counter(), process_time()
    path.parent.mkdir(parents=True, exist_ok=True)
    values = dict(original_group_indices=indices, rollout_seeds=seeds,
        **{k:arrays[k] for k in ('scores','actions','status','new_raw_tiles','final_boards','reward_return','win','utility')})
    np.savez_compressed(path, **values, metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False))
    return dict(file=str(path.resolve()), metadata=metadata, saved_bytes=path.stat().st_size,
        array_bytes=sum(v.nbytes for v in values.values()), save_cpu_seconds=process_time()-cpu,
        save_wall_seconds=perf_counter()-started)


def _groups_json(old, result, indices, seeds):
    groups = []
    for local, index in enumerate(indices):
        replicas = []
        for member in range(MEMBERS):
            status = STATUS[int(result['status'][local,member])]
            replicas.append(dict(teacher_reward=float(old['targetreward'][local,member]),
                teacher_win=float(old['targetwin'][local,member]),
                actual_reward=None if status=='CUTOFF' else float(result['reward_return'][local,member]),
                actual_win=None if status=='CUTOFF' else int(result['win'][local,member]),
                status=status, seed=int(seeds[local,member]), score=int(result['scores'][local,member]),
                actions=int(result['actions'][local,member]), new_raw_tiles=int(result['new_raw_tiles'][local,member])))
        groups.append(dict(index=int(index),replicas=replicas))
    return groups


def _run_life(template, source, old, runtime, out):
    life = old['lifecycle']; indices = group_indices(); heads, initial, setups, stages = {}, {}, {}, {}
    for task in TASKS:
        first = old['initial'][task]; version = first['head_version']
        heads[task], setups[task] = _restore_first(template,version,runtime)
        initial[task] = dict(teacher_version=version, planning_belief=deepcopy(first['planning_belief']))
    for number in (1,2):
        stages[str(number)] = {}
        for task in TASKS:
            first = heads[task]; teacher = initial[task]['teacher_version']; before = first.updates
            p_model = initial[task]['planning_belief']['estimated_p_four']; probability = .1 if task=='A' else .5
            seeds = np.asarray([[rollout_seed(life,task,number,g,m) for m in range(MEMBERS)]
                for g in indices], dtype=np.uint64)
            arms = {}
            for arm in ARMS:
                receipt = old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']
                data, read = _read_groups(receipt,indices)
                directory = out/'continuations'/f'life_{life}'/task
                trace = directory/f'{arm}_R{number}_trace.npz'
                result = continue_targets(first,data['roots'],data['spawn_cells'],data['spawn_ranks'],
                    data['selected_action'],data['targetkind'],seeds,runtime,trace,
                    p_model=p_model,p_true=probability,max_steps=8192)
                if first.updates!=before or first.reward_weights.flags.writeable or first.risk_weights.flags.writeable:
                    raise ValueError('V320 continuations changed the frozen actual FIRST teacher')
                metadata = dict(schema='acfqp.teacher_calibration_outcome.v320',lifecycle=life,parent=source['parent'],
                    task=task,round=number,arm=arm,groups=GROUPS,members=MEMBERS,
                    selected_group_indices=indices.tolist(),source_group_file=receipt['file'],teacher_version=teacher,
                    p_model=p_model,p_true=probability,max_steps=8192,
                    return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
                    continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
                artifact = _outcome(directory/f'{arm}_R{number}_outcome.npz',result,indices,seeds,metadata)
                compact = {k:v for k,v in result.items() if not isinstance(v,np.ndarray)}
                arms[arm] = dict(source_group_artifact=receipt, source_read=read, continuation=compact,
                    outcome_artifact=artifact, groups=_groups_json(data,result,indices,seeds))
                print(json.dumps(dict(event='teacher_calibration_cell_complete',lifecycle=life,task=task,
                    round=number,arm=arm,rollouts=GROUPS*MEMBERS,new_raw_tiles=int(np.sum(result['new_raw_tiles'])),
                    cutoffs=int(np.count_nonzero(result['status']==0)))),flush=True)
            stages[str(number)][task] = dict(teacher_version=teacher,teacher_unchanged=True,groups=GROUPS,
                replicas=MEMBERS,selected_group_indices=indices.tolist(),arms=arms)
    row = dict(lifecycle=life,parent=source['parent'],initial=initial,head_setups=setups,stages=stages)
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    return row


def _run_parent(source, document, out):
    cpu, started, compiler = process_time(), perf_counter(), _child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    rows = [_run_life(template,source,old,runtime,out) for old in document['by_lifecycle'] if old['parent']==source['parent']]
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,cpu_seconds=process_time()-cpu,
        compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-started)


def accounting(previous, lives, parents, cpu, wall, inherited_full_cpu):
    perarm = {}
    for arm in ARMS:
        cells = [row['stages'][r][t]['arms'][arm] for row in lives for r in ('1','2') for t in TASKS]
        replicas = [rep for cell in cells for group in cell['groups'] for rep in group['replicas']]
        perarm[arm] = dict(rollouts=len(replicas),new_raw_tiles=sum(rep['new_raw_tiles'] for rep in replicas),
            reused_first_spawns=len(replicas), actions=sum(rep['actions'] for rep in replicas),
            terminal_counts={s:sum(rep['status']==s for rep in replicas) for s in ('WON','LOST','CUTOFF')},
            environment_counts=sum_counts(c['continuation']['environment_counts'] for c in cells),
            planning_counts=sum_counts(c['continuation']['planning_counts'] for c in cells),
            representation_counts=sum_counts(c['continuation']['representation_counts'] for c in cells),
            continuation_counts=sum_counts(c['continuation']['counts'] for c in cells),
            source_files_read=len(cells),source_file_bytes_referenced=sum(c['source_read']['source_file_bytes'] for c in cells),
            source_read_cpu_seconds=sum(c['source_read']['cpu_seconds'] for c in cells),
            continuation_cpu_seconds=sum(c['continuation']['cpu_seconds'] for c in cells),
            trace_files=len(cells),trace_saved_bytes=sum(c['continuation']['trace_artifact']['compressed_bytes'] for c in cells),
            outcome_files=len(cells),outcome_saved_bytes=sum(c['outcome_artifact']['saved_bytes'] for c in cells))
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    return dict(new_raw_tiles=sum(p['new_raw_tiles'] for p in perarm.values()),rollouts=sum(p['rollouts'] for p in perarm.values()),
        reused_first_spawns=sum(p['reused_first_spawns'] for p in perarm.values()),per_arm=perarm,
        fit_updates=0,source_training_repeated=False,first_adaptation_repeated=False,prior_full_audit_repeated=False,
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_calibration_component_cpu_seconds=worker+compiler+cpu,wall_seconds=wall,
        inherited_successful_source_v317_v319_full_cpu_seconds=inherited_full_cpu,
        economic_source_v317_v319_and_calibration_component_cpu_seconds=inherited_full_cpu+worker+compiler+cpu,
        scope='No source training, first adaptation, prior spawn production or fitting is repeated. All variable-length '
            'continuations and both arms actual work are paid. Component CPU includes read/setup/physics/planning/trace and outcome IO '
            'inside workers; complete process-tree execution CPU additionally measures final summary serialization and shutdown. '
            'Audit CPU is separate. Historical dynamics and failed-attempt CPU remain unknown.')


def run(source_summary, output):
    cpu, started = process_time(), perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V320 calibration is already frozen')
    source_path = Path(source_summary).resolve(); previous = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    execution = json.loads((source_path.parent/'execution.json').read_text())
    if previous['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid'] or execution['exit_code']!=0:
        raise ValueError('V320 requires the audited complete frozen V319 group evidence')
    inherited = json.loads((source_path.parent/'audit_costs.json').read_text())['full_economic_source_v317_and_experiment_cpu_seconds']
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,previous,out) for s in previous['source_provenance']['parents']]):
            result = job.result(); parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json",{k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent'])
    lives = sorted((row for p in parents for row in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.teacher_calibration.v320',status='DIAGNOSTIC_COMPLETE' if analysis['complete_terminal_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='TEACHER_CALIBRATION_NOT_LEARNING_OR_U006_GATE',settings=settings,source_summary=str(source_path),
        source_provenance=previous['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(previous,lives,parents,process_time()-cpu,perf_counter()-started,inherited))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='teacher_calibration_complete',status=result['status'],primary=analysis['primary_status'])),flush=True)
    return result
