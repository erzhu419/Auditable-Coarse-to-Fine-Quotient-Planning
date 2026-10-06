"""Audit fixed-teacher Bellman consequences and unseen-query full games."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from scripts import analyze_controlled_predictive_frozen_leaf_planning_v135 as planning

LIVES, REPRESENTATIONS, TEACHERS = tuple(range(4)), ('SINGLE', 'CAPACITY'), ('risk1', 'risk8')
NEW_QUERIES, METHODS = ('risk2', 'risk6'), ('TEACHER', 'INITIAL_H2', 'LEARNED_H2')
QUERIES = {f'risk{risk}': dict(reward_weight=1., failure_penalty=float(risk), goal_bonus=float(risk))
    for risk in (1, 2, 6, 8)}
REPLICAS, MAX_STEPS, BASE, BUDGET = 16, 2000, 136*100000000, 524288


def evaluation_queries(teacher):
    return (teacher,)+NEW_QUERIES


def mean(values):
    values = list(values)
    return None if not values or any(value is None for value in values) else sum(values)/len(values)


def utility(score, status, query):
    q = QUERIES[query]
    return score/2048.-q['failure_penalty']*(status == 'LOST')+q['goal_bonus']*(status == 'WON')


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def full_game_comparison(indexed, valid):
    """Keep teacher policies and representations separate on every query."""
    cells = []
    for representation in REPRESENTATIONS:
        for teacher in TEACHERS:
            for query in evaluation_queries(teacher):
                methods, comparisons = {}, {}
                for method in METHODS:
                    lives = []
                    for life in LIVES:
                        keys = [(life, representation, teacher, query, method, replica) for replica in range(REPLICAS)]
                        rows = [indexed[key] for key in keys if key in indexed]
                        complete = all(key in indexed and valid.get(key, False)
                            and indexed[key]['result']['status'] in ('WON', 'LOST') for key in keys)
                        lives.append(dict(life=life, complete=complete, games=len(rows),
                            statuses=dict(Counter(row['result']['status'] for row in rows)),
                            wins=sum(row['result']['status'] == 'WON' for row in rows),
                            means={name: mean(row['result'][name] for row in rows) if complete else None
                                for name in ('utility', 'score', 'steps')}))
                    methods[method] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                        means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
                for baseline in ('TEACHER', 'INITIAL_H2'):
                    lives = []
                    for life in LIVES:
                        complete = methods['LEARNED_H2']['lifecycles'][life]['complete'] and methods[baseline]['lifecycles'][life]['complete']
                        item = dict(life=life, complete=complete)
                        if complete:
                            deltas = [indexed[(life, representation, teacher, query, 'LEARNED_H2', replica)]['result']['utility']-
                                indexed[(life, representation, teacher, query, baseline, replica)]['result']['utility']
                                for replica in range(REPLICAS)]
                            item.update(mean=mean(deltas), replica_deltas=deltas)
                        lives.append(item)
                    comparisons['LEARNED_minus_'+baseline] = dict(lifecycles=lives,
                        complete=all(row['complete'] for row in lives), mean=mean(row.get('mean') for row in lives),
                        positive=sum(row.get('mean', 0) > 0 for row in lives),
                        negative=sum(row.get('mean', 0) < 0 for row in lives), zero=sum(row.get('mean') == 0 for row in lives))
                cells.append(dict(representation=representation, teacher_query=teacher, query=query,
                    query_role='old' if query == teacher else 'new', methods=methods, comparisons=comparisons))
    return dict(cells=cells, complete=all(method['complete'] for cell in cells for method in cell['methods'].values()))


def diagnostic_targets(scores, status):
    """Observed suffix reward excludes its afterstate's own action reward."""
    if status not in ('WON', 'LOST'): return None
    remaining = sum(scores); result = []
    for index, score in enumerate(scores):
        remaining -= score
        if status == 'WON' and index == len(scores)-1: break
        result.append(dict(reward=remaining/2048., success=float(status == 'WON')))
    return result


