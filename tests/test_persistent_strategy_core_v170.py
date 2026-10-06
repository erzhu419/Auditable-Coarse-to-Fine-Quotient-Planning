"""Observed source induction, paid whole-game selection, and paired episodes."""
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science import controlled_predictive_persistent_strategy_v170 as core


def strategy(action='DOWN'):
    return dict(nodes=[dict(probe_action='LEFT', true_action=action, false_action='H2', true_next=1, false_next=0),
                       dict(probe_action='UP', true_action='RIGHT', false_action='H2', true_next=0, false_next=1)])


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
        actions.append(name); choices.append(dict(afterstate=list(after)))
        board = list(after)
        cell = next(index for index, rank in enumerate(board) if rank == 0)
        board[cell] = 1
        cells.append(cell); ranks.append(1)
    return dict(life=life, query='risk1', replica=replica, seed=100+life*10+replica,
                initial_board=initial, actions=actions, choices=choices,
                spawned_cells=cells, spawned_ranks=ranks, result=dict(status='CUTOFF'))


def test_source_uses_current_predecision_boards_and_excludes_heldout_before_access():
    learned = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
                              ((1, .9), (2, .1)), 'uniform')
    class RecordingRule:
        def __init__(self): self.calls = []
        def swipe(self, board, action, work):
            self.calls.append((tuple(board), action))
            return learned.swipe(board, action, work)
    rule = RecordingRule()
    games = [source_game(life, replica) for life in range(3) for replica in range(4)]+[dict(life=3, query='risk1')]
    seeded = core.source_candidates(games, {life: rule for life in range(3)}, 3)
    assert seeded['complete'] and seeded['training_lives'] == [0, 1, 2]
    assert seeded['counts']['decision_windows'] == seeded['counts']['source_state_reconstructions'] == 96
    assert seeded['counts']['probe_checks'] == seeded['counts']['learned_swipe_calls'] == 384
    assert seeded['counts']['board_transforms'] == 768 and seeded['counts']['action_transports'] == 96
    expected = []
    for row in games[:-1]:
        board = tuple(row['initial_board'])
        for choice, cell, rank in zip(row['choices'], row['spawned_cells'], row['spawned_ranks'], strict=True):
            canonical, _ = core.canonical_frame(board)
            expected.extend((canonical, probe) for probe in core.ACTIONS)
            board = list(choice['afterstate']); board[cell] = rank; board = tuple(board)
    assert rule.calls == expected
    assert all(row['occurrences'] == 96 for row in seeded['probe_tables'])
    assert seeded['probe_tables'] == sorted(seeded['probe_tables'], key=lambda row: (-row['source_match_score'], row['probe_action']))
    for index, node in enumerate(seeded['parents'][1]['nodes']):
        assert node['true_action'] == node['false_action'] == 'H2'
        assert node['true_next'] == 1-index and node['false_next'] == index


def test_empty_observed_condition_uses_H2_and_incomplete_source_roster_stops():
    class FalseProbe:
        def swipe(self, board, action, work):
            work['learned_swipe_calls'] += 1
            return tuple(board), 0, False
    games = [source_game(life, replica) for life in range(3) for replica in range(4)]
    seeded = core.source_candidates(games, {life: FalseProbe() for life in range(3)}, 3)
    assert seeded['complete'] and all(row['condition_counts']['true'] == 0 for row in seeded['probe_tables'])
    assert all(row['modal_actions']['true'] == 'H2' for row in seeded['probe_tables'])
    assert all(node['true_action'] == 'H2' for node in seeded['parents'][0]['nodes'])
    incomplete = core.source_candidates(games[:-1], {life: FalseProbe() for life in range(3)}, 3)
    assert not incomplete['complete'] and 'source_game_roster' in incomplete['issues']


def test_mutation_changes_all_graph_fields_and_preserves_duplicate_physical_slots():
    parents = [strategy('DOWN'), strategy('LEFT')]
    before = deepcopy(parents)
    slots = core.mutate(parents)
    assert len(slots) == 54 and [row['candidate_slot'] for row in slots] == list(range(54))
    assert slots[1]['program'] == slots[5]['program'] == parents[1]
    assert slots[2]['program']['nodes'][0]['probe_action'] == 'DOWN'
    assert slots[8]['program']['nodes'][0]['true_action'] == 'H2'
    assert slots[13]['program']['nodes'][0]['true_next'] == 0
    assert slots[14]['program']['nodes'][0]['false_next'] == 1
    assert len({core.program_key(slot['program']) for slot in slots}) < 54 and parents == before


