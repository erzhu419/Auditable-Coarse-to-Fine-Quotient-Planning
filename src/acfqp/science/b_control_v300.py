"""Target-only Bellman control ablation on all retained stable-B histories."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_control_analysis_v300 import ARMS, BOOTSTRAP_SEED, summarize
from .b_mechanism_v299 import load_parent, sum_counts
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .native_b_control_v300 import fit_control
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .retained_critic_v287 import compact_dataset

EVALUATION_GAMES = 32


def evaluation_seed(life, episode):
    return 300900000000 + life*1000000 + episode


def configuration(source_summary):
    return dict(schema='acfqp.b_control_freeze.v300',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/B_CONTROL_V300.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(64)), parents=4,
        arms=ARMS, phase='B', true_p_four=.5,
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='ALL_RETAINED_V298_B_COMPLETE_GAMES_WITHOUT_NEW_TRAINING_ACQUISITION',
        fit_fraction=.8, alpha=.0025, query=QUERY,
        target_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        control_target='H2_EXPECTED_NEXT_DIRECT_MAX_FROM_GAME_START_HEAD',
        consolidation='PER_GAME_ADDRESS_OCCURRENCE_NORMALIZED_MEAN',
        seed_evaluation=300900000000, evaluation_games=EVALUATION_GAMES, max_steps=MAX_STEPS,
        bootstrap_draws=20000, bootstrap_seed=BOOTSTRAP_SEED,
        primary='EXPECTED_CONTROL_minus_SOURCE_COMPLETE_GAME_UTILITY',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        training='RETAINED_PURE_B_TARGET_ONLY_COMPARISON',
        finite_test_passes=dict(native=9,analysis=14,independent_audit=13,driver=4),
        stop_rule='NO_PRIMARY_GAIN_STOPS_TARGET_BRANCH_WITHOUT_HYPERPARAMETER_OR_SEED_TUNING')


def _fit_identity(fit):
    return {key:fit[key] for key in ('method','alpha','fitted_games','fitted_steps',
        'trained_afterstates','learning_counts','target_counts','consolidation_counts',
        'first_sample','last_sample')}


def _run_lifecycle(template, data, old, runtime, engine):
    life, parent = old['lifecycle'], old['parent']
    memory = SpawnMemory.from_payload(data['fit_memory'])
    p = memory.predict()
    snapshot = dict(memory=memory.to_payload(), estimated_p_four=p)
    if compact_dataset(data) != old['dataset'] or snapshot != old['evaluation_snapshot']:
        raise ValueError('Retained B data or fixed fit-prefix belief changed')
    arms = {}
    for arm in ARMS:
        if arm == 'SOURCE':
            leaf = template
            fit = dict(method='NONE', trained_afterstates=0, learning_counts={}, target_counts={},
                planning_counts={}, consolidation_counts={}, seconds=0., cpu_seconds=0.)
            head_setup = dict(source_weights_shared=True, setup_counts={}, setup_seconds=0.,
                setup_cpu_seconds=0., private_weight_bytes=0)
        else:
            setup_cpu = process_time()
            leaf = QueryTD(template.parent, 'PRIOR', runtime)
            head_setup = dict(source_weights_shared=False, setup_counts=dict(leaf.setup_counts),
                setup_seconds=leaf.setup_seconds, setup_cpu_seconds=process_time()-setup_cpu,
                private_weight_bytes=leaf.weights.nbytes)
            fit = (fit_consolidated(leaf, data, 'EPISODE_MEAN_MC', runtime)
                if arm == 'MC' else fit_control(leaf, data, p, runtime))
            if arm == 'MC' and _fit_identity(fit) != _fit_identity(old['arms']['EPISODE_MEAN_MC']['fit']):
                raise ValueError('MC did not reproduce the original V298 fit')
            leaf.freeze()
        updates_before = leaf.updates
        heldout = score_retained(leaf, data, runtime)
        if arm != 'EXPECTED_CONTROL':
            prior = old['arms']['FROZEN' if arm == 'SOURCE' else 'EPISODE_MEAN_MC']['heldout']
            if heldout['game_metrics'] != prior['game_metrics']:
                raise ValueError('Full SOURCE/MC heldout predictions did not reproduce V298')
        before_eval = engine.state()
        evaluated = engine.evaluate_games(leaf, p, .5,
            [evaluation_seed(life, episode) for episode in range(EVALUATION_GAMES)],
            depth=2, max_steps=MAX_STEPS)
        if engine.state() != before_eval or leaf.updates != updates_before:
            raise ValueError('Static scoring/evaluation changed the critic or training stream')
        arms[arm] = dict(fit=fit, head_setup=head_setup, heldout=heldout,
            processed_training_samples=fit['trained_afterstates'], sample_counter=leaf.updates,
            game_summaries=evaluated['game_summaries'], evaluation_counts=evaluated['counts'],
            evaluation_seconds=evaluated['seconds'], evaluation_cpu_seconds=evaluated['cpu_seconds'],
            static_evaluation_valid=True)
        print(json.dumps(dict(event='b_control_arm_complete', lifecycle=life, arm=arm,
            samples=fit['trained_afterstates'], parameter_writes=fit['learning_counts'].get('table_updates',0),
            heldout=heldout['metrics'],
            mean_utility=sum(game['utility'] for game in evaluated['game_summaries'])/EVALUATION_GAMES)), flush=True)
        if arm != 'SOURCE':
            del leaf
    if (template.updates != 0 or arms['MC']['processed_training_samples'] !=
            arms['EXPECTED_CONTROL']['processed_training_samples']):
        raise ValueError('Source changed or target arms processed different inventories')
    return dict(lifecycle=life, parent=parent, dataset=compact_dataset(data),
        evaluation_snapshot=snapshot, arms=arms)


def _run_parent(source, receipt, old_lives, output):
    started, cpu_started = perf_counter(), process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']
    runtime = Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True, exist_ok=True)
    datasets, roots, reconstruction = load_parent(receipt, old_lives)
    del roots
    template, setup = load_leaf(source, runtime)
    engine = NativeValueStream(template, evaluation_seed(parent,0), runtime)
    rows = []
    try:
        for life in receipt['lifecycle_ids']:
            data = datasets.pop(life)
            # Keep the old acquisition cost receipt with the retained input.
            # Today's reconstruction CPU is reported separately by load_parent.
            data['costs']['processing_cpu_seconds'] = old_lives[life]['dataset']['costs']['processing_cpu_seconds']
            rows.append(_run_lifecycle(template, data, old_lives[life], runtime, engine))
            del data
    finally:
        engine.close()
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup, reconstruction=reconstruction,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts), seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime)


def build_accounting(old, lives, parents, cpu, wall):
    def stage_values(arm, stage, key):
        return [life['arms'][arm][stage].get(key,{}) for life in lives]
    def total(values):
        return sum_counts({key:value for key,value in row.items() if not key.endswith('_peak')} for row in values)
    def peaks(values):
        return {key:max(row.get(key,0) for row in values)
            for key in {key for row in values for key in row if key.endswith('_peak')}}
    def evaluation(arm):
        return {kind:sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives)
            for kind in ('environment','planning')}
    inherited = old['accounting']['inherited_costs_per_arm']['FROZEN']
    economic = old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']
    per_arm_eval = {arm:evaluation(arm) for arm in ARMS}
    return dict(new_training_environment_observations=0, new_training_environment_counts={}, physical_acquisitions=0,
        retained_B_acquisition_raw_tiles=old['accounting']['new_training_environment_observations'],
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economic),
        inherited_costs_per_arm={arm:inherited for arm in ARMS},
        inherited_B_acquisition=dict(raw_tiles=old['accounting']['new_training_environment_observations'],
            actor_raw_tiles=old['accounting']['new_actor_B_raw_tiles'],
            warmup_raw_tiles=old['accounting']['new_warmup_raw_tiles'],
            environment_counts=old['accounting']['new_training_environment_counts'],
            actor_counts=old['accounting']['new_actor_B_counts'],
            warmup_direct_counts=old['accounting']['new_warmup_direct_counts'],
            excluded_tail_raw_tiles=old['accounting']['excluded_tail_raw_tiles']),
        processed_training_samples={arm:sum(life['arms'][arm]['processed_training_samples'] for life in lives) for arm in ARMS},
        fit_counts={arm:total(stage_values(arm,'fit','learning_counts')) for arm in ARMS},
        fit_target_counts={arm:total(stage_values(arm,'fit','target_counts')) for arm in ARMS},
        fit_target_buffer_peaks={arm:peaks(stage_values(arm,'fit','target_counts')) for arm in ARMS},
        fit_planning_counts={arm:total(stage_values(arm,'fit','planning_counts')) for arm in ARMS},
        fit_setup_counts={arm:total(stage_values(arm,'fit','setup_counts')) for arm in ARMS},
        consolidation_counts={arm:total(stage_values(arm,'fit','consolidation_counts')) for arm in ARMS},
        consolidation_buffer_peaks={arm:peaks(stage_values(arm,'fit','consolidation_counts')) for arm in ARMS},
        heldout_prediction_counts={arm:total(stage_values(arm,'heldout','prediction_counts')) for arm in ARMS},
        heldout_target_counts={arm:total(stage_values(arm,'heldout','target_counts')) for arm in ARMS},
        heldout_target_buffer_peaks={arm:peaks(stage_values(arm,'heldout','target_counts')) for arm in ARMS},
        heldout_setup_counts={arm:total(stage_values(arm,'heldout','setup_counts')) for arm in ARMS},
        head_setup_counts={arm:sum_counts(life['arms'][arm]['head_setup']['setup_counts'] for life in lives) for arm in ARMS},
        private_head_weight_bytes_created={arm:sum(life['arms'][arm]['head_setup']['private_weight_bytes'] for life in lives) for arm in ARMS},
        processing_seconds_per_arm={arm:dict(
            **{stage:sum(life['arms'][arm][stage]['seconds'] for life in lives) for stage in ('fit','heldout')},
            head_setup=sum(life['arms'][arm]['head_setup']['setup_seconds'] for life in lives)) for arm in ARMS},
        processing_cpu_seconds_per_arm={arm:dict(
            **{stage:sum(life['arms'][arm][stage]['cpu_seconds'] for life in lives) for stage in ('fit','heldout')},
            head_setup=sum(life['arms'][arm]['head_setup']['setup_cpu_seconds'] for life in lives)) for arm in ARMS},
        evaluation_counts_per_arm=per_arm_eval,
        evaluation_counts={kind:sum_counts(per_arm_eval[arm][kind] for arm in ARMS) for kind in ('environment','planning')},
        evaluation_cpu_seconds_per_arm={arm:sum(life['arms'][arm]['evaluation_cpu_seconds'] for life in lives) for arm in ARMS},
        evaluation_seconds_per_arm={arm:sum(life['arms'][arm]['evaluation_seconds'] for life in lives) for arm in ARMS},
        retained_canonical_trace_bytes=old['accounting']['canonical_trace_bytes'],
        canonical_rows_read=sum(parent['reconstruction']['canonical_rows_read'] for parent in parents),
        reconstruction_counts=sum_counts(parent['reconstruction']['reconstruction_counts'] for parent in parents),
        reconstruction_cpu_seconds=sum(parent['reconstruction']['cpu_seconds'] for parent in parents),
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents),
        compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall,
        accounting_scope='Retained source, dynamics and all old B raw are inherited once physically and paid economically '
            'by each arm. No new training acquisition. Target enumeration, normalization, head copies, reconstruction, '
            'heldout scoring and new complete-game evaluation are actual additional computation; their CPU is contained '
            'in worker CPU, not added again. Same training observations and parameter writes are not equal compute budgets.')


def run(source_summary, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V300 formal freeze or results already exist')
    source_summary = Path(source_summary).resolve()
    old = json.loads(source_summary.read_text())
    if not json.loads(source_summary.with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V298 retained training provenance requires its passing independent audit')
    settings = configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started, cpu_started = perf_counter(), process_time()
    old_lives = {row['lifecycle']:row for row in old['by_lifecycle']}
    receipts = {row['parent']:row for row in old['parent_receipts']}
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, receipts[source['parent']], old_lives, output)
            for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda row:row['parent'])
    lives = sorted([life for parent in parents for life in parent['lifecycles']],key=lambda row:row['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.b_control.v300', status='EXPERIMENT_COMPLETE', scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings, source_provenance=old['source_provenance'], by_lifecycle=lives,
        parent_receipts=[dict({key:value for key,value in parent.items() if key!='lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']]) for parent in parents],
        summary=analysis, accounting=build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='b_control_complete',status=result['status'],
        control_target_gain_supported=analysis['control_target_gain_supported'],
        utility_primary=analysis['paired_contrasts'][analysis['primary_contrast']])),flush=True)
    return result
