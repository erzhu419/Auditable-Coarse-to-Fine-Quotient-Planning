"""Five three-action CUTOFF development games; no main-lifecycle experience."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v77_runner_integration',
    ROOT / 'scripts/run_controlled_predictive_lifelong_v77.py')
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)
LEDGER = dict(scope='Synthetic episode labels 0..14; five development games capped at 3 actions.',
              lifecycle=99, replica=99, max_steps=3, main_experiment=False,
              source_environment_transitions=0, sampled_transitions=0,
              full_support_ground_calls=0, games=[])


@pytest.fixture(scope='module', autouse=True)
def retain_attempt(request):
    started = perf_counter()
    yield
    LEDGER.update(test_failures=request.session.testsfailed, seconds=perf_counter() - started)
    path = ROOT / 'reports/controlled_predictive_lifelong_v77.runner_checks.json'
    prior = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    prior['attempts'].append(LEDGER)
    path.write_text(json.dumps(prior, indent=2, allow_nan=False) + '\n')


def test_runner_five_methods_use_legal_actions_and_same_observed_prefix():
    records = []
    for episode in range(15):
        policy = RUNNER.POLICIES[episode % 3]
        for sample in range(8):
            board = [0] * 16
            board[sample] = 1 + sample % 3
            board[15 - sample] = 1 + episode % 4
            records.append(dict(board=board, horizon=30 + sample % 2,
                policy=policy, episode=episode,
                target=[(sample + episode % 4) / 32, float(sample == 0), float(sample == 7)]))
    models, fit_log = RUNNER.Knowledge.initialize(records)
    LEDGER['synthetic_training_rows'] = len(records)
    LEDGER['fit_counts'] = fit_log['counts']
    assert all(row['training_rows'] == 32 for row in fit_log['policies'].values())
    payloads = {mode: model.to_payload() for mode, model in models.items()}
    rule = RUNNER.LearnedDynamics.from_payload(json.loads((ROOT /
        'reports/controlled_predictive_composition_v69/learned_rule.json').read_text()))
    deployed = {method: None if method == 'H2_ONLY' else RUNNER.Knowledge.from_payload(
        payloads[method.split('_')[0]]) for method in RUNNER.METHODS}
    assert deployed['REVISED_PLAN'].to_payload() == deployed['REVISED_DIRECT'].to_payload()
    assert deployed['REVISED_PLAN'] is not deployed['REVISED_DIRECT']
    assert all(model.checkpoint == 15 for model in deployed.values() if model is not None)
    results, raw_games = {}, {}
    env_counts = Counter()
    for method in RUNNER.METHODS:
        result, raw = RUNNER.evaluate_game(method, deployed[method], rule,
            lifecycle=99, replica=99, query_name='risk_goal', max_steps=3)
        results[method], raw_games[method] = result, raw
        env_counts.update(result['environment_counts'])
        LEDGER['sampled_transitions'] = env_counts['sampled_transitions']
        LEDGER['games'].append(dict(method=method, seed=result['seed'],
            status=result['status'], steps=result['steps'],
            environment_counts=result['environment_counts'],
            planning_counts=result['planning_counts']))
        assert result['status'] == 'CUTOFF' and result['steps'] == 3
        assert result['environment_counts']['sampled_transitions'] == 3
        assert result['environment_counts']['environment_random_draws'] == 10
        assert result['planning_counts']['model_uniform_draws'] == 12
        for decision, step in zip(raw['decisions'], raw['episode']['steps']):
            assert decision['action'] == step['action']
            assert decision['action'] in ('UP', 'DOWN', 'LEFT', 'RIGHT')
            assert step['afterstate'] != step['board']
        if deployed[method] is not None:
            assert deployed[method].checkpoint == 15
            assert deployed[method].trees == payloads[method.split('_')[0]]['trees']
    first = raw_games[RUNNER.METHODS[0]]['episode']
    for raw in raw_games.values():
        episode = raw['episode']
        assert episode['initial_board'] == first['initial_board']
        assert episode['initial_spawns'] == first['initial_spawns']
        assert episode['seed'] == first['seed']
        assert [step['spawned_rank'] for step in episode['steps']] == [
            step['spawned_rank'] for step in first['steps']]
    assert env_counts['sampled_transitions'] == 15
    assert env_counts['environment_random_draws'] == 50
    json.dumps(dict(results=results, raw_games=raw_games, models=payloads), allow_nan=False)
    LEDGER['environment_counts'] = dict(env_counts)
    LEDGER['same_checkpoint'] = 15
    LEDGER['same_revised_payload'] = True
    LEDGER['json_serializable'] = True
