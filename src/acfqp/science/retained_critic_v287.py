"""One fixed factual actor dataset, two critic targets, fresh H2 control."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS

ARMS = ('FROZEN', 'SHADOW_TD', 'EPISODIC_MC')
EVALUATION_GAMES = 16


def evaluation_seed(life, episode):
    return 287500000000 + life*1000000 + episode


def freeze_configuration(source_summary):
    return dict(schema='acfqp.retained_critic_freeze.v287',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/RETAINED_CRITIC_V287.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)),
        parents=4, arms=ARMS, phase='A', fit_fraction=.8, alpha=.0025,
        evaluation_games=EVALUATION_GAMES, seed_evaluation=287500000000,
        bootstrap_draws=20000, bootstrap_seed=28700001, max_steps=MAX_STEPS,
        finite_test_passes=dict(native=8, reconstruction=7, analysis=9, driver=3),
        query=QUERY, primary='EPISODIC_MC_minus_FROZEN',
        observations='RETAINED_FROZEN_A_ALL_RAW_INCLUDING_INITIAL',
        evaluation='STATIC_FIT_PREFIX_BELIEF_AND_VALUE_WITHOUT_FEEDBACK')


def compact_dataset(dataset):
    return {key: value for key, value in dataset.items()
            if key not in ('afterstates', 'rewards', 'ends', 'terminal_codes')}


def _run_parent(source, parent_receipt, original_lives, output):
    from .native_retained_critic_v287 import fit_retained, score_retained
    from .native_value_stream_v286 import NativeValueStream
    from .retained_actor_data_v287 import load_retained_parent
    started, cpu_started = perf_counter(), process_time()
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    runtime = Path(output)/'runtime'/f"parent_{source['parent']}"
    runtime.mkdir(parents=True, exist_ok=True)
    life_ids = parent_receipt['lifecycle_ids']
    datasets = load_retained_parent(parent_receipt['trace_file'], life_ids, original_lives)
    template, setup = load_leaf(source, runtime)
    engine = NativeValueStream(template, evaluation_seed(life_ids[0], 0), runtime)
    rows = []
    for life in life_ids:
        dataset = datasets.pop(life)
        memory = SpawnMemory.from_payload(dataset['fit_memory'])
        estimated_p = memory.predict()
        snapshot = dict(memory=memory.to_payload(), estimated_p_four=estimated_p)
        arms = {}
        update_inventory = {}
        for arm in ARMS:
            if arm == 'FROZEN':
                leaf = template
                fit = dict(method='NONE', trained_afterstates=0, learning_counts={},
                    target_counts={}, seconds=0., cpu_seconds=0.)
                head_setup = dict(source_weights_shared=True, setup_counts={},
                    setup_seconds=0., private_weight_bytes=0)
            else:
                leaf = QueryTD(template.parent, 'PRIOR', runtime)
                head_setup = dict(source_weights_shared=False,
                    setup_counts=dict(leaf.setup_counts), setup_seconds=leaf.setup_seconds,
                    private_weight_bytes=leaf.weights.nbytes)
                fit = fit_retained(leaf, dataset,
                    'TD' if arm == 'SHADOW_TD' else 'MC', runtime)
                leaf.freeze()
            updates_before = leaf.updates
            heldout = score_retained(leaf, dataset, runtime)
            before_eval = engine.state()
            evaluated = engine.evaluate_games(leaf, estimated_p, .1,
                [evaluation_seed(life, episode) for episode in range(EVALUATION_GAMES)],
                depth=2, max_steps=MAX_STEPS)
            if engine.state() != before_eval or leaf.updates != updates_before:
                raise ValueError('Static scoring/evaluation changed the learner stream or updates')
            update_inventory[arm] = leaf.updates
            arms[arm] = dict(fit=fit, head_setup=head_setup, heldout=heldout,
                game_summaries=evaluated['game_summaries'], evaluation_counts=evaluated['counts'],
                evaluation_seconds=evaluated['seconds'], evaluation_cpu_seconds=evaluated['cpu_seconds'],
                new_value_updates=leaf.updates)
            print(json.dumps(dict(event='retained_critic_arm_complete', lifecycle=life,
                arm=arm, updates=leaf.updates, heldout=heldout['metrics'],
                mean_eval_utility=sum(g['utility'] for g in evaluated['game_summaries'])/16)), flush=True)
            if arm != 'FROZEN':
                del leaf
        if update_inventory['FROZEN'] != 0 or update_inventory['SHADOW_TD'] != update_inventory['EPISODIC_MC']:
            raise ValueError('Critics did not fit the same nonwinning afterstate inventory')
        rows.append(dict(lifecycle=life, parent=source['parent'], dataset=compact_dataset(dataset),
            evaluation_snapshot=snapshot, arms=arms))
    engine.close()
    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=source['parent'], lifecycles=rows, source_setup=setup,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts), seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime
            - children_before.ru_utime-children_before.ru_stime)


def build_accounting(original, lives, parents, coordinator_cpu, wall_seconds):
    """Inherited acquisition is economic per arm; physical reuse is counted once."""
    original_lives = {life['lifecycle']: life for life in original['by_lifecycle']}
    inherited_old = original['accounting']['inherited_costs_per_arm']['FROZEN']
    retained_counts = {kind: dict(sum((Counter(original_lives[life['lifecycle']]['arms']['FROZEN']
        ['phases']['A']['training']['counts'][kind]) for life in lives), Counter()))
        for kind in ('environment', 'planning', 'learning')}
    retained_raw = retained_counts['environment']['raw_tile_productions']
    inherited = dict(source_training_raw_tiles=inherited_old['source_training_raw_tiles'],
        source_training_games=inherited_old['source_training_games'],
        source_training_environment_counts=inherited_old['source_training_environment_counts'],
        source_training_seconds=inherited_old['source_training_seconds'],
        dynamics_raw_tiles=inherited_old['dynamics_raw_tiles'], dynamics_costs=inherited_old['dynamics_costs'],
        warmup_raw_tiles=inherited_old['warmup_raw_tiles'],
        warmup_environment_counts=inherited_old['warmup_environment_counts'],
        warmup_direct_counts=inherited_old['warmup_direct_counts'],
        warmup_memory_counts=inherited_old['warmup_memory_counts'],
        retained_actor_A_raw_tiles=retained_raw, retained_actor_A_counts=retained_counts)
    economic = sum(inherited[key] for key in ('source_training_raw_tiles', 'dynamics_raw_tiles',
        'warmup_raw_tiles', 'retained_actor_A_raw_tiles'))
    evaluation = {kind: dict(sum((Counter(life['arms'][arm]['evaluation_counts'][kind])
        for life in lives for arm in ARMS), Counter())) for kind in ('environment', 'planning')}
    return dict(new_training_environment_observations=0,
        economic_training_raw_tiles_per_arm={arm: economic for arm in ARMS},
        inherited_costs_per_arm={arm: inherited for arm in ARMS},
        retained_physical_A_raw_tiles=retained_raw, retained_physical_A_counts=retained_counts,
        shared_warmup_raw_tiles=inherited_old['warmup_raw_tiles'],
        reconstruction_costs_by_lifecycle={str(life['lifecycle']): life['dataset']['costs'] for life in lives},
        new_value_updates={arm: sum(life['arms'][arm]['new_value_updates'] for life in lives) for arm in ARMS},
        fit_counts={arm: dict(sum((Counter(life['arms'][arm]['fit']['learning_counts'])
            for life in lives), Counter())) for arm in ARMS},
        fit_target_counts={arm: dict(sum((Counter({key: value for key, value in
            life['arms'][arm]['fit']['target_counts'].items() if key != 'target_buffer_doubles_peak'})
            for life in lives), Counter())) for arm in ARMS},
        fit_target_buffer_doubles_peak={arm: max(life['arms'][arm]['fit']['target_counts']
            .get('target_buffer_doubles_peak', 0) for life in lives) for arm in ARMS},
        heldout_prediction_counts={arm: dict(sum((Counter(life['arms'][arm]['heldout']['prediction_counts'])
            for life in lives), Counter())) for arm in ARMS},
        heldout_target_counts={arm: dict(sum((Counter({key: value for key, value in
            life['arms'][arm]['heldout']['target_counts'].items() if key != 'target_buffer_doubles_peak'})
            for life in lives), Counter())) for arm in ARMS},
        heldout_target_buffer_doubles_peak={arm: max(life['arms'][arm]['heldout']['target_counts']
            .get('target_buffer_doubles_peak', 0) for life in lives) for arm in ARMS},
        evaluation_counts=evaluation,
        private_head_weight_bytes_created={arm: sum(life['arms'][arm]['head_setup']['private_weight_bytes']
            for life in lives) for arm in ARMS},
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents),
        compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),
        coordinator_cpu_seconds=coordinator_cpu, wall_seconds=wall_seconds,
        acquisition_scope='The common source, warmup and complete retained FROZEN A acquisition are charged '
            'equally to each arm; old physical acquisition occurred once. Processing and fresh evaluation are new costs.')


def run(source_summary, output):
    from .retained_critic_analysis_v287 import summarize
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'summary.json').exists() or (output/'configuration.json').exists():
        raise FileExistsError('V287 formal results or freeze configuration already exist')
    original = json.loads(Path(source_summary).read_text())
    audit = json.loads(Path(source_summary).with_name('audit.json').read_text())
    if not audit['independent_valid']:
        raise ValueError('Retained V286 actor data must have a passing independent audit')
    configuration = freeze_configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n')
    started, cpu_started = perf_counter(), process_time()
    original_lives = {life['lifecycle']: life for life in original['by_lifecycle']}
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_run_parent, source, original['parent_receipts'][source['parent']],
            original_lives, output) for source in original['source_provenance']['parents']]
        for future in as_completed(futures):
            parents.append(future.result())
    parents.sort(key=lambda row: row['parent'])
    lives = sorted([life for parent in parents for life in parent['lifecycles']],
        key=lambda row: row['lifecycle'])
    analysis = summarize(lives)
    accounting = build_accounting(original, lives, parents,
        process_time()-cpu_started, perf_counter()-started)
    result = dict(schema='acfqp.retained_critic.v287', status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', settings=configuration,
        source_provenance=original['source_provenance'], by_lifecycle=lives,
        parent_receipts=[dict({key: value for key, value in parent.items() if key != 'lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']]) for parent in parents],
        summary=analysis, accounting=accounting)
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='retained_critic_complete', status=result['status'],
        contrasts=analysis['paired_contrasts'], accounting=accounting)), flush=True)
    return result