def module(program, arm, steps=10):
    direct = 0 if arm == 'H2' else steps//2
    return dict(program=deepcopy(program), arm=arm, current_node=0,
                node_visits=[0, 0] if arm == 'H2' else [steps//2, steps-steps//2],
                latches=[None, None], last_predicates=[None, None],
                decisions=0 if arm == 'H2' else steps, direct_decisions=direct,
                h2_calls=steps-direct, explicit_h2_calls=0 if arm == 'H2' else steps-direct,
                illegal_fallbacks=0, live_predicate_changes=0 if arm == 'H2' else 2,
                latch_divergences=2 if arm == 'LATCHED' else 0,
                control_transitions=0 if arm == 'H2' else steps, node_switches=0 if arm == 'H2' else steps)


def selection_fixture(phase='G1', resolver=None, parents=None):
    parents = parents or [strategy('DOWN'), strategy('UP')]
    slots = [dict(candidate_slot=index, program=deepcopy(program)) for index, program in enumerate(parents)] if phase == 'FINAL' else core.mutate(parents)
    cells = [dict(heldout_life=3, query='risk1', phase=phase, parents=deepcopy(parents),
                  slots=slots, complete=True, issues=[])]
    resolver = resolver or (lambda life, episode, candidate, route:
        [20. if route == 'COND' and candidate['candidate_slot'] == 2 else 5. if route == 'COND' and candidate['candidate_slot'] == 3 else 1., 1., 0.])
    rows = []
    for life in range(3):
        for episode in range(core.PHASE_EPISODES[phase]):
            entries = [('H2', None, None, [0., 1., 0.])]
            entries += [(route, candidate['candidate_slot'], candidate['program'], resolver(life, episode, candidate, route))
                        for candidate in slots for route in ('COND', 'LATCHED')]
            for route, slot, program, vector in entries:
                rows.append(dict(phase=phase, life=life, heldout_life=3, episode=episode,
                    query='risk1', mode='H2' if route == 'H2' else f'P{slot}_{route}', route=route, arm=route,
                    candidate_slot=slot, seed=core.episode_seed(phase, life, episode, 3),
                    score=vector[0]*2048., steps=10, status='WON' if vector[2] else 'LOST',
                    components=deepcopy(vector), utility=utility(vector, 'risk1'), module=module(program, route)))
    return cells, rows


def test_selection_uses_physical_COND_wholegames_and_keeps_separate_LATCHED_vectors():
    selected = core.choose_parents(*selection_fixture(), 'G1')[0]
    winner = selected['slot_scores'][2]
    assert selected['complete'] and selected['selected_slots'] == [2, 3]
    assert winner['train_component_mean'] == [20., 1., 0.] and winner['train_gain'] == 20.
    assert winner['latched_component_mean'] == [1., 1., 0.] and winner['train_gain_vs_LATCHED'] == 19.
    assert selected['logical_work']['paired_terminal_episodes_examined'] == 54*3*2


def test_full_vector_weighting_retains_negative_winner_and_distinct_parent_tie():
    parents = [strategy('DOWN'), strategy('LEFT')]
    def resolver(life, episode, candidate, route):
        return [3.*(life+1)*(episode+1) if candidate['program'] == parents[1] else 0., 1., 0.]
    cells, rows = selection_fixture(parents=parents, resolver=resolver)
    for row in rows:
        if row['mode'] == 'H2':
            row.update(score=100.*2048., components=[100., 1., 0.], utility=99.)
    selected = core.choose_parents(cells, rows, 'G1')[0]
    assert selected['complete'] and selected['selected_slots'][0] == 1
    assert len({core.program_key(program) for program in selected['selected_parents']}) == 2
    assert selected['slot_scores'][1]['train_gain'] == -91.
    assert [row['gain'] for row in selected['slot_scores'][1]['per_history']] == [-95.5, -91., -86.5]


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'cutoff', 'seed', 'metadata', 'components', 'utility', 'program', 'unexpected'])
def test_any_unselected_trial_failure_blocks_fold_without_replacement(failure):
    cells, rows = selection_fixture()
    row = next(row for row in rows if row['mode'] == 'P53_LATCHED')
    if failure == 'missing': rows.remove(row)
    elif failure == 'duplicate': rows.append(deepcopy(row))
    elif failure == 'cutoff': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'metadata': row['candidate_slot'] = 0
    elif failure == 'components': row['status'] = 'WON'
    elif failure == 'utility': row['utility'] += 1
    elif failure == 'program': row['module']['program']['nodes'][0]['true_next'] ^= 1
    else:
        extra = deepcopy(row); extra['episode'] = 2; rows.append(extra)
    selected = core.choose_parents(cells, rows, 'G1')[0]
    assert not selected['complete'] and selected['selected_parents'] == []
    assert len(selected['slot_scores']) == 54 and not selected['slot_scores'][53]['complete']