def component_errors(predictions, targets, teacher_query):
    if targets is None or len(predictions) != len(targets) or not targets:
        return dict(complete=False, eligible_afterstates=0 if targets is None else len(targets))
    q = QUERIES[teacher_query]; reward_errors, success_errors, query_errors = [], [], []
    for predicted, target in zip(predictions, targets):
        reward, success = predicted['reward'], predicted['success']
        if not (math.isfinite(reward) and math.isfinite(success) and 0 <= success <= 1):
            return dict(complete=False, eligible_afterstates=len(targets))
        re, se = reward-target['reward'], success-target['success']
        reward_errors.append(re); success_errors.append(se)
        query_errors.append(re+(q['failure_penalty']+q['goal_bonus'])*se)
    return dict(complete=True, eligible_afterstates=len(targets), reward_mse=mean(e*e for e in reward_errors),
        success_brier=mean(e*e for e in success_errors), source_query_mse=mean(e*e for e in query_errors),
        reward_bias=mean(reward_errors), success_bias=mean(success_errors), source_query_bias=mean(query_errors))


def calibration_summary(games):
    metrics = ('reward_mse', 'success_brier', 'source_query_mse', 'reward_bias', 'success_bias', 'source_query_bias')
    cells = []
    for representation in REPRESENTATIONS:
        for teacher in TEACHERS:
            lives = []
            for life in LIVES:
                selected = [row for row in games if (row['representation'], row['teacher_query'], row['life']) == (representation, teacher, life)]
                complete = (len(selected) == REPLICAS and {row['replica'] for row in selected} == set(range(REPLICAS))
                    and all(row[phase]['complete'] for row in selected for phase in ('initial', 'learned')))
                phases = {phase: {metric: mean(row[phase][metric] for row in selected) if complete else None
                    for metric in metrics} for phase in ('initial', 'learned')}
                changes = {metric: phases['learned'][metric]-phases['initial'][metric] if complete else None for metric in metrics}
                lives.append(dict(life=life, complete=complete, games=len(selected), phases=phases,
                    eligible_afterstates=sum(row['initial']['eligible_afterstates'] for row in selected), changes=changes))
            cells.append(dict(representation=representation, teacher_query=teacher,
                complete=all(row['complete'] for row in lives), lifecycles=lives,
                means={phase: {metric: mean(row['phases'][phase][metric] for row in lives) for metric in metrics}
                    for phase in ('initial', 'learned')},
                changes={metric: mean(row['changes'][metric] for row in lives) for metric in metrics}))
    return dict(cells=cells, complete=all(cell['complete'] for cell in cells),
        weighting='eligible afterstates within each game, then equally weighted games and four histories')


def parameter_count(representation):
    return 2*planning.previous.parameter_count(representation)


def component_state(representation, updates, readonly=True):
    return dict(updates=updates, readonly=readonly, parameter_count=parameter_count(representation))


def reward_intercept(source, teacher):
    return planning.previous.expected_offset(source, teacher, 'PRIOR')


def train_seed(life, representation, teacher, episode):
    return BASE+10000000+life*2000000+REPRESENTATIONS.index(representation)*1000000+TEACHERS.index(teacher)*500000+episode


def component_counts_valid(counts, representation, updates):
    value = lambda key: counts.get(key, 0)
    predictions = value('joint_predictions')
    return (value('reward_predictions') == value('success_predictions') == value('sigmoid_evaluations') == predictions
        and value('table_lookups') == 64*predictions and value('feature_address_occurrences') == 32*predictions
        and value('bank_0_prediction_occurrences')+value('bank_1_prediction_occurrences') == 32*(predictions-updates)
        and value('bank_0_update_occurrences')+value('bank_1_update_occurrences') == 32*updates
        and value('td_updates') == value('reward_td_updates') == value('success_td_updates') == updates
        and value('reward_table_update_occurrences') == value('success_table_update_occurrences') == 32*updates
        and value('reward_table_updates') == value('success_table_updates')
        and updates <= value('reward_table_updates') <= 32*updates
        and 32*updates <= value('update_feature_squared_norm') <= 256*updates
        and all(value(key) == (32*predictions if representation == 'CAPACITY' else 0)
            for key in ('context_cell_reads', 'context_bank_selections', 'context_bank_offset_additions'))
        and not any(amount for key, amount in counts.items() if key.endswith('model_spawn_samples')))


