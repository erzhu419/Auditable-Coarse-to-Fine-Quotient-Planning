"""Terminal selection, counterfactual twins, paid rosters, and conditional CI."""
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science import controlled_predictive_joint_feedback_generation_v169 as core


def program(first='DOWN', probe='LEFT', true=('DOWN', 'LEFT', 'RIGHT'), false=('RIGHT', 'LEFT', 'DOWN')):
    return dict(first_action=first, probe_action=probe, true_suffix=list(true), false_suffix=list(false))


def source_game(life, replica):
    board = [0]*16
    board[(life+replica) % 16] = 1
    initial = list(board)
    actions, choices, cells, ranks = [], [], [], []
    preferred = ('UP', 'LEFT', 'DOWN', 'RIGHT')
    for step in range(8):
        order = preferred[(step+replica) % 4:]+preferred[:(step+replica) % 4]
        for name in order:
            after, _, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(name))
            if legal:
                break
        choices.append(dict(afterstate=list(after)))
        actions.append(name)
        board = list(after)
        cell = next(index for index, rank in enumerate(board) if rank == 0)
        board[cell] = 1
        cells.append(cell)
        ranks.append(1)
    return dict(life=life, query='risk1', replica=replica, seed=100+life*10+replica,
                initial_board=initial, actions=actions, choices=choices,
                spawned_cells=cells, spawned_ranks=ranks, result=dict(status='CUTOFF'))


def test_source_exclusion_precedes_heldout_trace_and_rule_access():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
                           ((1, .9), (2, .1)), 'uniform')
    games = [source_game(life, replica) for life in range(4) for replica in range(4)]
    baseline = core.source_candidates(games, {life: rule for life in range(3)}, 3)
    hidden = [dict(life=3, query='risk1') if row['life'] == 3 else row for row in games]
    repeated = core.source_candidates(hidden, {life: rule for life in range(3)}, 3)
    assert repeated == baseline
    assert baseline['training_lives'] == [0, 1, 2] and len(baseline['source_games']) == 12
    assert baseline['counts']['source_state_reconstructions'] == 96
    assert baseline['counts']['fragment_windows'] == 60


def test_source_parent_metadata_is_stripped_and_missing_game_roster_stops(monkeypatch):
    source = dict(training_lives=[0, 1, 2], counts=dict(source_games=12),
                  source_games=[dict(life=life, replica=replica) for life in range(3) for replica in range(4)],
                  candidates=[dict(program('DOWN'), candidate_id='P0', occurrences=10,
                                   condition_counts=dict(true=5, false=5), fixed_suffix=['UP']*3),
                              dict(program('UP'), candidate_id='P1', occurrences=9,
                                   condition_counts=dict(true=4, false=5), fixed_suffix=['LEFT']*3)])
    monkeypatch.setattr(core, 'generate_candidates', lambda *args, **kwargs: deepcopy(source))
    seeded = core.source_candidates([], {}, 3)
    assert seeded['complete'] and seeded['parents'] == [program('DOWN'), program('UP')]
    source['source_games'].pop()
    assert 'source_game_roster' in core.source_candidates([], {}, 3)['issues']
    source['candidates'].pop()
    assert 'source_program_pool' in core.source_candidates([], {}, 3)['issues']


def test_mutation_retains_duplicate_physical_slots_and_changes_condition_and_suffix_genes():
    parents = [program('DOWN'), program('LEFT')]
    before = deepcopy(parents)
    slots = core.mutate(parents)
    assert len(slots) == 50 and [row['candidate_slot'] for row in slots] == list(range(50))
    assert slots[1]['program'] == slots[2]['program'] == parents[1]
    assert slots[5]['program']['probe_action'] == 'DOWN'
    assert slots[8]['program']['true_suffix'] == ['LEFT', 'LEFT', 'RIGHT']
    assert slots[17]['program']['false_suffix'] == ['DOWN', 'LEFT', 'DOWN']
    assert len({core.program_key(row['program']) for row in slots}) < 50
    assert parents == before


