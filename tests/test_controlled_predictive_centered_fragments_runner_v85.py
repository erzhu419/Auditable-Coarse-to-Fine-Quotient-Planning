"""Check fixed means and changed rankings reach the unchanged real controller."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_centered_rankings_reach_committed_deployment():
    spec = importlib.util.spec_from_file_location('v85_runner', ROOT /
        'scripts/run_controlled_predictive_centered_fragments_v85.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    leaf = dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.],
        values=[[0.] * 12], samples=[8])
    joint = runner.JointSelector({q: deepcopy(leaf) for q in runner.QUERIES}, 6)
    residual = deepcopy(leaf)
    residual['values'] = [[1., 0., 0., -4., 0., 0., 0., 0., 0., 3., 0., 0.]]
    centered = runner.CenteredSelector({q: deepcopy(residual) for q in runner.QUERIES}, 6, joint)
    payload = centered.to_payload()
    rule = runner.LearnedDynamics.from_payload(json.loads((runner.SOURCE / 'supplied_dynamics.json').read_text()))
    games, raws, work = {}, {}, Counter()
    for method in runner.METHODS:
        model = (runner.CenteredSelector.from_payload(payload) if method.startswith('CENTERED')
            else joint if method == 'JOINT' else None)
        games[method], raws[method] = runner.evaluate_game(method, model, rule, 99, 99, 'reward', max_steps=100)
        work.update(games[method]['environment_counts'])
    ledger_path = ROOT / 'reports/controlled_predictive_centered_fragments_v85.runner_checks.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'attempts': []}
    ledger['attempts'].append(dict(lifecycle=99, replica=99, ground_work=dict(work),
        synthetic_tree_fits=0, main_campaign_calls=0))
    runner.save(ledger_path, ledger)
    assert len({game['seed'] for game in games.values()}) == 1
    assert games['CENTERED']['seed'] == 8590000 + 99 * 100 + 99
    assert centered.to_payload() == payload
    assert games['CENTERED']['selected_option'] == 'SNAKE_4'
    assert games['CENTERED']['fragment_actions'] == 4
    assert games['CENTERED_ONE_STEP']['selected_option'] == 'SPACE_1'
    assert games['CENTERED_ONE_STEP']['fragment_actions'] == 1
    assert raws['CENTERED']['episode']['steps'] == raws['CENTERED_FROZEN6']['episode']['steps']
    assert raws['H2_ONLY']['episode']['steps'] == raws['JOINT']['episode']['steps']
    trigger = games['CENTERED']['initiation_step']
    assert trigger is not None
    for method, game in games.items():
        assert game['committed_length_matches']
        assert game['controller_events'] <= 1
        assert game['planning_counts']['model_uniform_draws'] == 4 * game['steps']
        assert raws[method]['episode']['steps'][:trigger] == raws['H2_ONLY']['episode']['steps'][:trigger]
    for method in ('CENTERED', 'CENTERED_ONE_STEP', 'CENTERED_FROZEN6'):
        counts = games[method]['planning_counts']
        assert counts['anchor_prediction_roots'] == counts['residual_prediction_roots'] == 1
