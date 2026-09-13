"""Fit one source decision rule, freeze four new-target predictions, then audit."""
from collections import Counter
from fractions import Fraction
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
METHODS = ('EXACT', 'GREEDY', 'RULE', 'SELECTIVE')


def module(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def roster():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for index in range(48):
        seed = 763000 + index
        rng = random.Random(seed)
        board = [rng.randint(1, 10) for _ in range(16)]
        pair = edges[index % 24]
        board[pair[0]] = board[pair[1]] = 1 + index % 10
        for cell in rng.sample([c for c in range(16) if c not in pair], index % 3):
            board[cell] = 0
        cases.append(dict(name=f'v76_fresh_h2_{index:02d}', seed=seed, horizon=2,
                          board=board, forced_pair=pair, vacancies=index % 3))
    return cases


def snapshot(output):
    scripts = ['run_controlled_predictive_decisions_v76', 'prepare_controlled_predictive_decisions_v76',
        'query_controlled_predictive_decisions_v76', 'analyze_controlled_predictive_decisions_v76',
        'query_controlled_predictive_effect_v74', 'query_controlled_predictive_grouped_v73',
        'query_controlled_predictive_local_v72', 'check_controlled_predictive_grouped_generalization_v73']
    modules = ['controlled_predictive_decision_rule_v76', 'controlled_predictive_decision_audit_v76',
        'controlled_predictive_relational_dynamics_v69', 'controlled_predictive_effect_contract_v74',
        'controlled_predictive_grouped_contract_v73', 'controlled_predictive_local_contract_v72',
        'controlled_predictive_symbolic_successors_v71']
    files = ['scripts/' + name + '.py' for name in scripts]
    files += ['src/acfqp/science/' + name + '.py' for name in modules]
    files += ['src/acfqp/domains/standard_2048.py',
              'specs/CONTROLLED_PREDICTIVE_DECISION_RULE_V76.md']
    for relative in files:
        destination = output / 'source' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


def run(output):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    snapshot(output)
    manifest = dict(schema='acfqp.decisions_campaign.v76', status='running',
        platform=platform.platform(), python=sys.version, executable=sys.executable,
        target_cases=48, worker_commands={}, worker_order=list(METHODS),
        source_fit_calls=0, target_ground_calls_before_predictions=0)
    save(output / 'manifest.json', manifest)
    input_tick = perf_counter()
    worker = module('scripts/query_controlled_predictive_decisions_v76.py', 'v76_runner_worker')
    dynamics = module('src/acfqp/science/controlled_predictive_relational_dynamics_v69.py', 'v76_runner_dynamics')
    payload = json.loads((ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json').read_text())
    rule = dynamics.LearnedDynamics.from_payload(payload)
    queries = json.loads((ROOT / 'reports/controlled_predictive_effect_v74/v69_h3_00/inputs.json').read_text())['queries']
    cases, input_work = roster(), Counter()
    for case in cases:
        status, moves = rule.classify(tuple(case['board']), input_work)
        if status != 'ACTIVE' or not moves:
            raise ValueError('frozen roster unexpectedly contains a terminal root')
        action, after, _ = moves[0]
        observation = list(after)
        cell = observation.index(0)
        observation[cell] = 1
        input_work['matched_h1_observations_created'] += 1
        case.update(h1_observation=observation, observation_root_action=action, spawn_cell=cell)
    save(output / 'inputs.json', dict(queries=queries, cases=cases))
    save(output / 'learned_rule.json', payload)
    manifest['input_preparation_seconds'] = perf_counter() - input_tick
    manifest['input_counts'] = dict(input_work)
    manifest['query_names'] = list(queries)

    source_tick = perf_counter()
    prepare = module('scripts/prepare_controlled_predictive_decisions_v76.py', 'v76_runner_source')
    predictor = module('src/acfqp/science/controlled_predictive_decision_rule_v76.py', 'v76_runner_predictor')
    source, source_counts = prepare.prepare()
    source_boards = {tuple(row['board']) for row in source['boards']}
    source_target_disjoint = all(tuple(case['board']) not in source_boards for case in cases)
    if not source_target_disjoint:
        raise ValueError('frozen target overlaps source; no reroll allowed')
    feature_work = Counter()
    tick = perf_counter()
    cache = {row['board_id']: predictor.features(row['board'], rule, feature_work)
             for row in source['boards']}
    records = []
    for occurrence in source['occurrences']:
        base = cache[occurrence['board_id']]
        if sorted(base) != occurrence['legal_actions']:
            raise ValueError('source learned legal actions differ from retained teacher')
        for query_row in occurrence['query_rows']:
            query = source['queries'][query_row['query_name']]
            for action_row in query_row['actions']:
                records.append(dict(features=predictor.query_features(base[action_row['action']], query),
                                    label=int(action_row['optimal'])))
    feature_seconds = perf_counter() - tick
    model = predictor.fit(records)
    save(output / 'tree.json', model)
    manifest.update(source_fit_calls=1, train_query_names=list(source['queries']))
    source_summary = dict(counts=source_counts, feature_counts=dict(feature_work),
        feature_seconds=feature_seconds, training=model['training'],
        tree_feature_importance=model['feature_importance'], source_target_disjoint=source_target_disjoint,
        source_scope=source['source_scope'])
    save(output / 'source_summary.json', source_summary)
    tick = perf_counter()
    del source, cache, records, model, source_boards
    gc.collect()
    manifest['source_cleanup_seconds'] = perf_counter() - tick
    manifest['source_cost_seconds'] = perf_counter() - source_tick
    save(output / 'manifest.json', manifest)
    print(json.dumps(dict(phase='source_complete', seconds=manifest['source_cost_seconds'],
                         training=source_summary['training'])), flush=True)

    for method in METHODS:
        command = [sys.executable, str(ROOT / 'scripts/query_controlled_predictive_decisions_v76.py'),
            '--method', method, '--inputs', str(output / 'inputs.json'),
            '--rule', str(output / 'learned_rule.json'), '--output', str(output / f'{method}.json')]
        if method in {'RULE', 'SELECTIVE'}:
            command += ['--model', str(output / 'tree.json')]
        tick = perf_counter()
        with (output / f'{method}.stdout.log').open('x') as out, (output / f'{method}.stderr.log').open('x') as err:
            process = subprocess.run(command, stdout=out, stderr=err, cwd=ROOT)
        info = dict(seconds=perf_counter()-tick, exit_code=process.returncode,
                    stderr_bytes=(output / f'{method}.stderr.log').stat().st_size)
        manifest['worker_commands'][method] = info
        save(output / 'manifest.json', manifest)
        print(json.dumps(dict(phase='worker_complete', method=method, **info)), flush=True)
        if process.returncode:
            raise RuntimeError(f'{method} worker failed; retained attempt must not be overwritten')

    # Every method's complete output is on disk before ground is imported.
    audit_tick = perf_counter()
    outputs = {method: worker.decode(json.loads((output / f'{method}.json').read_text()))
               for method in METHODS}
    if any(len(result['cases']) != 48 or result['ground_imports'] or result['forbidden_imports']
           for result in outputs.values()):
        raise ValueError('incomplete or contaminated inference output')
    helper = module('scripts/check_controlled_predictive_grouped_generalization_v73.py', 'v76_runner_ground_helper')
    auditor = module('src/acfqp/science/controlled_predictive_decision_audit_v76.py', 'v76_runner_auditor')
    sys.path.insert(0, str(ROOT / 'src'))
    from acfqp.domains import standard_2048 as ground

    work, h1_cache = Counter(), {}
    ground_tick = perf_counter()
    natives = [helper.true_h2(tuple(case['board']), ground, work, h1_cache) for case in cases]
    matched = []
    for case in cases:
        work['matched_h1_explicit_state_calls'] += 1
        state = ground.state_from_board_v1(tuple(case['h1_observation']))
        status = state.status.value
        matched.append((status, helper.true_h1(state, ground, work, h1_cache)
                        if status == 'ACTIVE' else ()))
    ground_seconds = perf_counter() - ground_tick
    effect = module('scripts/query_controlled_predictive_effect_v74.py', 'v76_runner_effect')
    encoder = effect._compiler(rule)
    encoder_errors = []
    for board, contract in h1_cache.items():
        if worker.canonical_h1(encoder.observation_contract(board)) != contract:
            encoder_errors.append(list(board))
    result_cases = []
    for index, (case, native) in enumerate(zip(cases, natives)):
        exact = outputs['EXACT']['cases'][index]
        if any(result['cases'][index]['name'] != case['name'] for result in outputs.values()):
            raise ValueError('worker case order differs from frozen roster')
        same = exact['exact_contract'] == native
        row = dict(name=case['name'], predicted_kernel_equal=same, ground_contract=worker.encode(native), queries=[])
        status, contract = matched[index]
        for name, query in queries.items():
            continuation = [(entry['contract'], entry['action']) for entry in exact['continuations'][name]]
            qrow = dict(query_name=name, seen_query=name in manifest['train_query_names'], methods={}, matched_h1={})
            if contract:
                matched_truth = auditor._h1_metrics(contract, query, Counter())
            else:
                matched_truth = dict(actions={}, optimal_actions=[], metrics=auditor._terminal(status, query))
            for method in METHODS:
                prediction = outputs[method]['cases'][index]
                evaluation = auditor.evaluate_choice(native, query, prediction['actions'][name]['action'], continuation)
                details = evaluation.pop('continuation_details')
                evaluation['continuation_count'] = len(details)
                evaluation['continuation_errors'] = worker.encode([d for d in details if not d['optimal']])
                evaluation.pop('reference_scope')
                evaluation.pop('execution_scope')
                qrow['methods'][method] = evaluation
                h1 = prediction['h1_actions'][name]
                action = h1['action']
                legal = action in matched_truth['actions'] if contract else action is None
                optimal = action in matched_truth['optimal_actions'] if contract else action is None
                truth_metrics = matched_truth['actions'].get(action) if contract else matched_truth['metrics']
                metrics_equal = truth_metrics is not None and all(
                    abs(float(h1['metrics'][key]) - truth_metrics[key]) <= 1e-12 for key in truth_metrics)
                qrow['matched_h1'][method] = dict(action_legal=legal,
                    action_optimal_membership=optimal, metrics_equal=metrics_equal)
            row['queries'].append(qrow)
        result_cases.append(row)
    audit = dict(schema='acfqp.decisions_audit.v76', complete=len(result_cases) == 48,
        valid_ground_models=all(row['predicted_kernel_equal'] for row in result_cases),
        h1_encoder_valid=not encoder_errors, source_target_disjoint=source_target_disjoint,
        ground_counts=dict(work), ground_seconds=ground_seconds,
        h1_encoder_observations=len(h1_cache), h1_encoder_counts=dict(encoder.work),
        h1_encoder_errors=encoder_errors, cases=result_cases, predictions_frozen_before_ground=True,
        metric_scope='Actual root metrics use supplied frozen exact H1 actions; observed-board encoding is independently checked. Matched H1 cost is a controlled workload, not an on-policy rollout. Deltas to the canonical optimal reference may differ even for tied-optimal policies.')
    save(output / 'audit.json', worker.encode(audit))
    manifest.update(status='complete', audit_seconds=perf_counter()-audit_tick,
                    campaign_wall_seconds=perf_counter()-started)
    save(output / 'manifest.json', manifest)
    print(json.dumps(dict(phase='complete', valid_ground_models=audit['valid_ground_models'],
        h1_encoder_valid=audit['h1_encoder_valid'], ground_counts=audit['ground_counts'],
        campaign_wall_seconds=manifest['campaign_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
