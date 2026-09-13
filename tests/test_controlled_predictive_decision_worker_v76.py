"""Freeze small worker predictions, then check real H2/H1 metrics independently."""
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import pytest


ROOT = Path(__file__).resolve().parents[1]
DENSE = (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10)
WINNING_SWIPE = (10, 10, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10)
WON = (11, 2, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10)
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
CASES = [dict(name='development_dense', board=DENSE, h1_observation=DENSE),
         dict(name='development_winning_swipe', board=WINNING_SWIPE, h1_observation=WON),
         dict(name='development_already_won', board=WON, h1_observation=LOST)]
QUERIES = dict(tied=dict(reward_weight=0, failure_penalty=0, goal_bonus=0),
               reward=dict(reward_weight=1, failure_penalty=0, goal_bonus=0),
               mixed=dict(reward_weight=0.7, failure_penalty=1.3, goal_bonus=2.1))
LEDGER = dict(ground_counts=Counter(), command=None, worker_exit=None,
              source_fit_calls=0, main_target_cases=0, direct_terminal_dp_calls=0)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


@pytest.fixture(scope='module')
def retained_output(request):
    ledger_path = ROOT / 'reports/controlled_predictive_decision_v76.worker_checks.json'
    payload = json.loads(ledger_path.read_text()) if ledger_path.exists() else dict(attempts=[])
    output = ROOT / 'reports/controlled_predictive_decision_v76.worker_checks' / f'attempt_{len(payload["attempts"]) + 1:02d}'
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    yield output
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        seconds=perf_counter() - started, output=str(output), development_cases=CASES,
        queries=QUERIES, scope='One integration check; three hand-written roots and three H1 '
            'observations. EXACT predictions are retained before any ground calls. '
            'No source fitting or main target cohort execution.', **LEDGER))
    ledger_path.write_text(json.dumps(payload, indent=2) + '\n')


def metrics_match(actual, expected):
    assert set(actual) == set(expected)
    for name, value in actual.items():
        assert isinstance(value, Fraction), (name, value)
        assert float(value) == pytest.approx(expected[name], abs=1e-12, rel=0)


def test_frozen_exact_worker_matches_ground_values_ties_and_specified_h1(retained_output):
    worker = module('scripts/query_controlled_predictive_decisions_v76.py', 'v76_test_worker')
    inputs, predictions = retained_output / 'inputs.json', retained_output / 'predictions.json'
    inputs.write_text(json.dumps(dict(cases=CASES, queries=QUERIES)) + '\n')
    command = [sys.executable, str(ROOT / 'scripts/query_controlled_predictive_decisions_v76.py'),
        '--method', 'EXACT', '--inputs', str(inputs), '--rule',
        str(ROOT / 'reports/controlled_predictive_composition_v69/learned_rule.json'),
        '--output', str(predictions)]
    LEDGER['command'] = command
    started = perf_counter()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    LEDGER.update(worker_exit=process.returncode, worker_seconds=perf_counter() - started,
                  worker_stderr_bytes=len(process.stderr.encode()))
    (retained_output / 'stdout.txt').write_text(process.stdout)
    (retained_output / 'stderr.txt').write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    encoded = json.loads(predictions.read_text())
    frozen = worker.decode(encoded)
    assert worker.encode(frozen) == encoded
    assert frozen['ground_imports'] == frozen['forbidden_imports'] == ()
    assert frozen['counts']['case_count'] == 3
    assert frozen['counts']['root_no_action'] == 3
    terminal = frozen['cases'][2]
    terminal_predictions = {}
    for name, query in QUERIES.items():
        terminal_predictions[name] = worker.h2_metrics(terminal['exact_contract'], query)
        LEDGER['direct_terminal_dp_calls'] += 1
    (retained_output / 'terminal_predictions.json').write_text(
        json.dumps(worker.encode(terminal_predictions)) + '\n')
    LEDGER['predictions_frozen_before_ground'] = True
    LEDGER['worker_counts'], LEDGER['worker_work'] = encoded['counts'], encoded['work']

    # Ground is first imported after the subprocess and all additional predictions are saved.
    sys.path.insert(0, str(ROOT / 'src'))
    from acfqp.domains import standard_2048 as ground
    oracle = module('scripts/check_controlled_predictive_grouped_generalization_v73.py', 'v76_test_ground')
    audit = module('src/acfqp/science/controlled_predictive_decision_audit_v76.py', 'v76_test_worker_audit')
    work, cache = LEDGER['ground_counts'], {}
    truth_rows = []
    for case, prediction in zip(CASES, frozen['cases']):
        true = oracle.true_h2(case['board'], ground, work, cache)
        assert prediction['exact_contract'] == true
        truth_rows.append(dict(name=case['name'], ground_contract=worker.encode(true)))
        for name, query in QUERIES.items():
            reference = audit.query_metrics(true, query)
            assert set(prediction['root_values'][name]) == set(reference['actions'])
            if true[0] == 'TERMINAL':
                assert prediction['actions'][name]['action'] is None
                metrics_match(terminal_predictions[name]['metrics'], reference['reference_metrics'])
                continue
            for action, expected in reference['actions'].items():
                metrics_match(prediction['root_values'][name][action], expected)
            selected = prediction['actions'][name]['action']
            continuations = [(row['contract'], row['action']) for row in prediction['continuations'][name]]
            result = audit.evaluate_choice(true, query, selected, continuations)
            assert result['execution_verified'] and result['root_action_optimal_membership']
            assert result['continuation_optimal'] and result['total_regret'] <= 1e-12
            metrics_match(prediction['root_values'][name][selected], result['actual_metrics'])
            if name == 'tied':
                assert len(reference['optimal_actions']) == len(reference['actions']) >= 2
                assert selected == min(reference['optimal_actions'])

        work['designated_h1_explicit_state_calls'] += 1
        h1_state = ground.state_from_board_v1(case['h1_observation'])
        if h1_state.status.value == 'ACTIVE':
            h1_contract = oracle.true_h1(h1_state, ground, work, cache)
            h1_native = (('CHECK', ((('H1', h1_contract), Fraction(0), Fraction(1)),)),)
        else:
            h1_native = ('TERMINAL', h1_state.status.value)
        for name, query in QUERIES.items():
            expected = audit.query_metrics(h1_native, query)
            actual = prediction['h1_actions'][name]
            if h1_state.status.value == 'ACTIVE':
                h1 = expected['h1'][0]
                assert actual['action'] in h1['optimal_actions']
                metrics_match(actual['metrics'], h1['actions'][actual['action']])
            else:
                assert actual['action'] is None
                metrics_match(actual['metrics'], expected['reference_metrics'])
    winning_rows = frozen['cases'][1]['root_values']['mixed']
    assert winning_rows['LEFT']['success'] == winning_rows['RIGHT']['success'] == 1
    assert frozen['cases'][1]['h1_actions']['mixed']['metrics']['success'] == 1
    assert frozen['cases'][2]['h1_actions']['mixed']['metrics']['failure'] == 1
    assert work['ground_h1_unique_active_boards'] > 0
    (retained_output / 'ground.json').write_text(json.dumps(truth_rows) + '\n')
    LEDGER['valid'] = True
