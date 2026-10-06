"""Same observed histories, different spawn estimates and continuation readouts.

Reference scores use the true spawn probability and the same learned leaf.
They diagnose ranking, not optimal-policy regret or counterfactual game returns.
"""
from collections import Counter
import gzip
import json
from math import log
from pathlib import Path
import random
from time import perf_counter, process_time

from .natural_action_components_v283 import ActionComponents
from .natural_model_revision_v281 import load_leaf, QUERY, PHASES
from .controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .controlled_predictive_regime_experience_v115 import observed_rank

MODELS = ('FROZEN', 'POOLED', 'LIBRARY')
CARRIER = 'LIBRARY_H2'
PHASE_NAMES = tuple(name for name, _ in PHASES)
BOOTSTRAP_DRAWS, BOOTSTRAP_SEED = 20000, 28300001


def future_utilities(game):
    """After-current-reward suffix utility on the actual retained policy path."""
    value = 4. * (game['status'] == 'WON') - 4. * (game['status'] == 'LOST')
    suffixes = []
    for step in reversed(game['steps']):
        suffixes.append(value)
        value += step['score'] / 2048.
    return list(reversed(suffixes))


def proxy_loss(reference, choice):
    return reference['value'] - reference['action_values'][choice['action']]['value']


def ranking_metrics(payload, full, short, probabilities, true_p, factual_action,
                    future_utility, direct_choice):
    reference, short_reference = full['ORACLE_P'], short['ORACLE_P']
    metrics = {}
    ref_action = reference['action']
    components = payload['action_components']
    ref_slope = components[ref_action]['rank2_tail'] - components[ref_action]['rank1_tail']
    for model in MODELS:
        action = full[model]['action']
        slope = components[action]['rank2_tail'] - components[action]['rank1_tail']
        loss = proxy_loss(reference, full[model])
        metrics.update({f'{model}.p_mse': (probabilities[model] - true_p)**2,
            f'{model}.reference_score_loss': loss,
            f'{model}.reference_disagreement': float(action != ref_action),
            f'{model}.positive_reference_loss': float(loss > 0.),
            f'{model}.changed_from_frozen': float(action != full['FROZEN']['action']),
            f'{model}.short_reference_score_loss': proxy_loss(short_reference, short[model]),
            f'{model}.full_short_action_change': float(action != short[model]['action']),
            f'{model}.relative_slope_abs': abs(slope - ref_slope)})
    actions = reference['action_values']
    ordered = sorted(actions, key=lambda action: (-actions[action]['value'], action))
    metrics['DIRECT.reference_score_loss'] = proxy_loss(reference, direct_choice)
    metrics['DIRECT.reference_disagreement'] = float(direct_choice['action'] != ref_action)
    metrics['ORACLE_P.full_short_action_change'] = float(ref_action != short_reference['action'])
    metrics['multiple_legal_actions'] = float(len(ordered) > 1)
    if len(ordered) > 1:
        runner = ordered[1]
        runner_slope = components[runner]['rank2_tail'] - components[runner]['rank1_tail']
        metrics['oracle_margin_sum'] = actions[ref_action]['value'] - actions[runner]['value']
        metrics['oracle_competitor_slope_abs_sum'] = abs(ref_slope - runner_slope)
    else:
        metrics['oracle_margin_sum'] = metrics['oracle_competitor_slope_abs_sum'] = 0.
    short_action = short_reference['action']
    short_gap = (short_reference['action_values'][ref_action]['value']
                 - short_reference['action_values'][short_action]['value'])
    full_gap = reference['value'] - actions[short_action]['value']
    overrides = ref_action != short_action and short_gap < 0.
    metrics['strict_short_preference_overridden'] = float(overrides)
    metrics['overridden_short_gap_sum'] = short_gap if overrides else 0.
    metrics['overriding_continuation_gap_sum'] = full_gap - short_gap if overrides else 0.
    # This residual also includes changed second-action choices.
    predicted = actions[factual_action]['tail_value']
    direct_prediction = direct_choice['action_values'][factual_action]['tail_value']
    metrics['ORACLE_P.factual_future_bias'] = predicted - future_utility
    metrics['ORACLE_P.factual_future_mae'] = abs(predicted - future_utility)
    metrics['DIRECT.factual_future_bias'] = direct_prediction - future_utility
    metrics['DIRECT.factual_future_mae'] = abs(direct_prediction - future_utility)
    return metrics


