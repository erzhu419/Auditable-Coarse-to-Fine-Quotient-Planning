"""Check real prefix equality, arm isolation and acquisition cost accounting."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import common_inheritance_v246 as prefix

DIRECTORY = Path(__file__).resolve().parents[1]/'reports/query_allocation_lifecycle_v245'


def first_return(life):
    with gzip.open(DIRECTORY/f'records_life_{life:02d}.jsonl.gz', 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['arm'] == 'ONE_WAY' and row['index'] == 54:
                return row


@pytest.mark.parametrize('life,target_paid', [(0, 6768), (1, 9216), (2, 7952)])
def test_replay_matches_actual_first_return_and_charges_all_paid_prefix(life, target_paid):
    observed = prefix.load_prefix(DIRECTORY, life)
    state, ledger = prefix.replay_prefix(observed, Counter())
    retained = first_return(life)
    counts = prefix.core.point_counts(retained['case'], state, retained['identity'])
    assert counts == retained['pooled_before'] == retained['initial_plan']['evidence_counts']
    assert ledger['source_samples_by_context'] == {'A': 3456, 'B': 1152}
    assert ledger['source_paid_samples'] == retained['source_paid_samples'] == 4608
    assert ledger['history_paid_samples'] == retained['history_paid_samples'] == target_paid
    assert ledger['total_prefix_paid_samples'] == target_paid+4608
    assert sum(ledger['target_batches_by_context'].values())*16 == target_paid
    assert state['a_at_switch'] == state['a']
    assert state['return_merge'] is None and state['arm'] == 'ONE_WAY'


def test_compact_loader_excludes_return_other_arms_plans_and_truth():
    observed = prefix.load_prefix(DIRECTORY, 0)
    assert len(observed['targets']) == 48
    assert [row['index'] for row in observed['targets']] == list(prefix.PREFIX_TARGETS)
    assert {row['case']['stage'] for row in observed['targets']} == {'A', 'B'}
    assert all(set(row) == {'index', 'identity', 'case', 'record_position', 'batches'}
               for row in observed['targets'])
    assert all(set(batch) == {'operator', 'increments'}
               for row in observed['targets'] for batch in row['batches'])
    assert set(observed) == {'life', 'sources', 'targets', 'changed_operator', 'b_to_a', 'reference'}
    assert observed['reference']['arm'] == 'ONE_WAY'


def test_replays_do_not_share_native_banks_or_mutate_the_retained_prefix():
    observed = prefix.load_prefix(DIRECTORY, 2)
    before = deepcopy(observed)
    left, left_cost = prefix.replay_prefix(observed)
    right, right_cost = prefix.replay_prefix(observed)
    original_right = deepcopy(right)
    operator = prefix.core.OPERATORS[0]
    increments = dict.fromkeys(prefix.core.ALPHABETS[operator], 0)
    increments['DELIVERY'] = 16
    prefix.core.observe(left, {'context': 'A', 'stage': 'A_RETURN'}, 0, operator, increments)
    left_cost['reference']['arm'] = 'mutated'
    assert right == original_right and observed == before
    assert right_cost['reference']['arm'] == 'ONE_WAY'
    assert left['b'] == right['b'] and left['a_at_switch'] == right['a_at_switch']
    assert left['a']['pools'][0][operator]['DELIVERY'] == right['a']['pools'][0][operator]['DELIVERY']+16
