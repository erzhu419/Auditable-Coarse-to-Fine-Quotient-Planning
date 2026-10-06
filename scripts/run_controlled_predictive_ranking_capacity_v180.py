"""Diagnose shared linear rankings on fixed V179 data, without a new learner."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

import numpy as np
import scipy
import sympy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_ranking_capacity_v180 as core

SOURCE = ROOT/'reports/controlled_predictive_shared_consequences_v179'
RUNTIME = ROOT/'reports/v180_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_ranking_capacity_v180'
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def fitted_beta(models):
    return [row[0]-row[1]+row[2] for row in models['SHARED']['coefficients']]


def terminal_identities(roots, labels):
    records, work = [], Counter()
    for cohort in ('SOURCE', 'TARGET'):
        index = {row['root_id']: row for row in labels[cohort]}
        for root in roots[cohort]:
            for action in root['legal_actions']:
                work['cached_goal_feature_reads'] += 1
                if root['action_features'][action][0]:
                    vector = index[root['root_id']]['action_components'][action]
                    expected = [root['immediate_rewards'][action], 0., 1.]
                    records.append(dict(root_id=root['root_id'], cohort=cohort, action=action,
                        components=vector, expected=expected,
                        consistent=all(abs(a-b) <= EPSILON for a, b in zip(vector, expected))))
                    work.update(goal_component_reads=3, goal_identity_comparisons=3)
    return dict(consistent=all(row['consistent'] for row in records),
        actions=len(records), records=records, work=dict(work))


def interpret_certificates(problems, capacities):
    """Identify when a dual also cancels arbitrary functions of feature tuples."""
    scopes, work = {}, Counter()
    for name, capacity in capacities.items():
        roots = {row['root_id']: row for row in problems[name]['roots']}
        nodes = []
        for node in capacity['nodes']:
            flow = Counter()
            for support in node['dual']['support']:
                work['certificate_support_rows_inspected'] += 1
                row = node['constraints'][support['constraint_index']]
                if row['kind'] == 'margin_cap':
                    continue
                classes = {item['representative']: item for item in roots[row['root_id']]['classes']}
                weight = Fraction(support['weight'])
                flow[tuple(classes[row['bad_action']]['features'])] += weight
                flow[tuple(classes[row['best_action']]['features'])] -= weight
                work['feature_flow_additions'] += 2
            residual = [dict(features=list(features), weight=str(weight))
                for features, weight in sorted(flow.items()) if weight]
            nodes.append(dict(node_id=node['node_id'], feature_flow=residual,
                bounds_any_shared_feature_function=not residual))
        terminal_ids = {node['node_id'] for node in capacity['nodes']
            if node['disposition'] in ('pruned_negative', 'pruned_zero')}
        scopes[name] = dict(nodes=nodes, all_terminal_bounds_apply_to_any_shared_function=(
            all(node['bounds_any_shared_feature_function'] for node in nodes if node['node_id'] in terminal_ids)
            if capacity['status'] != 'strict_feasible' else None))
    return dict(scopes=scopes, work=dict(work))


def summarize(problems, capacities, fitted, terminal, inherited, interpretation):
    return dict(schema='acfqp.ranking_capacity.v180.summary', complete=True,
        scopes={name: dict(roots=len(problems[name]['roots']), capacity_status=capacities[name]['status'],
            upper_bound=capacities[name]['upper_bound'], witness=capacities[name]['witness'],
            weak_witness=capacities[name]['weak_witness'], costs=capacities[name]['costs'],
            fitted=fitted[name]) for name in ('SOURCE', 'TARGET', 'JOINT')},
        terminal_identities=terminal,
        certificate_interpretation=interpretation,
        inherited_V179={cohort: deepcopy(inherited['SHARED']['cohorts'][cohort]) for cohort in ('SOURCE', 'TARGET')},
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_predictors_fitted=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_ranking_capacity_v180')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_ranking_capacity_v180.py',
        'scripts/analyze_controlled_predictive_ranking_capacity_v180.py',
        'specs/RANKING_CAPACITY_V180.md',
        'tests/test_ranking_capacity_core_v180.py', 'tests/test_ranking_capacity_runner_v180.py',
        'tests/test_ranking_capacity_analysis_v180.py',
        'reports/v180_runtime_tmp/run_checks.py', 'reports/v180_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        destination = output/'source_code'/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, destination)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.ranking_capacity.v180.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable,
            numpy=np.__version__, scipy=scipy.__version__, sympy=sympy.__version__),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        inherited_cost_refs=[dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v179_runtime_tmp/stage_checks.json'), fields=['attempts']),
            *[dict(path=str(ROOT/f'reports/v179_runtime_tmp/{kind}_checks.json'), fields=['attempts'])
                for kind in ('core', 'runner', 'analyzer')]],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, work = [], Counter()
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs'/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=work['json_read_operations']))
        save(output/'run.json', record); print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output)
        stage = read(ROOT/'reports/v179_runtime_tmp/stage_checks.json', 'stage_checks.json')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if not stage['valid'] or inherited_run['status'] != 'complete':
            raise ValueError('required inherited V179 stage is not complete and valid')
        roots, labels = read(SOURCE/'roots.json', 'roots.json'), read(SOURCE/'labels.json', 'labels.json')
        models, inherited = read(SOURCE/'models.json', 'models.json'), read(SOURCE/'summary.json', 'summary.json')
        terminal = terminal_identities(roots, labels); save(output/'terminal_identities.json', terminal)
        if not terminal['consistent']:
            raise ValueError('known absorbing-goal labels differ from current first reward/WON identity')
        problems = {name: core.build_problem(roots[name], labels[name]) for name in ('SOURCE', 'TARGET')}
        problems['JOINT'] = core.build_problem(roots['SOURCE']+roots['TARGET'], labels['SOURCE']+labels['TARGET'])
        save(output/'problems.json', problems)
        record['costs']['problem_work'] = {name: problem['work'] for name, problem in problems.items()}
        record['costs']['terminal_work'] = terminal['work']
        beta = fitted_beta(models); fitted = {name: core.evaluate_beta(problem, beta) for name, problem in problems.items()}
        for cohort in ('SOURCE', 'TARGET'):
            old = {row['root_id']: row['modes']['TREE']['action'] for row in inherited['SHARED']['cohorts'][cohort]['root_records']}
            if any(row['chosen'] != old[row['root_id']] for row in fitted[cohort]['root_records']):
                raise ValueError('inherited full-vector fit and scalar utility replay choose different actions')
        save(output/'fitted_diagnostics.json', fitted); phase('problems_frozen')
        capacities = {}
        for name in ('SOURCE', 'TARGET', 'JOINT'):
            phase(name.lower()+'_capacity'); tick = perf_counter()
            capacities[name] = core.solve_capacity(problems[name])
            record['costs'][name] = dict(counts=capacities[name]['costs'], seconds=perf_counter()-tick)
            save(output/'capacities.json', capacities); save(output/'run.json', record)
        interpretation = interpret_certificates(problems, capacities)
        save(output/'certificate_interpretation.json', interpretation)
        record['costs']['certificate_interpretation_work'] = interpretation['work']
        summary = summarize(problems, capacities, fitted, terminal, inherited, interpretation)
        save(output/'summary.json', summary); record['costs']['input_counts'] = dict(work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        print(json.dumps({name: value['status'] for name, value in capacities.items()}), flush=True)
        return record
    except Exception as error:
        failure = dict(type=type(error).__name__, message=str(error))
        if hasattr(error, 'record'):
            save(output/'failed_capacity.json', error.record); failure['paid_record_ref'] = 'failed_capacity.json'
        record.update(status='failed', seconds=perf_counter()-begun, failure=failure)
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
