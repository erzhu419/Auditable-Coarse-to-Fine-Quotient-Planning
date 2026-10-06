"""Pure full-frequency, mutation-roster, consequence-choice and CI fixtures."""
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science.controlled_predictive_consequence_generation_v168 import (
    branch_seed, choose_parents, final_selection, mutate, seed_parents, source_frequencies, summarize_eval)


def source_game(life, replica):
    board = [0]*16
    board[(life+replica) % 16] = 1
    initial = list(board)
    actions, choices, cells, ranks, scores = [], [], [], [], []
    preferred = ('UP', 'LEFT', 'DOWN', 'RIGHT')
    for step in range(8):
        order = preferred[(step+replica) % 4:]+preferred[:(step+replica) % 4]
        for name in order:
            after, score, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(name))
            if legal:
                break
        choices.append(dict(afterstate=list(after)))
        actions.append(name)
        board = list(after)
        cell = next(index for index, rank in enumerate(board) if rank == 0)
        board[cell] = 1
        cells.append(cell)
        ranks.append(1)
        scores.append(score)
    return dict(life=life, query='risk1', replica=replica, seed=100+life*10+replica,
        initial_board=initial, actions=actions, choices=choices, spawned_cells=cells, spawned_ranks=ranks,
        result=dict(status='CUTOFF', score=sum(scores), steps=8))


def test_source_frequency_uses_all_windows_and_excludes_heldout_before_trace_access():
    games = [source_game(life, replica) for life in range(4) for replica in range(4)]
    cell = source_frequencies(games, 0)
    assert cell['training_lives'] == [1, 2, 3] and len(cell['source_games']) == 12
    assert len(cell['source_frequencies']) == cell['counts']['unique_words']
    assert sum(row['frequency'] for row in cell['source_frequencies']) == cell['counts']['fragment_windows'] == 60
    assert cell['source_frequencies'] == sorted(cell['source_frequencies'], key=lambda row: (-row['frequency'], tuple(row['word'])))
    hidden = [dict(life=0, query='risk1') if row['life'] == 0 else row for row in games]
    repeated = source_frequencies(hidden, 0)
    assert repeated['source_frequencies'] == cell['source_frequencies'] and repeated['source_games'] == cell['source_games']


def test_seed_parents_keep_lexical_ties_and_incomplete_source_stops():
    a, b, c = ['DOWN']*4, ['LEFT']*4, ['UP']*4
    cell = dict(complete=True, source_frequencies=[dict(word=c, frequency=9), dict(word=b, frequency=9), dict(word=a, frequency=9)])
    assert seed_parents(cell) == [a, b]
    cell['complete'] = False
    assert seed_parents(cell) == []


def test_mutation_keeps_26_physical_slots_and_duplicate_words_in_frozen_order():
    parents = [['DOWN']*4, ['LEFT', 'DOWN', 'DOWN', 'DOWN']]
    before = deepcopy(parents)
    slots = mutate(parents)
    assert len(slots) == 26 and [row['candidate_slot'] for row in slots] == list(range(26))
    assert len({tuple(row['word']) for row in slots}) == 22
    assert slots[0]['word'] == parents[0] and slots[1]['word'] == slots[2]['word'] == parents[1]
    assert slots[3]['word'] == ['RIGHT', 'DOWN', 'DOWN', 'DOWN']
    assert slots[4]['word'] == ['UP', 'DOWN', 'DOWN', 'DOWN']
    assert parents == before


