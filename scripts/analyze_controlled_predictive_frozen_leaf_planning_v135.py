"""Reconcile frozen-leaf planning, paired full games and enumeration costs."""
import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from scripts import analyze_controlled_predictive_contextual_ntuple_v134 as previous

LIVES, REPRESENTATIONS, MODES = tuple(range(4)), ('SINGLE', 'CAPACITY'), ('DIRECT', 'H2')
QUERIES = {q: old.QUERIES[q] for q in ('risk1', 'risk8')}
REPLICAS, MAX_STEPS, BASE, AGE = 16, 2000, 135*100000000, 524288


def mean(values):
    values = list(values)
    return None if not values or any(value is None for value in values) else sum(values)/len(values)


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def full_game_comparison(indexed, valid):
    """Pair identical seeds within each history; never replace censored returns."""
    methods, comparisons = {}, {}
    for representation in REPRESENTATIONS:
        methods[representation], comparisons[representation] = {}, {}
        for mode in MODES:
            methods[representation][mode] = {}
            for query in QUERIES:
                lives = []
                for life in LIVES:
                    keys = [(life, query, representation, mode, replica) for replica in range(REPLICAS)]
                    rows = [indexed[key] for key in keys if key in indexed]
                    complete = all(key in indexed and valid.get(key, False)
                        and indexed[key]['result']['status'] in ('WON', 'LOST') for key in keys)
                    lives.append(dict(life=life, complete=complete, games=len(rows),
                        statuses=dict(Counter(row['result']['status'] for row in rows)),
                        wins=sum(row['result']['status'] == 'WON' for row in rows),
                        means={name: mean(row['result'][name] for row in rows) if complete else None
                            for name in ('utility', 'score', 'steps')}))
                methods[representation][mode][query] = dict(lifecycles=lives,
                    complete=all(row['complete'] for row in lives),
                    means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
        for query in QUERIES:
            lives = []
            for life in LIVES:
                complete = all(methods[representation][mode][query]['lifecycles'][life]['complete'] for mode in MODES)
                item = dict(life=life, complete=complete)
                if complete:
                    deltas = [indexed[(life, query, representation, 'H2', replica)]['result']['utility']-
                        indexed[(life, query, representation, 'DIRECT', replica)]['result']['utility']
                        for replica in range(REPLICAS)]
                    item.update(mean=mean(deltas), replica_deltas=deltas)
                lives.append(item)
            comparisons[representation][query] = dict(lifecycles=lives,
                complete=all(row['complete'] for row in lives), mean=mean(row.get('mean') for row in lives),
                positive=sum(row.get('mean', 0) > 0 for row in lives),
                negative=sum(row.get('mean', 0) < 0 for row in lives),
                zero=sum(row.get('mean') == 0 for row in lives))
    return dict(methods=methods, comparisons=comparisons,
        complete=all(row['complete'] for modes in methods.values() for queries in modes.values() for row in queries.values()))


def planning_counts_valid(counts, mode, representation, steps, root_legal_actions):
    """Enumeration is model work, even though it consumes no random draws."""
    value = lambda key: counts.get(key, 0)
    outcomes = value('generated_spawn_outcomes')
    leaf_goals = value('leaf_terminal_goal_states')
    common = (value('choose_calls') == steps and value('root_swipe_calls') == 4*steps
        and value('root_legal_actions') == root_legal_actions
        and 0 <= value('root_goal_actions') <= root_legal_actions
        and value('learned_swipe_calls') == value('root_swipe_calls')+value('second_ply_swipe_calls')
        and value('line_table_lookups') == 4*value('learned_swipe_calls')
        and value('table_lookups') == 32*value('value_predictions')
        and value('learned_terminal_checks') == steps+value('leaf_choose_calls')+value('legal_swipes')
        and not any(amount for key, amount in counts.items() if key.endswith(('td_updates', 'model_spawn_samples'))))
    enum_keys = ('generated_spawn_outcomes', 'expanded_postspawn_states', 'leaf_choose_calls',
        'expectimax_probability_products', 'expectimax_probability_sums')
    if mode == 'H2':
        common &= (all(value(key) == outcomes for key in enum_keys)
            and value('spawn_rank1_outcomes') == value('spawn_rank2_outcomes')
            and value('spawn_rank1_outcomes')+value('spawn_rank2_outcomes') == outcomes
            and value('second_ply_swipe_calls') == 4*(outcomes-leaf_goals)
            and 2*(root_legal_actions-value('root_goal_actions')) <= outcomes <= 32*(root_legal_actions-value('root_goal_actions'))
            and value('value_predictions') == value('legal_swipes')-root_legal_actions-
                value('terminal_goal_bypasses')+value('root_goal_actions')+leaf_goals)
    else:
        common &= (all(value(key) == 0 for key in enum_keys+('spawn_rank1_outcomes', 'spawn_rank2_outcomes',
                'second_ply_swipe_calls', 'leaf_terminal_loss_states', 'leaf_terminal_goal_states'))
            and value('legal_swipes') == root_legal_actions
            and value('value_predictions') == root_legal_actions-value('root_goal_actions'))
    if representation == 'CAPACITY':
        common &= previous.context_counts_valid({'inner_'+key: amount for key, amount in counts.items()}, 'CAPACITY')
    return bool(common)


def expected_model_state(source, query, representation):
    reference = source['leaves'][query][representation]
    return previous.model_state(source, query, representation, reference['updates'])


def expected_spawn_probabilities(source):
    distribution = {rank: Fraction(numerator, denominator)
        for rank, numerator, denominator in source['rule']['spawn_distribution']}
    return [float(distribution[rank]) for rank in (1, 2)]


def work_ratios(direct, planned):
    """Report per-decision work as well as totals when game lengths differ."""
    ratio = lambda numerator, denominator: None if not denominator else numerator/denominator
    result = dict(steps_ratio=ratio(planned['steps'], direct['steps']))
    for metric, key in (('leaf_predictions', 'value_predictions'), ('learned_swipes', 'learned_swipe_calls')):
        left, right = direct['policy_counts'].get(key, 0), planned['policy_counts'].get(key, 0)
        result[metric] = dict(direct_total=left, planned_total=right, total_ratio=ratio(right, left),
            direct_per_decision=ratio(left, direct['steps']), planned_per_decision=ratio(right, planned['steps']),
            per_decision_ratio=ratio(right*direct['steps'], left*planned['steps']))
    result['decision_seconds'] = dict(direct_total=direct['decision_seconds'], planned_total=planned['decision_seconds'],
        total_ratio=ratio(planned['decision_seconds'], direct['decision_seconds']),
        direct_per_decision=ratio(direct['decision_seconds'], direct['steps']),
        planned_per_decision=ratio(planned['decision_seconds'], planned['steps']),
        per_decision_ratio=ratio(planned['decision_seconds']*direct['steps'], direct['decision_seconds']*planned['steps']))
    return result


def control_valid(row, source):
    result = row['result']; steps = result['steps']
    representation, mode = row['representation'], row['mode']
    state = expected_model_state(source, row['query'], representation)
    alternatives = row['action_values']
    checks = dict(control_trace=old.compact_valid(row) and row['seed'] == outer_seed(row['life'], row['replica'])
        and row['checkpoint'] == AGE and row['method'] == f'{representation}_{mode}'
        and result['utility'] == old.utility(result['score'], result['status'], row['query'])
        and len(row['chosen_values']) == len(alternatives) == steps
        and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'],
        evaluation_frozen=result['model_state_before'] == result['model_state_after'] == state,
        greedy_root_selection=True, planning_counts=True)
    if len(row['chosen_values']) != steps or len(alternatives) != steps:
        checks['greedy_root_selection'] = False; return checks
    for i, options in enumerate(alternatives):
        valid_options = (0 < len(options) <= 4 and set(options).issubset({'DOWN', 'LEFT', 'RIGHT', 'UP'})
            and all(all(math.isfinite(item[key]) for key in ('score', 'tail_value', 'value')) for item in options.values()))
        checks['greedy_root_selection'] &= valid_options
        if not valid_options: continue
        action = min(options, key=lambda name: (-options[name]['value'], name))
        checks['greedy_root_selection'] &= (row['actions'][i] == action
            and row['scores'][i] == options[action]['score'] and row['chosen_values'][i] == options[action]['value'])
    if result['status'] == 'WON':
        checks['greedy_root_selection'] &= row['chosen_values'][-1] == row['scores'][-1]/2048.+QUERIES[row['query']]['goal_bonus']
    checks['planning_counts'] = planning_counts_valid(result['policy_counts'], mode, representation,
        steps, sum(len(options) for options in alternatives))
    return {key: bool(value) for key, value in checks.items()}


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    run = json.loads((directory/'run.json').read_text())
    capsule = json.loads((directory/'source_capsule.json').read_text())
    sources = {source['life']: source for source in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES), policies={p: old.QUERIES[p] for p in old.POLICIES},
        queries=QUERIES, parents=previous.PARENTS, representations=list(REPRESENTATIONS), modes=list(MODES),
        depths=dict(DIRECT=1, H2=2), checkpoint=AGE, replicas=REPLICAS, max_steps=MAX_STEPS, workers=4,
        p_four=.1, planner_spawn_law='frozen_identified_distribution', version_base=BASE,
        physical_control_games=512, new_training_transitions=0)
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        lifecycle_roster=len(run['eval_lifecycles']) == 4 and {row['life'] for row in run['eval_lifecycles']} == set(LIVES),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        leaf_roster=True, frozen_source_references=True, source_immutable=True,
        model_loads=True, planner_roster=True, planner_counters=True, frozen_spawn_probabilities=True, control_roster=True)
    costs = dict(control=old.new_cost(), by_method={}, by_query={query: {} for query in QUERIES},
        model_accounting=[], decision_seconds=0., new_training_transitions=0)
    indexed, valid, grouped_counts = {}, {}, {}
    for source in sources.values():
        checks['leaf_roster'] &= set(source['leaves']) == set(QUERIES)
        for query, leaves in source['leaves'].items():
            checks['leaf_roster'] &= set(leaves) == set(REPRESENTATIONS)
            for representation, reference in leaves.items():
                metadata = json.loads(Path(reference['model_ref']+'.query.json').read_text())
                checks['frozen_source_references'] &= (reference['checkpoint'] == AGE
                    and reference['parameter_count'] == previous.parameter_count(representation)
                    and metadata['kind'] == 'PRIOR' and metadata['target_query'] == QUERIES[query]
                    and metadata['updates'] == reference['updates']
                    and metadata['offset'] == previous.expected_offset(source, query, representation)
                    and metadata['source_updates'] == source['models'][previous.PARENTS[query]]['updates'])
                if representation == 'CAPACITY':
                    checks['frozen_source_references'] &= (metadata['representation'] == representation
                        and metadata['context_spec'] == previous.CONTEXT_SPEC)
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]
        rows = list(old.read_rows(directory/lifecycle['control_trace']))
        keys = [(row['life'], row['query'], row['representation'], row['mode'], row['replica']) for row in rows]
        expected = {(life, query, representation, mode, replica) for query in QUERIES
            for representation in REPRESENTATIONS for mode in MODES for replica in range(REPLICAS)}
        checks['control_roster'] &= len(keys) == len(set(keys)) == 128 and set(keys) == expected
        for key, row in zip(keys, rows):
            row_checks = control_valid(row, source)
            for name, value in row_checks.items(): checks[name] = checks.get(name, True) and value
            indexed[key], valid[key] = row, all(row_checks.values())
            old.add_cost(costs['control'], row)
            method = row['method']; costs['by_method'].setdefault(method, old.new_cost())
            old.add_cost(costs['by_method'][method], row)
            costs['decision_seconds'] += row['result']['decision_seconds']
            query_cell = costs['by_query'][row['query']].setdefault(method, old.new_cost())
            old.add_cost(query_cell, row)
            for cell in (query_cell, costs['by_method'][method]):
                cell['decision_seconds'] = cell.get('decision_seconds', 0.)+row['result']['decision_seconds']
                cell['steps'] = cell.get('steps', 0)+row['result']['steps']
            group = key[:4]; grouped_counts.setdefault(group, Counter()).update(row['result']['policy_counts'])
        checks['planner_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query, qdata in lifecycle['queries'].items():
            parent_state = previous.model_state(source, query, 'PARENT', 0)
            checks['source_immutable'] &= qdata['parent_before'] == qdata['parent_after'] == parent_state
            checks['model_loads'] &= qdata['loads']['load_counts'].get('checkpoint_loads') == 1
            checks['planner_roster'] &= set(qdata['representations']) == set(REPRESENTATIONS)
            for representation, data in qdata['representations'].items():
                state = expected_model_state(source, query, representation)
                checks['source_immutable'] &= data['before'] == data['after'] == state
                checks['model_loads'] &= (data['reference'] == source['leaves'][query][representation]
                    and data['load_counts'].get('checkpoint_loads') == 1
                    and data['load_counts'].get('inner_checkpoint_loads') == 1
                    and data['setup_counts'].get('allocated_weight_parameters') == previous.parameter_count(representation))
                checks['planner_roster'] &= set(data['planners']) == set(MODES)
                for mode, planner in data['planners'].items():
                    checks['source_immutable'] &= planner['before'] == planner['after'] == state
                    checks['planner_counters'] &= Counter(planner['counts']) == grouped_counts[(life, query, representation, mode)]
                    checks['frozen_spawn_probabilities'] &= planner['spawn_probabilities'] == expected_spawn_probabilities(source)
                costs['model_accounting'].append(dict(life=life, query=query, representation=representation, **data))
            costs['model_accounting'].append(dict(phase='original_source_load', life=life, query=query, loads=qdata['loads']))
    checks['all_physical_games_counted_once'] = len(indexed) == costs['control']['games'] == 512
    policy_counts = costs['control']['policy_counts']
    costs['new_environment_samples'] = costs['control']['environment_counts'].get('sampled_transitions', 0)
    costs['new_model_samples'] = sum(value for key, value in policy_counts.items() if key.endswith('model_spawn_samples'))
    costs['generated_model_outcomes'] = policy_counts.get('generated_spawn_outcomes', 0)
    costs['planning_work_ratios'] = {representation: {query: work_ratios(
        cells[f'{representation}_DIRECT'], cells[f'{representation}_H2'])
        for query, cells in costs['by_query'].items()} for representation in REPRESENTATIONS}
    checks['no_training_or_stochastic_model_samples'] = costs['new_training_transitions'] == costs['new_model_samples'] == 0
    control = full_game_comparison(indexed, valid)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.frozen_leaf_planning.v135.analysis', complete=complete,
        primary_complete=complete and control['complete'], checks={key: bool(value) for key, value in checks.items()},
        control=control, costs=costs, inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Fixed final V134 leaves, paired seeds within each representation and all four histories. Recorded greedy root choices, immutable states, enumerated work and physical interactions are reconciled without resampling or weight replay. Censored games retain cost but suppress their affected full-return comparison.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
