"""Runner metadata/cache checks with stub certificates and no tape replay."""
from copy import deepcopy
import json

from scripts import run_paired_query_score_v233 as runner


def snapshot(previous):
    return dict(**{key: deepcopy(previous[key]) for key in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity')},
        operators={'SHORT_PASS': ['DELIVERY']*7,
                   'DETOUR_PASS': ['RECOVERY']*5, 'RECOVERY_RETRY': ['LOST']*2},
        fees={key: previous[key] for key in ('source_paid_samples',
              'history_paid_samples', 'current_paid_samples', 'total_reference_paid_samples')})


def proof(queries):
    decisions = {query: dict(policy=row['policy'], certified=True,
        comparisons=[dict(n=5, required_rows=['SHORT_PASS', 'DETOUR_PASS'])])
        for query, row in queries.items()}
    return dict(queries=decisions, all_ready=True, threshold=4320,
                comparison_records=[{}]*6)


def test_fixed_24_roster_order_point_queries_and_paid_reference_metadata(monkeypatch):
    previous = runner.read_rows(runner.INPUT/'inputs.jsonl.gz')
    roster = json.loads((runner.INPUT/'run.json').read_text())['selected']
    original = deepcopy(previous)
    calls = []

    def certificates(operators, case, queries, cache):
        calls.append(deepcopy((operators, case, queries)))
        return proof(queries)

    monkeypatch.setattr(runner.core, 'certificates', certificates)
    snapshots = [snapshot(row) for row in previous]
    before = deepcopy(snapshots)
    results = [runner.qualify(tape, row, {}) for tape, row in zip(snapshots, previous)]
    assert len(results) == 24
    assert [runner.key(row) for row in results] == [runner.key(row) for row in roster]
    for result, row, call, tape in zip(results, previous, calls, snapshots):
        assert call == (tape['operators'], row['case'], row['terminal_plan']['queries'])
        assert {q: r['policy'] for q, r in result['queries'].items()} == {
            q: r['policy'] for q, r in row['terminal_plan']['queries'].items()}
        assert result['queries']['goal']['comparisons'][0]['n'] == 5
        assert result['row_lengths'] == {'SHORT_PASS': 7, 'DETOUR_PASS': 5, 'RECOVERY_RETRY': 2}
        assert result['fees'] == tape['fees']
        assert result['fees']['total_reference_paid_samples'] == (
            row['source_paid_samples']+row['history_paid_samples']+row['current_paid_samples'])
        assert (result['kind'], result['phase'], result['case']) == (row['kind'], row['phase'], row['case'])
        assert result['new_observations'] == result['new_paid_samples'] == 0
    assert previous == original and snapshots == before


def test_qualification_time_and_cache_unique_hits_are_per_call(monkeypatch):
    previous = runner.read_rows(runner.INPUT/'inputs.jsonl.gz')[0]
    tape, cache = snapshot(previous), {}
    clocks = iter((10., 10.375, 20., 20.125))
    monkeypatch.setattr(runner, 'perf_counter', lambda: next(clocks))

    def certificates(operators, case, queries, actual_cache):
        assert actual_cache is cache
        actual_cache.setdefault('stream_a', object())
        actual_cache.setdefault('stream_b', object())
        return proof(queries)

    monkeypatch.setattr(runner.core, 'certificates', certificates)
    first = runner.qualify(tape, previous, cache)
    second = runner.qualify(tape, previous, cache)
    assert (first['unique_score_streams'], first['score_cache_hits']) == (2, 4)
    assert (second['unique_score_streams'], second['score_cache_hits']) == (0, 6)
    assert first['model_seconds'] == .375 and second['model_seconds'] == .125
    assert first['fees'] == second['fees'] == tape['fees']
    assert first['new_observations'] == second['new_observations'] == 0
