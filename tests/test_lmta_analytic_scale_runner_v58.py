"""Frozen new-graph roster and paid interrupted output, without model execution."""
import importlib.util
import json
from pathlib import Path

import networkx as nx


SPEC = importlib.util.spec_from_file_location('analytic_scale_runner_v58_test',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_analytic_scale_v58.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_new_roster_holds_expected_degree_and_absolute_budget():
    protocol = runner.PROTOCOL
    assert protocol['budget'] == 2 and protocol['horizon'] == 3
    assert protocol['methods'] == ['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL_ANALYTIC']
    assert [(p['nodes'], p['stratum']) for p in protocol['panels']] == [
        (9, 'sparse'), (9, 'dense'), (11, 'sparse'), (11, 'dense')]
    ids = [seed for p in protocol['panels'] for seed in p['seeds']]
    assert len(ids) == len(set(ids)) == 64
    for panel, first in zip(protocol['panels'], [580000, 580100, 580200, 580300]):
        assert panel['seeds'] == list(range(first, first + 16))
        assert panel['p'] == panel['expected_degree'] / (panel['nodes'] - 1)
    assert protocol['limits'] == dict(max_planner_action_values=2000000,
        max_policy_states=100000, max_wall_seconds=60.)


def test_runner_keeps_limited_case_then_finishes_roster_with_cleanup_cost(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'manifest.json').write_text(json.dumps(dict(status='complete')))
    (source / 'analysis.json').write_text(json.dumps(dict(
        integrity=dict(passed=True), complete_performance_evidence=True)))
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'FROZEN', {})
    monkeypatch.setattr(runner, 'SOURCES', [])
    panel = dict(nodes=3, stratum='hand', expected_degree=1., p=.5, seeds=[1, 2])
    monkeypatch.setattr(runner, 'PROTOCOL', {**runner.PROTOCOL, 'panels': [panel]})
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    monkeypatch.setattr(runner, 'generate_graph', lambda *args, **kwargs: graph)
    events = []
    monkeypatch.setattr(runner.gc, 'collect', lambda: events.append('gc'))

    def evaluated(graph, graph_id, stratum, p, budget, horizon, method, limits):
        events.append((graph_id, method))
        status = 'resource_limit' if len(events) == 2 else 'complete'
        return dict(graph_id=graph_id, method=method, status=status,
            wall_seconds=.2, decision_seconds=.1, state_records=1), [dict(graph_id=graph_id, method=method)]

    monkeypatch.setattr(runner, 'evaluate', evaluated)
    output = tmp_path / 'output'
    runner.run(output)
    manifest = json.loads((output / 'manifest.json').read_text())
    cases = [json.loads(line) for line in (output / 'cases.jsonl').read_text().splitlines()]
    assert manifest['status'] == 'complete' and manifest['completed_cases'] == 6
    assert manifest['resource_limited_cases'] == 1 and manifest['successful_cases'] == 5
    assert manifest['total_state_records'] == 6 and manifest['new_graphs'] == 2
    assert [case['method'] for case in cases] == runner.METHODS * 2
    for index, case in enumerate(cases):
        assert events[3 * index:3 * index + 3] == ['gc', (case['graph_id'], case['method']), 'gc']
        assert case['prepare_gc_seconds'] >= 0 and case['cleanup_seconds'] >= 0
        assert case['decision_total_seconds'] == .1 + case['cleanup_seconds']
        assert case['block_seconds'] == .2 + case['cleanup_seconds']
        assert case['serialization_seconds'] >= 0
    assert manifest['data_output_seconds'] >= sum(case['serialization_seconds'] for case in cases)
    assert all(manifest[name] == 0 for name in ('new_environment_samples', 'new_environment_calls',
        'new_RL_updates', 'new_MCTS_calls'))
