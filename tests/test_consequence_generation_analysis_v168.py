"""Independent paid-vector selection, frequency metadata and fixed-weight CI."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_consequence_generation_v168 as audit
from acfqp.science import controlled_predictive_consequence_generation_v168 as core
from test_consequence_generation_core_v168 import source_game, selection_fixture


def test_all_frequency_metadata_matches_ground_source_generator():
    rows = [source_game(life, replica) for life in range(4) for replica in range(4)]
    source_results = []
    for life in range(4):
        words, games = Counter(), []
        for row in rows:
            if row['life'] != life: continue
            board, boards = list(row['initial_board']), []
            for step, choice in enumerate(row['choices']):
                boards.append(board)
                board = list(choice['afterstate'])
                board[row['spawned_cells'][step]] = row['spawned_ranks'][step]
            words.update(audit.canonical_counts(boards, row))
            games.append({k: row[k] for k in ('life', 'query', 'replica', 'seed')} |
                         {k: row['result'][k] for k in ('steps', 'status')})
        source_results.append(dict(life=life, word_counts=words, source_games=games))
    independent = audit.frequency_cells(source_results)
    for heldout in range(4):
        assert audit._equal(core.source_frequencies(rows, heldout), independent[heldout])
        counts = independent[heldout]['counts']
        assert counts['source_rows_examined'] == 16 and counts['source_games'] == 12
        assert counts['source_state_reconstructions'] == 96 and counts['fragment_windows'] == 60


def test_distinct_terminal_and_frequency_selection_and_fixed_ci():
    for phase in ('G1', 'FINAL'):
        cells, roots, rows = selection_fixture(phase)
        independent = audit.select_parents(cells, roots, rows)
        assert audit._equal(core.choose_parents(cells, roots, rows, phase), independent)
        assert all(len(cell['selected_parents']) == (1 if phase == 'FINAL' else 2) for cell in independent)
        assert all(len(set(map(tuple, cell['selected_parents']))) == len(cell['selected_parents']) for cell in independent)
    # Two scoring suffix differences [0,2] give root mean variance 1;
    # four fixed roots/history and four histories propagate it to 1/16.
    root = audit._moments([0., 2.])
    history = audit._pool([root]*4, 4)
    aggregate = audit._pool([history]*4, 4)
    assert aggregate['mean'] == 1 and aggregate['mean_variance'] == pytest.approx(1/16)
    assert aggregate['conditional_suffix_ci95'] == pytest.approx([.51, 1.49])


@pytest.mark.parametrize('corruption', ['seed', 'duplicate'])
def test_invalid_paid_pair_retains_every_slot_and_stops_selection(corruption):
    cells, roots, rows = selection_fixture()
    selected = next(row for row in rows if row['mode'].startswith('CONS_W'))
    if corruption == 'seed': selected['seed'] -= 100000000
    else: rows.append(deepcopy(selected))
    independent = audit.select_parents(cells, roots, rows)
    consequence = next(cell for cell in independent if cell['route'] == 'CONS')
    assert not consequence['complete'] and consequence['selected_parents'] == []
    assert len(consequence['slot_scores']) == 26
