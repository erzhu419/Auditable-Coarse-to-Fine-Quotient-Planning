"""Reconcile fresh-stream confirmed-context TD, retained queues and outcomes."""
import argparse
from collections import Counter
from itertools import groupby
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts import analyze_controlled_predictive_ntuple_regime_v121 as old
from acfqp.science.controlled_predictive_confirmed_context_v124 import ConfirmedSpawnMemory

LIVES, QUERIES, PHASES = old.LIVES, old.QUERIES, old.PHASES
METHODS, LABELS = ('CONT', 'DELAY', 'BANK'), (0, 524288)
BUDGET, REPLICAS, BASE = 524288, 8, 125 * 100000000
DENSE_BYTES = 4 * 11**6 * 8


def train_seed(life, query, phase, episode):
    return BASE + 1000000 + life * 10000000 + QUERIES.index(query) * 4000000 + PHASES.index(phase) * 1000000 + episode


def evaluation_seed(life, phase, replica):
    return BASE + 90000000 + life * 100000 + PHASES.index(phase) * 10000 + replica


def initial_router(ranks):
    result = ConfirmedSpawnMemory()
    for rank in ranks:
        result.observe(rank)
    return result


def initial_state(ranks, updates, method, manifest=None):
    delayed = method in ('DELAY', 'BANK')
    return dict(method=method, updates=updates,
        router=(ConfirmedSpawnMemory.from_payload(manifest['router']) if manifest else initial_router(ranks)) if delayed else None,
        bank_updates={row['bank_id']: row['updates'] for row in manifest['banks']} if manifest else {0: updates},
        pending=[], max_pending=0)


def pending_descriptor(row):
    return {key: row[key] for key in ('obs_index', 'origin_context_id', 'target', 'target_context_id')}


