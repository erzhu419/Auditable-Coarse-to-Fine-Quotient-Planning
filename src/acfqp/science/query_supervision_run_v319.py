"""Matched fresh supervision at factual vs actual frozen FIRST H2-query roots."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .b_mechanism_v299 import sum_counts
from .closed_loop_run_v313 import _child_cpu, _new_head
from .closed_loop_versions_v313 import snapshot_weights, save_version
from .native_query_supervision_v319 import query_roots, supervise, fit_supervision
from .native_split_risk_v301 import evaluate_split
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf
from .query_facts_v319 import iter_query_lifecycles, prepare_anchors
from .query_supervision_analysis_v319 import summarize, TASKS, UPDATING_ARMS

PROBABILITIES = {'A': .1, 'B': .5}
GROUPS, REPLICAS = 16384, 4


class CensusUnavailable(Exception):
    """The frozen cohort cannot supply its declared paired anchor quota."""
    def __init__(self, partial):
        self.partial = partial
        super().__init__(partial['census_failure']['reason'])


def _save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def selection_seed(life, task, number):
    return 319100000000+life*10000000+TASKS.index(task)*1000000+number*100000


def draw_seed(life, task, number):
    return 319500000000+life*10000000+TASKS.index(task)*1000000+number*100000


def evaluation_seed(life, task, episode):
    return 319900000000+life*1000000+TASKS.index(task)*100000+episode


def configuration(source):
    return dict(schema='acfqp.query_supervision_freeze.v319', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/QUERY_SUPERVISION_V319.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=TASKS, arms=UPDATING_ARMS,
        rounds=[1, 2], alpha=.0025, groups_per_arm_task_round=GROUPS, replicas_per_group=REPLICAS,
        census_anchors_per_task_round=2*GROUPS, true_probabilities=PROBABILITIES,
        teacher='IMMUTABLE_ACTUAL_V317_FIRST_LOCAL_V0_ALL_ROUNDS_AND_BOTH_ARMS',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        anchor='COMPLETE_FIT_NONWIN_CURRENT_AFTERSTATE_WITH_SAME_GAME_PREDECESSOR_POSTSPAWN',
        query_root='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        valid_selection='EQUIDISTANT_VALID_CENSUS_POSITIONS_SHARED_BETWEEN_ARMS',
        reset_access='ARBITRARY_AFTERSTATE_GENERATIVE_ACCESS_FOR_BOTH_ARMS',
        target='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH',
        update='GROUPED_LOCAL_CURRENT_PREDICTION_ONCE_PER_ROOTGROUP_MEAN_REPLICAS',
        max_steps=8192, evaluation_games_per_cell=32, seed_selector=319100000000,
        seed_ground=319500000000, collection_life_stride=10000000, collection_task_stride=1000000,
        collection_round_stride=100000, seed_evaluation=319900000000,
        bootstrap_seed=31900001, bootstrap_draws=20000,
        primary='QUERY_LOCAL_minus_FIRST_LOCAL_FINAL_AB', coverage='QUERY_LOCAL_minus_FACTUAL_LOCAL_FINAL_AB',
        retention='FINAL_QUERY_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_new_training_raw_tiles=2*16*2*2*GROUPS*REPLICAS,
        expected_new_evaluation_games=16*2*32*6,
        evidence_scope='FIXED_EXISTING_FIRST_COHORT_FOUR_FROZEN_PARENTS_GENERATIVE_ONE_STEP_SUPERVISION',
        stop_rule='WHOLE_COHORT_HOLD_IF_INSUFFICIENT_CENSUS_OR_CUTOFF_NO_REPLACEMENTS_OR_TUNING')


def _restore_first(template, version, runtime):
    started = process_time()
    leaf, setup = _new_head(template, 'LOCAL_RISK', runtime)
    with np.load(version['file'], allow_pickle=False) as saved:
        leaf.reward_weights.reshape(-1)[saved['reward_indices']] = saved['reward_values']
        leaf.risk_weights.reshape(-1)[saved['terminal_indices']] = saved['terminal_values']
    leaf.updates = version['updates']; leaf.freeze()
    setup['restore_cpu_seconds'] = process_time()-started
    setup['restored_version'] = version
    return leaf, setup


def _evaluate(leaf, life, task, belief, runtime, engine, version=None):
    seeds = [evaluation_seed(life, task, i) for i in range(32)]
    updates = leaf.updates; p = belief['estimated_p_four']
    result = (engine.evaluate_games(leaf, p, PROBABILITIES[task], seeds, depth=2, max_steps=8192)
        if version is None else evaluate_split(leaf, p, PROBABILITIES[task], seeds, runtime, max_steps=8192))
    if leaf.updates != updates: raise ValueError('V319 evaluation changed its frozen head')
    return dict(result, estimated_p_four=p, head_version=deepcopy(version), planner='H2', static_evaluation_valid=True)


def _artifact(path, metadata, **arrays):
    started, cpu = perf_counter(), process_time()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays, metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False))
    return dict(file=str(path.resolve()), saved_bytes=path.stat().st_size,
        array_bytes=sum(value.nbytes for value in arrays.values()), metadata=metadata,
        save_cpu_seconds=process_time()-cpu, save_wall_seconds=perf_counter()-started)


def _compact(value):
    return {key:item for key,item in value.items() if not isinstance(item, np.ndarray)}


def _run_life(template, source, life, datasets, extraction, runtime, out, engine):
    identity = life['lifecycle']; heads, versions, initial, setups = {}, {}, {}, {}
    for task in TASKS:
        inherited = life['initial'][task]; teacher_version = inherited['head_versions']['FIRST_LOCAL']
        first, setup = _restore_first(template, teacher_version, runtime)
        heads[task] = {'FIRST_LOCAL': first}; versions[task] = {arm:teacher_version for arm in UPDATING_ARMS}
        setups[task] = {'FIRST_LOCAL': setup}
        for arm in UPDATING_ARMS:
            leaf, setup = _new_head(template, 'LOCAL_RISK', runtime, first); leaf.freeze()
            heads[task][arm] = leaf; setups[task][arm] = setup
        belief = deepcopy(inherited['planning_belief'])
        initial[task] = dict(context_id=inherited['context_id'], planning_belief=belief,
            head_version=deepcopy(teacher_version), evaluations={
                'SOURCE':_evaluate(template, identity, task, belief, runtime, engine),
                'FIRST_LOCAL':_evaluate(first, identity, task, belief, runtime, engine, teacher_version)})
    rounds = {}
    for number in (1, 2):
        rounds[str(number)] = {}
        for task in TASKS:
            other = 'B' if task=='A' else 'A'
            inactive_before = deepcopy(versions[other]); first = heads[task]['FIRST_LOCAL']
            before_teacher_updates = first.updates; teacher_version = initial[task]['head_version']
            belief = initial[task]['planning_belief']; p = belief['estimated_p_four']
            dataset = datasets[str(number)][task]
            try:
                anchors = prepare_anchors(dataset, GROUPS)
            except ValueError as error:
                if str(error) != 'V319 insufficient eligible complete FIT anchors for the frozen census': raise
                raise CensusUnavailable(dict(lifecycle=identity,parent=source['parent'],initial=initial,
                    rounds=rounds,extraction=extraction,head_setups=setups,final_head_versions=versions,
                    census_failure=dict(task=task,round=number,reason=str(error),query=None))) from error
            queried = query_roots(first, anchors['preboards'], selection_seed(identity,task,number), runtime, p_model=p)
            if not np.array_equal(queried['chosen_afterstates'], anchors['natural_roots']):
                raise ValueError('V319 H2 teacher must reproduce every retained FIRST natural root at its factual preboard')
            valid = np.flatnonzero(queried['validmask'])
            if len(valid) < GROUPS:
                raise CensusUnavailable(dict(lifecycle=identity,parent=source['parent'],initial=initial,
                    rounds=rounds,extraction=extraction,head_setups=setups,final_head_versions=versions,
                    census_failure=dict(task=task,round=number,
                        reason='V319 insufficient valid actual-query anchors: frozen cohort must HOLD',
                        valid_anchors=int(len(valid)),requested_groups=GROUPS,
                        anchor_counts=anchors['counts'],anchor_cpu_seconds=anchors['cpu_seconds'],query=_compact(queried))))
            positions = valid[np.linspace(0, len(valid)-1, GROUPS, dtype=np.int64)]
            directory = out/'models'/f'life_{identity}'/f"bank_{initial[task]['context_id']}"
            collector = life['rounds'][str(number)][task]['collectors']['FIXED_FIRST']
            metadata = dict(schema='acfqp.query_census.v319', lifecycle=identity, parent=source['parent'],
                task=task, round=number, groups=GROUPS, anchors=2*GROUPS,
                teacher_version=teacher_version, selection_seed=selection_seed(identity,task,number),
                planning_probability=p, selection_rule=queried['selection_rule'],
                source_batch=dict(actor_version=collector['actor_version'], batch_id=f'{task}_R{number}',
                    fit_step_end=dataset['fit_step_end'], fit_game_count=dataset['fit_game_count'],
                    stream_seed=collector['acquisition']['training']['before_stream']['stream_seed']))
            census = _artifact(directory/f'census_R{number}.npz', metadata,
                anchor_indices=anchors['indices'], validmask=queried['validmask'],
                query_ordinals=queried['provenance'][:,4], query_counts=queried['provenance'][:,5],
                selected_positions=positions, selected_provenance=queried['provenance'][positions])
            census.update(anchor_counts=anchors['counts'], anchor_cpu_seconds=anchors['cpu_seconds'],
                query=_compact(queried), selected_groups=GROUPS)
            rootsets = {'FACTUAL_LOCAL':anchors['natural_roots'][positions],
                'QUERY_LOCAL':queried['root_afterstates'][positions]}
            arms = {}
            for arm in UPDATING_ARMS:
                roots = np.ascontiguousarray(rootsets[arm], dtype=np.int32)
                labels = supervise(first, roots, PROBABILITIES[task], draw_seed(identity,task,number), runtime, REPLICAS)
                means_r = np.mean(labels['targetreward'], axis=1); means_w = np.mean(labels['targetwin'], axis=1)
                group_metadata = dict(schema='acfqp.query_supervision_groups.v319', lifecycle=identity,
                    parent=source['parent'], task=task, round=number, arm=arm, groups=GROUPS, replicas=REPLICAS,
                    sampling_unit='ROOTGROUP_FOUR_INDEPENDENT_FRESH_GROUND_SPAWNS',
                    teacher_version=teacher_version, draw_seed=draw_seed(identity,task,number),
                    true_probability=PROBABILITIES[task], census_file=census['file'],
                    target_rule=labels['target_rule'])
                artifact = _artifact(directory/f'{arm}_R{number}_groups.npz', group_metadata, roots=roots,
                    **{k:labels[k] for k in ('targetreward','targetwin','selected_action','targetkind','spawn_cells','spawn_ranks')},
                    mean_reward=means_r, mean_win=means_w)
                leaf = heads[task][arm]; before = leaf.updates; previous = snapshot_weights(leaf)
                leaf.reward_weights.flags.writeable = leaf.risk_weights.flags.writeable = True
                fit = fit_supervision(leaf, roots, labels['targetreward'], labels['targetwin'], runtime, alpha=.0025)
                leaf.freeze()
                if leaf.updates-before != GROUPS or fit['learning_counts']['rootgroup_updates'] != GROUPS:
                    raise ValueError('V319 must process exactly one current prediction/update per frozen rootgroup')
                version = save_version(leaf, source, identity, initial[task]['context_id'], arm, number,
                    directory/f'{arm}_v{number}.npz', base=versions[task][arm], previous=previous)
                del previous
                versions[task][arm] = version
                arms[arm] = dict(supervision=dict(_compact(labels), group_artifact=artifact), fit=fit,
                    updates_before=before, updates_after=leaf.updates, head_version=version,
                    evaluations=_evaluate(leaf,identity,task,belief,runtime,engine,version))
            # Address multiplicity may change; rootgroup prediction/update budgets must not.
            for key in ('rootgroup_updates','current_predictions','reward_predictions','win_predictions','table_lookups'):
                if arms['FACTUAL_LOCAL']['fit']['learning_counts'][key] != arms['QUERY_LOCAL']['fit']['learning_counts'][key]:
                    raise ValueError('V319 matched rootgroups require the same current prediction budget')
            inactive_after = deepcopy(versions[other])
            unchanged = (first.updates==before_teacher_updates and not first.reward_weights.flags.writeable
                and not first.risk_weights.flags.writeable)
            if not unchanged or inactive_after != inactive_before:
                raise ValueError('V319 supervision changed frozen teacher or inactive bank')
            rounds[str(number)][task] = dict(groups=GROUPS, replicas=REPLICAS, teacher_version=teacher_version,
                teacher_unchanged=unchanged, census=census, arms=arms,
                inactive_head_versions_before=inactive_before, inactive_head_versions_after=inactive_after)
            print(json.dumps(dict(event='query_supervision_round_complete',lifecycle=identity,task=task,
                round=number,groups=GROUPS,new_training_raw=2*GROUPS*REPLICAS)),flush=True)
    row = dict(lifecycle=identity, parent=source['parent'], initial=initial, rounds=rounds,
        extraction=extraction, head_setups=setups, final_head_versions=versions)
    _save(out/'lifecycle_receipts'/f'life_{identity}.json', row)
    print(json.dumps(dict(event='query_supervision_life_complete',lifecycle=identity)),flush=True)
    return row


def _run_parent(source, document, out):
    cpu, started, compiler = process_time(), perf_counter(), _child_cpu()
    runtime = out/'runtime'/f"parent_{source['parent']}"; runtime.mkdir(parents=True, exist_ok=True)
    template, setup = load_leaf(source, runtime)
    engine = NativeValueStream(template, 319800000000+source['parent'], runtime); rows = []
    status = 'PARENT_COMPLETE'
    for life, datasets, extraction in iter_query_lifecycles(document, source['parent']):
        try:
            rows.append(_run_life(template,source,life,datasets,extraction,runtime,out,engine))
        except CensusUnavailable as error:
            status = 'HOLD_CENSUS'; rows.append(error.partial)
            _save(out/'lifecycle_receipts'/f"life_{life['lifecycle']}_partial.json",error.partial)
            print(json.dumps(dict(event='query_supervision_census_hold',parent=source['parent'],
                lifecycle=life['lifecycle'],failure=error.partial['census_failure'])),flush=True)
            break
        del datasets
    return dict(parent=source['parent'], status=status, lifecycles=rows, source_setup=setup,
        cpu_seconds=process_time()-cpu, compiler_cpu_seconds=_child_cpu()-compiler, wall_seconds=perf_counter()-started)


def accounting(document, lives, parents, cpu, wall):
    stages = [stage for row in lives for tasks in row['rounds'].values() for stage in tasks.values()]
    evaluations = [evaluation for row in lives for item in row['initial'].values() for evaluation in item['evaluations'].values()]
    evaluations += [stage['arms'][a]['evaluations'] for stage in stages for a in UPDATING_ARMS]
    perarm = {}; allarms = [stage['arms'][a] for stage in stages for a in UPDATING_ARMS]
    for arm in UPDATING_ARMS:
        items = [stage['arms'][arm] for stage in stages]
        perarm[arm] = dict(new_training_raw_tiles=sum(i['supervision']['counts']['supervision_start_spawns'] for i in items),
            rootgroups=sum(i['fit']['fitted_rootgroups'] for i in items),
            training_environment_counts=sum_counts(i['supervision']['environment_counts'] for i in items),
            supervision_counts=sum_counts(i['supervision']['counts'] for i in items),
            supervision_planning_counts=sum_counts(i['supervision']['planning_counts'] for i in items),
            supervision_representation_counts=sum_counts(i['supervision']['representation_counts'] for i in items),
            fit_counts=sum_counts(i['fit']['learning_counts'] for i in items),
            normalization_counts=sum_counts(i['fit']['normalization_counts'] for i in items),
            supervision_cpu_seconds=sum(i['supervision']['cpu_seconds'] for i in items),
            fit_cpu_seconds=sum(i['fit']['cpu_seconds'] for i in items),
            economic_census_query_counts=sum_counts(s['census']['query']['counts'] for s in stages),
            economic_census_cpu_seconds=sum(s['census']['query']['cpu_seconds']+s['census']['anchor_cpu_seconds'] for s in stages))
    worker = sum(p['cpu_seconds'] for p in parents); compiler = sum(p['compiler_cpu_seconds'] for p in parents)
    new_cpu = worker+compiler+cpu
    groups = [i['supervision']['group_artifact'] for i in allarms]
    heads = [i['head_version'] for i in allarms]; census = [s['census'] for s in stages]
    partial_queries = [row['census_failure'] for row in lives if row.get('census_failure',{}).get('query') is not None]
    query_receipts = [s['query'] for s in census]+[f['query'] for f in partial_queries]
    for arm in UPDATING_ARMS:
        perarm[arm]['economic_census_query_counts'] = sum_counts(q['counts'] for q in query_receipts)
        perarm[arm]['economic_census_cpu_seconds'] += sum(f['query']['cpu_seconds']+f['anchor_cpu_seconds'] for f in partial_queries)
    return dict(source_physical_training_repeated=False, initial_adaptation_repeated=False,
        new_training_raw_tiles=sum(p['new_training_raw_tiles'] for p in perarm.values()), per_arm=perarm,
        retained_raw_tiles_reconstructed=sum(r['extraction']['reconstructed_raw_tiles'] for r in lives),
        retained_trace_records_parsed=sum(r['extraction']['parsed_records'] for r in lives),
        retained_compressed_trace_bytes_read=sum(r['extraction']['compressed_bytes_read'] for r in lives),
        retained_selected_training_records=sum(r['extraction']['selected_training_records'] for r in lives),
        retained_fact_read_cpu_seconds=sum(r['extraction']['cpu_seconds'] for r in lives),
        new_evaluation_games=sum(len(v['game_summaries']) for v in evaluations),
        new_evaluation_environment_counts=sum_counts(v['counts']['environment'] for v in evaluations),
        new_evaluation_cpu_seconds=sum(v['cpu_seconds'] for v in evaluations),
        physical_census_query_counts=sum_counts(q['counts'] for q in query_receipts),
        physical_census_planning_counts=sum_counts(q['planning_counts'] for q in query_receipts),
        physical_census_representation_counts=sum_counts(q['representation_counts'] for q in query_receipts),
        census_files=len(census), census_saved_bytes=sum(s['saved_bytes'] for s in census),
        group_files=len(groups), group_saved_bytes=sum(s['saved_bytes'] for s in groups),
        group_array_bytes=sum(s['array_bytes'] for s in groups),
        new_head_files=len(heads), new_head_saved_bytes=sum(s['saved_bytes'] for s in heads),
        worker_cpu_seconds=worker, compiler_cpu_seconds=compiler, coordinator_cpu_seconds=cpu,
        new_experiment_cpu_seconds=new_cpu, wall_seconds=wall,
        inherited_successful_source_and_v317_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds'],
        economic_source_v317_and_experiment_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds']+new_cpu,
        scope='All new work is contained once in worker/compiler/coordinator CPU; component CPU is not added twice. '
            'Common census is physical once and economically charged to both arms. Retained post facts are reconstructed, '
            'not new acquisition. V318 diagnostic is not required to execute either algorithm. Historical dynamics and '
            'archived failed V317 attempt CPU are unknown; this is not total historical cost closure.')


def run(source_summary, output):
    cpu, started = process_time(), perf_counter(); out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=True)
    if (out/'configuration.json').exists(): raise FileExistsError('V319 is already frozen')
    source_path = Path(source_summary).resolve(); document = json.loads(source_path.read_text())
    audit = json.loads((source_path.parent/'audit.json').read_text())
    if document['status']!='EXPERIMENT_COMPLETE' or not audit['independent_valid']:
        raise ValueError('V319 requires the audited complete frozen V317 cohort')
    settings = configuration(source_path); _save(out/'configuration.json', settings)
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for job in as_completed([pool.submit(_run_parent,s,document,out) for s in document['source_provenance']['parents']]):
            result = job.result(); parents.append(result)
            _save(out/f"parent_{result['parent']}_receipt.json", {k:v for k,v in result.items() if k!='lifecycles'})
    parents.sort(key=lambda p:p['parent'])
    lives = sorted((r for p in parents for r in p['lifecycles']),key=lambda r:r['lifecycle'])
    hold = any(p['status']=='HOLD_CENSUS' for p in parents)
    analysis = (dict(primary_self_improvement_status='HOLD_CENSUS',primary_self_improvement_supported=False,
        coverage_intervention_status='HOLD_CENSUS',coverage_intervention_supported=False,
        retained_improvement_supported=False,coverage_mechanism_supported=False,
        census_failures=[dict(lifecycle=r['lifecycle'],parent=r['parent'],**r['census_failure']) for r in lives if 'census_failure' in r],
        reason='Whole frozen cohort cannot supply the declared census; no effect inference or replacements.') if hold else summarize(lives))
    status = 'HOLD_CENSUS' if hold else 'EXPERIMENT_COMPLETE' if analysis['complete_game_endpoints'] else 'HOLD_CUTOFF'
    result = dict(schema='acfqp.query_supervision.v319', status=status,
        scientific_gate='EXPLORATORY_NO_U006_AUTHORIZATION', settings=settings, source_summary=str(source_path),
        source_provenance=document['source_provenance'], by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents], summary=analysis,
        accounting=accounting(document,lives,parents,process_time()-cpu,perf_counter()-started))
    _save(out/'summary.json',result)
    print(json.dumps(dict(event='query_supervision_complete',status=result['status'],
        primary=analysis['primary_self_improvement_status'],retained=analysis['retained_improvement_supported'])),flush=True)
    return result
