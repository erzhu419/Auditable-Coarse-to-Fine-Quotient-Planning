"""Scripted executor control flow; no random environment sampling or fitting."""
from collections import Counter
from copy import deepcopy

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_persistent_strategy_v170 as core

BOARDS = [
    (1, 2)+(0,)*14,
    (0, 1, 0, 2)+(0,)*12,
    (0,)*4+(1, 0, 2, 3)+(0,)*8,
    (0,)*8+(1, 2, 0, 3)+(0,)*4,
    (0,)*12+(1, 0, 2, 3),
    (0, 1, 2, 3)+(0,)*12,
]


def controller(first='DOWN', second='RIGHT', alternate=False):
    return dict(nodes=[dict(probe_action='LEFT', true_action=first, false_action=second,
                            true_next=1 if alternate else 0, false_next=1 if alternate else 0),
                       dict(probe_action='UP', true_action=second, false_action=first,
                            true_next=0, false_next=0)])


class Teacher:
    def __init__(self):
        self.counts, self.calls = Counter(choose_calls=9), []
    def choose(self, board, query):
        self.calls.append((tuple(board), deepcopy(query)))
        self.counts.update(choose_calls=1, value_predictions=4)
        return dict(action='UP', afterstate=list(board), score=0)


def episode(monkeypatch, program, arm, predicates, illegal=(), max_steps=None, terminal='LOST'):
    steps = len(predicates)
    spawn_calls, status_calls = [], []
    def spawn(board, rng, counts, p_four):
        index = len(spawn_calls)
        spawn_calls.append(tuple(board))
        # The executor receives predetermined observations, never rng.random().
        if index == 0:
            return (1,)+(0,)*15, 0, 1
        if index == 1:
            return BOARDS[0], 1, 2
        return BOARDS[index-1], index-2, 1
    def status(board, counts):
        index = len(status_calls)
        status_calls.append(tuple(board))
        counts['ground_state_status_calls'] += 1
        return terminal if index == steps else 'ACTIVE'
    def physical_swipe(board, action):
        return tuple(board), 0, True
    class Rule:
        def __init__(self): self.calls = []; self.by_board = Counter()
        def swipe(self, board, action, counts):
            step = BOARDS.index(tuple(board))
            probe = self.by_board[step] == 0
            self.by_board[step] += 1
            self.calls.append((step, probe, action))
            counts.update(learned_swipe_calls=1, learned_line_rewrites=4)
            return tuple(board), 4 if probe and predicates[step] else 0, True if probe else step not in illegal
    monkeypatch.setattr(core, '_spawn', spawn)
    monkeypatch.setattr(core, '_status', status)
    monkeypatch.setattr(core.ground, 'swipe_board_v1', physical_swipe)
    bank, rule = {query: Teacher() for query in core.QUERIES}, Rule()
    row = core.run_episode(bank, rule, 'risk1', program, arm, 17050123,
                           max_steps=steps if max_steps is None else max_steps)
    assert len(spawn_calls) == row['result']['steps']+2
    assert row['result']['environment_counts'].get('environment_random_draws', 0) == 0
    assert all(query == core.QUERIES['risk1'] for _, query in bank['risk1'].calls)
    assert bank['risk8'].calls == [] and row['result']['policy_counts_by_query']['risk8'] == {}
    return row, rule, bank


def test_persistent_current_frame_and_fresh_predicates_continue_beyond_four_decisions(monkeypatch):
    program = controller()
    row, rule, _ = episode(monkeypatch, program, 'COND', [True, False, True, False, True])
    assert row['result']['status'] == 'LOST' and row['result']['steps'] == 5
    assert row['module']['decisions'] == row['module']['direct_decisions'] == row['module']['control_transitions'] == 5
    assert row['module']['node_visits'] == [5, 0] and row['module']['h2_calls'] == 0
    assert row['module']['live_predicate_changes'] == 4 and row['module']['latches'] == [None, None]
    frames = set()
    for step, choice in enumerate(row['choices']):
        decision = choice['program_decision']
        canonical, transform = core.canonical_frame(BOARDS[step])
        frames.add(transform)
        inverse = core.INVERSE[D4Transform(transform)]
        leaf = 'DOWN' if step % 2 == 0 else 'RIGHT'
        expected_action = ground.transform_action_v1(ground.Swipe2048Action(leaf), inverse).value
        expected_probe = ground.transform_action_v1(ground.Swipe2048Action('LEFT'), inverse).value
        assert decision['canonical_board'] == list(canonical) and decision['transform'] == transform
        assert decision['probe_action'] == expected_probe and row['actions'][step] == expected_action
        assert decision['current_predicate'] is (step % 2 == 0)
        assert decision['used_predicate'] == decision['current_predicate']
        assert choice['phase'] == 'program' and choice['policy_key'] == 'PROGRAM'
    assert len(frames) > 1 and len(rule.calls) == 10
    work = row['result']['policy_counts']
    assert work['program_board_transforms'] == 40 and work['program_action_transports'] == 10
    assert work['program_probe_checks'] == 5 and work['program_action_checks'] == 5
    assert work['probe_learned_swipe_calls'] == work['program_learned_swipe_calls'] == 5