def replay_game(row, state, training=True):
    """Replay causal contexts and queued TD accounting without learned values."""
    method, router = state['method'], state['router']
    r = row['result']; n = r['steps']; delayed = router is not None
    before_updates = state['updates']
    checks = dict(causal_contexts=True, routing_events=True, td_targets=True,
        commit_events=True, pending_carry=True, replay_counters=True)
    diagnostics = Counter()
    if not delayed:
        checks['causal_contexts'] = all(not row[key] for key in ('context_ids', 'bank_ids', 'routing_events', 'commit_events', 'td_targets', 'target_context_ids'))
        applied = n - int(r['status'] in ('WON', 'CUTOFF')) if training else 0
        state['updates'] += applied; state['bank_updates'][0] += applied
        return dict(checks=checks, applied=applied, censored=0, diagnostics=dict(diagnostics))
    arrays = ('context_ids', 'bank_ids') + (('td_targets', 'target_context_ids') if training else ())
    if any(len(row[key]) != n for key in arrays):
        checks['causal_contexts'] = False
        return dict(checks=checks, applied=0, censored=0, diagnostics={})
    checks['pending_carry'] &= (r['router_observations_before'] == router.observations_seen
        and r['pending_before'] == (len(state['pending']) if training else 0))
    events, commits = [], []
    counters_before = router.counts.copy()
    expected = Counter(); old_max = state['max_pending']
    if not training:
        expected['evaluation_weight_views'] = len(state['bank_updates'])
        expected['evaluation_shared_parameters'] = len(state['bank_updates']) * DENSE_BYTES // 8
    for index, rank in enumerate(row['spawned_ranks']):
        origin = router.module_id
        bank_id = origin if method == 'BANK' else 0
        checks['causal_contexts'] &= row['context_ids'][index] == origin and row['bank_ids'][index] == bank_id
        diagnostics['source_context_actions'] += origin == 0
        event = router.observe(rank)
        if event is not None:
            events.append(dict(event, observed_action_index=index))
            diagnostics['creations'] += event['kind'] == 'created'
            diagnostics['reactivations'] += event['kind'] == 'reactivated'
            if event['kind'] == 'created' and method == 'BANK':
                state['bank_updates'][event['module_id']] = state['bank_updates'][event['previous_module_id']]
                expected['bank_creations'] += 1
                if training:
                    expected['bank_weight_copies'] += 1
                    expected['bank_copied_parameters'] += DENSE_BYTES // 8
                    expected['bank_copied_bytes'] += DENSE_BYTES
                else:
                    expected['evaluation_weight_views'] += 1
                    expected['evaluation_shared_parameters'] += DENSE_BYTES // 8
        if not training:
            continue
        target, target_context = row['td_targets'][index], row['target_context_ids'][index]
        terminal = index == n - 1
        if terminal:
            expected_target = (-4. if row['query'] == 'risk_goal' else 0.) if r['status'] == 'LOST' else None
            checks['td_targets'] &= target == expected_target and target_context is None
        else:
            checks['td_targets'] &= isinstance(target, (float, int)) and math.isfinite(target) and target_context == router.module_id
        expected['queued_transitions'] += 1
        expected['queued_targets'] += target is not None
        expected['queued_untargeted_transitions'] += target is None
        state['pending'].append(dict(obs_index=router.observations_seen,
            origin_context_id=origin, target=target,
            target_context_id=None if terminal else router.module_id))
        state['max_pending'] = max(state['max_pending'], len(state['pending']))
        if event is not None and event['committed_n']:
            destination = router.module_id
            destination_bank = destination if method == 'BANK' else 0
            commit = dict(obs_index=router.observations_seen,
                committed_n=len(state['pending']), context_id=destination, bank_id=destination_bank,
                applied=0, censored=0, untargeted=0, observed_action_index=index)
            checks['pending_carry'] &= len(state['pending']) == event['committed_n']
            for pending in state['pending']:
                if pending['target'] is None:
                    commit['untargeted'] += 1
                elif pending['origin_context_id'] != destination or pending['target_context_id'] not in (None, destination):
                    commit['censored'] += 1
                else:
                    commit['applied'] += 1
            state['updates'] += commit['applied']
            state['bank_updates'][destination_bank] += commit['applied']
            expected['committed_batches'] += 1
            expected['committed_transitions'] += commit['committed_n']
            expected['cross_context_target_skips'] += commit['censored']
            expected['committed_untargeted_transitions'] += commit['untargeted']
            state['pending'] = []; commits.append(commit)
    applied = state['updates'] - before_updates
    expected['max_pending_transitions'] = state['max_pending'] - old_max
    checks['routing_events'] = events == row['routing_events']
    checks['commit_events'] = commits == row['commit_events']
    checks['causal_contexts'] &= row['final_context_id'] == router.module_id
    checks['pending_carry'] &= (r['router_observations_after'] == router.observations_seen
        and r['pending_after'] == (len(state['pending']) if training else 0)
        and len(state['pending']) <= 128)
    if not training:
        checks['td_targets'] &= not row['td_targets'] and not row['target_context_ids']
    for key, value in router.counts.items():
        expected[f'router_{key}'] = value - counters_before.get(key, 0)
    learn = r['learning_counts']
    checks['replay_counters'] = all(learn.get(key, 0) == value for key, value in expected.items())
    diagnostics.update(applied_targets=applied, censored_targets=expected['cross_context_target_skips'],
        queued_targets=expected['queued_targets'], committed_untargeted=expected['committed_untargeted_transitions'])
    return dict(checks=checks, applied=applied, censored=expected['cross_context_target_skips'], diagnostics=dict(diagnostics))


