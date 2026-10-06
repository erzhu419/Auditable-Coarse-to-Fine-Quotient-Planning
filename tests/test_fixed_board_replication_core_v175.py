"""Zero-environment counterexamples for frozen choices and replication binding."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_fixed_board_replication_v175 as core


def leaf(leaf_id=0, preferred='LEFT'):
    return dict(leaf_id=leaf_id,
        action_root_ids={action: [f'fit:{i}' for i in range(4)] for action in core.ACTIONS},
        connected_components=[['DOWN', 'LEFT'], ['RIGHT'], ['UP']],
        coefficients={action: [2. if action == preferred else 0., 0., 0.] for action in core.ACTIONS})


def models():
    result = {}
    for life in core.LIVES:
        result[life] = dict(
            TREE=dict(life=life, mode='PART_UTILITY_UNPRUNED',
                      nodes=[dict(node_id=0, kind='leaf', leaf_id=0)], leaves=[leaf()]),
            ONE=dict(life=life, mode='ONE_LATE', groups={'ALL': 0}, leaves=[leaf(preferred='DOWN')]))
    return result


def root(cohort='TRAIN', life=0, source=0):
    return dict(cohort=cohort, root_id=f'{cohort}:{life}:{source}:root', life=life,
        source_id=f'{cohort}:{life}:source:{source}', canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.},
        reference_trials=[dict(suffix=suffix, seed=10000+life*1000+source*10+suffix,
            action_components={'DOWN': [10., 1., 0.], 'LEFT': [12.+source, 1., 0.]}) for suffix in range(4)])


def cohort_fixture(same=False):
    bank = models()
    if same:
        for life in core.LIVES:
            bank[life]['TREE']['leaves'][0] = leaf(preferred='DOWN')
    roots = [root(cohort, life, source) for cohort in core.COHORTS for life in core.LIVES
             for source in range(core.SOURCE_COUNTS[cohort])]
    frozen = core.freeze_selections(roots, bank)
    outcomes = []
    for ordinal, choice in enumerate(frozen['choices']):
        if not choice['changed']:
            continue
        source = int(choice['source_id'].rsplit(':', 1)[1])
        for suffix in range(core.SUFFIXES):
            for action in ('DOWN', 'LEFT'):
                outcomes.append(dict(cohort=choice['cohort'], root_id=choice['root_id'], life=choice['life'],
                    source_id=choice['source_id'], suffix=suffix, seed=200000+ordinal*100+suffix,
                    canonical_action=action, status='LOST',
                    components=[13.+source if action == 'LEFT' else 10., 1., 0.]))
    return roots, bank, frozen, outcomes


def test_selection_uses_current_tree_leaf_and_exact_reward_without_teacher_or_outcome_labels():
    bank, item = models(), root()
    bank[0]['TREE']['nodes'] = [dict(node_id=0, kind='split', cell=0, threshold=0, left=1, right=2),
                               dict(node_id=1, kind='leaf', leaf_id=1), dict(node_id=2, kind='leaf', leaf_id=2)]
    bank[0]['TREE']['leaves'] = [leaf(1, 'LEFT'), leaf(2, 'DOWN')]
    bank[0]['ONE']['leaves'][0]['coefficients']['DOWN'][0] = 5.
    before = deepcopy(bank)
    first = core.freeze_selections([item], bank)
    assert 'teacher_action' not in item
    assert first['choices'][0]['decisions']['TREE']['canonical_action'] == 'LEFT'
    item['canonical_board'][0] = 1
    second = core.freeze_selections([item], bank)
    assert second['choices'][0]['decisions']['TREE']['canonical_action'] == 'DOWN'
    item['immediate_rewards']['LEFT'] = 3.
    for trial in item['reference_trials']:
        trial['action_components']['DOWN'][0] = 10000.
    third = core.freeze_selections([item], bank)
    assert third['choices'][0]['decisions']['TREE']['canonical_action'] == 'LEFT'
    assert third['choices'][0]['old_difference_components'][0] < 0.
    assert bank == before
    assert third['work']['selection_decisions'] == 2
    assert third['work']['selection_coefficient_component_reads'] == 12


def test_full_vector_risk1_and_fixed_epsilon_ties_determine_actions():
    model, item = models()[0]['TREE'], root()
    model['leaves'][0]['coefficients'].update(DOWN=[4., 1., 0.], LEFT=[2., 0., 1.])
    tied = core.supported_action(model, item, Counter())
    assert tied['canonical_action'] == 'DOWN'  # Both utilities are three.
    model['leaves'][0]['coefficients']['LEFT'][0] += core.EPSILON/2
    assert core.supported_action(model, item, Counter())['canonical_action'] == 'DOWN'
    model['leaves'][0]['coefficients']['LEFT'][0] += 2*core.EPSILON
    assert core.supported_action(model, item, Counter())['canonical_action'] == 'LEFT'
    item['legal_actions'].reverse()
    assert core.supported_action(model, item, Counter())['canonical_action'] == 'LEFT'


def test_single_legal_action_requires_four_distinct_fit_roots_and_keeps_unsupported_root():
    bank, item = models(), root()
    item['legal_actions'] = ['DOWN']
    bank[0]['TREE']['leaves'][0]['action_root_ids']['DOWN'].pop()
    frozen = core.freeze_selections([item, root(source=1)], bank)
    assert not frozen['complete'] and len(frozen['choices']) == 2
    blocked = frozen['choices'][0]['decisions']['TREE']
    assert not blocked['support']['complete'] and blocked['canonical_action'] is None
    assert blocked['reason'] == 'insufficient_action_support'
    assert frozen['work'].get('reference_trials_read', 0) == 0


def test_disconnected_current_legal_actions_stop_without_fallback_or_dropping_roots():
    bank, item = models(), root()
    bank[0]['TREE']['leaves'][0]['connected_components'] = [[action] for action in core.ACTIONS]
    frozen = core.freeze_selections([item], bank)
    assert not frozen['complete'] and len(frozen['choices']) == 1
    decision = frozen['choices'][0]['decisions']['TREE']
    assert decision['reason'] == 'disconnected_required_actions'
    assert decision['canonical_action'] is None and not decision['support']['complete']
    item['life'] = 1
    with pytest.raises(ValueError, match='same frozen history'):
        core.supported_action(bank[0]['TREE'], item, Counter())


def test_same_actions_are_exact_zero_with_no_sampling_and_all_sources_retained():
    roots, _, frozen, outcomes = cohort_fixture(same=True)
    assert len(roots) == 80 and frozen['complete'] and outcomes == []
    summary = core.summarize_replication(frozen, outcomes)
    assert summary['complete'] and summary['physical_outcomes'] == summary['expected_physical_outcomes'] == 0
    assert summary['work']['same_action_roots_zeroed'] == len(roots)
    assert summary['work'].get('new_terminal_vector_reads', 0) == 0
    assert frozen['work'].get('reference_terminal_vector_reads', 0) == 0
    for cohort in core.COHORTS:
        for kind in ('new', 'old', 'new_minus_old'):
            comparison = summary['cohorts'][cohort][kind]
            for metric in core.METRICS:
                assert comparison['metrics'][metric]['mean'] == 0.
                assert comparison['metrics'][metric]['conditional_source_ci95'] == [0., 0.]
            assert all(history['source_clusters'] == core.SOURCE_COUNTS[cohort]
                       for history in comparison['per_history'])


def test_new_minus_old_is_source_paired_instead_of_adding_separate_variances():
    _, _, frozen, outcomes = cohort_fixture()
    summary = core.summarize_replication(frozen, outcomes)
    assert summary['complete']
    for cohort in core.COHORTS:
        stats = summary['cohorts'][cohort]
        assert stats['new']['metrics']['utility']['conditional_source_se'] > 0.
        assert stats['old']['metrics']['utility']['conditional_source_se'] > 0.
        paired = stats['new_minus_old']['metrics']['utility']
        assert paired['mean'] == 1. and paired['conditional_source_se'] == 0.
        assert paired['conditional_source_ci95'] == [1., 1.]
    assert summary['work']['new_terminal_vector_reads'] == len(outcomes)
    assert summary['work']['paired_suffix_seed_checks'] == len(frozen['choices'])*core.SUFFIXES


def test_replication_preserves_terminal_event_components_in_addition_to_reward():
    _, _, frozen, outcomes = cohort_fixture()
    for row in outcomes:
        row['components'] = [1., 0., 1.] if row['canonical_action'] == 'LEFT' else [4., 1., 0.]
        row['status'] = 'WON' if row['canonical_action'] == 'LEFT' else 'LOST'
    summary = core.summarize_replication(frozen, outcomes)
    assert summary['complete']
    for cohort in core.COHORTS:
        assert {metric: stat['mean'] for metric, stat in summary['cohorts'][cohort]['new']['metrics'].items()} == {
            'utility': -1., 'reward': -3., 'failure': -1., 'success': 1.}


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'cutoff', 'metadata', 'unpaired_seed',
                                 'reused_reference_seed', 'repeated_suffix_seed', 'terminal_event'])
def test_bad_replication_binding_stops_summary_instead_of_estimating_partial_cohort(fault):
    _, _, frozen, outcomes = cohort_fixture()
    if fault == 'missing':
        outcomes.pop()
    elif fault == 'duplicate':
        outcomes.append(deepcopy(outcomes[0]))
    elif fault == 'cutoff':
        outcomes[0]['status'] = 'CUT'
    elif fault == 'metadata':
        outcomes[0]['life'] = 1
    elif fault == 'unpaired_seed':
        outcomes[0]['seed'] += 1
    elif fault == 'reused_reference_seed':
        outcomes[0]['seed'] = outcomes[1]['seed'] = frozen['choices'][0]['reference_seeds'][0]
    elif fault == 'repeated_suffix_seed':
        outcomes[2]['seed'] = outcomes[3]['seed'] = outcomes[0]['seed']
    else:
        outcomes[0]['components'][1:] = [0., 1.]
    summary = core.summarize_replication(frozen, outcomes)
    assert not summary['complete'] and summary['issues']
    assert summary['cohorts'] == summary['cross_cohort'] == {}


def test_same_action_physical_rows_and_missing_source_cluster_are_not_silently_accepted():
    _, _, frozen, _ = cohort_fixture(same=True)
    choice = frozen['choices'][0]
    unexpected = dict(cohort=choice['cohort'], root_id=choice['root_id'], life=choice['life'], source_id=choice['source_id'],
                      suffix=0, seed=200000, canonical_action='DOWN', components=[10., 1., 0.], status='LOST')
    summary = core.summarize_replication(frozen, [unexpected])
    assert not summary['complete'] and any('unexpected_outcome' in issue for issue in summary['issues'])
    frozen['choices'].pop()
    missing = core.summarize_replication(frozen, [])
    assert not missing['complete'] and any('source_roster_mismatch' in issue for issue in missing['issues'])


def test_reference_trials_must_be_the_complete_frozen_four_suffixes():
    item = root()
    item['reference_trials'][3]['suffix'] = 2
    with pytest.raises(ValueError, match='four distinct frozen reference suffixes'):
        core.freeze_selections([item], models())
    with pytest.raises(ValueError, match='sixteen frozen replication suffixes'):
        core.summarize_replication(dict(choices=[], complete=True, issues=[]), [], suffixes=4)


def test_fixed_board_suffix_noise_is_zero_despite_positive_source_heterogeneity():
    _, _, frozen, outcomes = cohort_fixture()
    summary = core.summarize_replication(frozen, outcomes)
    assert summary['complete']
    for cohort in core.COHORTS:
        stat = summary['cohorts'][cohort]['new']['metrics']['utility']
        assert stat['conditional_source_se'] > 0.
        assert stat['conditional_suffix_mean_variance'] == stat['conditional_suffix_se'] == 0.
        assert stat['conditional_suffix_ci95'] == [stat['mean'], stat['mean']]


def test_paired_suffix_noise_uses_full_utility_squared_weights_and_fixed_old_reference():
    roots, bank, _, outcomes = cohort_fixture()
    first = roots[0]
    # OLD variability is part of the fixed observed reference, not fresh noise.
    for trial in first['reference_trials']:
        trial['action_components']['LEFT'][0] = 10.+100*(trial['suffix'] % 2)
    extra = deepcopy(first)
    extra['root_id'] += ':same-action'
    extra['immediate_rewards']['DOWN'] = 3.
    roots.append(extra)
    frozen = core.freeze_selections(roots, bank)
    assert not frozen['choices'][-1]['changed']
    for row in outcomes:
        if row['root_id'] == first['root_id'] and row['canonical_action'] == 'LEFT':
            if row['suffix'] < 8:
                row['components'], row['status'] = [11., 1., 0.], 'LOST'
            else:
                row['components'], row['status'] = [13., 0., 1.], 'WON'
    summary = core.summarize_replication(frozen, outcomes)
    assert summary['complete']
    train = summary['cohorts']['TRAIN']
    stat = train['new']['metrics']['utility']
    # Utility samples are 1 and 5: var(mean)=4/15 at the only noisy root.
    # Its SOURCE has two roots, then twelve SOURCEs, then four fixed histories.
    expected = (4/15)/(2**2 * 12**2 * 4**2)
    assert stat['conditional_suffix_mean_variance'] == pytest.approx(expected)
    assert stat['conditional_suffix_se']**2 == pytest.approx(expected)
    assert train['new']['per_history'][0]['metrics']['utility']['conditional_suffix_mean_variance'] == pytest.approx(1/2160)
    noisy_source = next(row for row in train['new']['clusters'] if row['source_id'] == first['source_id'])
    assert noisy_source['roots'] == 2
    assert noisy_source['conditional_suffix_mean_variance']['utility'] == pytest.approx(1/15)
    component_variances = [train['new']['metrics'][metric]['conditional_suffix_mean_variance']
                          for metric in ('reward', 'failure', 'success')]
    assert component_variances == pytest.approx([1/138240, 1/552960, 1/552960])
    assert sum(component_variances) != pytest.approx(expected)
    for metric in core.METRICS:
        assert train['old']['metrics'][metric]['conditional_suffix_mean_variance'] == 0.
        assert train['new_minus_old']['metrics'][metric]['conditional_suffix_mean_variance'] == pytest.approx(
            train['new']['metrics'][metric]['conditional_suffix_mean_variance'])
        assert summary['cross_cohort']['new']['metrics'][metric]['conditional_suffix_mean_variance'] == pytest.approx(
            train['new']['metrics'][metric]['conditional_suffix_mean_variance'])
