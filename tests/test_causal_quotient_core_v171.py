"""Causal rows, same-teacher boundaries and complete-vector Bellman witnesses."""
from collections import Counter
from copy import deepcopy

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_causal_quotient_v171 as core

S0, S1, S2 = 'A:0:2:1', 'A:1:2:1', 'A:2:2:1'


def edge(state, reward, count=8):
    terminal = state in ('WON', 'LOST')
    return dict(next_state=state, status=state if terminal else 'ACTIVE', count=count,
                reward_sum=reward*count, reward_mean=reward,
                failure=float(state == 'LOST'), success=float(state == 'WON'))


def row(state, action, outcomes):
    return dict(state=state, action=action, count=sum(item['count'] for item in outcomes), outcomes=outcomes)


def payload(rows=(), tails=None, life=0):
    tails = tails or {S0: [0., 0., 0.], S1: [1., 0., 0.]}
    return dict(schema='acfqp.causal_quotient.v171.model', life=life, rows=deepcopy(list(rows)),
                tails=[dict(state=state, count=1, component_sum=list(vector), component_mean=list(vector))
                       for state, vector in sorted(tails.items())], counts={})


def test_quotient_retains_compressed_merge_capacity_and_goal_precedence():
    no_merge = (1, 2, 3, 4, 2, 3, 4, 1, 3, 4, 1, 2, 4, 1, 2, 3)
    assert core.state_key(no_merge) == 'LOST'
    assert core.state_key((11,)+no_merge[1:]) == 'WON'
    for maximum, group in ((8, 0), (9, 1), (10, 2)):
        board = (maximum, 0, 1, 1)+(0,)*12
        assert core.state_key(board) == f'A:{group}:2:1'
    # Equal tiles separated by zero can merge after compression.
    board = (2, 0, 2)+(0,)*13
    counts = Counter()
    assert core.state_key(board, counts) == 'A:0:2:1'
    assert counts['quotient_state_tile_reads'] == 48 and counts['quotient_merge_line_checks'] == 8


def test_depth_three_changes_action_using_a_single_complete_continuation_vector():
    model = core.compile_model(payload([
        row(S0, 'DOWN', [edge('LOST', 3.)]),
        row(S0, 'LEFT', [edge(S1, 0.)]),
        row(S1, 'UP', [edge('WON', 4.)]),
    ]))
    values1 = {item['state']: item for item in model.tables['depths']['1']['values']}
    values3 = {item['state']: item for item in model.tables['depths']['3']['values']}
    assert values1[S0]['chosen_action'] == 'DOWN' and values1[S0]['components'] == [3., 1., 0.]
    assert values3[S0]['chosen_action'] == 'LEFT' and values3[S0]['components'] == [4., 0., 1.]
    assert model.q(S0, 'LEFT', 1) == [1., 0., 0.]
    assert model.q(S0, 'LEFT', 3) == [4., 0., 1.]
    assert values3['WON']['components'] == values3['LOST']['components'] == [0., 0., 0.]


def test_component_maxima_and_success_recounting_are_not_continuation_policies():
    model = core.compile_model(payload([
        row(S0, 'UP', [edge(S1, 0.)]),
        row(S1, 'DOWN', [edge('LOST', 10.)]),
        row(S1, 'LEFT', [edge('WON', 9.)]),
    ]))
    assert model.q(S0, 'UP', 3) == [9., 0., 1.]
    assert model.q(S1, 'LEFT', 1) == model.q(S1, 'LEFT', 3) == [9., 0., 1.]
    assert model.q(S0, 'UP', 3) != [10., 0., 1.]


def test_support_threshold_missing_tail_and_early_same_teacher_boundary():
    supported = row(S0, 'LEFT', [edge(S1, 2.)])
    weak = row(S0, 'DOWN', [edge('WON', 99., count=7)])
    model = core.compile_model(payload([supported, weak], {S0: [0., 0., 0.], S1: [3., .25, .75]}))
    assert model.q(S0, 'DOWN', 1) is None
    assert model.q(S0, 'LEFT', 3) == [5., .25, .75]
    missing = core.compile_model(payload([supported, row(S1, 'UP', [edge('WON', 100.)])], {S0: [0., 0., 0.]}))
    assert missing.q(S0, 'LEFT', 1) is None and missing.q(S0, 'LEFT', 3) is None
    blocked = next(item for item in missing.tables['depths']['3']['actions'] if item['state'] == S0 and item['action'] == 'LEFT')
    assert blocked['issues'] == ['missing_teacher_tail']


def test_empirical_edge_weights_keep_full_reward_failure_success_mixture():
    model = core.compile_model(payload([row(S0, 'RIGHT', [edge('LOST', 2., 2), edge('WON', 6., 6)])]))
    assert model.q(S0, 'RIGHT', 1) == [5., .25, .75]
    assert model.q(S0, 'RIGHT', 3) == [5., .25, .75]


def trace(life=0, forced=False):
    board = [1, 0, 1]+[0]*13
    first, first_score, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action('LEFT'))
    assert legal
    spawned = list(first); cell0 = next(index for index, rank in enumerate(spawned) if rank == 0); spawned[cell0] = 1
    second, second_score, legal = ground.swipe_board_v1(tuple(spawned), ground.Swipe2048Action('DOWN'))
    assert legal
    cell1 = next(index for index, rank in enumerate(second) if rank == 0)
    return dict(life=life, query='risk1', initial_board=board, root_board=board,
                actions=['LEFT', 'DOWN'], choices=[dict(afterstate=list(first)), dict(afterstate=list(second))],
                scores=[first_score, second_score], spawned_cells=[cell0, cell1], spawned_ranks=[1, 1],
                result=dict(status='LOST'), forced=forced)


def test_fit_streams_preserve_teacher_identity_and_exclude_forced_first_tail():
    source, forced = trace(), trace(forced=True)
    hidden = dict(life=1, query='risk1')
    fitted = core.fit_model(iter([source, hidden]), iter([forced, hidden]), 0)
    assert fitted['life'] == 0
    assert sum(item['count'] for item in fitted['rows']) == 4
    assert sum(item['count'] for item in fitted['tails']) == 3
    assert fitted['counts']['source_transitions'] == fitted['counts']['train_transitions'] == 2
    assert fitted['counts']['teacher_tail_labels'] == 3
    only_forced = core.fit_model([], [forced], 0)
    expected_tail_state = core.state_key(tuple(forced['choices'][0]['afterstate'][:forced['spawned_cells'][0]]+
        [forced['spawned_ranks'][0]]+forced['choices'][0]['afterstate'][forced['spawned_cells'][0]+1:]))
    assert only_forced['tails'] == [dict(state=expected_tail_state, count=1,
        component_sum=[forced['scores'][1]/2048., 1., 0.], component_mean=[forced['scores'][1]/2048., 1., 0.])]
    assert len(only_forced['rows']) == 2


def test_compile_snapshot_load_and_lookup_do_not_change_frozen_model():
    compiled = core.compile_model(payload([row(S0, 'DOWN', [edge('LOST', 3.)])]))
    frozen = deepcopy((compiled.payload, compiled.tables, compiled.counts))
    loaded = core.load_compiled(compiled.payload, compiled.tables)
    value = loaded.q(S0, 'DOWN', 3)
    value[0] = -999.
    assert loaded.q(S0, 'DOWN', 3) == [3., 1., 0.]
    assert loaded.counts == {} and compiled.counts['action_rows_evaluated'] == 216
    assert (compiled.payload, compiled.tables, compiled.counts) == frozen
