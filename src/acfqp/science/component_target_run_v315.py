"""New paired evaluation of frozen, independently learned reward/WIN components."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import ctypes
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu
from .component_target_analysis_v315 import summarize
from .frozen_components_v315 import restore_head, combine_heads
from .native_split_risk_v301 import evaluate_split
from .natural_model_revision_v281 import load_leaf, MAX_STEPS, QUERY

TASKS = ('A', 'B')
PROBABILITIES = {'A': .1, 'B': .5}
ARMS = ('MC_MC', 'TD_MC', 'MC_TD', 'TD_TD', 'FIRST_LOCAL')
COMPONENTS = dict(MC_MC=('MC_LOCAL','MC_LOCAL'), TD_MC=('TD_LOCAL','MC_LOCAL'),
    MC_TD=('MC_LOCAL','TD_LOCAL'), TD_TD=('TD_LOCAL','TD_LOCAL'),
    FIRST_LOCAL=('FIRST_LOCAL','FIRST_LOCAL'))


def _save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def evaluation_seed(life, task, episode):
    return 315900000000+life*1000000+(100000 if task=='B' else 0)+episode


def configuration(prior_summary):
    return dict(schema='acfqp.component_target_freeze.v315',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/COMPONENT_TARGETS_V315.md'),
        prior_summary=str(Path(prior_summary).resolve()), lifecycles=list(range(16)),
        parents=4, workers=4, tasks=TASKS, arms=ARMS, components=COMPONENTS,
        true_probabilities=PROBABILITIES, source_versions='V314_FIRST_V0_MC_V2_TD_V2',
        planning_probability='V314_IMMUTABLE_FIRST_FIT_BANK_BELIEF',
        combination='EXACT_IMMUTABLE_ARRAY_REFERENCES_ZERO_WEIGHT_COPY',
        new_training_raw_tiles=0, new_fit_states=0, new_parameter_writes=0,
        query=QUERY, planner='H2', max_steps=MAX_STEPS,
        evaluation_games_per_cell=32, seed_evaluation=315900000000,
        expected_evaluation_games=5120, action_probes='FIRST_NEW_GAME_INITIAL_BOARD_PER_CELL',
        bootstrap_draws=20000, bootstrap_seed=31500001,
        mechanism_family=('reward_given_MC_WIN','reward_given_TD_WIN',
            'WIN_given_MC_reward','WIN_given_TD_reward','interaction'),
        mechanism_family_ci=.99, pointwise_ci=.95, multiplicity='BONFERRONI_FIVE_AB_CONTRASTS',
        evidence_scope='FROZEN_V314_TRAINING_INSTANCES_NEW_PAIRED_EVALUATION_ONLY',
        stop_rule='NO_ARM_SEED_FIT_BUDGET_OR_INTERVAL_SELECTION_RETAIN_ALL_ENDPOINTS')


def _initial_probe(leaf, seed, probability, planning_probability):
    """Use the same native mt19937_64 uniforms as the actual evaluation initializer."""
    cpu, started = process_time(), perf_counter()
    draws = np.empty((2,2),dtype=np.float64)
    function=leaf.library.native_common_draws_v285
    function.argtypes=[ctypes.c_uint64,ctypes.c_int,
        np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')]
    function.restype=None
    function(seed,2,draws)
    board=[0]*16; spawns=[]
    for cell_draw,rank_draw in draws:
        empty=[i for i,v in enumerate(board) if not v]
        cell=empty[int(cell_draw*len(empty))]; rank=1 if rank_draw<1.-probability else 2
        board[cell]=rank; spawns.append(dict(kind='INITIAL',cell=cell,rank=rank))
    chosen=leaf.choose(board,planning_probability)
    return dict(episode=0,seed=seed,board=board,initial_spawns=spawns,chosen=chosen,
        origin='NATIVE_NEW_EVALUATION_INITIAL_STATE_SAME_H2_ENTRYPOINT',
        cpu_seconds=process_time()-cpu,seconds=perf_counter()-started,
        repeated_initial_random_draws=4)


def _run_task(template, old_life, task, runtime):
    life=old_life['lifecycle']; initial=old_life['initial'][task]
    p=initial['planning_belief']['estimated_p_four']
    versions=dict(FIRST_LOCAL=initial['head_versions']['FIRST_LOCAL'],
        **{arm:old_life['rounds']['2'][task]['arms'][arm]['head_version']
           for arm in ('MC_LOCAL','TD_LOCAL')})
    heads, restorations={},{}
    for arm,version in versions.items():
        heads[arm],restorations[arm]=restore_head(template,version,runtime)
    evaluations,probes,components,states={},{},{},{}
    seeds=[evaluation_seed(life,task,e) for e in range(32)]
    for arm,(reward,win) in COMPONENTS.items():
        leaf=combine_heads(heads[reward],heads[win])
        components[arm]=dict(reward_version=deepcopy(versions[reward]),
            win_version=deepcopy(versions[win]))
        before=dict(reward_updates=heads[reward].updates,win_updates=heads[win].updates)
        probe=_initial_probe(leaf,seeds[0],PROBABILITIES[task],p)
        evaluations[arm]=dict(evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=MAX_STEPS),
            estimated_p_four=p,planner='H2')
        probes[arm]=[probe]
        after=dict(reward_updates=heads[reward].updates,win_updates=heads[win].updates)
        if before!=after or leaf.reward_weights.flags.writeable or leaf.risk_weights.flags.writeable:
            raise ValueError('V315 evaluation must leave both selected component tables frozen')
        states[arm]=dict(before=before,after=after,weight_copy_parameters=0,
            allocated_weight_bytes=0,weight_files_saved=0,new_fit_states=0,new_parameter_writes=0)
        print(json.dumps(dict(event='component_cell_complete',lifecycle=life,task=task,arm=arm)),flush=True)
    return dict(context_id=initial['context_id'],estimated_p_four=p,head_components=components,
        head_restorations=restorations,component_states=states,evaluations=evaluations,action_probes=probes)


def _run_parent(source, old_lives, output):
    cpu,started,compiler=process_time(),perf_counter(),_child_cpu()
    runtime=output/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime)
    lives=[]
    for old in old_lives:
        row=dict(lifecycle=old['lifecycle'],parent=source['parent'],
            tasks={task:_run_task(template,old,task,runtime) for task in TASKS})
        lives.append(row); _save(output/'lifecycle_receipts'/f"life_{row['lifecycle']}.json",row)
    return dict(parent=source['parent'],lifecycles=lives,source_setup=setup,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,
        wall_seconds=perf_counter()-started)


def build_accounting(prior, lives, parents, cpu, wall):
    tasks=[task for life in lives for task in life['tasks'].values()]
    evaluations=[value for task in tasks for value in task['evaluations'].values()]
    probes=[value for task in tasks for values in task['action_probes'].values() for value in values]
    restorations=[value for task in tasks for value in task['head_restorations'].values()]
    worker=sum(row['cpu_seconds'] for row in parents); compiler=sum(row['compiler_cpu_seconds'] for row in parents)
    inherited=prior['accounting']
    return dict(inherited_v314_accounting=deepcopy(inherited),
        prior_training_physical_repeated=False,new_training_raw_tiles=0,new_fit_states=0,new_parameter_writes=0,
        economic_training_raw_tiles_per_arm={arm:inherited['economic_training_raw_tiles_per_arm'][
            'FIRST_LOCAL' if arm=='FIRST_LOCAL' else 'TD_LOCAL'] for arm in ARMS},
        new_combination_weight_copy_parameters=0,new_combination_weight_bytes=0,new_weight_files=0,
        restored_head_instances=len(restorations),head_reconstruction_counts=sum_counts(
            item['counts'] for item in restorations),
        head_reconstruction_setup_counts=sum_counts(item['setup_counts'] for item in restorations),
        private_head_weight_bytes_peak=max(sum(item['private_weight_bytes'] for item in task['head_restorations'].values()) for task in tasks),
        head_reconstruction_cpu_seconds=sum(item['cpu_seconds'] for item in restorations),
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations),
        evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        evaluation_planning_counts=sum_counts(value['counts']['planning'] for value in evaluations),
        evaluation_representation_counts=sum_counts(value['representation_counts'] for value in evaluations),
        action_probes=len(probes),probe_repeated_initial_random_draws=sum(value['repeated_initial_random_draws'] for value in probes),
        probe_cpu_seconds=sum(value['cpu_seconds'] for value in probes),
        probe_planning_counts=sum_counts(value['chosen']['counts'] for value in probes),
        probe_representation_counts=sum_counts(value['chosen']['representation_counts'] for value in probes),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_evaluation_total_cpu_seconds=worker+compiler+cpu,wall_seconds=wall,
        economic_source_and_target_and_new_cpu_seconds=inherited['economic_source_and_target_cpu_seconds']+worker+compiler+cpu,
        new_compute_closed=True,
        scope='Frozen V314 experiment and its SOURCE charged economically once; no additional fitting. '
            'Reconstruction allocation, sparse reads, native probes, compilation and evaluation are paid in worker/compiler/coordinator CPU. '
            'Mixed tables are shared immutable references, not additional copies or checkpoints. '
            'Prior and new independent audit CPU are separate; historical dynamics CPU remains unknown.')


def run(prior_summary,output):
    cpu,started=process_time(),perf_counter(); output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists(): raise FileExistsError('V315 is already frozen')
    path=Path(prior_summary).resolve(); prior=json.loads(path.read_text())
    audit=json.loads((path.parent/'audit.json').read_text())
    if prior['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V315 requires the completed and independently audited V314 training instances')
    settings=configuration(path); _save(output/'configuration.json',settings)
    (output/'lifecycle_receipts').mkdir(); parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,source,
            [life for life in prior['by_lifecycle'] if life['parent']==source['parent']],output)
            for source in prior['source_provenance']['parents']]):
            row=job.result(); parents.append(row)
            _save(output/f"parent_{row['parent']}_receipt.json",{k:v for k,v in row.items() if k!='lifecycles'})
    parents.sort(key=lambda row:row['parent'])
    lives=sorted((life for row in parents for life in row['lifecycles']),key=lambda row:row['lifecycle'])
    analysis=summarize(lives)
    result=dict(schema='acfqp.component_targets.v315',status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE',settings=settings,
        prior_summary=str(path),source_provenance=prior['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in row.items() if k!='lifecycles'} for row in parents],summary=analysis,
        accounting=build_accounting(prior,lives,parents,process_time()-cpu,perf_counter()-started))
    _save(output/'summary.json',result)
    print(json.dumps(dict(event='component_targets_complete',status=result['status'])),flush=True)
    return result