def test_latched_bits_control_both_leaf_and_edge_with_per_node_cache_and_episode_reset(monkeypatch):
    program = controller(alternate=True)
    program['nodes'][0]['false_next'] = 0
    program['nodes'][1]['false_next'] = 1
    latched, _, _ = episode(monkeypatch, program, 'LATCHED', [True, False, False, True, True])
    decisions = [choice['program_decision'] for choice in latched['choices']]
    assert [decision['node'] for decision in decisions] == [0, 1, 1, 1, 1]
    assert [decision['used_predicate'] for decision in decisions] == [True, False, False, False, False]
    assert latched['module']['latches'] == [True, False]
    assert latched['module']['latch_divergences'] == 2 and latched['module']['node_visits'] == [1, 4]
    assert latched['result']['policy_counts']['program_probe_checks'] == 5
    assert decisions[3]['current_predicate'] is True and decisions[3]['next_node'] == 1
    fresh, _, _ = episode(monkeypatch, program, 'COND', [True, False, False, True, True])
    assert [choice['program_decision']['node'] for choice in fresh['choices']] == [0, 1, 1, 1, 0]
    reset, _, _ = episode(monkeypatch, program, 'LATCHED', [False, True])
    assert reset['choices'][0]['program_decision']['node'] == 0
    assert reset['choices'][0]['program_decision']['latch_before'] is None
    assert reset['choices'][0]['program_decision']['used_predicate'] is False


def test_illegal_direct_fallback_is_one_step_and_graph_remains_active(monkeypatch):
    program = controller(alternate=True)
    row, _, bank = episode(monkeypatch, program, 'COND', [True, True, False], illegal=(0,))
    assert [choice['phase'] for choice in row['choices']] == ['teacher', 'program', 'program']
    assert [choice['program_decision']['node'] for choice in row['choices']] == [0, 1, 0]
    first = row['choices'][0]['program_decision']
    assert first['fallback'] and not first['actual_action_attempt']['legal'] and first['next_node'] == 1
    assert row['module']['illegal_fallbacks'] == row['module']['h2_calls'] == 1
    assert row['module']['explicit_h2_calls'] == 0 and row['module']['direct_decisions'] == 2
    assert len(bank['risk1'].calls) == 1
    assert row['result']['policy_counts']['forced_decisions'] == 1
    assert row['result']['policy_counts']['program_probe_checks'] == 3


def test_all_H2_graph_exact_actions_and_environment_match_baseline_with_added_observation_cost(monkeypatch):
    program = controller(alternate=True)
    for node in program['nodes']:
        node['true_action'] = node['false_action'] = 'H2'
    baseline, _, _ = episode(monkeypatch, None, 'H2', [True, False, True, False, True])
    graph, _, _ = episode(monkeypatch, program, 'COND', [True, False, True, False, True])
    for key in ('initial_board', 'initial_spawns', 'actions', 'spawned_cells', 'spawned_ranks', 'scores', 'final_board'):
        assert graph[key] == baseline[key]
    assert graph['result']['environment_counts'] == baseline['result']['environment_counts']
    assert graph['module']['h2_calls'] == graph['module']['explicit_h2_calls'] == 5
    assert graph['module']['direct_decisions'] == graph['module']['illegal_fallbacks'] == 0
    assert graph['module']['decisions'] == graph['module']['control_transitions'] == 5
    assert baseline['module']['decisions'] == 0 and baseline['module']['node_visits'] == [0, 0]
    assert baseline['module']['explicit_h2_calls'] == 0 and baseline['module']['current_node'] == 0
    assert graph['result']['policy_counts']['program_probe_checks'] == 5
    assert graph['result']['policy_counts']['program_action_transports'] == 5
    assert graph['result']['policy_counts_by_query'] == baseline['result']['policy_counts_by_query']
    assert graph['result']['program_setup_counts'] == baseline['result']['program_setup_counts'] == {}


def test_cutoff_preserves_incomplete_terminal_label_and_8192_cap_accepts_long_valid_limit(monkeypatch):
    row, _, _ = episode(monkeypatch, controller(), 'COND', [True, False, True], max_steps=2)
    assert row['result']['status'] == 'CUTOFF' and row['result']['utility'] is None
    assert row['result']['components'][1:] == [0., 0.] and row['module']['decisions'] == 2
    complete, _, _ = episode(monkeypatch, controller(), 'COND', [True, False, True], max_steps=8192)
    assert complete['result']['status'] == 'LOST' and complete['max_steps'] == 8192


def test_terminal_mass_bound_follows_from_goal_rank_capacity_and_observed_legal_swipes():
    active_mass_bound = 16*(1 << (ground.GOAL_RANK-1))
    assert active_mass_bound == 16384 and 4+2*8191 > active_mass_bound
    # Legal merges conserve tile mass; every allowed spawn adds at least two.
    for board in BOARDS:
        mass = sum((1 << rank) for rank in board if rank)
        for action in core.ACTIONS:
            after, _, legal = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            if legal:
                assert sum((1 << rank) for rank in after if rank) == mass
