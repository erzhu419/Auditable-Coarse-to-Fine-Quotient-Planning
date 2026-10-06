"""Fresh execution streams for one frozen, development-selected WIN-only head."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .natural_model_revision_v281 import load_leaf
from .native_split_risk_v301 import evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .query_supervision_run_v319 import _restore_first, _save
from .reward_targets_run_v321 import _apply_delta
from .win_confirmation_analysis_v323 import summarize

TASKS = ('A','B')
ARMS = ('SOURCE','FIRST_LOCAL','WIN_ONLY')
PROBABILITIES = {'A':.1,'B':.5}
EPISODES = 64


def evaluation_seed(life, task, episode):
    return 323900000000+life*1000000+TASKS.index(task)*100000+episode


def configuration(source):
    return dict(schema='acfqp.win_confirmation_freeze.v323',source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/WIN_CONFIRMATION_V323.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),arms=list(ARMS),
        candidate='ACTUAL_V322_WIN_ONLY_V1_FIRST_REWARD_PLUS_SAVED_QUERY_WIN',
        candidate_selection='V322_NOMINAL_SECONDARY_DEVELOPMENT_SIGNAL_BEFORE_NEW_STREAMS',
        restore='ACTUAL_FIRST_V0_THEN_WIN_ONLY_V1_ABSOLUTE_SPARSE_WRITES_NO_NEW_VERSIONS',
        planning_belief='ACTUAL_IMMUTABLE_V322_FIRST_BANK_BELIEF',true_probabilities=PROBABILITIES,
        evaluation_games_per_cell=EPISODES,max_steps=8192,seed_evaluation=323900000000,
        fresh_evaluation_streams=True,paired_stream_reuse=False,expected_new_evaluation_games=6144,
        maximum_new_evaluation_raw_tiles=50343936,new_training_raw_tiles=0,new_fit_updates=0,new_head_files=0,
        primary='WIN_ONLY_minus_FIRST_LOCAL_FINAL_AB',bootstrap_draws=20000,bootstrap_seed=32300001,
        retention='BOTH_TASK_WIN_ONLY_MINUS_FIRST_CI_LOWER_NONNEGATIVE',
        stop_rule='ANY_NATURAL_GAME_CUTOFF_GLOBAL_HOLD_NO_REPLACEMENTS_QUOTA_EXTENSION_OR_CANDIDATE_CHANGE',
        independent_learning_histories=False,evidence_scope='FRESH_EXECUTION_VALIDATION_CONDITIONAL_ON_EXISTING_LEARNT_COHORT')


def _restore_candidate(template, first, version, runtime):
    leaf, setup = _new_head(template,'LOCAL_RISK',runtime,first)
    setup['delta_restore'] = _apply_delta(leaf,version)
    setup['restored_version'] = version
    return leaf, setup


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    seeds = [evaluation_seed(life,task,i) for i in range(EPISODES)]; before = leaf.updates
    p = belief['estimated_p_four']
    result = (engine.evaluate_games(leaf,p,PROBABILITIES[task],seeds,depth=2,max_steps=8192) if version is None else
        evaluate_split(leaf,p,PROBABILITIES[task],seeds,runtime,max_steps=8192))
    if leaf.updates != before:
        raise ValueError('V323 fresh natural evaluation changed its frozen head')
    return dict(result,estimated_p_four=p,head_version=deepcopy(version),planner='H2',static_evaluation_valid=True)


def _run_life(template, source, old, runtime, out, engine):
    life = old['lifecycle']; candidates, evaluations, setups = {}, {}, {}
    for task in TASKS:
        initial = old['initial'][task]; saved = old['cells'][task]['WIN_ONLY']
        version = saved['head_version']
        first, first_setup = _restore_first(template,initial['head_version'],runtime)
        candidate, candidate_setup = _restore_candidate(template,first,version,runtime)
        candidates[task] = dict(head_version=version,assembly=deepcopy(saved['assembly']))
        setups[task] = {'FIRST_LOCAL':first_setup,'CANDIDATE':candidate_setup}
        belief = initial['planning_belief']
        evaluations[task] = {
            'SOURCE':_evaluate(template,life,task,belief,runtime,engine),
            'FIRST_LOCAL':_evaluate(first,life,task,belief,runtime,engine,initial['head_version']),
            'WIN_ONLY':_evaluate(candidate,life,task,belief,runtime,engine,version)}
        if first.reward_weights.flags.writeable or first.risk_weights.flags.writeable or candidate.reward_weights.flags.writeable or candidate.risk_weights.flags.writeable:
            raise ValueError('V323 evaluated heads must retain immutable parameters')
        del first, candidate
    row = dict(lifecycle=life,parent=source['parent'],initial=deepcopy(old['initial']),frozen_candidate=candidates,
        evaluations=evaluations,head_setups=setups)
    _save(out/'lifecycle_receipts'/f'life_{life}.json',row)
    print(json.dumps(dict(event='win_confirmation_life_complete',lifecycle=life,new_games=384)),flush=True)
    return row


def _run_parent(source, document, out):
    cpu, wall, compiler = process_time(),perf_counter(),_child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source,runtime)
    engine = NativeValueStream(template,323800000000+source['parent'],runtime)
    rows = [_run_life(template,source,row,runtime,out,engine) for row in document['by_lifecycle'] if row['parent']==source['parent']]
    return dict(parent=source['parent'],lifecycles=rows,source_setup=setup,
        cpu_seconds=process_time()-cpu,compiler_cpu_seconds=_child_cpu()-compiler,wall_seconds=perf_counter()-wall)


def accounting(lives, parents, cpu, wall, inherited, diagnostic):
    evaluations = [row['evaluations'][t][a] for row in lives for t in TASKS for a in ARMS]
    per_arm = {arm:dict(new_evaluation_games=sum(len(row['evaluations'][t][arm]['game_summaries']) for row in lives for t in TASKS),
        environment_counts=sum_counts(row['evaluations'][t][arm]['counts']['environment'] for row in lives for t in TASKS),
        evaluation_cpu_seconds=sum(row['evaluations'][t][arm]['cpu_seconds'] for row in lives for t in TASKS)) for arm in ARMS}
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    component = worker+compiler+cpu
    return dict(new_training_raw_tiles=0,new_fit_updates=0,new_head_files=0,source_training_repeated=False,
        first_adaptation_repeated=False,prior_full_audit_repeated=False,per_arm=per_arm,
        new_evaluation_games=sum(len(v['game_summaries']) for v in evaluations),reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(v['counts']['environment'] for v in evaluations),
        new_evaluation_planning_counts=sum_counts(v['counts']['planning'] for v in evaluations),
        split_evaluation_representation_counts=sum_counts(v['representation_counts'] for v in evaluations if 'representation_counts' in v),
        representation_scope='FIRST_AND_WIN_ONLY_SPLIT_HEADS_SOURCE_ONLY_HAS_PLANNING_COUNTS',
        new_evaluation_cpu_seconds=sum(v['cpu_seconds'] for v in evaluations),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,coordinator_cpu_seconds=cpu,
        new_experiment_component_cpu_seconds=component,wall_seconds=wall,
        inherited_successful_source_v317_v319_v321_v322_full_cpu_seconds=inherited,
        economic_source_v317_v319_v321_v322_and_experiment_component_cpu_seconds=inherited+component,
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        cost_scope='All restore/reads/new evaluation/compiler/coordinator work once; no new head files or training. '
            'All evaluation games and raw tiles are new. Full execution adds final serialization/shutdown. '
            'Successful retained lineage inherited once; V320 diagnosis and audits separate. Historical dynamics/failed-attempt CPU unknown.')


def run(source_summary, output):
    cpu, wall = process_time(),perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V323 is already frozen')
    source_path = Path(source_summary).resolve(); document = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    if document['status']!='DIAGNOSTIC_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V323 requires audited complete V322 frozen candidate and FIRST heads')
    settings = configuration(source_path); _save(out/'configuration.json',settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,document,out) for s in document['source_provenance']['parents']]):
            parent = job.result(); parents.append(parent)
            _save(out/f"parent_{parent['parent']}_receipt.json",{k:v for k,v in parent.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent']); lives = sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    analysis = summarize(lives); costs = json.loads((source_path.parent/'audit_costs.json').read_text())
    result = dict(schema='acfqp.win_confirmation.v323',status='EVALUATION_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF',
        scientific_gate='FRESH_EXECUTION_VALIDATION_NOT_INDEPENDENT_LEARNING_OR_U006',settings=settings,source_summary=str(source_path),
        source_provenance=document['source_provenance'],by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=analysis,
        accounting=accounting(lives,parents,process_time()-cpu,perf_counter()-wall,
            costs['full_economic_source_v317_v319_v321_and_experiment_cpu_seconds'],costs['preceding_v320_diagnostic_full_cpu_seconds']))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='win_confirmation_complete',status=result['status'],primary=analysis['primary_status'],
        retained_execution_gain=analysis['retained_execution_gain_supported'])),flush=True)
    return result
