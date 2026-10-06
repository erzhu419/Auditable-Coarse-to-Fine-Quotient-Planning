"""Execution-only spawn-model revision over one unchanged natural-game value leaf.

The four V120 parents are reused, not independent new value-training histories.
Only fresh spawn memories and game suffixes differ between the 16 lifecycles.
"""
from collections import Counter
import json
from pathlib import Path
import random
from time import perf_counter, process_time

from .controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from .controlled_predictive_ntuple_td_v120 import NtupleValue
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_paired_ntuple_v130 import QueryParent
from .controlled_predictive_regime_experience_v115 import observed_rank, run_episode
from .controlled_predictive_regime_memory_v115 import SpawnMemory, WARMUP
from .controlled_predictive_relational_dynamics_v69 import LearnedDynamics

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'reports/controlled_predictive_ntuple_learning_v120'
RUNTIME = ROOT / 'reports/natural_model_revision_v281/runtime'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
ARMS = ('DIRECT', 'FROZEN_H2', 'POOLED_H2', 'LIBRARY_H2')
METHODS = dict(DIRECT='FROZEN', FROZEN_H2='FROZEN',
               POOLED_H2='POOLED', LIBRARY_H2='LIBRARY')
PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
LIFECYCLES = tuple(range(16))
EPISODES_PER_PHASE = 8
MAX_STEPS = 8192
BOOTSTRAP_DRAWS, BOOTSTRAP_SEED = 20000, 28100001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def seed_base(lifecycle):
    return 28140100 + 100 * lifecycle


def environment_seed(lifecycle, phase_index, episode):
    return seed_base(lifecycle) + phase_index * EPISODES_PER_PHASE + episode


def warmup_seed(lifecycle, episode):
    # Separate stream family; whole-game warmup never consumes an online seed.
    return 28100000000 + 100000 * lifecycle + episode


def utility(game):
    return (game['return_score'] / 2048. - 4. * (game['status'] == 'LOST')
            + 4. * (game['status'] == 'WON'))


def delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def load_sources(source_dir=SOURCE):
    """Read only required risk_goal training costs, excluding old evaluations."""
    source_dir = Path(source_dir)
    capsule = json.loads((source_dir / 'source_capsule.json').read_text())
    run = json.loads((source_dir / 'run.json').read_text())
    snapshots = {row['life']: row for row in capsule['snapshots']}
    parents = []
    for life in range(4):
        record = next(row for row in run['lifecycles'] if row['life'] == life)
        q = record['queries']['risk_goal']
        cp = next(row for row in q['checkpoints'] if row['episodes'] == 4096)
        blocks = q['training_blocks']
        costs = dict(
            environment_counts=dict(sum((Counter(b['environment_counts']) for b in blocks), Counter())),
            learning_counts=dict(sum((Counter(b['learning_counts']) for b in blocks), Counter())),
            training_seconds=sum(b['seconds'] for b in blocks),
            training_games=sum(b['games'] for b in blocks),
            setup_counts=q['setup_counts'], setup_seconds=q['setup_seconds'],
            checkpoint_save_counts=dict(sum((Counter(c['save_counts']) for c in q['checkpoints']), Counter())),
            checkpoint_save_seconds=sum(c['save_seconds'] for c in q['checkpoints']))
        parents.append(dict(parent=life, rule=snapshots[life]['rule'],
            checkpoint=str((source_dir / cp['model_file']).resolve()),
            updates=cp['updates'], source_query=run['settings']['queries']['risk_goal'],
            inherited_training_costs=costs))
    return dict(parents=parents, inherited_dynamics_costs=capsule['inherited_costs'],
        scope='Four risk_goal source learners once; reward learners and old evaluations excluded. '
              'Supplied dynamics acquisition is retained separately, not new natural feedback.')


def load_leaf(source, runtime=RUNTIME):
    """All arms receive this exact frozen QueryTD object and weight storage."""
    started, cpu_started = perf_counter(), process_time()
    rule = LearnedDynamics.from_payload(source['rule'])
    native = NtupleValue.load(source['checkpoint'], rule, runtime)
    native.weights.flags.writeable = False
    parent = QueryParent(native, source['source_query'], QUERY, .5)
    leaf = QueryTD(parent, 'PRIOR', runtime)
    leaf.freeze()
    return leaf, dict(wall_seconds=perf_counter() - started,
        cpu_seconds=process_time() - cpu_started,
        setup_counts=dict(native.setup_counts + leaf.setup_counts),
        checkpoint_loads=1,
        checkpoint_loaded_parameters=native.counts['checkpoint_loaded_parameters'],
        leaf_weight_bytes=leaf.weights.nbytes,
        resident_source_and_leaf_weight_bytes=native.weights.nbytes + leaf.weights.nbytes,
        inherited_updates=native.updates, new_leaf_updates=leaf.updates)