def selection_fixture(phase='G1', resolver=None, parents=None):
    parents = parents or [['DOWN']*4, ['UP']*4]
    slots = [dict(candidate_slot=index, word=deepcopy(word)) for index, word in enumerate(parents)] if phase == 'FINAL' else mutate(parents)
    frequency = [dict(word=deepcopy(parents[0]), frequency=100), dict(word=deepcopy(parents[1]), frequency=90)]
    cells = [dict(heldout_life=3, route=route, phase=phase, parents=deepcopy(parents), slots=deepcopy(slots),
                  source_frequencies=deepcopy(frequency), complete=True, issues=[]) for route in ('FREQ', 'CONS')]
    roots = [dict(root_id=f'TRAIN_SOURCE:{life}:{replica}:{slot}', phase='TRAIN_SOURCE',
        life=life, query='risk1', replica=replica, slot=slot)
        for life in range(4) for replica in range(2) for slot in range(2)]
    outcomes = []
    resolver = resolver or (lambda root, suffix, candidate: [20. if candidate['candidate_slot'] == 2 else 5. if candidate['candidate_slot'] == 3 else 1., 1., 0.])
    for root in roots:
        if root['life'] == 3: continue
        for suffix in range(4 if phase == 'FINAL' else 2):
            seed = branch_seed(phase, root, suffix, 3)
            entries = [('H2', 'H2', None, [0., 1., 0.])]+[(cell['route'], f'{cell["route"]}_W{slot["candidate_slot"]}', slot['candidate_slot'], resolver(root, suffix, slot))
                       for cell in cells for slot in cell['slots']]
            for route, mode, candidate_slot, vector in entries:
                outcomes.append(dict(heldout_life=3, phase=phase, root_id=root['root_id'], life=root['life'],
                    query='risk1', replica=root['replica'], slot=root['slot'], suffix=suffix, seed=seed,
                    route=route, mode=mode, candidate_slot=candidate_slot, score=vector[0]*2048., steps=10,
                    status='WON' if vector[2] else 'LOST', components=deepcopy(vector), utility=utility(vector, 'risk1')))
    return cells, roots, outcomes


def test_routes_use_terminal_consequences_or_full_source_frequency_on_same_slot_roster():
    cells, roots, rows = selection_fixture()
    freq, cons = choose_parents(cells, roots, rows, 'G1')
    assert freq['selected_slots'] == [0, 1] and freq['selection_basis'] == 'source_frequency'
    assert cons['selected_slots'] == [2, 3] and cons['selection_basis'] == 'terminal_utility'
    assert len(freq['slot_scores']) == len(cons['slot_scores']) == 26
    assert cons['slot_scores'][2]['train_component_delta_vs_H2'] == [20., 0., 0.]
    assert cons['logical_work']['paired_terminal_trials_examined'] == 26*12*2


def test_distinct_parent_selection_keeps_original_duplicate_slot_tie():
    parents = [['DOWN']*4, ['LEFT', 'DOWN', 'DOWN', 'DOWN']]
    cells, roots, rows = selection_fixture(parents=parents,
        resolver=lambda r, s, candidate: [10. if candidate['word'] == parents[1] else 1., 1., 0.])
    cons = choose_parents(cells, roots, rows, 'G1')[1]
    assert cons['selected_slots'][0] == 1
    assert len({tuple(word) for word in cons['selected_parents']}) == 2
    assert cons['slot_scores'][1]['train_gain'] == cons['slot_scores'][2]['train_gain']


def test_negative_winners_and_lexical_ties_are_retained():
    cells, roots, rows = selection_fixture(resolver=lambda r, s, c: [1., 1., 0.])
    for row in rows:
        if row['mode'] == 'H2': row.update(score=10.*2048., components=[10., 1., 0.], utility=9.)
    freq, cons = choose_parents(cells, roots, rows, 'G1')
    assert freq['complete'] and cons['complete']
    assert cons['selected_parents'] == [['DOWN']*4, ['DOWN', 'DOWN', 'DOWN', 'LEFT']]
    assert all(row['train_gain'] == -9. for row in cons['slot_scores'])


def test_terminal_parent_scores_use_equal_four_roots_and_three_histories():
    cells, roots, rows = selection_fixture(resolver=lambda r, s, c: [3.*(r['life']+1)*(r['replica']*2+r['slot']+1) if c['candidate_slot'] == 2 else 0., 1., 0.])
    cons = choose_parents(cells, roots, rows, 'G1')[1]
    assert cons['slot_scores'][2]['train_gain'] == 15.
    assert [row['gain'] for row in cons['slot_scores'][2]['per_history']] == [7.5, 15., 22.5]


