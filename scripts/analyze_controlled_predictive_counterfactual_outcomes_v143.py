"""Audit realized first-action outcomes under one frozen H2 continuation policy."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.domains import standard_2048 as ground
from scripts import analyze_controlled_predictive_h1_continuation_v142 as previous

planning, teacher_analysis = previous.planning, previous.teacher_analysis
LIVES, QUERIES, REPLICAS = previous.LIVES, previous.QUERIES, 8
METHODS = ('H2', 'SHALLOW', 'LEARNED64', 'H1_CONT')
ROOTS_PER_GAME, SUFFIXES, MAX_STEPS, BASE = 4, 8, 2000, 143*100000000
COMPARISONS = {'H1_CONT-H2': ('H1_CONT', 'H2'), 'LEARNED64-H2': ('LEARNED64', 'H2'),
    'SHALLOW-H2': ('SHALLOW', 'H2'), 'H1_CONT-LEARNED64': ('H1_CONT', 'LEARNED64'),
    'H1_CONT-SHALLOW': ('H1_CONT', 'SHALLOW')}
METRICS = ('utility', 'reward', 'failure', 'success')
mean, add_checks = previous.mean, previous.add_checks


def legal_exits(board):
    if max(board) >= ground.GOAL_RANK:
        return 'WON', {}, 0
    exits = {}
    for action in ground.ACTION_ORDER:
        after, score, changed = ground.swipe_board_v1(board, action)
        if changed: exits[action.value] = (after, score)
    return ('ACTIVE' if exits else 'LOST'), exits, 4


def replay_branch(row, query, max_steps=MAX_STEPS):
    """Replay recorded actions and the declared shared random stream, without a planner."""
    result = row['result']; steps = result['steps']
    checks = dict(branch_array_lengths=steps > 0 and all(len(row[name]) == steps
        for name in ('actions', 'spawned_cells', 'spawned_ranks', 'scores')),
        branch_root_active=True, branch_actions_legal=True, branch_spawn_stream=True,
        branch_scores=True, branch_first_action=True, branch_terminal_chain=True,
        branch_returns=True, branch_environment_accounting=True,
        branch_h2_accounting=True, branch_no_learning=not any(result['learning_counts'].values()),
        branch_seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds'])
            and 0 <= result['decision_seconds'] <= result['seconds'])
    if not checks['branch_array_lengths']: return checks, 0
    board = tuple(row['root_board']); status, exits, swipes = legal_exits(board)
    checks['branch_root_active'] = status == 'ACTIVE'
    rng = random.Random(row['seed']); score_total = 0; continuation_legal = 0
    expected = Counter(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes,
        ground_swipe_calls=swipes)
    replay_swipes = swipes
    for index, action in enumerate(row['actions']):
        checks['branch_terminal_chain'] &= status == 'ACTIVE'
        checks['branch_actions_legal'] &= action in exits
        if action not in exits: return checks, replay_swipes
        if index: continuation_legal += len(exits)
        after, score = exits[action]; score_total += score
        expected.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1,
            sampled_transitions=1, environment_random_draws=2,
            **{'continuation_actions' if index else 'forced_actions': 1})
        empty = [cell for cell, rank in enumerate(after) if rank == 0]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        checks['branch_spawn_stream'] &= cell == row['spawned_cells'][index] and rank == row['spawned_ranks'][index]
        checks['branch_scores'] &= score == row['scores'][index]
        board = list(after); board[cell] = rank; board = tuple(board)
        if not index:
            checks['branch_first_action'] &= action == row['first_action'] and list(after) == row['first_afterstate'] and list(board) == row['first_exit']
        status, exits, swipes = legal_exits(board); replay_swipes += swipes
        expected.update(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    final_status = 'CUTOFF' if status == 'ACTIVE' else status
    checks['branch_terminal_chain'] &= (list(board) == row['final_board'] and result['status'] == final_status
        and steps <= max_steps and (status != 'ACTIVE' or steps == max_steps))
    components = [score_total/2048., float(final_status == 'LOST'), float(final_status == 'WON')]
    utility = None if final_status == 'CUTOFF' else components[0]-QUERIES[query]['failure_penalty']*components[1]+QUERIES[query]['goal_bonus']*components[2]
    checks['branch_returns'] &= result['score'] == score_total and result['components'] == components and result['utility'] == utility
    checks['branch_environment_accounting'] &= (Counter(result['environment_counts']) == expected
        and result['forced_action_count'] == 1 and result['continuation_decisions'] == steps-1)
    checks['branch_h2_accounting'] &= planning.planning_counts_valid(result['policy_counts'], 'H2', 'SINGLE', steps-1, continuation_legal)
    checks['branch_no_learning'] &= not any(value for key, value in result['policy_counts'].items()
        if key.endswith('updates') or key.startswith(('fit_', 'observations')))
    return checks, replay_swipes


def paired_comparison(roots, indexed, valid):
    """Average suffixes, four fixed roots, eight games, then four histories."""
    comparisons = {}
    for label, (left, right) in COMPARISONS.items():
        comparisons[label] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                games = []
                for replica in range(REPLICAS):
                    cells = []
                    for slot in range(ROOTS_PER_GAME):
                        key = life, query, replica, slot; root = roots.get(key)
                        pairs = []; same_action = None
                        if root is not None:
                            a, b = root['choices'][left], root['choices'][right]
                            same_action = a == b
                            for suffix in range(SUFFIXES):
                                ka, kb = (*key, a, suffix), (*key, b, suffix)
                                ra, rb = indexed.get(ka), indexed.get(kb)
                                complete = all(row is not None and valid.get(k, False) and row['result']['status'] in ('WON', 'LOST')
                                    for k, row in ((ka, ra), (kb, rb)))
                                item = dict(suffix=suffix, complete=complete)
                                if complete:
                                    va = dict(zip(METRICS, [ra['result']['utility'], *ra['result']['components']]))
                                    vb = dict(zip(METRICS, [rb['result']['utility'], *rb['result']['components']]))
                                    item['deltas'] = {metric: va[metric]-vb[metric] for metric in METRICS}
                                pairs.append(item)
                        complete = len(pairs) == SUFFIXES and all(pair['complete'] for pair in pairs)
                        cells.append(dict(root_slot=slot, complete=complete, same_action=same_action,
                            means={metric: mean(pair.get('deltas', {}).get(metric) for pair in pairs) if complete else None for metric in METRICS}))
                    complete = all(cell['complete'] for cell in cells)
                    games.append(dict(replica=replica, roots=cells, complete=complete,
                        means={metric: mean(cell['means'][metric] for cell in cells) for metric in METRICS}))
                lives.append(dict(life=life, games=games, complete=all(game['complete'] for game in games),
                    means={metric: mean(game['means'][metric] for game in games) for metric in METRICS}))
            comparisons[label][query] = dict(lifecycles=lives, complete=all(life['complete'] for life in lives),
                mean=mean(life['means']['utility'] for life in lives),
                means={metric: mean(life['means'][metric] for life in lives) for metric in METRICS},
                positive=sum(life['means']['utility'] is not None and life['means']['utility'] > 0 for life in lives),
                negative=sum(life['means']['utility'] is not None and life['means']['utility'] < 0 for life in lives),
                zero=sum(life['means']['utility'] == 0 for life in lives),
                same_action_roots=sum(cell['same_action'] is True for life in lives for game in life['games'] for cell in game['roots']))
    return dict(comparisons=comparisons, complete=all(cell['complete'] for group in comparisons.values() for cell in group.values()),
        conditioning_policy='frozen query-specific H2 after the forced first action',
        estimand='paired realized suffix returns with equal suffix, root, game and lifecycle weights')


def expected_settings():
    return dict(lifecycles=list(LIVES), queries=QUERIES, replicas=REPLICAS, workers=4,
        methods=list(METHODS), roots_per_game=ROOTS_PER_GAME, suffixes=SUFFIXES,
        root_selection='sorted retained steps; index floor((2*j+1)*n/8), j=0..3',
        expected_roots=256, expected_source_roots=1973, representation='SINGLE',
        continuation='H2', p_four=.1, max_steps=MAX_STEPS, version_base=BASE,
        new_training_samples=0, branch_deduplication='one branch per distinct first action and suffix',
        suffix_seed='BASE+life*1000000+query_index*100000+replica*10000+slot*100+suffix',
        cutoff_rule='retain all costs; no terminal utility or replacement')


def source_cohort(sources):
    """Independently recover every fixed quantile from the inherited complete roster."""
    roots = []; reads = Counter(); checks = dict(source_diagnostic_roster=True, source_root_identity=True)
    for source in sources:
        old_rows = list(previous.old.read_rows(source['diagnostic_source_trace']))
        new_rows = list(previous.old.read_rows(source['h1_diagnostic_trace']))
        reads.update(v141=len(old_rows), v142=len(new_rows))
        key = lambda row: (row['life'], row['query'], row['replica'], row['step'])
        new = {key(row): row for row in new_rows}
        checks['source_diagnostic_roster'] &= (len(new) == len(new_rows) == len(old_rows)
            and len({key(row) for row in old_rows}) == len(old_rows) and set(new) == {key(row) for row in old_rows}
            and {(row['life'], row['query'], row['replica']) for row in old_rows}
                == {(source['life'], q, r) for q in QUERIES for r in range(REPLICAS)})
        for query in QUERIES:
            for replica in range(REPLICAS):
                rows = sorted((r for r in old_rows if r['query'] == query and r['replica'] == replica), key=lambda r: r['step'])
                checks['source_diagnostic_roster'] &= len(rows) >= ROOTS_PER_GAME
                if len(rows) < ROOTS_PER_GAME: continue
                for slot in range(ROOTS_PER_GAME):
                    ordinal = ((2*slot+1)*len(rows))//8; row = rows[ordinal]; h1 = new.get(key(row))
                    fields = ('life', 'query', 'replica', 'seed', 'step', 'board', 'previous_action', 'simulation_seed')
                    checks['source_root_identity'] &= h1 is not None and all(row[name] == h1[name] for name in fields)
                    checks['source_root_identity'] &= (row['seed'] == previous.v140.outer_seed(source['life'], replica)
                        and row['simulation_seed'] == previous.v140.model_seed(source['life'], replica, row['step']))
                    if h1 is None: continue
                    choices = dict(H2=row['reference']['action'], SHALLOW=row['probes']['SHALLOW']['action'],
                        LEARNED64=row['probes']['LEARNED64']['action'], H1_CONT=h1['probes']['H1_CONT']['action'])
                    roots.append(dict(**{name: row[name] for name in fields}, root_id=':'.join(map(str, key(row))),
                        slot=slot, source_ordinal=ordinal, source_game_roots=len(rows), choices=choices,
                        actions=sorted(set(choices.values())), suffix_seeds=[BASE+source['life']*1000000+
                            list(QUERIES).index(query)*100000+replica*10000+slot*100+s for s in range(SUFFIXES)]))
    checks['source_diagnostic_roster'] &= reads == Counter(v141=1973, v142=1973) and len(roots) == 256
    return roots, reads, checks


def new_cost():
    return dict(physical_branches=0, steps=0, seconds=0., decision_seconds=0.,
        statuses=Counter(), environment_counts=Counter(), policy_counts=Counter())


def add_cost(cell, branch):
    result = branch['result']; cell['physical_branches'] += 1
    for name in ('steps', 'seconds', 'decision_seconds'): cell[name] += result[name]
    cell['statuses'][result['status']] += 1
    for name in ('environment_counts', 'policy_counts'): cell[name].update(result[name])


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen, cohort = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json', 'cohort.json'))
    checks = dict(frozen_settings=run['settings'] == expected_settings(),
        source_roster=len(capsule['snapshots']) == 4 and {s['life'] for s in capsule['snapshots']} == set(LIVES),
        frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings', 'inherited_costs', 'cohort_ref')),
        evaluation_lifecycles=len(run['eval_lifecycles']) == 4 and {row['life'] for row in run['eval_lifecycles']} == set(LIVES),
        source_complete=True, source_references=True, inherited_costs=True,
        cohort_exact_roster=True, cohort_counts=True, paired_record_roster=True,
        shared_suffix_seeds=True, distinct_action_branches=True, branch_roots=True,
        frozen_continuation=True, query_roster=True, model_loads=True, frozen_models=True,
        planner_spawn_law=True, query_accounting=True)
    sources = {s['life']: s for s in capsule['snapshots']}
    origin = Path(capsule['snapshots'][0]['h1_diagnostic_trace']).parent.parent
    origin_run, origin_capsule, origin_analysis = (json.loads((origin/name).read_text()) for name in ('run.json', 'source_capsule.json', 'analysis.json'))
    checks['source_complete'] &= origin_run['status'] == 'complete' and origin_analysis['complete'] and origin_analysis['primary_complete']
    checks['inherited_costs'] &= run['inherited_costs'] == capsule['inherited_costs'] == {
        **origin_capsule['inherited_costs'], 'v142_experiment': origin_analysis['costs']}
    expected_roots, reads, source_checks = source_cohort(capsule['snapshots']); add_checks(checks, source_checks)
    checks['cohort_exact_roster'] &= cohort['roots'] == expected_roots
    physical = sum(len(r['actions'])*SUFFIXES for r in expected_roots)
    checks['cohort_counts'] &= (cohort['source_rows_read'] == dict(reads)
        and cohort['physical_branches'] == physical and cohort['paired_records'] == 2048
        and cohort['logical_method_suffixes'] == 8192)
    by_id = {r['root_id']: r for r in expected_roots}
    roots = {(r['life'], r['query'], r['replica'], r['slot']): r for r in expected_roots}
    indexed, valid, records = {}, {}, []; costs = dict(new_outcomes=new_cost(), by_query={q: new_cost() for q in QUERIES},
        source_rows_read=dict(reads), model_accounting=[], new_training_samples=0,
        logical_method_suffixes=8192, analysis_replay_swipes=0)
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]
        original = next(s for s in origin_capsule['snapshots'] if s['life'] == life)
        origin_eval = next(s for s in origin_run['eval_lifecycles'] if s['life'] == life)
        copied = dict(source); copied.pop('h1_diagnostic_trace')
        checks['source_references'] &= copied == original and Path(source['h1_diagnostic_trace']) == origin/origin_eval['diagnostics_trace']
        query_costs = {q: new_cost() for q in QUERIES}; pairs = Counter()
        for row in previous.old.read_rows(directory/lifecycle['consequences_trace']):
            records.append((row['root_id'], row['suffix'])); root = by_id.get(row['root_id'])
            checks['paired_record_roster'] &= root is not None and root['life'] == life and 0 <= row['suffix'] < SUFFIXES
            if root is None: continue
            query = root['query']; pairs[query] += 1
            checks['shared_suffix_seeds'] &= row['seed'] == root['suffix_seeds'][row['suffix']]
            checks['frozen_continuation'] &= row['continuation'] == 'H2'
            checks['distinct_action_branches'] &= set(row['branches']) == set(root['actions'])
            for action, branch in row['branches'].items():
                key = (life, query, root['replica'], root['slot'], action, row['suffix'])
                checks['branch_roots'] &= (branch['root_board'] == root['board'] and branch['first_action'] == action
                    and branch['seed'] == row['seed'])
                branch_checks, swipes = replay_branch(branch, query); add_checks(checks, branch_checks)
                indexed[key] = branch; valid[key] = all(branch_checks.values())
                costs['analysis_replay_swipes'] += swipes
                for cell in (costs['new_outcomes'], costs['by_query'][query], query_costs[query]): add_cost(cell, branch)
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query, qdata in lifecycle['queries'].items():
            cell = query_costs[query]
            checks['query_accounting'] &= (qdata['roots'] == 32 and qdata['paired_records'] == pairs[query] == 256
                and qdata['physical_branches'] == cell['physical_branches'] and Counter(qdata['statuses']) == cell['statuses']
                and Counter(qdata['environment_counts']) == cell['environment_counts']
                and Counter(qdata['policy_counts']) == cell['policy_counts'])
            checks['model_loads'] &= teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['frozen_models'] &= (qdata['leaf_before'] == qdata['leaf_after'] == planning.expected_model_state(source, query, 'SINGLE')
                and qdata['parent_before'] == qdata['parent_after'] == planning.previous.model_state(source, query, 'PARENT', 0))
            checks['planner_spawn_law'] &= qdata['spawn_probabilities'] == planning.expected_spawn_probabilities(source)
            costs['model_accounting'].append(dict(life=life, query=query, loads=qdata['loads']))
    expected_records = {(root['root_id'], suffix) for root in expected_roots for suffix in range(SUFFIXES)}
    checks['paired_record_roster'] &= len(records) == len(set(records)) == 2048 and set(records) == expected_records
    checks['distinct_action_branches'] &= len(indexed) == costs['new_outcomes']['physical_branches'] == physical
    costs['new_environment_samples'] = costs['new_outcomes']['environment_counts'].get('sampled_transitions', 0)
    work = costs['new_outcomes']['policy_counts']
    costs['new_model_samples'] = sum(value for key, value in work.items() if key.endswith(('model_spawn_samples', 'model_sampled_transitions')))
    costs['generated_model_outcomes'] = work.get('generated_spawn_outcomes', 0)
    outcomes = paired_comparison(roots, indexed, valid)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.counterfactual_outcomes.v143.analysis', complete=complete,
        primary_complete=complete and outcomes['complete'], checks={key: bool(value) for key, value in checks.items()},
        outcomes=outcomes, costs=costs, inherited_work=run['inherited_costs'],
        required_inputs=capsule['required_inputs'], seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Fixed 256 roots from all 64 retained H2 games; eight shared new suffix streams. Distinct first actions are executed once per stream, followed by the same frozen query-specific H2 policy. Same-action zero contrasts remain in the fixed population. Realized outcomes are conditional on this continuation policy and are neither optimal Q values nor a new closed-loop method evaluation. Every cutoff retains cost and suppresses affected complete terminal means. No model is fitted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143')
    directory = parser.parse_args().input; result = analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
