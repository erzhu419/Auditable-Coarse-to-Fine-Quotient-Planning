"""Bounded goal-64 SOURCE acquisition and frozen finite-H3/H4 transfer."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import importlib
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_deep_transfer_v200 as core

OUTPUT = ROOT/'reports/controlled_predictive_deep_transfer_v200'
RUNTIME = ROOT/'reports/v200_runtime_tmp'
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
ARMS = ('COARSE', 'LEARNED', 'LEARNED_D1', 'NATIVE_H2')
QUERIES = {'reward': dict(reward_weight=1, failure_penalty=0, goal_bonus=0),
    'goal': dict(reward_weight=1, failure_penalty=0, goal_bonus=4),
    'risk': dict(reward_weight=1, failure_penalty=4, goal_bonus=4)}
PAIRS = ((0, 5), (1, 6), (0, 6), (0, 10), (1, 7), (4, 10),
         (5, 11), (2, 8), (3, 12), (5, 14), (6, 13), (2, 15))
SOURCE_BOUNDS = dict(rows=20000, outcomes=250000, boards=50000)
TARGET_BOUNDS = dict(rows=24000, outcomes=200000, boards=100000)


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'))+'\n')


def roster():
    cases = {'SOURCE': [], 'TARGET': []}
    for split, count, base in (('SOURCE', 32, 200100), ('TARGET', 24, 200200)):
        for index in range(count):
            seed = base+index; rng = random.Random(seed)
            board = [rng.randint(1, 4) for _ in range(16)]
            first, second = PAIRS[index%12]; board[first] = board[second] = 5
            if index%2:
                board[rng.choice([cell for cell in range(16) if cell not in (first, second)])] = 0
            cases[split].append(dict(root_id=f'v200_{split.lower()}_{index:02d}', seed=seed, board=board))
    return cases


class NativeLaw:
    """One full-support law cache; goal rank is six for this independent task."""
    def __init__(self, bounds):
        self.bounds = bounds; self.counts = Counter()
        self.states, self.index, self.moves, self.rows = [], {}, {}, {}
        self.evaluation_work = {}

    def observe(self, board):
        board = tuple(board); self.counts['observation_requests'] += 1
        if board in self.index:
            self.counts['observation_memo_hits'] += 1; return self.index[board]
        if len(self.states) >= self.bounds['boards']:
            raise RuntimeError('observed-board bound reached')
        sid = len(self.states); moves = {}; self.counts['board_maximum_scans'] += 1
        if max(board) >= 6:
            status, legal = 'WON', []
        else:
            for action in ACTIONS:
                self.counts['native_swipe_calls'] += 1
                moves[action] = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            legal = [action for action in ACTIONS if moves[action][2]]
            status = 'ACTIVE' if legal else 'LOST'
        self.states.append(dict(board=list(board), status=status, legal=legal))
        self.index[board] = sid; self.moves[sid] = moves
        self.counts['observed_boards'] += 1; self.counts['status_'+status] += 1; return sid

    def row(self, sid, action):
        self.counts['support_row_requests'] += 1; key = (sid, action)
        if key in self.rows:
            self.counts['support_row_memo_hits'] += 1; return self.rows[key]
        self.counts['support_row_attempts'] += 1
        if len(self.rows) >= self.bounds['rows']:
            raise RuntimeError('support-row bound reached')
        after, score, changed = self.moves[sid][action]
        if not changed:
            raise ValueError('native row requested an illegal action')
        empty = [cell for cell, rank in enumerate(after) if rank == 0]
        self.counts['post_swipe_empty_scans'] += 1
        reward = Fraction(score, 2048); self.counts['reward_normalizations'] += 1
        outcomes = []
        for cell in empty:
            for rank, mass in ((1, 9), (2, 1)):
                if self.counts['support_outcomes'] >= self.bounds['outcomes']:
                    raise RuntimeError('support-outcome bound reached')
                self.counts['support_outcomes'] += 1
                board = list(after); board[cell] = rank
                probability = Fraction(mass, 10*len(empty))
                self.counts['spawn_board_constructions'] += 1
                self.counts['probability_fraction_constructions'] += 1
                nxt = self.observe(board)
                outcomes.append([probability.numerator, probability.denominator, nxt, reward.numerator, reward.denominator])
        self.rows[key] = outcomes; self.counts['support_rows'] += 1; return outcomes

    def export(self, controlled=(), root_ids=()):
        return dict(states=self.states, rows=[[sid, action, outcomes] for (sid, action), outcomes in self.rows.items()],
            controlled=sorted(controlled), root_ids=list(root_ids))


def acquire_source(cases, law):
    root_ids = [law.observe(case['board']) for case in cases]
    controlled, frontier = set(), sorted(set(root_ids))
    for _ in range(2):
        following = set()
        for sid in frontier:
            state = law.states[sid]
            if state['status'] != 'ACTIVE' or sid in controlled:
                continue
            controlled.add(sid)
            for action in state['legal']:
                following.update(row[2] for row in law.row(sid, action))
        frontier = sorted(following)
    augmentations = 0
    while True:
        masks = {tuple(law.states[sid]['legal']) for sid in controlled}
        missing = next((sid for sid, state in enumerate(law.states)
            if state['status'] == 'ACTIVE' and tuple(state['legal']) not in masks), None)
        if missing is None:
            break
        controlled.add(missing); augmentations += 1
        law.counts['source_mask_augmentations'] += 1
        for action in law.states[missing]['legal']:
            law.row(missing, action)
    result = law.export(controlled, root_ids); result['mask_augmentations'] = augmentations
    return result


def utility(vector, query):
    return query['reward_weight']*vector[0]-query['failure_penalty']*vector[1]+query['goal_bonus']*vector[2]


def packed(vector, query, action=None):
    return dict(components=[float(value) for value in vector], component_fractions=[str(value) for value in vector],
        utility=float(utility(vector, query)), action=action)


class Evaluator:
    def __init__(self, law, models, plans):
        self.law, self.models, self.plans = law, models, plans
        self.work = defaultdict(Counter); self.oracle_cache, self.replay_cache, self.codes = {}, {}, {}
        self.action_vectors, self.transforms = {}, {}

    def terminal(self, sid, h):
        status = self.law.states[sid]['status']
        if status != 'ACTIVE' or h == 0:
            return [Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON')]
        return None

    def oracle(self, sid, h, query):
        counts = self.work['oracle']; counts['value_requests'] += 1; key = (sid, h, query)
        if key in self.oracle_cache:
            counts['value_memo_hits'] += 1; return self.oracle_cache[key]
        terminal = self.terminal(sid, h)
        if terminal is not None:
            result = (terminal, None)
        else:
            values = {}
            for action in self.law.states[sid]['legal']:
                vector = [Fraction(0)]*3
                for pn, pd, nxt, rn, rd in self.law.row(sid, action):
                    probability, reward = Fraction(pn, pd), Fraction(rn, rd)
                    tail = self.oracle(nxt, h-1, query)[0]
                    for component in range(3):
                        vector[component] += probability*(tail[component]+(reward if component == 0 else 0))
                    counts.update(outcome_evaluations=1, component_products=3, component_additions=3)
                values[action] = vector
            self.action_vectors[key] = values
            action = core.choose_action(values, QUERIES[query], counts); counts['action_selections'] += 1
            result = (values[action], action)
        self.oracle_cache[key] = result; counts['values_completed'] += 1; return result

    def code(self, mode, sid, h):
        key = (mode, sid, h); counts = self.work['encoding']; counts['code_requests'] += 1
        if key not in self.codes:
            state = self.law.states[sid]
            self.codes[key] = core.encode(self.models[mode], state['board'], h, state['status'], state['legal'], counts)
        else:
            counts['code_memo_hits'] += 1
        return self.codes[key]

    def policy(self, sid, h, arm, query):
        if arm == 'NATIVE_H2':
            self.work['native_h2']['policy_requests'] += 1
            return self.oracle(sid, min(2, h), query)[1], False
        mode = 'COARSE' if arm == 'COARSE' else 'LEARNED'; depth = 1 if arm == 'LEARNED_D1' else h
        cell = self.code(mode, sid, depth)
        self.work['replay']['policy_requests'] += 1
        if cell is None:
            self.work['replay']['unknown_mask_fallbacks'] += 1
            return self.law.states[sid]['legal'][0], True
        return self.plans[mode][query]['policy'][cell], False

    def replay(self, sid, h, arm, query):
        counts = self.work['replay']; counts['value_requests'] += 1; key = (sid, h, arm, query)
        if key in self.replay_cache:
            counts['value_memo_hits'] += 1; return self.replay_cache[key]
        terminal = self.terminal(sid, h)
        if terminal is not None:
            result = (terminal, Fraction(0), Fraction(0))
        else:
            action, fallback = self.policy(sid, h, arm, query)
            vector, visits, probability_any = [Fraction(0)]*3, Fraction(int(fallback)), Fraction(int(fallback))
            for pn, pd, nxt, rn, rd in self.law.row(sid, action):
                probability, reward = Fraction(pn, pd), Fraction(rn, rd)
                tail, tail_visits, tail_probability = self.replay(nxt, h-1, arm, query)
                for component in range(3):
                    vector[component] += probability*(tail[component]+(reward if component == 0 else 0))
                visits += probability*tail_visits
                if not fallback:
                    probability_any += probability*tail_probability
                counts.update(outcome_evaluations=1, component_products=3, component_additions=3,
                    fallback_visit_products=1, fallback_probability_products=int(not fallback))
            result = (vector, visits, probability_any)
        self.replay_cache[key] = result; counts['values_completed'] += 1; return result

    def predicted(self, sid, h, arm, query):
        if arm == 'NATIVE_H2':
            vector, action = self.oracle(sid, min(2, h), query)
            return packed(vector, QUERIES[query], action)
        mode = 'COARSE' if arm == 'COARSE' else 'LEARNED'; depth = 1 if arm == 'LEARNED_D1' else h
        cell = self.code(mode, sid, depth)
        if cell is None:
            return None
        plan = self.plans[mode][query]
        return packed(plan['values'][cell], QUERIES[query], plan['policy'].get(cell))

    def step_diagnostics(self, sid, h):
        cell = self.code('LEARNED', sid, h)
        if cell is None or self.law.states[sid]['status'] != 'ACTIVE':
            return None
        counts, result = self.work['step_diagnostics'], {}
        rows = {(owner, action): outcomes for owner, action, outcomes in self.models['LEARNED']['rows']}
        counts['model_row_index_reads'] += len(rows)
        for action in self.law.states[sid]['legal']:
            estimated, actual = defaultdict(Fraction), defaultdict(Fraction)
            estimated_reward, actual_reward, unknown = Fraction(0), Fraction(0), Fraction(0)
            for pn, pd, destination, rn, rd in rows[cell, action]:
                probability = Fraction(pn, pd); estimated[destination] += probability
                estimated_reward += probability*Fraction(rn, rd); counts['model_outcome_reads'] += 1
            for pn, pd, nxt, rn, rd in self.law.row(sid, action):
                probability = Fraction(pn, pd); destination = self.code('LEARNED', nxt, h-1)
                actual[-1 if destination is None else destination] += probability
                actual_reward += probability*Fraction(rn, rd)
                if destination is None:
                    unknown += probability
                counts.update(native_outcome_reads=1, successor_encoding_requests=1)
            variation = sum((abs(estimated[key]-actual[key]) for key in set(estimated)|set(actual)), Fraction(0))/2
            counts['tv_coordinate_reads'] += len(set(estimated)|set(actual))
            result[action] = dict(reward_error=float(abs(estimated_reward-actual_reward)),
                successor_tv=float(variation), unknown_successor_mass=float(unknown))
        return result

    def deep_counts(self, root, horizon):
        keys = dict(states=set(), rows=set(), D4_states=set(), D4_rows=set())
        counts = self.work['native_d4']; frontier = {root}
        for h in range(horizon, 1, -1):
            following = set()
            for sid in sorted(frontier):
                state = self.law.states[sid]
                if state['status'] != 'ACTIVE':
                    continue
                board = tuple(state['board']); keys['states'].add((h, board))
                if sid not in self.transforms:
                    self.transforms[sid] = [(ground.transform_board_v1(board, transform), transform)
                        for transform in ground.D4_ELEMENTS]
                    counts['native_board_transform_calls'] += len(ground.D4_ELEMENTS)
                options = self.transforms[sid]; keys['D4_states'].add((h, min(row[0] for row in options)))
                for action in state['legal']:
                    keys['rows'].add((h, board, action))
                    canonical = min((oriented, ground.transform_action_v1(ground.Swipe2048Action(action), transform).value)
                        for oriented, transform in options)
                    counts['native_action_transform_calls'] += len(options)
                    keys['D4_rows'].add((h, *canonical))
                    following.update(row[2] for row in self.law.row(sid, action))
                    counts['deep_graph_row_visits'] += 1
            frontier = following
        return benchmark_counts(keys, horizon), keys


def evaluate_case(case, law, models, plans):
    sid = law.observe(case['board']); evaluator = Evaluator(law, models, plans); evaluations = []
    law.evaluation_work = evaluator.work
    for h in (3, 4):
        for query, coefficients in QUERIES.items():
            oracle, action = evaluator.oracle(sid, h, query); arms = {}
            for arm in ARMS:
                actual, visits, probability = evaluator.replay(sid, h, arm, query)
                terminal = evaluator.terminal(sid, h)
                root_action = None if terminal is not None else evaluator.policy(sid, h, arm, query)[0]
                arms[arm] = dict(predicted=evaluator.predicted(sid, h, arm, query), actual=packed(actual, coefficients, root_action),
                    root_action=root_action, regret=float(utility(oracle, coefficients)-utility(actual, coefficients)),
                    fallback_probability=float(probability), fallback_probability_fraction=str(probability),
                    expected_fallback_visits=float(visits), expected_fallback_visits_fraction=str(visits))
            reference = packed(oracle, coefficients, action)
            action_vectors = evaluator.action_vectors.get((sid, h, query), {})
            reference.update(action_vectors={name: [float(value) for value in vector] for name, vector in action_vectors.items()},
                action_vector_fractions={name: [str(value) for value in vector] for name, vector in action_vectors.items()})
            evaluations.append(dict(horizon=h, query=query, oracle=reference, arms=arms))
    deep, keys = {}, {}
    for h in (3, 4):
        deep[str(h)], keys[str(h)] = evaluator.deep_counts(sid, h)
    record = dict(**case, evaluations=evaluations, native_deep=deep,
        step_diagnostics={str(h): evaluator.step_diagnostics(sid, h) for h in (3, 4)},
        native_status_counts={status: law.counts['status_'+status] for status in ('ACTIVE', 'WON', 'LOST')},
        costs=dict(native=dict(law.counts), **{name: dict(counts) for name, counts in evaluator.work.items()}))
    return record, keys


def benchmark_counts(keys, horizon):
    return dict(layers={str(h): dict(active_states=sum(row[0] == h for row in keys['states']),
        action_rows=sum(row[0] == h for row in keys['rows'])) for h in range(2, horizon+1)},
        D4_states=len(keys['D4_states']), D4_rows=len(keys['D4_rows']))


def plan_payload(plans):
    return {mode: {query: dict(values={str(cell): [str(value) for value in vector] for cell, vector in plan['values'].items()},
        policy={str(cell): action for cell, action in plan['policy'].items()}) for query, plan in modes.items()}
        for mode, modes in plans.items()}


def model_counts(model):
    layers = {}
    def tree_size(node):
        if 'cell' in node:
            return 1, 1
        left, right = tree_size(node['left']), tree_size(node['right'])
        return 1+left[0]+right[0], left[1]+right[1]
    cell_h = {cell: h for cell, h, _ in model['cells']}
    for h in range(1, 5):
        trees = [tree_size(row['tree']) for row in model['trees'][str(h)]]
        rows = [row for row in model['rows'] if cell_h[row[0]] == h]
        layers[str(h)] = dict(active_cells=sum(layer == h and status == 'ACTIVE' for _, layer, status in model['cells']),
            action_rows=len(rows), outcomes=sum(len(row[2]) for row in rows), tree_nodes=sum(row[0] for row in trees),
            tree_leaves=sum(row[1] for row in trees))
    return dict(layers=layers, serialized_bytes=len((json.dumps(model, ensure_ascii=False, separators=(',', ':'))+'\n').encode()),
        feature_columns=42, terminal_cells=3)


def summarize(records, models, benchmark):
    return importlib.import_module('scripts.deep_transfer_summary_v200').summarize(records, models, benchmark)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_deep_transfer_v200')
    importlib.import_module('scripts.deep_transfer_summary_v200')
    paths = {ROOT/relative for relative in ('src/acfqp/science/controlled_predictive_deep_transfer_v200.py',
        'scripts/run_controlled_predictive_deep_transfer_v200.py',
        'scripts/analyze_controlled_predictive_deep_transfer_v200.py', 'scripts/deep_transfer_summary_v200.py',
        'specs/DEEP_CONTROLLED_TRANSFER_V200.md', 'tests/test_deep_transfer_core_v200.py', 'tests/test_deep_transfer_runner_v200.py',
        'tests/test_deep_transfer_analysis_v200.py', 'src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py',
        'reports/v200_runtime_tmp/run_checks.py', 'reports/v200_runtime_tmp/run_stage.py')}
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.deep_transfer.v200.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), new_random_samples=0,
        new_teacher_loads=0, new_native_weight_updates=0, source_roots=32, target_roots=24,
        source_bounds=SOURCE_BOUNDS, target_bounds=TARGET_BOUNDS, completed_targets=0,
        target_support_rows=0, target_support_outcomes=0,
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    source_law, current_law = None, None
    models, plans, results = {}, {}, []
    unions = {str(h): {name: set() for name in ('states', 'rows', 'D4_states', 'D4_rows')} for h in (3, 4)}
    terminal_support = Counter()
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            target_support_rows=record['target_support_rows'], target_support_outcomes=record['target_support_outcomes']))
        save(output/'run.json', record); print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output); save(output/'input_manifest.json', []); phase('protocol_frozen')
        cases = roster(); save(output/'cases.json', cases)
        tick = perf_counter(); source_law = NativeLaw(SOURCE_BOUNDS)
        source = acquire_source(cases['SOURCE'], source_law); save(output/'source.json', source)
        record['costs']['source_acquisition'] = dict(seconds=perf_counter()-tick, counts=dict(source_law.counts))
        phase('source_acquired')
        for mode in ('COARSE', 'LEARNED'):
            tick = perf_counter(); models[mode] = core.fit_model(source, mode)
            record['costs']['learning_'+mode] = dict(seconds=perf_counter()-tick, counts=models[mode]['fit_counts'])
            save(output/'models'/f'{mode}.json', models[mode])
            counts = Counter(); tick = perf_counter(); plans[mode] = core.plan_model(models[mode], QUERIES, counts)
            record['costs']['abstract_dp_'+mode] = dict(seconds=perf_counter()-tick, counts=dict(counts))
        save(output/'plans.json', plan_payload(plans)); save(output/'model_counts.json', {mode: model_counts(model) for mode, model in models.items()})
        phase('models_frozen'); record['costs']['target_cases'] = []
        for case in cases['TARGET']:
            tick = perf_counter(); current_law = NativeLaw(TARGET_BOUNDS)
            result, keys = evaluate_case(case, current_law, models, plans)
            result['seconds'] = perf_counter()-tick; results.append(result)
            for h, names in keys.items():
                for name, values in names.items():
                    unions[h][name].update(values)
            terminal_support.update(result['native_status_counts'])
            record['completed_targets'] += 1
            record['target_support_rows'] += current_law.counts['support_rows']
            record['target_support_outcomes'] += current_law.counts['support_outcomes']
            record['costs']['target_cases'].append(dict(root_id=case['root_id'], seconds=result['seconds'], counts=result['costs']))
            save(output/'target_results.json', dict(records=results)); save(output/'run.json', record)
            print(json.dumps(dict(event='target_complete', root_id=case['root_id'], completed=record['completed_targets'], seconds=perf_counter()-begun)), flush=True)
            current_law = None
        benchmark = {str(h): benchmark_counts(unions[str(h)], h) for h in (3, 4)}
        benchmark['terminal_support_counts'] = {status: terminal_support[status] for status in ('WON', 'LOST', 'ACTIVE')}
        save(output/'benchmark.json', benchmark); phase('target_complete')
        save(output/'summary.json', summarize(results, models, benchmark))
        record['seconds'] = perf_counter()-begun; phase('complete'); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        if source_law is not None and 'source_acquisition' not in record['costs']:
            save(output/'partial_source.json', source_law.export())
            record['costs']['failed_source_acquisition'] = dict(seconds=perf_counter()-tick, counts=dict(source_law.counts))
        if current_law is not None:
            record['target_support_rows'] += current_law.counts['support_rows']
            record['target_support_outcomes'] += current_law.counts['support_outcomes']
            record['costs']['failed_target'] = dict(seconds=perf_counter()-tick, counts=dict(native=dict(current_law.counts),
                **{name: dict(counts) for name, counts in current_law.evaluation_work.items()}))
        if hasattr(error, 'counts'):
            record['failure']['counts'] = error.counts
        save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
