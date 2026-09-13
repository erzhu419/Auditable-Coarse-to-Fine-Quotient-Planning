"""Freeze guarded H2 predictions on new numeric bindings before exact ground."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import gc
import json
from pathlib import Path
import random
from time import perf_counter

from check_controlled_predictive_grouped_generalization_v73 import ROOT, module, save, encode, true_h2


ARMS = ('BASE', 'TRACE', 'PARAM')


def roster():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for index in range(16):
        seed = 753000 + index
        rng = random.Random(seed)
        base = [rng.randint(3, 6) for _ in range(16)]
        left, right = edges[index % len(edges)]
        base[left] = base[right] = 3 + index % 4
        for cell in rng.sample([i for i in range(16) if i not in (left, right)], index % 2):
            base[cell] = 0
        cases.append(dict(name=f'v75_binding_{index:02d}', seed=seed, horizon=2,
            forced_pair=[left, right], boards=[[rank + shift if rank else 0 for rank in base]
                                             for shift in (0, 1, 2)]))
    return cases


def semantic(rows):
    result = []
    for action, score, outcomes in rows:
        mass = defaultdict(Fraction)
        for probability, status, description in outcomes:
            child = (('H1', tuple(sorted((a, r, tuple(sorted(terms))) for a, r, terms in description)))
                     if status == 'ACTIVE' else ('TERMINAL', status))
            mass[child, Fraction(score, 2048)] += probability
        result.append((action, tuple((child, reward, probability)
            for (child, reward), probability in sorted(mass.items()))))
    return tuple(sorted(result))


def baseline_contract(compiler, board):
    context = compiler.prepare(board)
    return tuple((action, score, tuple((p, status, description)
        for p, status, description, _, _ in compiler.spawn_groups(after)))
        for action, score, after in compiler.actions(context))


def run(output):
    started = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    cases = roster(); save(output/'roster.json', cases)
    dynamics = module(ROOT/'src/acfqp/science/controlled_predictive_relational_dynamics_v69.py', 'v75_binding_dynamics')
    effect = module(ROOT/'src/acfqp/science/controlled_predictive_effect_contract_v74.py', 'v75_binding_effect')
    parametric = module(ROOT/'src/acfqp/science/controlled_predictive_parametric_contract_v75.py', 'v75_binding_parametric')
    rule = dynamics.LearnedDynamics.from_payload(json.loads((ROOT/'reports/controlled_predictive_composition_v69/learned_rule.json').read_text()))
    predictions, costs = [], {name: dict(method_seconds=0.0, counts=Counter()) for name in ARMS}
    for index, case in enumerate(cases):
        record = dict(name=case['name'], predictions={}, arm_costs={})
        for name in ARMS[index % 3:] + ARMS[:index % 3]:
            tick = perf_counter()
            compiler = (effect.SharedEffectCompiler(rule) if name == 'BASE'
                        else parametric.ParametricCompiler(rule, reuse=name == 'PARAM'))
            entries = []
            for shift, board in enumerate(case['boards']):
                before = Counter(compiler.work); bind_started = perf_counter()
                rows = baseline_contract(compiler, tuple(board)) if name == 'BASE' else compiler.contract(tuple(board))
                prediction = encode(semantic(rows))
                entries.append(dict(shift=shift, contract=prediction,
                    seconds=perf_counter()-bind_started, counts=dict(Counter(compiler.work)-before)))
            counts = dict(compiler.work)
            del rows, compiler; gc.collect()
            elapsed = perf_counter()-tick
            record['predictions'][name] = entries
            record['arm_costs'][name] = dict(method_seconds=elapsed, counts=counts)
            costs[name]['method_seconds'] += elapsed; costs[name]['counts'].update(counts)
        predictions.append(record)
    save(output/'predictions.json', dict(cases=predictions, costs=costs, source_fit_calls=0,
        ground_calls=0, template_seed_boards=16, subsequent_bindings=32,
        scope='Each arm pays initialization, all three boards including the template seed, '
              'semantic serialization preparation, and compiler cleanup; no seed compilation is free.'))
    # No ground imports or calls occur before every arm's 48 predictions are saved.
    frozen = json.loads((output/'predictions.json').read_text())
    ground_started = perf_counter()
    import sys
    sys.path.insert(0, str(ROOT/'src'))
    from acfqp.domains import standard_2048 as ground
    work, cache, errors, results = Counter(), {}, Counter(), []
    fresh_binding_hits = 0
    for case, prediction in zip(cases, frozen['cases']):
        for shift, board in enumerate(case['boards']):
            before = work.copy()
            expected = encode(true_h2(tuple(board), ground, work, cache))
            matches = {name: prediction['predictions'][name][shift]['contract'] == expected for name in ARMS}
            for name, match in matches.items():
                if not match: errors[name+'_joint_contract_difference'] += 1
            entry = prediction['predictions']['PARAM'][shift]
            reused = shift > 0 and entry['counts'].get('template_hits', 0) == 1 and entry['counts'].get('template_compilations', 0) == 0
            fresh_binding_hits += reused
            results.append(dict(name=case['name'], shift=shift, matches=matches, valid=all(matches.values()),
                new_binding_reused_without_compilation=reused, ground_contract=expected,
                ground_counts=dict(work-before)))
    ground_seconds = perf_counter()-ground_started
    result = dict(schema='acfqp.parametric_binding.v75', complete=len(results)==48,
        valid=len(results)==48 and not errors, observations=len(results),
        template_seed_boards=16, new_bindings=32, new_bindings_reused_without_compilation=fresh_binding_hits,
        matched={name: sum(row['matches'][name] for row in results) for name in ARMS},
        errors=dict(errors), cases=results, prediction_costs=frozen['costs'],
        ground_counts=dict(work), ground_seconds=ground_seconds, source_fit_calls=0,
        predictions_frozen_before_ground=True, wall_seconds_before_write=perf_counter()-started,
        scope='New fixed H2 observations test two uniform nonzero-rank shifts per seed; '
              'success is bounded numeric rebinding, not unrestricted strategic learning. '
              'All three arms pay seed and binding costs; exact ground validation is separate.')
    save(output/'verification.json', result)
    print(json.dumps({key: result[key] for key in ('complete','valid','observations','matched',
        'new_bindings_reused_without_compilation','errors','ground_counts')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
