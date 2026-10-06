"""Pure exact-kernel and learner counterexamples; no environment draws."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_exact_h3_v177 as core


def kernel(rational=False):
    cells = [[0, 0, 'CUTOFF'], [1, 0, 'LOST'], [2, 0, 'WON'],
             [3, 1, 'ACTIVE'], [4, 2, 'ACTIVE'], [5, 3, 'ACTIVE'],
             [6, 1, 'LOST'], [7, 2, 'WON']]
    raw = [[3, 'DOWN', [(Fraction(1), 0, Fraction(1))]],
           [3, 'LEFT', [(Fraction(1, 2), 1, Fraction(2)), (Fraction(1, 2), 2, Fraction(2))]],
           [4, 'DOWN', [(Fraction(1), 3, Fraction(1))]],
           [4, 'LEFT', [(Fraction(1), 6, Fraction(4))]],
           [5, 'DOWN', [(Fraction(1), 4, Fraction(0))]],
           [5, 'LEFT', [(Fraction(1), 7, Fraction(2))]]]
    rows = [[state, action, [[p.numerator, p.denominator, target, reward.numerator, reward.denominator]
        if rational else [float(p), target, float(reward)] for p, target, reward in outcomes]]
        for state, action, outcomes in raw]
    return dict(cells=cells, rows=rows, roots=[5], policy={'3': 'LEFT', '4': 'DOWN', '5': 'DOWN'})


def examples(kind='signal', missing_h2=True, duplicate_feature=False):
    rows = []
    for source in range(12):
        for index in range(4):
            ordinal = 4*source+index
            if missing_h2 and ordinal == 15:
                continue
            side = int(index >= 2)
            board = [0]*16
            board[0], board[15] = side, 2
            if duplicate_feature:
                board[1] = side
            legal, rewards = ['DOWN', 'LEFT'], dict(DOWN=0., LEFT=0.)
            if kind == 'same_action':
                tails = dict(DOWN=[10. if not side else 100., 1., 0.],
                             LEFT=[9. if not side else 90., 1., 0.])
            elif kind == 'reward_parameter':
                tails = dict(DOWN=[2., 1., 0.], LEFT=[3., 1., 0.])
                rewards['DOWN'] = 2. if side else 0.
            else:
                preferred = 'LEFT' if not side else 'DOWN'
                if kind == 'reversed_folds' and source % 2:
                    preferred = 'DOWN' if not side else 'LEFT'
                tails = {action: [0., 0., 1.] if action == preferred else [0., 1., 0.] for action in legal}
                if kind == 'unsupported' and source % 2 and not side:
                    legal.append('RIGHT')
                    rewards['RIGHT'], tails['RIGHT'] = 0., [10., 0., 0.]
            rows.append(dict(root_id=f'root:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{source:02d}',
                canonical_board=board, legal_actions=legal, immediate_rewards=rewards,
                action_components={action: [tails[action][0]+rewards[action], *tails[action][1:]] for action in legal},
                provenance=dict(original_source_ordinal=ordinal, horizon=3)))
    return rows


def candidate(payload):
    return next(row for row in payload['candidate_records']
                if row['node_id'] == 0 and row['cell'] == 0 and row['threshold'] == 0)


@pytest.mark.parametrize('rational', [False, True])
def test_exact_whole_vector_uses_one_policy_and_terminal_events_once(rational):
    data = kernel(rational)
    result = core.exact_action_labels(data['cells'], data['rows'], data['policy'], [5, 3, 0])
    root, one_step, cutoff = result['labels']
    assert root['action_components'] == dict(DOWN=[3., .5, .5], LEFT=[2., 0., 1.])
    assert root['continuation_components'] == [3., .5, .5]
    assert root['oracle_action'] == 'DOWN'  # Utility tie follows the frozen lexical rule.
    assert root['oracle_components'] == [3., .5, .5]
    assert root['oracle_components'] != [3., 0., 1.]  # Componentwise maxima are not a policy.
    assert root['action_component_fractions']['DOWN'] == [[3, 1], [1, 2], [1, 2]]
    assert one_step['action_components']['DOWN'] == [1., 0., 0.]
    assert cutoff['oracle_action'] is None and cutoff['oracle_components'] == [0., 0., 0.]
    assert result['counts']['teacher_states_evaluated'] == 3
    if rational:
        assert result['counts']['kernel_rational_outcomes_loaded'] == 7
        assert 'kernel_probability_recoveries' not in result['counts']
    else:
        assert result['counts']['kernel_probability_recoveries'] == 7
        assert result['counts']['kernel_reward_recoveries'] == 7


def test_native_rational_restoration_reports_actual_grid_error_and_rejects_non_native_atoms():
    counts = Counter()
    restored = core._restore_float(.9/7, True, counts)
    assert restored == Fraction(9, 70)
    assert counts['probability_grid_changed_atoms'] == 1
    assert 0. < counts['probability_grid_max_error'] < 1e-12
    assert core._restore_float(17/2048, False, counts) == Fraction(17, 2048)
    assert counts['reward_grid_changed_atoms'] == 0
    with pytest.raises(ValueError, match='native rational grid'):
        core._restore_float(.123456789, True, Counter())


def test_saved_policy_identity_controls_tail_and_payload_root_indices_keep_original_binding():
    data = kernel(True)
    data['roots'] = [3, 5]
    changed = dict(data['policy'], **{'3': 'DOWN'})
    expected = core.evaluate_payload(data, dict(policy=data['policy']), [1])
    actual = core.evaluate_payload(data, dict(policy=changed), [1])
    assert expected['labels'][0]['root_index'] == 1
    assert expected['labels'][0]['root_cell'] == 5
    assert actual['labels'][0]['action_components']['DOWN'] == [2., 0., 0.]
    assert expected['labels'][0]['action_components']['DOWN'] == [3., .5, .5]


def test_ground_root_transport_and_observable_fallback_do_not_access_labels():
    board = [1, 0, 0, 0]+[0]*12  # Exactly two legal physical actions.
    counts = Counter()
    root = core.root_from_case(dict(name='two_legal', board=board, horizon=3), 16, 'SOURCE', counts)
    assert len(root['legal_actions']) == 2
    assert set(root['action_map']) == set(root['legal_actions']) == set(root['immediate_rewards'])
    assert root['source_id'] == 'DESIGN_SOURCE:04'
    assert root['fallback_action'] == root['legal_actions'][0]
    assert root['teacher_action'] == root['fallback_action']
    for canonical, actual in root['action_map'].items():
        after, score, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(actual))
        canonical_after, canonical_score, canonical_legal = ground.swipe_board_v1(
            tuple(root['canonical_board']), ground.Swipe2048Action(canonical))
        assert legal and canonical_legal and score == canonical_score
        assert ground.transform_board_v1(after, D4Transform(root['frame'])) == canonical_after
        assert root['immediate_rewards'][canonical] == score/2048
    assert counts['root_ground_swipe_calls'] == 4 and counts['root_board_transforms'] == 8


def test_exact_adapter_keeps_47_roots_12_design_groups_and_single_pair_labels():
    rows = examples()
    prepared, folds = core._prepare_exact(rows, 0, counts := Counter())
    assert len(prepared) == 47 and len(folds[0]) == len(folds[1]) == 6
    assert [row['source_id'] for row in prepared].count('DESIGN_SOURCE:03') == 3
    assert counts['exact_action_vector_reads'] == 94 and counts['label_component_reads'] == 282
    assert counts['paired_vector_labels'] == 47 and 'suffix_trials_read' not in counts
    for item in prepared:
        assert len(item['observations']) == 1 and item['observations'][0][2] == 1.
        assert 'suffixes' not in item['fit_label'] and 'suffix_trials' not in item['training_outcome']
        assert item['training_outcome']['provenance']['horizon'] == 3
    fitted = core.fit_exact_partition(rows)
    assert fitted['nodes'][0]['kind'] == 'split'
    assert fitted['source_root_counts']['DESIGN_SOURCE:03'] == 3
    assert fitted['label_kind'] == 'exact_enumerated_vector' and 'suffixes' not in fitted['constants']
    selected = candidate(fitted)
    assert selected['selected'] and selected['comparable']
    source = next(row for direction in selected['directions'] for row in direction['source_effects']
                  if row['source_id'] == 'DESIGN_SOURCE:03')
    assert source['roots'] == 3 and source['in_region_roots'] == 3
    effects = next(direction for direction in selected['directions']
                   if any(row['source_id'] == source['source_id'] for row in direction['source_effects']))
    individual = [row['actual_difference_components'] for row in effects['root_decisions']
                  if row['source_id'] == source['source_id']]
    assert source['components'] == pytest.approx([sum(row[i] for row in individual)/3 for i in range(3)])


def test_exact_learner_uses_full_vector_utility_not_sse_capacity_or_same_root_refit_score():
    signal = core.fit_exact_partition(examples(missing_h2=False))
    row = candidate(signal)
    assert row['selected'] and row['score'] == pytest.approx(1.)
    assert row['directions'][0]['mean_components'] == pytest.approx([0., -.5, .5])
    unchanged = core.fit_exact_partition(examples('same_action', missing_h2=False))
    assert unchanged['nodes'] == [dict(node_id=0, kind='leaf', leaf_id=0)]
    assert candidate(unchanged)['score'] == 0.
    reversed_signal = core.fit_exact_partition(examples('reversed_folds', missing_h2=False))
    assert candidate(reversed_signal)['score'] == pytest.approx(-1.)
    assert reversed_signal['nodes'][0]['kind'] == 'leaf'


def test_unsupported_heldout_action_rejects_whole_candidate_without_immediate_fallback_in_training():
    fitted = core.fit_exact_partition(examples('unsupported', missing_h2=False))
    row = candidate(fitted)
    assert row['reason'] == 'unsupported_heldout_policy' and not row['comparable'] and row['score'] is None
    assert fitted['nodes'][0]['kind'] == 'leaf'
    assert all(direction['source_effects'] == [] for direction in row['directions'])


def test_immediate_reward_remains_an_observed_parameter_and_target_labels_never_change_choice():
    data = examples('reward_parameter', missing_h2=False)
    fitted = core.fit_exact_one(data)
    assert fitted['leaves'][0]['coefficients']['DOWN'] == pytest.approx([-.5, 0., 0.], abs=1e-12)
    decisions = []
    for raw in data[:4]:
        root = dict(raw, fallback_action='LEFT', teacher_action='DOWN', action_map=dict(DOWN='UP', LEFT='RIGHT'))
        before = core.choose_action(fitted, root)
        root['action_components'] = dict(DOWN=[1e9, 0., 1.], LEFT=[-1e9, 1., 0.])
        assert core.choose_action(fitted, root) == before
        decisions.append(before)
    assert [row['canonical_action'] for row in decisions] == ['LEFT', 'LEFT', 'DOWN', 'DOWN']
    assert [row['actual_action'] for row in decisions] == ['RIGHT', 'RIGHT', 'UP', 'UP']
    assert not any(row['fallback'] for row in decisions)


def test_unsupported_deployment_uses_only_immediate_reward_fallback_and_lexical_feature_ties():
    fitted = core.fit_exact_partition(examples(missing_h2=False, duplicate_feature=True))
    assert fitted['nodes'][0]['cell'] == 0 and fitted['nodes'][0]['threshold'] == 0
    root = deepcopy(examples(missing_h2=False)[0])
    root.update(legal_actions=['DOWN', 'LEFT', 'RIGHT'], fallback_action='RIGHT', teacher_action='LEFT',
                immediate_rewards=dict(DOWN=0., LEFT=0., RIGHT=5.))
    decision = core.choose_action(fitted, root)
    assert decision['fallback'] and decision['canonical_action'] == 'RIGHT'
    assert decision['reason'] == 'insufficient_action_support'
    root['legal_actions'], root['fallback_action'] = ['RIGHT'], 'RIGHT'
    forced = core.choose_action(fitted, root)
    assert not forced['fallback'] and forced['reason'] == 'single_legal_action'


def test_other_teacher_data_is_excluded_before_exact_label_access():
    class Unreadable(dict):
        def __getitem__(self, key):
            raise AssertionError('other-teacher label was read')
    rows = examples()
    rows.append(dict(root_id='other', source_id='other', life=1, action_components=Unreadable()))
    payload = core.fit_exact_one(rows, 0)
    assert len(payload['root_ids']) == 47 and payload['fit_counts']['other_life_examples_excluded'] == 1