def joint_planning_counts_valid(counts, representation, steps, root_actions):
    value = lambda key: counts.get(key, 0); outcomes = value('generated_spawn_outcomes')
    return (component_counts_valid(counts, representation, 0)
        and value('choose_calls') == steps and value('root_swipe_calls') == 4*steps
        and value('root_legal_actions') == root_actions and value('root_goal_actions') <= root_actions
        and value('leaf_choose_calls') == outcomes
        and value('spawn_rank1_outcomes') == value('spawn_rank2_outcomes')
        and value('spawn_rank1_outcomes')+value('spawn_rank2_outcomes') == outcomes
        and value('second_ply_swipe_calls') == 4*outcomes
        and value('learned_swipe_calls') == value('root_swipe_calls')+value('second_ply_swipe_calls')
        and value('line_table_lookups') == 4*value('learned_swipe_calls')
        and value('learned_terminal_checks') == steps+outcomes+value('legal_swipes')
        and value('joint_predictions') == value('legal_swipes')-root_actions-value('terminal_goal_bypasses')+value('root_goal_actions')
        and value('expectimax_probability_products') == value('expectimax_probability_sums') == 3*outcomes
        and 2*(root_actions-value('root_goal_actions')) <= outcomes <= 32*(root_actions-value('root_goal_actions')))


def update_valid(update, target_reward, target_success, intercept):
    return (update['target_reward'] == target_reward and update['target_success'] == target_success
        and update['raw_reward_target'] == target_reward-intercept
        and update['pre_reward'] == update['pre_raw_reward']+intercept
        and update['reward_error'] == update['raw_reward_target']-update['pre_raw_reward']
        and update['success_error'] == target_success-update['pre_success']
        and 0 <= target_success <= 1 and 0 <= update['pre_success'] <= 1
        and all(math.isfinite(update[key]) for key in ('pre_raw_reward', 'pre_reward', 'pre_logit',
            'pre_success', 'target_reward', 'target_success', 'raw_reward_target', 'reward_error', 'success_error'))
        and update['work'].get('td_updates') == update['work'].get('reward_td_updates') == update['work'].get('success_td_updates') == 1)