def play_game(planner, memory, seed, p_four, max_steps=MAX_STEPS):
    """Commit previous feedback before choosing; commit terminal feedback once.

    p_four is passed only to the environment. Neither memory nor planner sees
    the true law or the phase label. Initial tiles never enter spawn memory.
    """
    started, cpu_started = perf_counter(), process_time()
    before_plan, before_memory = dict(planner.counts), dict(memory.counts)
    before_observations = memory.observations_seen
    pending, decisions, events = None, [], []
    decision_seconds = decision_cpu_seconds = memory_seconds = memory_cpu_seconds = 0.

    def commit(afterstate, board, action_index):
        nonlocal memory_seconds, memory_cpu_seconds
        clock, cpu = perf_counter(), process_time()
        rank = observed_rank(dict(afterstate=afterstate, next_board=board))
        event = memory.observe(rank)
        if event is not None:
            events.append(dict(event, action_index=action_index))
        memory_seconds += perf_counter() - clock
        memory_cpu_seconds += process_time() - cpu

    def act(board, step):
        nonlocal pending, decision_seconds, decision_cpu_seconds
        nonlocal memory_seconds, memory_cpu_seconds
        if pending is not None:
            commit(pending, board, step - 1)
        clock, cpu = perf_counter(), process_time()
        p_used = memory.predict()
        planner.spawn_probabilities = (1. - p_used, p_used)
        memory_seconds += perf_counter() - clock
        memory_cpu_seconds += process_time() - cpu
        clock, cpu = perf_counter(), process_time()
        choice = planner.choose(board, QUERY)
        decision_seconds += perf_counter() - clock
        decision_cpu_seconds += process_time() - cpu
        pending = choice['afterstate']
        decisions.append(dict(action=choice['action'], value=choice['value'],
            p_four=p_used, module_id=memory.module_id,
            observations_before=memory.observations_seen))
        return choice['action']

    game = run_episode(seed, act, p_four, max_steps)
    if pending is not None:
        commit(pending, game['final_board'], game['steps_count'] - 1)
    wall, cpu = perf_counter() - started, process_time() - cpu_started
    costs = dict(environment_counts=game['work'],
        planning_counts=delta(planner.counts, before_plan),
        memory_counts=delta(memory.counts, before_memory),
        decision_seconds=decision_seconds, decision_cpu_seconds=decision_cpu_seconds,
        memory_seconds=memory_seconds, memory_cpu_seconds=memory_cpu_seconds,
        environment_seconds=max(0., wall - decision_seconds - memory_seconds),
        environment_cpu_seconds=max(0., cpu - decision_cpu_seconds - memory_cpu_seconds),
        cpu_seconds=cpu, wall_seconds=wall)
    summary = dict(seed=seed, score=game['return_score'], status=game['status'],
        steps=game['steps_count'], utility=utility(game),
        observations_before=before_observations, observations_after=memory.observations_seen,
        costs=costs)
    return summary, dict(summary=summary, episode=game, decisions=decisions, memory_events=events)


def sum_costs(rows):
    result = {}
    for key in ('environment_counts', 'planning_counts', 'memory_counts'):
        result[key] = dict(sum((Counter(row[key]) for row in rows), Counter()))
    for key in ('decision_seconds', 'decision_cpu_seconds', 'memory_seconds',
                'memory_cpu_seconds', 'environment_seconds', 'environment_cpu_seconds',
                'cpu_seconds', 'wall_seconds'):
        result[key] = sum(row[key] for row in rows)
    return result


def phase_summary(games):
    return dict(games=len(games), utility_sum=sum(g['utility'] for g in games),
        mean_utility=sum(g['utility'] for g in games) / len(games),
        wins=sum(g['status'] == 'WON' for g in games),
        losses=sum(g['status'] == 'LOST' for g in games),
        cutoffs=sum(g['status'] == 'CUTOFF' for g in games),
        costs=sum_costs([g['costs'] for g in games]), game_summaries=games)