def test_final_stage_uses_terminal_utility_for_both_routes():
    cells, roots, rows = selection_fixture('FINAL', resolver=lambda r, s, c: [20. if c['candidate_slot'] == 1 else 1., 1., 0.])
    selected = final_selection(cells, roots, rows)
    assert all(row['selection_basis'] == 'terminal_utility' and row['selected_slots'] == [1] for row in selected)
    assert all(row['selected_parents'] == [['UP']*4] for row in selected)


@pytest.mark.parametrize('failure', ['missing', 'cutoff', 'seed', 'utility', 'terminal', 'duplicate'])
def test_any_unselected_bad_slot_stops_route_without_replacement(failure):
    cells, roots, rows = selection_fixture()
    row = next(row for row in rows if row['mode'] == 'CONS_W25')
    if failure == 'missing': rows.remove(row)
    elif failure == 'cutoff': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'utility': row['utility'] += 1
    elif failure == 'terminal': row['status'] = 'WON'
    else: rows.append(deepcopy(row))
    freq, cons = choose_parents(cells, roots, rows, 'G1')
    assert freq['complete'] and not cons['complete'] and cons['selected_parents'] == []
    assert len(cons['slot_scores']) == 26 and not cons['slot_scores'][25]['complete']


def test_generation_streams_are_distinct_and_fixed_seed_formula_is_exact():
    root = dict(life=1, replica=1, slot=1)
    assert branch_seed('G1', root, 1, 2) == 16822101101
    assert branch_seed('G2', root, 1, 2) == 16832101101
    assert branch_seed('FINAL', root, 3, 2) == 16842101103
    assert branch_seed('EVAL', root, 15) == 16851001115


def eval_fixture():
    roots = [dict(root_id=f'EVAL_SOURCE:{life}:{replica}:{slot}', phase='EVAL_SOURCE',
        life=life, query='risk1', replica=replica, slot=slot)
        for life in range(4) for replica in range(4) for slot in range(2)]
    outcomes = []
    for root in roots:
        factor = (root['life']+1)*(root['replica']*2+root['slot']+1)
        for suffix in range(16):
            for mode in ('H2', 'FREQ', 'CONS'):
                vector = [0., 1., 0.] if mode == 'H2' else [1., 1., 0.] if mode == 'FREQ' else [(2. if suffix % 2 == 0 else 6.)*factor, 1., 0.]
                outcomes.append(dict(root_id=root['root_id'], suffix=suffix, mode=mode, phase='EVAL',
                    heldout_life=root['life'], life=root['life'], query='risk1', seed=branch_seed('EVAL', root, suffix),
                    score=vector[0]*2048., status='LOST', components=vector, utility=utility(vector, 'risk1'),
                    module=dict(prefix_steps=0 if mode == 'H2' else 4, attempts=0 if mode == 'H2' else 4,
                                exit_reason='baseline' if mode == 'H2' else 'budget')))
    return roots, outcomes


def test_fresh_eval_paired_CI_propagates_fixed_root_history_weights():
    result = summarize_eval(*eval_fixture())
    comparison = next(row for row in result['comparisons'] if row['contrast'] == 'CONS-FREQ')
    assert result['complete'] and comparison['metrics']['utility']['mean'] == 44.
    stats = comparison['metrics']['utility']
    assert stats['mean_variance'] == pytest.approx(1.59375)
    assert stats['conditional_suffix_ci95'] == pytest.approx([44-1.96*sqrt(1.59375), 44+1.96*sqrt(1.59375)])
    assert len(result['root_rows']) == 32 and result['logical_work']['contrast_component_vectors'] == 1536


def test_eval_cutoff_keeps_every_root_and_three_affected_contrasts_incomplete():
    roots, rows = eval_fixture()
    next(row for row in rows if row['mode'] == 'CONS').update(status='CUTOFF', utility=None)
    result = summarize_eval(roots, rows)
    assert len(result['root_rows']) == 32 and not result['complete']
    assert all(row['metrics']['utility']['mean'] is None for row in result['comparisons'])
    assert result['root_rows'][0]['pairs'][0]['outcomes']['CONS']['status'] == 'CUTOFF'
