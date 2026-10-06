"""Frozen acquisition wiring; synthetic roots only, no environment sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import run_controlled_predictive_consequence_program_v163 as runner
from scripts import run_controlled_predictive_feedback_program_v162 as previous

TEMP = Path(__file__).resolve().parents[1] / 'reports/v163_runtime_tmp'
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
        scope='Fold exclusion, variable candidate roster and fresh paired seeds.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def roots(phase, replicas):
    rows = [dict(root_id=f'{phase}:{life}:{query}:{replica}:{slot}',
        life=life, query=query, replica=replica, slot=slot, board=[1, 2] + [0]*14)
        for life in range(4) for query in ('risk1', 'risk8')
        for replica in replicas for slot in range(2)]
    WORK['synthetic_root_rows'] += len(rows)
    return rows


def candidate_cells(count=2):
    return [dict(heldout_life=life, query=query,
        candidates=[dict(candidate_id=f'P{index}') for index in range(count)])
        for life in range(4) for query in ('risk1', 'risk8')]


def test_screening_excludes_heldout_and_pairs_every_program_arm():
    source = roots('TRAIN_SOURCE', range(2))
    roster = runner.screening_roster(source, candidate_cells())
    WORK['synthetic_screen_roster_rows'] += len(roster)
    assert len(roster) == len({row['branch_id'] for row in roster}) == 1920
    rootmap = {row['root_id']: row for row in source}
    groups = {}
    for row in roster:
        root = rootmap[row['root_id']]
        assert row['heldout_life'] != root['life']
        assert row['suffix'] in range(4)
        assert row['seed'] == runner.branch_seed('SCREEN', root, row['suffix'], row['heldout_life'])
        groups.setdefault((row['root_id'], row['heldout_life'], row['suffix']), []).append(row)
    assert len(groups) == 384
    for rows in groups.values():
        assert [row['mode'] for row in rows] == ['H2', 'P0_A', 'P0_B', 'P1_A', 'P1_B']
        assert len({row['seed'] for row in rows}) == 1
    assert len({rows[0]['seed'] for rows in groups.values()}) == 384
    changed = deepcopy(source)
    for root in changed:
        root.update(result=dict(status='LOST', utility=-1e9), prediction=1e9)
    assert runner.screening_roster(changed, candidate_cells()) == roster


def test_smaller_candidate_pools_are_retained_without_replacements():
    source = roots('TRAIN_SOURCE', range(2))
    cells = candidate_cells(1)
    roster = runner.screening_roster(source, cells)
    WORK['synthetic_screen_roster_rows'] += len(roster)
    assert len(roster) == 1152
    assert {row['mode'] for row in roster} == {'H2', 'P0_A', 'P0_B'}
    cells[0]['candidates'] = []
    reduced = runner.screening_roster(source, cells)
    WORK['synthetic_screen_roster_rows'] += len(reduced)
    empty_fold = [row for row in reduced if row['heldout_life'] == 0
        and ':risk1:' in row['root_id']]
    assert len(empty_fold) == 48
    assert {row['mode'] for row in empty_fold} == {'H2'}
    assert len(reduced) == 1056
    assert {row['suffix'] for row in reduced} == set(range(4))


def test_evaluation_keeps_all_roots_and_six_paired_arms():
    source = roots('EVAL_SOURCE', range(4))
    roster = runner.eval_roster(source)
    WORK['synthetic_eval_roster_rows'] += len(roster)
    assert len(roster) == len({row['branch_id'] for row in roster}) == 6144
    groups = {}
    rootmap = {row['root_id']: row for row in source}
    for row in roster:
        root = rootmap[row['root_id']]
        assert row['heldout_life'] == root['life']
        assert row['seed'] == runner.branch_seed('EVAL', root, row['suffix'])
        assert row['suffix'] in range(16)
        groups.setdefault((row['root_id'], row['suffix']), []).append(row)
    assert len(groups) == 1024
    assert all([row['mode'] for row in rows] == ['H2', 'MODAL', 'LEARNED', 'MATCH_MODAL', 'GLOBAL', 'FIXED']
        and len({row['seed'] for row in rows}) == 1 for rows in groups.values())
    assert len({rows[0]['seed'] for rows in groups.values()}) == 1024


def test_sources_screen_and_eval_are_disjoint_and_version_fresh():
    sources = {runner.source_seed(phase, life, query, replica)
        for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in range(4)
        for query in ('risk1', 'risk8') for replica in range(4)}
    train = roots('TRAIN_SOURCE', range(2)); evaluation = roots('EVAL_SOURCE', range(4))
    screen = {row['seed'] for row in runner.screening_roster(train, candidate_cells())}
    evaluate = {row['seed'] for row in runner.eval_roster(evaluation)}
    assert (len(sources), len(screen), len(evaluate)) == (64, 384, 1024)
    assert sources.isdisjoint(screen) and sources.isdisjoint(evaluate) and screen.isdisjoint(evaluate)
    current = sources | screen | evaluate
    old = {previous.source_seed(phase, life, query, replica)
        for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in range(4)
        for query in ('risk1', 'risk8') for replica in range(4)}
    old.update(row['seed'] for row in previous.screening_roster(train, [dict(heldout_life=l, query=q,
        candidates=[dict(candidate_id=f'P{i}') for i in range(2)])
        for l in range(4) for q in ('risk1', 'risk8')]))
    old.update(row['seed'] for row in previous.eval_roster(evaluation))
    assert current.isdisjoint(old)
    assert all(163*100000000 <= seed < 164*100000000 for seed in current)
    assert runner.MAX_STEPS == 2000
