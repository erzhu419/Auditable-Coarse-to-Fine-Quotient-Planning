"""Freeze new H1 local-contract predictions, then check each true action once."""
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


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'src/acfqp/science' / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def roster():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for index in range(32):
        seed = 722000 + index
        rng = random.Random(seed)
        board = [rng.randint(1, 10) for _ in range(16)]
        left, right = edges[index % len(edges)]
        board[left] = board[right] = 1 + index % 10
        vacancies = (0, 1, 2, 4)[index % 4]
        for cell in rng.sample([cell for cell in range(16) if cell not in (left, right)], vacancies):
            board[cell] = 0
        cases.append(dict(name=f'v72_fresh_h1_{index:02d}', horizon=1, seed=seed,
                          vacancies=vacancies, forced_pair=[left, right], board=board))
    return cases


def canonical(signature):
    """Serialize exact joint (terminal status, normalized reward) probabilities."""
    rows = []
    for action, score, outcomes in signature:
        mass = defaultdict(Fraction)
        reward = Fraction(score, 2048)
        for status, probability in outcomes:
            mass[status, reward] += probability
        rows.append([action, [[status, reward.numerator, reward.denominator,
                               probability.numerator, probability.denominator]
                              for (status, reward), probability in sorted(mass.items())]])
    return sorted(rows)


def true_contract(board, ground, work):
    work['ground_explicit_state_calls'] += 1
    state = ground.state_from_board_v1(board)
    if state.status.value != 'ACTIVE':
        return state.status.value, []
    rows = []
    for action in ground.Swipe2048Action:
        work['ground_explicit_swipe_calls'] += 1
        _, _, changed = ground.swipe_board_v1(board, action)
        if not changed:
            continue
        work['ground_step_calls'] += 1
        outcomes = ground.step_v1(state, action)
        work['ground_step_outcomes'] += len(outcomes)
        mass = defaultdict(Fraction)
        for outcome in outcomes:
            status = outcome.next_state.status.value
            if status == 'ACTIVE':
                status = 'CUTOFF'
            mass[status, Fraction(outcome.merge_score, 2048)] += outcome.probability
        rows.append([action.value, [[status, reward.numerator, reward.denominator,
                                     probability.numerator, probability.denominator]
                                    for (status, reward), probability in sorted(mass.items())]])
    return state.status.value, sorted(rows)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    cases = roster()
    save(output / 'roster.json', cases)
    dynamics = module('controlled_predictive_relational_dynamics_v69.py', 'acfqp_v72_probe_dynamics')
    local = module('controlled_predictive_local_contract_v72.py', 'acfqp_v72_probe_local')
    rule_payload = json.loads((ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json').read_text())
    prediction_started = perf_counter()
    compiler = local.LocalCompiler(dynamics.LearnedDynamics.from_payload(rule_payload))
    predictions = []
    for case in cases:
        board = tuple(case['board'])
        whole = canonical(compiler.observation_contract(board))
        cell = next((cell for cell, rank in enumerate(board) if rank in (1, 2)), None)
        patch = None
        if cell is not None:
            base = list(board)
            rank, base[cell] = base[cell], 0
            context = compiler.prepare(tuple(base))
            patch = dict(cell=cell, rank=rank, base=base,
                predicted_status=compiler.patch_status(context, cell, rank),
                contract=canonical(compiler.contract(context, cell, rank)))
        predictions.append(dict(name=case['name'], whole=whole, patch=patch))
    prediction_seconds = perf_counter() - prediction_started
    # The entire roster and both prediction paths are saved before importing or calling ground.
    save(output / 'predictions.json', dict(cases=predictions, counts=dict(compiler.work),
        prediction_seconds=prediction_seconds, source_fit_calls=0, target_ground_calls=0,
        source_rule_path=str(ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json')))
    del compiler

    frozen = json.loads((output / 'predictions.json').read_text())
    ground_started = perf_counter()
    sys.path.insert(0, str(ROOT / 'src'))
    from acfqp.domains import standard_2048 as ground

    work, errors, results = Counter(), Counter(), []
    for case, prediction in zip(cases, frozen['cases']):
        before = work.copy()
        status, expected = true_contract(tuple(case['board']), ground, work)
        failures = []
        if status != 'ACTIVE':
            failures.append('unexpected_terminal_root')
        if prediction['whole'] != expected:
            failures.append('whole_contract_difference')
        patch = prediction['patch']
        if patch is not None:
            if patch['predicted_status'] != status:
                failures.append('patch_status_difference')
            if patch['contract'] != expected:
                failures.append('patch_contract_difference')
        errors.update(failures)
        results.append(dict(name=case['name'], valid=not failures, errors=failures,
            ground_status=status, ground_contract=expected, patch_checked=patch is not None,
            ground_counts=dict(work - before)))
    ground_seconds = perf_counter() - ground_started
    result = dict(schema='acfqp.local_generalization.v72', complete=len(results) == 32,
        valid=len(results) == 32 and not errors, observations=len(results),
        whole_contracts_checked=len(results), patch_contracts_checked=sum(r['patch_checked'] for r in results),
        errors=dict(errors), cases=results, source_fit_calls=0, predictions_frozen_before_ground=True,
        prediction_counts=frozen['counts'], ground_counts=dict(work),
        prediction_seconds=prediction_seconds, ground_seconds=ground_seconds,
        wall_seconds_before_write=perf_counter() - started,
        scope='Thirty-two fresh, fixed H1 boards test whole-observation and available single-spawn '
              'patch contracts against one true row per legal action. Exact terminal/reward joints '
              'are checked after all predictions are saved. These are exact-support ground checks, '
              'not sampled episodes, a learning campaign, higher-horizon transfer, or support reduction.',
        ground_count_scope='Explicit state and swipe API invocations, step invocations and returned '
                           'outcomes are counted. Validation calls internal to the ground APIs are '
                           'not separately counted; their time is included in ground_seconds.')
    save(output / 'verification.json', result)
    print(json.dumps({key: result[key] for key in ('complete', 'valid', 'observations',
        'patch_contracts_checked', 'errors', 'ground_counts')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
