"""Fixed-input metadata and stub certificates; no optimizer or environment draws."""
from collections import Counter
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts import run_kernel_query_profile_v232 as runner


@pytest.fixture(scope='module')
def snapshots():
    rows = runner.read_records()
    failures = json.loads((runner.INPUT/'countermodel_summary.json').read_text())['cases']
    return rows, failures, runner.select(rows, failures)


def key(row):
    return row['life'], row['index'], row['arm']


def test_frozen_failure_roster_and_first_controls_ignore_truth(snapshots):
    rows, failures, selected = snapshots
    assert Counter(r['kind'] for r in selected) == {'failure': 12, 'positive': 12}
    assert len({key(r) for r in selected}) == 24
    assert {key(r) for r in selected if r['kind'] == 'failure'} == {key(r) for r in failures}
    for control in (r for r in selected if r['kind'] == 'positive'):
        eligible = [r for r in rows if r['life'] == control['life'] and r['arm'] == control['arm']
                    and runner.phase(r['index']) == control['phase'] and r['terminal_plan']['query_ready']]
        assert control['index'] == min(r['index'] for r in eligible)
    enriched = [dict(row, true_regret=(-100 if i % 2 else 100)) for i, row in enumerate(rows)]
    assert [key(r) for r in runner.select(enriched, failures)] == [key(r) for r in selected]


def test_inherited_scope_excludes_changed_row_and_separates_prefixes(snapshots):
    row = next(r for r in snapshots[2] if r['case']['context'] == 'B')
    before = deepcopy(row)
    groups = runner.prefixes(row)
    assert [g['name'] for g in groups] == ['pool', 'inherited_pool', 'source', 'inherited_source', 'member']
    assert [g['threshold'] for g in groups] == [240, 480, 240, 480, 2880]
    constraints = row['terminal_plan']['joint_constraints']
    changed = next(op for op in constraints if len(constraints[op]) == 3)
    for group, index in zip(groups, (1, 4, 0, 3, 2)):
        assert group['counts'] == {op: constraints[op][index]['counts'] for op in group['operators']}
        if group['name'].startswith('inherited'):
            assert changed not in group['operators'] and len(group['operators']) == 2
    assert row == before


def test_comparison_and_query_conjunction_prefix_order_and_cache(monkeypatch, snapshots):
    row = next(deepcopy(r) for r in snapshots[2] if r['case']['context'] == 'A')
    before, calls = deepcopy(row), []
    blocker = next(p for p in runner.POLICIES if p != row['terminal_plan']['queries']['goal']['policy'])
    source = runner.prefixes(row)[1]['counts']

    def certificate(case, query, chosen, other, counts, operators, threshold, **kwargs):
        calls.append((query, other, counts))
        certified = counts == source and not (query == 'goal' and other == blocker)
        return {'status': 'certified' if certified else 'unknown'}

    monkeypatch.setattr(runner, 'core', SimpleNamespace(certificate=certificate))
    cache, work = {}, Counter()
    result = runner.qualify(row, cache, work)
    assert not result['query_ready'] and not result['queries']['goal']['certified']
    assert result['queries']['reward']['certified'] and result['queries']['risk']['certified']
    for query, decision in result['queries'].items():
        for comparison in decision['comparisons']:
            blocked = query == 'goal' and comparison['other'] == blocker
            assert [a['prefix'] for a in comparison['attempts']] == (['pool', 'source', 'member'] if blocked else ['pool', 'source'])
            assert comparison['certified'] == (not blocked)
    n = len(calls)
    runner.qualify(row, cache, work)
    assert len(calls) == n and work['profile_cache_hits'] == n
    assert row == before and result['new_observations'] == 0


def test_cache_distinguishes_evidence_threshold_and_cost(snapshots):
    row = snapshots[2][0]
    case, prefix = deepcopy(row['case']), runner.prefixes(row)[0]
    base = runner.cache_key(case, 'goal', 'SHORT', 'WAIT', prefix)
    changed = deepcopy(prefix)
    changed['counts'][changed['operators'][0]]['DELIVERY'] += 1
    assert runner.cache_key(case, 'goal', 'SHORT', 'WAIT', changed) != base
    changed = dict(prefix, threshold=prefix['threshold']+1)
    assert runner.cache_key(case, 'goal', 'SHORT', 'WAIT', changed) != base
    for field, value in (('operating', 'low' if case['operating'] == 'high' else 'high'), ('retry_cost', '1/2')):
        assert runner.cache_key(dict(case, **{field: value}), 'goal', 'SHORT', 'WAIT', prefix) != base
