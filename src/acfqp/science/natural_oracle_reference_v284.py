"""Known-law H2 full-game reference on the unchanged V281 value parents.

This diagnostic knows the spawn probability. It is neither a learned model
nor an upper bound on achievable game utility.
"""
from collections import Counter
import json
from pathlib import Path
import random
from time import perf_counter, process_time

from .controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from .controlled_predictive_regime_experience_v115 import run_episode
from .natural_model_revision_v281 import (load_leaf, delta, utility, sum_costs,
    phase_summary, percentile, QUERY, PHASES, MAX_STEPS, INTERVAL_SCOPE)

ARM = 'ORACLE_H2'
BASELINES = ('LIBRARY_H2', 'FROZEN_H2')
BOOTSTRAP_DRAWS, BOOTSTRAP_SEED = 20000, 28400001


def play_known_game(planner, seed, p_four):
    started, cpu_started = perf_counter(), process_time()
    before = dict(planner.counts)
    decisions, decision_seconds, decision_cpu_seconds = [], 0., 0.
    planner.spawn_probabilities = (1. - p_four, p_four)

    def act(board, step):
        nonlocal decision_seconds, decision_cpu_seconds
        clock, cpu = perf_counter(), process_time()
        choice = planner.choose(board, QUERY)
        decision_seconds += perf_counter() - clock
        decision_cpu_seconds += process_time() - cpu
        decisions.append(dict(action=choice['action'], value=choice['value'], p_four=p_four))
        return choice['action']

    game = run_episode(seed, act, p_four, MAX_STEPS)
    wall, cpu = perf_counter() - started, process_time() - cpu_started
    costs = dict(environment_counts=game['work'], planning_counts=delta(planner.counts, before),
        memory_counts={}, memory_seconds=0., memory_cpu_seconds=0.,
        decision_seconds=decision_seconds, decision_cpu_seconds=decision_cpu_seconds,
        environment_seconds=max(0., wall-decision_seconds),
        environment_cpu_seconds=max(0., cpu-decision_cpu_seconds), cpu_seconds=cpu, wall_seconds=wall)
    summary = dict(seed=seed, score=game['return_score'], status=game['status'],
        steps=game['steps_count'], utility=utility(game), costs=costs)
    return summary, dict(summary=summary, episode=game, decisions=decisions)