def inspect_training(rows, life, query, phase, state, budget=BUDGET):
    method = state['method']; transitions = episodes = 0
    checks = dict(training_roster=True, training_seeds=True, training_trace=True,
        training_caps=True, exact_training_budget=True, td_update_timing=True,
        native_update_counters=True, no_model_spawns=True)
    cost, blocks, block = old.new_cost(), [], old.empty_block(0, 0)
    diagnostics = Counter()
    for index, row in enumerate(rows):
        r = row['result']; n = r['steps']; status = r['status']; updates = state['updates']
        checks['training_roster'] &= (row['life'], row['query'], row['phase'], row['method'], row['episode_index']) == (life, query, phase, method, index)
        checks['training_seeds'] &= row['seed'] == train_seed(life, query, phase, index)
        checks['training_trace'] &= old.compact_valid(row) and status in ('WON', 'LOST', 'CUTOFF')
        cap = min(2000, budget - transitions)
        checks['training_caps'] &= row['max_steps'] == cap and 0 < n <= cap and (status != 'CUTOFF' or n == cap)
        checks['exact_training_budget'] &= row['transitions_before'] == transitions and row['transitions_after'] == transitions + n <= budget
        replay = replay_game(row, state)
        for key, value in replay['checks'].items(): checks[key] = checks.get(key, True) and value
        checks['td_update_timing'] &= (r['updates_before'] == updates and r['updates_after'] == state['updates']
            and row['terminal_target'] == (status == 'LOST') and row['analytic_terminal'] == (status == 'WON')
            and row['censored_last_update'] == (status == 'CUTOFF'))
        learn = r['learning_counts']
        checks['native_update_counters'] &= (learn.get('td_updates', 0) == replay['applied']
            and learn.get('choose_calls', 0) == n and learn.get('table_update_occurrences', 0) == 32 * replay['applied'])
        checks['no_model_spawns'] &= all(not r.get(field, {}).get('model_spawn_samples', 0) for field in old.FIELDS)
        diagnostics.update(replay['diagnostics'])
        old.add_cost(cost, row); transitions += n; episodes += 1
        block.update(end=episodes, transitions_after=transitions)
        block['games'] += 1; block['statuses'][status] += 1; block['total_score'] += r['score']; block['seconds'] += r['seconds']
        for field in ('environment_counts', 'learning_counts'): block[field].update(r[field])
        block.setdefault('setup_counts', Counter()).update(r['setup_counts'])
        block['setup_seconds'] = block.get('setup_seconds', 0.) + r['setup_seconds']
        if episodes % 64 == 0 or transitions == budget:
            blocks.append(block); block = old.empty_block(episodes, transitions)
    if block['games']: blocks.append(block)
    checks['exact_training_budget'] &= transitions == budget
    if state['router'] is not None:
        module = state['router'].modules[0]
        diagnostics.update(final_contexts=len(state['router'].modules), final_banks=len(state['bank_updates']),
            final_pending=len(state['pending']), max_pending=state['max_pending'])
        diagnostics['source_context_probability'] = module['alpha'] / (module['alpha'] + module['beta'])
    return dict(checks=checks, cost=cost, blocks=blocks, episodes=episodes, diagnostics=dict(diagnostics))


def outer_valid(row, checkpoint):
    r = row['result']; learn = r['learning_counts']
    okay = (old.compact_valid(row) and row['seed'] == evaluation_seed(row['life'], row['phase'], row['replica'])
        and row['max_steps'] == 2000 and r['status'] in ('WON', 'LOST', 'CUTOFF')
        and (r['status'] != 'CUTOFF' or r['steps'] == 2000)
        and r['updates_before'] == r['updates_after'] == checkpoint['updates']
        and learn.get('td_updates', 0) == 0 and learn.get('choose_calls', 0) == r['steps']
        and all(not r.get(field, {}).get('model_spawn_samples', 0) for field in old.FIELDS))
    state = initial_state([], checkpoint['updates'], row['method'], checkpoint.get('bank_manifest'))
    replay = replay_game(row, state, False)
    return bool(okay and all(replay['checks'].values())), replay['diagnostics']


