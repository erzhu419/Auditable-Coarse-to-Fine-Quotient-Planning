"""Audit frozen paired-outcome learning and its new-game policy consequences."""
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
from scripts import analyze_controlled_predictive_counterfactual_outcomes_v143 as previous

h1, planning, old = previous.previous, previous.planning, previous.previous.old
LIVES, QUERIES, REPLICAS = previous.LIVES, previous.QUERIES, 8
BASE, MAX_STEPS, PASSES, ALPHA = 144*100000000, 2000, 32, .1
METHODS = ('H2', 'ZERO', 'LEARNED')
COMPARISONS = {'LEARNED-H2': ('LEARNED', 'H2'), 'LEARNED-ZERO': ('LEARNED', 'ZERO'),
               'ZERO-H2': ('ZERO', 'H2')}
PATTERNS = ((0, 1, 2, 4, 5, 6), (4, 5, 6, 8, 9, 10),
            (0, 1, 2, 3, 4, 5), (4, 5, 6, 7, 8, 9))
mean, add_checks = previous.mean, previous.add_checks


def close(left, right):
    return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def feature_counts(board):
    """Plain scalar indexing, independent of the production NumPy implementation."""
    result = Counter()
    for table, pattern in enumerate(PATTERNS):
        for reflected in (False, True):
            for rotations in range(4):
                address = 0
                for cell in pattern:
                    row, col = divmod(cell, 4)
                    if reflected: col = 3-col
                    for _ in range(rotations): row, col = col, 3-row
                    address = 11*address+board[4*row+col]
                result[table*11**6+address] += 1
    return result


def feature_difference(candidate, baseline):
    a, b = feature_counts(candidate), feature_counts(baseline)
    return {key: a[key]-b[key] for key in sorted(a.keys() | b.keys()) if a[key] != b[key]}


def predict_difference(difference, weights):
    value = [0., 0., 0.]
    for index, multiplicity in difference.items():
        for component, weight in enumerate(weights.get(index, (0., 0., 0.))):
            value[component] += multiplicity*weight
    return value


def fit_oracle(examples, passes=PASSES, alpha=ALPHA):
    """Use one averaged target per root; shared suffixes are not eight training rows."""
    weights, updates, attempts = {}, 0, 0
    cached = [(feature_difference(row['candidate_after'], row['baseline_after']),
               row['target_tail']) for row in examples]
    for _ in range(passes):
        for difference, target in cached:
            attempts += 1
            before = predict_difference(difference, weights)
            error = [target[k]-before[k] for k in range(3)]
            norm = sum(value**2 for value in difference.values())
            if not norm: continue
            updates += 1
            for index, multiplicity in difference.items():
                prior = weights.get(index, (0., 0., 0.))
                value = tuple(prior[k]+alpha*multiplicity*error[k]/norm for k in range(3))
                if any(value): weights[index] = value
                else: weights.pop(index, None)
    return dict(weights=weights, updates=updates, attempts=attempts)


def model_matches(payload, expected):
    actual = {int(row[0]): tuple(row[1:]) for row in payload['weights']}
    return (payload['radix'] == 11 and payload['frozen'] and payload['updates'] == expected['updates']
        and len(actual) == len(payload['weights']) and actual.keys() == expected['weights'].keys()
        and all(close(actual[key][k], expected['weights'][key][k]) for key in actual for k in range(3)))