def test_forced_twin_keeps_first_probe_and_independent_copies():
    candidate = program()
    a, b = core.executable(candidate, 'A'), core.executable(candidate, 'B')
    assert a['true_suffix'] == a['false_suffix'] == candidate['true_suffix']
    assert b['true_suffix'] == b['false_suffix'] == candidate['false_suffix']
    assert a['first_action'] == b['first_action'] == candidate['first_action']
    assert a['probe_action'] == b['probe_action'] == candidate['probe_action']
    b['true_suffix'][0] = 'UP'
    assert b['false_suffix'] == candidate['false_suffix'] and candidate == program()


def selection_fixture(phase='G1', resolver=None, predicate=None, parents=None):
    parents = parents or [program('DOWN'), program('UP')]
    slots = [dict(candidate_slot=index, program=deepcopy(candidate)) for index, candidate in enumerate(parents)] if phase == 'FINAL' else core.mutate(parents)
    cells = [dict(heldout_life=3, query='risk1', phase=phase,
                  parents=deepcopy(parents), slots=slots, complete=True, issues=[])]
    roots = [dict(root_id=f'TRAIN_SOURCE:{life}:{replica}:{slot}', phase='TRAIN_SOURCE',
                  life=life, query='risk1', replica=replica, slot=slot)
             for life in range(4) for replica in range(2) for slot in range(2)]
    predicate = predicate or (lambda root, suffix: root['slot'] == 0)
    resolver = resolver or (lambda root, suffix, candidate, arm, observed:
        [20. if candidate['candidate_slot'] == 2 else 5. if candidate['candidate_slot'] == 3 else 1., 1., 0.])
    rows = []
    for root in roots:
        if root['life'] == 3:
            continue
        for suffix in range(core.PHASE_SUFFIXES[phase]):
            seed = core.branch_seed(phase, root, suffix, 3)
            entries = [('H2', 'H2', None, None, [0., 1., 0.])]
            for candidate in slots:
                for arm in ('A', 'B'):
                    observed = predicate(root, suffix)
                    entries.append((arm, f'P{candidate["candidate_slot"]}_{arm}', candidate['candidate_slot'],
                                    candidate, resolver(root, suffix, candidate, arm, observed)))
            for route, mode, candidate_slot, candidate, vector in entries:
                rows.append(dict(heldout_life=3, phase=phase, root_id=root['root_id'], life=root['life'],
                    query='risk1', replica=root['replica'], slot=root['slot'], suffix=suffix, seed=seed,
                    route=route, mode=mode, candidate_slot=candidate_slot,
                    arm='H2' if route == 'H2' else 'FEEDBACK', score=vector[0]*2048., steps=10,
                    status='WON' if vector[2] else 'LOST', components=deepcopy(vector), utility=utility(vector, 'risk1'),
                    module=dict(program=None if candidate is None else core.executable(candidate['program'], route),
                                arm='H2' if route == 'H2' else 'FEEDBACK',
                                predicate=None if route == 'H2' else predicate(root, suffix))))
    return cells, roots, rows


def test_conditional_selection_uses_full_realized_vector_instead_of_reward_or_best_unconditional():
    def outcomes(root, suffix, candidate, arm, observed):
        if candidate['candidate_slot'] == 2:
            return [2., 0., 1.] if (arm == 'A') == observed else [2., 1., 0.]
        return [3., 1., 0.]
    selected = core.choose_parents(*selection_fixture(resolver=outcomes), 'G1')[0]
    winner = selected['slot_scores'][2]
    assert selected['complete'] and selected['selected_slots'][0] == 2
    assert winner['train_component_mean'] == [2., 0., 1.] and winner['train_gain'] == 4.
    assert winner['unconditional']['A']['component_mean'] == [2., .5, .5]
    assert winner['unconditional']['A']['utility'] == winner['unconditional']['B']['utility'] == 2.
    assert winner['predicate_counts'] == dict(true=6, false=6)


