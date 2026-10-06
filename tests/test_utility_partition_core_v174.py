"""Pure counterexamples for action utility, fold isolation and strict support."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_utility_partition_v174 as core
from acfqp.science import controlled_predictive_consequence_partition_v172 as old


def examples(kind='signal', duplicate_feature=False):
    rows = []
    for source in range(12):
        for index in range(8):
            side = int(index >= 4)
            board = [0]*16; board[0], board[15] = side, 2
            if duplicate_feature:
                board[1] = side
            legal = ['DOWN', 'LEFT']
            rewards = dict(DOWN=0., LEFT=0.)
            if kind == 'sse_only':
                tails = dict(DOWN=[10. if not side else 100., 1., 0.],
                             LEFT=[9. if not side else 90., 1., 0.])
            elif kind == 'reward_parameter':
                tails = dict(DOWN=[2., 1., 0.], LEFT=[3., 1., 0.])
                rewards['DOWN'] = 2. if side else 0.
            else:
                preferred = 'LEFT' if not side else 'DOWN'
                if kind == 'reversed_folds' and source % 2:
                    preferred = 'DOWN' if not side else 'LEFT'
                tails = {action: [4., 1., 0.] if action == preferred else [0., 1., 0.] for action in legal}
                if kind == 'unsupported' and source % 2 and not side:
                    legal.append('RIGHT'); rewards['RIGHT'] = 0.; tails['RIGHT'] = [10., 1., 0.]
            rows.append(dict(root_id=f'root:{source:02}:{index}', life=0, source_id=f'source:{source:02}',
                canonical_board=board, legal_actions=legal, immediate_rewards=rewards,
                suffix_trials=[dict(suffix=suffix, seed=1000+source*100+index*10+suffix,
                    action_components={action: [tails[action][0]+rewards[action], *tails[action][1:]] for action in legal})
                    for suffix in range(4)]))
    return rows


def candidate(payload, cell=0, threshold=0):
    return next(row for row in payload['candidate_records']
                if row['node_id'] == 0 and row['cell'] == cell and row['threshold'] == threshold)


def test_source_crossfit_selects_repeatable_actual_utility_and_preserves_complete_vectors():
    data = examples()
    fitted = core.propose_partition(data, 0)
    selected = candidate(fitted)
    assert selected['comparable'] and selected['selected'] and selected['score'] == pytest.approx(2.)
    assert fitted['nodes'][0]['cell'] == 0 and fitted['nodes'][0]['threshold'] == 0
    assert fitted['source_folds'] == [[f'source:{i:02}' for i in range(0, 12, 2)],
                                     [f'source:{i:02}' for i in range(1, 12, 2)]]
    for direction in selected['directions']:
        assert len(direction['source_effects']) == 6
        assert direction['mean_components'] == pytest.approx([2., 0., 0.])
        assert direction['score'] == pytest.approx(2.)
        fit_sources = set(fitted['source_folds'][direction['fit_fold']])
        assert all(row['source_id'] not in fit_sources for row in direction['root_decisions'])
        assert all(row['parent']['support']['complete'] and row['child']['support']['complete']
                   for row in direction['root_decisions'])
    assert all('teacher_action' not in row for row in data)
    assert len(fitted['training_outcomes']) == 96 and len(fitted['training_outcomes'][0]['suffix_trials']) == 4


def test_sse_contrast_improvement_without_action_benefit_cannot_generate_a_split():
    data = examples('sse_only')
    sse = old.fit_partition(data, 0, 'PART_LATE')
    utility = core.propose_partition(data, 0)
    assert sse['nodes'][0]['kind'] == 'split'
    assert utility['nodes'] == [dict(node_id=0, kind='leaf', leaf_id=0)]
    row = candidate(utility)
    assert row['comparable'] and row['score'] == 0. and not row['selected']
    assert all(d['parent']['canonical_action'] == d['child']['canonical_action'] == 'DOWN'
               for direction in row['directions'] for d in direction['root_decisions'])


def test_opposite_source_folds_are_scored_on_the_other_fold_not_full_data_refits():
    fitted = core.propose_partition(examples('reversed_folds'), 0)
    row = candidate(fitted)
    assert row['score'] == pytest.approx(-2.)
    assert [direction['score'] for direction in row['directions']] == pytest.approx([-2., -2.])
    assert fitted['nodes'] == [dict(node_id=0, kind='leaf', leaf_id=0)]
    # Pooling both folds would erase their action ordering and conceal the loss.
    assert fitted['node_fits']['0']['coefficients']['DOWN'] == pytest.approx([0., 0., 0.], abs=1e-12)


def test_one_unsupported_heldout_action_disqualifies_the_whole_candidate():
    fitted = core.propose_partition(examples('unsupported'), 0)
    row = candidate(fitted)
    assert not row['comparable'] and row['score'] is None
    assert row['reason'] == 'unsupported_heldout_policy'
    assert any(not decision['complete'] for direction in row['directions'] for decision in direction['root_decisions'])
    assert all(direction['score'] is None and direction['source_effects'] == [] for direction in row['directions'])
    assert not any('actual_difference_components' in decision
                   for direction in row['directions'] for decision in direction['root_decisions'])
    assert fitted['nodes'][0]['kind'] == 'leaf'


def test_single_legal_action_still_requires_four_fit_roots_in_crossfit():
    fit = dict(action_root_ids={'DOWN': ['a', 'b', 'c']},
               connected_components=[['DOWN'], ['LEFT'], ['RIGHT'], ['UP']], coefficients={'DOWN': [0., 0., 0.]})
    item = dict(legal=['DOWN'], rewards={'DOWN': 1.})
    decision = core._action(fit, item, Counter())
    assert not decision['support']['complete'] and decision['canonical_action'] is None
    fit['action_root_ids']['DOWN'].append('d')
    supported = core._action(fit, item, Counter())
    assert supported['support']['complete'] and supported['canonical_action'] == 'DOWN'


def test_minimum_child_sources_applies_separately_inside_both_fit_folds():
    data = examples()
    for row in data:
        row['canonical_board'][0] = 0 if row['source_id'] in ('source:00', 'source:01') else 1
    fitted = core.propose_partition(data, 0)
    row = candidate(fitted)
    assert row['reason'] == 'insufficient_fit_child_sources' and row['score'] is None
    assert all(direction['fit_children']['left']['roots'] == 8 for direction in row['directions'])
    assert all(len(direction['fit_children']['left']['sources']) == 1 for direction in row['directions'])
    assert fitted['nodes'][0]['kind'] == 'leaf'


def test_current_immediate_reward_is_a_parameter_and_not_a_spurious_spatial_target():
    fitted = core.propose_partition(examples('reward_parameter'), 0)
    row = candidate(fitted)
    assert row['score'] == 0. and fitted['nodes'][0]['kind'] == 'leaf'
    for direction in row['directions']:
        for decision in direction['root_decisions']:
            expected = 'LEFT' if decision['side'] == 'left' else 'DOWN'
            assert decision['parent']['canonical_action'] == decision['child']['canonical_action'] == expected


def test_lexical_ties_input_order_and_final_full_discovery_refits_are_deterministic():
    data = examples(duplicate_feature=True)
    first = core.propose_partition(data, 0)
    second = core.propose_partition(reversed(data), 0)
    assert first == second and first['nodes'][0]['cell'] == 0
    assert candidate(first, 0)['selected'] and not candidate(first, 1)['selected']
    assert len(first['node_fits']['0']['root_ids']) == 96
    assert first['node_fits']['0']['action_root_ids']['DOWN'] == first['root_ids']
    assert first['node_fit_counts']['full_discovery_node_fits'] == len(first['nodes'])
    assert first['node_fit_counts']['leaf_fits'] == len(first['nodes'])
    assert len({row['candidate_id'] for row in first['candidate_records']}) == len(first['candidate_records'])
    assert sum(row['selected'] for row in first['candidate_records']) == sum(node['kind'] == 'split' for node in first['nodes'])
    assert first['fit_counts']['observed_terminal_component_reads'] == 96*4*2*3


def test_teacher_binding_and_four_suffix_completeness_do_not_consume_foreign_labels():
    data = examples()
    fitted = core.propose_partition([dict(life=1), *data], 0)
    assert fitted['fit_counts']['other_life_examples_excluded'] == 1
    assert all(row['life'] == 0 for row in fitted['training_outcomes'])
    broken = deepcopy(data); broken[0]['suffix_trials'].pop()
    with pytest.raises(ValueError, match='four complete fixed'):
        core.propose_partition(broken, 0)
