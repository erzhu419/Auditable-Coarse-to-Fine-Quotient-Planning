"""Frozen paired order and compact retained-query selection without planning."""
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('paired_runner_v57_test',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_paired_timing_v57.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_six_rounds_balance_first_method_for_every_graph_and_reverse_graph_order():
    ids = sorted(seed for panel in runner.PROTOCOL['panels'] for seed in panel['seeds'])
    slots = runner.schedule(reversed(ids))
    warmup = [slot for slot in slots if slot['phase'] == 'warmup']
    measured = [slot for slot in slots if slot['phase'] == 'measured']
    assert len(warmup) == 10 and len(measured) == 768
    assert all(slot['graph_id'] == 550000 for slot in warmup)
    assert Counter(slot['method'] for slot in warmup) == Counter(dict.fromkeys(runner.METHODS, 5))
    first = defaultdict(Counter)
    for repetition in range(6):
        rows = [slot for slot in measured if slot['repetition'] == repetition]
        assert [slot['graph_id'] for slot in rows[::2]] == (ids if repetition % 2 == 0 else ids[::-1])
        for left, right in zip(rows[::2], rows[1::2]):
            assert left['graph_id'] == right['graph_id']
            assert left['position'] == 0 and right['position'] == 1
            assert {left['method'], right['method']} == set(runner.METHODS)
            index = ids.index(left['graph_id'])
            assert left['method'] == runner.METHODS[(repetition + index) % 2]
            first[left['graph_id']][left['method']] += 1
    assert all(value == Counter(dict.fromkeys(runner.METHODS, 3)) for value in first.values())


def test_compact_reference_loading_filters_method_and_regression_without_copying_Q(tmp_path):
    common = dict(statuses=[0, 0, 0], remaining_budget=2, remaining_days=3,
                  selected=[0], planned_value=2.75, decision_work=dict(planner_calls=1),
                  reach_probability=1., root_action_values=[dict(selected=[0], value=2.75)])
    rows = [dict(common, graph_id=550000, method='LOOKAHEAD_FULL'),
            dict(common, graph_id=540009, method='LOOKAHEAD_FULL'),
            dict(common, graph_id=550000, method='LOOKAHEAD_2')]
    (tmp_path / 'states.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    actual = runner.read_references(tmp_path, 'LOOKAHEAD_FULL', {550000})
    assert list(actual) == [550000] and len(actual[550000]) == 1
    query = actual[550000][0]
    assert query['statuses'] == (0, 0, 0) and query['reach_probability'] == 1.
    assert query['decision_work'] == dict(planner_calls=1)
    assert 'root_action_values' not in query and 'method' not in query
