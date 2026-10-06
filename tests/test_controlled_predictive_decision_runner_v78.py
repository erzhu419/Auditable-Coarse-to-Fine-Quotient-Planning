"""Small actual branch wiring check, using only inherited warmup knowledge."""
from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_acquisition_and_whole_model_comparison_are_paired(tmp_path):
    spec = importlib.util.spec_from_file_location('v78_runner_check',
        ROOT / 'scripts/run_controlled_predictive_decision_v78.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    rule = runner.LearnedDynamics.from_payload(json.loads(
        (runner.SOURCE / 'supplied_dynamics.json').read_text()))
    initial = runner.Knowledge.from_payload(json.loads(
        (runner.SOURCE / 'life_0/checkpoint_15/FROZEN.json').read_text()))
    before = initial.to_payload()
    root = dict(episode=15, step=0, board=[1, 1] + [0]*14)
    branch_path = tmp_path / 'branches.gz'
    labels, acquisition = runner.acquire([root], rule, 99, 0, branch_path)
    with gzip.open(branch_path, 'rt') as handle:
        branches = [json.loads(line) for line in handle]
    assert len(labels) == 2 * len(branches)
    for branch in branches:
        for label in branch['labels']:
            assert label['episode'] == 15 and label['anchor_step'] == 0
            last = min(label['horizon'], len(branch['game']['steps'])-1)
            reward = sum(s['score'] for s in branch['game']['steps'][1:last+1]) / 2048
            assert label['target'][0] == reward
    # Environment streams are shared across action/policy branches of each replica.
    for replica in (0, 1):
        assert len({b['game']['seed'] for b in branches if b['replica'] == replica}) == 1
    pairs, acceptance = runner.compare_rollouts([root], [root], initial, initial, rule,
        99, 0, tmp_path / 'acceptance.gz')
    assert len(pairs) == 8 and acceptance['trajectories'] == 16
    assert all(p['candidate_utility'] == p['incumbent_utility'] for p in pairs)
    assert acceptance['first_action_disagreements'] == 0
    decision = runner.update.decision_acceptance(pairs)
    assert decision['complete_strata'] and not decision['accepted']
    a, _ = runner.evaluate_game('MSE_PLAN', runner.clone(initial), rule, 99, 99, 'reward', max_steps=3)
    b, _ = runner.evaluate_game('DECISION_PLAN', runner.clone(initial), rule, 99, 99, 'reward', max_steps=3)
    assert all(a[key] == b[key] for key in ('seed', 'score', 'steps', 'status', 'utility'))
    assert initial.to_payload() == before
    counts = Counter(acquisition['work'])
    counts.update(acceptance['work'])
    counts.update(a['environment_counts'])
    counts.update(b['environment_counts'])
    ledger = ROOT / 'reports/controlled_predictive_decision_v78.runner_checks.json'
    data = json.loads(ledger.read_text()) if ledger.exists() else {'attempts': []}
    data['attempts'].append(dict(lifecycle=99, main_campaign_calls=0, inherited_model='V77 warmup',
        fits=0, full_support_teacher_calls=0, acquisition=acquisition,
        acceptance=acceptance, evaluation_games=2, environment_counts=dict(counts)))
    runner.save(ledger, data)
