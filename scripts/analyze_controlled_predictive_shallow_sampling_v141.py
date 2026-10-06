"""Separate root sampling from program continuation on retained paired games."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_program_planning_v140 as previous

old, planning, teacher_analysis = previous.old, previous.planning, previous.teacher_analysis
LIVES, QUERIES, REPLICAS = previous.LIVES, previous.QUERIES, previous.REPLICAS
METHODS = ('H2', 'SHALLOW', 'LEARNED64')
COMPARISONS = {'LEARNED64-SHALLOW': ('LEARNED64', 'SHALLOW'),
    'SHALLOW-H2': ('SHALLOW', 'H2'), 'LEARNED64-H2': ('LEARNED64', 'H2')}
mean, add_checks = previous.mean, previous.add_checks


def full_game_comparison(indexed, valid):
    """Keep all fixed seeds and suppress affected returns on missing/cutoff games."""
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


def action_metrics(reference, prediction):
    """Frozen H2 Q values are a comparison proxy, not ground-truth returns."""
    ref, pred = reference['action_values'], prediction['action_values']
    if set(ref) != set(pred) or not ref:
        raise ValueError('conditional action roster differs')
    errors = [pred[action]['value']-ref[action]['value'] for action in sorted(ref)]
    bias = mean(errors)
    return dict(signed_q_error=bias, absolute_q_error=mean(abs(value) for value in errors),
        centered_absolute_q_error=mean(abs(value-bias) for value in errors),
        centered_squared_q_error=mean((value-bias)**2 for value in errors),
        greedy_disagreement=int(reference['action'] != prediction['action']),
        h2_proxy_regret=reference['value']-ref[prediction['action']]['value'])


def conditional_comparison(indexed):
    """Average roots within games, eight games within history, then four histories."""
    metric_names = ('signed_q_error', 'absolute_q_error', 'centered_absolute_q_error',
        'centered_squared_q_error', 'greedy_disagreement', 'h2_proxy_regret')
    methods = {}; grouped = {}
    for (life, query, replica, step), probes in indexed.items():
        grouped.setdefault((life, query, replica), []).append(probes)
    for method in ('SHALLOW', 'LEARNED64'):
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                games = []
                for replica in range(REPLICAS):
                    rows = grouped.get((life, query, replica), [])
                    games.append(dict(replica=replica, roots=len(rows),
                        means={name: mean(row[method][name] for row in rows) for name in metric_names}))
                lives.append(dict(life=life, games=games, roots=sum(row['roots'] for row in games),
                    means={name: mean(row['means'][name] for row in games) for name in metric_names}))
            methods[method][query] = dict(lifecycles=lives,
                means={name: mean(row['means'][name] for row in lives) for name in metric_names})
    delta = {}
    for query in QUERIES:
        lives = []
        for life in LIVES:
            left = methods['LEARNED64'][query]['lifecycles'][life]['means']
            right = methods['SHALLOW'][query]['lifecycles'][life]['means']
            lives.append(dict(life=life, means={name: None if left[name] is None or right[name] is None
                else left[name]-right[name] for name in metric_names}))
        delta[query] = dict(lifecycles=lives,
            means={name: mean(row['means'][name] for row in lives) for name in metric_names})
    return dict(roots=len(indexed), methods=methods, learned_minus_shallow=delta,
        reference='Frozen H2 action values on its retained states; not true optimal Q values')


def shallow_counts_valid(counts, options):
    n = lambda key: counts.get(key, 0)
    roots = len(options); goals = sum(max(row['afterstate']) >= 11 for row in options.values())
    rollouts = sum(row['rollouts'] for row in options.values())
    checks = dict(shallow_budget=True, shallow_composition=True, shallow_sampling=True,
        shallow_no_program_continuation=True, no_evaluation_fitting=True)
    for row in options.values():
        cap = 0 if max(row['afterstate']) >= 11 else 8*row['afterstate'].count(0)
        samples = max(1, cap//16) if cap else 0
        checks['shallow_budget'] &= row['budget'] == cap and row['rollouts'] == samples and row['used'] == 4*samples <= cap
    checks['shallow_budget'] &= (n('choose_calls') == 1 and n('root_swipe_calls') == 4
        and n('root_legal_actions') == roots and n('root_goal_actions') == goals
        and n('model_swipe_budget') == 4+sum(row['budget'] for row in options.values())
        and n('model_swipes_used') == n('learned_swipe_calls') == 4+4*rollouts
        and n('program_swipe_calls') == 4 and n('bootstrap_swipe_calls') == 4*rollouts
        and n('leaf_choose_calls') == rollouts and n('root_empty_cell_reads') == 16*(roots-goals))
    checks['shallow_composition'] &= (n('line_lookup_calls') == n('line_hits') == n('composition_line_gathers')
        == n('composition_line_scatters') == 16 and n('line_misses') == 0
        and n('line_bound_output_cells') == n('line_zero_mask_rank_reads') == 64
        and n('line_guard_rank_reads') == 2*n('line_guard_checks')
        and n('line_table_lookups') == 4*n('bootstrap_swipe_calls')
        and n('table_lookups') == 32*n('value_predictions')
        and n('learned_terminal_checks') == 1+n('legal_swipes')+n('leaf_choose_calls'))
    checks['shallow_sampling'] &= (n('rollouts_started') == n('model_sampled_transitions') == rollouts
        and n('simulation_uniform_draws') == 2*rollouts and n('simulation_rng_initializations') == rollouts
        and n('spawn_empty_cell_reads') == 16*rollouts and n('spawn_board_writes') == rollouts
        and n('rollout_mean_additions') == rollouts)
    checks['shallow_no_program_continuation'] &= all(n(key) == 0 for key in ('tree_calls', 'tree_order_reads',
        'tree_predicate_checks', 'feature_board_reads', 'feature_neighbor_comparisons', 'feature_predicate_values',
        'rollout_actions', 'rollout_reward_additions', 'direct_choose_calls', 'rollout_terminal_goal_states',
        'rollout_terminal_loss_states'))
    checks['no_evaluation_fitting'] &= not any(value for key, value in counts.items()
        if key.endswith('updates') or key.startswith(('compiled_', 'fit_', 'observations')))
    return checks


def choice_checks(board, choice, query, method):
    options = choice['action_values']; expected = {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = previous.ground.swipe_board_v1(tuple(board), previous.ground.Swipe2048Action(action))
        if changed:
            expected[action] = dict(afterstate=list(after), score=score)
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
    add_checks(checks, shallow_counts_valid(choice['work'], options) if method == 'SHALLOW'
        else previous.program_counts_valid(choice['work'], options, False))
    return checks


def shallow_control_checks(row):
    result, choices = row['result'], row['choices']
    checks = dict(new_control_trace=old.compact_valid(row) and row['method'] == 'SHALLOW'
        and row['seed'] == previous.outer_seed(row['life'], row['replica'])
        and result['utility'] == old.utility(result['score'], result['status'], row['query'])
        and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'],
        new_decision_roster=len(choices) == result['steps'], new_decision_seeds=True,
        new_successor_chain=True, new_step_cost_totals=True)
    board, prior, work = list(row['initial_board']), 'DOWN', Counter()
    for step, choice in enumerate(choices):
        work.update(choice['work'])
        checks['new_decision_seeds'] &= (choice['previous_action'] == prior
            and choice['simulation_seed'] == previous.model_seed(row['life'], row['replica'], step))
        add_checks(checks, choice_checks(board, choice, row['query'], 'SHALLOW'))
        action = choice['action']; after = list(choice['action_values'][action]['afterstate'])
        cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        checks['new_successor_chain'] &= action == row['actions'][step] and after[cell] == 0
        after[cell] = rank; board, prior = after, action
    checks['new_successor_chain'] &= board == row['final_board']
    checks['new_step_cost_totals'] &= work == Counter(result['policy_counts'])
    return checks


def cost_cell(cost, row):
    old.add_cost(cost, row)
    cost['steps'] = cost.get('steps', 0)+row['result']['steps']
    cost['decision_seconds'] = cost.get('decision_seconds', 0.)+row['result']['decision_seconds']


def summarize_cost(cost):
    steps, work = cost['steps'], cost['policy_counts']
    cost['per_decision'] = dict(seconds=cost['decision_seconds']/steps,
        swipes=work.get('learned_swipe_calls', 0)/steps, leaf_predictions=work.get('value_predictions', 0)/steps,
        sampled_model_transitions=work.get('model_sampled_transitions', 0)/steps,
        enumerated_model_outcomes=work.get('generated_spawn_outcomes', 0)/steps,
        tree_calls=work.get('tree_calls', 0)/steps)


def expected_settings():
    return dict(lifecycles=list(LIVES), replicas=REPLICAS, workers=4, queries=QUERIES,
        methods=list(METHODS), representation='SINGLE', policy_age=64, p_four=.1, max_steps=2000,
        new_physical_games=64, inherited_physical_games=128, logical_games=192, diagnostic_stride=32,
        seed_version_base=previous.BASE, model_budget=previous.expected_settings()['model_budget'],
        first_spawn_count='max(1,(8*empty)//16)', planner_spawn_law='frozen_identified_distribution',
        diagnostic_source='every32nd decision of all retained V140 H2 games', new_training_samples=0)


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json'))
    sources = {row['life']: row for row in capsule['snapshots']}
    checks = dict(frozen_settings=run['settings'] == expected_settings(),
        source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        evaluation_lifecycles=len(run['eval_lifecycles']) == 4
            and {row['life'] for row in run['eval_lifecycles']} == set(LIVES),
        frozen_before_new_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings', 'inherited_costs')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        source_complete=True, source_references=True, retained_baseline_roster=True,
        new_game_roster=True, diagnostic_roster=True, diagnostic_roots=True,
        diagnostic_reference=True, diagnostic_common_model_seeds=True,
        query_roster=True, model_loads=True, frozen_models=True, frozen_program_payloads=True,
        planner_setup=True, planner_spawn_law=True, control_accounting=True,
        diagnostic_accounting=True, total_planner_accounting=True, reconstruction_accounting=True,
        unused_h2_planner=True, diagnostic_seconds=True)
    costs = dict(new_control=old.new_cost(), retained_control=old.new_cost(), by_method={},
        by_query={q: {} for q in QUERIES}, diagnostic={method: dict(choices=0, seconds=0., policy_counts=Counter())
            for method in ('SHALLOW', 'LEARNED64')}, source_game_rows_read=0,
        reconstruction_work=Counter(), model_accounting=[], new_training_samples=0,
        analysis_replay_swipes=0)
    indexed, valid, expected_diagnostics, metrics = {}, {}, {}, {}
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]
        origin = Path(source['baseline_control_trace']).parent.parent
        origin_run = json.loads((origin/'run.json').read_text())
        origin_capsule = json.loads((origin/'source_capsule.json').read_text())
        origin_analysis = json.loads((origin/'analysis.json').read_text())
        checks['source_complete'] &= (origin_run['status'] == 'complete'
            and origin_analysis['complete'] and origin_analysis['primary_complete'])
        original_source = next(row for row in origin_capsule['snapshots'] if row['life'] == life)
        source_copy = dict(source); source_copy.pop('program_ref'); source_copy.pop('baseline_control_trace')
        trained = next(row for row in origin_run['lifecycles'] if row['life'] == life)
        policy_ref = next(row for row in trained['snapshots'] if row['age'] == 64)['LEARNED']['path']
        old_eval = next(row for row in origin_run['eval_lifecycles'] if row['life'] == life)
        checks['source_references'] &= (source_copy == original_source
            and Path(source['program_ref']) == origin/policy_ref
            and Path(source['baseline_control_trace']) == origin/old_eval['control_trace']
            and lifecycle['baseline_control_trace'] == source['baseline_control_trace'])
        checks['inherited_costs'] &= capsule['inherited_costs'] == {
            **origin_capsule['inherited_costs'], 'v140_experiment': origin_analysis['costs']}
        baseline_keys, baseline_roster, source_rows = [], [], 0
        reconstruction = {query: Counter() for query in QUERIES}
        for row in old.read_rows(source['baseline_control_trace']):
            source_rows += 1
            if row['method'] not in ('H2', 'LEARNED64'): continue
            key = row['life'], row['query'], row['method'], row['replica']
            baseline_keys.append(key)
            baseline_roster.append({name: row[name] for name in ('query', 'method', 'replica', 'seed')})
            row_checks = previous.control_checks(row, None); add_checks(checks, row_checks)
            indexed[key] = dict(result=row['result']); valid[key] = all(row_checks.values())
            old.add_cost(costs['retained_control'], row)
            for cell in (costs['by_method'].setdefault(row['method'], old.new_cost()),
                    costs['by_query'][row['query']].setdefault(row['method'], old.new_cost())):
                cost_cell(cell, row)
            if row['method'] == 'H2':
                board, prior, query = list(row['initial_board']), 'DOWN', row['query']
                reconstruction[query]['initial_board_rank_reads'] += 16
                for step, choice in enumerate(row['choices']):
                    if step%32 == 0:
                        dkey = life, query, row['replica'], step
                        expected_diagnostics[dkey] = dict(board=list(board), previous_action=prior,
                            seed=row['seed'], simulation_seed=previous.model_seed(life, row['replica'], step), reference=choice)
                    action = row['actions'][step]; board = list(choice['action_values'][action]['afterstate'])
                    board[row['spawned_cells'][step]] = row['spawned_ranks'][step]; prior = action
                    reconstruction[query].update(retained_afterstate_rank_reads=16, recorded_spawn_patches=1)
        expected = {(life, query, method, replica) for query in QUERIES
            for method in ('H2', 'LEARNED64') for replica in range(REPLICAS)}
        checks['retained_baseline_roster'] &= (len(baseline_keys) == len(set(baseline_keys)) == 32
            and set(baseline_keys) == expected and lifecycle['baseline_roster'] == baseline_roster
            and lifecycle['source_game_rows_read'] == source_rows == 128)
        costs['source_game_rows_read'] += source_rows
        control_work = {query: Counter() for query in QUERIES}; new_keys = []
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key = row['life'], row['query'], row['method'], row['replica']; new_keys.append(key)
            row_checks = shallow_control_checks(row); add_checks(checks, row_checks)
            indexed[key] = dict(result=row['result']); valid[key] = all(row_checks.values())
            old.add_cost(costs['new_control'], row); control_work[row['query']].update(row['result']['policy_counts'])
            costs['analysis_replay_swipes'] += 4*row['result']['steps']
            for cell in (costs['by_method'].setdefault('SHALLOW', old.new_cost()),
                    costs['by_query'][row['query']].setdefault('SHALLOW', old.new_cost())):
                cost_cell(cell, row)
        expected = {(life, query, 'SHALLOW', replica) for query in QUERIES for replica in range(REPLICAS)}
        checks['new_game_roster'] &= len(new_keys) == len(set(new_keys)) == 16 and set(new_keys) == expected
        diag_keys = []; diag_work = {q: {m: Counter() for m in ('SHALLOW', 'LEARNED64')} for q in QUERIES}
        for row in old.read_rows(directory/lifecycle['diagnostics_trace']):
            key = row['life'], row['query'], row['replica'], row['step']; diag_keys.append(key)
            expected = expected_diagnostics.get(key)
            checks['diagnostic_roots'] &= expected is not None and all(row[name] == expected[name]
                for name in ('board', 'previous_action', 'seed'))
            checks['diagnostic_reference'] &= expected is not None and row['reference'] == expected['reference']
            checks['diagnostic_common_model_seeds'] &= expected is not None and row['simulation_seed'] == expected['simulation_seed']
            checks['diagnostic_roster'] &= set(row['probes']) == {'SHALLOW', 'LEARNED64'}
            metrics[key] = {}
            for method, probe in row['probes'].items():
                add_checks(checks, choice_checks(row['board'], probe, row['query'], method))
                costs['analysis_replay_swipes'] += 4
                checks['diagnostic_seconds'] &= math.isfinite(probe['seconds']) and probe['seconds'] >= 0
                metrics[key][method] = action_metrics(row['reference'], probe)
                diag_work[row['query']][method].update(probe['work'])
                cell = costs['diagnostic'][method]; cell['choices'] += 1; cell['seconds'] += probe['seconds']
                cell['policy_counts'].update(probe['work'])
        expected_keys = {key for key in expected_diagnostics if key[0] == life}
        checks['diagnostic_roster'] &= len(diag_keys) == len(set(diag_keys)) and set(diag_keys) == expected_keys
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        checks['frozen_program_payloads'] &= lifecycle['policy_payload_unchanged'] and lifecycle['factored_payload_unchanged']
        for query, qdata in lifecycle['queries'].items():
            state = planning.expected_model_state(source, query, 'SINGLE')
            parent = planning.previous.model_state(source, query, 'PARENT', 0)
            checks['frozen_models'] &= qdata['parent_before'] == qdata['parent_after'] == parent and qdata['leaf_before'] == qdata['leaf_after'] == state
            checks['model_loads'] &= teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            costs['model_accounting'].append(dict(life=life, query=query, loads=qdata['loads']))
            checks['control_accounting'] &= Counter(qdata['control_work']) == control_work[query]
            checks['diagnostic_accounting'] &= (qdata['diagnostic_windows'] == sum(key[1] == query for key in diag_keys)
                and set(qdata['diagnostic_work']) == {'SHALLOW', 'LEARNED64'}
                and all(Counter(qdata['diagnostic_work'][method]) == diag_work[query][method] for method in diag_work[query]))
            checks['reconstruction_accounting'] &= Counter(qdata['reconstruction_work']) == reconstruction[query]
            costs['reconstruction_work'].update(reconstruction[query])
            checks['unused_h2_planner'] &= not any(qdata['unused_teacher_counts'].values())
            checks['planner_setup'] &= set(qdata['planners']) == {'SHALLOW', 'LEARNED64'}
            for method, planner in qdata['planners'].items():
                n = source['factored_summary']['num_programs']; setup = planner['setup_counts']
                checks['planner_setup'] &= (setup.get('copied_local_programs') == n
                    and setup.get('copied_program_integer_cells') == 30*n and setup.get('copied_program_bytes') == 120*n
                    and setup.get('copied_tree_integer_cells', 0) == (0 if method == 'SHALLOW' else 140)
                    and setup.get('copied_tree_bytes', 0) == (0 if method == 'SHALLOW' else 560))
                checks['planner_spawn_law'] &= planner['spawn_probabilities'] == planning.expected_spawn_probabilities(source)
                expected_work = diag_work[query][method]+(control_work[query] if method == 'SHALLOW' else Counter())
                checks['total_planner_accounting'] &= Counter(planner['counts']) == expected_work
                costs['model_accounting'].append(dict(life=life, query=query, method=method,
                    setup_counts=setup, setup_seconds=planner['setup_seconds']))
    checks['all_games_counted_once'] = (len(indexed) == 192 and costs['new_control']['games'] == 64
        and costs['retained_control']['games'] == 128)
    for cell in [*costs['by_method'].values(), *(cell for group in costs['by_query'].values() for cell in group.values())]:
        summarize_cost(cell)
    costs['new_environment_samples'] = costs['new_control']['environment_counts'].get('sampled_transitions', 0)
    costs['new_control_model_samples'] = costs['new_control']['policy_counts'].get('model_sampled_transitions', 0)
    costs['new_diagnostic_model_samples'] = sum(cell['policy_counts'].get('model_sampled_transitions', 0) for cell in costs['diagnostic'].values())
    costs['new_diagnostic_environment_samples'] = 0
    control = full_game_comparison(indexed, valid)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.shallow_sampling.v141.analysis', complete=complete,
        primary_complete=complete and control['complete'], checks={key: bool(value) for key, value in checks.items()},
        control=control, diagnostics=conditional_comparison(metrics), costs=costs,
        inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='192 paired logical games comprise 128 retained V140 games and 64 new SHALLOW games. Conditional errors use every32nd retained H2 decision with complete legal-action Q values, averaged by game then history. H2 Q is a frozen proxy. Initial spawn sampling is held fixed while three continuation actions are removed; ceilings match while actual work is charged. CUTOFF retains costs and suppresses affected complete returns.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_shallow_sampling_v141')
    result = analyze(parser.parse_args().input)
    (parser.parse_args().input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
