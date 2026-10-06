"""Runner checks use synthetic saved observations, never a paid simulator draw."""
from copy import deepcopy
import gzip
import json

from scripts import run_shared_prefix_score_v234 as runner


def previous(index=0):
    queries = {query: dict(policy=policy) for query, policy in
               (('reward', 'WAIT'), ('goal', 'DETOUR_RETRY'), ('risk', 'DETOUR_RETURN'))}
    return dict(life=index // 2, index=index, arm='ORACLE_BALANCED' if index % 2 else 'ORACLE_GAP',
        kind='failure' if index < 12 else 'positive', phase='late_B',
        case={'id': str(index), 'operating': 'low', 'retry_cost': '17/20'}, identity=1,
        terminal_plan=dict(query_ready=index >= 12, queries=queries))


def snapshot(row):
    return dict(**{field: deepcopy(row[field]) for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity')},
        operators={'SHORT_PASS': ['DELIVERY'] * 7, 'DETOUR_PASS': ['RECOVERY'] * 5,
                   'RECOVERY_RETRY': ['LOST'] * 11},
        fees=dict(source_paid_samples=10, history_paid_samples=8, current_paid_samples=5,
                  total_reference_paid_samples=23, evidence_samples=23))


def proof(queries):
    shared = dict(method='shared_prefix_rectangle', certified=True,
        n_by_row={'DETOUR_PASS': 5, 'RECOVERY_RETRY': 11},
        k_by_row={'DETOUR_PASS': 5, 'RECOVERY_RETRY': 0}, row_intervals={})
    direct = dict(method='paired_direct', certified=True, n=5, zero_bets=0)
    decisions = {'reward': dict(policy=queries['reward']['policy'], certified=True)}
    records = []
    for query in ('goal', 'risk'):
        comparisons = [deepcopy(direct), deepcopy(direct), deepcopy(shared)]
        decisions[query] = dict(policy=queries[query]['policy'], certified=True, comparisons=comparisons)
        records.extend(comparisons)
    return dict(queries=decisions, all_ready=True, threshold=3600,
        comparison_records=records,
        evidence_records=[dict(operator=op, n=n, k=k, lower='0', upper='1')
            for op, n, k in (('DETOUR_PASS', 5, 5), ('RECOVERY_RETRY', 11, 0))])


def test_qualification_preserves_policies_paid_rows_and_full_shared_lengths(monkeypatch):
    old, cache, calls = previous(), {}, []
    tape = snapshot(old)
    originals = deepcopy((old, tape))

    def certificates(operators, case, queries, actual_cache):
        calls.append(deepcopy((operators, case, queries)))
        assert actual_cache is cache
        for i in range(4):
            actual_cache.setdefault(('direct', i), object())
        for op in ('DETOUR_PASS', 'RECOVERY_RETRY'):
            actual_cache.setdefault(('bernoulli', op, tuple(operators[op]), 3600), object())
        return proof(queries)

    clocks = iter((10., 10.375, 20., 20.125))
    monkeypatch.setattr(runner.core, 'certificates', certificates)
    monkeypatch.setattr(runner, 'perf_counter', lambda: next(clocks))
    first = runner.qualify(tape, old, cache)
    second = runner.qualify(tape, old, cache)
    assert calls == [(tape['operators'], old['case'], old['terminal_plan']['queries'])] * 2
    assert runner.policies(first['queries']) == runner.policies(old['terminal_plan']['queries'])
    assert first['row_lengths'] == {'SHORT_PASS': 7, 'DETOUR_PASS': 5, 'RECOVERY_RETRY': 11}
    shared = first['queries']['goal']['comparisons'][2]
    assert shared['n_by_row'] == {'DETOUR_PASS': 5, 'RECOVERY_RETRY': 11}
    assert 'n' not in shared and 'zero_bets' not in shared
    assert first['fees'] == second['fees'] == tape['fees']
    assert (first['unique_direct_score_streams'], first['direct_score_cache_hits']) == (4, 0)
    assert (second['unique_direct_score_streams'], second['direct_score_cache_hits']) == (0, 4)
    assert (first['unique_row_intervals'], first['row_interval_cache_hits']) == (2, 0)
    assert (second['unique_row_intervals'], second['row_interval_cache_hits']) == (0, 2)
    assert (first['model_seconds'], second['model_seconds']) == (.375, .125)
    assert first['new_observations'] == second['new_paid_samples'] == 0
    assert (old, tape) == originals


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def test_all_certificates_are_frozen_before_saved_truth_is_read(monkeypatch, tmp_path):
    inputs, paid, output = (tmp_path / name for name in ('inputs', 'paid', 'output'))
    old = [previous(i) for i in range(24)]
    tapes = [snapshot(row) for row in old]
    write_rows(inputs / 'inputs.jsonl.gz', old)
    prior = [dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')},
        queries=deepcopy(row['terminal_plan']['queries']), query_ready=row['terminal_plan']['query_ready'])
        for row in old]
    write_rows(inputs / 'records.jsonl.gz', prior)
    write_rows(paid / 'records.jsonl.gz', prior)
    write_rows(paid / 'tapes.jsonl.gz', tapes)
    saved_scores = [dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')},
        regrets=dict(reward='0', goal='0', risk='1/10'), false_certificates=0) for row in old]
    (paid / 'scores.json').write_text(json.dumps(saved_scores))
    monkeypatch.setattr(runner, 'INPUT', inputs)
    monkeypatch.setattr(runner, 'PAID', paid)
    monkeypatch.setattr(runner, 'OUTPUT', output)
    monkeypatch.setattr(runner, 'capture', lambda: None)
    calls = []

    def certificates(operators, case, queries, cache):
        calls.append(deepcopy((operators, case, queries)))
        return proof(queries)

    monkeypatch.setattr(runner.core, 'certificates', certificates)
    actual_score_frozen = runner.score_frozen

    def score_frozen(results, previous_records):
        run = json.loads((output / 'run.json').read_text())
        assert run['phases'] == ['protocol_frozen', 'tapes_frozen', 'certificates_frozen']
        assert len(runner.read_rows(output / 'records.jsonl.gz')) == len(results) == 24
        assert len(calls) == 24
        return actual_score_frozen(results, previous_records)

    monkeypatch.setattr(runner, 'score_frozen', score_frozen)
    summary = runner.run()
    assert len(calls) == 24 and summary['records'] == 24
    assert summary['false_certificates'] == 24
    assert summary['new_observations'] == summary['new_paid_samples'] == 0
    assert summary['scientific_gate_changed'] is False
    assert (output / 'tapes.jsonl.gz').read_bytes() == (paid / 'tapes.jsonl.gz').read_bytes()
    records = runner.read_rows(output / 'records.jsonl.gz')
    assert [runner.key(row) for row in records] == [runner.key(row) for row in old]
    assert all(runner.policies(new['queries']) == runner.policies(old_row['terminal_plan']['queries'])
               for new, old_row in zip(records, old))
    run = json.loads((output / 'run.json').read_text())
    assert run['complete'] and run['stream_count'] == 180 and run['threshold'] == 3600


def test_changed_policy_cannot_reuse_saved_truth(monkeypatch):
    row = previous()

    def certificates(operators, case, queries, cache):
        certificate = proof(queries)
        certificate['queries']['goal']['policy'] = 'SHORT'
        return certificate

    monkeypatch.setattr(runner.core, 'certificates', certificates)
    import pytest
    with pytest.raises(ValueError, match='preserve the frozen selected policies'):
        runner.qualify(snapshot(row), row, {})