def replay_game(raw, memories, engine, direct, emit):
    game, retained = raw['episode'], raw['decisions']
    if len(retained) != len(game['steps']):
        raise ValueError('carrier decisions and retained transitions differ')
    suffixes, sums, counts = future_utilities(game), Counter(), Counter()
    changed_rows = 0
    for index, (step, saved, suffix) in enumerate(zip(game['steps'], retained, suffixes)):
        probabilities = {model: memories[model].predict() for model in MODELS}
        library = memories['LIBRARY']
        if (probabilities['LIBRARY'] != saved['p_four']
                or library.module_id != saved['module_id']
                or library.observations_seen != saved['observations_before']):
            raise ValueError('LIBRARY does not reproduce the retained pre-observation prefix')
        payload = engine.components(step['board'])
        true_p = raw['environment_p_four']
        ps = dict(probabilities, ORACLE_P=true_p)
        full = {model: engine.compose(payload, p, 'full') for model, p in ps.items()}
        short = {model: engine.compose(payload, p, 'short') for model, p in ps.items()}
        chosen = full['LIBRARY']
        if (chosen['action'] != saved['action'] or chosen['value'] != saved['value']
                or chosen['action'] != step['action']
                or chosen['afterstate'] != step['afterstate']):
            raise ValueError('component replay does not exactly restore retained H2 action/value')
        direct_choice = direct.choose(step['board'], QUERY)
        metrics = ranking_metrics(payload, full, short, probabilities, true_p,
                                  saved['action'], suffix, direct_choice)
        # Outcome likelihood is scored after recommendations and before commit.
        rank = observed_rank(step)
        for model, probability in probabilities.items():
            metrics[f'{model}.observed_rank_logloss'] = -log(probability if rank == 2 else 1.-probability)
        sums.update(metrics)
        counts['restored_decisions'] += 1
        counts['tail_overrides'] += int(metrics['strict_short_preference_overridden'])
        for model in MODELS:
            for metric in ('reference_disagreement', 'positive_reference_loss',
                           'changed_from_frozen', 'full_short_action_change'):
                counts[f'{model}.{metric}'] += int(metrics[f'{model}.{metric}'])
        counts['ORACLE_P.full_short_action_change'] += int(metrics['ORACLE_P.full_short_action_change'])
        changed = len({result['action'] for result in (*full.values(), *short.values())}) > 1
        if changed:
            rows = {action: dict(full=full['ORACLE_P']['action_values'][action]['value'],
                short=short['ORACLE_P']['action_values'][action]['value'],
                slope=component['rank2_tail']-component['rank1_tail'])
                for action, component in payload['action_components'].items()}
            emit(dict(lifecycle=raw['lifecycle'], parent=raw['parent'], phase=raw['phase'],
                episode_index=raw['episode_index'], decision=index, board=step['board'],
                observations_before=library.observations_seen, p=ps,
                full_actions={m: x['action'] for m, x in full.items()},
                short_actions={m: x['action'] for m, x in short.items()},
                reference_loss={m: metrics[f'{m}.reference_score_loss'] for m in MODELS},
                action_scores=rows))
            changed_rows += 1
        # No shadow action generates feedback: each consumes the carrier's rank.
        for memory in memories.values():
            memory.observe(rank)
    if memories['LIBRARY'].observations_seen != raw['summary']['observations_after']:
        raise ValueError('terminal retained feedback was not committed exactly once')
    n = len(retained)
    return dict(lifecycle=raw['lifecycle'], parent=raw['parent'], phase=raw['phase'],
        episode_index=raw['episode_index'], seed=raw['summary']['seed'], decisions=n,
        changed_rows=changed_rows, counts=dict(counts),
        metrics={name: value/n for name, value in sums.items()})