def summaries(indexed, valid, cps):
    methods, contrasts = {}, {}
    for phase in PHASES:
        methods[phase], contrasts[phase] = {}, {}
        for method in ('FROZEN_A',) + METHODS:
            methods[phase][method] = {}
            for label in ((0,) if method == 'FROZEN_A' else LABELS):
                methods[phase][method][str(label)] = {}
                for query in QUERIES:
                    lives = []
                    for life in LIVES:
                        keys = [(life, query, phase, method, label, rep) for rep in range(REPLICAS)]
                        games = [indexed[key] for key in keys if key in indexed]
                        complete = len(games) == REPLICAS and all(valid.get(key, False) for key in keys)
                        lives.append(dict(life=life, complete=complete, games=len(games),
                            training_transitions=cps.get((life, query, phase, method, label), {}).get('transitions'),
                            means={field: old.mean(g['result'][field] for g in games) if complete else None for field in old.METRICS},
                            wins=sum(g['result']['status'] == 'WON' for g in games),
                            statuses=dict(Counter(g['result']['status'] for g in games))))
                    methods[phase][method][str(label)][query] = dict(lifecycles=lives,
                        complete=all(item['complete'] for item in lives),
                        lifecycle_mean={field: old.mean(item['means'][field] for item in lives) for field in old.METRICS},
                        wins=sum(item['wins'] for item in lives), games=sum(item['games'] for item in lives))
        for right in ('DELAY', 'CONT', 'FROZEN_A'):
            contrasts[phase][f'BANK_final_minus_{right}'] = {q: old.comparisons(
                methods[phase]['BANK'][str(BUDGET)][q],
                methods[phase][right][str(0 if right == 'FROZEN_A' else BUDGET)][q]) for q in QUERIES}
        contrasts[phase]['DELAY_final_minus_CONT'] = {q: old.comparisons(
            methods[phase]['DELAY'][str(BUDGET)][q], methods[phase]['CONT'][str(BUDGET)][q]) for q in QUERIES}
    retention = {method: {q: old.comparisons(methods['A_RETURN'][method]['0'][q],
        methods['A_RETURN']['FROZEN_A']['0'][q]) for q in QUERIES} for method in METHODS}
    return dict(methods=methods, comparisons=contrasts, return_initial_minus_frozen=retention,
        return_initial_bank_minus_control={method: {q: old.comparisons(
            methods['A_RETURN']['BANK']['0'][q], methods['A_RETURN'][method]['0'][q]) for q in QUERIES}
            for method in ('DELAY', 'CONT')})