def warmup(leaf, lifecycle, emit, runtime=RUNTIME):
    planner = FrozenLeafPlanner(leaf, depth=1, build_dir=runtime)
    memories = {arm: SpawnMemory(method) for arm, method in METHODS.items()}
    games, observations, episode = [], 0, 0
    import_seconds = import_cpu_seconds = 0.
    while observations < WARMUP:
        summary, raw = play_game(planner, memories['DIRECT'],
            warmup_seed(lifecycle, episode), .1)
        clock, cpu = perf_counter(), process_time()
        ranks = [observed_rank(step) for step in raw['episode']['steps']]
        for arm, memory in memories.items():
            if arm == 'DIRECT':
                continue
            for rank in ranks:
                memory.observe(rank)
        import_seconds += perf_counter() - clock
        import_cpu_seconds += process_time() - cpu
        observations += len(ranks)
        games.append(summary)
        emit(dict(kind='WARMUP', lifecycle=lifecycle, parent=lifecycle % 4,
                  episode_index=episode, **raw))
        episode += 1
    return memories, dict(observations=observations, physical_games=len(games),
        physical_costs=sum_costs([g['costs'] for g in games]),
        summaries=games, planner_setup_counts=dict(planner.setup_counts),
        planner_setup_seconds=planner.setup_seconds,
        frozen_statistics_observations=WARMUP,
        memory_import_seconds=import_seconds, memory_import_cpu_seconds=import_cpu_seconds,
        memory_import_counts={arm: dict(m.counts) for arm, m in memories.items()})


def run_lifecycle(leaf, lifecycle, emit, runtime=RUNTIME):
    memories, source = warmup(leaf, lifecycle, emit, runtime)
    arms = {}
    for arm in ARMS:
        memory = memories[arm]
        planner = FrozenLeafPlanner(leaf, depth=1 if arm == 'DIRECT' else 2, build_dir=runtime)
        before = memory.to_payload()
        phases = {}
        for phase_index, (phase, p_four) in enumerate(PHASES):
            games = []
            for episode in range(EPISODES_PER_PHASE):
                summary, raw = play_game(planner, memory,
                    environment_seed(lifecycle, phase_index, episode), p_four)
                games.append(summary)
                emit(dict(kind='ONLINE', lifecycle=lifecycle, parent=lifecycle % 4,
                    arm=arm, phase=phase, episode_index=episode, environment_p_four=p_four, **raw))
            phases[phase] = phase_summary(games)
        arms[arm] = dict(total_utility=sum(p['utility_sum'] for p in phases.values()),
            phases=phases, costs=sum_costs([p['costs'] for p in phases.values()]),
            memory_before=before, memory_after=memory.to_payload(),
            planner_setup_counts=dict(planner.setup_counts),
            planner_setup_seconds=planner.setup_seconds, leaf_updates=leaf.updates)
    return dict(lifecycle=lifecycle, parent=lifecycle % 4, seed_base=seed_base(lifecycle),
                warmup=source, arms=arms)