def test_equal_suffix_root_history_weighting_and_negative_winner_retention():
    cells, roots, rows = selection_fixture(resolver=lambda root, suffix, candidate, arm, observed:
        [3.*(root['life']+1)*(root['replica']*2+root['slot']+1) if candidate['candidate_slot'] == 2 else 0., 1., 0.])
    for row in rows:
        if row['mode'] == 'H2':
            row.update(score=100.*2048., components=[100., 1., 0.], utility=99.)
    selected = core.choose_parents(cells, roots, rows, 'G1')[0]
    winner = selected['slot_scores'][2]
    assert selected['complete'] and selected['selected_slots'][0] == 2
    assert winner['train_gain'] == -85.
    assert [row['gain'] for row in winner['per_history']] == [-92.5, -85., -77.5]


def test_duplicate_program_is_one_parent_and_lowest_original_slot_breaks_tie():
    parents = [program('DOWN'), program('LEFT')]
    selected = core.choose_parents(*selection_fixture(parents=parents,
        resolver=lambda root, suffix, candidate, arm, observed:
            [10. if candidate['program'] == parents[1] else 1., 1., 0.]), 'G1')[0]
    assert selected['selected_slots'][0] == 1
    assert len({core.program_key(candidate) for candidate in selected['selected_parents']}) == 2
    assert selected['slot_scores'][1]['train_utility'] == selected['slot_scores'][2]['train_utility']


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'cutoff', 'seed', 'metadata', 'predicate', 'unobserved', 'components', 'program'])
def test_bad_unselected_physical_trial_stops_without_extra_samples(failure):
    cells, roots, rows = selection_fixture()
    row = next(row for row in rows if row['mode'] == 'P49_B')
    if failure == 'missing':
        rows.remove(row)
    elif failure == 'duplicate':
        rows.append(deepcopy(row))
    elif failure == 'cutoff':
        row.update(status='CUTOFF', utility=None)
    elif failure == 'seed':
        row['seed'] += 1
    elif failure == 'metadata':
        row['candidate_slot'] = 0
    elif failure == 'predicate':
        row['module']['predicate'] = not row['module']['predicate']
    elif failure == 'unobserved':
        counterpart = next(other for other in rows if other['mode'] == 'P49_A' and other['root_id'] == row['root_id'])
        row['module']['predicate'] = counterpart['module']['predicate'] = None
        row.update(score=2.*2048., components=[2., 1., 0.], utility=1.)
    elif failure == 'components':
        row['status'] = 'WON'
    else:
        row['module']['program']['probe_action'] = 'UP'
    selected = core.choose_parents(cells, roots, rows, 'G1')[0]
    assert not selected['complete'] and selected['selected_parents'] == []
    assert len(selected['slot_scores']) == 50 and not selected['slot_scores'][49]['complete']


def test_single_predicate_support_and_unobserved_predicate_are_valid_no_replacements():
    for value in (True, False, None):
        selected = core.choose_parents(*selection_fixture(predicate=lambda root, suffix: value), 'G1')[0]
        assert selected['complete']
        assert selected['slot_scores'][2]['predicate_counts'] == {'true' if value is True else 'false' if value is False else 'unobserved': 12}


def test_final_freezes_best_unconditional_twin_of_selected_candidate_and_ties_A():
    def resolver(root, suffix, candidate, arm, observed):
        return [8. if candidate['candidate_slot'] == 1 and arm == 'B' else 6. if candidate['candidate_slot'] == 1 else 1., 1., 0.]
    selected = core.choose_parents(*selection_fixture('FINAL', resolver=resolver), 'FINAL')[0]
    assert selected['selected_slots'] == [1] and selected['selected_twin'] == 'B'
    assert selected['slot_scores'][1]['train_component_mean'] == [7., 1., 0.]
    tied = core.choose_parents(*selection_fixture('FINAL'), 'FINAL')[0]
    assert tied['selected_twin'] == 'A'


def test_phase_seed_streams_are_disjoint_and_candidate_arm_independent():
    root = dict(life=1, replica=1, slot=1)
    assert core.branch_seed('G1', root, 0, 2) == 16922101100
    assert core.branch_seed('G2', root, 0, 2) == 16932101100
    assert core.branch_seed('FINAL', root, 3, 2) == 16942101103
    assert core.branch_seed('EVAL', root, 15) == 16951001115


