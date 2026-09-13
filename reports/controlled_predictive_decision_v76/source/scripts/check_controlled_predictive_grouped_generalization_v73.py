"""Freeze sixteen new H2 predictions before exact two-step ground verification."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import random
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def encode(value):
    """Keep exact fractions distinguishable from structural tuples in JSON."""
    if isinstance(value, Fraction):
        return {'fraction': [value.numerator, value.denominator]}
    if isinstance(value, tuple):
        return [encode(item) for item in value]
    return value


def roster():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for index in range(16):
        seed = 733000 + index
        rng = random.Random(seed)
        board = [rng.randint(1, 10) for _ in range(16)]
        left, right = edges[index % len(edges)]
        board[left] = board[right] = 1 + index % 10
        vacancies = index % 2
        for cell in rng.sample([cell for cell in range(16) if cell not in (left, right)], vacancies):
            board[cell] = 0
        cases.append(dict(name=f'v73_fresh_h2_{index:02d}', horizon=2, seed=seed,
                          vacancies=vacancies, forced_pair=[left, right], board=board))
    return cases


def true_rows(state, ground, work, horizon):
    """Call each legal ground row once; charge explicit entry points and outcomes."""
    for action in ground.Swipe2048Action:
        work[f'ground_h{horizon}_explicit_swipe_calls'] += 1
        if not ground.swipe_board_v1(state.board, action)[2]:
            continue
        work[f'ground_h{horizon}_step_calls'] += 1
        outcomes = ground.step_v1(state, action)
        work[f'ground_h{horizon}_step_outcomes'] += len(outcomes)
        yield action.value, outcomes


def true_h1(state, ground, work, cache):
    work['ground_h1_contract_requests'] += 1
    if state.board in cache:
        work['ground_h1_contract_cache_hits'] += 1
        return cache[state.board]
    work['ground_h1_unique_active_boards'] += 1
    rows = []
    for action, outcomes in true_rows(state, ground, work, 1):
        mass = defaultdict(Fraction)
        for outcome in outcomes:
            status = outcome.next_state.status.value
            mass['CUTOFF' if status == 'ACTIVE' else status] += outcome.probability
        rows.append((action, outcomes[0].merge_score, tuple(sorted(mass.items()))))
    result = tuple(sorted(rows))
    cache[state.board] = result
    return result


def true_h2(board, ground, work, h1_cache):
    work['ground_h2_explicit_state_calls'] += 1
    state = ground.state_from_board_v1(board)
    if state.status.value != 'ACTIVE':
        return ('TERMINAL', state.status.value)
    work['ground_h2_active_roots'] += 1
    rows = []
    for action, outcomes in true_rows(state, ground, work, 2):
        mass = defaultdict(Fraction)
        for outcome in outcomes:
            child = outcome.next_state
            leaf = (('H1', true_h1(child, ground, work, h1_cache))
                    if child.status.value == 'ACTIVE' else ('TERMINAL', child.status.value))
            mass[leaf, Fraction(outcome.merge_score, 2048)] += outcome.probability
        rows.append((action, tuple((leaf, reward, probability)
                                   for (leaf, reward), probability in sorted(mass.items()))))
    return tuple(sorted(rows))


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    cases = roster()
    save(output / 'roster.json', cases)
    dynamics = module(ROOT / 'src/acfqp/science/controlled_predictive_relational_dynamics_v69.py',
                      'acfqp_v73_probe_dynamics')
    worker = module(ROOT / 'scripts/query_controlled_predictive_grouped_v73.py', 'acfqp_v73_probe_worker')
    rule_path = ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json'
    rule = dynamics.LearnedDynamics.from_payload(json.loads(rule_path.read_text()))
    predictions, costs = [], {name: dict(seconds=0.0, counts=Counter()) for name in ('EACH', 'GROUP')}
    prediction_started = perf_counter()
    for index, case in enumerate(cases):
        row = dict(name=case['name'], predictions={}, costs={})
        order = ('EACH', 'GROUP') if index % 2 == 0 else ('GROUP', 'EACH')
        for name in order:
            work = Counter()
            tick = perf_counter()
            semantic = worker.semantic_h2(tuple(case['board']), rule, grouping=name == 'GROUP', work=work)
            elapsed = perf_counter() - tick
            row['predictions'][name] = encode(semantic)
            row['costs'][name] = dict(seconds=elapsed, counts=dict(work))
            costs[name]['seconds'] += elapsed
            costs[name]['counts'].update(work)
        predictions.append(row)
    prediction_seconds = perf_counter() - prediction_started
    save(output / 'predictions.json', dict(cases=predictions, costs=costs,
        prediction_seconds=prediction_seconds, source_fit_calls=0, target_ground_calls=0,
        source_rule_path=str(rule_path)))
    # Both algorithms' complete predictions are now retained, before importing ground.
    frozen = json.loads((output / 'predictions.json').read_text())
    ground_started = perf_counter()
    sys.path.insert(0, str(ROOT / 'src'))
    from acfqp.domains import standard_2048 as ground

    work, h1_cache, errors, results = Counter(), {}, Counter(), []
    for case, prediction in zip(cases, frozen['cases']):
        before = work.copy()
        expected = encode(true_h2(tuple(case['board']), ground, work, h1_cache))
        matches = {name: prediction['predictions'][name] == expected for name in ('EACH', 'GROUP')}
        for name, matches_ground in matches.items():
            if not matches_ground:
                errors[name + '_joint_contract_difference'] += 1
        results.append(dict(name=case['name'], valid=all(matches.values()), matches=matches,
            ground_contract=expected, ground_counts=dict(work - before)))
    ground_seconds = perf_counter() - ground_started
    result = dict(schema='acfqp.grouped_generalization.v73', complete=len(results) == 16,
        valid=len(results) == 16 and not errors, observations=len(results),
        each_contracts_matched=sum(row['matches']['EACH'] for row in results),
        group_contracts_matched=sum(row['matches']['GROUP'] for row in results),
        errors=dict(errors), cases=results, source_fit_calls=0, predictions_frozen_before_ground=True,
        prediction_costs=frozen['costs'], ground_counts=dict(work),
        prediction_seconds=prediction_seconds, ground_seconds=ground_seconds,
        wall_seconds_before_write=perf_counter() - started,
        scope='Sixteen fixed new H2 observations compare EACH and GROUP predictions to exact '
              'nested joint reward/H1-contract distributions. Every ground H2 action is queried '
              'once; actual H1 boards share an oracle cache. This is an exact-support semantic '
              'check, not sampled learning, reduced candidate support or unrestricted planning.',
        ground_count_scope='Explicit state and swipe entry calls, step calls and returned outcomes '
                           'are counted. Ground internal validation calls are not separately '
                           'counted; their time is included in ground_seconds.')
    save(output / 'verification.json', result)
    print(json.dumps({key: result[key] for key in ('complete', 'valid', 'observations',
        'each_contracts_matched', 'group_contracts_matched', 'errors', 'ground_counts')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