def segment_checks(row, previous, source, representation, teacher):
    n, status = len(row['actions']), row['status']; first = row['start_step'] == 0
    intercept = reward_intercept(source, teacher)
    arrays = ('scores', 'spawned_cells', 'spawned_ranks', 'chosen_values', 'next_components', 'joint_updates')
    checks = dict(segment_shape=0 < n and all(len(row[key]) == n for key in arrays)
        and row['end_step']-row['start_step'] == n and row['end_step'] <= MAX_STEPS,
        segment_terminal=status in ('ACTIVE', 'WON', 'LOST', 'CUTOFF')
        and planning.previous.board_status(row['end_board']) == ('ACTIVE' if status == 'CUTOFF' else status)
        and (status != 'CUTOFF' or row['end_step'] == MAX_STEPS)
        and row['budget_status'] == ('BUDGET_END' if status == 'ACTIVE' else 'EPISODE_END')
        and row['censored_last_update'] == (status == 'CUTOFF'),
        stream_continuity=True, initial_spawns=True, joint_targets=True, pending_semantics=True,
        training_counters=True, teacher_planning=True)
    if not checks['segment_shape']: return {key: False for key in checks}
    if first:
        spawns = row.get('initial_spawns', []); board = [0]*16
        for spawn in spawns: board[spawn['cell']] = spawn['rank']
        checks['initial_spawns'] &= (len(spawns) == 2 and len({s['cell'] for s in spawns}) == 2
            and board == row['start_board'] and row['pending_before'] is None)
    else:
        checks['initial_spawns'] &= 'initial_spawns' not in row and row['pending_before'] is not None
    if previous is None:
        checks['stream_continuity'] &= row['episode'] == 0 and first and row['updates_before'] == 0
    else:
        same = previous['status'] == 'ACTIVE'
        checks['stream_continuity'] &= (row['updates_before'] == previous['updates_after']
            and row['cumulative_transitions'] == previous['cumulative_transitions']+n
            and row['episode'] == previous['episode']+int(not same)
            and (not same or (row['seed'] == previous['seed'] and row['start_step'] == previous['end_step']
                and row['start_board'] == previous['end_board'] and row['pending_before'] == previous['pending_after']))
            and (same or first))
    checks['stream_continuity'] &= row['return_score'] == (0 if first else previous['return_score'])+sum(row['scores'])
    for i, (prediction, update) in enumerate(zip(row['next_components'], row['joint_updates'])):
        winning = status == 'WON' and i == n-1
        if winning:
            checks['joint_targets'] &= prediction == dict(raw_reward=0., reward=0., logit=None, success=1., failure=0.)
        else:
            checks['joint_targets'] &= (all(math.isfinite(prediction[key]) for key in ('raw_reward', 'reward', 'logit', 'success', 'failure'))
                and prediction['reward'] == prediction['raw_reward']+intercept
                and 0 <= prediction['success'] <= 1 and prediction['failure'] == 1.-prediction['success'])
        checks['joint_targets'] &= (update is None) if first and i == 0 else (update is not None
            and update_valid(update, row['scores'][i]/2048.+prediction['reward'], prediction['success'], intercept))
    terminal = row['terminal_update']
    checks['joint_targets'] &= (terminal is not None and update_valid(terminal, 0., 0., intercept)) if status == 'LOST' else terminal is None
    after = list(row['end_board']); cell = row['spawned_cells'][-1]
    checks['pending_semantics'] &= after[cell] == row['spawned_ranks'][-1]
    after[cell] = 0
    checks['pending_semantics'] &= row['pending_after'] == (after if status == 'ACTIVE' else None)
    if terminal is not None: checks['pending_semantics'] &= terminal['afterstate'] == after
    updates = sum(update is not None for update in row['joint_updates'])+int(terminal is not None)
    work, model, teacher_counts = row['environment_counts'], row['model_counts'], row['teacher_counts']
    checks['training_counters'] &= (row['updates_after'] == row['updates_before']+updates
        and row['cumulative_updates'] == row['updates_after'] and work.get('sampled_transitions') == n
        and work.get('initial_spawns', 0) == 2*first and work.get('environment_random_draws') == 2*n+4*first
        and work.get('ground_explicit_swipe_calls') == n and work.get('ground_state_status_calls') == n+first
        and work.get('ground_status_internal_swipe_calls') == 4*(n+first-int(status == 'WON'))
        and model.get('value_calls') == n and model.get('choose_calls', 0) == 0
        and model.get('joint_predictions') == n-int(status == 'WON')+updates
        and component_counts_valid(model, representation, updates))
    checks['teacher_planning'] &= planning.planning_counts_valid(teacher_counts, 'H2', representation, n, teacher_counts.get('root_legal_actions', 0))
    checks['segment_shape'] &= (all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= cell < 16 for cell in row['spawned_cells']) and all(rank in (1, 2) for rank in row['spawned_ranks'])
        and all(math.isfinite(value) for value in row['chosen_values']))
    return {key: bool(value) for key, value in checks.items()}


def inspect_training(rows, source, life, representation, teacher):
    checks = dict(training_roster=True, training_seeds=True, exact_training_budget=True)
    cost = dict(segments=0, episodes_started=0, episodes_completed=0, seconds=0., statuses=Counter(),
        environment_counts=Counter(), model_counts=Counter(), teacher_counts=Counter())
    previous = None
    for row in rows:
        checks['training_roster'] &= (row['life'],row['representation'],row['teacher_query'],row['checkpoint']) == (life,representation,teacher,BUDGET)
        checks['training_seeds'] &= row['seed'] == train_seed(life, representation, teacher, row['episode'])
        for key, value in segment_checks(row, previous, source, representation, teacher).items():
            checks[key] = checks.get(key, True) and value
        cost['segments'] += 1; cost['episodes_started'] += row['start_step'] == 0
        cost['episodes_completed'] += row['status'] != 'ACTIVE'; cost['statuses'][row['status']] += 1
        cost['seconds'] += row['seconds']
        for key in ('environment_counts','model_counts','teacher_counts'): cost[key].update(row[key])
        checks['exact_training_budget'] &= row['cumulative_transitions'] == cost['environment_counts']['sampled_transitions'] <= BUDGET
        previous = row
    updates = BUDGET-cost['statuses']['WON']-cost['statuses']['CUTOFF']-int(previous['pending_after'] is not None)
    checks['exact_training_budget'] &= previous['cumulative_transitions'] == BUDGET and previous['updates_after'] == updates
    state = dict(transitions=BUDGET, episodes_started=cost['episodes_started'], episodes_completed=cost['episodes_completed'],
        episode=previous['episode'], step=previous['end_step'], board=previous['end_board'], pending=previous['pending_after'],
        environment_counts=dict(cost['environment_counts']))
    return dict(checks=checks, cost=cost, updates=updates, stream_state=state)