def percentile(values, q):
    position = (len(values) - 1) * q
    lo, hi = int(position), min(int(position) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def paired_contrast(records, left, right, phase=None):
    def total(row, arm):
        return (row['arms'][arm]['total_utility'] if phase is None else
                row['arms'][arm]['phases'][phase]['utility_sum'])
    values = [total(row, left) - total(row, right) for row in records]
    rng = random.Random(BOOTSTRAP_SEED)
    groups = {parent: [value for value, row in zip(values, records) if row['parent'] == parent]
              for parent in sorted({row['parent'] for row in records})}
    samples = sorted(sum(sum(rng.choices(group, k=len(group))) / len(group)
        for group in groups.values()) / len(groups) for _ in range(BOOTSTRAP_DRAWS))
    parents = {str(parent): sum(group) / len(group) for parent, group in groups.items()}
    return dict(mean=sum(parents.values()) / len(parents), ci95=[percentile(samples, .025), percentile(samples, .975)],
        lifecycle_deltas=values, parent_mean_deltas=parents,
        improved=sum(value > 0 for value in values), equal=sum(value == 0 for value in values),
        worse=sum(value < 0 for value in values), interval_scope=INTERVAL_SCOPE,
        statistic='Sum of executed episode utility per whole memory lifecycle',
        resampling='Within each fixed parent, resample its complete memory lifecycles; equal parent weights')


def summarize(records):
    arms = {}
    for arm in ARMS:
        rows = [row['arms'][arm] for row in records]
        arms[arm] = dict(total_lifecycle_utility=sum(r['total_utility'] for r in rows),
            mean_lifecycle_utility=sum(r['total_utility'] for r in rows) / len(rows),
            phase_mean_episode_utility={phase: sum(r['phases'][phase]['utility_sum'] for r in rows)
                / sum(r['phases'][phase]['games'] for r in rows) for phase, _ in PHASES},
            wins=sum(p['wins'] for r in rows for p in r['phases'].values()),
            losses=sum(p['losses'] for r in rows for p in r['phases'].values()),
            cutoffs=sum(p['cutoffs'] for r in rows for p in r['phases'].values()),
            costs=sum_costs([r['costs'] for r in rows]),
            memory_creations=sum(r['memory_after']['counts']['module_creations']
                - r['memory_before']['counts']['module_creations'] for r in rows),
            memory_reactivations=sum(r['memory_after']['counts']['module_reactivations']
                - r['memory_before']['counts']['module_reactivations'] for r in rows))
    pairs = (('LIBRARY_H2', 'POOLED_H2'), ('LIBRARY_H2', 'FROZEN_H2'),
             ('FROZEN_H2', 'DIRECT'))
    contrasts = {f'{left}-{right}': dict(paired_contrast(records, left, right),
        phases={phase: paired_contrast(records, left, right, phase) for phase, _ in PHASES})
        for left, right in pairs}
    parent_means = {str(parent): {arm: sum(r['arms'][arm]['total_utility']
        for r in records if r['parent'] == parent) / sum(r['parent'] == parent for r in records)
        for arm in ARMS} for parent in sorted({r['parent'] for r in records})}
    return dict(arms=arms, paired_contrasts=contrasts, by_lifecycle=records,
        parent_means=parent_means,
        primary_result=('SUPPORTED_CONDITIONAL_ON_PARENTS' if
            all(contrasts[name]['ci95'][0] > 0 for name in
                ('LIBRARY_H2-POOLED_H2', 'LIBRARY_H2-FROZEN_H2')) else
            'NOT_SUPPORTED_CONDITIONAL_ON_PARENTS'),
        accounting=dict(physical_warmup_transitions=sum(r['warmup']['observations'] for r in records),
            physical_warmup_games=sum(r['warmup']['physical_games'] for r in records),
            warmup_costs=sum_costs([r['warmup']['physical_costs'] for r in records]),
            warmup_memory_import_seconds=sum(r['warmup']['memory_import_seconds'] for r in records),
            warmup_memory_import_cpu_seconds=sum(r['warmup']['memory_import_cpu_seconds'] for r in records),
            physical_online_transitions=sum(a['costs']['environment_counts']['sampled_transitions']
                for r in records for a in r['arms'].values()),
            physical_online_games=len(records) * len(ARMS) * len(PHASES) * EPISODES_PER_PHASE,
            new_value_parameter_updates=0))


def run_replication(emit, runtime=RUNTIME):
    started, cpu_started = perf_counter(), process_time()
    sources = load_sources()
    leaves, setups = {}, {}
    for source in sources['parents']:
        leaves[source['parent']], setups[str(source['parent'])] = load_leaf(source, runtime)
    records = []
    for lifecycle in LIFECYCLES:
        record = run_lifecycle(leaves[lifecycle % 4], lifecycle, emit, runtime)
        records.append(record)
        print(json.dumps(dict(event='memory_lifecycle_complete', lifecycle=lifecycle,
            parent=lifecycle % 4, utilities={a: record['arms'][a]['total_utility'] for a in ARMS})), flush=True)
    return dict(schema='acfqp.natural_model_revision.v281', status='DEVELOPMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', settings=dict(lifecycles=list(LIFECYCLES),
            parents=4, arms=ARMS, phases=PHASES, episodes_per_phase=EPISODES_PER_PHASE,
            max_steps=MAX_STEPS, warmup_minimum_actual_spawns=WARMUP, query=QUERY,
            bootstrap_draws=BOOTSTRAP_DRAWS, bootstrap_seed=BOOTSTRAP_SEED,
            bootstrap_resampling='WITHIN_PARENT_COMPLETE_MEMORY_LIFECYCLES_EQUAL_PARENT_WEIGHTS',
            interval_scope=INTERVAL_SCOPE, value_parameters='SAME_FROZEN_LEAF_ALL_ARMS',
            memory_rule='UNCHANGED_V115', warmup='Whole natural DIRECT games; all observed outcomes imported.'),
        source_provenance=sources, parent_setup_costs=setups,
        resident_source_and_leaf_weight_bytes=sum(s['resident_source_and_leaf_weight_bytes'] for s in setups.values()),
        summary=summarize(records), wall_seconds=perf_counter() - started,
        cpu_seconds=process_time() - cpu_started)
