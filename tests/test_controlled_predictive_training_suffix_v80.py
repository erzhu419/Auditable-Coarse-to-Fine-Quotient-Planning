"""Training continuation preserves the forced root, fixed policy, and RNG."""
from collections import Counter
import json
from pathlib import Path

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_lifelong_planner_v77 import policy_action
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_training_suffix_v80 import complete_training_branch


ROOT = Path(__file__).resolve().parents[1]


def test_fixed_policy_training_suffix_matches_uninterrupted_game(monkeypatch):
    ledger = Counter()
    for name in ('swipe_board_v1', 'state_from_board_v1', 'step_v1'):
        original = getattr(ground, name)

        def counted(*args, _function=original, _name=name, **kwargs):
            ledger[_name] += 1
            return _function(*args, **kwargs)

        monkeypatch.setattr(ground, name, counted)

    rule = LearnedDynamics.from_payload(json.loads((ROOT /
        'reports/controlled_predictive_decision_v78/supplied_dynamics.json').read_text()))
    policy, forced = 'SPACE', 'DOWN'
    policy_work = Counter()

    def act(board, step):
        return forced if step == 0 else policy_action(board, policy, rule, policy_work)

    board, seed = (1, 1) + (0,) * 14, 809901
    full = rollout_from_board(board, seed, act, max_steps=12)
    prefix = rollout_from_board(board, seed, act, max_steps=5)
    raw = dict(root=dict(board=list(board), episode=15, step=0),
               policy=policy, action=forced, game=prefix)
    before = json.loads(json.dumps(raw))
    completed, log, suffix = complete_training_branch(raw, rule, max_total_steps=12)
    assert raw == before
    assert completed['steps'] == full['steps']
    assert suffix['steps'] == full['steps'][5:]
    assert completed['steps'][0]['action'] == forced
    assert any(step['action'] != forced for step in suffix['steps'])
    for key in ('seed', 'initial_board', 'initial_spawns', 'final_board', 'status',
                'return_score', 'steps_count', 'work'):
        assert completed[key] == full[key]
    assert log['resumed'] and log['prefix_steps'] == 5 and log['new_steps'] == 7
    assert log['restoration_random_draws'] == 10
    assert log['prefix_work'] == prefix['work']
    assert log['new_work'] == suffix['work']
    assert log['new_work']['sampled_transitions'] == 7
    assert log['new_work']['environment_random_draws'] == 14
    assert log['policy_work']['learned_terminal_checks'] == 7

    terminal = rollout_from_board((10, 10) + (0,) * 14, seed,
                                  lambda *_: 'LEFT', max_steps=1)
    assert terminal['status'] == 'WON'
    old_ground = dict(ledger)
    done, terminal_log, empty = complete_training_branch(
        dict(game=terminal, action='LEFT', policy=policy), rule)
    assert done['steps'] == terminal['steps']
    assert done['return_score'] == terminal['return_score']
    assert not terminal_log['resumed']
    assert terminal_log['new_work'] == terminal_log['policy_work'] == {}
    assert terminal_log['restoration_random_draws'] == 0
    assert empty['steps_count'] == 0 and empty['steps'] == []
    assert dict(ledger) == old_ground

    sampled = Counter()
    for game in (full, prefix, suffix, terminal):
        sampled.update({key: game['work'].get(key, 0) for key in
                        ('sampled_transitions', 'environment_random_draws')})
    ledger.update(sampled)
    ledger['restoration_random_draws'] += log['restoration_random_draws']
    path = ROOT / 'reports/controlled_predictive_target_horizon_v80.suffix_checks.json'
    data = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    data['attempts'].append(dict(seed=seed, tests=1, main_campaign_calls=0,
        full_support_teacher_calls=ledger.get('step_v1', 0), work=dict(ledger),
        prefix_policy_work=dict(policy_work), suffix_policy_work=log['policy_work']))
    path.write_text(json.dumps(data, indent=2) + '\n')
