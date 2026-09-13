"""Exact support, suffix sharing, and contradictory-label toy checks."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_observation_dag_v70 import Encoder, compile_encoder


LEDGER = dict(compilations=[], encoding_counts=Counter())


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_observation_dag_v70.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
                                   scope='toy labels only; no V69 main cohort', **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def compile_labels(labels):
    result = compile_encoder(labels)
    LEDGER['compilations'].append(dict(counts=result.counts, elapsed_seconds=result.elapsed_seconds))
    return result


def encode(encoder, board, h):
    return encoder.encode(board, h, LEDGER['encoding_counts'])


def test_equal_labels_do_not_accept_missing_rank_combinations_or_skip_suffixes():
    first, second = (1, 1) + (0,) * 14, (2, 2) + (0,) * 14
    encoder = compile_labels([(2, first, 7), (2, second, 7)])
    for board in (first, second):
        work = Counter()
        assert encoder.encode(board, 2, work) == 7
        assert work['rank_tests'] == 16 and work['node_visits'] == 17
        LEDGER['encoding_counts'].update(work)
    for first_rank, second_rank in ((1, 2), (2, 1)):
        assert encode(encoder, (first_rank, second_rank) + (0,) * 14, 2) is None
    for cell in range(16):
        unknown = list(first)
        unknown[cell] = 18
        assert encode(encoder, tuple(unknown), 2) is None
    assert encode(encoder, first, 3) is None
    assert encode(encoder, first + (0,), 2) is None


def test_suffix_dag_and_json_roundtrip_preserve_exact_finite_mapping():
    labels = [(h, (a, b) + (0,) * 14, b + 7)
              for h in (1, 2) for a in (1, 2) for b in (1, 2)]
    encoder = compile_labels(labels)
    assert encoder.counts['dag_nodes'] < encoder.counts['trie_prefix_visits']
    assert encoder.counts['shared_subtree_visits'] > 0
    assert encoder.roots[1] == encoder.roots[2]
    root_position, root_edges = encoder.nodes[encoder.roots[1]]
    assert root_position == 0 and len(set(root_edges.values())) == 1
    payload = json.loads(json.dumps(encoder.to_payload()))
    assert set(payload) == {'roots', 'nodes'}
    restored = Encoder.from_payload(payload)
    for h, board, expected in labels:
        assert encode(restored, board, h) == expected
    assert encode(restored, (3, 1) + (0,) * 14, 1) is None
    assert restored.counts['dag_nodes'] == encoder.counts['dag_nodes']


def test_duplicate_labels_are_valid_but_conflicting_cells_stop_compilation():
    board = (1,) + (0,) * 15
    encoder = compile_labels([(1, board, 4), (1, board, 4)])
    assert encoder.counts['distinct_observations'] == 1
    assert encoder.counts['duplicate_observations'] == 1
    assert encode(encoder, board, 1) == 4
    with pytest.raises(ValueError, match='conflicting contract labels'):
        compile_encoder([(1, board, 4), (1, board, 5)])
    LEDGER['conflicting_label_attempts'] = 1
