"""Independent whole-episode finite-controller reconstruction and accounting."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import argparse
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_program_consolidation_v161 as prior
from scripts import analyze_controlled_predictive_feedback_program_v162 as frames
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal, _mean, _moments, _pool

LIVES = range(4)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
LEAVES = (*ACTIONS, 'H2')
MODES = ('H2', 'COND', 'LATCHED')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'COND-LATCHED': ('COND', 'LATCHED'), 'COND-H2': ('COND', 'H2'), 'LATCHED-H2': ('LATCHED', 'H2')}
NODE_FIELDS = ('probe_action', 'true_action', 'false_action', 'true_next', 'false_next')
MODULE_COUNTS = ('decisions', 'direct_decisions', 'h2_calls', 'explicit_h2_calls', 'illegal_fallbacks',
                 'live_predicate_changes', 'latch_divergences', 'control_transitions', 'node_switches')
BASE = 17000000000


def program_key(program):
    return tuple(node[field] for node in program['nodes'] for field in NODE_FIELDS)


def branch_seed(phase, life, episode, heldout=None):
    if phase == 'EVAL': return BASE+50000000+life*1000000+episode
    return BASE+{'G1':20000000, 'G2':30000000, 'FINAL':40000000}[phase]+heldout*1000000+life*100000+episode


def mutations(parents):
    children = deepcopy(parents)
    for parent in parents:
        for node in range(2):
            for field in NODE_FIELDS:
                choices = ACTIONS if field == 'probe_action' else LEAVES if field.endswith('action') else (0, 1)
                for value in choices:
                    if value == parent['nodes'][node][field]: continue
                    child = deepcopy(parent); child['nodes'][node][field] = value; children.append(child)
    return [dict(candidate_slot=i, program=program) for i, program in enumerate(children)]


def source_candidates(rows):
    cells = []
    for heldout in LIVES:
        counts = Counter(source_rows_examined=len(rows)); tables = {probe: {True: Counter(), False: Counter()} for probe in ACTIONS}; games = []
        for row in rows:
            if row['life'] == heldout or row['query'] != 'risk1': continue
            counts['source_games'] += 1; board = tuple(row['initial_board'])
            for step, action in enumerate(row['actions']):
                canonical, transform = frames.frame(board)
                label = prior.ground.transform_action_v1(prior.ground.Swipe2048Action(action), transform).value
                for probe in ACTIONS:
                    _, score, legal = prior.ground.swipe_board_v1(canonical, prior.ground.Swipe2048Action(probe))
                    tables[probe][bool(legal and score > 0)][label] += 1
                    counts.update(probe_checks=1, learned_swipe_calls=1, learned_line_rewrites=4)
                after, _, _ = prior.ground.swipe_board_v1(board, prior.ground.Swipe2048Action(action))
                board = list(after); board[row['spawned_cells'][step]] = row['spawned_ranks'][step]; board = tuple(board)
                counts.update(source_state_reconstructions=1, decision_windows=1, board_transforms=8, action_transports=1)
            games.append({key: row[key] for key in ('life', 'query', 'replica', 'seed')} | dict(steps=len(row['actions']), status=row['result']['status']))
        probe_tables = []
        for probe, branches in tables.items():
            ordered = {str(branch).lower(): [dict(action=action, count=n) for action, n in sorted(table.items(), key=lambda item: (-item[1], item[0]))] for branch, table in branches.items()}
            modal = {label: values[0]['action'] if values else 'H2' for label, values in ordered.items()}
            probe_tables.append(dict(probe_action=probe, occurrences=sum(sum(table.values()) for table in branches.values()),
                condition_counts={str(branch).lower(): sum(table.values()) for branch, table in branches.items()}, action_counts=ordered,
                modal_actions=modal, source_match_score=sum(max(table.values(), default=0) for table in branches.values())))
        probe_tables.sort(key=lambda table: (-table['source_match_score'], table['probe_action']))
        counts.update(probe_groups=4, observed_condition_branches=sum(bool(branch) for table in tables.values() for branch in table.values()))
        nodes = [dict(probe_action=table['probe_action'], true_action=table['modal_actions']['true'], false_action=table['modal_actions']['false'],
                      true_next=1-i, false_next=i) for i, table in enumerate(probe_tables[:2])]
        baseline = deepcopy(nodes)
        for node in baseline: node.update(true_action='H2', false_action='H2')
        issues = []
        histories = sorted({game['life'] for game in games})
        if histories != [life for life in LIVES if life != heldout]: issues.append('source_history_roster')
        for life in histories:
            selected = [game for game in games if game['life'] == life]
            if len(selected) != 4 or {game['replica'] for game in selected} != set(range(4)):
                if 'source_game_roster' not in issues: issues.append('source_game_roster')
        parents = [dict(nodes=nodes), dict(nodes=baseline)]
        if len({program_key(program) for program in parents}) != 2: issues.append('source_program_pool')
        cells.append(dict(heldout_life=heldout, query='risk1', training_lives=histories, source_games=games, counts=dict(counts),
                          probe_tables=probe_tables, parents=parents, complete=not issues, issues=issues))
    return cells


def generation_cells(sources, phase, previous=None):
    result = []
    for source in sources:
        parents = source['parents'] if phase == 'G1' else next(cell['selected_parents'] for cell in previous if cell['heldout_life'] == source['heldout_life'])
        slots = mutations(parents) if phase != 'FINAL' else [dict(candidate_slot=i, program=deepcopy(p)) for i, p in enumerate(parents)]
        result.append(dict(heldout_life=source['heldout_life'], query='risk1', phase=phase, parents=parents, slots=slots,
                           complete=source['complete'], issues=list(source['issues'])))
    return result


def _utility(vector): return vector[0]-vector[1]+vector[2]


def episode_pool(histories):
    result = _pool(histories,4)
    result['conditional_episode_se'] = result.pop('conditional_suffix_se')
    result['conditional_episode_ci95'] = result.pop('conditional_suffix_ci95')
    return result


def _terminal_valid(row, phase, life, episode, heldout):
    return row is not None and row['phase'] == phase and row['life'] == life and row['episode'] == episode and row['heldout_life'] == heldout and row['query'] == 'risk1' and row['seed'] == branch_seed(phase, life, episode, heldout) and row['status'] in ('WON', 'LOST') and _equal(row['components'], [row['score']/2048., float(row['status'] == 'LOST'), float(row['status'] == 'WON')]) and _equal(row['utility'], _utility(row['components']))


def select_parents(cells, outcomes):
    coordinates = lambda row: (row['heldout_life'], row['life'], row['episode'], row['mode'])
    index = {coordinates(row): row for row in outcomes}; counts = Counter(coordinates(row) for row in outcomes)
    result = []
    for cell in cells:
        heldout, phase = cell['heldout_life'], cell['phase']; histories = [life for life in LIVES if life != heldout]
        episodes = 4 if phase == 'FINAL' else 2; scores = []
        for slot in cell['slots']:
            per_history, complete = [], cell['complete']
            for life in histories:
                vectors = {mode: [] for mode in ('H2', 'COND', 'LATCHED')}
                for episode in range(episodes):
                    keys = [(heldout, life, episode, mode) for mode in ('H2', f"P{slot['candidate_slot']}_COND", f"P{slot['candidate_slot']}_LATCHED")]
                    rows = [index.get(key) for key in keys]
                    valid = all(counts[key] == 1 and _terminal_valid(row, phase, life, episode, heldout) for key, row in zip(keys, rows))
                    if valid:
                        for route, row in zip(('H2', 'COND', 'LATCHED'), rows):
                            valid &= row['route'] == route and row['arm'] == route and row['candidate_slot'] == (None if route == 'H2' else slot['candidate_slot']) and row['module']['program'] == (None if route == 'H2' else slot['program'])
                    if not valid: complete = False; continue
                    for mode, row in zip(vectors, rows): vectors[mode].append(row['components'])
                if len(vectors['COND']) != episodes: continue
                means = {mode: [_mean([v[k] for v in values]) for k in range(3)] for mode, values in vectors.items()}
                delta = [a-b for a, b in zip(means['COND'], means['H2'])]; latch_delta = [a-b for a, b in zip(means['COND'], means['LATCHED'])]
                per_history.append(dict(life=life, episodes=episodes, component_mean=means['COND'], utility=_utility(means['COND']),
                    component_delta_vs_H2=delta, gain=_utility(delta), latched_component_mean=means['LATCHED'], latched_utility=_utility(means['LATCHED']),
                    component_delta_vs_LATCHED=latch_delta, gain_vs_LATCHED=_utility(latch_delta)))
            def mean_field(field): return [_mean([history[field][k] for history in per_history]) for k in range(3)] if complete else None
            vector, delta, latched, latch_delta = [mean_field(field) for field in ('component_mean', 'component_delta_vs_H2', 'latched_component_mean', 'component_delta_vs_LATCHED')]
            scores.append(dict(candidate_slot=slot['candidate_slot'], program=deepcopy(slot['program']), complete=complete,
                train_component_mean=vector, train_utility=None if vector is None else _utility(vector), train_component_delta_vs_H2=delta,
                train_gain=None if delta is None else _utility(delta), latched_component_mean=latched, latched_utility=None if latched is None else _utility(latched),
                train_component_delta_vs_LATCHED=latch_delta, train_gain_vs_LATCHED=None if latch_delta is None else _utility(latch_delta),
                per_history=per_history))
        complete = cell['complete'] and bool(scores) and all(score['complete'] for score in scores); selected = []
        if complete:
            for score in sorted(scores, key=lambda row: (-row['train_utility'], program_key(row['program']), row['candidate_slot'])):
                if program_key(score['program']) not in {program_key(row['program']) for row in selected}: selected.append(score)
                if len(selected) == (1 if phase == 'FINAL' else 2): break
        result.append({**{key:value for key, value in cell.items() if key != 'issues'}, 'slot_scores': scores, 'complete': complete,
                       'selection_basis':'whole_episode_conditional_utility', 'selected_parents':[row['program'] for row in selected],
                       'selected_slots':[row['candidate_slot'] for row in selected]})
    return result


def expected_roster(cells, phase):
    result = []; by_fold = {cell['heldout_life']:cell for cell in cells}
    for life in LIVES:
        for heldout in ([life] if phase == 'EVAL' else [fold for fold in LIVES if fold != life]):
            cell = by_fold[heldout]
            for episode in range(32 if phase == 'EVAL' else 4 if phase == 'FINAL' else 2):
                alternatives = [('H2','H2',None,None)]
                if phase == 'EVAL': alternatives.extend((route,route,None,cell['selected_parents'][0]) for route in ('COND','LATCHED'))
                else: alternatives.extend((f"P{slot['candidate_slot']}_{route}", route, slot['candidate_slot'], slot['program']) for slot in cell['slots'] for route in ('COND','LATCHED'))
                for mode, route, slot, program in alternatives:
                    result.append(dict(branch_id=f'{phase}:{life}:fold{heldout}:{episode}:{mode}', phase=phase, life=life,
                        heldout_life=heldout, query='risk1', episode=episode, route=route, mode=mode, arm=route, candidate_slot=slot,
                        seed=branch_seed(phase,life,episode,heldout), program=deepcopy(program)))
    return result


def eval_summary(outcomes):
    index = {(row['life'],row['episode'],row['mode']):row for row in outcomes}; counts = Counter((row['life'],row['episode'],row['mode']) for row in outcomes)
    cohort = not (set(index)-{(life,episode,mode) for life in LIVES for episode in range(32) for mode in MODES})
    episode_rows, histories = [], {label:[] for label in CONTRASTS}
    for life in LIVES:
        paired = {label:{metric:[] for metric in METRICS} for label in CONTRASTS}
        for episode in range(32):
            rows = {mode:index.get((life,episode,mode)) for mode in MODES}
            valid = cohort and all(counts[life,episode,mode] == 1 and _terminal_valid(row,'EVAL',life,episode,life) for mode,row in rows.items())
            if valid:
                valid = all(row['route'] == mode and row['arm'] == mode and row['candidate_slot'] is None and row['module']['arm'] == mode for mode,row in rows.items())
                valid = valid and rows['H2']['module']['program'] is None and rows['COND']['module']['program'] == rows['LATCHED']['module']['program']
            deltas = {label:[a-b for a,b in zip(rows[left]['components'],rows[right]['components'])] if valid else None for label,(left,right) in CONTRASTS.items()}
            episode_rows.append(dict(life=life,episode=episode,complete=valid,seed=branch_seed('EVAL',life,episode),component_deltas=deltas))
            for label,delta in deltas.items():
                for metric,value in zip(METRICS,[_utility(delta),*delta] if valid else [None]*4): paired[label][metric].append(value)
        for label in CONTRASTS: histories[label].append(dict(life=life,episodes=32,metrics={metric:_moments(values) for metric,values in paired[label].items()}))
    comparisons = []
    for label in CONTRASTS:
        metrics = {metric:episode_pool([history['metrics'][metric] for history in histories[label]]) for metric in METRICS}
        comparisons.append(dict(query='risk1',contrast=label,episodes=128,complete=all(value['complete'] for value in metrics.values()),metrics=metrics,per_history=histories[label]))
    diagnostics = []
    for mode in MODES:
        rows = [index[life,episode,mode] for life in LIVES for episode in range(32) if (life,episode,mode) in index]
        module_counts = {key:sum(row['module'][key] for row in rows) for key in MODULE_COUNTS}; steps = sum(row['steps'] for row in rows)
        diagnostics.append(dict(mode=mode,episodes=128,present_episodes=len(rows),terminal_episodes=sum(row['status'] in ('WON','LOST') for row in rows),
            steps_sum=sum(row['steps'] for row in rows),module_counts=module_counts,node_visits=[sum(row['module']['node_visits'][i] for row in rows) for i in range(2)],
            direct_decision_fraction=module_counts['direct_decisions']/steps if steps else None, teacher_call_fraction=module_counts['h2_calls']/steps if steps else None,
            episodes_with_repeated_node_visits=sum(any(visits>1 for visits in row['module']['node_visits']) for row in rows),
            episodes_with_live_predicate_changes=sum(row['module']['live_predicate_changes']>0 for row in rows),episodes_with_latch_divergences=sum(row['module']['latch_divergences']>0 for row in rows)))
    return dict(episode_rows=episode_rows,comparisons=comparisons,program_diagnostics=diagnostics,complete=all(row['complete'] for row in comparisons))


def replay_episode(row, max_steps=8192):
    """Recompute current-board probes, graph edges, latch bits and all spawns."""
    result, program, arm = row['result'], row['module']['program'], row['arm']
    n, query = result['steps'], row['query']
    checks = dict(episode_arrays=n>0 and all(len(row[key]) == n for key in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        episode_settings=row['max_steps'] == max_steps and row['p_four'] == .1 and query == 'risk1', initial_rng=True,
        controller_grammar=(arm == 'H2') == (program is None) and arm in MODES,
        controller_decisions=True, controller_work=True, controller_module=True, teacher_choices=True,
        actions=True, rng=True, terminal=True, returns=True, environment=True, policy_totals=True,
        no_learning=not any(result['learning_counts'].values()), seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'])
    if not checks['episode_arrays']: return checks, 0
    rng, board = random.Random(row['seed']), [0]*16
    for spawn in row['initial_spawns']:
        empty = [i for i,value in enumerate(board) if not value]; cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['initial_rng'] &= spawn == dict(cell=cell,rank=rank); board[cell] = rank
    checks['initial_rng'] &= len(row['initial_spawns']) == 2 and board == row['initial_board']
    status, exits, swipes = prior.prior.previous.legal_exits(tuple(board)); replayed = swipes
    environment = Counter(initial_spawns=2,environment_random_draws=4,ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    module = dict(program=program,arm=arm,current_node=0,node_visits=[0,0],latches=[None,None],last_predicates=[None,None],**{key:0 for key in MODULE_COUNTS})
    policy, teacher_totals, score_total = Counter(), {q:Counter() for q in ('risk1','risk8')}, 0
    for step, choice in enumerate(row['choices']):
        work, decision, direct, next_node = Counter(), None, False, None
        if program is not None:
            node_index = module['current_node']; node = program['nodes'][node_index]
            canonical, transform = frames.frame(board); probe = frames.transport(transform,[node['probe_action']])[0]
            after_probe, score_probe, legal_probe = prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(probe)); replayed += 1
            predicate = bool(legal_probe and score_probe>0); latch_before = module['latches'][node_index]
            used = predicate if arm == 'COND' or latch_before is None else latch_before
            if arm == 'LATCHED' and latch_before is None: module['latches'][node_index] = predicate
            leaf = node['true_action' if used else 'false_action']; next_node = node['true_next' if used else 'false_next']
            attempt, fallback = None, False
            work.update(program_decisions=1,program_board_transforms=8,program_action_transports=1,program_probe_checks=1,
                        probe_learned_swipe_calls=1,probe_learned_line_rewrites=4)
            module['decisions'] += 1; module['node_visits'][node_index] += 1
            previous = module['last_predicates'][node_index]
            module['live_predicate_changes'] += previous is not None and previous is not predicate
            module['last_predicates'][node_index] = predicate; module['latch_divergences'] += used is not predicate
            if leaf != 'H2':
                action = frames.transport(transform,[leaf])[0]
                after, score, legal = prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(action)); replayed += 1
                attempt = dict(action=action,afterstate=list(after),score=score,legal=bool(legal)); direct, fallback = bool(legal), not legal
                work.update(program_action_transports=1,program_action_checks=1,program_learned_swipe_calls=1,program_learned_line_rewrites=4)
                module['illegal_fallbacks'] += fallback
            else: module['explicit_h2_calls'] += 1
            decision = dict(node=node_index,canonical_board=list(canonical),transform=transform.value,probe_action=probe,
                probe_afterstate=list(after_probe),probe_score=score_probe,probe_legal=bool(legal_probe),current_predicate=predicate,
                used_predicate=used,latch_before=latch_before,latch_after=module['latches'][node_index],leaf=leaf,
                actual_action_attempt=attempt,next_node=next_node,fallback=bool(fallback))
        expected_phase, expected_policy = ('program','PROGRAM') if direct else ('teacher',query)
        if direct:
            module['direct_decisions'] += 1
            checks['actions'] &= choice['action'] == attempt['action'] and choice['afterstate'] == attempt['afterstate'] and choice['score'] == attempt['score']
        else:
            module['h2_calls'] += 1
            actual_work = Counter(choice['work']); native = {key[len(f'policy_{query}_'):]:value for key,value in actual_work.items() if key.startswith(f'policy_{query}_')}
            work.update(forced_decisions=1); work.update({f'policy_{query}_{key}':value for key,value in native.items()})
            checks['teacher_choices'] &= prior.prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.prior.local.compact_choice_valid(choice,exits,query)
            prior.add_checks(checks,prior.prior.h1.root_choice_checks(board,choice,query)); replayed += 4
        checks['controller_decisions'] &= choice['step'] == step and choice['phase'] == expected_phase and choice['policy_key'] == expected_policy and choice['program_decision'] == decision
        checks['controller_work'] &= Counter(choice['work']) == work
        policy.update(choice['work']); prior.prior.add_policy_work(teacher_totals,choice['work'])
        action = choice['action']; checks['actions'] &= status == 'ACTIVE' and action in exits and row['actions'][step] == action
        if action not in exits: return checks,replayed
        after, score = exits[action]; score_total += score; checks['actions'] &= row['scores'][step] == score
        empty = [i for i,value in enumerate(after) if not value]; cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step]) == (cell,rank)
        board = list(after); board[cell] = rank
        status,exits,swipes = prior.prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
                           ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
        if program is not None:
            module['node_switches'] += next_node != module['current_node']; module['current_node'] = next_node; module['control_transitions'] += 1
    final = 'CUTOFF' if status == 'ACTIVE' else status; vector = [score_total/2048.,float(final == 'LOST'),float(final == 'WON')]
    checks['controller_module'] &= row['module'] == module
    checks['terminal'] &= row['final_board'] == board and result['status'] == final and n <= max_steps and (final != 'CUTOFF' or n == max_steps)
    checks['returns'] &= result['score'] == score_total and result['components'] == vector and result['utility'] == (None if final == 'CUTOFF' else _utility(vector))
    checks['environment'] &= Counter(result['environment_counts']) == environment
    checks['policy_totals'] &= Counter(result['policy_counts']) == policy and Counter(result['program_setup_counts']) == Counter() and set(result['policy_counts_by_query']) == set(teacher_totals) and all(Counter(result['policy_counts_by_query'][q]) == teacher_totals[q] for q in teacher_totals)
    return checks,replayed


def replay_lifecycle(task):
    directory,phase,lifecycle,source,plans = task; directory = Path(directory)
    life,cost,checks = lifecycle['life'],prior.new_cost(),{}; source_phase = phase == 'SOURCE'
    plans = {plan['branch_id']:plan for plan in plans}; totals = {q:Counter() for q in ('risk1','risk8')}
    compact = [] if source_phase else json.loads((directory/lifecycle['outcomes_ref']).read_text())
    compact_index = {row['branch_id']:row for row in compact}; observed,rows = [],[]
    route_costs = {route:prior.new_cost() for route in (('SOURCE',) if source_phase else MODES)}
    trace = lifecycle['source_trace'] if source_phase else lifecycle['branch_trace']
    for row in prior.prior.old.read_rows(directory/trace):
        if source_phase:
            local,swipes,_ = prior.prior.replay_game(row,{})
            local['source_identity'] = _equal(row,dict(phase='SOURCE',life=life,query='risk1',replica=row['replica'],source_id=f'SOURCE:{life}:risk1:{row["replica"]}',method='H2',duration=0,max_steps=8192,seed=BASE+10000000+life*1000000+row['replica']))
            prior.prior.add_policy_work(totals,row['result']['policy_counts']); observed.append(row['replica']); rows.append(row)
            route,physical_key = 'SOURCE','physical_games'
        else:
            local,swipes = replay_episode(row); observed.append(row['branch_id']); plan = plans.get(row['branch_id'])
            expected = {key:value for key,value in (plan or {}).items() if key != 'program'}
            local['frozen_episode_identity'] = plan is not None and _equal(row,expected)
            local['frozen_controller'] = plan is not None and row['module']['program'] == plan['program']
            expected.update({key:row['result'][key] for key in ('score','steps','status','components','utility')},module=row['module'])
            local['compact_matches_trace'] = _equal(compact_index.get(row['branch_id']),expected)
            for q in totals: totals[q].update(row['result']['policy_counts_by_query'][q])
            route,physical_key = row['route'],'physical_branches'
        prior.add_checks(checks,local); prior.add_cost(cost,row['result'],physical_key); cost['analysis_replay_swipes'] += swipes
        prior.add_cost(route_costs[route],row['result'],physical_key); route_costs[route]['analysis_replay_swipes'] += swipes
    prior.add_checks(checks,prior.teacher_checks(lifecycle,source,totals))
    if source_phase: checks['four_source_games'] = sorted(observed) == list(range(4))
    else:
        checks['readonly_rule'] = lifecycle['rule_before'] == lifecycle['rule_after'] == source['rule']
        checks['physical_episode_roster'] = len(observed) == len(plans) and len(set(observed)) == len(plans) and set(observed) == set(plans)
        checks['compact_episode_roster'] = len(compact) == len(plans) and len(compact_index) == len(plans) and set(compact_index) == set(plans)
    for key in (('physical_games',) if source_phase else ('physical_branches','program_setup_counts'))+('environment_counts','policy_counts','statuses'):
        checks['cost:'+key] = _equal(lifecycle[key],dict(cost[key]) if isinstance(cost[key],Counter) else cost[key])
    return dict(phase=phase,life=life,checks=checks,costs=cost,route_costs=route_costs,source_rows=rows)


def analyze(directory):
    started = perf_counter(); read = lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen = [read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json')]
    checks,phase_results,sources,selections,selection_history = [],{},None,None,{}
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    check('execution_settings_frozen',frozen['status'] == 'frozen' and frozen['settings'] == run['settings'])
    check('frozen_physical_budget',_equal(run['settings'],dict(lifecycles=list(LIVES),queries=['risk1'],source_replicas=4,source_games=16,
        control_nodes=2,initial_node=0,generations=2,beam=2,candidate_slots=54,generation_episodes_per_history=2,
        final_episodes_per_history=4,eval_episodes_per_history=32,generation_games=5232,final_games=240,evaluation_games=384,controlled_games=5856,total_games=5872,
        maximum_environment_transitions=48103424,max_steps=8192,p_four=.1,workers=4,version_base=BASE,new_parameter_updates=0)))
    source_roster = [dict(phase='SOURCE',life=life,query='risk1',replica=replica,seed=BASE+10000000+life*1000000+replica) for life in LIVES for replica in range(4)]
    check('frozen_source_roster',frozen['source_roster'] == source_roster)
    inherited = json.loads(Path(capsule['source_analysis_ref']).read_text()); inherited_capsule = json.loads((Path(capsule['source_analysis_ref']).parent/'source_capsule.json').read_text())
    check('inherited_audited_capsule',inherited['valid'] and inherited['primary_complete'] and capsule['snapshots'] == inherited_capsule['snapshots'] and capsule['inherited_v169_environment_samples'] == inherited['costs']['new_environment_samples'])
    full_order = ['INPUTS_FROZEN','SOURCE','G1','G1_SELECTED','G2','G2_SELECTED','FINAL','PROGRAMS_FROZEN','EVAL']
    check('declared_phase_sequence',run['phase_order'] == full_order[:len(run['phase_order'])])
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('SOURCE','G1','G2','FINAL','EVAL'):
            if phase not in run['phases']: continue
            if phase == 'SOURCE': plans = []
            else:
                inputs = read(f'inputs_{phase.lower()}.json')
                if phase == 'EVAL':
                    cells = selections; check('frozen_final_controllers',_equal(read('frozen_programs.json'),cells))
                else: cells = generation_cells(sources,phase,selections)
                plans = expected_roster(cells,phase)
                check(f'{phase}:frozen_candidate_cells',_equal(inputs['cells'],cells)); check(f'{phase}:frozen_physical_roster',inputs['branch_roster'] == plans)
            lifecycles = run['phases'][phase]['lifecycles']; check(f'{phase}:four_lifecycles',len(lifecycles) == 4 and [row['life'] for row in lifecycles] == list(LIVES))
            results = list(pool.map(replay_lifecycle,[(str(directory),phase,lifecycle,capsule['snapshots'][lifecycle['life']],[plan for plan in plans if plan['life'] == lifecycle['life']]) for lifecycle in lifecycles])); phase_results[phase] = results
            for result in results:
                for name,value in result['checks'].items(): check(f'{phase}:life{result["life"]}:{name}',value)
            if phase == 'SOURCE':
                sources = source_candidates([row for result in results for row in result['source_rows']]); check('independent_source_candidates',_equal(read('source_candidates.json'),sources))
            elif phase in ('G1','G2','FINAL'):
                selections = select_parents(cells,[row for lifecycle in lifecycles for row in read(lifecycle['outcomes_ref'])]); selection_history[phase] = read(f'selections_{phase.lower()}.json')
                check(f'{phase}:independent_selection',_equal(selection_history[phase],selections))
            print(json.dumps(dict(audited_phase=phase,lifecycles=len(results))),flush=True)
    training_complete = selections is not None and selections[0]['phase'] == 'FINAL' and all(cell['complete'] for cell in selections)
    check('incomplete_training_stops_eval',training_complete or 'EVAL' not in run['phases'])
    if not training_complete: check('incomplete_programs_not_frozen','PROGRAMS_FROZEN' not in run['phase_order'] and not (directory/'frozen_programs.json').exists())
    expected = None
    if 'EVAL' in phase_results:
        expected = eval_summary([row for lifecycle in run['phases']['EVAL']['lifecycles'] for row in read(lifecycle['outcomes_ref'])]); check('independent_eval_statistics',_equal(read('summary.json'),expected))
    all_results = [row for results in phase_results.values() for row in results]; costs = prior.aggregate_costs([row['costs'] for row in all_results])
    costs.update(new_parameter_updates=0,physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in results]) for phase,results in phase_results.items()},
        route_costs={route:prior.aggregate_costs([row['route_costs'][route] for row in all_results if route in row['route_costs']]) for route in ('SOURCE',*MODES)},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        generation_counts=dict(sum((Counter(cell['counts']) for cell in sources or []),Counter())),
        selection_logical_work={phase:dict(sum((Counter(cell['logical_work']) for cell in cells),Counter())) for phase,cells in selection_history.items()},
        generation_seconds=run['generation_seconds'],selection_seconds=run.get('selection_seconds',{}),
        inherited_v169_environment_samples=capsule['inherited_v169_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'])
    check('physical_transition_cap',costs['new_environment_samples'] <= 48103424)
    if run['status'] == 'complete':
        check('complete_physical_roster',costs['physical_games'] == 16 and costs['physical_branches'] == 5856); check('completed_phase_sequence',run['phase_order'] == full_order)
    check('declared_run_status',run['status'] == ('complete' if 'EVAL' in phase_results else 'incomplete_training'))
    valid = all(item['passed'] for item in checks)
    result = dict(schema='acfqp.persistent_strategy.v170.analysis',valid=valid,complete=valid,primary_complete=expected is not None and expected['complete'],training_complete=training_complete,
        checks=checks,passed_checks=sum(item['passed'] for item in checks),total_checks=len(checks),comparisons=[] if expected is None else expected['comparisons'],
        costs=costs,inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_persistent_strategy_v170')
    result = analyze(parser.parse_args().directory); print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__': main()
