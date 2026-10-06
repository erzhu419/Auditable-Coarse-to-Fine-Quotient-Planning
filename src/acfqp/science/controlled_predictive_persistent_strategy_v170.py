"""Generate and execute persistent two-node whole-game feedback strategies."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_policy_modules_v151 import QUERIES, counter_delta, utility
from .controlled_predictive_program_consolidation_v161 import CHOICE_KEYS, INVERSE, canonical_frame
from .controlled_predictive_consequence_generation_v168 import (
    _issue, _mean, _vector_mean, _terminal_issues, _moments, _pool)

LIVES = (0, 1, 2, 3)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
LEAVES = ACTIONS+('H2',)
NODE_FIELDS = ('probe_action', 'true_action', 'false_action', 'true_next', 'false_next')
BASE = 17000000000
PHASE_EPISODES = dict(G1=2, G2=2, FINAL=4)
MODES = ('H2', 'COND', 'LATCHED')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'COND-LATCHED': ('COND', 'LATCHED'), 'COND-H2': ('COND', 'H2'),
             'LATCHED-H2': ('LATCHED', 'H2')}
MODULE_COUNTS = ('decisions', 'direct_decisions', 'h2_calls', 'explicit_h2_calls',
                 'illegal_fallbacks', 'live_predicate_changes', 'latch_divergences',
                 'control_transitions', 'node_switches')


def program_key(program):
    return tuple(node[field] for node in program['nodes'] for field in NODE_FIELDS)


def _valid_program(program):
    return len(program['nodes']) == 2 and all(
        node['probe_action'] in ACTIONS and node['true_action'] in LEAVES and
        node['false_action'] in LEAVES and node['true_next'] in (0, 1) and node['false_next'] in (0, 1)
        for node in program['nodes'])


def mutate(parents):
    """Keep both parents and all 52 substitutions, including duplicate slots."""
    if len(parents) != 2 or len({program_key(parent) for parent in parents}) != 2 or any(not _valid_program(parent) for parent in parents):
        raise ValueError('two distinct two-node strategies required')
    candidates = deepcopy(parents)
    for parent in parents:
        for node in range(2):
            for field in NODE_FIELDS:
                alternatives = ACTIONS if field == 'probe_action' else LEAVES if field.endswith('_action') else (0, 1)
                for alternative in alternatives:
                    if alternative == parent['nodes'][node][field]:
                        continue
                    child = deepcopy(parent)
                    child['nodes'][node][field] = alternative
                    candidates.append(child)
    return [dict(candidate_slot=slot, program=program) for slot, program in enumerate(candidates)]


def source_candidates(source_rows, rules_by_life, heldout):
    """Count source actions under current-board canonical probe observations."""
    counts, games = Counter(), []
    tables = {probe: {True: Counter(), False: Counter()} for probe in ACTIONS}
    for row in source_rows:
        counts['source_rows_examined'] += 1
        if row['life'] == heldout or row['query'] != 'risk1':
            continue
        rule = rules_by_life[row['life']]
        board = tuple(row['initial_board'])
        counts['source_games'] += 1
        for action, choice, cell, rank in zip(row['actions'], row['choices'], row['spawned_cells'], row['spawned_ranks'], strict=True):
            canonical, frame = canonical_frame(board)
            canonical_action = ground.transform_action_v1(ground.Swipe2048Action(action), D4Transform(frame)).value
            counts.update(decision_windows=1, board_transforms=8, action_transports=1)
            for probe in ACTIONS:
                native = Counter()
                _, score, legal = rule.swipe(canonical, probe, native)
                tables[probe][bool(legal and score > 0)][canonical_action] += 1
                counts['probe_checks'] += 1
                counts.update(native)
            board = list(choice['afterstate'])
            board[cell] = rank
            board = tuple(board)
            counts['source_state_reconstructions'] += 1
        games.append(dict(life=row['life'], query='risk1', replica=row['replica'], seed=row['seed'],
                          steps=len(row['actions']), status=row['result']['status']))
    probe_tables = []
    for probe in ACTIONS:
        branches = {name: sorted([dict(action=action, count=count) for action, count in tables[probe][value].items()],
                                key=lambda row: (-row['count'], row['action']))
                    for name, value in (('true', True), ('false', False))}
        condition_counts = {name: sum(row['count'] for row in rows) for name, rows in branches.items()}
        modal = {name: rows[0]['action'] if rows else 'H2' for name, rows in branches.items()}
        probe_tables.append(dict(probe_action=probe, occurrences=sum(condition_counts.values()),
            condition_counts=condition_counts, action_counts=branches, modal_actions=modal,
            source_match_score=sum(rows[0]['count'] if rows else 0 for rows in branches.values())))
    probe_tables.sort(key=lambda row: (-row['source_match_score'], row['probe_action']))
    counts.update(probe_groups=4, observed_condition_branches=sum(bool(rows) for probe in probe_tables for rows in probe['action_counts'].values()))
    seed = dict(nodes=[dict(probe_action=row['probe_action'], true_action=row['modal_actions']['true'],
                            false_action=row['modal_actions']['false'], true_next=1-node, false_next=node)
                       for node, row in enumerate(probe_tables[:2])])
    incumbent = deepcopy(seed)
    for node in incumbent['nodes']:
        node.update(true_action='H2', false_action='H2')
    histories, issues = sorted({row['life'] for row in games}), []
    if histories != [life for life in LIVES if life != heldout]:
        _issue(issues, 'source_history_roster')
    for life in LIVES:
        if life == heldout:
            continue
        roster = [row for row in games if row['life'] == life]
        if len(roster) != 4 or {row['replica'] for row in roster} != set(range(4)):
            _issue(issues, 'source_game_roster')
    if len({program_key(seed), program_key(incumbent)}) != 2:
        _issue(issues, 'source_program_pool')
    return dict(heldout_life=heldout, query='risk1', training_lives=histories,
                source_games=games, counts=dict(counts), probe_tables=probe_tables,
                parents=[seed, incumbent], complete=not issues, issues=issues)


def episode_seed(phase, life, episode, heldout_life=None):
    if phase == 'SOURCE':
        return BASE+10000000+life*1000000+episode
    if phase == 'EVAL':
        return BASE+50000000+life*1000000+episode
    return BASE+dict(G1=20000000, G2=30000000, FINAL=40000000)[phase]+heldout_life*1000000+life*100000+episode


def run_episode(bank, rule, target_query, program, arm, seed, max_steps=8192, p_four=.1):
    """Observe and select a graph leaf at every decision until the game ends."""
    if target_query not in QUERIES:
        raise ValueError('unknown query')
    if arm not in MODES or (arm == 'H2') != (program is None) or (program is not None and not _valid_program(program)):
        raise ValueError('H2 requires no program; strategy arms require two valid nodes')
    if not 0 < max_steps <= 8192 or not 0 <= p_four <= 1:
        raise ValueError('invalid episode sampling limits')
    started = perf_counter()
    rng, environment, policy_counts = random.Random(seed), Counter(), Counter()
    board, initial_spawns = (0,)*16, []
    for _ in range(2):
        board, cell, rank = _spawn(board, rng, environment, p_four)
        initial_spawns.append(dict(cell=cell, rank=rank))
        environment['initial_spawns'] += 1
    initial_board = board
    status = _status(board, environment)
    module = dict(program=deepcopy(program), arm=arm, current_node=0,
                  node_visits=[0, 0], latches=[None, None], last_predicates=[None, None],
                  **{key: 0 for key in MODULE_COUNTS})
    before_bank = {query: dict(bank[query].counts) for query in QUERIES}
    actions, cells, ranks, scores, choices = [], [], [], [], []
    decision_seconds = 0.
    for step in range(max_steps):
        decision_started, work, decision = perf_counter(), Counter(), None
        choice, phase, policy_key = None, 'teacher', target_query
        if program is not None:
            node_index = module['current_node']
            node = program['nodes'][node_index]
            canonical, frame = canonical_frame(board)
            inverse = INVERSE[D4Transform(frame)]
            actual_probe = ground.transform_action_v1(ground.Swipe2048Action(node['probe_action']), inverse).value
            work.update(program_decisions=1, program_board_transforms=8, program_action_transports=1, program_probe_checks=1)
            native = Counter()
            probe_after, probe_score, probe_legal = rule.swipe(board, actual_probe, native)
            work.update({f'probe_{key}': value for key, value in native.items()})
            current = bool(probe_legal and probe_score > 0)
            latch_before = module['latches'][node_index]
            if arm == 'LATCHED' and latch_before is None:
                module['latches'][node_index] = current
            used = current if arm == 'COND' else module['latches'][node_index]
            previous = module['last_predicates'][node_index]
            module['live_predicate_changes'] += previous is not None and current is not previous
            module['last_predicates'][node_index] = current
            module['latch_divergences'] += current is not used
            module['node_visits'][node_index] += 1
            module['decisions'] += 1
            leaf = node['true_action' if used else 'false_action']
            next_node = node['true_next' if used else 'false_next']
            attempt, fallback = None, False
            if leaf == 'H2':
                module['explicit_h2_calls'] += 1
            else:
                action = ground.transform_action_v1(ground.Swipe2048Action(leaf), inverse).value
                work['program_action_transports'] += 1
                native = Counter()
                after, score, legal = rule.swipe(board, action, native)
                work['program_action_checks'] += 1
                work.update({f'program_{key}': value for key, value in native.items()})
                attempt = dict(action=action, afterstate=list(after), score=score, legal=bool(legal))
                if legal:
                    choice = dict(action=action, afterstate=list(after), score=score)
                    phase, policy_key = 'program', 'PROGRAM'
                    module['direct_decisions'] += 1
                else:
                    fallback = True
                    module['illegal_fallbacks'] += 1
            module['current_node'] = next_node
            module['control_transitions'] += 1
            module['node_switches'] += next_node != node_index
            decision = dict(node=node_index, canonical_board=list(canonical), transform=frame,
                            probe_action=actual_probe, probe_afterstate=list(probe_after),
                            probe_score=probe_score, probe_legal=bool(probe_legal),
                            current_predicate=current, used_predicate=used,
                            latch_before=latch_before, latch_after=module['latches'][node_index],
                            leaf=leaf, actual_action_attempt=attempt, next_node=next_node, fallback=fallback)
        if choice is None:
            before = dict(bank[target_query].counts)
            choice = bank[target_query].choose(board, QUERIES[target_query])
            work['forced_decisions'] += 1
            work.update({f'policy_{target_query}_{key}': value
                         for key, value in counter_delta(bank[target_query].counts, before).items()})
            module['h2_calls'] += 1
        decision_seconds += perf_counter()-decision_started
        policy_counts.update(work)
        compact = {key: deepcopy(choice[key]) for key in CHOICE_KEYS if key in choice}
        compact.update(step=step, phase=phase, policy_key=policy_key,
                       program_decision=decision, work=dict(work))
        action = ground.Swipe2048Action(choice['action'])
        environment.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
        after, score, legal = ground.swipe_board_v1(board, action)
        if not legal:
            raise ValueError(f'illegal executed action {action.value} at step {step}')
        board, cell, rank = _spawn(after, rng, environment, p_four)
        environment['sampled_transitions'] += 1
        status = _status(board, environment)
        actions.append(action.value); cells.append(cell); ranks.append(rank); scores.append(score); choices.append(compact)
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
                  utility=None if status == 'CUTOFF' else utility(components, target_query),
                  environment_counts=dict(environment), policy_counts=dict(policy_counts),
                  policy_counts_by_query={query: counter_delta(bank[query].counts, before_bank[query]) for query in QUERIES},
                  program_setup_counts={}, learning_counts={}, decision_seconds=decision_seconds,
                  seconds=perf_counter()-started)
    return dict(seed=seed, query=target_query, arm=arm, max_steps=max_steps, p_four=p_four,
                initial_board=list(initial_board), initial_spawns=initial_spawns,
                actions=actions, spawned_cells=cells, spawned_ranks=ranks, scores=scores,
                choices=choices, final_board=list(board), module=module, result=result)


def _metadata_issues(row, phase, life, heldout, episode, mode, slot, route, program):
    if row is None:
        return []
    expected = dict(phase=phase, life=life, heldout_life=heldout, episode=episode,
                    query='risk1', mode=mode, candidate_slot=slot, route=route, arm=route)
    issues = []
    if any(row.get(key) != value for key, value in expected.items()):
        _issue(issues, 'outcome_metadata_mismatch')
    if row['module']['program'] != program or row['module']['arm'] != route:
        _issue(issues, 'executable_program_mismatch')
    return issues


def choose_parents(cells, outcomes, phase):
    """Rank physically measured full-game COND outcomes, retaining every slot."""
    episodes = PHASE_EPISODES[phase]
    index, duplicates = {}, set()
    for row in outcomes:
        if row['phase'] != phase:
            continue
        key = row['heldout_life'], row['life'], row['episode'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
    result = []
    for cell in cells:
        heldout = cell['heldout_life']
        histories = [life for life in LIVES if life != heldout]
        issues = list(cell['issues'])
        if not cell['complete']:
            _issue(issues, 'candidate_cell_incomplete')
        if cell['phase'] != phase or cell['query'] != 'risk1':
            _issue(issues, 'candidate_phase_mismatch')
        count = 2 if phase == 'FINAL' else 54
        if len(cell['slots']) != count or [slot['candidate_slot'] for slot in cell['slots']] != list(range(count)):
            _issue(issues, 'candidate_slot_roster')
        expected = {(heldout, life, episode, mode) for life in histories for episode in range(episodes)
                    for mode in ['H2']+[f'P{slot["candidate_slot"]}_{route}' for slot in cell['slots'] for route in ('COND', 'LATCHED')]}
        if any(key[0] == heldout and key not in expected for key in index):
            _issue(issues, 'unexpected_outcome')
        scores, work = [], Counter(paired_terminal_episodes_examined=0, terminal_vector_differences=0)
        for slot in cell['slots']:
            candidate_issues, per_history = list(issues), []
            for life in histories:
                vectors = {route: [] for route in MODES}
                for episode in range(episodes):
                    seed = episode_seed(phase, life, episode, heldout)
                    work['paired_terminal_episodes_examined'] += 1
                    trial_issues, rows = [], {}
                    for route in MODES:
                        mode = 'H2' if route == 'H2' else f'P{slot["candidate_slot"]}_{route}'
                        key = heldout, life, episode, mode
                        row = index.get(key)
                        rows[route] = row
                        for issue in _terminal_issues(row, seed):
                            _issue(trial_issues, issue)
                        if key in duplicates:
                            _issue(trial_issues, 'duplicate_outcome')
                        for issue in _metadata_issues(row, phase, life, heldout, episode, mode,
                                None if route == 'H2' else slot['candidate_slot'], route,
                                None if route == 'H2' else slot['program']):
                            _issue(trial_issues, issue)
                    for issue in trial_issues:
                        _issue(candidate_issues, issue)
                    if trial_issues:
                        continue
                    for route in MODES:
                        vectors[route].append(rows[route]['components'])
                    work['terminal_vector_differences'] += 2
                if len(vectors['COND']) == episodes:
                    means = {route: _vector_mean(vectors[route]) for route in MODES}
                    delta = [a-b for a, b in zip(means['COND'], means['H2'], strict=True)]
                    feedback = [a-b for a, b in zip(means['COND'], means['LATCHED'], strict=True)]
                    per_history.append(dict(life=life, episodes=episodes, component_mean=means['COND'],
                        utility=utility(means['COND'], 'risk1'), component_delta_vs_H2=delta, gain=utility(delta, 'risk1'),
                        latched_component_mean=means['LATCHED'], latched_utility=utility(means['LATCHED'], 'risk1'),
                        component_delta_vs_LATCHED=feedback, gain_vs_LATCHED=utility(feedback, 'risk1')))
            complete = not candidate_issues and len(per_history) == 3
            def average(key):
                return _vector_mean(row[key] for row in per_history) if complete else None
            vector, delta, latched, feedback = (average(key) for key in ('component_mean', 'component_delta_vs_H2',
                                                                      'latched_component_mean', 'component_delta_vs_LATCHED'))
            scores.append(dict(candidate_slot=slot['candidate_slot'], program=deepcopy(slot['program']),
                complete=complete, issues=candidate_issues, train_component_mean=vector,
                train_utility=None if vector is None else utility(vector, 'risk1'),
                train_component_delta_vs_H2=delta, train_gain=None if delta is None else utility(delta, 'risk1'),
                latched_component_mean=latched, latched_utility=None if latched is None else utility(latched, 'risk1'),
                train_component_delta_vs_LATCHED=feedback,
                train_gain_vs_LATCHED=None if feedback is None else utility(feedback, 'risk1'), per_history=per_history))
        complete = not issues and bool(scores) and all(row['complete'] for row in scores)
        chosen, seen = [], set()
        if complete:
            for score in sorted(scores, key=lambda row: (-row['train_utility'], program_key(row['program']), row['candidate_slot'])):
                key = program_key(score['program'])
                if key not in seen:
                    chosen.append(score); seen.add(key)
                if len(chosen) == (1 if phase == 'FINAL' else 2):
                    break
            if len(chosen) != (1 if phase == 'FINAL' else 2):
                complete = False
                _issue(issues, 'distinct_parent_pool')
                chosen = []
        if not complete:
            _issue(issues, 'incomplete_terminal_cohort')
        selected = deepcopy(cell)
        selected.update(complete=complete, issues=issues, slot_scores=scores,
                        selection_basis='whole_episode_conditional_utility', logical_work=dict(work),
                        selected_parents=[deepcopy(row['program']) for row in chosen],
                        selected_slots=[row['candidate_slot'] for row in chosen])
        result.append(selected)
    return result


def summarize_eval(outcomes):
    """Pair 32 new whole-game seeds within each of four existing histories."""
    index, duplicates = {}, set()
    for row in outcomes:
        key = row['life'], row['episode'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
    expected = {(life, episode, mode) for life in LIVES for episode in range(32) for mode in MODES}
    roster_issues = ['unexpected_outcome'] if set(index)-expected else []
    episode_rows = []
    for life in LIVES:
        for episode in range(32):
            issues, seed = list(roster_issues), episode_seed('EVAL', life, episode)
            rows = {mode: index.get((life, episode, mode)) for mode in MODES}
            for mode, row in rows.items():
                for issue in _terminal_issues(row, seed):
                    _issue(issues, issue)
                if (life, episode, mode) in duplicates:
                    _issue(issues, 'duplicate_outcome')
                for issue in _metadata_issues(row, 'EVAL', life, life, episode, mode, None, mode,
                        None if mode == 'H2' else None if row is None else row['module']['program']):
                    _issue(issues, issue)
            if rows['COND'] is not None and rows['LATCHED'] is not None and rows['COND']['module']['program'] != rows['LATCHED']['module']['program']:
                _issue(issues, 'paired_program_mismatch')
            complete = not issues
            deltas = {name: [a-b for a, b in zip(rows[left]['components'], rows[right]['components'], strict=True)] if complete else None
                      for name, (left, right) in CONTRASTS.items()}
            episode_rows.append(dict(life=life, episode=episode, seed=seed, complete=complete,
                issues=issues, outcomes=deepcopy(rows), component_deltas=deltas))
    comparisons = []
    for name in CONTRASTS:
        histories = []
        for life in LIVES:
            selected = [row for row in episode_rows if row['life'] == life]
            values = {metric: [] for metric in METRICS}
            for row in selected:
                delta = row['component_deltas'][name]
                for metric, value in zip(METRICS, [utility(delta, 'risk1'), *delta] if delta is not None else [None]*4, strict=True):
                    values[metric].append(value)
            histories.append(dict(life=life, episodes=32, metrics={metric: _moments(values[metric]) for metric in METRICS}))
        metrics = {metric: _pool([row['metrics'][metric] for row in histories], 4) for metric in METRICS}
        for stats in metrics.values():
            stats['conditional_episode_se'] = stats.pop('conditional_suffix_se')
            stats['conditional_episode_ci95'] = stats.pop('conditional_suffix_ci95')
        comparisons.append(dict(query='risk1', contrast=name, episodes=128,
            complete=all(stats['complete'] for stats in metrics.values()), metrics=metrics, per_history=histories))
    diagnostics = []
    for mode in MODES:
        rows = [index[life, episode, mode] for life in LIVES for episode in range(32) if (life, episode, mode) in index]
        counts = {key: sum(row['module'][key] for row in rows) for key in MODULE_COUNTS}
        steps = sum(row['steps'] for row in rows)
        diagnostics.append(dict(mode=mode, episodes=128, present_episodes=len(rows),
            terminal_episodes=sum(row['status'] in ('WON', 'LOST') for row in rows), steps_sum=steps,
            module_counts=counts, node_visits=[sum(row['module']['node_visits'][node] for row in rows) for node in range(2)],
            direct_decision_fraction=None if not steps else counts['direct_decisions']/steps,
            teacher_call_fraction=None if not steps else counts['h2_calls']/steps,
            episodes_with_repeated_node_visits=sum(max(row['module']['node_visits']) > 1 for row in rows),
            episodes_with_live_predicate_changes=sum(row['module']['live_predicate_changes'] > 0 for row in rows),
            episodes_with_latch_divergences=sum(row['module']['latch_divergences'] > 0 for row in rows)))
    return dict(schema='acfqp.persistent_strategy.v170.summary',
        complete=all(row['complete'] for row in episode_rows) and all(row['complete'] for row in comparisons),
        episode_rows=episode_rows, comparisons=comparisons, program_diagnostics=diagnostics,
        logical_work=dict(outcome_rows_supplied=len(outcomes), paired_whole_episodes_examined=128,
                          contrast_component_vectors=sum(row['complete'] for row in episode_rows)*3),
        uncertainty='Normal paired-whole-episode CI conditional on four existing historical teachers and frozen strategies; equal32 new complete game seeds/history and four histories. Source folds overlap.')