def analyze(directory):
    directory = Path(directory).resolve()
    run = json.loads((directory / 'run.json').read_text())
    source = json.loads((directory / 'source_capsule.json').read_text())
    expected_settings = dict(lifecycles=list(LIVES), queries=dict(
        reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
        risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)),
        phases=old.P_FOUR, methods=list(METHODS), checkpoints=list(LABELS), train_transitions=BUDGET,
        replicas=REPLICAS, max_steps=2000, workers=4, alpha=.0025, version_base=BASE)
    checks = dict(frozen_settings=run['settings'] == expected_settings,
        lifecycle_roster=len(run['lifecycles']) == len(LIVES) and {r['life'] for r in run['lifecycles']} == set(LIVES),
        source_roster=source['schema'] == 'acfqp.confirmed_value.v125.source' and len(source['snapshots']) == len(LIVES)
            and {r['life'] for r in source['snapshots']} == set(LIVES),
        inherited_costs=source['inherited_costs'] == run['inherited_costs'],
        phase_method_roster=True, checkpoint_roster=True, source_rank_prefix=True,
        context_initialization=True, training_group_roster=True, training_blocks=True,
        checkpoint_state=True, bank_manifests=True, model_origins=True, sparse_models=True,
        model_setup=True, outer_roster=True, outer_aliases=True, outer_summaries=True, outer_causal_no_td=True)
    sources = {r['life']: r for r in source['snapshots']}
    cps, indexed, valid, training, outer_routing = {}, {}, {}, [], []
    cost, outer_cost = old.new_cost(), old.new_cost()
    train_by_phase = {p: {m: old.new_cost() for m in METHODS} for p in PHASES}
    outer_by_method = {m: old.new_cost() for m in ('FROZEN_A',) + METHODS}
    setup_counts, loads, saves, initial_counts = Counter(), Counter(), Counter(), Counter()
    setup_seconds = load_seconds = save_seconds = initial_seconds = eval_copy_seconds = 0.
    stored_bytes = saved_files = physical = aliases = peak_banks = peak_pending = 0
    sparse_cache = {}
    def sparse(path, updates, size=None):
        key = str(path), updates, size
        if key not in sparse_cache:
            cp = dict(model_ref=str(path), updates=updates)
            if size is not None: cp['model_bytes'] = size
            sparse_cache[key] = old.model_valid(directory, cp)
        return sparse_cache[key]
    for history in run['lifecycles']:
        life = history['life']; src = sources[life]
        checks['lifecycle_roster'] &= set(history['queries']) == set(QUERIES)
        for query, data in history['queries'].items():
            origin, ranks = src['models'][query], src['initial_ranks'][query]
            actual, rows_read = [], 0
            for row in old.read_rows(Path(src['initial_rank_sources'][query]['path'])):
                rows_read += 1; actual.extend(row['spawned_ranks'][:256 - len(actual)])
                if len(actual) == 256: break
            checks['source_rank_prefix'] &= len(ranks) == 256 and ranks == actual and rows_read == src['initial_rank_sources'][query]['rows_read']
            checks['sparse_models'] &= sparse(Path(origin['path']), origin['updates'])
            initial = initial_router(ranks).to_payload()
            for method in ('DELAY', 'BANK'):
                item = data['context_initialization'][method]
                checks['context_initialization'] &= item['router'] == initial and item['source'] == src['initial_rank_sources'][query]
                initial_counts.update(item['router']['counts']); initial_seconds += item['seconds']
            checks['phase_method_roster'] &= set(data['phases']) == set(PHASES)
            for phase in PHASES:
                phase_data = data['phases'][phase]
                checks['phase_method_roster'] &= phase_data['p_four'] == old.P_FOUR[phase] and set(phase_data['methods']) == {'FROZEN_A', *METHODS}
                for method, md in phase_data['methods'].items():
                    checks['checkpoint_roster'] &= [c['label'] for c in md['checkpoints']] == ([0] if method == 'FROZEN_A' else list(LABELS))
                    for cp in md['checkpoints']:
                        label = cp['label']; cps[life, query, phase, method, label] = cp
                        checks['checkpoint_roster'] &= cp['transitions'] == label
                        if method in ('DELAY', 'BANK'):
                            m = cp['bank_manifest']; ids = [b['bank_id'] for b in m['banks']]
                            checks['bank_manifests'] &= (m['schema'] == 'acfqp.confirmed_value.v125' and m['method'] == method and m['training_enabled']
                                and m['updates'] == cp['updates'] and m['initial_router'] == initial
                                and m['context_id'] == m['router']['active_module_id']
                                and m['active_bank_id'] == (m['context_id'] if method == 'BANK' else 0)
                                and ids == (list(range(len(m['router']['modules']))) if method == 'BANK' else [0]))
                            peak_banks = max(peak_banks, len(ids)); peak_pending = max(peak_pending, m['counts'].get('max_pending_transitions', 0))
                            if label:
                                checks['bank_manifests'] &= json.loads((directory / cp['model_ref']).read_text()) == m
                                files = {f['bank_id']: f for f in m['model_files']}
                                checks['bank_manifests'] &= set(files) == set(ids) and cp['model_bytes'] == sum(f['bytes'] for f in files.values())
                                for bank in m['banks']:
                                    f = files[bank['bank_id']]
                                    checks['sparse_models'] &= sparse(directory / f['path'], bank['updates'], f['bytes'])
                                saved_files += len(files)
                        elif label:
                            checks['sparse_models'] &= sparse(directory / cp['model_ref'], cp['updates'], cp['model_bytes'])
                            saved_files += 1
                        if label:
                            stored_bytes += cp['model_bytes']; saves.update(cp['save_counts']); save_seconds += cp['save_seconds']
                        elif method == 'FROZEN_A' or phase == 'B':
                            checks['model_origins'] &= cp['model_ref'] == origin['path'] and cp['updates'] == origin['updates']
                        else:
                            previous = cps[life, query, 'B', method, BUDGET]
                            checks['model_origins'] &= cp['model_ref'] == previous['model_ref'] and cp['updates'] == previous['updates']
            states = {m: initial_state(ranks, origin['updates'], m) for m in METHODS}
            groups = []
            for (phase, method), rows in groupby(old.read_rows(directory / data['training_trace']), key=lambda r: (r['phase'], r['method'])):
                groups.append((phase, method)); state = states[method]
                md = data['phases'][phase]['methods'][method]
                before = cps[life, query, phase, method, 0]
                checks['checkpoint_state'] &= before['updates'] == state['updates']
                if method != 'CONT':
                    bm = before['bank_manifest']
                    checks['checkpoint_state'] &= (bm['router'] == state['router'].to_payload()
                        and [pending_descriptor(r) for r in bm['pending_transitions']] == state['pending']
                        and {b['bank_id']: b['updates'] for b in bm['banks']} == state['bank_updates'])
                found = inspect_training(rows, life, query, phase, state)
                for key, value in found['checks'].items(): checks[key] = checks.get(key, True) and value
                checks['training_blocks'] &= md['training_blocks'] == found['blocks'] and md['training_episodes'] == found['episodes']
                cp = cps[life, query, phase, method, BUDGET]
                checks['checkpoint_state'] &= cp['updates'] == md['final_updates'] == state['updates'] and md['final_transitions'] == BUDGET
                if method != 'CONT':
                    m = cp['bank_manifest']
                    checks['checkpoint_state'] &= (m['router'] == state['router'].to_payload()
                        and [pending_descriptor(r) for r in m['pending_transitions']] == state['pending']
                        and {b['bank_id']: b['updates'] for b in m['banks']} == state['bank_updates'])
                old.merge_cost(cost, found['cost']); old.merge_cost(train_by_phase[phase][method], found['cost'])
                training.append(dict(life=life, query=query, phase=phase, method=method,
                    games=found['episodes'], cost=found['cost'], diagnostics=found['diagnostics'], checks=found['checks']))
            checks['training_group_roster'] &= groups == [(p, m) for p in PHASES for m in METHODS]
            checks['model_setup'] &= [m['method'] for m in data['model_setup']] == ['FROZEN_A', *METHODS]
            for item in data['model_setup']:
                checks['model_setup'] &= (item['phase_origin'] == 'B' and item['origin_ref'] == origin['path']
                    and item['updates_at_creation'] == origin['updates']
                    and item['load_counts'] == dict(checkpoint_loads=1, checkpoint_loaded_parameters=origin['nonzero_weights']))
                setup_counts.update(item['setup_counts']); loads.update(item['load_counts'])
                setup_seconds += item['setup_seconds']; load_seconds += item['load_seconds']
            raw = list(old.read_rows(directory / data['control_trace'])); raw_index = {r['eval_id']: r for r in raw}
            logical = [r for p in PHASES for md in data['phases'][p]['methods'].values() for c in md['checkpoints'] for r in c['evaluations']]
            expected = {(life, query, p, m, c, rep) for p in PHASES for m in ('FROZEN_A',) + METHODS
                for c in ((0,) if m == 'FROZEN_A' else LABELS) for rep in range(REPLICAS)}
            alias_keys = {(life, query, 'B', 'CONT', 0, rep) for rep in range(REPLICAS)}
            checks['outer_roster'] &= (len(logical) == len(expected) and {old.outer_key(r) for r in logical} == expected
                and len(raw) == len(raw_index) == len(expected - alias_keys) and {old.outer_key(r) for r in raw} == expected - alias_keys)
            for row in raw:
                physical += 1; old.add_cost(outer_cost, row); old.add_cost(outer_by_method[row['method']], row)
                eval_copy_seconds += row['result'].get('evaluation_copy_seconds', 0.)
                checks['outer_aliases'] &= row['reused_from'] is None
            for row in logical:
                key = old.outer_key(row); alias = key in alias_keys; reuse = row['reused_from']; cp = cps[key[:-1]]
                aliases += alias; ref = raw_index.get(reuse or row['eval_id'])
                okay = bool(reuse) == alias and row['eval_id'] == '/'.join(map(str, key))
                if alias: okay &= reuse == f'{life}/{query}/B/FROZEN_A/0/{row["replica"]}'
                checks['outer_aliases'] &= okay
                omitted = {'eval_id', 'reused_from', 'method', 'checkpoint'} if alias else set()
                matches = ref is not None and all(ref.get(k) == v for k, v in row.items() if k not in omitted)
                checks['outer_summaries'] &= matches
                ready, diag = outer_valid({**ref, **row}, cp) if ref is not None else (False, {})
                checks['outer_causal_no_td'] &= ready
                indexed[key] = row; valid[key] = ready and okay and matches and row['result']['status'] != 'CUTOFF'
                if row['method'] in ('DELAY', 'BANK'):
                    outer_routing.append(dict(life=life, query=query, phase=row['phase'], method=row['method'],
                        checkpoint=row['checkpoint'], replica=row['replica'], **diag))
    checks['aggregate_training_budget'] = cost['environment_counts']['sampled_transitions'] == len(LIVES) * len(QUERIES) * len(PHASES) * len(METHODS) * BUDGET
    cohort = len(LIVES) * len(QUERIES) * REPLICAS
    checks['physical_logical_roster'] = physical == 13 * cohort and len(indexed) == 14 * cohort and aliases == cohort
    checks['bounded_pending_queue'] = peak_pending <= 128
    # These are maximum-state deltas, not additive operations. Peak queue size
    # is reported separately from final manifests instead of summed as work.
    all_costs = [cost, outer_cost, *outer_by_method.values(),
        *(c for by_method in train_by_phase.values() for c in by_method.values()),
        *(group['cost'] for group in training)]
    for item in all_costs:
        for key in ('max_pending_transitions', 'router_max_uncommitted_observations'):
            item['learning_counts'].pop(key, None)
    prior = Counter()
    for life in source['inherited_costs']['v120_training']:
        for query in life['queries'].values():
            for block in query['training_blocks']: prior.update(block['environment_counts'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.confirmed_value.v125.analysis', complete=complete,
        primary_complete=complete and all(valid.values()), checks={k: bool(v) for k, v in checks.items()},
        control=summaries(indexed, valid, cps), training=training, outer_routing=outer_routing,
        costs=dict(training=cost, training_by_phase_method=train_by_phase, outer=outer_cost,
            outer_by_method=outer_by_method, physical_outer_games=physical, logical_outer_rows=len(indexed), reused_outer_rows=aliases,
            actual_environment_transitions=cost['environment_counts']['sampled_transitions'] + outer_cost['environment_counts']['sampled_transitions'],
            model_load_counts=dict(loads), model_load_seconds=load_seconds,
            model_setup_counts=dict(setup_counts), model_setup_seconds=setup_seconds,
            source_context_processing_counts=dict(initial_counts), source_context_seconds=initial_seconds,
            model_save_counts=dict(saves), model_save_seconds=save_seconds,
            retained_model_bytes=stored_bytes, retained_model_files=saved_files,
            peak_resident_bank_count=peak_banks, peak_resident_bank_bytes=peak_banks * DENSE_BYTES,
            peak_pending_transitions=peak_pending, evaluation_copy_seconds=eval_copy_seconds,
            model_spawn_samples=sum(c[field].get('model_spawn_samples', 0) for c in (cost, outer_cost) for field in old.FIELDS)),
        inherited_work=dict(v120_training=dict(prior), details=source['inherited_costs']),
        seconds=run.get('seconds'), scope='Four inherited source histories, fresh fixed-budget learning and paired outer games; no significance or general-strategic-learning claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args(); report = analyze(args.run_dir)
    (args.run_dir / 'analysis.json').write_text(json.dumps(report, allow_nan=False, indent=2) + '\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'], checks=report['checks'])))
