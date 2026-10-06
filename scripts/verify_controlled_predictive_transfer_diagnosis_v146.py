#!/usr/bin/env python3
"""Independent scalar-noise and direct-SVD checks of retained V146 rows."""
import argparse
from itertools import combinations, product
import json
from math import fsum, isclose
from pathlib import Path
from time import perf_counter

import numpy as np


METHODS = ('PRIOR', 'REPLAY', 'UPDATED')


def matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and matches(actual[key], value)
                                               for key, value in expected.items())
    if isinstance(expected, (list, tuple)):
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(
            matches(left, right) for left, right in zip(actual, expected))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
    return actual == expected


def independent_labels(values, predictions):
    mean = fsum(values)/8
    variance = fsum((values[i]-values[j])**2 for i in range(8) for j in range(i))/56
    halves = []
    for selected in combinations(range(8), 4):
        if 0 not in selected:
            continue
        complement = tuple(index for index in range(8) if index not in selected)
        means = [fsum(values[index] for index in part)/4 for part in (selected, complement)]
        signs = [int(value > 0)-int(value < 0) for value in means]
        gates = [value > 0 for value in means]
        halves.append(dict(indices=[list(selected), list(complement)], means=means,
            signs=signs, gates=gates, sign_agreement=signs[0] == signs[1],
            gate_agreement=gates[0] == gates[1], positive_both=all(s > 0 for s in signs),
            negative_both=all(s < 0 for s in signs), mixed_sign=set(signs) == {-1, 1},
            zero_both=all(s == 0 for s in signs), one_zero=signs.count(0) == 1))
    rates = {key: sum(half[key] for half in halves)/35 for key in (
        'sign_agreement', 'gate_agreement', 'positive_both', 'negative_both',
        'mixed_sign', 'zero_both', 'one_zero')}
    methods, partition_products = {}, {}
    for name, prediction in predictions.items():
        error = (prediction-mean)**2
        methods[name] = dict(prediction=prediction, squared_error=error,
            noise_adjusted_squared_error=error-variance/8, select_h1=prediction > 0,
            cross_half_squared_error=(prediction-halves[0]['means'][0])
                                    *(prediction-halves[0]['means'][1]))
        partition_products[name] = fsum((prediction-half['means'][0])
            *(prediction-half['means'][1]) for half in halves)/35
    return dict(n=8, mean=mean, variance=variance, mean_noise_variance=variance/8,
        fixed_halves=halves[0], partitions=dict(count=35, half_count=70, **rates),
        methods=methods), partition_products


class SVDGeometry:
    def __init__(self, training):
        self.training = [dict(row) for row in training]
        self.addresses = sorted({address for row in self.training for address, value in row.items() if value})
        self.matrix = np.array([[row.get(address, 0) for address in self.addresses]
                                for row in self.training], dtype=float)
        self.norms = np.sum(self.matrix**2, axis=1)
        self.svd_calls = int(bool(self.addresses))
        if self.addresses:
            _, singular, vectors = np.linalg.svd(self.matrix, full_matrices=False)
            self.basis = vectors[singular > singular[0]*1e-5]
        else:
            self.basis = np.empty((0, 0))

    def measure(self, pairs):
        query = {address: value for address, value in pairs if value}
        norm = sum(value**2 for value in query.values())
        vector = np.array([query.get(address, 0) for address in self.addresses], dtype=float)
        covered = {address: value for address, value in query.items() if address in self.addresses}
        projection = float(np.sum((self.basis @ vector)**2))
        dots = self.matrix @ vector
        cosines = [abs(dot)/(norm*row_norm)**.5 for dot, row_norm in zip(dots, self.norms)
                   if norm and row_norm]
        covered_norm = sum(value**2 for value in covered.values())
        return dict(train_roots=len(self.training), nonzero_train_roots=int(sum(self.norms > 0)),
            train_rank=len(self.basis), train_addresses=len(self.addresses),
            query_addresses=len(query), query_norm2=norm, covered_addresses=len(covered),
            covered_norm2=covered_norm, covered_norm_fraction=covered_norm/norm if norm else None,
            projection_norm2=projection, projection_fraction=projection/norm if norm else None,
            max_abs_cosine=float(max(cosines, default=0)), zero_feature=norm == 0,
            orthogonal_to_training=all(dot == 0 for dot in dots))


