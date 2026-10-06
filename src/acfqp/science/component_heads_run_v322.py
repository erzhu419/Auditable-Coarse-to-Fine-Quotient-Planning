"""Saved reward/WIN parameter crossover with two new natural-game cells."""
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
from .native_split_risk_v301 import evaluate_split
from .query_supervision_run_v319 import _restore_first, _save
from .reward_targets_run_v321 import _apply_delta, evaluation_seed
from .component_heads_analysis_v322 import summarize

TASKS = ('A','B')
NEW_ARMS = ('REWARD_ONLY','WIN_ONLY')
REUSED_ARMS = ('FIRST_LOCAL','NSTEP_QUERY')
PROBABILITIES = {'A':.1,'B':.5}


def configuration(source):
    return dict(schema='acfqp.component_heads_freeze.v322',source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/COMPONENT_HEADS_V322.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),
        new_arms=list(NEW_ARMS),reused_arms=list(REUSED_ARMS),
        components={'FIRST_LOCAL':['FIRST_LOCAL','FIRST_LOCAL'],'NSTEP_QUERY':['NSTEP_QUERY','NSTEP_QUERY'],
            'REWARD_ONLY':['NSTEP_QUERY','FIRST_LOCAL'],'WIN_ONLY':['FIRST_LOCAL','NSTEP_QUERY']},
        restore='ACTUAL_FIRST_V0_THEN_NSTEP_QUERY_V1_THEN_V2_ABSOLUTE_SPARSE_WRITES',
        assembly='FULL_SELECTED_COMPONENT_COPY_OTHER_COMPONENT_EXACT_FIRST_NO_FIT',
        updates_counter='INHERITED_FIRST_ONLY_HYBRID_VERSION_IS_ASSEMBLY_NOT_TRAINING',
        planning_belief='ACTUAL_IMMUTABLE_V321_FIRST_BANK_BELIEF',true_probabilities=PROBABILITIES,
        evaluation_games_per_cell=32,max_steps=8192,seed_evaluation=321900000000,
        paired_stream_reuse=True,expected_new_evaluation_games=2048,expected_reused_evaluation_games=2048,
        maximum_new_evaluation_raw_tiles=16781312,new_training_raw_tiles=0,new_fit_updates=0,
        primary='REWARD_ONLY_minus_NSTEP_QUERY_FINAL_AB',bootstrap_draws=20000,bootstrap_seed=32200001,
        stop_rule='ANY_NEW_OR_REUSED_NATURAL_GAME_CUTOFF_GLOBAL_HOLD_NO_REPLACEMENTS',
        evidence_scope='SAVED_COMPONENT_POLICY_MECHANISM_FIXED_V321_STREAMS_NOT_INDEPENDENT_CONFIRMATION')


def _restore_final(template, first, chain, runtime):
    final, setup = _new_head(template,'LOCAL_RISK',runtime,first)
    setup['delta_restores'] = [_apply_delta(final,version) for version in chain[1:]]
    setup['source_versions'] = chain
    return final, setup


def _assemble(template, first, final, chain, source, life, context, arm, runtime, directory):
    cpu, wall = process_time(),perf_counter()
    leaf, setup = _new_head(template,'LOCAL_RISK',runtime,first)
    previous = snapshot_weights(first)
    reward_source, win_source = ('NSTEP_QUERY','FIRST_LOCAL') if arm=='REWARD_ONLY' else ('FIRST_LOCAL','NSTEP_QUERY')
    if arm=='REWARD_ONLY': np.copyto(leaf.reward_weights,final.reward_weights)
    else: np.copyto(leaf.risk_weights,final.risk_weights)
    if not np.array_equal(leaf.reward_weights,final.reward_weights if reward_source=='NSTEP_QUERY' else first.reward_weights) or not np.array_equal(
            leaf.risk_weights,final.risk_weights if win_source=='NSTEP_QUERY' else first.risk_weights):
        raise ValueError('V322 mixed head differs from its selected complete saved components')
    leaf.freeze()
    version = save_version(leaf,source,life,context,arm,1,directory/f'{arm}_v1.npz',base=chain[0],previous=previous)
    receipt = dict(method='SAVED_COMPONENT_CROSSOVER_NO_FIT',reward_source=reward_source,win_source=win_source,
        reward_source_versions=chain if reward_source=='NSTEP_QUERY' else chain[:1],
        win_source_versions=chain if win_source=='NSTEP_QUERY' else chain[:1],
        new_fit_updates=0,weights_frozen=True,parameter_updates_counter=first.updates,
        component_copy_parameters=int(first.reward_weights.size),component_copy_bytes=int(first.reward_weights.nbytes),
        complete_component_equality=True,cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-wall)
    return leaf, setup, version, receipt


def _evaluate(leaf, life, task, belief, version, runtime):
    before = leaf.updates; seeds = [evaluation_seed(life,task,i) for i in range(32)]
    value = evaluate_split(leaf,belief['estimated_p_four'],PROBABILITIES[task],seeds,runtime,max_steps=8192)
    if leaf.updates != before or leaf.reward_weights.flags.writeable or leaf.risk_weights.flags.writeable:
        raise ValueError('V322 diagnostic natural evaluation changed its frozen component head')
    return dict(value,estimated_p_four=belief['estimated_p_four'],head_version=deepcopy(version),
        planner='H2',static_evaluation_valid=True)


