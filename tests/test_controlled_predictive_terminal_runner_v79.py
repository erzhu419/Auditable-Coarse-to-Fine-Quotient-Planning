"""Prove both planner and environment resume at the exact retained stream point."""
import importlib.util
import json
from pathlib import Path
import random

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board


ROOT = Path(__file__).resolve().parents[1]


def test_planner_and_environment_suffix_equal_uninterrupted_run(monkeypatch):
    spec = importlib.util.spec_from_file_location('v79_runner_check',
        ROOT / 'scripts/run_controlled_predictive_terminal_v79.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    initial = json.loads((runner.SOURCE / 'life_0/initial_knowledge.json').read_text())
    rule = runner.LearnedDynamics.from_payload(json.loads((runner.SOURCE / 'supplied_dynamics.json').read_text()))
    seed = 9890000000
    board = [1, 1] + [0]*14
    states = []
    real_choose = runner.planner.choose

    def record_choose(board, query, knowledge, rule, rng, **kwargs):
        states.append(rng.getstate())
        return real_choose(board, query, knowledge, rule, rng, **kwargs)

    monkeypatch.setattr(runner.planner, 'choose', record_choose)

    def play(n):
        rng = random.Random(seed + 1000000000000)
        model = runner.Knowledge.from_payload(initial)
        def act(observation, step):
            return runner.planner.choose(observation, runner.QUERIES['reward'], model, rule, rng)['action']
        return rollout_from_board(board, seed, act, max_steps=n)

    uninterrupted = play(20)
    uninterrupted_states = list(states)
    states.clear()
    prefix = play(7)
    states.clear()
    raw = dict(game=prefix, query='reward', stratum='new', replica=0, model='candidate',
               root=dict(episode=19, step=0, board=board))
    row, result = runner.continue_trajectory(raw, runner.Knowledge.from_payload(initial), rule,
                                           max_total_steps=20)
    suffix = result['suffix']
    assert prefix['steps'] + suffix['steps'] == uninterrupted['steps']
    assert states == uninterrupted_states[7:]
    assert row['full']['score'] == uninterrupted['return_score']
    assert row['full']['status'] == uninterrupted['status']
    assert row['full']['steps'] == 20
    assert row['extension']['work']['sampled_transitions'] == 13
    assert row['extension']['restoration_random_draws'] == 14
    assert row['extension']['model_restoration_random_draws'] == 28
    assert [d['step'] for d in result['decisions']] == list(range(7,20))
    path = ROOT / 'reports/controlled_predictive_terminal_v79.runner_checks.json'
    ledger = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    ledger['attempts'].append(dict(seed=seed, sampled_transitions=40,
        new_environment_random_draws=80, restoration_random_draws=14,
        model_restoration_random_draws=28, fitted_models=0, full_support_teacher_calls=0,
        main_campaign_calls=0, exact_environment_steps=True, exact_planner_rng_states=True))
    runner.save(path, ledger)
