"""Verify both target models enter the same five-arm natural-game wiring."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_matched_models_and_frozen_copies_use_paired_deployment():
    spec = importlib.util.spec_from_file_location('v80_runner_check',
        ROOT / 'scripts/run_controlled_predictive_target_horizon_v80.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    rows = [dict(board=[1, 1]+[0]*14, policy=policy, episode=0, anchor_step=index,
        source_kind='natural', short_target=[0., .25, 0.], terminal_target=[.2, 1., 0.])
        for policy in ('GREEDY', 'SPACE', 'SNAKE') for index in range(32)]
    fitted, logs = {}, {}
    for scope in runner.SCOPES:
        fitted[scope], logs[scope] = runner.fit_model(rows, 15, scope)
    assert logs['SHORT']['training_records'] == logs['TERMINAL']['training_records'] == len(rows)
    assert runner.dataset_summary(rows, Counter(LOST=1), Counter())['paired_records'] == len(rows)
    rule = runner.LearnedDynamics.from_payload(json.loads((runner.BRANCHES / 'supplied_dynamics.json').read_text()))
    games, raw_games, counts = {}, {}, Counter()
    for method in runner.METHODS:
        model = None if method == 'H2_ONLY' else runner.ConsequenceModel.from_payload(
            fitted[method.split('_')[0]].to_payload())
        game, raw = runner.evaluate_game(method, model, rule, 99, 99, 'reward', max_steps=3)
        games[method], raw_games[method] = game, raw
        counts.update(game['environment_counts'])
    assert len({g['seed'] for g in games.values()}) == 1
    for scope in runner.SCOPES:
        a, b = games[scope+'_PLAN'], games[scope+'_FROZEN']
        assert all(a[key] == b[key] for key in ('score', 'status', 'steps', 'utility'))
        assert raw_games[scope+'_PLAN']['episode']['steps'] == raw_games[scope+'_FROZEN']['episode']['steps']
    short = raw_games['SHORT_PLAN']['decisions'][0]['metrics']
    terminal = raw_games['TERMINAL_PLAN']['decisions'][0]['metrics']
    assert terminal['reward'] - short['reward'] == pytest.approx(.2)
    assert short['failure'] == .25 and terminal['failure'] == 1.
    path = ROOT / 'reports/controlled_predictive_target_horizon_v80.runner_checks.json'
    ledger = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    ledger['attempts'].append(dict(lifecycle=99, replica=99, environment_counts=dict(counts),
        synthetic_tree_fits=sum(log['counts']['tree_fits'] for log in logs.values()),
        synthetic_fit_rows=sum(log['counts']['fit_rows'] for log in logs.values()),
        main_campaign_calls=0, full_support_teacher_calls=0, paired_deployment=True))
    runner.save(path, ledger)
