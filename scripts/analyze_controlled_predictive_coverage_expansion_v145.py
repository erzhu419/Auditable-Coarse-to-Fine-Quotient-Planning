"""Independently audit active paired-experience expansion and fresh policy games."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_paired_advantage_v144 as prior

previous, h1, planning, old = prior.previous, prior.h1, prior.planning, prior.old
LIVES, QUERIES, REPLICAS = prior.LIVES, prior.QUERIES, 8
BASE, MAX_STEPS, PASSES, ALPHA = 145*100000000, 2000, 32, .1
METHODS = ('H2', 'PRIOR', 'REPLAY', 'UPDATED')
LEARNERS = METHODS[1:]
COMPARISONS = {'UPDATED-H2': ('UPDATED', 'H2'), 'UPDATED-PRIOR': ('UPDATED', 'PRIOR'),
    'UPDATED-REPLAY': ('UPDATED', 'REPLAY'), 'REPLAY-PRIOR': ('REPLAY', 'PRIOR')}
mean, add_checks = prior.mean, prior.add_checks
close, compact_choice_valid, gate_checks = prior.close, prior.compact_choice_valid, prior.gate_checks
new_cost, add_cost, unprefix = prior.new_cost, prior.add_cost, prior.unprefix
fit_oracle, model_matches = prior.fit_oracle, prior.model_matches

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


def selected_game_roots(game):
    """Select by trajectory order and candidate actions, never by suffix outcomes."""
    board = list(game['initial_board']); eligible = []
    for step, choice in enumerate(game['choices']):
        pair = choice['selection']; a, b = pair['candidate_choice'], pair['baseline_choice']
        if a['action'] != b['action'] and max(a['afterstate']) < 11 and max(b['afterstate']) < 11:
            eligible.append(dict(life=game['life'], query=game['query'], replica=game['replica'],
                seed=game['seed'], step=step, board=board[:], previous_action=choice['previous_action'],
                simulation_seed=choice['simulation_seed'], choices=dict(H2=b['action'], H1_CONT=a['action']),
                candidate_after=a['afterstate'], baseline_after=b['afterstate'],
                candidate_score=a['score'], baseline_score=b['score'],
                immediate_difference=(a['score']-b['score'])/2048.))
        board = list(choice['afterstate']); board[game['spawned_cells'][step]] = game['spawned_ranks'][step]
    roots = []
    if len(eligible) >= 4:
        for slot in range(4):
            ordinal = ((2*slot+1)*len(eligible))//8
            roots.append(dict(**eligible[ordinal], slot=slot, source_ordinal=ordinal,
                root_id=f"v145:{game['life']}:{game['query']}:{game['replica']}:{eligible[ordinal]['step']}",
                actions=sorted(eligible[ordinal]['choices'].values()),
                source_game_roots=len(eligible), suffix_seeds=[BASE+game['life']*1000000+
                    list(QUERIES).index(game['query'])*100000+game['replica']*10000+slot*100+s for s in range(8)]))
    return roots, len(eligible)


def source_cohort(sources):
    roots, games, checks = [], [], dict(source_game_roster=True, source_selection=True, source_trace_chain=True)
    reads = Counter()
    for source in sources:
        for game in old.read_rows(source['advantage_control_trace']):
            reads['physical_game_records'] += 1
            if game['method'] != 'LEARNED': continue
            games.append((game['life'], game['query'], game['replica']))
            reads.update(learned_games=1, learned_decisions=len(game['choices']))
            checks['source_trace_chain'] &= (game['life'] == source['life'] and old.compact_valid(game)
                and len(game['choices']) == game['result']['steps'])
            selected, eligible = selected_game_roots(game)
            reads['eligible_decisions'] += eligible
            checks['source_selection'] &= len(selected) == 4
            roots.extend(selected)
    expected = {(life, query, replica) for life in LIVES for query in QUERIES for replica in range(REPLICAS)}
    checks['source_game_roster'] &= len(games) == len(set(games)) == 64 and set(games) == expected
    roots.sort(key=lambda row: (row['life'], list(QUERIES).index(row['query']), row['replica'], row['slot']))
    return roots, reads, checks


def training_sequences(old_examples, new_examples, life, query):
    selected = lambda rows: [e for e in rows if e['life'] == life and e['query'] == query and e['split'] == 'TRAIN']
    old_train, new_train = selected(old_examples), selected(new_examples)
    return dict(PRIOR=old_train, REPLAY=old_train+old_train, UPDATED=old_train+new_train)


def fit_work_valid(work, expected):
    n = expected['attempts']
    return (work.get('update_calls', 0) == n and work.get('pair_updates', 0) == expected['updates']
        and work.get('unidentifiable_pairs', 0) == n-expected['updates']
        and work.get('pair_predictions', 0) == n and work.get('feature_board_reads', 0) == 32*n
        and work.get('feature_rank_reads', 0) == 384*n
        and work.get('component_weight_updates', 0) == 3*work.get('weight_address_updates', 0))


def state(payload):
    return {key: payload[key] for key in ('radix', 'updates', 'frozen', 'weights')}


def expected_settings():
    return dict(lifecycles=list(LIVES), queries=QUERIES, replicas=REPLICAS, workers=4,
        methods=list(METHODS), train_replicas=[0,1,2,3], validation_replicas=[4,5,6,7],
        roots_per_game=4, suffixes_per_root=8, expected_roots=256, physical_branches=4096,
        root_selection='V144 LEARNED nonterminal candidate disagreements; floor((2*j+1)*n/8), j=0..3',
        epochs=PASSES, alpha=ALPHA, training_order=dict(PRIOR='retained V144 frozen model',
            REPLAY='old TRAIN then old TRAIN per pass', UPDATED='old TRAIN then new TRAIN per pass'),
        update='normalized LMS on exact signed n-tuple multiplicities; denominator=sum(x*x)',
        target='mean paired H1_CONT minus H2 reward/failure/success; subtract immediate reward difference',
        representation='SINGLE', continuation='H2', gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1, max_steps=MAX_STEPS, physical_games=256, version_base=BASE,
        cutoff_rule='retain all costs; incomplete supervision blocks fitting; no replacement',
        diagnostic_policy='no validation-dependent selection, refitting or early stopping')


def summarize_diagnostics(cells):
    return dict(lifecycles=cells, utility_mse=mean(d['utility_mse'] for d in cells),
        zero_utility_mse=mean(d['zero_utility_mse'] for d in cells),
        component_mse=[mean(d['component_mse'][k] for d in cells) for k in range(3)],
        selected_h1=sum(d['selected_h1'] for d in cells),
        action_disagreements=sum(d['action_disagreements'] for d in cells),
        selected_realized_advantage=mean(d['selected_realized_advantage'] for d in cells))


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen, frozen_training, cohort, retained = (read(name) for name in
        ('run.json', 'source_capsule.json', 'frozen_inputs.json', 'frozen_training.json', 'cohort.json', 'examples.json'))
    checks = dict(frozen_settings=run['settings'] == expected_settings(), source_roster=True,
        frozen_before_acquisition=(frozen['status'] == 'frozen' and not frozen['acquisition_lifecycles']
            and not frozen['lifecycles'] and not frozen['eval_lifecycles']
            and all(frozen[k] == run[k] for k in ('settings', 'inherited_costs'))),
        all_models_frozen_before_evaluation=(frozen_training['status'] == 'trained_frozen'
            and not frozen_training['eval_lifecycles'] and all(frozen_training[k] == run[k]
                for k in ('settings', 'inherited_costs', 'acquisition_lifecycles', 'lifecycles'))),
        source_complete=True, source_references=True, inherited_costs=True,
        cohort_exact_roster=True, cohort_counts=True, paired_record_roster=True,
        shared_suffix_seeds=True, distinct_action_branches=True, branch_roots=True,
        frozen_continuation=True, query_roster=True, model_loads=True, frozen_leaves=True,
        planner_spawn_law=True, acquisition_accounting=True, lifecycle_rosters=True,
        example_roster=True, exact_paired_targets=True, whole_game_split=True,
        model_bindings=True, fixed_training_order=True, normalized_lms_weights=True,
        prior_weights_unchanged=True, training_work=True, frozen_advantage_models=True,
        validation_predictions=True, planner_totals=True, game_roster=True)
    sources = {s['life']: s for s in capsule['snapshots']}
    checks['source_roster'] &= len(capsule['snapshots']) == 4 and set(sources) == set(LIVES)
    source_dir = Path(capsule['prior_run_ref']).parent
    original_run, original_capsule, original_analysis = (json.loads((source_dir/name).read_text())
        for name in ('run.json', 'source_capsule.json', 'analysis.json'))
    checks['source_complete'] &= original_run['status'] == 'complete' and original_analysis['complete'] and original_analysis['primary_complete']
    initial = json.loads((source_dir/'analysis_initial_fail/analysis.json').read_text())['costs']
    history = dict(extra_initial_work={k: initial[k] for k in ('analysis_replay_swipes', 'analysis_lms_attempts')},
        attempts=[{k: record[k] for k in ('status', 'seconds', 'stderr_bytes')} for record in
            (json.loads((source_dir/'analysis_initial_fail/analysis_attempt.json').read_text()),
             json.loads((source_dir/'analysis_attempt2.json').read_text()))])
    checks['inherited_costs'] &= run['inherited_costs'] == capsule['inherited_costs'] == {
        **original_capsule['inherited_costs'], 'v144_experiment': original_analysis['costs'],
        'v144_analysis_history': history}
    checks['source_references'] &= Path(capsule['prior_examples_ref']) == source_dir/'examples.json'
    for life, source in sources.items():
        original = next(s for s in original_capsule['snapshots'] if s['life'] == life)
        original_eval = next(s for s in original_run['eval_lifecycles'] if s['life'] == life)
        original_fit = next(s for s in original_run['lifecycles'] if s['life'] == life)
        copied = dict(source); copied.pop('advantage_control_trace'); copied.pop('prior_models')
        checks['source_references'] &= (copied == original
            and Path(source['advantage_control_trace']) == source_dir/original_eval['control_trace']
            and source['prior_models'] == {q: str(source_dir/original_fit['queries'][q]['model_ref']) for q in QUERIES})
    expected_roots, source_reads, source_checks = source_cohort(capsule['snapshots']); add_checks(checks, source_checks)
    checks['cohort_exact_roster'] &= (len(cohort['roots']) == len(expected_roots) == 256
        and all(all(actual.get(key) == value for key, value in expected.items())
            for actual, expected in zip(cohort['roots'], expected_roots)))
    roots = {r['root_id']: r for r in cohort['roots']}
    checks['cohort_counts'] &= (len(roots) == 256 and cohort['physical_branches'] == 4096
        and cohort['paired_records'] == 2048 and cohort['source_rows_read'] == dict(source_reads)
        and source_reads['physical_game_records'] == 192 and all(len(r['actions']) == len(set(r['actions'])) == 2
            and set(r['actions']) == set(r['choices'].values()) for r in roots.values()))
    checks['lifecycle_rosters'] &= all(len(run[key]) == 4 and {r['life'] for r in run[key]} == set(LIVES)
        for key in ('acquisition_lifecycles', 'lifecycles', 'eval_lifecycles'))
    costs = dict(new_acquisition=previous.new_cost(), acquisition_by_query={q: previous.new_cost() for q in QUERIES},
        new_control=new_cost(), by_method={m: new_cost() for m in METHODS},
        by_query={q: {m: new_cost() for m in METHODS} for q in QUERIES}, source_rows_read=dict(source_reads),
        training_counts=Counter(), training_by_method={m: Counter() for m in LEARNERS}, validation_counts=Counter(),
        training_seconds=sum(r['seconds'] for r in run['lifecycles']), model_accounting=[],
        coverage=[],
        acquisition_seconds=sum(r['seconds'] for r in run['acquisition_lifecycles']),
        analysis_replay_swipes=0, analysis_lms_attempts=0)
    records = {key: [] for key in roots}; seen = []; reads = Counter(); acquisition_terminal = True
    for lifecycle in run['acquisition_lifecycles']:
        life = lifecycle['life']; source = sources[life]
        local = {q: previous.new_cost() for q in QUERIES}; pairs = Counter()
        for row in old.read_rows(directory/lifecycle['consequences_trace']):
            seen.append((row['root_id'], row['suffix'])); root = roots.get(row['root_id'])
            checks['paired_record_roster'] &= root is not None and root['life'] == life and 0 <= row['suffix'] < 8
            if root is None: continue
            query = root['query']; pairs[query] += 1
            checks['shared_suffix_seeds'] &= row['seed'] == root['suffix_seeds'][row['suffix']]
            checks['frozen_continuation'] &= row['continuation'] == 'H2'
            checks['distinct_action_branches'] &= set(row['branches']) == set(root['actions'])
            reads.update(paired_records=1, physical_branches=len(row['branches']))
            for action, branch in row['branches'].items():
                checks['branch_roots'] &= (branch['root_board'] == root['board'] and branch['first_action'] == action
                    and branch['seed'] == row['seed'])
                branch_checks, swipes = previous.replay_branch(branch, query); add_checks(checks, branch_checks)
                costs['analysis_replay_swipes'] += swipes
                acquisition_terminal &= branch['result']['status'] in ('WON', 'LOST')
                for cell in (costs['new_acquisition'], costs['acquisition_by_query'][query], local[query]): previous.add_cost(cell, branch)
            records[row['root_id']].append(dict(root_id=row['root_id'], suffix=row['suffix'], seed=row['seed'],
                continuation=row['continuation'], branches={action: dict(result=branch['result'],
                    first_afterstate=branch['first_afterstate'], scores=branch['scores'][:1])
                    for action, branch in row['branches'].items()}))
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query, qdata in lifecycle['queries'].items():
            cell = local[query]
            checks['acquisition_accounting'] &= (qdata['roots'] == 32 and qdata['paired_records'] == pairs[query] == 256
                and qdata['physical_branches'] == cell['physical_branches'] == 512
                and all(Counter(qdata[k]) == cell[k] for k in ('statuses', 'environment_counts', 'policy_counts')))
            checks['model_loads'] &= h1.teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['frozen_leaves'] &= (qdata['parent_before'] == qdata['parent_after'] == planning.previous.model_state(source, query, 'PARENT', 0)
                and qdata['leaf_before'] == qdata['leaf_after'] == planning.expected_model_state(source, query, 'SINGLE'))
            checks['planner_spawn_law'] &= qdata['spawn_probabilities'] == planning.expected_spawn_probabilities(source)
            costs['model_accounting'].append(dict(stage='acquisition', life=life, query=query, loads=qdata['loads']))
    checks['paired_record_roster'] &= (len(seen) == len(set(seen)) == 2048
        and set(seen) == {(root, suffix) for root in roots for suffix in range(8)})
    checks['distinct_action_branches'] &= costs['new_acquisition']['physical_branches'] == 4096
    expected_examples = []
    for root in cohort['roots']:
        target, values = prior.suffix_target(root, records[root['root_id']]); add_checks(checks, values)
        expected_examples.append(dict(root_id=root['root_id'], life=root['life'], query=root['query'], replica=root['replica'],
            slot=root['slot'], step=root['step'], split='TRAIN' if root['replica'] < 4 else 'VALIDATION',
            candidate_action=root['choices']['H1_CONT'], baseline_action=root['choices']['H2'], **target, suffixes=8, origin='V145'))
        costs['analysis_replay_swipes'] += 2
    checks['example_roster'] &= len(retained['examples']) == len({e['root_id'] for e in retained['examples']}) == 256
    checks['exact_paired_targets'] &= all(all(actual.get(k) == v for k, v in expected.items())
        for actual, expected in zip(retained['examples'], expected_examples))
    checks['acquisition_accounting'] &= retained['source_rows_read'] == dict(reads) and reads == Counter(paired_records=2048, physical_branches=4096)
    old_examples = json.loads(Path(capsule['prior_examples_ref']).read_text())['examples']
    groups = dict(OLD=old_examples, NEW=retained['examples'])
    checks['whole_game_split'] &= all(Counter((e['life'], e['query'], e['split']) for e in rows)
        == Counter({(life, query, split): 16 for life in LIVES for query in QUERIES for split in ('TRAIN', 'VALIDATION')})
        and all(e['split'] == ('TRAIN' if e['replica'] < 4 else 'VALIDATION') for e in rows) for rows in groups.values())
    models, diagnostics = {}, {q: {origin: {split: {m: [] for m in LEARNERS} for split in ('TRAIN', 'VALIDATION')}
        for origin in groups} for q in QUERIES}
    trained = {r['life']: r for r in run['lifecycles']}
    for life in LIVES:
        source, lifecycle = sources[life], trained[life]
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for query in QUERIES:
            qdata = lifecycle['queries'][query]; sequences = training_sequences(old_examples, expected_examples, life, query)
            coverage = dict(life=life, query=query, train={}, weight_addresses={})
            for origin, rows in (('OLD', sequences['PRIOR']), ('NEW', sequences['UPDATED'][16:])):
                differences = [prior.feature_difference(e['candidate_after'], e['baseline_after']) for e in rows]
                coverage['train'][origin] = dict(roots=len(rows), nonzero_pairs=sum(bool(d) for d in differences),
                    distinct_addresses=len({address for difference in differences for address in difference}))
            costs['coverage'].append(coverage)
            checks['model_bindings'] &= qdata['binding'] == dict(life=life, query=query, continuation='H2', leaf_ref=source['leaves'][query]['SINGLE']['model_ref'])
            checks['fixed_training_order'] &= (qdata['old_train_roots'] == [e['root_id'] for e in sequences['PRIOR']]
                and qdata['new_train_roots'] == [e['root_id'] for e in sequences['UPDATED'][16:]])
            checks['query_roster'] &= set(qdata['models']) == set(LEARNERS)
            for method in LEARNERS:
                mdata = qdata['models'][method]; payload = read(mdata['model_ref']); frozen_state = state(payload)
                expected = fit_oracle(sequences[method]); costs['analysis_lms_attempts'] += expected['attempts']
                models[life, query, method] = expected['weights']
                coverage['weight_addresses'][method] = len(expected['weights'])
                checks['normalized_lms_weights'] &= model_matches(payload, expected)
                checks['frozen_advantage_models'] &= (mdata['frozen_state'] == mdata['after_validation'] == frozen_state
                    and mdata['model_bytes'] == (directory/mdata['model_ref']).stat().st_size)
                checks['fixed_training_order'] &= mdata['training_roots'] == ([] if method == 'PRIOR' else [e['root_id'] for e in sequences[method]])
                if method == 'PRIOR':
                    original_payload = json.loads(Path(source['prior_models'][query]).read_text())
                    checks['prior_weights_unchanged'] &= frozen_state == state(original_payload) == mdata['before']
                    checks['training_work'] &= not any(mdata['fit_counts'].values())
                else:
                    checks['frozen_advantage_models'] &= mdata['before'] == dict(radix=11, updates=0, frozen=False, weights=[])
                    checks['training_work'] &= fit_work_valid(mdata['fit_counts'], expected) and expected['attempts'] == 1024
                costs['training_counts'].update(mdata['fit_counts']); costs['training_by_method'][method].update(mdata['fit_counts'])
                costs['model_accounting'].append(dict(stage='training', life=life, query=query, method=method,
                    model_bytes=mdata['model_bytes'], storage=payload['storage'], setup_counts=mdata['setup_counts'],
                    fit_counts=mdata['fit_counts'], total_counts=mdata['total_counts'],
                    checkpoint_counts={k: v for k, v in mdata['total_counts'].items() if k.startswith('checkpoint_')}))
                for origin, rows in groups.items():
                    validation = [e for e in rows if e['life'] == life and e['query'] == query and e['split'] == 'VALIDATION']
                    checks['fixed_training_order'] &= qdata['validation_roots'][origin] == [e['root_id'] for e in validation]
                    actual = qdata['validation'][origin][method]
                    predictions = [prior.expected_prediction(e, expected['weights']) for e in validation]
                    checks['validation_predictions'] &= len(actual) == 16 and all(prior.prediction_matches(a, b) for a, b in zip(actual, predictions))
                    costs['validation_counts'].update(qdata['validation_work'][origin][method])
                    for split in ('TRAIN', 'VALIDATION'):
                        cells = [e for e in rows if e['life'] == life and e['query'] == query and e['split'] == split]
                        diagnostics[query][origin][split][method].append(dict(life=life,
                            **prior.prediction_metrics(cells, expected['weights'], query)))
    indexed, valid = {}, {}
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]; per_query = {q: {m: Counter() for m in METHODS} for q in QUERIES}
        checks['query_roster'] &= set(lifecycle['queries']) == set(QUERIES)
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key = row['life'], row['query'], row['method'], row['replica']
            checks['game_roster'] &= (key not in indexed and key[0] == life and key[1] in QUERIES
                and key[2] in METHODS and key[3] in range(REPLICAS))
            weights = {} if row['method'] == 'H2' else models[life, row['query'], row['method']]
            row_checks, swipes = control_checks(row, weights); add_checks(checks, row_checks)
            indexed[key], valid[key] = dict(result=row['result']), all(row_checks.values())
            costs['analysis_replay_swipes'] += swipes
            for cell in (costs['new_control'], costs['by_method'][row['method']], costs['by_query'][row['query']][row['method']]): add_cost(cell, row)
            per_query[row['query']][row['method']].update(row['result']['policy_counts'])
        for query, qdata in lifecycle['queries'].items():
            checks['model_loads'] &= h1.teacher_analysis.teacher_loads_valid(qdata['loads'], source, 'SINGLE', query)
            checks['frozen_leaves'] &= (qdata['parent_before'] == qdata['parent_after'] == planning.previous.model_state(source, query, 'PARENT', 0)
                and qdata['leaf_before'] == qdata['leaf_after'] == planning.expected_model_state(source, query, 'SINGLE'))
            checks['query_roster'] &= set(qdata['planners']) == set(METHODS)
            teacher_total, candidate_total = Counter(), Counter()
            for method, mdata in qdata['planners'].items():
                work = per_query[query][method]; checks['planner_totals'] &= Counter(mdata['counts']) == work
                if method == 'H2':
                    teacher_total.update(work); checks['frozen_advantage_models'] &= mdata['model_before'] is None and mdata['model_after'] is None
                else:
                    teacher_total.update(unprefix(work, 'baseline_')); candidate_total.update(unprefix(work, 'candidate_'))
                    frozen_state = trained[life]['queries'][query]['models'][method]['frozen_state']
                    checks['frozen_advantage_models'] &= mdata['model_before'] == mdata['model_after'] == frozen_state
            checks['planner_totals'] &= teacher_total == Counter(qdata['teacher_total_counts']) and candidate_total == Counter(qdata['candidate_total_counts'])
            costs['model_accounting'].append(dict(stage='control', life=life, query=query, loads=qdata['loads'],
                candidate_setup_counts=qdata['candidate_setup_counts'], candidate_setup_seconds=qdata['candidate_setup_seconds'],
                learner_setup_counts={m: qdata['planners'][m]['setup_counts'] for m in METHODS}))
    checks['game_roster'] &= set(indexed) == {(life, q, m, r) for life in LIVES for q in QUERIES for m in METHODS for r in range(REPLICAS)}
    full = full_game_comparison(indexed, valid)
    summary = {q: {origin: {split: {m: summarize_diagnostics(diagnostics[q][origin][split][m]) for m in LEARNERS}
        for split in ('TRAIN', 'VALIDATION')} for origin in groups} for q in QUERIES}
    costs['new_acquisition_environment_samples'] = costs['new_acquisition']['environment_counts'].get('sampled_transitions', 0)
    costs['new_control_environment_samples'] = costs['new_control']['environment_counts'].get('sampled_transitions', 0)
    costs['new_environment_samples'] = costs['new_acquisition_environment_samples']+costs['new_control_environment_samples']
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.coverage_expansion.v145.analysis', complete=complete,
        primary_complete=complete and acquisition_terminal and full['complete'], checks=checks,
        full_games=full, diagnostics=summary, costs=costs, inherited_work=run['inherited_costs'],
        seconds=perf_counter()-started,
        interpretation='New root outcomes remain H2-conditioned; fresh full games compare added experience against prior and matched replay attempts.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_coverage_expansion_v145')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=len(result['checks']),
        failed=[k for k, v in result['checks'].items() if not v], seconds=result['seconds'])), flush=True)
    raise SystemExit(0 if result['complete'] else 1)