def test_final_measures_four_games_per_source_history_and_freezes_one_program():
    selected = core.choose_parents(*selection_fixture('FINAL', resolver=lambda life, episode, candidate, route:
        [4. if candidate['candidate_slot'] == 1 and route == 'COND' else 1., 1., 0.]), 'FINAL')[0]
    assert selected['complete'] and selected['selected_slots'] == [1]
    assert selected['selected_parents'] == [strategy('UP')]
    assert selected['logical_work']['paired_terminal_episodes_examined'] == 24


def test_source_generation_final_and_eval_seed_streams_are_disjoint():
    assert core.episode_seed('SOURCE', 1, 3) == 17011000003
    assert core.episode_seed('G1', 1, 1, 2) == 17022100001
    assert core.episode_seed('G2', 1, 1, 2) == 17032100001
    assert core.episode_seed('FINAL', 1, 3, 2) == 17042100003
    assert core.episode_seed('EVAL', 1, 31) == 17051000031


def eval_fixture():
    rows = []
    program = strategy()
    for life in range(4):
        for episode in range(32):
            factor = life+1
            for mode in core.MODES:
                vector = [0., 1., 0.] if mode == 'H2' else [1., 1., 0.] if mode == 'LATCHED' else [(2. if episode % 2 == 0 else 6.)*factor, 1., 0.]
                rows.append(dict(phase='EVAL', life=life, heldout_life=life, episode=episode,
                    query='risk1', mode=mode, route=mode, arm=mode, candidate_slot=None,
                    seed=core.episode_seed('EVAL', life, episode), score=vector[0]*2048., steps=10,
                    status='LOST', components=vector, utility=utility(vector, 'risk1'),
                    module=module(None if mode == 'H2' else program, mode)))
    return rows


def test_eval_CI_uses_wholeepisode_pairs_and_aggregates_persistent_use():
    summary = core.summarize_eval(eval_fixture())
    stats = next(row for row in summary['comparisons'] if row['contrast'] == 'COND-LATCHED')['metrics']['utility']
    assert summary['complete'] and len(summary['episode_rows']) == 128
    assert stats['mean'] == 9.
    variance = sum(4.*(life+1)**2/31 for life in range(4))/16
    assert stats['mean_variance'] == pytest.approx(variance)
    assert stats['conditional_episode_ci95'] == pytest.approx([9-1.96*sqrt(variance), 9+1.96*sqrt(variance)])
    cond = next(row for row in summary['program_diagnostics'] if row['mode'] == 'COND')
    assert cond['module_counts']['decisions'] == cond['steps_sum'] == 1280
    assert cond['node_visits'] == [640, 640] and cond['episodes_with_repeated_node_visits'] == 128
    assert cond['direct_decision_fraction'] == cond['teacher_call_fraction'] == .5


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'cutoff', 'seed', 'paired_program', 'unexpected'])
def test_eval_keeps_every_wholegame_and_blocks_pooled_result_on_failure(failure):
    rows = eval_fixture()
    row = next(row for row in rows if row['mode'] == 'COND')
    if failure == 'missing': rows.remove(row)
    elif failure == 'duplicate': rows.append(deepcopy(row))
    elif failure == 'cutoff': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'paired_program': row['module']['program']['nodes'][0]['true_action'] = 'UP'
    else:
        extra = deepcopy(row); extra['episode'] = 32; rows.append(extra)
    summary = core.summarize_eval(rows)
    assert not summary['complete'] and len(summary['episode_rows']) == 128
    assert all(row['metrics']['utility']['mean'] is None for row in summary['comparisons'])