def average_metrics(rows):
    keys = rows[0]['metrics']
    return {key: sum(row['metrics'][key] for row in rows)/len(rows) for key in keys}


def bootstrap_contrast(records, metric, left, right):
    deltas = [row['metrics'][f'{left}.{metric}'] - row['metrics'][f'{right}.{metric}']
              for row in records]
    groups = {parent: [value for value, row in zip(deltas, records) if row['parent'] == parent]
              for parent in sorted({r['parent'] for r in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    draws = sorted(sum(sum(rng.choices(values, k=len(values)))/len(values)
                       for values in groups.values())/len(groups) for _ in range(BOOTSTRAP_DRAWS))
    def quantile(q):
        x = (len(draws)-1)*q
        lo, hi = int(x), min(int(x)+1, len(draws)-1)
        return draws[lo] + (draws[hi]-draws[lo])*(x-lo)
    return dict(mean=sum(deltas)/len(deltas), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas=deltas, improved_equal_worse=[sum(x<0 for x in deltas),
            sum(x==0 for x in deltas), sum(x>0 for x in deltas)],
        parent_mean_deltas={str(p): sum(v)/len(v) for p, v in groups.items()})


def summarize_games(games):
    lifecycles = []
    for life in sorted({game['lifecycle'] for game in games}):
        rows = [game for game in games if game['lifecycle'] == life]
        phases = {phase: dict(games=len(items), decisions=sum(g['decisions'] for g in items),
                             metrics=average_metrics(items))
                  for phase in PHASE_NAMES
                  for items in [[g for g in rows if g['phase'] == phase]]}
        lifecycles.append(dict(lifecycle=life, parent=rows[0]['parent'], phases=phases,
            metrics=average_metrics(list(phases.values()))))
    contrasts = {}
    for metric in ('p_mse', 'reference_score_loss'):
        for right in ('POOLED', 'FROZEN'):
            name = f'LIBRARY_minus_{right}.{metric}'
            contrasts[name] = dict(bootstrap_contrast(lifecycles, metric, 'LIBRARY', right),
                phases={phase: bootstrap_contrast([
                    dict(parent=r['parent'], metrics=r['phases'][phase]['metrics']) for r in lifecycles],
                    metric, 'LIBRARY', right) for phase in PHASE_NAMES})
    return dict(metrics=average_metrics(lifecycles),
        phases={phase: average_metrics([r['phases'][phase] for r in lifecycles]) for phase in PHASE_NAMES},
        counts=dict(sum((Counter(g['counts']) for g in games), Counter())),
        phase_counts={phase: dict(sum((Counter(g['counts']) for g in games if g['phase']==phase), Counter()))
                      for phase in PHASE_NAMES},
        paired_diagnostic_contrasts=contrasts, by_lifecycle=lifecycles, games=games)


def run_replay(input_path, source_summary, output):
    started, cpu_started = perf_counter(), process_time()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    trace_path, summary_path = output/'changed_actions.jsonl.gz', output/'summary.json'
    if trace_path.exists() or summary_path.exists():
        raise FileExistsError('V283 diagnostic receipts already exist')
    original = json.loads(Path(source_summary).read_text())
    if original['schema'] != 'acfqp.natural_model_revision.v281':
        raise ValueError('V283 requires retained V281 natural-game evidence')
    runtime = output/'runtime'
    engines, directs, source_setups = {}, {}, {}
    for source in original['source_provenance']['parents']:
        parent = source['parent']
        leaf, setup = load_leaf(source, runtime)
        engines[parent], directs[parent] = ActionComponents(leaf, runtime), FrozenLeafPlanner(leaf, 1, runtime)
        source_setups[str(parent)] = setup
    memories, games, read_rows, read_transitions, warmup_rows = {}, [], 0, 0, 0
    with gzip.open(trace_path, 'xt', encoding='utf-8') as out:
        def emit(row):
            out.write(json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n')
        with gzip.open(input_path, 'rt', encoding='utf-8') as handle:
            for line in handle:
                row = json.loads(line)
                read_rows += 1
                read_transitions += row['episode']['steps_count']
                life, parent = row['lifecycle'], row['parent']
                if row['kind'] == 'WARMUP':
                    if life not in memories:
                        memories[life] = {model: SpawnMemory(model) for model in MODELS}
                    for step in row['episode']['steps']:
                        rank = observed_rank(step)
                        for memory in memories[life].values():
                            memory.observe(rank)
                    warmup_rows += row['episode']['steps_count']
                elif row['arm'] == CARRIER:
                    games.append(replay_game(row, memories[life], engines[parent], directs[parent], emit))
                    if row['phase'] == 'A_prime' and row['episode_index'] == 7:
                        print(json.dumps(dict(event='replayed_lifecycle', lifecycle=life,
                            restored_decisions=sum(g['decisions'] for g in games if g['lifecycle']==life))), flush=True)
    expected = {(life, phase, episode) for life in original['settings']['lifecycles']
                for phase in PHASE_NAMES for episode in range(8)}
    if (set((g['lifecycle'], g['phase'], g['episode_index']) for g in games) != expected
            or len(games) != len(expected)
            or sum(g['decisions'] for g in games) !=
                original['summary']['arms'][CARRIER]['costs']['environment_counts']['sampled_transitions']):
        raise ValueError('the full unfiltered LIBRARY carrier cohort was not restored')
    for life, state in memories.items():
        expected_memory = original['summary']['by_lifecycle'][life]['arms'][CARRIER]['memory_after']
        if state['LIBRARY'].to_payload() != expected_memory:
            raise ValueError('the full retained LIBRARY final memory differs')
    result = dict(schema='acfqp.natural_action_value.v283', status='DIAGNOSTIC_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', input=str(Path(input_path).resolve()),
        source_summary=str(Path(source_summary).resolve()),
        settings=dict(carrier=CARRIER, shadow_memories=MODELS, reference='H2_TRUE_P_SAME_LEARNED_LEAF',
            short_tail='SECOND_ACTION_RESELECTED_WITH_NONTERMINAL_TD_TAIL_ZERO',
            aggregation='DECISIONS_PER_GAME_THEN_EQUAL_GAMES_PHASES_LIFECYCLES',
            bootstrap_draws=BOOTSTRAP_DRAWS, bootstrap_seed=BOOTSTRAP_SEED,
            bootstrap_scope='WITHIN_FOUR_FIXED_PARENTS_COMPLETE_PAIRED_LIFECYCLES'),
        summary=summarize_games(games),
        accounting=dict(new_source_observations=0, new_target_observations=0, new_value_updates=0,
            read_games=read_rows, read_retained_transitions=read_transitions,
            shadow_warmup_observations=warmup_rows, replayed_games=len(games),
            restored_decisions=sum(g['decisions'] for g in games), changed_action_rows=sum(g['changed_rows'] for g in games),
            component_counts=dict(sum((engine.counts for engine in engines.values()), Counter())),
            direct_counts=dict(sum((planner.counts for planner in directs.values()), Counter())),
            shadow_memory_counts={model: dict(sum((state[model].counts for state in memories.values()), Counter()))
                                  for model in MODELS},
            cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started),
        setup=dict(parent_loads=source_setups,
            components={str(p): dict(counts=dict(e.setup_counts), seconds=e.setup_seconds) for p,e in engines.items()},
            direct={str(p): dict(counts=dict(d.setup_counts), seconds=d.setup_seconds) for p,d in directs.items()}),
        retained_storage=dict(input_gzip_bytes=Path(input_path).stat().st_size,
            changed_actions_gzip_bytes=trace_path.stat().st_size),
        limitations=['Reference score loss uses the same learned leaf, not optimal-policy regret.',
            'Short-tail replans second actions; its residual is not a pure additive tail effect.',
            'Factual suffix errors include subsequent LIBRARY control and random outcomes.',
            'Diagnostics are conditional on retained LIBRARY states and four frozen value parents.'])
    result['accounting']['timing_scope'] = 'Input reads, replay, scoring, compressed rows and bootstrap; final summary serialization excluded'
    summary_path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result