def control_valid(row, source, updates):
    result = row['result']; n = result['steps']; representation, teacher, method = row['representation'], row['teacher_query'], row['method']
    expected = (planning.expected_model_state(source, teacher, representation) if method == 'TEACHER' else
        component_state(representation, 0 if method == 'INITIAL_H2' else updates))
    options = row['action_values']; counts = result['policy_counts']
    checks = dict(control_trace=old.compact_valid(row) and row['seed'] == outer_seed(row['life'], row['replica'])
        and result['utility'] == utility(result['score'], result['status'], row['query'])
        and len(row['chosen_values']) == len(options) == n,
        evaluation_frozen=result['model_state_before'] == result['model_state_after'] == expected,
        greedy_actions=True, joint_readouts=True, control_counters=True, exact_initial_equivalence=True)
    if len(options) != n or len(row['chosen_values']) != n:
        checks['greedy_actions'] = False; return checks
    for i, actions in enumerate(options):
        finite = 0 < len(actions) <= 4 and all(all(math.isfinite(item[key]) for key in ('score','value','tail_value')) for item in actions.values())
        checks['greedy_actions'] &= finite
        if not finite: continue
        action = min(actions, key=lambda name: (-actions[name]['value'], name))
        checks['greedy_actions'] &= (row['actions'][i] == action and row['scores'][i] == actions[action]['score']
            and row['chosen_values'][i] == actions[action]['value'])
        if method != 'TEACHER':
            q = QUERIES[row['query']]
            for item in actions.values():
                reward, failure, success = item['consequences']
                checks['joint_readouts'] &= (all(math.isfinite(value) for value in (reward,failure,success))
                    and -1e-12 <= failure <= 1+1e-12 and -1e-12 <= success <= 1+1e-12
                    and math.isclose(failure+success, 1., rel_tol=0., abs_tol=1e-12)
                    and math.isclose(item['value'], item['score']/2048.+reward-q['failure_penalty']*failure+q['goal_bonus']*success,
                        rel_tol=0., abs_tol=1e-10))
    root_actions = sum(len(actions) for actions in options)
    if method == 'TEACHER':
        checks['control_counters'] &= planning.planning_counts_valid(counts, 'H2', representation, n, root_actions)
        zero = row['zero_equivalence']
        checks['exact_initial_equivalence'] &= (zero['exact'] is True
            and zero['before'] == zero['after'] == component_state(representation, 0)
            and joint_planning_counts_valid(zero['counts'], representation, n, root_actions))
    else:
        checks['control_counters'] &= joint_planning_counts_valid(counts, representation, n, root_actions)
    return {key: bool(value) for key, value in checks.items()}


