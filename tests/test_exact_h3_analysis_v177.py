"""Independent exact vectors, learner reconstruction and finite-roster headroom."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

import pytest

from acfqp.science import controlled_predictive_exact_h3_v177 as core
from scripts import analyze_controlled_predictive_exact_h3_v177 as audit
from scripts import run_controlled_predictive_exact_h3_v177 as runner


def tiny_kernel(rational):
    cells = [[0, 0, 'CUTOFF'], [1, 0, 'LOST'], [2, 0, 'WON'],
             [3, 1, 'ACTIVE'], [4, 2, 'ACTIVE'], [5, 3, 'ACTIVE'], [6, 2, 'WON']]
    atoms = [(3, 'DOWN', [(Fraction(1), 0, Fraction(1))]),
             (3, 'LEFT', [(Fraction(1, 2), 1, Fraction(2)), (Fraction(1, 2), 2, Fraction(2))]),
             (4, 'DOWN', [(Fraction(1), 3, Fraction(1))]),
             (5, 'DOWN', [(Fraction(1), 4, Fraction(0))]),
             (5, 'LEFT', [(Fraction(1), 6, Fraction(0))])]
    rows = [[state, action, [[p.numerator, p.denominator, target, reward.numerator, reward.denominator]
        if rational else [float(p), target, float(reward)] for p, target, reward in outcomes]]
        for state, action, outcomes in atoms]
    return dict(cells=cells, rows=rows, roots=[5, 0]), dict(policy={'3': 'DOWN', '4': 'DOWN', '5': 'DOWN'})


@pytest.mark.parametrize('rational', [False, True])
def test_independent_DP_keeps_fixed_teacher_and_cutoff_semantics(rational):
    kernel, plan = tiny_kernel(rational)
    actual = audit.evaluate_payload(kernel, plan)
    expected = core.evaluate_payload(kernel, plan)
    assert audit._equal(actual, expected) and audit._equal(expected, actual)
    assert actual['labels'][0]['action_components']['DOWN'] == [2., 0., 0.]
    assert actual['labels'][1]['oracle_components'] == [0., 0., 0.]
    changed = audit.evaluate_payload(kernel, dict(policy=dict(plan['policy'], **{'3': 'LEFT'})))
    assert changed['labels'][0]['action_components']['DOWN'] == [3., .5, .5]
    assert actual['labels'][0]['action_component_fractions']['DOWN'] == [[2, 1], [0, 1], [0, 1]]
    assert actual['counts'] == expected['counts']


def exact_examples():
    rows = []
    for ordinal in range(48):
        if ordinal == 15:
            continue
        side = int(ordinal % 4 >= 2)
        rows.append(dict(root_id=f'r:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{ordinal//4:02d}',
            canonical_board=[side]+[0]*15, legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.},
            action_components={'DOWN': [0., float(not side), float(side)], 'LEFT': [0., float(side), float(not side)]},
            provenance={'kind': 'exact H3'}))
    return rows


def test_exact_pair_fit_candidates_and_node_counts_are_independent():
    examples = exact_examples(); before = deepcopy(examples)
    for mode, own, production in (('TREE', audit.fit_exact_partition, core.fit_exact_partition), ('ONE', audit.fit_exact_one, core.fit_exact_one)):
        expected = production(examples); actual = own(examples)
        assert audit._equal(actual, expected) and audit._equal(expected, actual), mode
        assert actual['source_root_counts']['DESIGN_SOURCE:03'] == 3
        assert actual['fit_counts']['paired_vector_labels'] == 47
        assert 'suffix_trials_read' not in actual['fit_counts']
        assert all('suffixes' not in row for row in actual['fit_labels'])
        root = dict(examples[0], fallback_action='DOWN', action_map={'DOWN': 'UP', 'LEFT': 'RIGHT'})
        decision, reference = audit.choose_action(actual, root), production_choice(expected, root)
        assert audit._equal(decision, reference) and audit._equal(reference, decision)
        root['action_components'] = {'DOWN': [1000., 0., 1.], 'LEFT': [-1000., 1., 0.]}
        changed_decision, changed_reference = audit.choose_action(actual, root), production_choice(expected, root)
        assert audit._equal(changed_decision, changed_reference) and audit._equal(changed_reference, changed_decision)
        assert changed_decision == decision and changed_reference == reference
    assert examples == before


def production_choice(model, root):
    return core.choose_action(model, root)


def test_observable_root_transport_cost_and_legal_map():
    case = dict(name='observed', horizon=3, board=[1, 0, 0, 0]+[0]*12)
    own_counts, core_counts = Counter(), Counter()
    actual = audit.root_from_case(case, 16, 'TARGET', own_counts)
    expected = core.root_from_case(case, 16, 'TARGET', core_counts)
    assert actual == expected and own_counts == core_counts
    assert len(actual['action_map']) == len(actual['legal_actions']) == 2
    assert actual['fallback_action'] == actual['legal_actions'][0]
    assert 'action_components' not in actual


def test_exact_headroom_uses_full_vectors_and_distinct_group_weights():
    roots, labels, choices = {}, {}, {}
    for cohort in ('SOURCE', 'TARGET'):
        roots[cohort] = [dict(root_id=f'{cohort}:{i}', source_id='large' if i < 2 else 'small', legal_actions=['DOWN', 'LEFT']) for i in range(3)]
        labels[cohort] = [dict(root_id=root['root_id'], action_components={'DOWN': [0., 1., 0.], 'LEFT': [0., 0., 1.]} if i < 2 else {'DOWN': [0., 0., 0.], 'LEFT': [0., 0., 0.]}) for i, root in enumerate(roots[cohort])]
        choices[cohort] = [dict(root_id=root['root_id'], mode=mode, canonical_action='LEFT' if mode == 'TREE' else 'DOWN', fallback=False) for root in roots[cohort] for mode in ('TREE', 'ONE', 'FALLBACK')]
    models = {'TREE': dict(nodes=[dict(kind='leaf')], candidate_records=[])}
    summary = audit.summarize(roots, labels, choices, models)
    assert audit._equal(summary, runner.summarize(roots, labels, choices, models))
    source = summary['cohorts']['SOURCE']
    assert source['aggregates']['ROOT_MEAN']['headroom'] == pytest.approx(4/3)
    assert source['aggregates']['DESIGN_GROUP_MEAN']['headroom'] == pytest.approx(1.)
    assert source['aggregates']['DESIGN_GROUP_MEAN']['headroom_closed_fraction'] == pytest.approx(1.)
    assert source['diagnostics']['oracle_action_disagreements']['TREE'] == 1
    assert source['diagnostics']['positive_regret_roots']['TREE'] == 0
    for rows in labels.values():
        for row in rows:
            row['action_components']['LEFT'] = list(row['action_components']['DOWN'])
    uninformative = audit.summarize(roots, labels, choices, models)
    assert uninformative['cohorts']['TARGET']['aggregates']['ROOT_MEAN']['headroom_closed_fraction'] is None


def test_native_binary_grid_recovery_records_nonzero_rational_error():
    kernel, plan = tiny_kernel(False)
    kernel['rows'][1][2] = [[.9/7, 1, 2.], [1-.9/7, 2, 2.]]
    actual = audit.evaluate_payload(kernel, plan)
    expected = core.evaluate_payload(kernel, plan)
    assert actual['counts'] == expected['counts']
    assert actual['counts']['probability_grid_changed_atoms'] == 2
    assert 0. < actual['counts']['probability_grid_max_error'] < 1e-12
    assert actual['labels'][0]['action_component_fractions'] == expected['labels'][0]['action_component_fractions']
