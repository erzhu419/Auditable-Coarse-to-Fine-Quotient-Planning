"""Separate query-aware continuation from the retained learned-program policy."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_shallow_sampling_v141 as previous

old, planning, teacher_analysis = previous.old, previous.planning, previous.teacher_analysis
v140 = previous.previous
LIVES, QUERIES, REPLICAS = previous.LIVES, previous.QUERIES, previous.REPLICAS
METHODS = ('H2', 'SHALLOW', 'LEARNED64', 'H1_CONT')
PROBES = ('SHALLOW', 'LEARNED64', 'H1_CONT')
COMPARISONS = {'H1_CONT-LEARNED64': ('H1_CONT', 'LEARNED64'),
    'H1_CONT-SHALLOW': ('H1_CONT', 'SHALLOW'), 'H1_CONT-H2': ('H1_CONT', 'H2')}
mean, add_checks, action_metrics = previous.mean, previous.add_checks, previous.action_metrics


def full_game_comparison(indexed, valid):
    """Keep every fixed seed, including censored and invalid outcomes."""
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
        complete=all(cell['complete'] for group in methods.values() for cell in group.values()))


def conditional_comparison(indexed):
    """Give each retained game and history equal weight despite varying lengths."""
    names = ('signed_q_error', 'absolute_q_error', 'centered_absolute_q_error',
        'centered_squared_q_error', 'greedy_disagreement', 'h2_proxy_regret')
    methods, grouped = {}, {}
    for (life, query, replica, step), probes in indexed.items():
        grouped.setdefault((life, query, replica), []).append(probes)
    for method in PROBES:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                games = []
                for replica in range(REPLICAS):
                    rows = grouped.get((life, query, replica), [])
                    games.append(dict(replica=replica, roots=len(rows),
                        means={name: mean(row[method][name] for row in rows) for name in names}))
                lives.append(dict(life=life, games=games, roots=sum(row['roots'] for row in games),
                    means={name: mean(row['means'][name] for row in games) for name in names}))
            methods[method][query] = dict(lifecycles=lives,
                means={name: mean(row['means'][name] for row in lives) for name in names})
    comparisons = {}
    for label, (left, right) in COMPARISONS.items():
        if right == 'H2': continue
        comparisons[label] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                a = methods[left][query]['lifecycles'][life]['means']
                b = methods[right][query]['lifecycles'][life]['means']
                lives.append(dict(life=life, means={name: None if a[name] is None or b[name] is None
                    else a[name]-b[name] for name in names}))
            comparisons[label][query] = dict(lifecycles=lives,
                means={name: mean(row['means'][name] for row in lives) for name in names})
    return dict(roots=len(indexed), methods=methods, comparisons=comparisons,
        reference='Frozen H2 action values on retained states; not true optimal Q values')


def root_choice_checks(board, choice, query):
    options, expected = choice['action_values'], {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = v140.ground.swipe_board_v1(tuple(board), v140.ground.Swipe2048Action(action))
        if changed: expected[action] = dict(afterstate=list(after), score=score)
    checks = dict(complete_root_action_values=set(options) == set(expected) and bool(options),
        root_action_values=True, greedy_choice=True)
    for action, item in options.items():
        checks['root_action_values'] &= (action in expected and item['afterstate'] == expected[action]['afterstate']
            and item['score'] == expected[action]['score']
            and all(math.isfinite(item[key]) for key in ('score', 'tail_value', 'value'))
            and item['value'] == item['score']/2048.+item['tail_value'])
        if max(item['afterstate']) >= 11:
            checks['root_action_values'] &= item['tail_value'] == QUERIES[query]['goal_bonus']
    selected = min(options, key=lambda action: (-options[action]['value'], action)) if options else None
    checks['greedy_choice'] &= (choice['status'] == 'ACTIVE' and choice['action'] == selected
        and selected is not None and choice['value'] == options[selected]['value']
        and choice.get('value_kind', 'estimated_return') == 'estimated_return')
    return checks


def h1_counts_valid(counts, options):
    n = lambda key: counts.get(key, 0)
    roots = len(options); goals = sum(max(row['afterstate']) >= 11 for row in options.values())
    rollouts = sum(row['rollouts'] for row in options.values())
    max_choices = 0
    checks = dict(h1_budget=True, h1_composition=True, h1_continuation=True,
        h1_sampling=True, h1_no_tree=True, no_evaluation_fitting=True)
    for row in options.values():
        cap = 0 if max(row['afterstate']) >= 11 else 8*row['afterstate'].count(0)
        samples = max(1, cap//16) if cap else 0
        checks['h1_budget'] &= row['budget'] == cap and row['rollouts'] == samples and 0 <= row['used'] <= cap and row['used']%4 == 0
        if samples:
            for replica in range(samples):
                allowance = cap//samples+int(replica < cap%samples)
                max_choices += min(3, max(0, (allowance-4)//4))
    checks['h1_budget'] &= (n('choose_calls') == 1 and n('root_swipe_calls') == 4
        and n('root_legal_actions') == roots and n('root_goal_actions') == goals
        and n('model_swipe_budget') == 4+sum(row['budget'] for row in options.values())
        and n('model_swipes_used') == n('learned_swipe_calls') == 4+sum(row['used'] for row in options.values())
        and n('learned_swipe_calls') == n('program_swipe_calls')+n('continuation_swipe_calls')+n('bootstrap_swipe_calls')
        and n('root_empty_cell_reads') == 16*(roots-goals))
    checks['h1_composition'] &= (n('program_swipe_calls') == 4
        and n('line_lookup_calls') == n('line_hits') == n('composition_line_gathers') == n('composition_line_scatters') == 16
        and n('line_misses') == 0 and n('line_bound_output_cells') == n('line_zero_mask_rank_reads') == 64
        and n('line_guard_rank_reads') == 2*n('line_guard_checks')
        and n('line_table_lookups') == 4*(n('bootstrap_swipe_calls')+n('continuation_swipe_calls'))
        and n('table_lookups') == 32*n('value_predictions')
        and n('learned_terminal_checks') == 1+n('legal_swipes')+n('leaf_choose_calls')+n('continuation_choose_calls'))
    checks['h1_continuation'] &= (n('continuation_swipe_calls') == 4*(n('continuation_choose_calls')-n('continuation_terminal_goal_states'))
        and n('continuation_choose_calls') <= max_choices
        and n('continuation_value_predictions') <= n('value_predictions')
        and n('continuation_value_predictions') <= n('continuation_swipe_calls')
        and n('bootstrap_swipe_calls') == 4*n('leaf_choose_calls')
        and n('leaf_choose_calls')+n('rollout_terminal_loss_states')+n('rollout_terminal_goal_states') == rollouts
        and n('continuation_choose_calls') == n('rollout_actions')+n('continuation_terminal_loss_states')+n('continuation_terminal_goal_states')
        and n('rollout_terminal_loss_states') == n('continuation_terminal_loss_states'))
    samples = n('model_sampled_transitions')
    checks['h1_sampling'] &= (n('rollouts_started') == rollouts
        and samples == rollouts+n('rollout_actions')-n('rollout_terminal_goal_states')+n('continuation_terminal_goal_states')
        and n('simulation_uniform_draws') == 2*samples and n('simulation_rng_initializations') == rollouts
        and n('spawn_empty_cell_reads') == 16*samples and n('spawn_board_writes') == samples
        and n('rollout_reward_additions') == n('rollout_actions') and n('rollout_mean_additions') == rollouts)
    checks['h1_no_tree'] &= all(n(key) == 0 for key in ('tree_calls', 'tree_order_reads',
        'tree_predicate_checks', 'feature_board_reads', 'feature_neighbor_comparisons', 'feature_predicate_values', 'direct_choose_calls'))
    checks['no_evaluation_fitting'] &= not any(value for key, value in counts.items()
        if key.endswith('updates') or key.startswith(('compiled_', 'fit_', 'observations')))
    return checks


def choice_checks(board, choice, query):
    checks = root_choice_checks(board, choice, query)
    add_checks(checks, h1_counts_valid(choice['work'], choice['action_values']))
    return checks


def control_checks(row):
    result, choices = row['result'], row['choices']
    checks = dict(new_control_trace=old.compact_valid(row) and row['method'] == 'H1_CONT'
        and row['seed'] == v140.outer_seed(row['life'], row['replica'])
        and result['utility'] == old.utility(result['score'], result['status'], row['query'])
        and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'],
        new_decision_roster=len(choices) == result['steps'], new_decision_seeds=True,
        new_successor_chain=True, new_step_cost_totals=True)
    board, prior, work = list(row['initial_board']), 'DOWN', Counter()
    for step, choice in enumerate(choices):
        work.update(choice['work'])
        checks['new_decision_seeds'] &= (choice['previous_action'] == prior
            and choice['simulation_seed'] == v140.model_seed(row['life'], row['replica'], step))
        add_checks(checks, choice_checks(board, choice, row['query']))
        action = choice['action']; after = list(choice['action_values'][action]['afterstate'])
        cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        checks['new_successor_chain'] &= action == row['actions'][step] and after[cell] == 0
        after[cell] = rank; board, prior = after, action
    checks['new_successor_chain'] &= board == row['final_board']
    checks['new_step_cost_totals'] &= work == Counter(result['policy_counts'])
    return checks


def expected_settings():
    return dict(lifecycles=list(LIVES), replicas=REPLICAS, workers=4, queries=QUERIES,
        methods=list(METHODS), representation='SINGLE', p_four=.1, max_steps=2000,
        new_physical_games=64, inherited_physical_games=192, logical_games=256,
        seed_version_base=v140.BASE, model_budget=v140.expected_settings()['model_budget'],
        first_spawn_count='max(1,(8*empty)//16)', continuation_rule='query-specific complete H1 action maximization',
        stopping_rule='same V140 allowance; remaining>=8 to start; at most3 continuation actions',
        planner_spawn_law='frozen_identified_distribution', diagnostic_source='all1973 retained V141 diagnostic roots',
        new_training_samples=0)


def retained_control_checks(row):
    """Validate the retained roster and returns; its original independent audit remains inherited."""
    return dict(retained_control_valid=old.compact_valid(row)
        and row['seed'] == v140.outer_seed(row['life'], row['replica'])
        and row['result']['utility'] == old.utility(row['result']['score'], row['result']['status'], row['query']))


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json'))
    sources = {row['life']: row for row in capsule['snapshots']}
    checks = dict(frozen_settings=run['settings'] == expected_settings(),
        source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        evaluation_lifecycles=len(run['eval_lifecycles']) == 4 and {row['life'] for row in run['eval_lifecycles']} == set(LIVES),
        frozen_before_new_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings', 'inherited_costs')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        source_complete=True, source_references=True, retained_baseline_roster=True,
        new_game_roster=True, diagnostic_roster=True, diagnostic_roots=True,
        diagnostic_reference_roster=True, diagnostic_common_model_seeds=True,
        query_roster=True, model_loads=True, frozen_models=True, frozen_program_payloads=True,
        planner_setup=True, planner_spawn_law=True, control_accounting=True,
        diagnostic_accounting=True, total_planner_accounting=True,
        unused_h2_planner=True, diagnostic_seconds=True, inherited_diagnostic_accounting=True)
    costs = dict(new_control=old.new_cost(), retained_control=old.new_cost(), by_method={},
        by_query={q: {} for q in QUERIES}, new_diagnostic=dict(choices=0, seconds=0., policy_counts=Counter()),
        retained_diagnostic={m: dict(choices=0, seconds=0., policy_counts=Counter()) for m in ('SHALLOW', 'LEARNED64')},
        source_game_rows_read=0, source_diagnostic_rows_read=0, model_accounting=[], new_training_samples=0,
        analysis_replay_swipes=0)
    indexed, valid, metrics = {}, {}, {}
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]
        origin = Path(source['shallow_control_trace']).parent.parent
        origin_run = json.loads((origin/'run.json').read_text())
        origin_capsule = json.loads((origin/'source_capsule.json').read_text())
        origin_analysis = json.loads((origin/'analysis.json').read_text())
        checks['source_complete'] &= origin_run['status'] == 'complete' and origin_analysis['complete'] and origin_analysis['primary_complete']
        original_source = next(row for row in origin_capsule['snapshots'] if row['life'] == life)
        origin_eval = next(row for row in origin_run['eval_lifecycles'] if row['life'] == life)
        source_copy = dict(source); source_copy.pop('shallow_control_trace'); source_copy.pop('diagnostic_source_trace')
        refs = dict(H2=source['baseline_control_trace'], LEARNED64=source['baseline_control_trace'], SHALLOW=source['shallow_control_trace'])
        checks['source_references'] &= (source_copy == original_source
            and Path(source['shallow_control_trace']) == origin/origin_eval['control_trace']
            and Path(source['diagnostic_source_trace']) == origin/origin_eval['diagnostics_trace']
            and lifecycle['baseline_refs'] == refs and lifecycle['diagnostic_source_trace'] == source['diagnostic_source_trace'])
        checks['inherited_costs'] &= capsule['inherited_costs'] == {
            **origin_capsule['inherited_costs'], 'v141_experiment': origin_analysis['costs']}
        baseline_keys = []
        for path, roster in ((source['baseline_control_trace'], ('H2', 'LEARNED64')),
                (source['shallow_control_trace'], ('SHALLOW',))):
            for row in old.read_rows(path):
                costs['source_game_rows_read'] += 1
                if row['method'] not in roster: continue
                key = row['life'], row['query'], row['method'], row['replica']; baseline_keys.append(key)
                result = retained_control_checks(row); add_checks(checks, result)
                indexed[key] = dict(result=row['result']); valid[key] = all(result.values())
                old.add_cost(costs['retained_control'], row)
                for cell in (costs['by_method'].setdefault(row['method'], old.new_cost()),
                        costs['by_query'][row['query']].setdefault(row['method'], old.new_cost())):
                    previous.cost_cell(cell, row)
        expected_keys = {(life, q, m, r) for q in QUERIES for m in ('H2', 'SHALLOW', 'LEARNED64') for r in range(REPLICAS)}
        checks['retained_baseline_roster'] &= len(baseline_keys) == len(set(baseline_keys)) == 48 and set(baseline_keys) == expected_keys
        control_work = {q: Counter() for q in QUERIES}; new_keys = []
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key = row['life'], row['query'], row['method'], row['replica']; new_keys.append(key)
            result = control_checks(row); add_checks(checks, result)
            indexed[key] = dict(result=row['result']); valid[key] = all(result.values())
            old.add_cost(costs['new_control'], row); control_work[row['query']].update(row['result']['policy_counts'])
            costs['analysis_replay_swipes'] += 4*row['result']['steps']
            for cell in (costs['by_method'].setdefault('H1_CONT', old.new_cost()),
                    costs['by_query'][row['query']].setdefault('H1_CONT', old.new_cost())):
                previous.cost_cell(cell, row)
        expected_keys = {(life, q, 'H1_CONT', r) for q in QUERIES for r in range(REPLICAS)}
        checks['new_game_roster'] &= len(new_keys) == len(set(new_keys)) == 16 and set(new_keys) == expected_keys
        retained, source_keys = {}, []
        inherited_diag = {q: {m: Counter() for m in ('SHALLOW', 'LEARNED64')} for q in QUERIES}
        for row in old.read_rows(source['diagnostic_source_trace']):
            key = row['life'], row['query'], row['replica'], row['step']; source_keys.append(key); retained[key] = row
            checks['diagnostic_reference_roster'] &= set(row['probes']) == {'SHALLOW', 'LEARNED64'}
            for method, probe in row['probes'].items():
                cell = costs['retained_diagnostic'][method]; cell['choices'] += 1; cell['seconds'] += probe['seconds']
                cell['policy_counts'].update(probe['work']); inherited_diag[row['query']][method].update(probe['work'])
        checks['diagnostic_roster'] &= (len(source_keys) == len(set(source_keys)) == lifecycle['source_diagnostic_rows_read']
            and len(source_keys) == sum(q['diagnostic_windows'] for q in origin_eval['queries'].values()))
        costs['source_diagnostic_rows_read'] += len(source_keys)
        diag_work = {q: Counter() for q in QUERIES}; diag_keys = []
        for row in old.read_rows(directory/lifecycle['diagnostics_trace']):
            key = row['life'], row['query'], row['replica'], row['step']; diag_keys.append(key)
            original = retained.get(key)
            checks['diagnostic_roots'] &= original is not None and all(row[name] == original[name]
                for name in ('life', 'query', 'replica', 'seed', 'step', 'board', 'previous_action', 'simulation_seed'))
            checks['diagnostic_common_model_seeds'] &= row['simulation_seed'] == v140.model_seed(life, row['replica'], row['step'])
            checks['diagnostic_roster'] &= set(row['probes']) == {'H1_CONT'}
            if original is None: continue
            metrics[key] = {method: action_metrics(original['reference'], probe) for method, probe in original['probes'].items()}
            probe = row['probes']['H1_CONT']; add_checks(checks, choice_checks(row['board'], probe, row['query']))
            metrics[key]['H1_CONT'] = action_metrics(original['reference'], probe)
            checks['diagnostic_seconds'] &= math.isfinite(probe['seconds']) and probe['seconds'] >= 0
            costs['analysis_replay_swipes'] += 4
            diag_work[row['query']].update(probe['work'])
            cell = costs['new_diagnostic']; cell['choices'] += 1; cell['seconds'] += probe['seconds']; cell['policy_counts'].update(probe['work'])
        checks['diagnostic_roster'] &= len(diag_keys) == len(set(diag_keys)) and set(diag_keys) == set(source_keys)
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        checks['frozen_program_payloads'] &= lifecycle['factored_payload_unchanged']
        for query, qdata in lifecycle['queries'].items():
            state = planning.expected_model_state(source, query, 'SINGLE')
            parent = planning.previous.model_state(source, query, 'PARENT', 0)
            checks['frozen_models'] &= qdata['parent_before'] == qdata['parent_after'] == parent and qdata['leaf_before'] == qdata['leaf_after'] == state
            checks['model_loads'] &= teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['control_accounting'] &= Counter(qdata['control_work']) == control_work[query]
            checks['diagnostic_accounting'] &= qdata['diagnostic_windows'] == sum(key[1] == query for key in diag_keys) and Counter(qdata['diagnostic_work']) == diag_work[query]
            checks['inherited_diagnostic_accounting'] &= all(Counter(origin_eval['queries'][query]['diagnostic_work'][m]) == inherited_diag[query][m] for m in inherited_diag[query])
            checks['unused_h2_planner'] &= not any(qdata['unused_teacher_counts'].values())
            n, setup = source['factored_summary']['num_programs'], qdata['setup_counts']
            checks['planner_setup'] &= (setup.get('copied_local_programs') == n
                and setup.get('copied_program_integer_cells') == 30*n and setup.get('copied_program_bytes') == 120*n
                and setup.get('copied_tree_integer_cells', 0) == setup.get('copied_tree_bytes', 0) == 0)
            checks['planner_spawn_law'] &= qdata['spawn_probabilities'] == planning.expected_spawn_probabilities(source)
            checks['total_planner_accounting'] &= Counter(qdata['counts']) == control_work[query]+diag_work[query]
            costs['model_accounting'].append(dict(life=life, query=query, loads=qdata['loads'], setup_counts=setup, setup_seconds=qdata['setup_seconds']))
    checks['all_games_counted_once'] = len(indexed) == 256 and costs['new_control']['games'] == 64 and costs['retained_control']['games'] == 192
    checks['all_retained_roots_probed_once'] = len(metrics) == costs['new_diagnostic']['choices'] == costs['source_diagnostic_rows_read'] == 1973
    for cell in [*costs['by_method'].values(), *(cell for group in costs['by_query'].values() for cell in group.values())]:
        previous.summarize_cost(cell)
        cell['per_decision']['continuation_choices'] = cell['policy_counts'].get('continuation_choose_calls', 0)/cell['steps']
        cell['per_decision']['continuation_predictions'] = cell['policy_counts'].get('continuation_value_predictions', 0)/cell['steps']
    costs['new_environment_samples'] = costs['new_control']['environment_counts'].get('sampled_transitions', 0)
    costs['new_control_model_samples'] = costs['new_control']['policy_counts'].get('model_sampled_transitions', 0)
    costs['new_diagnostic_model_samples'] = costs['new_diagnostic']['policy_counts'].get('model_sampled_transitions', 0)
    costs['new_diagnostic_environment_samples'] = 0
    control = full_game_comparison(indexed, valid); complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.h1_continuation.v142.analysis', complete=complete,
        primary_complete=complete and control['complete'], checks={key: bool(value) for key, value in checks.items()},
        control=control, diagnostics=conditional_comparison(metrics), costs=costs,
        inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='256 paired logical games comprise 192 retained games and 64 new H1_CONT games. All 1973 retained roots receive only the new H1_CONT probe. H2 Q is a frozen proxy. Initial sampling, per-trajectory allowance and maximum three continuation actions are retained; one-vacancy trajectories allow one ordinary action. Candidate H1 selection and terminal bootstrap are separately charged. Old diagnostics and their original checks remain inherited. Cutoffs retain costs and suppress affected complete returns.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_h1_continuation_v142')
    directory = parser.parse_args().input; result = analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
