from collections import Counter
from types import SimpleNamespace

from acfqp.science import controlled_predictive_relational_programs_v196 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import RewriteProgram


def rule(reward='output_value'):
    return SimpleNamespace(program=RewriteProgram(True, 'equal', 1, 'once', reward),
                           goal_rank=11)


def prefix(contract, *word):
    record = next(row for row in contract['words'] if row['actions'] == list(word))
    return contract['prefixes'][record['prefix_id']]


def test_two_parent_genealogy_survives_a_second_merge_without_same_step_cascade():
    contract = core.trace_afterstate([9, 9, 10, 0] + [0]*12, rule())
    first = prefix(contract, 'LEFT')
    second = prefix(contract, 'LEFT', 'LEFT')
    assert len(first['events']) == 1
    assert first['events'][0] == dict(id=16, left=0, right=1, left_rank=9, right_rank=9,
        rank=10, reward=1024, origins=[0, 1], step=1, line=0, cell=0)
    assert not first['goal']
    event = second['events'][0]
    assert (event['left'], event['right'], event['origins']) == (16, 2, [0, 1, 2])
    assert event['step'] == 2 and event['rank'] == 11
    assert second['goal_ids'] == [17]
    assert second['linked_goal'] and second['score'] == 1.5


def test_once_consumption_keeps_four_equal_inputs_as_two_children():
    contract = core.trace_afterstate([9]*4 + [0]*12, rule())
    first = prefix(contract, 'LEFT')
    assert [event['origins'] for event in first['events']] == [[0, 1], [2, 3]]
    assert [event['rank'] for event in first['events']] == [10, 10]
    second = prefix(contract, 'LEFT', 'LEFT')
    assert second['events'][0]['left'] == 16
    assert second['events'][0]['right'] == 17
    assert second['events'][0]['origins'] == [0, 1, 2, 3]
    assert second['linked_goal']


def test_shared_prefixes_pay_twenty_swipes_and_only_eighty_one_features():
    board = [1, 2, 0, 0, 0, 3, 0, 4, 0, 0, 0, 0, 0, 0, 5, 0]
    counts = Counter()
    contract = core.trace_afterstate(board, rule(), counts)
    assert counts['program_swipe_calls'] == 20
    assert counts['program_line_rewrites'] == 80
    assert len(contract['prefixes']) == 21 and len(contract['words']) == 20
    assert len(contract['values']) == len(core.VALUE_NAMES) == 81
    assert counts['program_feature_values_written'] == 81
    assert counts['program_dependency_edges'] == 2*counts['program_merges']
    assert all('board' not in row for row in contract['prefixes'])


def test_initial_and_early_goal_stop_without_fictitious_swipes():
    counts = Counter()
    contract = core.trace_afterstate([11] + [0]*15, rule(), counts)
    assert counts['program_swipe_calls'] == 0
    assert counts['program_stopped_prefix_reuses'] == 20
    assert all(row['valid'] and row['goal'] and not row['linked_goal'] and row['score'] == 0
               for row in contract['words'])
    contract = core.trace_afterstate([10, 10, 0, 0] + [0]*12, rule())
    for action in core.ACTIONS:
        node = prefix(contract, 'LEFT', action)
        assert not node['executed'] and node['valid'] and node['goal']
        assert node['events'] == [] and node['score'] == 1.
        assert not node['linked_goal']


def test_illegal_prefix_stops_and_retains_the_legal_partial_score():
    contract = core.trace_afterstate([9, 9, 0, 0] + [0]*12, rule())
    first = prefix(contract, 'LEFT')
    second = prefix(contract, 'LEFT', 'LEFT')
    assert first['valid'] and first['score'] == .5
    assert second['executed'] and not second['valid'] and second['score'] == .5
    board = [0]*12 + [1, 0, 0, 0]
    contract = core.trace_afterstate(board, rule())
    for action in core.ACTIONS:
        node = prefix(contract, 'LEFT', action)
        assert not node['executed'] and not node['valid'] and not node['goal']
        assert node['score'] == 0 and node['events'] == []


def test_word_condition_shares_translated_merge_structure_and_learned_reward():
    upper = core.trace_afterstate([9, 9, 10, 0] + [0]*12, rule('count'))
    lower = core.trace_afterstate([0]*4 + [9, 9, 10, 0] + [0]*8, rule('count'))
    names = ('valid', 'goal', 'linked_goal', 'score')
    left = prefix(upper, 'LEFT', 'LEFT')
    right = prefix(lower, 'LEFT', 'LEFT')
    assert [left[name] for name in names] == [right[name] for name in names]
    assert left['score'] == 2/2048.
    assert left['events'][0]['origins'] == [0, 1, 2]
    assert right['events'][0]['origins'] == [4, 5, 6]


def test_root_cache_reuses_paid_contract_and_never_requests_spawn_or_labels():
    def forbidden(*args, **kwargs):
        raise AssertionError('conditional program must not read a stochastic outcome')
    learned = rule()
    learned.successors_from_afterstate = forbidden
    learned.classify = forbidden
    root = dict(legal_actions=['LEFT'], raw_afterstates={'LEFT': [9, 9, 10, 0] + [0]*12})
    first = core.cache_roots([root], learned)
    saved = root['program_contracts']
    second = core.cache_roots([root], learned)
    assert first['program_contracts_built'] == first['program_cache_roots_built'] == 1
    assert second == {'program_cache_hits': 1}
    assert root['program_contracts'] is saved