def inspect_diagnostic(row, updates):
    diagnostic = row['diagnostic']; n = row['result']['steps']-int(row['result']['status'] == 'WON')
    representation, teacher = row['representation'], row['teacher_query']
    checks = dict(diagnostic_roster=all(set(diagnostic[key]) == {'INITIAL_H2','LEARNED_H2'} for key in ('predictions','counts','before','after')),
        diagnostic_frozen=True, diagnostic_predictions=True, diagnostic_counters=True)
    item = {key: row[key] for key in ('life','representation','teacher_query','replica')}
    targets = diagnostic_targets(row['scores'], row['result']['status'])
    for method, phase in (('INITIAL_H2','initial'), ('LEARNED_H2','learned')):
        predictions, counts = diagnostic['predictions'][method], diagnostic['counts'][method]
        checks['diagnostic_frozen'] &= diagnostic['before'][method] == diagnostic['after'][method] == component_state(representation, 0 if phase == 'initial' else updates)
        checks['diagnostic_predictions'] &= len(predictions) == n and all(math.isfinite(p['reward']) and math.isfinite(p['success']) and 0 <= p['success'] <= 1 for p in predictions)
        checks['diagnostic_counters'] &= (counts.get('value_calls') == counts.get('joint_predictions') == n
            and counts.get('choose_calls', 0) == 0 and component_counts_valid(counts, representation, 0))
        item[phase] = component_errors(predictions, targets, teacher)
    return checks, item


