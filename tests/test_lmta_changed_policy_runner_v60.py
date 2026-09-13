"""One-case execution and retention, using synthetic evaluation results."""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('changed_policy_runner_v60_test',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_changed_policy_v60.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.mark.parametrize('status', ['complete', 'resource_limit'])
def test_single_frozen_case_keeps_terminal_status_and_all_cost_views(status, tmp_path, monkeypatch):
    graph_row = dict(graph_id=580109, nodes=3, stratum='hand', p=.5, edges=[[0, 2], [1, 2]])
    monkeypatch.setattr(runner, 'read_source', lambda: graph_row)
    monkeypatch.setattr(runner, 'SOURCES', [])
    events = []
    monkeypatch.setattr(runner.gc, 'collect', lambda: events.append('gc'))

    def evaluated(graph, graph_id, stratum, p, budget, horizon, limits):
        events.append('evaluate')
        assert (graph_id, budget, horizon) == (580109, 2, 3)
        assert limits == runner.PROTOCOL['limits']
        assert len(graph) == 3 and len(graph.edges()) == 2
        return dict(status=status, method='LOOKAHEAD_1_ANALYTIC', wall_seconds=.2,
            decision_seconds=.1, root_value=2.75 if status == 'complete' else None), [dict(statuses=[0, 0, 0])]

    monkeypatch.setattr(runner, 'evaluate', evaluated)
    out = tmp_path / 'result'
    runner.run(out)
    manifest = json.loads((out / 'manifest.json').read_text())
    case = json.loads((out / 'case.json').read_text())
    assert events == ['gc', 'evaluate', 'gc']
    assert manifest['status'] == 'complete' and manifest['completed_cases'] == 1
    assert manifest['successful_cases'] == int(status == 'complete')
    assert manifest['resource_limited_cases'] == int(status == 'resource_limit')
    assert manifest['new_full_policy_evaluations'] == 1 and manifest['total_state_records'] == 1
    assert all(manifest[name] == 0 for name in ('new_graphs', 'new_environment_samples',
        'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls'))
    assert case['status'] == status
    assert case['prepare_gc_seconds'] >= 0 and case['cleanup_seconds'] >= 0
    assert case['decision_total_seconds'] == .1 + case['cleanup_seconds']
    assert case['block_seconds'] == .2 + case['cleanup_seconds']
    assert manifest['data_output_seconds'] >= case['serialization_seconds'] >= 0
    assert (out / 'states.jsonl').read_text().count('\n') == 1
