"""Finite selection and alias fixtures; no native models or sampled games."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_td_attribution_v132 as runner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_td_attribution_v132.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0,
        scope='Scripted choices and retained transitions; first feature disagreement, fixed slots and aliases'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def board(index):
    return (index,)+(0,)*15


def selection_fixture(monkeypatch, different_at=1):
    calls = []
    def choose(state, final=False):
        values = {'DOWN': dict(afterstate=board(1), value=3.),
                  'UP': dict(afterstate=board(2 if state[0] == different_at else 1), value=4.)}
        action = 'UP' if final else 'DOWN'
        return dict(action=action, value=values[action]['value'], action_values=values)
    models = [SimpleNamespace(choose=lambda state: choose(state), rule=None),
              SimpleNamespace(choose=lambda state: choose(state, True), rule=None)]
    def advance(row, index, state, rule, work):
        calls.append(index)
        return board(index+1)
    monkeypatch.setattr(runner, 'advance_recorded', advance)
    monkeypatch.setattr(runner, 'feature_difference', lambda model, a, b: {7: 1} if a != b else {})
    monkeypatch.setattr(runner, 'probe_prediction', lambda models, state, choices: dict(board=list(state)))
    row = dict(initial_board=board(0), actions=['DOWN']*3, chosen_values=[3.]*3)
    return models, row, calls


def test_first_nonzero_feature_disagreement_precedes_any_later_candidate(monkeypatch):
    models, row, calls = selection_fixture(monkeypatch)
    work = Counter()
    index, item, trace = runner.first_feature_probe(models, row, work)
    assert index == 1 and item['board'] == list(board(1))
    assert calls == [0] and trace['scanned_steps'] == 2
    assert trace['differing_candidates'] == [
        dict(index=0, mid_action='DOWN', final_action='UP', nonzero_features=False),
        dict(index=1, mid_action='DOWN', final_action='UP', nonzero_features=True)]
    assert work['feature_difference_checks'] == 2
    # Return/status are unnecessary inputs to selection, so changing them cannot rank roots.
    row.update(result=dict(utility=-999.), status='LOST')
    assert runner.first_feature_probe(models, row, Counter()) == (index, item, trace)
    row.update(result=dict(utility=999.), status='WON')
    assert runner.first_feature_probe(models, row, Counter()) == (index, item, trace)


def test_missing_feature_candidate_preserves_entire_selection_trace(monkeypatch):
    models, row, calls = selection_fixture(monkeypatch, different_at=None)
    index, item, trace = runner.first_feature_probe(models, row, Counter())
    assert index is None and item is None
    assert calls == [0, 1, 2] and trace['scanned_steps'] == 3
    assert [r['index'] for r in trace['differing_candidates']] == [0, 1, 2]
    assert not any(r['nonzero_features'] for r in trace['differing_candidates'])


@pytest.mark.parametrize('field, replacement', [('actions', ['UP']*3), ('chosen_values', [9.]*3)])
def test_changed_retained_mid_action_or_value_stops_selection(monkeypatch, field, replacement):
    models, row, calls = selection_fixture(monkeypatch)
    row[field] = replacement
    with pytest.raises(ValueError, match='MID model no longer reproduces'):
        runner.first_feature_probe(models, row, Counter())
    assert calls == []


def test_roster_keeps_first_feature_aliases_missing_slots_and_life_offsets(monkeypatch, tmp_path):
    models = [SimpleNamespace(counts=Counter(), rule=None, choose=lambda state: dict(action='DOWN')),
              SimpleNamespace(counts=Counter(), rule=None, choose=lambda state: dict(action='UP'))]
    monkeypatch.setattr(runner, 'load_models', lambda source, folder: (models, {}))
    rows = [dict(checkpoint=age, replica=replica, query='risk8', method='PRIOR', seed=100+replica,
                 result=dict(utility=(-1 if age == runner.AGES[0] else 1)*replica))
            for age in runner.AGES for replica in range(runner.REPLICAS)]
    monkeypatch.setattr(runner, 'read_rows', lambda path: rows)
    monkeypatch.setattr(runner, 'board_at_first_divergence', lambda left, right, rule:
        dict(index=0 if left['replica'] < 2 else None, diverged=left['replica'] < 2,
             board=board(1), left_action='DOWN', right_action='UP', counts={}))
    monkeypatch.setattr(runner, 'probe_prediction', lambda models, state, choices: dict(board=list(state)))
    trace = dict(scanned_steps=1, differing_candidates=[])
    monkeypatch.setattr(runner, 'first_feature_probe', lambda models, row, work:
        (0, dict(board=list(board(1 if row['replica'] == 0 else 2))), trace)
        if row['replica'] in (0, 2) else (None, None, trace))
    prepared = [runner.prepare_lifecycle(dict(life=life, control_trace='scripted'), tmp_path)
                for life in (1, 0)]
    for life in prepared:
        assert len(life['cases']) == 32 and len(life['probes']) == 2
        cases = {(row['group'], row['replica']): row for row in life['cases']}
        assert cases['FIRST', 0]['local_probe_id'] == cases['FIRST', 1]['local_probe_id'] == 0
        assert cases['FEATURE', 0]['local_probe_id'] == 0
        assert cases['FEATURE', 2]['local_probe_id'] == 1
        assert not cases['FIRST', 2]['available'] and cases['FIRST', 2]['local_probe_id'] is None
        assert not cases['FEATURE', 1]['available'] and cases['FEATURE', 1]['selection_trace'] == trace
    roster = runner.assemble_roster(prepared)
    assert len(roster['cases']) == 64 and len(roster['probes']) == 4
    assert [p['life'] for p in roster['probes']] == [0, 0, 1, 1]
    cases = {(r['life'], r['group'], r['replica']): r for r in roster['cases']}
    assert cases[0, 'FEATURE', 2]['probe_id'] == 1
    assert cases[1, 'FEATURE', 2]['probe_id'] == 3
    assert cases[1, 'FIRST', 2]['probe_id'] is None
    assert len({r['case_id'] for r in roster['cases']}) == 64


def test_recorded_goal_step_keeps_its_actual_spawn_without_random_sampling():
    after = (11,)+(0,)*15
    rule = SimpleNamespace(swipe=lambda state, action, work: (after, 2048, True))
    row = dict(actions=['LEFT'], scores=[2048], spawned_cells=[3], spawned_ranks=[1])
    work = Counter()
    actual = runner.advance_recorded(row, 0, (10, 10)+(0,)*14, rule, work)
    assert actual == (11, 0, 0, 1)+(0,)*12
    assert work == Counter(recorded_spawns_replayed=1)