def teacher_loads_valid(loads, source, representation, teacher):
    return (loads['reference'] == source['leaves'][teacher][representation]
        and loads['parent']['load_counts'].get('checkpoint_loads') == 1
        and loads['leaf']['load_counts'].get('checkpoint_loads') == 1
        and loads['leaf']['setup_counts'].get('allocated_weight_parameters') == planning.previous.parameter_count(representation)
        and loads['leaf']['state'] == planning.expected_model_state(source, teacher, representation)
        and loads['teacher']['spawn_probabilities'] == planning.expected_spawn_probabilities(source))


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json','source_capsule.json','frozen_training.json'))
    sources = {source['life']: source for source in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES), representations=list(REPRESENTATIONS), teacher_queries=list(TEACHERS),
        queries=QUERIES, methods=list(METHODS), checkpoints=[0,BUDGET], transitions_per_teacher=BUDGET,
        replicas=REPLICAS, max_steps=MAX_STEPS, workers=4, alpha=.0025, initial_success=.5, p_four=.1,
        planner_spawn_law='frozen_identified_distribution', version_base=BASE, physical_control_games=1536, logical_control_rows=2304)
    checks = dict(frozen_settings=run['settings'] == settings, source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[key]) == 4 and {row['life'] for row in run[key]} == set(LIVES) for key in ('lifecycles','eval_lifecycles')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        all_training_frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings','lifecycles','inherited_costs')),
        learner_roster=True, teacher_immutable=True, model_loads=True, initialization=True, checkpoint_metadata=True,
        checkpoint_states=True, saved_work=True, control_roster=True, physical_logical_rosters=True)
    costs = dict(training=dict(segments=0, episodes_started=0, episodes_completed=0, seconds=0., statuses=Counter(),
        environment_counts=Counter(), model_counts=Counter(), teacher_counts=Counter()),
        control=old.new_cost(), control_by_cell={}, zero_equivalence_counts=Counter(),
        diagnostic_counts={method: Counter() for method in ('INITIAL_H2','LEARNED_H2')}, model_accounting=[])
    learners, trained, updates = [], {}, {}
    empty_stream = dict(transitions=0,episodes_started=0,episodes_completed=0,episode=-1,step=0,board=None,pending=None,environment_counts={})
    for lifecycle in run['lifecycles']:
        life = lifecycle['life']; source = sources[life]
        checks['learner_roster'] &= set(lifecycle['representations']) == set(REPRESENTATIONS)
        for representation, teachers in lifecycle['representations'].items():
            checks['learner_roster'] &= set(teachers) == set(TEACHERS)
            for teacher, data in teachers.items():
                key = (life,representation,teacher); trained[key] = data
                inspected = inspect_training(old.read_rows(directory/data['training_trace']), source, life, representation, teacher)
                for name, value in inspected['checks'].items(): checks[name] = checks.get(name, True) and value
                updates[key] = inspected['updates']; costs['model_accounting'].append(dict(phase='training',life=life,representation=representation,teacher_query=teacher,
                    loads=data['loads'], initialization=data['initialization'], checkpoints=data['checkpoints'], final_counts=data['final_counts']))
                parent_state = planning.previous.model_state(source, teacher, 'PARENT', 0)
                checks['teacher_immutable'] &= (data['parent_before'] == data['parent_after'] == parent_state
                    and data['teacher_before'] == data['teacher_after'] == planning.expected_model_state(source, teacher, representation))
                checks['model_loads'] &= teacher_loads_valid(data['loads'], source, representation, teacher)
                init = data['initialization']; head_size = planning.previous.parameter_count(representation)
                checks['initialization'] &= (init['state'] == component_state(representation, 0, False) and init['counts'] == {}
                    and init['setup_counts'].get('allocated_weight_parameters') == 2*head_size
                    and init['setup_counts'].get('source_parameters_copied') == head_size
                    and init['setup_counts'].get('source_weight_bytes_copied') == 8*head_size)
                checks['checkpoint_states'] &= [row['age'] for row in data['checkpoints']] == [0,BUDGET]
                saved = Counter()
                for checkpoint in data['checkpoints']:
                    age = checkpoint['age']; count = 0 if age == 0 else inspected['updates']
                    metadata = read(checkpoint['model_ref']+'.components.json')
                    checks['checkpoint_states'] &= (checkpoint['updates'] == count
                        and checkpoint['stream_state'] == (empty_stream if age == 0 else inspected['stream_state'])
                        and checkpoint['metadata']['parameter_count'] == 2*head_size)
                    checks['checkpoint_metadata'] &= (metadata['schema'] == 'acfqp.bellman_consequences.v136'
                        and metadata['representation'] == representation and metadata['teacher_query'] == QUERIES[teacher]
                        and metadata['teacher_updates'] == source['leaves'][teacher][representation]['updates']
                        and metadata['prior_success'] == .5 and metadata['alpha'] == .0025
                        and metadata['reward_intercept'] == reward_intercept(source, teacher)
                        and metadata['parameter_count'] == 2*head_size and metadata['updates'] == count)
                    checks['saved_work'] &= checkpoint['save_counts'].get('checkpoint_saves') == 1 and checkpoint['save_counts'].get('checkpoint_scanned_parameters') == 2*head_size
                    saved.update(checkpoint['save_counts'])
                checks['checkpoint_states'] &= (data['final_state'] == component_state(representation, inspected['updates']) and data['final_stream_state'] == inspected['stream_state'])
                checks['saved_work'] &= (Counter(data['final_counts']) == inspected['cost']['model_counts']+saved
                    and Counter(data['teacher_counts']) == inspected['cost']['teacher_counts'])
                learners.append(dict(life=life,representation=representation,teacher_query=teacher,**inspected))
                for name in ('segments','episodes_started','episodes_completed','seconds'): costs['training'][name] += inspected['cost'][name]
                for name in ('statuses','environment_counts','model_counts','teacher_counts'): costs['training'][name].update(inspected['cost'][name])
    indexed, valid, diagnostics = {}, {}, []
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]; seen = set(); teacher_totals = {}
        for row in old.read_rows(directory/lifecycle['control_trace']):
            rep, teacher, query, method, replica = (row[name] for name in ('representation','teacher_query','query','method','replica'))
            key = (life,rep,teacher,query,method,replica); checks['control_roster'] &= key not in seen and row['life'] == life; seen.add(key)
            row_checks = control_valid(row, source, updates[(life,rep,teacher)])
            for name, value in row_checks.items(): checks[name] = checks.get(name, True) and value
            indexed[key], valid[key] = dict(result=row['result']), all(row_checks.values())
            old.add_cost(costs['control'], row)
            cell = f'{rep}:{teacher}:{query}:{method}'; costs['control_by_cell'].setdefault(cell, old.new_cost())
            old.add_cost(costs['control_by_cell'][cell], row)
            if method == 'TEACHER':
                teacher_totals.setdefault((rep,teacher), Counter()).update(row['result']['policy_counts'])
                costs['zero_equivalence_counts'].update(row['zero_equivalence']['counts'])
                diagnostic_checks, diagnostic = inspect_diagnostic(row, updates[(life,rep,teacher)])
                for name, value in diagnostic_checks.items(): checks[name] = checks.get(name, True) and value
                diagnostics.append(diagnostic)
                for name, counts in row['diagnostic']['counts'].items(): costs['diagnostic_counts'][name].update(counts)
                for evaluation_query in evaluation_queries(teacher):
                    alias = (life,rep,teacher,evaluation_query,'TEACHER',replica)
                    result = dict(row['result'], utility=utility(row['result']['score'], row['result']['status'], evaluation_query))
                    indexed[alias], valid[alias] = dict(result=result), valid[key]
                alias = (life,rep,teacher,teacher,'INITIAL_H2',replica)
                indexed[alias], valid[alias] = indexed[key], valid[key]
        expected = {(life,rep,teacher,query,method,replica) for rep in REPRESENTATIONS for teacher in TEACHERS
            for query in evaluation_queries(teacher) for method in METHODS for replica in range(REPLICAS)
            if (method != 'TEACHER' or query == teacher) and (method != 'INITIAL_H2' or query != teacher)}
        checks['control_roster'] &= seen == expected and len(seen) == 384
        checks['learner_roster'] &= set(lifecycle['representations']) == set(REPRESENTATIONS)
        for rep, teachers in lifecycle['representations'].items():
            checks['learner_roster'] &= set(teachers) == set(TEACHERS)
            for teacher, data in teachers.items():
                key = (life,rep,teacher); parent_state = planning.previous.model_state(source,teacher,'PARENT',0)
                checks['teacher_immutable'] &= (data['parent_before'] == data['parent_after'] == parent_state
                    and data['teacher_before'] == data['teacher_after'] == planning.expected_model_state(source,teacher,rep)
                    and Counter(data['teacher_counts']) == teacher_totals[(rep,teacher)])
                checks['model_loads'] &= teacher_loads_valid(data['loads'], source, rep, teacher)
                loads = data['model_loads']; checks['model_loads'] &= len(loads) == 2 and {r['method'] for r in loads} == {'INITIAL_H2','LEARNED_H2'}
                for item in loads:
                    age, method = item['age'], item['method']; count = 0 if method == 'INITIAL_H2' else updates[key]
                    expected_checkpoint = trained[key]['checkpoints'][0 if method == 'INITIAL_H2' else 1]
                    checks['model_loads'] &= (item['model_ref'] == expected_checkpoint['model_ref'] and age == expected_checkpoint['age']
                        and item['state'] == data['final_model_states'][method] == component_state(rep,count)
                        and item['load_counts'].get('checkpoint_loads') == 1
                        and item['setup_counts'].get('allocated_weight_parameters') == parameter_count(rep))
                costs['model_accounting'].append(dict(phase='evaluation',life=life,representation=rep,teacher_query=teacher,**data))
    checks['physical_logical_rosters'] &= costs['control']['games'] == 1536 and len(indexed) == 2304 and len(diagnostics) == 256
    checks['equal_real_training_budgets'] = costs['training']['environment_counts']['sampled_transitions'] == 8388608
    costs['new_environment_samples'] = costs['training']['environment_counts']['sampled_transitions']+costs['control']['environment_counts']['sampled_transitions']
    work = costs['training']['model_counts']+costs['training']['teacher_counts']+costs['control']['policy_counts']+costs['zero_equivalence_counts']
    for counts in costs['diagnostic_counts'].values(): work.update(counts)
    costs['new_model_samples'] = sum(value for key,value in work.items() if key.endswith('model_spawn_samples'))
    costs['generated_model_outcomes'] = work.get('generated_spawn_outcomes',0)
    checks['no_stochastic_model_samples'] = costs['new_model_samples'] == 0
    control, calibration = full_game_comparison(indexed, valid), calibration_summary(diagnostics)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.bellman_consequences.v136.analysis',complete=complete,primary_complete=complete and control['complete'],
        checks={key:bool(value) for key,value in checks.items()},learners=learners,control=control,calibration=calibration,
        diagnostic_games=diagnostics,costs=costs,inherited_work=run['inherited_costs'],required_inputs=capsule['required_inputs'],
        seconds=run['seconds'],analysis_seconds=perf_counter()-started,
        scope='Retained fixed-teacher joint targets, component readouts, budgets, immutable evaluations and held-out teacher calibration are reconciled without resampling or weight replay. Teachers are never selected across queries; physical games are counted once before declared rescoring and exact initial aliases.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_bellman_consequences_v136')
    args=parser.parse_args(); result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=result['checks'])))
