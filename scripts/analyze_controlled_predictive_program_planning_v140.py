"""Independently reconcile conditional-program planning and paired full games."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from scripts import analyze_controlled_predictive_frozen_leaf_planning_v135 as planning
from scripts import analyze_controlled_predictive_bellman_consequences_v136 as teacher_analysis
from acfqp.domains import standard_2048 as ground

LIVES, AGES, REPLICAS = tuple(range(4)), (1, 8, 64), 8
BASE, MAX_STEPS = 140*100000000, 2000
QUERIES = {q: old.QUERIES[q] for q in ('risk1', 'risk8')}
METHODS = ('H2', 'DIRECT64', 'LEARNED1', 'RANDOM1', 'LEARNED8', 'RANDOM8', 'LEARNED64', 'RANDOM64')
COMPARISONS = {**{f'LEARNED{age}-RANDOM{age}': (f'LEARNED{age}', f'RANDOM{age}') for age in AGES},
    'LEARNED64-H2': ('LEARNED64', 'H2'), 'LEARNED64-DIRECT64': ('LEARNED64', 'DIRECT64')}
mean = planning.mean


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def model_seed(life, replica, step):
    return BASE+80000000+life*1000000+replica*10000+step


def full_game_comparison(indexed, valid):
    """Preserve every roster cell; censored or missing games suppress returns."""
    methods, comparisons = {}, {}
    for method in METHODS:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                keys = [(life, query, method, replica) for replica in range(REPLICAS)]
                rows = [indexed[key] for key in keys if key in indexed]
                complete = all(key in indexed and valid.get(key, False)
                    and indexed[key]['result']['status'] in ('WON', 'LOST') for key in keys)
                lives.append(dict(life=life, complete=complete, games=len(rows),
                    statuses=dict(Counter(row['result']['status'] for row in rows)),
                    wins=sum(row['result']['status'] == 'WON' for row in rows),
                    means={name: mean(row['result'][name] for row in rows) if complete else None
                        for name in ('utility', 'score', 'steps')}))
            methods[method][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
    for name, (left, right) in COMPARISONS.items():
        comparisons[name] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                complete = all(methods[method][query]['lifecycles'][life]['complete'] for method in (left, right))
                item = dict(life=life, complete=complete)
                if complete:
                    deltas = [indexed[(life, query, left, replica)]['result']['utility']-
                        indexed[(life, query, right, replica)]['result']['utility'] for replica in range(REPLICAS)]
                    item.update(mean=mean(deltas), replica_deltas=deltas)
                lives.append(item)
            comparisons[name][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                mean=mean(row.get('mean') for row in lives), positive=sum(row.get('mean', 0) > 0 for row in lives),
                negative=sum(row.get('mean', 0) < 0 for row in lives), zero=sum(row.get('mean') == 0 for row in lives))
    return dict(methods=methods, comparisons=comparisons,
        complete=all(cell['complete'] for methods_by_query in methods.values() for cell in methods_by_query.values()))


def training_example(window):
    """Derive the actual second decision without evaluating a learned policy."""
    after, score, changed = ground.swipe_board_v1(tuple(window['root']), ground.Swipe2048Action(window['actions'][0]))
    spawn = window['spawns'][0]
    if not changed or after[spawn['cell']] != 0 or max(after) >= 11:
        raise ValueError('retained first action is not a legal nonterminal transition')
    board = list(after); board[spawn['cell']] = spawn['rank']
    if score != window['expected']['scores'][0]:
        raise ValueError('retained first reward disagrees with the source transition')
    return board, window['actions'][1]


def add_checks(checks, values):
    for name, value in values.items():
        checks[name] = checks.get(name, True) and bool(value)


def predicates(board):
    empty = board.count(0); largest = max(board)
    neighbors = [(r*4+c, r*4+c+1) for r in range(4) for c in range(3)]
    neighbors += [(r*4+c, (r+1)*4+c) for r in range(3) for c in range(4)]
    equal = sum(board[a] != 0 and board[a] == board[b] for a, b in neighbors)
    boundaries = ((0, 1, 2, 3), (12, 13, 14, 15), (0, 4, 8, 12), (3, 7, 11, 15))
    return [empty <= n for n in (2, 4, 8)]+[equal <= n for n in (0, 2, 4)]+[
        largest > 0 and board[cell] == largest for cell in (0, 3, 12, 15)]+[
        largest > 0 and any(board[cell] == largest for cell in edge) for edge in boundaries]


def tree_checks(learned, random, examples, seed):
    trees, metadata, work = learned['trees'], learned['metadata'], learned['work']
    actions = ('DOWN', 'LEFT', 'RIGHT', 'UP')
    checks = dict(tree_shapes=len(trees) == len(random['trees']) == 4,
        random_preserves_structure=True, fitted_node_histograms=True, learned_action_orders=True,
        training_mistakes=True, tree_training_accounting=True, random_accounting=True)
    counts = [[[0]*4 for _ in range(7)] for _ in range(4)]
    mistakes = [0]*4
    for example in examples:
        previous = actions.index(example['previous_action']); action = actions.index(example['action'])
        tree = trees[previous]; features = predicates(example['board']); node = 0
        while True:
            counts[previous][node][action] += 1
            predicate = tree[node][0]
            if predicate < 0:
                mistakes[previous] += tree[node][1] != action
                break
            node = 2*node+1+int(features[predicate])
    active, leaves, splits, visits, candidate_nodes, candidate_visits = 0, 0, 0, 0, 0, 0
    for tree_index, tree in enumerate(trees):
        checks['tree_shapes'] &= len(tree) == len(random['trees'][tree_index]) == 7
        reachable = [0]
        while reachable:
            index = reachable.pop(); node = tree[index]; histogram = counts[tree_index][index]
            n = sum(histogram); active += 1; visits += n
            checks['learned_action_orders'] &= node[1:] == sorted(range(4), key=lambda a: (-histogram[a], a))
            depth = 0 if index == 0 else 1 if index <= 2 else 2
            if depth < 2 and n >= 16 and n > max(histogram):
                candidate_nodes += 1; candidate_visits += n
            if node[0] >= 0:
                splits += 1
                children = [2*index+1, 2*index+2]
                checks['tree_shapes'] &= depth < 2 and node[0] < 14
                checks['training_mistakes'] &= min(sum(counts[tree_index][child]) for child in children) >= 8
                checks['training_mistakes'] &= sum(max(counts[tree_index][child]) for child in children) > max(histogram)
                reachable.extend(children)
            else:
                leaves += 1
        for index, node in enumerate(tree):
            random_node = random['trees'][tree_index][index]
            checks['tree_shapes'] &= len(node) == 5 and sorted(node[1:]) == list(range(4))
            checks['random_preserves_structure'] &= random_node[0] == node[0] and sorted(random_node[1:]) == list(range(4))
    checks['fitted_node_histograms'] &= (metadata['node_action_counts'] == counts
        and metadata['node_sample_counts'] == [[sum(node) for node in tree] for tree in counts]
        and metadata['examples'] == len(examples)
        and metadata['examples_by_previous_action'] == [sum(tree[0]) for tree in counts])
    checks['training_mistakes'] &= (metadata['fit_classification_mistakes'] == sum(mistakes)
        and metadata['tree_fit_mistakes'] == mistakes and metadata['split_nodes'] == splits
        and metadata['leaf_nodes'] == leaves and metadata['max_depth'] == 2 and metadata['min_child'] == 8)
    expected = dict(fit_calls=1, training_examples=len(examples), feature_calls=len(examples),
        feature_input_cells=16*len(examples), feature_neighbor_pairs=24*len(examples),
        feature_predicate_values=14*len(examples), training_label_encodings=len(examples),
        active_nodes=active, node_sample_visits=visits, node_histogram_updates=visits,
        action_rankings=active, ranked_action_entries=4*active, active_leaves=leaves,
        split_candidates=14*candidate_nodes, split_predicate_reads=14*candidate_visits,
        split_histogram_updates=14*candidate_visits, chosen_splits=splits,
        stored_tree_nodes=28, stored_node_integers=140)
    checks['tree_training_accounting'] &= all(work.get(key, 0) == value for key, value in expected.items())
    random_meta = dict(random['metadata']); random_meta.pop('random_seed', None); random_meta['randomized'] = False
    checks['random_preserves_structure'] &= not metadata['randomized'] and random['metadata']['randomized'] and random_meta == metadata
    checks['random_accounting'] &= (random['metadata']['random_seed'] == seed and random['work'] == dict(
        randomize_calls=1, copied_tree_nodes=28, copied_node_integers=140, random_draws=84, random_action_orders=28))
    return checks


def expected_settings():
    return dict(lifecycles=list(LIVES), ages=list(AGES), episodes=64, replicas=REPLICAS, workers=4,
        queries=QUERIES, methods=list(METHODS), representation='SINGLE', teacher_query='risk1', p_four=.1,
        max_steps=MAX_STEPS, physical_games=512, version_base=BASE, program_actions_after_root=3,
        tree_depth=2, min_child_examples=8,
        model_budget='root4 plus8 per empty cell of each legal non-goal root afterstate',
        planner_spawn_law='frozen_identified_distribution', initial_previous_action='DOWN')


def program_counts_valid(counts, options, direct):
    n = lambda key: counts.get(key, 0)
    roots = len(options); goals = sum(max(row['afterstate']) >= 11 for row in options.values())
    checks = dict(model_budget=True, program_costs=True, simulation_costs=True, no_evaluation_fitting=True)
    for row in options.values():
        cap = 0 if direct or max(row['afterstate']) >= 11 else 8*row['afterstate'].count(0)
        checks['model_budget'] &= (row['budget'] == cap and 0 <= row['used'] <= cap
            and row['rollouts'] == (max(1, cap//16) if cap else 0))
    checks['model_budget'] &= (n('model_swipe_budget') == 4+sum(row['budget'] for row in options.values())
        and n('model_swipes_used') == 4+sum(row['used'] for row in options.values())
        and n('model_swipes_used') == n('learned_swipe_calls') == n('program_swipe_calls')+n('bootstrap_swipe_calls')
        and n('root_swipe_calls') == 4 and n('rollouts_started') == sum(row['rollouts'] for row in options.values()))
    trees, swipes, rollouts, samples = n('tree_calls'), n('program_swipe_calls'), n('rollouts_started'), n('model_sampled_transitions')
    checks['program_costs'] &= (n('choose_calls') == 1 and n('root_legal_actions') == roots
        and n('root_goal_actions') == (0 if direct else goals)
        and n('line_lookup_calls') == n('line_hits') == n('composition_line_gathers') == n('composition_line_scatters') == 4*swipes
        and n('line_misses') == 0 and n('line_bound_output_cells') == n('line_zero_mask_rank_reads') == 16*swipes
        and n('line_guard_rank_reads') == 2*n('line_guard_checks')
        and n('line_table_lookups') == 4*n('bootstrap_swipe_calls')
        and n('table_lookups') == 32*n('value_predictions')
        and n('feature_board_reads') == 16*trees and n('feature_neighbor_comparisons') == 24*trees
        and n('feature_predicate_values') == 14*trees and n('tree_order_reads') == 4*trees
        and 0 <= n('tree_predicate_checks') <= 2*trees
        and n('learned_terminal_checks') == 1+n('legal_swipes')+n('leaf_choose_calls'))
    checks['simulation_costs'] &= (samples == rollouts+n('rollout_actions')-n('rollout_terminal_goal_states')
        and n('simulation_uniform_draws') == 2*samples and n('simulation_rng_initializations') == rollouts
        and n('spawn_empty_cell_reads') == 16*samples and n('spawn_board_writes') == samples
        and n('rollout_reward_additions') == n('rollout_actions') and n('rollout_mean_additions') == rollouts)
    if direct:
        checks['program_costs'] &= (n('direct_choose_calls') == trees == 1 and swipes == 4
            and n('value_predictions') == n('leaf_choose_calls') == n('bootstrap_swipe_calls') == 0)
        checks['simulation_costs'] &= samples == rollouts == n('rollout_actions') == 0
    else:
        checks['program_costs'] &= (n('direct_choose_calls') == 0
            and trees == n('rollout_actions')+n('rollout_terminal_loss_states')
            and trees <= 3*rollouts and 4+trees <= swipes <= 4+4*trees
            and n('bootstrap_swipe_calls') == 4*n('leaf_choose_calls')
            and n('leaf_choose_calls')+n('rollout_terminal_loss_states')+n('rollout_terminal_goal_states') == rollouts
            and n('root_empty_cell_reads') == 16*(roots-goals))
    checks['no_evaluation_fitting'] &= not any(value for key, value in counts.items()
        if key.endswith('updates') or key.startswith(('compiled_', 'fit_', 'observations')))
    return checks


def control_checks(row, payload):
    result, choices = row['result'], row['choices']; method = row['method']; direct = method == 'DIRECT64'
    checks = dict(control_trace=old.compact_valid(row) and row['seed'] == outer_seed(row['life'], row['replica'])
        and result['utility'] == old.utility(result['score'], result['status'], row['query'])
        and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'],
        decision_roster=len(choices) == result['steps'], decision_seeds=True,
        root_selection=True, recorded_successor_chain=True, step_cost_totals=True)
    board, previous, work = list(row['initial_board']), 'DOWN', Counter()
    actions = ('DOWN', 'LEFT', 'RIGHT', 'UP')
    for step, choice in enumerate(choices):
        options = choice['action_values']; work.update(choice['work'])
        checks['decision_seeds'] &= choice['previous_action'] == previous and choice['simulation_seed'] == (
            None if method == 'H2' else model_seed(row['life'], row['replica'], step))
        expected_kind = 'action_priority' if direct else 'estimated_return'
        checks['root_selection'] &= (choice['value_kind'] == expected_kind and choice['status'] == 'ACTIVE'
            and 0 < len(options) <= 4 and set(options) <= set(actions)
            and all(len(item['afterstate']) == 16 and all(math.isfinite(item[key])
                for key in ('score', 'tail_value', 'value')) for item in options.values()))
        selected = min(options, key=lambda action: (-options[action]['value'], action))
        checks['root_selection'] &= (choice['action'] == row['actions'][step] == selected
            and choice['value'] == options[selected]['value'] and row['scores'][step] == options[selected]['score'])
        if direct:
            tree = payload['trees'][actions.index(previous)]; node = 0; features = predicates(board)
            while tree[node][0] >= 0:
                node = 2*node+1+int(features[tree[node][0]])
            order = [actions[index] for index in tree[node][1:]]
            checks['root_selection'] &= all(item['value'] == 4-order.index(action) for action, item in options.items())
        else:
            for item in options.values():
                checks['root_selection'] &= item['value'] == item['score']/2048.+item['tail_value']
                if max(item['afterstate']) >= 11:
                    checks['root_selection'] &= item['tail_value'] == QUERIES[row['query']]['goal_bonus']
        board = list(options[selected]['afterstate']); cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        checks['recorded_successor_chain'] &= board[cell] == 0
        board[cell] = rank; previous = selected
        if method == 'H2':
            checks['h2_accounting'] = checks.get('h2_accounting', True) and planning.planning_counts_valid(
                choice['work'], 'H2', 'SINGLE', 1, len(options))
        else:
            add_checks(checks, program_counts_valid(choice['work'], options, direct))
    checks['recorded_successor_chain'] &= board == row['final_board']
    checks['step_cost_totals'] &= work == Counter(result['policy_counts'])
    return checks


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_training.json'))
    sources = {source['life']: source for source in capsule['snapshots']}
    checks = dict(frozen_settings=run['settings'] == expected_settings(),
        source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[key]) == 4 and {row['life'] for row in run[key]} == set(LIVES)
            for key in ('lifecycles', 'eval_lifecycles')),
        all_training_frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings', 'lifecycles', 'inherited_costs')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        source_references=True, matched_training_examples=True, episode_roster=True,
        rule_frozen=True, training_replay_accounting=True, snapshot_roster=True, snapshot_metadata=True,
        evaluation_roster=True, query_roster=True, planner_roster=True, teacher_frozen=True,
        model_loads=True, planner_references=True, planner_counts=True, planner_setup=True,
        program_payloads_frozen=True, identified_spawn_law=True)
    costs = dict(source_windows_read=0, analysis_replay_swipes=0, training_replay_work=Counter(),
        training_fit_work=Counter(), training_random_work=Counter(), training_seconds=0., training_bytes=0,
        control=old.new_cost(), by_method={}, by_query={q: {} for q in QUERIES}, model_accounting=[],
        decision_seconds=0., new_training_transitions=0)
    trained, payloads = {}, {}
    for lifecycle in run['lifecycles']:
        life = lifecycle['life']; source = sources[life]; trained[life] = lifecycle
        checks['source_references'] &= lifecycle['source_trace'] == source['training_windows']
        checks['episode_roster'] &= lifecycle['episodes'] == source['episodes'] and len(lifecycle['episodes']) == 64
        checks['rule_frozen'] &= lifecycle['rule_before'] == lifecycle['rule_after'] == source['rule']
        trace = iter(old.read_rows(directory/lifecycle['examples_trace'])); examples = []; prefixes = {}
        episode_windows = Counter()
        for window in old.read_rows(source['training_windows']):
            board, action = training_example(window); example = dict(board=board, previous_action=window['actions'][0], action=action)
            record = next(trace, None); episode = window['episode']; meta = source['episodes'][episode]
            expected = dict(life=life, episode=episode, seed=window['seed'], start_step=window['start_step'], **example)
            checks['matched_training_examples'] &= record == expected and window['life'] == life and window['seed'] == meta['seed']
            checks['episode_roster'] &= window['start_step'] == 32*episode_windows[episode]
            episode_windows[episode] += 1; examples.append(example)
            if episode+1 in AGES: prefixes[episode+1] = len(examples)
        checks['matched_training_examples'] &= next(trace, None) is None and lifecycle['examples'] == len(examples)
        checks['episode_roster'] &= set(episode_windows) == set(range(64)) and all(
            episode_windows[index] == episode['windows'] for index, episode in enumerate(source['episodes']))
        replay = lifecycle['replay_work']; n = len(examples)
        checks['training_replay_accounting'] &= (replay.get('learned_swipe_calls') == n
            and replay.get('recorded_spawn_patches') == n)
        costs['source_windows_read'] += n; costs['analysis_replay_swipes'] += n
        costs['training_replay_work'].update(replay); costs['training_seconds'] += lifecycle['seconds']
        checks['snapshot_roster'] &= [row['age'] for row in lifecycle['snapshots']] == list(AGES)
        for snapshot in lifecycle['snapshots']:
            age = snapshot['age']; seed = BASE+70000000+life*100000+age
            learned, random = (read(snapshot[kind]['path']) for kind in ('LEARNED', 'RANDOM'))
            checks['snapshot_metadata'] &= snapshot['examples'] == prefixes[age] and snapshot['random_seed'] == seed
            add_checks(checks, tree_checks(learned, random, examples[:prefixes[age]], seed))
            for kind, payload in (('LEARNED', learned), ('RANDOM', random)):
                item = snapshot[kind]; payloads[(life, kind, age)] = payload
                checks['snapshot_metadata'] &= (item['metadata'] == payload['metadata'] and item['work'] == payload['work']
                    and item['bytes'] == (directory/item['path']).stat().st_size)
                costs['training_bytes'] += item['bytes']
            costs['training_fit_work'].update(learned['work']); costs['training_random_work'].update(random['work'])
    indexed, valid, grouped = {}, {}, {}
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]; keys = []
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key = row['life'], row['query'], row['method'], row['replica']; keys.append(key)
            method, query = row['method'], row['query']
            kind = 'RANDOM' if method.startswith('RANDOM') else 'LEARNED'
            age = None if method == 'H2' else int(method.removeprefix('LEARNED').removeprefix('RANDOM').removeprefix('DIRECT'))
            payload = None if age is None else payloads[(life, kind, age)]
            row_checks = control_checks(row, payload); add_checks(checks, row_checks)
            indexed[key] = dict(result=row['result']); valid[key] = all(row_checks.values())
            old.add_cost(costs['control'], row); costs['decision_seconds'] += row['result']['decision_seconds']
            for cell in (costs['by_method'].setdefault(method, old.new_cost()), costs['by_query'][query].setdefault(method, old.new_cost())):
                old.add_cost(cell, row)
                cell['steps'] = cell.get('steps', 0)+row['result']['steps']
                cell['decision_seconds'] = cell.get('decision_seconds', 0.)+row['result']['decision_seconds']
            grouped.setdefault((life, query, method), Counter()).update(row['result']['policy_counts'])
        expected = {(life, query, method, replica) for query in QUERIES for method in METHODS for replica in range(REPLICAS)}
        checks['evaluation_roster'] &= len(keys) == len(set(keys)) == 128 and set(keys) == expected
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query, qdata in lifecycle['queries'].items():
            state = planning.expected_model_state(source, query, 'SINGLE')
            parent_state = planning.previous.model_state(source, query, 'PARENT', 0)
            checks['teacher_frozen'] &= (qdata['parent_before'] == qdata['parent_after'] == parent_state
                and qdata['leaf_before'] == qdata['leaf_after'] == state)
            checks['model_loads'] &= teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['planner_roster'] &= set(qdata['planners']) == set(METHODS)
            costs['model_accounting'].append(dict(life=life, query=query, loads=qdata['loads']))
            for method, planner in qdata['planners'].items():
                checks['teacher_frozen'] &= planner['before'] == planner['after'] == state
                checks['identified_spawn_law'] &= planner['spawn_probabilities'] == planning.expected_spawn_probabilities(source)
                checks['planner_counts'] &= Counter(planner['counts']) == grouped[(life, query, method)]
                checks['program_payloads_frozen'] &= planner['policy_payload_unchanged'] and planner['factored_payload_unchanged']
                reference = None
                if method != 'H2':
                    kind = 'RANDOM' if method.startswith('RANDOM') else 'LEARNED'
                    age = int(method.removeprefix('LEARNED').removeprefix('RANDOM').removeprefix('DIRECT'))
                    reference = next(row for row in trained[life]['snapshots'] if row['age'] == age)[kind]['path']
                    n = source['factored_summary']['num_programs']; setup = planner['setup_counts']
                    checks['planner_setup'] &= (setup.get('copied_local_programs') == n
                        and setup.get('copied_program_integer_cells') == 30*n and setup.get('copied_tree_integer_cells') == 140
                        and setup.get('copied_program_bytes') == 120*n and setup.get('copied_tree_bytes') == 560)
                checks['planner_references'] &= planner['program_ref'] == reference
                costs['model_accounting'].append(dict(life=life, query=query, method=method,
                    setup_counts=planner['setup_counts'], setup_seconds=planner['setup_seconds']))
    checks['all_physical_games_counted_once'] = len(indexed) == costs['control']['games'] == 512
    counts = costs['control']['policy_counts']
    costs['new_environment_samples'] = costs['control']['environment_counts'].get('sampled_transitions', 0)
    costs['new_model_samples'] = counts.get('model_sampled_transitions', 0)
    costs['generated_model_outcomes'] = counts.get('generated_spawn_outcomes', 0)
    for cell in [*costs['by_method'].values(), *(cell for queries in costs['by_query'].values() for cell in queries.values())]:
        steps = cell['steps']; work = cell['policy_counts']
        cell['per_decision'] = dict(seconds=cell['decision_seconds']/steps,
            swipes=work.get('learned_swipe_calls', 0)/steps, leaf_predictions=work.get('value_predictions', 0)/steps,
            sampled_model_transitions=work.get('model_sampled_transitions', 0)/steps,
            enumerated_model_outcomes=work.get('generated_spawn_outcomes', 0)/steps,
            tree_calls=work.get('tree_calls', 0)/steps, line_guards=work.get('line_guard_checks', 0)/steps,
            program_mask_tests=work.get('line_program_mask_tests', 0)/steps)
    control = full_game_comparison(indexed, valid)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.program_planning.v140.analysis', complete=complete,
        primary_complete=complete and control['complete'], checks={key: bool(value) for key, value in checks.items()},
        control=control, costs=costs, inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='All 512 fixed paired games are retained. The final learned program is compared with same-structure randomized priorities and frozen H2. Swipe ceilings match H2 at each visited root, while actual swipes, leaf predictions, tree guards, samples and time are reported separately. CUTOFF games retain all costs and suppress affected complete-return comparisons.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_program_planning_v140')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
