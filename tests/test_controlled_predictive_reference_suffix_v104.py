"""Synthetic wiring checks: retained namespace, suffix partition and censored costs."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import pytest
from acfqp.science import controlled_predictive_reference_suffix_v104 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_reference_suffix_v104.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        environment_transitions=0, model_transitions=0, neural_fits=0,
        scope='Synthetic raw reference records only; recorded counters do not execute transitions.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def fixture_rows(life=9, query='reward', episode=2, replicas=2, life_base=103000):
    root = dict(life=life, query=query, episode=episode, board=[1] * 10 + [0] * 6)
    raw = []; ground, planning, outcomes = Counter(), Counter(), Counter()
    for replica in range(replicas):
        seed = 8310000000 + (life_base + life) * 10000000 + tuple(m.QUERIES).index(query) * 100000 + episode * 100 + replica
        for oi, option in enumerate(m.OPTIONS):
            duration = 0 if option == 'H2' else int(option.split('_')[1]); steps = 1 + oi % 3
            status = 'CUTOFF' if replica == 0 and oi == 4 else ('WON' if oi == 0 else 'LOST')
            game = dict(seed=seed, initial_board=list(root['board']), status=status, steps_count=steps,
                work=dict(sampled_transitions=steps, environment_random_draws=2 * steps))
            row = dict(option=option, replica=replica, env_seed=seed, model_seed=seed + 1000000000000,
                game=game, planning_counts=dict(model_uniform_draws=4 * steps), controller=dict(
                    events=[{}], initiation_step=0, selected_option=option, fragment_actions=min(duration, steps)))
            raw.append(row); ground.update(game['work']); planning.update(row['planning_counts']); outcomes[status] += 1
    return root, raw, dict(trajectories=len(raw), ground_work=dict(ground), planning_counts=dict(planning),
        outcomes=dict(outcomes), censored_root=bool(outcomes['CUTOFF']))


def test_default_namespace_is_v103_and_life_base_is_explicit():
    root, raw, log = fixture_rows(replicas=32)
    assert all(m.audit_reference(root, raw, log).values())
    assert raw[0]['env_seed'] == 8310000000 + 103009 * 10000000 + 200
    wrong = deepcopy(raw)
    for row in wrong:
        row['env_seed'] += 1000 * 10000000
        row['game']['seed'] += 1000 * 10000000
        row['model_seed'] += 1000 * 10000000
    assert not m.audit_reference(root, wrong, log)['paired_fresh_streams']
    root, raw, log = fixture_rows(life_base=101000)
    assert all(m.audit_reference(root, raw, log, 2, life_base=101000).values())
    assert not m.audit_reference(root, raw, log, 2)['paired_fresh_streams']


def test_inherited_and_new_episode_seeds_are_disjoint_with_paired_options():
    old_seeds, new_seeds = set(), set()
    for life in (9, 10):
        for qi, query in enumerate(m.QUERIES):
            base = 8310000000 + (103000 + life) * 10000000 + qi * 100000
            old_seeds.update(base + episode * 100 + replica for episode in (0, 1) for replica in range(32))
            new_seeds.update(base + episode * 100 + replica for episode in range(2, 8) for replica in range(32))
            for episode in range(2, 8):
                root, raw, log = fixture_rows(life=life, query=query, episode=episode)
                assert all(m.audit_reference(root, raw, log, 2).values())
                for replica in range(2):
                    pairs = [row for row in raw if row['replica'] == replica]
                    assert {row['env_seed'] for row in pairs} == {base + episode * 100 + replica}
                    assert len({row['model_seed'] for row in pairs}) == 1
    assert len(old_seeds) == 256 and len(new_seeds) == 768 and old_seeds.isdisjoint(new_seeds)


def test_missing_or_duplicate_trajectory_is_reported():
    root, raw, log = fixture_rows()
    missing = m.audit_reference(root, raw[:-1], log, 2)
    assert not missing['trajectory_roster_complete'] and not missing['executed_costs_match']
    duplicated = deepcopy(raw); duplicated[-1] = deepcopy(duplicated[0])
    assert not m.audit_reference(root, duplicated, log, 2)['trajectory_roster_complete']


def test_cutoff_is_auditable_and_all_its_cost_remains_charged():
    root, raw, log = fixture_rows()
    assert log['censored_root'] and all(m.audit_reference(root, raw, log, 2).values())
    cutoff = next(row for row in raw if row['game']['status'] == 'CUTOFF')
    lost_cost = deepcopy(log)
    for key, value in cutoff['game']['work'].items():
        lost_cost['ground_work'][key] -= value
    for key, value in cutoff['planning_counts'].items():
        lost_cost['planning_counts'][key] -= value
    assert not m.audit_reference(root, raw, lost_cost, 2)['executed_costs_match']
    terminal = deepcopy(raw); terminal_log = deepcopy(log)
    for row in terminal:
        if row['game']['status'] == 'CUTOFF': row['game']['status'] = 'LOST'
    terminal_log['outcomes']['LOST'] += terminal_log['outcomes'].pop('CUTOFF')
    terminal_log['censored_root'] = False
    assert all(m.audit_reference(root, terminal, terminal_log, 2).values())
    wrong_censor = dict(log, censored_root=False)
    assert not m.audit_reference(root, raw, wrong_censor, 2)['censored_status_matches']


@pytest.mark.parametrize('change,failed', (
    ('board', 'root_boards_match'), ('environment', 'paired_fresh_streams'),
    ('planning', 'paired_fresh_streams'), ('fragment', 'committed_fragments_match'),
    ('model_seed', 'paired_fresh_streams')))
def test_existing_sampler_invariants_detect_changes(change, failed):
    root, raw, log = fixture_rows(); raw = deepcopy(raw)
    if change == 'board': raw[0]['game']['initial_board'] = [0] * 16
    elif change == 'environment': raw[0]['game']['work']['environment_random_draws'] += 1
    elif change == 'planning': raw[0]['planning_counts']['model_uniform_draws'] += 1
    elif change == 'fragment': raw[4]['controller']['fragment_actions'] = 4
    elif change == 'model_seed': raw[0]['model_seed'] += 1
    assert not m.audit_reference(root, raw, log, 2)[failed]