def summary_matches(rows, summary):
    """Recompose equal-game/equal-life means, including missing zero geometry."""
    def average(values):
        present = [value for value in values if value is not None]
        return fsum(present)/len(present) if present else None

    def metrics(row):
        result = {'mean_noise_variance': row['label_diagnostics']['mean_noise_variance']}
        for method in METHODS:
            for name in ('squared_error', 'noise_adjusted_squared_error', 'cross_half_squared_error'):
                result[method+'.'+name] = row['label_diagnostics']['methods'][method][name]
            for name in ('covered_norm_fraction', 'projection_fraction'):
                result[method+'.'+name] = row['geometry'][method][name]
        return result

    result, lives = True, []
    for life in range(4):
        games = []
        for replica in range(4, 8):
            values = [metrics(row) for row in rows if row['life'] == life and row['replica'] == replica]
            reduced = {key: average(row[key] for row in values) for key in values[0]}
            actual = next(g for g in summary['lifecycles'][life]['games'] if g['replica'] == replica)
            result &= actual['roots'] == len(values) and matches(actual['metrics'], reduced)
            games.append(reduced)
        reduced = {key: average(game[key] for game in games) for key in games[0]}
        result &= matches(summary['lifecycles'][life]['metrics'], reduced)
        lives.append(reduced)
    combined = {key: average(life[key] for life in lives) for key in lives[0]}
    return bool(result and summary['roots'] == len(rows) and matches(summary['metrics'], combined))


def verify(directory):
    started = perf_counter()
    read = lambda name: json.loads((directory/name).read_text())
    rows, groups = read('rows.json')['rows'], read('geometry_inputs.json')['groups']
    analysis, frozen = read('analysis.json'), read('frozen_inputs.json')
    identity = lambda row: (row['origin'], row['life'], row['query'], row['replica'], row['slot'])
    expected = set(product(('OLD', 'NEW'), range(4), ('risk1', 'risk8'), range(4, 8), range(4)))
    checks = dict(row_roster=len(rows) == 256 and {identity(row) for row in rows} == expected,
        frozen_cohort=len(frozen['cohort']) == 256 and sorted(
            (*identity(row), row['root_id']) for row in rows) == sorted(
            (*identity(row), row['root_id']) for row in frozen['cohort']),
        geometry_roster=len(groups) == 24 and {(g['life'], g['query'], g['method']) for g in groups}
        == set(product(range(4), ('risk1', 'risk8'), METHODS)),
        zero_new_work=all(analysis['costs'][name] == 0 for name in (
            'new_environment_samples', 'new_model_samples', 'training_update_attempts', 'new_control_games')))
    cache, geometry = {}, {}
    for group in groups:
        key = (group['life'], group['query'], group['method'])
        signature = tuple(tuple(tuple(pair) for pair in row) for row in group['training_differences'])
        if signature not in cache:
            cache[signature] = SVDGeometry(group['training_differences'])
        geometry[key] = cache[signature]
        checks['training_roots:'+':'.join(map(str, key))] = (
            len(group['training_roots']) == len(group['training_differences'])
            == (32 if group['method'] == 'UPDATED' else 16))
    checks['prior_replay_same_support'] = all(
        geometry[life, query, 'PRIOR'].training == geometry[life, query, 'REPLAY'].training
        for life in range(4) for query in ('risk1', 'risk8'))
    labels_ok, products_ok, geometry_ok = True, True, True
    for row in rows:
        predictions = {name: row['label_diagnostics']['methods'][name]['prediction'] for name in METHODS}
        label, products_mean = independent_labels(row['labels'], predictions)
        labels_ok &= len(row['labels']) == 8 and matches(row['label_diagnostics'], label)
        products_ok &= all(matches(products_mean[name], label['methods'][name]['noise_adjusted_squared_error'])
                           for name in METHODS)
        for method in METHODS:
            expected_geometry = geometry[row['life'], row['query'], method].measure(row['difference'])
            geometry_ok &= matches(row['geometry'][method], expected_geometry)
    checks.update(pairwise_variance_and_label_statistics=bool(labels_ok),
        all_partition_identity=bool(products_ok), direct_svd_geometry=bool(geometry_ok),
        equal_game_equal_life_summary=all(summary_matches(
            [row for row in rows if row['origin'] == origin and row['query'] == query],
            analysis['summary'][origin][query]) for origin in ('OLD', 'NEW') for query in ('risk1', 'risk8')))
    result = dict(schema='acfqp.transfer_diagnosis.v146.verification', complete=all(checks.values()),
        checks=checks, work=dict(rows=len(rows), direct_svd_calls=sum(g.svd_calls for g in cache.values()),
            geometry_queries=len(rows)*3, new_environment_samples=0, new_model_samples=0,
            training_update_attempts=0), seconds=perf_counter()-started)
    (directory/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    result = verify(parser.parse_args().directory)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['complete'] else 1)
