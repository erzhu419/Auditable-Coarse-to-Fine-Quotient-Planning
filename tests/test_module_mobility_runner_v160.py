"""Fixed V160 acquisition roster checks without sampling physical branches."""
from collections import Counter
import json
from pathlib import Path

import pytest

from scripts import run_controlled_predictive_module_mobility_v160 as runner


TEMP = Path(__file__).resolve().parents[1] / 'reports/v160_runtime_tmp'
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
        scope='Fixed 6144-branch roster, fresh paired seeds and outcome-independent identities.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


class IdentityRoot(dict):
    """Make accidental selection using retained prediction or outcomes observable."""

    def __getitem__(self, key):
        assert key not in {'prediction', 'result', 'outcome', 'utility'}
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in {'prediction', 'result', 'outcome', 'utility'}
        return super().get(key, default)


def synthetic_roots():
    return [IdentityRoot(root_id=f'{life}:{query}:{method}:{slot}', life=life,
        query=query, source_method=method, slot=slot,
        prediction={'advantage': (-1) ** slot}, result={'utility': 100 * slot})
        for life in range(4) for query in ('risk1', 'risk8')
        for method in ('H2', 'LEARN8') for slot in range(4)]


def build_roster(roots):
    rows = runner.branch_roster(roots)
    WORK['roster_rows'] += len(rows)
    return rows


def test_all_three_modes_share_fresh_seeds_without_root_or_suffix_collisions():
    roots = synthetic_roots()
    roster = build_roster(roots)
    assert len(roster) == 6144
    assert len({row['branch_id'] for row in roster}) == 6144
    assert set(row['mode'] for row in roster) == {'H2', 'OTHER8', 'MOBILITY'}
    assert set(row['suffix'] for row in roster) == set(range(32))
    by_root = {root['root_id']: root for root in roots}
    groups = {}
    for row in roster:
        root = by_root[row['root_id']]
        expected_seed = (160 * 100000000 + 20000000 + root['life'] * 1000000
            + ('risk1', 'risk8').index(root['query']) * 100000
            + ('H2', 'LEARN8').index(root['source_method']) * 10000
            + root['slot'] * 100 + row['suffix'])
        assert row['seed'] == expected_seed
        assert row['seed'] == runner.branch_seed(root['life'], root['query'],
            root['source_method'], root['slot'], row['suffix'])
        assert row['branch_id'] == f'{root["root_id"]}:{row["suffix"]}:{row["mode"]}'
        groups.setdefault((root['root_id'], row['suffix']), []).append(row)
    assert len(groups) == 2048
    seeds = set()
    for rows in groups.values():
        assert len(rows) == 3 and len({row['seed'] for row in rows}) == 1
        assert {row['mode'] for row in rows} == {'H2', 'OTHER8', 'MOBILITY'}
        seeds.add(rows[0]['seed'])
    assert len(seeds) == 2048
    previous = {158 * 100000000 + 20000000 + split * 10000000
        + root['life'] * 1000000
        + ('risk1', 'risk8').index(root['query']) * 100000
        + ('H2', 'LEARN8').index(root['source_method']) * 10000
        + root['slot'] * 100 + suffix
        for split in range(2) for root in roots for suffix in range(32)}
    assert seeds.isdisjoint(previous)


def test_roster_uses_all_fixed_identities_in_input_order_without_outcome_access():
    roots = synthetic_roots()
    roster = build_roster(roots)
    assert roster == build_roster(roots)
    expected_order = [(root['root_id'], suffix, mode) for root in roots
        for suffix in range(32) for mode in ('H2', 'OTHER8', 'MOBILITY')]
    assert [(row['root_id'], row['suffix'], row['mode']) for row in roster] == expected_order
    for root in roots:
        root['prediction'] = {'advantage': float('inf')}
        root['result'] = {'utility': float('-inf')}
    assert build_roster(roots) == roster
    reversed_roster = build_roster(list(reversed(roots)))
    assert {row['branch_id']: row for row in reversed_roster} == {
        row['branch_id']: row for row in roster}
    assert runner.SUFFIXES == 32 and runner.MAX_STEPS == 2000
