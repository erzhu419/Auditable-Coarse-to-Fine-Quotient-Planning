"""Freeze V74 predictions, then compare with V73's retained H2 ground truth."""
import argparse
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'reports/controlled_predictive_grouped_v73/fresh_h2'
ARMS = ('EARLY', 'SHARED')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def encode(value):
    if isinstance(value, Fraction):
        return {'fraction': [value.numerator, value.denominator]}
    if isinstance(value, tuple):
        return [encode(item) for item in value]
    return value


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((REFERENCE / 'roster.json').read_text())
    save(output / 'roster.json', cases)
    dynamics = module(ROOT / 'src/acfqp/science/controlled_predictive_relational_dynamics_v69.py',
                      'acfqp_v74_probe_dynamics')
    worker = module(ROOT / 'scripts/query_controlled_predictive_effect_v74.py', 'acfqp_v74_probe_worker')
    rule_path = ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json'
    rule = dynamics.LearnedDynamics.from_payload(json.loads(rule_path.read_text()))
    predictions, costs = [], {name: dict(seconds=0.0, counts=Counter()) for name in ARMS}
    prediction_started = perf_counter()
    for index, case in enumerate(cases):
        row = dict(name=case['name'], predictions={}, costs={})
        order = ARMS if index % 2 == 0 else ARMS[::-1]
        for name in order:
            work = Counter()
            tick = perf_counter()
            semantic = worker.semantic_h2(tuple(case['board']), rule, grouping=True,
                work=work, share_successors=name == 'SHARED')
            elapsed = perf_counter() - tick
            row['predictions'][name] = encode(semantic)
            row['costs'][name] = dict(seconds=elapsed, counts=dict(work))
            costs[name]['seconds'] += elapsed
            costs[name]['counts'].update(work)
        predictions.append(row)
    prediction_seconds = perf_counter() - prediction_started
    save(output / 'predictions.json', dict(cases=predictions, costs=costs,
        prediction_seconds=prediction_seconds, source_fit_calls=0, ground_calls=0,
        source_rule_path=str(rule_path)))
    # All new predictions are fixed before the retained oracle is opened.
    verification_started = perf_counter()
    frozen = json.loads((output / 'predictions.json').read_text())
    truth = json.loads((REFERENCE / 'verification.json').read_text())
    expected = {case['name']: case for case in truth['cases']}
    names = [case['name'] for case in cases]
    source_valid = (truth['complete'] and truth['valid'] and truth['observations'] == 16
        and len(names) == len(set(names)) == len(truth['cases']) == 16
        and set(names) == set(expected) and all(case['valid'] for case in truth['cases']))
    errors, results = Counter(), []
    if not source_valid:
        errors['retained_oracle_incomplete_or_invalid'] += 1
    for prediction in frozen['cases']:
        oracle = expected.get(prediction['name'])
        matches = {name: oracle is not None and
                   prediction['predictions'][name] == oracle['ground_contract'] for name in ARMS}
        for name, matches_ground in matches.items():
            if not matches_ground:
                errors[name + '_joint_contract_difference'] += 1
        results.append(dict(name=prediction['name'], valid=all(matches.values()), matches=matches))
    result = dict(schema='acfqp.effect_retained_generalization.v74', complete=len(results) == 16,
        valid=source_valid and len(results) == 16 and not errors,
        observations=len(results), fresh_observations=0, reused_observations=len(results),
        early_contracts_matched=sum(row['matches']['EARLY'] for row in results),
        shared_contracts_matched=sum(row['matches']['SHARED'] for row in results),
        errors=dict(errors), cases=results, source_fit_calls=0, ground_calls=0,
        retained_oracle_valid=source_valid, oracle_reused=True,
        oracle_path=str(REFERENCE / 'verification.json'), predictions_frozen_before_oracle_read=True,
        prediction_costs=frozen['costs'], prediction_seconds=prediction_seconds,
        verification_seconds=perf_counter() - verification_started,
        wall_seconds_before_write=perf_counter() - started,
        scope='The same sixteen H2 observations and exact nested ground contracts retained by V73 '
              'are reused. EARLY and SHARED predictions are saved before oracle access. No new '
              'observations, ground transitions, fitting, or fresh generalization trial are executed.')
    save(output / 'verification.json', result)
    print(json.dumps({key: result[key] for key in ('complete', 'valid', 'observations',
        'early_contracts_matched', 'shared_contracts_matched', 'errors', 'ground_calls')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
