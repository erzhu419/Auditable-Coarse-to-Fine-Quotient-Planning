"""Synthetic checks for certificates, bandwidth, histories and teacher metadata."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_nonlinear_relations_v192 as audit


def vector(value):
    return [float(value)]+[0.]*97


def root(name, features, rewards, components, source='s0', life=0):
    return dict(root_id=name, source_id=source, life=life, canonical_board=[0]*16,
        legal_actions=list(features), relation_features={a: vector(value) for a, value in features.items()},
        immediate_rewards=rewards, action_components=components, fallback_action=next(iter(features)),
        action_map={a: a for a in features})


def model():
    return dict(life=0, centers=[dict(root_id='train', source_id='s0', action='DOWN', features=vector(0))],
        coefficients=[[2., 1., 3.]], gamma=1., median_squared_distance=1.,
        action_root_ids={a: ['r0', 'r1', 'r2', 'r3'] for a in audit.ACTIONS},
        pair_root_ids={f'{a}|{b}': ['r0'] for index, a in enumerate(audit.ACTIONS) for b in audit.ACTIONS[index+1:]},
        connected_components=[list(audit.ACTIONS)])


def test_direct_shifted_system_certifies_saved_arrays_and_rejects_changed_prediction():
    H = np.array([[2., .1], [.1, 1.]])
    Y = np.array([[1., .2, .3], [-.5, .4, .1]])
    B = np.array([[1., -1., 0.], [0., 1., -1.]])
    independent_alpha = np.linalg.solve(H+3*.1*np.eye(2), Y)
    independent_coefficients = B.T@independent_alpha
    saved_alpha, saved_coefficients = independent_alpha.copy(), independent_coefficients.copy()
    saved_alpha[0, 0] += 1e-10; saved_coefficients[0, 0] += 1e-10
    work = Counter()
    certified_alpha, certified_coefficients = audit.certify_coefficients(H, Y, B, 3, .1, saved_alpha, saved_coefficients, work)
    assert np.array_equal(certified_alpha, saved_alpha) and np.array_equal(certified_coefficients, saved_coefficients)
    assert not np.array_equal(certified_alpha, independent_alpha)
    changed = saved_coefficients.copy(); changed[0, 0] += 1e-3
    with pytest.raises(ValueError, match='frozen direct-system tolerance'):
        audit.certify_coefficients(H, Y, B, 3, .1, saved_alpha, changed, work)
    assert work['independent_predictors_checked'] == 2 and work['independent_predictors_passed'] == 1


def test_training_bandwidth_pair_weights_full_tails_and_forced_root_normalization():
    first = root('a', dict(DOWN=0., LEFT=1., RIGHT=3.), dict(DOWN=.2, LEFT=.4, RIGHT=.8),
        dict(DOWN=[.3, .2, .3], LEFT=[.9, .3, .4], RIGHT=[1.6, .5, .9]), source='s0')
    forced = root('b', dict(DOWN=8.), dict(DOWN=.07), dict(DOWN=[.07, 0., 0.]), source='s2')
    heldout = root('c', dict(DOWN=1000.), dict(DOWN=0.), dict(DOWN=[999., 0., 1.]), source='s1')
    rows = [first, heldout, forced]
    train = [row for row in rows if row['source_id'] in ('s0', 's2')]
    design = audit.prepare_design(train)
    assert design['root_ids'] == ['a', 'b'] and len(design['roots']) == 2
    assert design['median_squared_distance'] == 17.
    assert design['center_shape'] == [4, 98] and design['shape'] == [3, 4]
    assert all(record['weight'] == 1/3 for record in design['pair_records'])
    assert np.allclose(design['Y'][0], np.sqrt(1/3)*np.array([-.4, -.1, -.1]))
    assert audit.prepare_design(rows)['median_squared_distance'] != 17.
    K, H, B, _ = audit.kernel_and_gram(design, 1.)
    assert np.allclose(H, B@K@B.T)
    assert design['work']['examples_fitted'] == 2 and len(design['fit_labels'][1]['pairs']) == 0


def test_full_RFS_scoring_adds_first_reward_once_and_preserves_support_fallback():
    observed = root('r', dict(DOWN=0., LEFT=0.), dict(DOWN=.2, LEFT=.5),
        dict(DOWN=[.1, .8, 0.], LEFT=[.1, 0., .9]))
    payload = model(); choice = audit.choose_action(payload, audit.observable(observed))
    assert choice['predicted_components']['DOWN'] == [2.2, 1., 3.]
    assert choice['predicted_components']['LEFT'] == [2.5, 1., 3.]
    assert choice['canonical_action'] == 'LEFT' and not choice['fallback']
    insufficient = deepcopy(payload); insufficient['action_root_ids']['LEFT'] = ['r0']
    choice = audit.choose_action(insufficient, audit.observable(observed))
    assert choice['fallback'] and choice['canonical_action'] == 'DOWN'
    assert choice['reason'] == 'insufficient_action_support'


def test_fresh_observer_metadata_and_fixed_seed_roster_do_not_create_source_split(monkeypatch):
    seeds, calls = [], []
    class Random:
        def __init__(self, seed):
            seeds.append(seed)
        def randint(self, first, last):
            return 1
        def sample(self, population, count):
            return population[:count]
    monkeypatch.setattr(audit.random, 'Random', Random)
    cases = audit.cohort_cases()
    assert seeds == list(range(1920200, 1920296)) and len(cases) == 96
    assert cases[-1]['name'] == 'v192_target_r03_23' and cases[-1]['vacancies'] == 2
    def observe(case, ordinal, cohort, work):
        calls.append(cohort); work['observed_roots'] += 1
        return dict(root_id=case['name'], source_id='overwritten', cohort=cohort, ordinal=ordinal)
    monkeypatch.setattr(audit.relation.exact, 'root_from_case', observe)
    observed, work = audit.observe_roots([cases[-1]])
    assert calls == ['FRESH'] and observed[0]['source_id'] == 'FRESH_REPLICA:03'
    assert observed[0]['cohort'] == 'FRESH' and 'split' not in observed[0]
    assert work == dict(observed_roots=1)


def test_summary_uses_actual_RFS_regret_and_source_diagnostic_with_all_controls():
    source = root('source', dict(DOWN=0., LEFT=0.), dict(DOWN=.2, LEFT=.5),
        dict(DOWN=[.1, .8, 0.], LEFT=[.1, 0., .9]))
    diagnostic = audit.source_diagnostics([source], model())
    target = dict(root_id='target', source_id='fresh', legal_actions=['DOWN', 'LEFT'], replica=0, stratum=0)
    choices = {name: [dict(root_id='target', canonical_action='LEFT' if name == 'NONLINEAR' else 'DOWN', fallback=False)]
        for name in (*audit.MODEL_NAMES, 'FALLBACK')}
    labels = [dict(root_id='target', action_components=source['action_components'])]
    selection = dict(selected_gamma=1., selected_lambda=.1, selected_utility=.7,
        candidates=[dict(gamma=1., lambda_value=.1, utility=.7)])
    fitted = dict(rank=2, median_squared_distance=17., root_mean_loss=.01)
    summary = audit.summarize(dict(SOURCE=[source], TARGET=[target]), labels, choices, selection, fitted, diagnostic)
    assert summary['SOURCE']['actual']['positive_regret_roots'] == 0
    assert summary['models']['NONLINEAR']['utility'] == pytest.approx(1.)
    assert summary['models']['LINEAR']['utility'] == pytest.approx(-.7)
    assert summary['comparisons']['NONLINEAR_MINUS_LINEAR']['utility'] == pytest.approx(1.7)
    assert summary['comparisons']['NONLINEAR_MINUS_LINEAR']['resolved_error_roots'] == 1
    assert len(summary['models']) == 11 and summary['headroom_closed_fraction'] == pytest.approx(1.)


def test_model_constructor_uses_native_teacher_query_and_horizon_constants():
    source = root('metadata', dict(DOWN=0., LEFT=1.), dict(DOWN=.2, LEFT=.5),
        dict(DOWN=[.3, 0., .1], LEFT=[.6, 0., .2]))
    design = audit.prepare_design([source])
    metadata = dict(gamma=1., eigenvalues=[1.], cutoff=1e-15, rank=1, minimum_eigenvalue=1., work={})
    fitted = dict(coefficients=[[1., 2., 3.], [-1., -2., -3.]], dual_coefficients=[[1., 2., 3.]],
        component_losses=[.1, 0., 0.], loss=.1, root_mean_loss=.1, rkhs_energy=.5, penalty=.05,
        objective=.15, residuals=[], counts={})
    actual = audit.model_from_fit(design, metadata, fitted, .1, [['s0'], ['s1']])
    assert actual['native_teacher_query'] == 'goal_1_risk_1' and actual['horizon'] == 3
    assert actual['query'] == 'risk1' and actual['constants']['columns'] == 98
