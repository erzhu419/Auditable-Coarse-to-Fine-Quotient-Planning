"""Keep the known regression out of the fresh panel and avoid rerunning its controls."""
import importlib.util
import json
from pathlib import Path

import networkx as nx


def test_frozen_roster_dispatches_fresh_controls_and_only_regression_candidate(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('tie_runner_v55_test',
        root / 'scripts/run_lmta_tie_refinement_v55.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    source = tmp_path / 'source'
    source.mkdir()
    regression = dict(graph_id=540009, nodes=7, stratum='sparse', expected_degree=1.5, p=.25, edges=[])
    (source / 'manifest.json').write_text(json.dumps(dict(status='complete', graphs=[regression])))
    (source / 'analysis.json').write_text(json.dumps(dict(complete_quality_evidence=True)))
    controls = [dict(graph_id=540009, method=m, root_value=5.5) for m in runner.METHODS if m != runner.CANDIDATE]
    (source / 'cases.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in controls))
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'FROZEN', [])
    monkeypatch.setattr(runner, 'SOURCES', [])
    generated, calls = [], []

    def fake_graph(nodes, seed, p):
        generated.append((seed, nodes, p))
        graph = nx.DiGraph()
        graph.add_nodes_from(range(nodes))
        return graph

    def fake_evaluator(kind):
        def evaluate(graph, graph_id, stratum, p, budget, horizon, method, limits):
            calls.append((graph_id, method, kind))
            assert budget == 2 and horizon == 3 and limits == runner.PROTOCOL['limits']
            return dict(graph_id=graph_id, method=method, status='complete'), []
        return evaluate

    monkeypatch.setattr(runner, 'generate_graph', fake_graph)
    monkeypatch.setattr(runner, 'evaluate_control', fake_evaluator('control'))
    monkeypatch.setattr(runner, 'evaluate_candidate', fake_evaluator('candidate'))
    output = tmp_path / 'run'
    runner.run(output)
    expected = [(seed, method, 'candidate' if method == runner.CANDIDATE else 'control')
                for panel in runner.PROTOCOL['panels'] for seed in panel['seeds'] for method in runner.METHODS]
    assert calls == expected + [(540009, runner.CANDIDATE, 'candidate')]
    assert len(generated) == 64 and all(seed != 540009 for seed, _, _ in generated)
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['status'] == 'complete'
    assert manifest['completed_cases'] == manifest['successful_cases'] == 257
    assert manifest['resource_limited_cases'] == 0
    assert manifest['regression_controls'] == controls
    assert sum(graph['panel'] == 'fresh' for graph in manifest['graphs']) == 64
    assert sum(graph['panel'] == 'regression' for graph in manifest['graphs']) == 1
    assert len((output / 'cases.jsonl').read_text().splitlines()) == 257
