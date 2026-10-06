"""Two-phase exact V319 controls and reward-only fixed-root intervention."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .closed_loop_versions_v313 import snapshot_weights, save_version
from .natural_model_revision_v281 import load_leaf
from .native_query_supervision_v319 import fit_supervision
from .native_reward_targets_v321 import acquire_rewards
from .native_split_risk_v301 import evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .query_supervision_run_v319 import _restore_first, _artifact, _compact, _save
from .reward_targets_analysis_v321 import summarize

TASKS = ('A', 'B')
DISTRIBUTIONS = ('FACTUAL_LOCAL', 'QUERY_LOCAL')
ARMS = ('OLD_FACTUAL', 'OLD_QUERY', 'NSTEP_FACTUAL', 'NSTEP_QUERY')
GROUPS, REPLICAS, HORIZON = 16384, 4, 4
PROBABILITIES = {'A': .1, 'B': .5}
DENSE_FIELDS = ('target_reward', 'scores', 'actions', 'new_raw_tiles', 'status',
    'tail_reward', 'bootstrap_afterstates', 'final_boards', 'last_preboards', 'last_afterstates', 'rollout_seeds')


def rollout_seed(life, task, number, group, member):
    return 321500000000+life*10000000+TASKS.index(task)*1000000+number*100000+group*4+member


def evaluation_seed(life, task, episode):
    return 321900000000+life*1000000+TASKS.index(task)*100000+episode


def configuration(source):
    return dict(schema='acfqp.reward_targets_freeze.v321', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/REWARD_TARGETS_V321.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS), arms=list(ARMS),
        distributions=list(DISTRIBUTIONS), rounds=[1,2], groups=GROUPS, replicas=REPLICAS,
        horizon=HORIZON, alpha=.0025, true_probabilities=PROBABILITIES,
        teacher='ACTUAL_IMMUTABLE_V317_FIRST_LOCAL_V0', planning_belief='ACTUAL_IMMUTABLE_V319_FIRST_BANK_BELIEF',
        controls='ALL_SIXTEEN_LIVES_ALL_ROUND_DELTAS_EXACT_V319_BEFORE_ANY_NEW_ACQUISITION',
        reward='SAVED_DIRECT_THEN_FIRST_H2_SCORE_PLUS_FIRST_REWARD_LAST_AFTERSTATE_BEFORE_SPAWN',
        win='UNCHANGED_V319_MEMBER_TARGETS_AND_EXACT_MATCHED_RISK_PARAMETERS',
        bootstrap='PLANNED_NONTERMINAL_TARGET_NOT_TERMINAL_TRUTH_OR_CUTOFF',
        seed_continuation=321500000000, life_stride=10000000, task_stride=1000000,
        round_stride=100000, group_stride=4, expected_rollouts=8388608,
        maximum_new_training_raw_tiles=25165824, evaluation_games_per_cell=32,
        evaluation_arms=['SOURCE','FIRST_LOCAL']+list(ARMS), evaluation_checkpoints=['FINAL'],
        seed_evaluation=321900000000, expected_evaluation_games=6144, max_steps=8192,
        primary='NSTEP_QUERY_minus_OLD_QUERY_FINAL_AB', bootstrap_draws=20000, bootstrap_seed=32100001,
        stop_rule='CONTROL_MISMATCH_NO_ACQUISITION_ANY_NATURAL_EVALUATION_CUTOFF_GLOBAL_HOLD',
        cost_scope='NEW_TARGETS_PHYSICAL_ONCE_CHARGED_TO_NSTEP_NOT_MATCHED_RAW_BUDGET_WITH_OLD')


def _read_groups(receipt):
    cpu, wall = process_time(), perf_counter(); path = Path(receipt['file'])
    names = ('roots','targetreward','targetwin','selected_action','targetkind','spawn_cells','spawn_ranks')
    with np.load(path, allow_pickle=False) as saved:
        if json.loads(str(saved['metadata_json'])) != receipt['metadata']:
            raise ValueError('V321 retained V319 group metadata differs')
        data = {k:np.ascontiguousarray(saved[k]) for k in names}
    if data['roots'].shape != (GROUPS,16) or data['targetreward'].shape != (GROUPS,REPLICAS):
        raise ValueError('V321 uses every original root group and member')
    return data, dict(file=str(path),source_file_bytes=path.stat().st_size,
        array_bytes=sum(v.nbytes for v in data.values()),new_raw_tiles=0,
        cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-wall)


def _match_versions(actual, expected, *, risk_only=False):
    cpu, wall = process_time(), perf_counter()
    names = ('terminal_indices','terminal_values') if risk_only else (
        'reward_indices','reward_values','terminal_indices','terminal_values')
    count = 0
    with np.load(actual['file'],allow_pickle=False) as left, np.load(expected['file'],allow_pickle=False) as right:
        for key in names:
            if not np.array_equal(left[key],right[key]):
                raise ValueError('V321 reward intervention changed WIN parameters' if risk_only else
                    'V321 old-label control cannot exactly reproduce V319; no acquisition authorized')
            count += left[key].size
    if actual['updates'] != expected['updates']:
        raise ValueError('V321 matched versions have different update counts')
    return dict(exact=True,file=expected['file'],arrays_compared=len(names),array_values_compared=count,
        cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-wall)


def _fit(leaf, roots, rewards, wins, source, life, context, arm, number, previous, directory, runtime):
    before = leaf.updates; snapshot = snapshot_weights(leaf)
    leaf.reward_weights.flags.writeable = leaf.risk_weights.flags.writeable = True
    fit = fit_supervision(leaf,roots,rewards,wins,runtime,alpha=.0025); leaf.freeze()
    if arm.startswith('NSTEP'):
        fit['sampling_unit'] = 'ROOTGROUP_MEAN_OF_FROZEN_FIRST_NSTEP_REWARD_AND_OLD_WIN_REPLICAS'
    if leaf.updates-before != GROUPS:
        raise ValueError('V321 must apply exactly one original grouped update per root')
    version = save_version(leaf,source,life,context,arm,number,directory/f'{arm}_v{number}.npz',
        base=previous,previous=snapshot)
    return dict(fit=fit,head_version=version,updates_before=before,updates_after=leaf.updates)


def _control_life(template, source, old, runtime, out):
    life = old['lifecycle']; rounds = {'1':{},'2':{}}; initial = {}; setups = {}
    for task in TASKS:
        inherited = old['initial'][task]; version = inherited['head_version']
        first, setup = _restore_first(template,version,runtime)
        initial[task] = dict(head_version=version,planning_belief=inherited['planning_belief'],context_id=inherited['context_id'])
        setups[task] = {'FIRST_LOCAL':setup}; heads = {}; versions = {}
        for distribution in DISTRIBUTIONS:
            arm = 'OLD_'+distribution.split('_')[0]
            heads[arm], setups[task][arm] = _new_head(template,'LOCAL_RISK',runtime,first)
            heads[arm].freeze(); versions[arm] = version
        directory = out/'models'/f'life_{life}'/f"bank_{inherited['context_id']}"
        for number in (1,2):
            stage = dict(teacher_version=version,teacher_unchanged=True,groups=GROUPS,replicas=REPLICAS,
                arms={},control_source_reads={})
            for distribution in DISTRIBUTIONS:
                arm = 'OLD_'+distribution.split('_')[0]; previous = old['rounds'][str(number)][task]['arms'][distribution]
                data, read = _read_groups(previous['supervision']['group_artifact'])
                item = _fit(heads[arm],data['roots'],data['targetreward'],data['targetwin'],source,life,
                    inherited['context_id'],arm,number,versions[arm],directory,runtime)
                item['control_match'] = _match_versions(item['head_version'],previous['head_version'])
                versions[arm] = item['head_version']; stage['arms'][arm] = item
                stage['control_source_reads'][distribution] = read
            rounds[str(number)][task] = stage
        del heads, first
    row = dict(lifecycle=life,parent=source['parent'],initial=initial,rounds=rounds,control_head_setups=setups)
    _save(out/'control_receipts'/f'life_{life}.json',row)
    print(json.dumps(dict(event='reward_control_life_exact',lifecycle=life)),flush=True)
    return row


def _apply_delta(leaf, version):
    cpu, wall = process_time(), perf_counter()
    leaf.reward_weights.flags.writeable = leaf.risk_weights.flags.writeable = True
    with np.load(version['file'],allow_pickle=False) as saved:
        leaf.reward_weights.reshape(-1)[saved['reward_indices']] = saved['reward_values']
        leaf.risk_weights.reshape(-1)[saved['terminal_indices']] = saved['terminal_values']
    leaf.updates = version['updates']; leaf.freeze()
    return dict(file=version['file'],cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-wall)


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    seeds = [evaluation_seed(life,task,i) for i in range(32)]; before = leaf.updates
    p = belief['estimated_p_four']
    result = (engine.evaluate_games(leaf,p,PROBABILITIES[task],seeds,depth=2,max_steps=8192) if version is None else
        evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=8192))
    if leaf.updates != before: raise ValueError('V321 natural evaluation changed a frozen head')
    return dict(result,estimated_p_four=p,head_version=deepcopy(version),planner='H2',static_evaluation_valid=True)


def _intervene_life(template, source, old, row, runtime, out, engine):
    row = deepcopy(row); life = row['lifecycle']; row['intervention_head_setups'] = {}; row['final_evaluations'] = {}
    for task in TASKS:
        initial = row['initial'][task]; first, setup = _restore_first(template,initial['head_version'],runtime)
        heads, versions = {}, {}; setups = {'FIRST_LOCAL':setup,'old_delta_restores':[]}
        for arm in ARMS:
            heads[arm], setups[arm] = _new_head(template,'LOCAL_RISK',runtime,first)
            heads[arm].freeze(); versions[arm] = initial['head_version']
        directory = out/'models'/f'life_{life}'/f"bank_{initial['context_id']}"
        for number in (1,2):
            stage = row['rounds'][str(number)][task]; stage['distributions'] = {}
            p = initial['planning_belief']['estimated_p_four']
            seeds = np.asarray([[rollout_seed(life,task,number,g,m) for m in range(REPLICAS)]
                for g in range(GROUPS)],dtype=np.uint64)
            for distribution in DISTRIBUTIONS:
                suffix = distribution.split('_')[0]; old_arm, arm = 'OLD_'+suffix, 'NSTEP_'+suffix
                receipt = old['rounds'][str(number)][task]['arms'][distribution]['supervision']['group_artifact']
                data, read = _read_groups(receipt)
                result = acquire_rewards(first,data['roots'],data['spawn_cells'],data['spawn_ranks'],
                    data['selected_action'],data['targetkind'],seeds,runtime,
                    directory/f'{distribution}_R{number}_trace.npz',p_model=p,p_true=PROBABILITIES[task],horizon=HORIZON)
                metadata = dict(schema='acfqp.reward_targets_outcome.v321',lifecycle=life,parent=source['parent'],
                    task=task,round=number,distribution=distribution,groups=GROUPS,replicas=REPLICAS,horizon=HORIZON,
                    teacher_version=initial['head_version'],p_model=p,p_true=PROBABILITIES[task],source_group_file=receipt['file'])
                artifact = _artifact(directory/f'{distribution}_R{number}_outcome.npz',metadata,
                    **{k:result[k] for k in DENSE_FIELDS})
                difference = result['target_reward']-data['targetreward']
                shift = dict(mean_old_reward=float(np.mean(data['targetreward'])),mean_new_reward=float(np.mean(result['target_reward'])),
                    mean_delta=float(np.mean(difference)),replica_delta_rms=float(np.sqrt(np.mean(difference**2))),win_targets_changed=0)
                stage['distributions'][distribution] = dict(source_group_artifact=receipt,source_read=read,
                    acquisition=_compact(result),outcome_artifact=artifact,label_shift=shift)
                item = _fit(heads[arm],data['roots'],result['target_reward'],data['targetwin'],source,life,
                    initial['context_id'],arm,number,versions[arm],directory,runtime)
                item['risk_match'] = _match_versions(item['head_version'],stage['arms'][old_arm]['head_version'],risk_only=True)
                versions[arm] = item['head_version']; stage['arms'][arm] = item
                old_version = stage['arms'][old_arm]['head_version']
                setups['old_delta_restores'].append(_apply_delta(heads[old_arm],old_version)); versions[old_arm] = old_version
            stage['teacher_unchanged'] = (first.updates==initial['head_version']['updates'] and
                not first.reward_weights.flags.writeable and not first.risk_weights.flags.writeable)
            print(json.dumps(dict(event='reward_intervention_round_complete',lifecycle=life,task=task,round=number)),flush=True)
        evaluations = {'SOURCE':_evaluate(template,life,task,initial['planning_belief'],runtime,engine),
            'FIRST_LOCAL':_evaluate(first,life,task,initial['planning_belief'],runtime,engine,initial['head_version'])}
        for arm in ARMS:
            evaluations[arm] = _evaluate(heads[arm],life,task,initial['planning_belief'],runtime,engine,versions[arm])
        row['final_evaluations'][task] = evaluations; row['intervention_head_setups'][task] = setups
        del heads, first
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    print(json.dumps(dict(event='reward_intervention_life_complete',lifecycle=life)),flush=True)
    return row


def _parent(source, document, out, phase, controls=None):
    cpu, wall, compiler = process_time(),perf_counter(),_child_cpu()
    runtime = out/'runtime'/phase/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    engine = NativeValueStream(template,321800000000+source['parent'],runtime) if phase=='intervention' else None
    rows = []
    for old in document['by_lifecycle']:
        if old['parent'] != source['parent']: continue
        rows.append(_control_life(template,source,old,runtime,out) if phase=='control' else
            _intervene_life(template,source,old,controls[old['lifecycle']],runtime,out,engine))
    return dict(parent=source['parent'],phase=phase,lifecycles=rows,source_setup=setup,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-wall)


def accounting(lives, parents, cpu, wall, inherited, diagnostic):
    stages = [s for row in lives for tasks in row['rounds'].values() for s in tasks.values()]
    distributions = [s['distributions'][d] for s in stages for d in DISTRIBUTIONS]
    evaluations = [e for row in lives for tasks in row['final_evaluations'].values() for e in tasks.values()]
    fit_items = [s['arms'][a] for s in stages for a in ARMS]
    reads = [r for s in stages for r in s['control_source_reads'].values()]+[d['source_read'] for d in distributions]
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    component = worker+compiler+cpu
    per_arm = {}
    for arm in ARMS:
        cells = [s['arms'][arm] for s in stages]; suffix = arm.split('_')[1]+'_LOCAL'
        acquisitions = [s['distributions'][suffix]['acquisition'] for s in stages] if arm.startswith('NSTEP') else []
        per_arm[arm] = dict(rootgroups=sum(i['fit']['fitted_rootgroups'] for i in cells),
            fit_counts=sum_counts(i['fit']['learning_counts'] for i in cells),fit_cpu_seconds=sum(i['fit']['cpu_seconds'] for i in cells),
            economic_new_training_raw_tiles=sum(int(v['environment_counts'].get('raw_tile_productions',0)) for v in acquisitions),
            economic_acquisition_cpu_seconds=sum(v['cpu_seconds'] for v in acquisitions))
    return dict(source_training_repeated=False,first_adaptation_repeated=False,prior_full_audit_repeated=False,
        control_matched_versions=len(stages)*2,per_arm=per_arm,
        new_training_raw_tiles=sum(int(d['acquisition']['environment_counts'].get('raw_tile_productions',0)) for d in distributions),
        training_environment_counts=sum_counts(d['acquisition']['environment_counts'] for d in distributions),
        acquisition_counts=sum_counts(d['acquisition']['counts'] for d in distributions),
        training_planning_counts=sum_counts(d['acquisition']['planning_counts'] for d in distributions),
        training_representation_counts=sum_counts(d['acquisition']['representation_counts'] for d in distributions),
        source_group_reads=len(reads),source_file_bytes_referenced=sum(r['source_file_bytes'] for r in reads),
        source_array_bytes_read=sum(r['array_bytes'] for r in reads),source_read_cpu_seconds=sum(r['cpu_seconds'] for r in reads),
        trace_files=len(distributions),trace_saved_bytes=sum(d['acquisition']['trace_artifact']['compressed_bytes'] for d in distributions),
        outcome_files=len(distributions),outcome_saved_bytes=sum(d['outcome_artifact']['saved_bytes'] for d in distributions),
        new_head_files=len(fit_items),new_head_saved_bytes=sum(i['head_version']['saved_bytes'] for i in fit_items),
        new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),
        new_evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),
        new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_experiment_component_cpu_seconds=component,wall_seconds=wall,
        inherited_successful_source_v317_v319_full_cpu_seconds=inherited,
        economic_source_v317_v319_and_experiment_component_cpu_seconds=inherited+component,
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        cost_scope='Physical generation once; NSTEP arms pay their distribution acquisition in full. OLD arms have no new target raw. '
            'All control/restore/read/fit/evaluation/IO/compiler/coordinator work included once; full execution adds final serialization/shutdown. '
            'Audit and preceding V320 diagnostic separate; historical dynamics/failed-attempt CPU unknown.')


def run(source_summary, output):
    cpu, wall = process_time(),perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V321 is already frozen')
    source_path = Path(source_summary).resolve(); document = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    if document['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V321 requires the audited complete V319 cohort')
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []; controls = {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_parent,s,document,out,'control') for s in document['source_provenance']['parents']]
        for job in as_completed(jobs):
            parent = job.result(); parents.append(parent)
            controls.update({r['lifecycle']:r for r in parent['lifecycles']})
            _save(out/f"control_parent_{parent['parent']}_receipt.json",{k:v for k,v in parent.items() if k!='lifecycles'})
    _save(out/'control_phase.json',dict(status='ALL_CONTROLS_EXACT',matched_versions=128,
        new_raw_tiles=0,lifecycles=sorted(controls),control_receipts=[str(out/'control_receipts'/f'life_{i}.json') for i in sorted(controls)]))
    print(json.dumps(dict(event='reward_all_controls_exact_before_acquisition',matched_versions=128)),flush=True)
    lives = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_parent,s,document,out,'intervention',controls) for s in document['source_provenance']['parents']]
        for job in as_completed(jobs):
            parent = job.result(); parents.append(parent); lives.extend(parent['lifecycles'])
            _save(out/f"intervention_parent_{parent['parent']}_receipt.json",{k:v for k,v in parent.items() if k!='lifecycles'})
    lives.sort(key=lambda r:r['lifecycle']); parents.sort(key=lambda p:(p['phase'],p['parent']))
    analysis = summarize(lives)
    inherited = json.loads((source_path.parent/'audit_costs.json').read_text())['full_economic_source_v317_and_experiment_cpu_seconds']
    diagnostic = json.loads((source_path.parent.parent/'teacher_calibration_v320/execution.json').read_text())['process_tree_cpu_seconds']
    result = dict(schema='acfqp.reward_targets.v321',status='EXPERIMENT_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='EXPLORATORY_REWARD_TARGET_INTERVENTION_NO_U006_AUTHORIZATION',settings=settings,source_summary=str(source_path),
        source_provenance=document['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(lives,parents,process_time()-cpu,perf_counter()-wall,inherited,diagnostic))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='reward_targets_complete',status=result['status'],primary=analysis['primary_status'],
        repaired=analysis['repaired_query_supported'])),flush=True)
    return result
