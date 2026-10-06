"""Finite policy fitting and random-control checks without natural-game samples."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_policy_programs_v140 as core


ROOT = Path(__file__).resolve().parents[1]
FITS, RANDOMS = [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_policy_programs_v140.tree_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, fit_work=[item['work'] for item in FITS],
        random_work=[item['work'] for item in RANDOMS], newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=0,
        scope='Finite board predicates, deterministic fitting, prefix isolation and random-control shape.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def examples(empty, action, count=8, previous='DOWN'):
    return [dict(board=[1]*(16-empty)+[0]*empty, previous_action=previous, action=action)
        for _ in range(count)]


def fit(rows):
    result = core.fit_programs(rows)
    FITS.append(result)
    return result


def test_predicate_order_counts_only_positive_orthogonal_neighbors():
    board = [0]*16
    board[3] = board[4] = 7
    observed = core.features(board)
    assert observed == (False, False, False, True, True, True,
        False, True, False, False, True, False, True, True)
    board[2] = 7
    assert core.features(board)[3:6] == (False, True, True)
    assert core.features([0]*16)[6:] == (False,)*8


def test_equal_pair_and_empty_threshold_boundaries_are_inclusive():
    board = [1, 1, 1, 0]+[0]*12
    assert core.features(board)[3:6] == (False, True, True)
    board = [1, 1, 1, 1, 1]+[0]*11
    assert core.features(board)[3:6] == (False, False, True)
    for empty, expected in ((2, (True, True, True)), (4, (False, True, True)),
        (8, (False, False, True)), (9, (False, False, False))):
        assert core.features([1]*(16-empty)+[0]*empty)[:3] == expected


def test_lowest_predicate_wins_equal_gain_and_false_true_children_are_distinct():
    model = fit(examples(0, 'DOWN')+examples(12, 'LEFT'))
    assert model['trees'][0][0][0] == 0
    assert model['trees'][0][1][1] == 1  # sparse board: predicate false
    assert model['trees'][0][2][1] == 0  # dense board: predicate true
    assert core.rank_actions([1]*16, 'DOWN', model)[0] == 'DOWN'
    assert core.rank_actions([1]*4+[0]*12, 'DOWN', model)[0] == 'LEFT'
    assert model['metadata']['fit_classification_mistakes'] == 0
    assert model['metadata']['node_sample_counts'][0][:3] == [16, 8, 8]


def test_minimum_child_blocks_seven_examples_but_accepts_eight():
    blocked = fit(examples(0, 'DOWN', 9)+examples(12, 'LEFT', 7))
    accepted = fit(examples(0, 'DOWN', 8)+examples(12, 'LEFT', 8))
    assert blocked['trees'][0][0][0] == -1
    assert accepted['trees'][0][0][0] == 0
    assert blocked['metadata']['fit_classification_mistakes'] == 7


def test_depth_two_stops_even_when_a_child_has_remaining_separable_errors():
    model = fit(sum((examples(empty, action) for empty, action in
        ((0, 'DOWN'), (3, 'LEFT'), (6, 'RIGHT'), (12, 'UP'))), []))
    tree = model['trees'][0]
    assert tree[0][0] == 0 and tree[1][0] == 1
    assert all(node[0] == -1 for node in tree[3:])
    assert model['metadata']['fit_classification_mistakes'] == 8
    assert core.rank_actions([1]*10+[0]*6, 'DOWN', model)[0] == 'RIGHT'
    assert core.rank_actions([1]*4+[0]*12, 'DOWN', model)[0] == 'RIGHT'


def test_zero_gain_does_not_split_even_when_two_predicates_could_explain_xor(monkeypatch):
    patterns = ((False, False), (False, True), (True, False), (True, True))
    monkeypatch.setattr(core, 'features', lambda board: patterns[board[0]]+(False,)*12)
    rows = [dict(board=[index]*16, previous_action='DOWN',
        action='LEFT' if left != right else 'DOWN')
        for index, (left, right) in enumerate(patterns) for _ in range(8)]
    model = fit(rows)
    assert model['trees'][0][0][0] == -1
    assert model['metadata']['fit_classification_mistakes'] == 16


def test_previous_action_trees_and_frequency_ties_are_independent():
    rows = examples(0, 'LEFT', 8, 'DOWN')+examples(0, 'RIGHT', 8, 'DOWN')
    rows += examples(0, 'UP', 8, 'LEFT')+examples(0, 'DOWN', 8, 'RIGHT')
    model = fit(rows)
    assert core.rank_actions([1]*16, 'DOWN', model) == ('LEFT', 'RIGHT', 'DOWN', 'UP')
    assert core.rank_actions([1]*16, 'LEFT', model)[0] == 'UP'
    assert core.rank_actions([1]*16, 'RIGHT', model)[0] == 'DOWN'
    assert core.rank_actions([1]*16, 'UP', model) == core.ACTIONS
    assert model['metadata']['examples_by_previous_action'] == [16, 8, 8, 0]


def test_empty_and_unvisited_nodes_have_fixed_lexical_action_order():
    model = fit([])
    assert model['trees'] == [[[-1, 0, 1, 2, 3] for _ in range(7)] for _ in range(4)]
    assert model['metadata']['examples'] == model['metadata']['fit_classification_mistakes'] == 0
    assert model['work']['active_leaves'] == 4


def test_fitting_prefixes_is_isolated_and_input_order_does_not_change_trees():
    prefix = examples(0, 'DOWN')
    complete = prefix+examples(12, 'LEFT')
    full = fit(complete)
    before = deepcopy(full)
    early = fit(prefix)
    shuffled = fit(list(reversed(complete)))
    assert early['trees'][0][0][0] == -1 and full['trees'][0][0][0] == 0
    assert early['metadata']['examples'] == 8 and full['metadata']['examples'] == 16
    assert full == before and shuffled['trees'] == full['trees']
    assert complete == prefix+examples(12, 'LEFT')


def test_random_control_preserves_all_predicates_and_charges_each_uniform_draw():
    learned = fit(examples(0, 'DOWN')+examples(12, 'LEFT'))
    before = deepcopy(learned)
    randomized = core.randomize_programs(learned, 140)
    RANDOMS.append(randomized)
    assert learned == before
    assert randomized == core.randomize_programs(learned, 140)
    assert randomized['trees'] != core.randomize_programs(learned, 141)['trees']
    assert [[node[0] for node in tree] for tree in learned['trees']] == [
        [node[0] for node in tree] for tree in randomized['trees']]
    assert all(sorted(node[1:]) == [0, 1, 2, 3] for tree in randomized['trees'] for node in tree)
    assert randomized['work']['random_draws'] == 84
    assert randomized['work']['random_action_orders'] == 28
    assert 'fit_calls' not in randomized['work']


def test_rank_action_reads_are_frozen_and_fit_work_includes_all_input_examples():
    model = fit(examples(0, 'DOWN')+examples(12, 'LEFT'))
    restored = json.loads(json.dumps(model))
    before = deepcopy(restored)
    assert core.rank_actions([1]*4+[0]*12, 'DOWN', restored) == ('LEFT', 'DOWN', 'RIGHT', 'UP')
    assert restored == before
    assert model['work']['training_examples'] == model['work']['feature_calls'] == 16
    assert model['work']['feature_neighbor_pairs'] == 24*16
    assert model['work']['split_candidates'] == 14
    assert model['work']['split_predicate_reads'] == 14*16
    assert model['work']['stored_node_integers'] == 140