def paired_contrast(records, baseline, phase=None):
    def total(row, arm):
        return (row['arms'][arm]['total_utility'] if phase is None else
                row['arms'][arm]['phases'][phase]['utility_sum'])
    values = [total(row, ARM)-total(row, baseline) for row in records]
    groups = {parent: [value for row, value in zip(records, values) if row['parent'] == parent]
              for parent in sorted({row['parent'] for row in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    draws = sorted(sum(sum(rng.choices(group, k=len(group)))/len(group)
                        for group in groups.values())/len(groups) for _ in range(BOOTSTRAP_DRAWS))
    parents = {str(parent): sum(group)/len(group) for parent, group in groups.items()}
    return dict(mean=sum(parents.values())/len(parents),
        ci95=[percentile(draws, .025), percentile(draws, .975)], lifecycle_deltas=values,
        parent_mean_deltas=parents, improved=sum(x > 0 for x in values),
        equal=sum(x == 0 for x in values), worse=sum(x < 0 for x in values),
        interval_scope=INTERVAL_SCOPE, statistic='Whole-lifecycle executed utility sum',
        resampling='Within each fixed parent, resample complete paired lifecycles; equal parent weights')


def summarize(records):
    rows = [r['arms'][ARM] for r in records]
    oracle = dict(total_lifecycle_utility=sum(r['total_utility'] for r in rows),
        mean_lifecycle_utility=sum(r['total_utility'] for r in rows)/len(rows),
        phase_mean_episode_utility={phase: sum(r['phases'][phase]['utility_sum'] for r in rows)
            /sum(r['phases'][phase]['games'] for r in rows) for phase, _ in PHASES},
        wins=sum(p['wins'] for r in rows for p in r['phases'].values()),
        losses=sum(p['losses'] for r in rows for p in r['phases'].values()),
        cutoffs=sum(p['cutoffs'] for r in rows for p in r['phases'].values()),
        costs=sum_costs([r['costs'] for r in rows]))
    contrasts = {f'{ARM}-{baseline}': dict(paired_contrast(records, baseline),
        phases={phase: paired_contrast(records, baseline, phase) for phase, _ in PHASES})
        for baseline in BASELINES}
    return dict(arms={ARM: oracle}, paired_contrasts=contrasts, by_lifecycle=records,
        parent_means={str(parent): {arm: sum(r['arms'][arm]['total_utility']
            for r in records if r['parent'] == parent)/sum(r['parent'] == parent for r in records)
            for arm in (ARM,)+BASELINES} for parent in sorted({r['parent'] for r in records})})


def run_replication(source_summary, emit, runtime):
    started, cpu_started = perf_counter(), process_time()
    original = json.loads(Path(source_summary).read_text())
    if original['schema'] != 'acfqp.natural_model_revision.v281':
        raise ValueError('V284 reuses the immutable V281 natural-game evidence')
    sources = original['source_provenance']
    leaves, setups = {}, {}
    for source in sources['parents']:
        leaves[source['parent']], setups[str(source['parent'])] = load_leaf(source, runtime)
    records = []
    for previous in original['summary']['by_lifecycle']:
        life, parent = previous['lifecycle'], previous['parent']
        leaf = leaves[parent]
        planner = FrozenLeafPlanner(leaf, depth=2, build_dir=runtime)
        phases = {}
        for phase, p_four in PHASES:
            games = []
            for episode, prior_game in enumerate(previous['arms']['LIBRARY_H2']['phases'][phase]['game_summaries']):
                seed = prior_game['seed']
                if seed != previous['arms']['FROZEN_H2']['phases'][phase]['game_summaries'][episode]['seed']:
                    raise ValueError('V281 reference arms no longer have the same paired seed')
                summary, raw = play_known_game(planner, seed, p_four)
                games.append(summary)
                emit(dict(kind='ONLINE', lifecycle=life, parent=parent, arm=ARM,
                    phase=phase, episode_index=episode, environment_p_four=p_four, **raw))
            phases[phase] = phase_summary(games)
        arms = {ARM: dict(total_utility=sum(p['utility_sum'] for p in phases.values()),
            phases=phases, costs=sum_costs([p['costs'] for p in phases.values()]),
            planner_setup_counts=dict(planner.setup_counts), planner_setup_seconds=planner.setup_seconds,
            leaf_updates=leaf.updates)}
        for baseline in BASELINES:
            old = previous['arms'][baseline]
            arms[baseline] = dict(total_utility=old['total_utility'], phases={phase:
                dict(utility_sum=old['phases'][phase]['utility_sum'], games=old['phases'][phase]['games'])
                for phase, _ in PHASES}, costs=old['costs'],
                planner_setup_counts=old['planner_setup_counts'],
                planner_setup_seconds=old['planner_setup_seconds'])
        records.append(dict(lifecycle=life, parent=parent, arms=arms))
        print(json.dumps(dict(event='oracle_lifecycle_complete', lifecycle=life,
            parent=parent, total_utility=arms[ARM]['total_utility'])), flush=True)
    summary = summarize(records)
    summary['arms'].update({baseline: original['summary']['arms'][baseline] for baseline in BASELINES})
    inherited = original['summary']['accounting']
    return dict(schema='acfqp.natural_oracle_reference.v284', status='DIAGNOSTIC_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', source_summary=str(Path(source_summary).resolve()),
        settings=dict(arm=ARM, information='TRUE_PHASE_SPAWN_PROBABILITY_KNOWN_AT_EACH_DECISION',
            lifecycles=original['settings']['lifecycles'], parents=4, phases=PHASES,
            episodes_per_phase=original['settings']['episodes_per_phase'], max_steps=MAX_STEPS,
            query=QUERY, value_parameters='UNCHANGED_FOUR_FROZEN_V281_LEAVES',
            warmup='REUSED_BASELINE_COST_ONLY; NO_ORACLE_WARMUP_EXECUTION',
            bootstrap_draws=BOOTSTRAP_DRAWS, bootstrap_seed=BOOTSTRAP_SEED,
            interval_scope=INTERVAL_SCOPE), source_provenance=sources, parent_setup_costs=setups,
        resident_source_and_leaf_weight_bytes=sum(s['resident_source_and_leaf_weight_bytes'] for s in setups.values()),
        summary=summary, accounting=dict(new_source_observations=0, new_warmup_observations=0,
            new_warmup_games=0, new_value_parameter_updates=sum(leaf.updates for leaf in leaves.values()),
            new_online_games=sum(p['games'] for r in records for p in r['arms'][ARM]['phases'].values()),
            new_online_transitions=summary['arms'][ARM]['costs']['environment_counts']['sampled_transitions'],
            oracle_costs=summary['arms'][ARM]['costs'],
            inherited_source_training_transitions=sum(s['inherited_training_costs']['environment_counts']['sampled_transitions']
                for s in sources['parents']), inherited_dynamics_costs=sources['inherited_dynamics_costs'],
            inherited_shared_warmup_games=inherited['physical_warmup_games'],
            inherited_shared_warmup_transitions=inherited['physical_warmup_transitions'],
            inherited_shared_warmup_costs=inherited['warmup_costs'],
            inherited_warmup_memory_import_seconds=inherited['warmup_memory_import_seconds'],
            inherited_warmup_memory_import_cpu_seconds=inherited['warmup_memory_import_cpu_seconds']),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        limitations=['Known-law reference is not a learned model or a performance upper bound.',
            'Paired results are conditional on four reused frozen value parents.',
            'Oracle trajectories provide no feedback to the retained V281 learned arms.'])