def _run_life(template, source, old, runtime, out):
    life = old['lifecycle']; cells, setups = {}, {}
    for task in TASKS:
        initial = old['initial'][task]
        chain = [initial['head_version']]+[old['rounds'][str(n)][task]['arms']['NSTEP_QUERY']['head_version'] for n in (1,2)]
        first, setup = _restore_first(template,chain[0],runtime)
        final, final_setup = _restore_final(template,first,chain,runtime)
        setups[task] = {'FIRST_LOCAL':setup,'NSTEP_QUERY':final_setup}; cells[task] = {}
        for arm in REUSED_ARMS:
            cells[task][arm] = dict(reused=True,evaluation=deepcopy(old['final_evaluations'][task][arm]))
        directory = out/'models'/f'life_{life}'/f"bank_{initial['context_id']}"
        for arm in NEW_ARMS:
            leaf, setup, version, assembly = _assemble(template,first,final,chain,source,life,
                initial['context_id'],arm,runtime,directory)
            setups[task][arm] = setup
            cells[task][arm] = dict(reused=False,head_version=version,assembly=assembly,
                evaluation=_evaluate(leaf,life,task,initial['planning_belief'],version,runtime))
            del leaf
        del first, final
    row = dict(lifecycle=life,parent=source['parent'],initial=deepcopy(old['initial']),cells=cells,head_setups=setups)
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    print(json.dumps(dict(event='component_heads_life_complete',lifecycle=life,new_games=128)),flush=True)
    return row


def _run_parent(source, document, out):
    cpu, wall, compiler = process_time(),perf_counter(),_child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    rows = [_run_life(template,source,row,runtime,out) for row in document['by_lifecycle'] if row['parent']==source['parent']]
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-wall)


def accounting(lives, parents, cpu, wall, inherited, diagnostic):
    new = [row['cells'][t][a] for row in lives for t in TASKS for a in NEW_ARMS]
    reused = [row['cells'][t][a]['evaluation'] for row in lives for t in TASKS for a in REUSED_ARMS]
    evaluations = [c['evaluation'] for c in new]
    per_arm = {arm:dict(new_evaluation_games=sum(len(row['cells'][t][arm]['evaluation']['game_summaries']) for row in lives for t in TASKS),
        environment_counts=sum_counts(row['cells'][t][arm]['evaluation']['counts']['environment'] for row in lives for t in TASKS),
        evaluation_cpu_seconds=sum(row['cells'][t][arm]['evaluation']['cpu_seconds'] for row in lives for t in TASKS)) for arm in NEW_ARMS}
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    component = worker+compiler+cpu
    return dict(new_training_raw_tiles=0,new_fit_updates=0,source_training_repeated=False,first_adaptation_repeated=False,
        prior_full_audit_repeated=False,per_arm=per_arm,
        new_evaluation_games=sum(len(v['game_summaries']) for v in evaluations),reused_evaluation_games=sum(len(v['game_summaries']) for v in reused),
        new_evaluation_environment_counts=sum_counts(v['counts']['environment'] for v in evaluations),
        new_evaluation_planning_counts=sum_counts(v['counts']['planning'] for v in evaluations),
        new_evaluation_representation_counts=sum_counts(v['representation_counts'] for v in evaluations),
        new_evaluation_cpu_seconds=sum(v['cpu_seconds'] for v in evaluations),
        new_head_files=len(new),new_head_saved_bytes=sum(c['head_version']['saved_bytes'] for c in new),
        assembly_component_copy_parameters=sum(c['assembly']['component_copy_parameters'] for c in new),
        assembly_component_copy_bytes=sum(c['assembly']['component_copy_bytes'] for c in new),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_experiment_component_cpu_seconds=component,wall_seconds=wall,
        inherited_successful_source_v317_v319_v321_full_cpu_seconds=inherited,
        economic_source_v317_v319_v321_and_experiment_component_cpu_seconds=inherited+component,
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        cost_scope='All restore/assembly/version IO/new evaluation/compiler/coordinator work once. '
            'Reused game receipts are not new physical games or new raw. Full execution adds final serialization/shutdown. '
            'V320 diagnosis and all independent audits separate; historical dynamics and failed-attempt CPU unknown.')


def run(source_summary, output):
    cpu, wall = process_time(),perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V322 is already frozen')
    source_path = Path(source_summary).resolve(); document = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    if document['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V322 requires audited complete V321 saved heads and paired natural evaluations')
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,document,out) for s in document['source_provenance']['parents']]):
            parent = job.result(); parents.append(parent)
            _save(out/f"parent_{parent['parent']}_receipt.json",{k:v for k,v in parent.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent']); lives = sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis = summarize(lives)
    cost = json.loads((source_path.parent/'audit_costs.json').read_text())
    result = dict(schema='acfqp.component_heads.v322',status='DIAGNOSTIC_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='SAVED_COMPONENT_MECHANISM_NOT_INDEPENDENT_CONFIRMATION_NO_U006',settings=settings,source_summary=str(source_path),
        source_provenance=document['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(lives,parents,process_time()-cpu,perf_counter()-wall,
            cost['full_economic_source_v317_v319_and_experiment_cpu_seconds'],cost['preceding_v320_diagnostic_full_cpu_seconds']))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='component_heads_complete',status=result['status'],primary=analysis['primary_status'],
        restored_growth=analysis['restored_growth_supported'])),flush=True)
    return result