def full_game_comparison(indexed, valid):
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
                    means={name: mean(row['result'][name] for row in rows) if complete else None
                           for name in ('utility', 'score', 'steps')}))
            methods[method][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
    for label, (left, right) in COMPARISONS.items():
        comparisons[label] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                complete = all(methods[m][query]['lifecycles'][life]['complete'] for m in (left, right))
                deltas = ([indexed[(life, query, left, r)]['result']['utility']-
                    indexed[(life, query, right, r)]['result']['utility'] for r in range(REPLICAS)] if complete else [])
                lives.append(dict(life=life, complete=complete, mean=mean(deltas), replica_deltas=deltas))
            comparisons[label][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                mean=mean(row['mean'] for row in lives), positive=sum((row['mean'] or 0) > 0 for row in lives),
                negative=sum((row['mean'] or 0) < 0 for row in lives), zero=sum(row['mean'] == 0 for row in lives))
    return dict(methods=methods, comparisons=comparisons,
        complete=all(cell['complete'] for group in methods.values() for cell in group.values()))


def new_cost():
    return dict(games=0, steps=0, seconds=0., decision_seconds=0., statuses=Counter(),
                environment_counts=Counter(), policy_counts=Counter())


def add_cost(cell, row):
    result = row['result']; cell['games'] += 1
    for key in ('steps', 'seconds', 'decision_seconds'): cell[key] += result[key]
    cell['statuses'][result['status']] += 1
    for key in ('environment_counts', 'policy_counts'): cell[key].update(result[key])


def unprefix(counts, prefix):
    return {key[len(prefix):]: value for key, value in counts.items()
        if key.startswith(prefix) and not (prefix == 'candidate_' and key == 'candidate_disagreements')}


def gate_checks(board, choice, query, weights, exits=None):
    if exits is None: _, exits, _ = previous.legal_exits(tuple(board))
    s = choice['selection']; a, b = s['candidate_choice'], s['baseline_choice']
    work = choice['work']; q = QUERIES[query]
    same = a['action'] == b['action']
    terminal = max(a['afterstate']) >= 11 or max(b['afterstate']) >= 11
    immediate = (a['score']-b['score'])/2048.
    predicted = [0., 0., 0.] if same or terminal else predict_difference(
        feature_difference(a['afterstate'], b['afterstate']), weights)
    advantage = 0. if same or terminal else q['reward_weight']*(immediate+predicted[0])-q['failure_penalty']*predicted[1]+q['goal_bonus']*predicted[2]
    selected = advantage > 0.; chosen = a if selected else b
    checks = dict(gate_equation=(s['same_action'] == same and s['terminal_pair_bypass'] == terminal
        and s['baseline_action'] == b['action'] and s['candidate_action'] == a['action']
        and s['baseline_score'] == b['score'] and s['candidate_score'] == a['score']

        and close(s['immediate_difference'], immediate)
        and all(close(x, y) for x, y in zip(s['predicted_tail_difference'], predicted))
        and len(s['predicted_tail_difference']) == 3 and close(s['estimated_advantage'], advantage)
        and s['selected_h1'] == selected and choice['action'] == chosen['action']
        and close(choice['value'], b['value']+(advantage if selected else 0.))
        and choice['value_kind'] == 'baseline_h2_proxy_plus_learned_advantage'),
        both_planners_charged=planning.planning_counts_valid(unprefix(work, 'baseline_'), 'H2', 'SINGLE', 1, len(exits)),
        selector_counts=(work.get('choose_calls') == 1 and work.get('terminal_pair_bypasses', 0) == int(terminal)
            and work.get('same_action_bypasses', 0) == int(same and not terminal)
            and work.get('candidate_disagreements', 0) == int(not same)
            and work.get('selected_h1', 0) == int(selected)))
    checks['candidate_exits'] = all(compact_choice_valid(x, exits, query) for x in (a, b))
    add_checks(checks, h1.h1_counts_valid(unprefix(work, 'candidate_'), a['action_values']))
    add_checks(checks, {'h2_'+k: v for k, v in h1.root_choice_checks(board, b, query).items()})
    add_checks(checks, {'candidate_'+k: v for k, v in h1.root_choice_checks(board, a, query).items()})
    learner = Counter(unprefix(work, 'learner_')); expected = Counter()
    if not same and not terminal:
        ca, cb = feature_counts(a['afterstate']), feature_counts(b['afterstate'])
        difference = feature_difference(a['afterstate'], b['afterstate'])
        expected.update(feature_board_reads=32, feature_rank_reads=384, feature_occurrences=64,
            pair_distinct_addresses=len(ca.keys() | cb.keys()), pair_nonzero_difference_addresses=len(difference),
            pair_signed_difference_occurrences=sum(abs(v) for v in difference.values()), pair_predictions=1,
            weight_address_lookups=len(difference), component_weight_reads=3*len(difference))
    checks['learner_prediction_accounting'] = learner == expected
    checks['gate_selected_exit'] = compact_choice_valid(choice, exits, query, analytic_goal=False)
    return checks


def control_checks(row, weights):
    r, choices = row['result'], row['choices']; n = r['steps']
    checks = dict(control_trace=old.compact_valid(row),
        control_seed=row['seed'] == BASE+90000000+row['life']*100000+row['replica'],
        control_choices=len(choices) == n, control_no_learning=not any(r['learning_counts'].values()),
        control_seconds=math.isfinite(r['decision_seconds']) and 0 <= r['decision_seconds'] <= r['seconds'],
        control_initial_stream=True, control_action_chain=True, control_spawn_stream=True,
        control_final_status=True, control_returns=True, control_cost_totals=True, control_model_seeds=True)
    if not checks['control_trace'] or not checks['control_choices']: return checks, 0
    rng = random.Random(row['seed']); board = [0]*16
    for recorded in row['initial_spawns']:
        empty = [i for i, v in enumerate(board) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        checks['control_initial_stream'] &= recorded == dict(cell=cell, rank=rank)
        board[cell] = rank
    checks['control_initial_stream'] &= board == row['initial_board']
    status, exits, swipes = previous.legal_exits(tuple(board)); replay_swipes = swipes
    expected = Counter(initial_spawns=2, environment_random_draws=4,
        ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    total, prior = Counter(), 'DOWN'
    for step, choice in enumerate(choices):
        work = choice['work']; total.update(work)
        replay_swipes += 4 if row['method'] == 'H2' else 8
        checks['control_model_seeds'] &= (choice['previous_action'] == prior and choice['simulation_seed'] ==
            (None if row['method'] == 'H2' else BASE+80000000+row['life']*1000000+row['replica']*10000+step))
        if row['method'] == 'H2':
            checks['h2_selected_exit'] = checks.get('h2_selected_exit', True) and compact_choice_valid(choice, exits, row['query'])
            add_checks(checks, {'h2_'+k: v for k, v in h1.root_choice_checks(board, choice, row['query']).items()})
            checks['h2_counts'] = checks.get('h2_counts', True) and planning.planning_counts_valid(work, 'H2', 'SINGLE', 1, len(exits))
        else:
            add_checks(checks, gate_checks(board, choice, row['query'], weights, exits))
        action = choice['action']; checks['control_action_chain'] &= status == 'ACTIVE' and action in exits and action == row['actions'][step]
        if action not in exits: return checks, replay_swipes
        after, score = exits[action]
        checks['control_action_chain'] &= row['scores'][step] == score
        empty = [i for i, v in enumerate(after) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        checks['control_spawn_stream'] &= cell == row['spawned_cells'][step] and rank == row['spawned_ranks'][step]
        board = list(after); board[cell] = rank; prior = action
        status, exits, swipes = previous.legal_exits(tuple(board)); replay_swipes += swipes
        expected.update(ground_explicit_swipe_calls=1, sampled_transitions=1, environment_random_draws=2,
            ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=1+swipes)
    final = 'CUTOFF' if status == 'ACTIVE' else status
    checks['control_final_status'] &= board == row['final_board'] and r['status'] == final and (final != 'CUTOFF' or n == MAX_STEPS)
    utility = None if final == 'CUTOFF' else old.utility(r['score'], final, row['query'])
    checks['control_returns'] &= r['utility'] == utility
    checks['control_cost_totals'] &= Counter(r['environment_counts']) == expected and total == Counter(r['policy_counts'])
    return checks, replay_swipes


def suffix_target(root, rows):
    """Pair original branch outcomes, remove only the first immediate score."""
    baseline, candidate = root['choices']['H2'], root['choices']['H1_CONT']
    b_after, b_score, b_changed = ground.swipe_board_v1(tuple(root['board']), ground.Swipe2048Action(baseline))
    a_after, a_score, a_changed = ground.swipe_board_v1(tuple(root['board']), ground.Swipe2048Action(candidate))
    checks = dict(training_root_actions=a_changed and b_changed,
        training_nonterminal_pairs=max(a_after) < 11 and max(b_after) < 11,
        training_suffixes=len(rows) == 8 and sorted(row['suffix'] for row in rows) == list(range(8)),
        training_pair_seeds=True, training_terminal_targets=True, training_first_reward=True)
    differences = []
    for row in sorted(rows, key=lambda x: x['suffix']):
        checks['training_pair_seeds'] &= row['seed'] == root['suffix_seeds'][row['suffix']] and row['continuation'] == 'H2'
        a, b = row['branches'][candidate], row['branches'][baseline]
        checks['training_terminal_targets'] &= all(x['result']['status'] in ('WON', 'LOST') for x in (a, b))
        checks['training_first_reward'] &= (a['first_afterstate'] == list(a_after) and b['first_afterstate'] == list(b_after)
            and a['scores'][0] == a_score and b['scores'][0] == b_score)
        differences.append([a['result']['components'][k]-b['result']['components'][k] for k in range(3)])
    components = [mean(d[k] for d in differences) for k in range(3)]
    immediate = (a_score-b_score)/2048.
    return dict(candidate_after=list(a_after), baseline_after=list(b_after),
        immediate_difference=immediate, target_total=components,
        target_tail=[components[0]-immediate, *components[1:]]), checks


def prediction_metrics(examples, weights, query):
    q = QUERIES[query]; rows = []
    for example in examples:
        difference = feature_difference(example['candidate_after'], example['baseline_after'])
        prediction = predict_difference(difference, weights); actual = example['target_tail']
        utility = lambda tail: q['reward_weight']*(example['immediate_difference']+tail[0])-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]
        predicted, target = utility(prediction), utility(actual)
        rows.append(dict(replica=example['replica'], component_squared_errors=[(prediction[k]-actual[k])**2 for k in range(3)],
            zero_component_squared_errors=[value**2 for value in actual], utility_squared_error=(predicted-target)**2,
            zero_utility_squared_error=(utility([0., 0., 0.])-target)**2,
            selected_h1=predicted > 0, realized_advantage=target if predicted > 0 else 0.,
            action_disagreement=example['candidate_after'] != example['baseline_after']))
    games = []
    for replica in sorted({row['replica'] for row in rows}):
        group = [row for row in rows if row['replica'] == replica]
        games.append(dict(replica=replica, roots=len(group),
            component_mse=[mean(row['component_squared_errors'][k] for row in group) for k in range(3)],
            zero_component_mse=[mean(row['zero_component_squared_errors'][k] for row in group) for k in range(3)],
            utility_mse=mean(row['utility_squared_error'] for row in group),
            zero_utility_mse=mean(row['zero_utility_squared_error'] for row in group),
            selected_h1=sum(row['selected_h1'] for row in group),
            action_disagreements=sum(row['action_disagreement'] for row in group),
            selected_realized_advantage=mean(row['realized_advantage'] for row in group)))
    return dict(games=games, roots=len(rows), component_mse=[mean(g['component_mse'][k] for g in games) for k in range(3)],
        zero_component_mse=[mean(g['zero_component_mse'][k] for g in games) for k in range(3)],
        utility_mse=mean(g['utility_mse'] for g in games), zero_utility_mse=mean(g['zero_utility_mse'] for g in games),
        selected_h1=sum(g['selected_h1'] for g in games), action_disagreements=sum(g['action_disagreements'] for g in games),
        selected_realized_advantage=mean(g['selected_realized_advantage'] for g in games))


def compact_choice_valid(choice, exits, query, analytic_goal=True):
    action = choice['action']
    if action not in exits: return False
    after, score = exits[action]
    valid = (choice['afterstate'] == list(after) and choice['score'] == score
        and choice['status'] == 'ACTIVE' and math.isfinite(choice['value']))
    if analytic_goal and max(after) >= 11:
        valid &= close(choice['value'], score/2048.+QUERIES[query]['goal_bonus'])
    return valid


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=4,
        methods=list(METHODS),train_replicas=[0,1,2,3],validation_replicas=[4,5,6,7],
        roots_per_game=4,suffixes_per_root=8,epochs=PASSES,alpha=ALPHA,
        update='normalized LMS on exact signed n-tuple multiplicities; denominator=sum(x*x)',
        target='mean paired H1_CONT minus H2 reward/failure/success; subtract immediate reward difference',
        representation='SINGLE',continuation='H2',gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1,max_steps=2000,physical_games=192,version_base=BASE,new_training_environment_samples=0,
        diagnostic_policy='no validation-dependent selection, refitting or early stopping')


def expected_prediction(example, weights):
    tail = predict_difference(feature_difference(example['candidate_after'], example['baseline_after']), weights)
    q = QUERIES[example['query']]
    advantage = example['immediate_difference']+tail[0]-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]
    return dict(root_id=example['root_id'], predicted_tail=tail, estimated_advantage=advantage, selected_h1=advantage > 0.)


def prediction_matches(actual, expected):
    return (actual['root_id'] == expected['root_id'] and actual['selected_h1'] == expected['selected_h1']
        and close(actual['estimated_advantage'], expected['estimated_advantage'])
        and len(actual['predicted_tail']) == 3
        and all(close(a, b) for a, b in zip(actual['predicted_tail'], expected['predicted_tail'])))


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen, frozen_training, retained = (read(name) for name in
        ('run.json', 'source_capsule.json', 'frozen_inputs.json', 'frozen_training.json', 'examples.json'))
    checks = dict(frozen_settings=run['settings'] == expected_settings(),
        source_roster=len(capsule['snapshots']) == 4 and {s['life'] for s in capsule['snapshots']} == set(LIVES),
        frozen_before_training=frozen['status'] == 'frozen' and frozen['lifecycles'] == [] and frozen['eval_lifecycles'] == []
            and all(frozen[k] == run[k] for k in ('settings', 'inherited_costs')),
        all_models_frozen_before_evaluation=frozen_training['status'] == 'trained_frozen'
            and frozen_training['eval_lifecycles'] == [] and frozen_training['lifecycles'] == run['lifecycles']
            and all(frozen_training[k] == run[k] for k in ('settings', 'inherited_costs')),
        training_lifecycles=len(run['lifecycles']) == 4 and {r['life'] for r in run['lifecycles']} == set(LIVES),
        evaluation_lifecycles=len(run['eval_lifecycles']) == 4 and {r['life'] for r in run['eval_lifecycles']} == set(LIVES),
        source_complete=True, source_references=True, inherited_costs=True, example_roster=True,
        source_row_accounting=True, exact_paired_targets=True, whole_game_split=True,
        model_bindings=True, fixed_training_order=True, normalized_lms_weights=True,
        training_work=True, frozen_advantage_models=True, validation_predictions=True,
        query_roster=True, model_loads=True, frozen_leaves=True, planner_totals=True, game_roster=True)
    sources = {s['life']: s for s in capsule['snapshots']}
    source_dir = Path(capsule['cohort_ref']).parent
    original_run, original_capsule, original_analysis = (json.loads((source_dir/name).read_text())
        for name in ('run.json', 'source_capsule.json', 'analysis.json'))
    checks['source_complete'] &= original_run['status'] == 'complete' and original_analysis['complete'] and original_analysis['primary_complete']
    checks['inherited_costs'] &= run['inherited_costs'] == capsule['inherited_costs'] == {
        **original_capsule['inherited_costs'], 'v143_experiment': original_analysis['costs']}
    cohort = json.loads(Path(capsule['cohort_ref']).read_text()); roots = {r['root_id']: r for r in cohort['roots']}
    records = {key: [] for key in roots}; reads = Counter()
    for life, source in sources.items():
        original = next(s for s in original_capsule['snapshots'] if s['life'] == life)
        original_eval = next(s for s in original_run['eval_lifecycles'] if s['life'] == life)
        copied = dict(source); copied.pop('paired_consequences_trace')
        checks['source_references'] &= copied == original and Path(source['paired_consequences_trace']) == source_dir/original_eval['consequences_trace']
        for row in old.read_rows(source['paired_consequences_trace']):
            reads.update(paired_records=1, physical_branches=len(row['branches']))
            checks['source_row_accounting'] &= row['root_id'] in roots and roots[row['root_id']]['life'] == life
            if row['root_id'] in records:
                # Keep terminal summaries and first rewards; do not replay old trajectories.
                records[row['root_id']].append(dict(root_id=row['root_id'], suffix=row['suffix'], seed=row['seed'],
                    continuation=row['continuation'], branches={action: dict(result=branch['result'],
                        first_afterstate=branch['first_afterstate'], scores=branch['scores'][:1])
                        for action, branch in row['branches'].items()}))
    expected_examples = []
    for root in sorted(cohort['roots'], key=lambda r: (r['life'], list(QUERIES).index(r['query']), r['replica'], r['slot'])):
        target, values = suffix_target(root, records[root['root_id']]); add_checks(checks, values)
        expected_examples.append(dict(root_id=root['root_id'], life=root['life'], query=root['query'], replica=root['replica'],
            slot=root['slot'], step=root['step'], split='TRAIN' if root['replica'] < 4 else 'VALIDATION',
            candidate_action=root['choices']['H1_CONT'], baseline_action=root['choices']['H2'], **target, suffixes=8))
    checks['example_roster'] &= len(expected_examples) == 256 and len({e['root_id'] for e in retained['examples']}) == 256
    checks['exact_paired_targets'] &= retained['examples'] == expected_examples
    checks['source_row_accounting'] &= retained['source_rows_read'] == dict(reads) and reads == Counter(paired_records=2048, physical_branches=3616)
    checks['whole_game_split'] &= Counter((e['life'], e['query'], e['split']) for e in expected_examples) == Counter({
        (life, query, split): 16 for life in LIVES for query in QUERIES for split in ('TRAIN', 'VALIDATION')})
    trained = {r['life']: r for r in run['lifecycles']}; models, diagnostics = {}, {q: {} for q in QUERIES}
    costs = dict(new_control=new_cost(), by_method={m: new_cost() for m in METHODS},
        by_query={q: {m: new_cost() for m in METHODS} for q in QUERIES}, source_rows_read=dict(reads),
        new_training_environment_samples=0, training_counts=Counter(), validation_counts=Counter(),
        training_seconds=sum(r['seconds'] for r in run['lifecycles']), model_accounting=[],
        analysis_replay_swipes=2*len(expected_examples), analysis_lms_attempts=0)
    for life in LIVES:
        source, lifecycle = sources[life], trained[life]
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query in QUERIES:
            qdata = lifecycle['queries'][query]
            train = [e for e in expected_examples if e['life'] == life and e['query'] == query and e['split'] == 'TRAIN']
            validation = [e for e in expected_examples if e['life'] == life and e['query'] == query and e['split'] == 'VALIDATION']
            expected = fit_oracle(train); costs['analysis_lms_attempts'] += expected['attempts']
            payload = read(qdata['model_ref']); models[life, query] = expected['weights']
            state = {k: payload[k] for k in ('radix', 'updates', 'frozen', 'weights')}
            checks['model_bindings'] &= qdata['binding'] == dict(life=life, query=query, continuation='H2', leaf_ref=source['leaves'][query]['SINGLE']['model_ref'])
            checks['fixed_training_order'] &= qdata['train_roots'] == [e['root_id'] for e in train] and qdata['validation_roots'] == [e['root_id'] for e in validation]
            checks['normalized_lms_weights'] &= model_matches(payload, expected)
            checks['frozen_advantage_models'] &= (qdata['before'] == dict(radix=11, updates=0, frozen=False, weights=[])
                and qdata['frozen_state'] == qdata['after_validation'] == state and qdata['model_bytes'] == (directory/qdata['model_ref']).stat().st_size)
            fit = qdata['fit_counts']; costs['training_counts'].update(fit)
            checks['training_work'] &= (fit.get('update_calls') == expected['attempts'] and fit.get('pair_updates', 0) == expected['updates']
                and fit.get('unidentifiable_pairs', 0) == expected['attempts']-expected['updates']
                and fit.get('pair_predictions') == expected['attempts']
                and fit.get('feature_board_reads') == 32*expected['attempts']
                and fit.get('feature_rank_reads') == 384*expected['attempts']
                and fit.get('component_weight_updates', 0) == 3*fit.get('weight_address_updates', 0))
            for method, weights in (('ZERO', {}), ('LEARNED', expected['weights'])):
                actual = qdata['validation'][method]; predictions = [expected_prediction(e, weights) for e in validation]
                checks['validation_predictions'] &= len(actual) == 16 and all(prediction_matches(a, b) for a, b in zip(actual, predictions))
                costs['validation_counts'].update(qdata['validation_work'][method])
            diagnostics[query][life] = dict(TRAIN=prediction_metrics(train, expected['weights'], query),
                VALIDATION=prediction_metrics(validation, expected['weights'], query))
    indexed, valid = {}, {}
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]; per_query = {q: {m: Counter() for m in METHODS} for q in QUERIES}
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key = row['life'], row['query'], row['method'], row['replica']
            checks['game_roster'] &= (key not in indexed and key[0] == life and key[1] in QUERIES
                and key[2] in METHODS and key[3] in range(REPLICAS))
            weights = models[life, row['query']] if row['method'] == 'LEARNED' else {}
            row_checks, swipes = control_checks(row, weights); add_checks(checks, row_checks)
            indexed[key], valid[key] = dict(result=row['result']), all(row_checks.values())
            costs['analysis_replay_swipes'] += swipes
            for cell in (costs['new_control'], costs['by_method'][row['method']], costs['by_query'][row['query']][row['method']]): add_cost(cell, row)
            per_query[row['query']][row['method']].update(row['result']['policy_counts'])
        for query, qdata in lifecycle['queries'].items():
            checks['model_loads'] &= h1.teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['frozen_leaves'] &= (qdata['parent_before'] == qdata['parent_after'] == planning.previous.model_state(source, query, 'PARENT', 0)
                and qdata['leaf_before'] == qdata['leaf_after'] == planning.expected_model_state(source, query, 'SINGLE'))
            teacher_total, candidate_total = Counter(), Counter()
            for method, mdata in qdata['planners'].items():
                work = per_query[query][method]
                checks['planner_totals'] &= Counter(mdata['counts']) == work
                if method == 'H2':
                    teacher_total.update(work); checks['frozen_advantage_models'] &= mdata['model_before'] is None and mdata['model_after'] is None
                else:
                    teacher_total.update(unprefix(work, 'baseline_')); candidate_total.update(unprefix(work, 'candidate_'))
                    state = trained[life]['queries'][query]['frozen_state'] if method == 'LEARNED' else dict(radix=11, updates=0, frozen=True, weights=[])
                    checks['frozen_advantage_models'] &= mdata['model_before'] == mdata['model_after'] == state
            checks['planner_totals'] &= teacher_total == Counter(qdata['teacher_total_counts']) and candidate_total == Counter(qdata['candidate_total_counts'])
            costs['model_accounting'].append(dict(life=life, query=query, loads=qdata['loads'],
                candidate_setup_counts=qdata['candidate_setup_counts'], candidate_setup_seconds=qdata['candidate_setup_seconds'],
                learner_setup_counts={m: qdata['planners'][m]['setup_counts'] for m in METHODS}))
    expected_keys = {(life, q, m, r) for life in LIVES for q in QUERIES for m in METHODS for r in range(REPLICAS)}
    checks['game_roster'] &= set(indexed) == expected_keys
    full = full_game_comparison(indexed, valid)
    summary = {}
    for query in QUERIES:
        summary[query] = {}
        for split in ('TRAIN', 'VALIDATION'):
            group = [diagnostics[query][life][split] for life in LIVES]
            summary[query][split] = dict(lifecycles=[dict(life=life, **diagnostics[query][life][split]) for life in LIVES],
                utility_mse=mean(d['utility_mse'] for d in group), zero_utility_mse=mean(d['zero_utility_mse'] for d in group),
                component_mse=[mean(d['component_mse'][k] for d in group) for k in range(3)],
                selected_h1=sum(d['selected_h1'] for d in group), action_disagreements=sum(d['action_disagreements'] for d in group),
                selected_realized_advantage=mean(d['selected_realized_advantage'] for d in group))
    return dict(schema='acfqp.paired_advantage.v144.analysis', complete=run['status'] == 'complete' and all(checks.values()),
        primary_complete=full['complete'] and all(checks.values()), checks=checks, full_games=full,
        diagnostics=summary, costs=costs, seconds=perf_counter()-started,
        interpretation='Validation MSE and H2-conditioned suffix outcomes are diagnostics; adoption requires new full-game utility improvement.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_paired_advantage_v144')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=len(result['checks']),
        failed=[k for k, v in result['checks'].items() if not v], seconds=result['seconds'])), flush=True)
    raise SystemExit(0 if result['complete'] else 1)
