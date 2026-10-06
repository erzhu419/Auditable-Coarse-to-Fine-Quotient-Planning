"""Four new zero-initialized V120 risk_goal learners on fresh natural games."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .controlled_predictive_ntuple_td_v120 import NtupleValue
from .controlled_predictive_regime_experience_v115 import run_episode
from .controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from .natural_model_revision_v281 import load_sources

ROOT = Path(__file__).resolve().parents[3]
DYNAMICS_CAPSULE = ROOT / 'reports/controlled_predictive_ntuple_learning_v120/source_capsule.json'
OUTPUT = ROOT / 'reports/fresh_source_v312'
PARENTS, TRAIN_EPISODES, MAX_STEPS, WORKERS = (0, 1, 2, 3), 4096, 2000, 4
BLOCK_SIZE, ALPHA, P_FOUR, SEED_BASE = 256, .0025, .1, 31200000000
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def _save(path, value):
    Path(path).write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def _delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def training_seed(parent, episode):
    return SEED_BASE + 1_000_000 + parent * 100_000 + 10_000 + episode


def configuration(dynamics_capsule=DYNAMICS_CAPSULE):
    return dict(schema='acfqp.fresh_source.v312', parents=list(PARENTS),
        games_per_parent=TRAIN_EPISODES, max_steps=MAX_STEPS, workers=WORKERS,
        block_size=BLOCK_SIZE, alpha=ALPHA, p_four=P_FOUR, seed_base=SEED_BASE,
        query=deepcopy(QUERY), queries=dict(risk_goal=deepcopy(QUERY)),
        initialization='ZERO_NTUPLE_WEIGHTS', dynamics='FIXED_ORIGINAL_V120_CAPSULE_ONLY',
        dynamics_capsule=str(Path(dynamics_capsule).resolve()),
        training_order='CHOOSE_NEXT_ACTION_BEFORE_PREVIOUS_AFTERSTATE_UPDATE',
        terminal_targets=dict(LOST=-4., WON='ANALYTIC_LAST_UNTRAINED',
                              CUTOFF='LAST_PENDING_UNTRAINED'),
        checkpoints=[TRAIN_EPISODES], evaluations=0)


def train_game(model, parent, episode):
    """V120 TD timing, with recorded decision/update events and an explicit seed."""
    seed, before = training_seed(parent, episode), dict(model.counts)
    updates_before, pending = model.updates, None
    decision_updates_before, decision_values, previous_update_targets = [], [], []

    def act(board, step):
        nonlocal pending
        decision_updates_before.append(model.updates)
        chosen = model.choose(board, QUERY)
        decision_values.append(chosen['value'])
        previous_update_targets.append(None if pending is None else chosen['value'])
        if pending is not None:
            model.update(pending, chosen['value'], ALPHA)
        pending = (None if max(chosen['afterstate']) >= model.rule.goal_rank
                   else chosen['afterstate'])
        return chosen['action']

    game = run_episode(seed, act, P_FOUR, MAX_STEPS)
    terminal_update = game['status'] == 'LOST' and pending is not None
    terminal_update_target = -QUERY['failure_penalty'] if terminal_update else None
    if terminal_update:
        started = perf_counter()
        model.update(pending, terminal_update_target, ALPHA)
        game['seconds'] += perf_counter() - started
    expected = game['steps_count'] - (game['status'] in ('WON', 'CUTOFF'))
    if model.updates - updates_before != expected:
        raise AssertionError('TD update count does not match terminal/censoring semantics')
    result = dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=game['return_score'] / 2048. - 4. * (game['status'] == 'LOST')
            + 4. * (game['status'] == 'WON'), environment_counts=game['work'],
        planning_counts={}, learning_counts=_delta(model.counts, before),
        setup_counts={}, setup_seconds=0., seconds=game['seconds'],
        updates_before=updates_before, updates_after=model.updates)
    row = dict(life=parent, query='risk_goal', method='TRAIN', checkpoint=None,
        replica=None, seed=seed, episode_index=episode, terminal_update=terminal_update,
        censored_last_update=game['status'] == 'CUTOFF', analytic_terminal=game['status'] == 'WON',
        result=result)
    raw = dict(**row, initial_board=game['initial_board'],
        initial_spawns=game['initial_spawns'], final_board=game['final_board'],
        actions=[s['action'] for s in game['steps']],
        spawned_cells=[s['spawned_cell'] for s in game['steps']],
        spawned_ranks=[s['spawned_rank'] for s in game['steps']],
        scores=[s['score'] for s in game['steps']],
        decision_updates_before=decision_updates_before, decision_values=decision_values,
        previous_update_targets=previous_update_targets, terminal_update_target=terminal_update_target)
    return row, raw


def _empty_block(start):
    return dict(start=start, end=start, games=0, environment_counts=Counter(),
        learning_counts=Counter(), statuses=Counter(), total_score=0, seconds=0.)


def _add_training(block, row):
    result = row['result']
    block['end'] = row['episode_index'] + 1
    block['games'] += 1
    block['environment_counts'].update(result['environment_counts'])
    block['learning_counts'].update(result['learning_counts'])
    block['statuses'][result['status']] += 1
    block['total_score'] += result['score']
    block['seconds'] += result['seconds']


def _child_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _run_parent(source, directory):
    started, cpu_started, compiler_started = perf_counter(), process_time(), _child_cpu()
    directory = Path(directory)
    folder = directory / f"life_{source['life']}"
    query_folder = folder / 'risk_goal'
    query_folder.mkdir(parents=True)
    setup_cpu = process_time()
    model = NtupleValue(LearnedDynamics.from_payload(source['rule']), folder / 'build')
    model.setup_counts['zero_initialized_weight_parameters'] = int(model.weights.size)
    setup_cpu = process_time() - setup_cpu
    trace = query_folder / 'training.jsonl.gz'
    query = dict(training_blocks=[], checkpoints=[], references=[],
        initial_updates=model.updates, initial_nonzero_parameters=0,
        setup_counts=dict(model.setup_counts), setup_seconds=model.setup_seconds,
        training_trace=str(trace.relative_to(directory)))
    lifecycle = dict(life=source['life'], queries=dict(risk_goal=query))
    block = _empty_block(0)
    with gzip.open(trace, 'xt') as stream:
        for episode in range(TRAIN_EPISODES):
            row, raw = train_game(model, source['life'], episode)
            stream.write(json.dumps(raw, allow_nan=False, separators=(',', ':')) + '\n')
            _add_training(block, row)
            done = episode + 1
            if done % BLOCK_SIZE == 0 or done == TRAIN_EPISODES:
                stream.flush()
                query['training_blocks'].append(block)
                _save(folder / 'lifecycle.json', lifecycle)
                print(json.dumps(dict(event='fresh_source_block_complete', life=source['life'],
                    episodes=done, updates=model.updates, statuses=dict(block['statuses']),
                    seconds=block['seconds'])), flush=True)
                block = _empty_block(done)
    path = query_folder / f'checkpoint_{TRAIN_EPISODES}.npz'
    save_started, save_cpu, before = perf_counter(), process_time(), dict(model.counts)
    metadata = model.save(path)
    save_seconds, save_cpu = perf_counter() - save_started, process_time() - save_cpu
    query['checkpoints'].append(dict(episodes=TRAIN_EPISODES,
        model_file=str(path.relative_to(directory)), updates=model.updates,
        parameter_count=metadata['parameter_count'], nonzero_weights=metadata['nonzero_weights'],
        bytes=metadata['bytes'], model_bytes=metadata['bytes'], model_metadata=metadata,
        save_counts=_delta(model.counts, before), save_seconds=save_seconds, evaluations=[]))
    query['final_updates'] = model.updates
    query['source_operation_counts'] = dict(model.counts)
    query['training_trace_bytes'] = trace.stat().st_size
    _save(folder / 'lifecycle.json', lifecycle)
    lifecycle['fresh_source_compute'] = dict(worker_cpu_seconds=process_time() - cpu_started,
        compiler_cpu_seconds=_child_cpu() - compiler_started, wall_seconds=perf_counter() - started,
        setup_cpu_seconds=setup_cpu, checkpoint_save_cpu_seconds=save_cpu)
    return lifecycle


def run(dynamics_capsule=DYNAMICS_CAPSULE, output=OUTPUT):
    started, cpu_started = perf_counter(), process_time()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ('configuration.json', 'run.json', 'source_summary.json')):
        raise FileExistsError('Fresh SOURCE output already contains a run')
    capsule = json.loads(Path(dynamics_capsule).read_text())
    sources = sorted(capsule['snapshots'], key=lambda row: row['life'])
    if [row['life'] for row in sources] != list(PARENTS):
        raise ValueError('Fresh SOURCE requires the four original V120 dynamics parents')
    if any(row['rule']['goal_rank'] != 11 for row in sources):
        raise ValueError('Fresh SOURCE uses the original goal-rank-11 dynamics')
    settings = configuration(dynamics_capsule)
    _save(output / 'configuration.json', settings)
    _save(output / 'source_capsule.json', capsule)
    record = dict(schema='acfqp.fresh_source.v312', status='SOURCE_RUNNING',
        settings=settings, lifecycles=[])
    _save(output / 'run.json', record)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        jobs = [pool.submit(_run_parent, source, output) for source in sources]
        for job in as_completed(jobs):
            record['lifecycles'].append(job.result())
            _save(output / 'run.json', record)
    record['lifecycles'].sort(key=lambda row: row['life'])
    record['status'] = 'SOURCE_COMPLETE'
    _save(output / 'run.json', record)
    provenance = load_sources(output)
    provenance['scope'] = ('Four new risk_goal SOURCE values trained from zero on fresh V312 seeds; '
        'only original V120 dynamics and their acquisition costs are inherited. '
        'No old value checkpoints, reward learners or evaluation games are used.')
    environment = sum((Counter(parent['inherited_training_costs']['environment_counts'])
                       for parent in provenance['parents']), Counter())
    receipts = [row['fresh_source_compute'] for row in record['lifecycles']]
    compute = dict(worker_cpu_seconds=sum(r['worker_cpu_seconds'] for r in receipts),
        compiler_cpu_seconds=sum(r['compiler_cpu_seconds'] for r in receipts),
        coordinator_cpu_seconds=process_time() - cpu_started, wall_seconds=perf_counter() - started,
        includes_source_setup_training_checkpoint_save=True,
        scope='Worker job entry through setup, training, trace/progress IO and final checkpoint save; '
              'compiler child CPU separately; coordinator run entry through completed aggregation. '
              'Historical inherited dynamics CPU is unavailable and excluded. '
              'Setup and save CPU are contained in worker CPU, not added again.')
    compute['full_source_cpu_seconds'] = sum(compute[key] for key in
        ('worker_cpu_seconds', 'compiler_cpu_seconds', 'coordinator_cpu_seconds'))
    dynamics = capsule['inherited_costs']
    source_costs = dict(source_training_raw_tiles=environment['initial_spawns'] + environment['sampled_transitions'],
        source_training_games=sum(p['inherited_training_costs']['training_games'] for p in provenance['parents']),
        source_training_environment_counts=dict(environment),
        source_training_seconds=sum(p['inherited_training_costs']['training_seconds'] for p in provenance['parents']),
        dynamics_raw_tiles=dynamics['source_environment']['initial_spawns'] + dynamics['source_environment']['sampled_transitions'],
        dynamics_costs=deepcopy(dynamics), fresh_source_compute=compute)
    summary = dict(schema='acfqp.fresh_source.v312', status='SOURCE_COMPLETE', settings=settings,
        source_provenance=provenance, accounting=dict(inherited_costs_per_arm=dict(SOURCE=source_costs)))
    _save(output / 'source_summary.json', summary)
    return summary