def eval_fixture():
    roots = [dict(root_id=f'EVAL_SOURCE:{life}:{replica}:{slot}', phase='EVAL_SOURCE',
                  life=life, query='risk1', replica=replica, slot=slot)
             for life in range(4) for replica in range(4) for slot in range(2)]
    rows = []
    candidate = program()
    for root in roots:
        factor = (root['life']+1)*(root['replica']*2+root['slot']+1)
        for suffix in range(16):
            for mode in core.MODES:
                observed = suffix % 2 == 0
                vector = [0., 1., 0.] if mode == 'H2' else [1., 1., 0.] if mode == 'TWIN' else [(2. if observed else 6.)*factor, 1., 0.]
                chosen = candidate['true_suffix'] if observed else candidate['false_suffix']
                rows.append(dict(root_id=root['root_id'], suffix=suffix, mode=mode, route=mode,
                    phase='EVAL', heldout_life=root['life'], life=root['life'], query='risk1',
                    replica=root['replica'], slot=root['slot'], candidate_slot=None,
                    arm='H2' if mode == 'H2' else 'FEEDBACK', seed=core.branch_seed('EVAL', root, suffix),
                    score=vector[0]*2048., steps=10, status='LOST', components=vector, utility=utility(vector, 'risk1'),
                    module=dict(program=None if mode == 'H2' else core.executable(candidate, 'A' if mode == 'TWIN' else None),
                        arm='H2' if mode == 'H2' else 'FEEDBACK', predicate=None if mode == 'H2' else observed,
                        actual_word=[] if mode == 'H2' else [candidate['first_action']]+(chosen if mode == 'COND' else candidate['true_suffix']),
                        prefix_steps=0 if mode == 'H2' else 4, attempts=0 if mode == 'H2' else 4,
                        exit_reason='baseline' if mode == 'H2' else 'budget')))
    return roots, rows


def test_eval_weights_all_fresh_roots_and_counts_actual_state_feedback_divergence():
    result = core.summarize_eval(*eval_fixture())
    stats = next(row for row in result['comparisons'] if row['contrast'] == 'COND-TWIN')['metrics']['utility']
    assert result['complete'] and stats['mean'] == 44.
    assert stats['mean_variance'] == pytest.approx(1.59375)
    assert stats['conditional_suffix_ci95'] == pytest.approx([44-1.96*sqrt(1.59375), 44+1.96*sqrt(1.59375)])
    assert result['feedback_diagnostics'] == dict(predicate_observed_branches=512, suffixes_differ_from_twin=256, roots_with_both_predicates=32)
    assert len(result['root_rows']) == 32 and result['logical_work']['contrast_component_vectors'] == 1536


@pytest.mark.parametrize('failure', ['cutoff', 'duplicate', 'unexpected', 'root_duplicate', 'twin_program', 'predicate'])
def test_eval_failure_keeps_fixed_roots_and_blocks_all_pooled_contrasts(failure):
    roots, rows = eval_fixture()
    row = next(row for row in rows if row['mode'] == 'COND')
    if failure == 'cutoff':
        row.update(status='CUTOFF', utility=None)
    elif failure == 'duplicate':
        rows.append(deepcopy(row))
    elif failure == 'unexpected':
        extra = deepcopy(row)
        extra['suffix'] = 16
        rows.append(extra)
    elif failure == 'root_duplicate':
        roots[-1] = deepcopy(roots[0])
    elif failure == 'twin_program':
        twin = next(row for row in rows if row['mode'] == 'TWIN')
        twin['module']['program']['probe_action'] = 'UP'
    else:
        row['module']['predicate'] = not row['module']['predicate']
    result = core.summarize_eval(roots, rows)
    assert not result['complete'] and len(result['root_rows']) == 32
    assert all(row['metrics']['utility']['mean'] is None for row in result['comparisons'])
