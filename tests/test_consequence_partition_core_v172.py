"""Pure witnesses for spatial information, contrast fitting and support."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_consequence_partition_v172 as core


def example(index, tails=None, legal=('DOWN', 'LEFT'), feature=0, immediate=None,
            life=0, source=None, second_feature=None):
    tails = tails or {action: [0., 1., 0.] for action in legal}
    immediate = immediate or {action: 0. for action in legal}
    board = [0]*16
    board[0], board[15] = feature, 2
    if second_feature is not None:
        board[1] = second_feature
    trials = [dict(suffix=suffix, seed=1000+index*10+suffix,
                   action_components={action: [tails[action][0]+immediate[action], *tails[action][1:]]
                                      for action in legal}) for suffix in range(4)]
    return dict(root_id=f'root:{index:03}', life=life, source_id=source or f'source:{index//4}',
                canonical_board=board, legal_actions=list(legal),
                immediate_rewards=dict(immediate), suffix_trials=trials)


def root(item, teacher='LEFT', immediate=None, legal=None):
    selected = list(legal or item['legal_actions'])
    return dict(life=item['life'], canonical_board=list(item['canonical_board']),
                legal_actions=selected, teacher_action=teacher,
                immediate_rewards=immediate or {action: item['immediate_rewards'].get(action, 0.) for action in selected})


def spatial_examples(single_source_children=False, duplicate_feature=False):
    result = []
    for index in range(16):
        side = int(index >= 8)
        preferred = 'DOWN' if not side else 'LEFT'
        tails = {action: [4., 0., 1.] if action == preferred else [0., 1., 0.]
                 for action in ('DOWN', 'LEFT')}
        source = f'source:side{side}' if single_source_children else None
        result.append(example(index, tails, feature=side, source=source,
                              second_feature=side if duplicate_feature else None))
    return result


def test_spatial_partition_separates_opposite_actions_with_complete_vector_contrasts():
    examples = spatial_examples()
    learned = core.fit_partition(examples, 0, 'PART_EARLY')
    unsplit = core.fit_partition(examples, 0, 'ONE_LATE')
    assert learned['nodes'][0]['cell'] == 0 and learned['nodes'][0]['threshold'] == 0
    assert len(learned['leaves']) == 2 and sum(leaf['loss'] for leaf in learned['leaves']) < 1e-20
    assert unsplit['leaves'][0]['loss'] > 0.
    first, second = (core.choose_action(learned, root(examples[index])) for index in (0, 8))
    assert first['canonical_action'] == 'DOWN' and second['canonical_action'] == 'LEFT'
    assert not first['fallback'] and not second['fallback']
    assert first['predicted_pairs']['DOWN|LEFT'] == pytest.approx([4., -1., 1.])
    assert second['predicted_pairs']['DOWN|LEFT'] == pytest.approx([-4., 1., -1.])


def test_pair_fitting_removes_legal_set_specific_common_offsets_instead_of_zero_labels():
    values = {'DOWN': [6., 0., 1.], 'LEFT': [2., 1., 0.], 'RIGHT': [0., 1., 0.]}
    examples = []
    for group, (legal, offset) in enumerate(((('DOWN', 'LEFT'), 100.),
                                            (('LEFT', 'RIGHT'), 200.),
                                            (('DOWN', 'RIGHT'), 0.))):
        tails = {action: [values[action][0]+offset, *values[action][1:]] for action in legal}
        examples.extend(example(4*group+index, tails, legal=legal) for index in range(4))
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    decision = core.choose_action(fitted, root(examples[0], legal=('DOWN', 'LEFT', 'RIGHT')))
    assert decision['canonical_action'] == 'DOWN' and not decision['fallback']
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([4., -1., 1.])
    assert decision['predicted_pairs']['DOWN|RIGHT'] == pytest.approx([6., -1., 1.])
    assert decision['predicted_pairs']['LEFT|RIGHT'] == pytest.approx([2., 0., 0.])
    assert decision['support']['action_root_counts'] == dict(DOWN=8, LEFT=8, RIGHT=8)
    assert fitted['leaves'][0]['action_root_ids']['UP'] == []
    for component in range(3):
        assert sum(fitted['leaves'][0]['coefficients'][action][component]
                   for action in ('DOWN', 'LEFT', 'RIGHT')) == pytest.approx(0., abs=1e-12)


def test_each_root_has_equal_total_pair_weight_when_legal_action_counts_vary():
    two = dict(DOWN=[2., 1., 0.], LEFT=[0., 1., 0.])
    three = {action: [0., 1., 0.] for action in ('DOWN', 'LEFT', 'RIGHT')}
    examples = [example(index, two) for index in range(4)]
    examples += [example(index, three, legal=('DOWN', 'LEFT', 'RIGHT')) for index in range(4, 8)]
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    decision = core.choose_action(fitted, root(examples[0], legal=('DOWN', 'LEFT', 'RIGHT')))
    # Eliminating RIGHT gives half the three-action-root weight to this contrast.
    assert decision['predicted_pairs']['DOWN|LEFT'][0] == pytest.approx(4./3.)
    for label in fitted['fit_labels']:
        assert sum(pair['weight'] for suffix in label['suffixes'] for pair in suffix['pairs']) == pytest.approx(1.)
    assert fitted['leaves'][0]['total_pair_weight'] == pytest.approx(8.)


def test_support_uses_distinct_roots_and_keeps_unsupported_teacher_decisions():
    examples = [example(index, dict(DOWN=[20., 0., 1.], LEFT=[0., 1., 0.])) for index in range(3)]
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    decision = core.choose_action(fitted, root(examples[0]))
    assert decision['canonical_action'] == 'LEFT' and decision['fallback']
    assert decision['reason'] == 'insufficient_action_support'
    assert decision['support']['action_root_counts'] == dict(DOWN=3, LEFT=3)
    assert decision['support']['pair_root_counts'] == {'DOWN|LEFT': 3}
    assert not decision['support']['complete']


def test_disconnected_comparisons_do_not_identify_an_action_across_relative_gauges():
    examples = [example(index) for index in range(4)]
    examples += [example(index, legal=('RIGHT', 'UP')) for index in range(4, 8)]
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    decision = core.choose_action(fitted, root(examples[0], teacher='UP', legal=core.ACTIONS))
    assert decision['fallback'] and decision['canonical_action'] == 'UP'
    assert decision['reason'] == 'disconnected_required_actions'
    assert set(decision['predicted_pairs']) == {'DOWN|LEFT', 'RIGHT|UP'}
    assert decision['support']['connected_components'] == [['DOWN', 'LEFT'], ['RIGHT', 'UP']]
    assert all(count == 4 for count in decision['support']['action_root_counts'].values())


def test_immediate_reward_is_removed_from_labels_and_added_from_the_current_root():
    tails, immediate = dict(DOWN=[2., 1., 0.], LEFT=[3., 1., 0.]), dict(DOWN=100., LEFT=0.)
    examples = [example(index, tails, immediate=immediate) for index in range(4)]
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    before = deepcopy(fitted)
    no_reward = core.choose_action(fitted, root(examples[0], immediate=dict(DOWN=0., LEFT=0.)))
    new_reward = core.choose_action(fitted, root(examples[0], immediate=dict(DOWN=2., LEFT=0.)))
    assert no_reward['canonical_action'] == 'LEFT' and new_reward['canonical_action'] == 'DOWN'
    assert no_reward['predicted_pairs']['DOWN|LEFT'] == pytest.approx([-1., 0., 0.])
    assert new_reward['predicted_pairs']['DOWN|LEFT'] == pytest.approx([1., 0., 0.])
    assert fitted['fit_labels'][0]['suffixes'][0]['pairs'][0]['components'] == [-1., 0., 0.]
    assert fitted == before


def test_source_siblings_cannot_alone_establish_a_spatial_split():
    examples = spatial_examples(single_source_children=True)
    fitted = core.fit_partition(examples, 0, 'PART_LATE')
    assert fitted['nodes'] == [dict(node_id=0, kind='leaf', leaf_id=0)]
    assert fitted['constants']['min_child_sources'] == 2
    assert len(fitted['leaves'][0]['root_ids']) == 16


def test_split_and_action_ties_are_deterministic_and_input_order_independent():
    examples = spatial_examples(duplicate_feature=True)
    first = core.fit_partition(examples, 0, 'PART_LATE')
    second = core.fit_partition(reversed(examples), 0, 'PART_LATE')
    assert first == second and first['nodes'][0]['cell'] == 0
    ties = [example(index, legal=core.ACTIONS) for index in range(4)]
    tied = core.fit_partition(ties, 0, 'ONE_LATE')
    decision = core.choose_action(tied, root(ties[0], teacher='UP'))
    assert decision['canonical_action'] == 'DOWN' and not decision['fallback']


def test_teacher_identity_is_bound_before_label_access_and_repeated_roots_are_rejected():
    examples = [example(index) for index in range(4)]
    fitted = core.fit_partition([dict(life=1), *examples], 0, 'ONE_LATE')
    assert fitted['root_ids'] == [item['root_id'] for item in examples]
    assert fitted['fit_counts']['other_life_examples_excluded'] == 1
    other = root(examples[0]); other['life'] = 1
    with pytest.raises(ValueError, match='same frozen teacher'):
        core.choose_action(fitted, other)
    with pytest.raises(ValueError, match='duplicate training root'):
        core.fit_partition([*examples, examples[0]], 0, 'ONE_LATE')


def test_coarse_unseen_state_falls_back_but_single_legal_action_remains_forced():
    examples = [example(index) for index in range(4)]
    fitted = core.fit_partition(examples, 0, 'COARSE_LATE')
    unseen = root(examples[0]); unseen['canonical_board'][0] = 10
    decision = core.choose_action(fitted, unseen)
    assert decision['fallback'] and decision['reason'] == 'missing_partition_leaf'
    only = deepcopy(unseen); only.update(legal_actions=['LEFT'], teacher_action='LEFT', immediate_rewards={'LEFT': 1.})
    forced = core.choose_action(fitted, only)
    assert forced['canonical_action'] == 'LEFT' and not forced['fallback']
    assert forced['reason'] == 'single_legal_action' and forced['support']['complete']
    assert forced['leaf'] is None


def test_decision_work_and_fit_provenance_preserve_all_suffix_labels_without_environment_calls():
    examples = [example(index) for index in range(4)]
    fitted = core.fit_partition(examples, 0, 'ONE_LATE')
    counts = Counter()
    decision = core.choose_action(fitted, root(examples[0]), counts)
    assert dict(counts) == decision['work']
    assert fitted['fit_counts']['label_component_reads'] == 4*4*2*3
    assert fitted['fit_counts']['paired_vector_labels'] == 4*4
    assert len(fitted['fit_labels']) == 4
    assert [trial['seed'] for trial in fitted['fit_labels'][0]['suffixes']] == [1000, 1001, 1002, 1003]
    assert not any('spawn' in key or 'sampled' in key or 'environment' in key
                   for key in (*fitted['fit_counts'], *decision['work']))



def test_retained_nonbinary_pair_weights_preserve_zero_sum_coordinates():
    """The V172 life0 early leaf3 normal equations produced a common offset."""
    import numpy as np
    from acfqp.science.controlled_predictive_consequence_partition_v172 import solve_centered_laplacian
    matrix = np.full((4, 4), -1.3333333333333335)
    np.fill_diagonal(matrix, 3.9999999999999942)
    rhs = np.asarray([
        [0.3369954427083332, -0.125, 0.125],
        [0.446044921875, -0.12499999999999997, 0.12499999999999997],
        [1.7533365885416667, -0.29166666666666663, 0.29166666666666663],
        [-2.5363769531249996, 0.5416666666666666, -0.5416666666666666],
    ])
    values = solve_centered_laplacian(matrix, rhs, [['DOWN', 'LEFT', 'RIGHT', 'UP']])
    assert np.allclose(values.sum(axis=0), 0., rtol=0., atol=1e-12)
    assert np.allclose(matrix @ values, rhs, rtol=0., atol=1e-12)
    assert values[0, 0] == pytest.approx(0.06318664550781244, abs=1e-12)

