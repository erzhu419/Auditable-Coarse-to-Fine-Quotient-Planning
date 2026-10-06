"""V161 acquisition wiring checks using synthetic traces, without sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import run_controlled_predictive_program_consolidation_v161 as runner


TEMP = Path(__file__).resolve().parents[1] / 'reports/v161_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP / 'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before,
        environment_samples=0, native_calls=0, production_source_reads=0,
        synthetic_work=dict(WORK),
        scope='Outcome-independent quarter roots, fold exclusion and paired fresh seeds.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def source_row(life=0, query='risk1', replica=0, status='WON', phase='TRAIN_SOURCE'):
    """Supply recorded afterstates directly; no environment is executed."""
    steps = 22
    return dict(life=life, query=query, replica=replica, seed=1234,
        source_id=f'{phase}:{life}:{query}:{replica}', phase=phase,
        initial_board=[1, 2] + [0] * 14,
        actions=['DOWN'] * steps,
        choices=[dict(afterstate=[step % 9 + 1] + [0] * 15)
            for step in range(steps)],
        spawned_cells=[15] * steps, spawned_ranks=[1 + step % 2 for step in range(steps)],
        scores=[0] * steps, result=dict(steps=steps, status=status,
            utility=1000 if status == 'WON' else -1000))


def all_roots(phase, replicas):
    roots = [root for life in range(4) for query in ('risk1', 'risk8')
        for replica in replicas
        for root in runner.roots_from_source(source_row(life, query, replica, phase=phase), phase)]
    WORK['synthetic_root_rows'] += len(roots)
    return roots


def candidate_cells():
    words = [list(word) for word in (
        ('DOWN', 'LEFT', 'DOWN', 'LEFT'),
        ('DOWN', 'RIGHT', 'DOWN', 'RIGHT'),
        ('UP', 'LEFT', 'UP', 'LEFT'),
        ('UP', 'RIGHT', 'UP', 'RIGHT'))]
    return [dict(heldout_life=heldout, query=query,
        training_lives=[life for life in range(4) if life != heldout],
        candidates=[dict(candidate_id=f'P{index}', word=word, occurrences=10-index)
            for index, word in enumerate(words)], counts={}, source_games=[])
        for heldout in range(4) for query in ('risk1', 'risk8')]


def test_quarter_roots_reconstruct_predecision_boards_without_outcome_selection():
    row = source_row(life=2, query='risk8', replica=1)
    roots = runner.roots_from_source(row, 'TRAIN_SOURCE')
    WORK['synthetic_root_rows'] += len(roots)
    assert [root['source_step'] for root in roots] == [5, 16]
    assert [root['slot'] for root in roots] == [0, 1]
    for root in roots:
        step = root['source_step']
        expected = list(row['choices'][step-1]['afterstate'])
        expected[row['spawned_cells'][step-1]] = row['spawned_ranks'][step-1]
        assert root['board'] == expected
        assert root['source_steps'] == 22
        assert root['source_seed'] == row['seed']
        assert root['source_id'] == 'TRAIN_SOURCE:2:risk8:1'
        assert root['root_id'] == f'TRAIN_SOURCE:2:risk8:1:{root["slot"]}'
    alternative = deepcopy(row)
    alternative['result'].update(status='LOST', utility=-1e12,
        components=[0.0, 1.0, 0.0])
    alternative['predictions'] = [float('inf')] * len(row['actions'])
    assert runner.roots_from_source(alternative, 'TRAIN_SOURCE') == roots
    assert runner.roots_from_source(row, 'EVAL_SOURCE') != roots


def test_screening_roster_uses_only_other_histories_with_all_four_candidates():
    roots = all_roots('TRAIN_SOURCE', range(2))
    assert len(roots) == 32
    roster = runner.screening_roster(roots, candidate_cells())
    WORK['synthetic_screen_roster_rows'] += len(roster)
    assert len(roster) == 1920
    assert len({row['branch_id'] for row in roster}) == 1920
    by_root = {root['root_id']: root for root in roots}
    groups = {}
    for row in roster:
        root = by_root[row['root_id']]
        assert row['heldout_life'] != root['life']
        assert row['suffix'] in range(4)
        assert row['seed'] == runner.branch_seed('SCREEN', root, row['suffix'],
            heldout_life=row['heldout_life'])
        assert row['branch_id'] == (f'{root["root_id"]}:fold{row["heldout_life"]}:'
            f'{row["suffix"]}:{row["mode"]}')
        groups.setdefault((root['root_id'], row['heldout_life'], row['suffix']), []).append(row)
    assert len(groups) == 384
    for rows in groups.values():
        assert {row['mode'] for row in rows} == {'H2', 'P0', 'P1', 'P2', 'P3'}
        assert len({row['seed'] for row in rows}) == 1
    assert len({rows[0]['seed'] for rows in groups.values()}) == 384
    changed = deepcopy(roots)
    for root in changed:
        root.update(result=dict(status='LOST', utility=-1000), prediction=dict(advantage=1e9))
    assert runner.screening_roster(changed, candidate_cells()) == roster


def test_evaluation_roster_retains_all_new_roots_and_three_paired_arms():
    roots = all_roots('EVAL_SOURCE', range(4))
    assert len(roots) == 64
    roster = runner.eval_roster(roots)
    WORK['synthetic_eval_roster_rows'] += len(roster)
    assert len(roster) == 3072
    assert len({row['branch_id'] for row in roster}) == 3072
    by_root = {root['root_id']: root for root in roots}
    groups = {}
    for row in roster:
        root = by_root[row['root_id']]
        assert row['heldout_life'] == root['life']
        assert row['suffix'] in range(16)
        assert row['seed'] == runner.branch_seed('EVAL', root, row['suffix'])
        assert row['branch_id'] == f'{root["root_id"]}:{row["suffix"]}:{row["mode"]}'
        groups.setdefault((root['root_id'], row['suffix']), []).append(row)
    assert len(groups) == 1024
    for rows in groups.values():
        assert {row['mode'] for row in rows} == {'H2', 'FREQ', 'BEST'}
        assert len({row['seed'] for row in rows}) == 1
    assert len({rows[0]['seed'] for rows in groups.values()}) == 1024
    assert [(row['root_id'], row['suffix'], row['mode']) for row in roster] == [
        (root['root_id'], suffix, mode) for root in roots
        for suffix in range(16) for mode in ('H2', 'FREQ', 'BEST')]


def test_source_screen_and_eval_seed_streams_are_disjoint_and_version_fresh():
    source = {runner.source_seed(phase, life, query, replica)
        for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in range(4)
        for query in ('risk1', 'risk8') for replica in range(4)}
    screen = {row['seed'] for row in runner.screening_roster(
        all_roots('TRAIN_SOURCE', range(2)), candidate_cells())}
    evaluation = {row['seed'] for row in runner.eval_roster(
        all_roots('EVAL_SOURCE', range(4)))}
    assert len(source) == 64 and len(screen) == 384 and len(evaluation) == 1024
    assert source.isdisjoint(screen) and source.isdisjoint(evaluation)
    assert screen.isdisjoint(evaluation)
    assert all(161 * 100000000 <= seed < 162 * 100000000
        for seed in source | screen | evaluation)
    assert runner.MAX_STEPS == 2000
