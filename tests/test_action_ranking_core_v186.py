"""Synthetic gradient, ranking semantics and frozen inference witnesses."""
from copy import deepcopy
from itertools import combinations
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import controlled_predictive_action_ranking_v186 as core


def layout(first=0., second=0., rank=0):
    board = [rank]*16
    tokens = [['cell', i, value] for i, value in enumerate(board)]
    tokens += [['horizontal', 4*r+c, board[4*r+c], board[4*r+c+1]] for r in range(4) for c in range(3)]
    tokens += [['vertical', 4*r+c, board[4*r+c], board[4*(r+1)+c]] for r in range(3) for c in range(4)]
    return dict(aggregate=[first, second, 0., 0., 0., 0.], tokens=tokens)


def examples():
    return [dict(root_id=f'synthetic:{i}', source_id=f'DESIGN_SOURCE:{i:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=layout(2.), LEFT=layout()),
        action_features=dict(DOWN=[2., 0., 0., 0., 0., 0.], LEFT=[0.]*6),
        action_components=dict(DOWN=[1., .1, .1], LEFT=[0., 0., 0.])) for i in range(4)]


def reference(rows):
    action_ids = {a: [row['root_id'] for row in rows if a in row['legal_actions']] for a in core.ACTIONS}
    pair_ids = {f'{a}|{b}': [row['root_id'] for row in rows if a in row['legal_actions'] and b in row['legal_actions']]
                for a, b in combinations(core.ACTIONS, 2)}
    return dict(life=0, root_ids=[row['root_id'] for row in rows],
        vocabulary=sorted(layout()['tokens'], key=tuple), action_root_ids=action_ids,
        pair_root_ids=pair_ids, connected_components=core.estimation._components(pair_ids))


def inference_model():
    model = reference(examples())
    model.update(mode='RANK', coefficients=[1.]+[0.]*45)
    return model


def test_loss_gradient_matches_finite_differences_for_active_and_satisfied_margins():
    rows = examples()
    for root in rows:
        root.update(legal_actions=['DOWN', 'LEFT', 'UP'],
            immediate_rewards=dict(DOWN=.25, LEFT=0., UP=.125),
            layout_features=dict(DOWN=layout(2., 1.), LEFT=layout(), UP=layout(1., 0.)),
            action_components=dict(DOWN=[1.25, .1, .1], LEFT=[0., 0., 0.], UP=[.625, 0., 0.]))
    design = core.prepare_ranking(rows, reference(rows))
    for first, second in ((.2, -.1), (.8, -.1)):
        beta = np.zeros(design['shape'][1]); beta[0], beta[1], beta[6] = first, second, .3
        _, gradient = core.loss_gradient(beta, design)
        for index in (0, 1, 6):
            plus, minus = beta.copy(), beta.copy()
            plus[index] += 1e-6; minus[index] -= 1e-6
            numerical = (core.loss_gradient(plus, design)[0]-core.loss_gradient(minus, design)[0])/2e-6
            assert gradient[index] == pytest.approx(numerical, abs=1e-8)


def test_one_dimensional_optimum_and_stationarity_gap_are_certified():
    rows = examples()
    result = core.fit_ranking(rows, reference(rows))
    coefficients, fit = result['model']['coefficients'], result['fit']
    # J=(1−2*beta)^2+.1*beta^2, minimizer beta=2/(4+.1).
    assert coefficients[0] == pytest.approx(20/41, abs=1e-9)
    assert coefficients[1:] == pytest.approx([0.]*45, abs=1e-12)
    assert fit['accepted'] and fit['gradient_inf'] <= 1e-7
    assert fit['objective_gap_upper_bound'] == pytest.approx(np.dot(fit['gradient'], fit['gradient'])/.4)
    assert fit['objective'] == pytest.approx(1/41, abs=1e-12)
    assert fit['costs']['ranking_optimizer_attempts'] == 1
    assert fit['costs']['ranking_loss_gradient_calls'] == fit['optimizer']['function_evaluations']+1
    assert fit['history'][0]['objective'] == 1.
    assert 'D' not in fit['design'] and 'targets' not in fit['design'] and 'weights' not in fit['design']


def test_ties_and_single_legal_roots_remain_in_denominator_and_rewards_are_offsets():
    rows = examples()
    rows[0]['immediate_rewards'] = dict(DOWN=.75, LEFT=.25)
    rows[1]['action_components'] = dict(DOWN=[.25, .1, .1], LEFT=[.25, 0., 0.])
    rows[2].update(legal_actions=['DOWN', 'LEFT', 'UP'],
        immediate_rewards=dict(DOWN=0., LEFT=0., UP=0.),
        layout_features=dict(DOWN=layout(2.), LEFT=layout(), UP=layout(1.)),
        action_components=dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.], UP=[.5, 0., 0.]))
    rows[3].update(legal_actions=['UP'], immediate_rewards=dict(UP=0.),
        layout_features=dict(UP=layout()), action_components=dict(UP=[0., 0., 0.]))
    design = core.prepare_ranking(rows, reference(rows))
    assert design['root_count'] == 4 and len(design['rows']) == 3
    assert design['rows'][0]['utility_gap'] == 1. and design['rows'][0]['immediate_reward_gap'] == .5
    assert design['rows'][0]['target'] == .5
    assert design['root_records'][1]['best_action'] == 'DOWN'
    assert design['root_records'][1]['tied_actions'] == ['DOWN', 'LEFT']
    assert design['root_records'][1]['loser_actions'] == []
    assert design['root_records'][3]['rows'] == []
    assert [row['weight'] for row in design['rows']] == [1., .5, .5]
    assert core.loss_gradient(np.zeros(design['shape'][1]), design)[0] == pytest.approx(.21875)


def test_preparation_uses_frozen_vocabulary_support_and_source_labels_without_swipes(monkeypatch):
    rows, ref = examples(), reference(examples())
    before = deepcopy(ref)
    for row in rows:
        row['oracle_action'] = row['teacher_action_native'] = 'LEFT'
    def forbidden(*args, **kwargs):
        raise AssertionError('ranking preparation recomputed an afterstate')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    design = core.prepare_ranking(rows+[dict(life=1, root_id='unread')], ref)
    assert ref == before and design['vocabulary'] == ref['vocabulary']
    assert design['action_root_ids'] == ref['action_root_ids']
    assert design['pair_root_ids'] == ref['pair_root_ids']
    assert all(row['best_action'] == 'DOWN' for row in design['root_records'])
    assert design['work']['ranking_other_life_excluded'] == 1
    assert 'layout_ground_swipe_calls' not in design['work']
    with pytest.raises(ValueError, match='match the frozen SOURCE'):
        core.prepare_ranking(rows[:-1], ref)


def test_scalar_observable_predictions_unknown_tokens_and_support_preserve_actions():
    model, current = inference_model(), deepcopy(examples()[0])
    current['layout_features']['DOWN'] = layout(1.)
    current['immediate_rewards']['LEFT'] = .25
    decision = core.choose_action(model, current)
    assert decision['canonical_action'] == 'DOWN' and decision['actual_action'] == 'UP'
    assert decision['predicted_utilities'] == dict(DOWN=1., LEFT=.25)
    assert decision['predicted_pair_utilities']['DOWN|LEFT'] == .75
    assert 'predicted_components' not in decision
    model['coefficients'] = [0.]*6+[100.]*40
    current['layout_features'] = dict(DOWN=layout(rank=99), LEFT=layout(rank=99))
    novel = core.choose_action(model, current)
    assert not novel['fallback'] and novel['canonical_action'] == 'LEFT'
    assert novel['predicted_utilities'] == dict(DOWN=0., LEFT=.25)
    assert all(value['unknown_tokens'] == 40 for value in novel['coverage'].values())
    model['action_root_ids']['LEFT'] = []
    missing = core.choose_action(model, current)
    assert missing['fallback'] and missing['reason'] == 'insufficient_action_support'
    current.update(legal_actions=['UP'], fallback_action='UP', immediate_rewards=dict(UP=0.),
        layout_features=dict(UP=layout()), action_map=dict(UP='DOWN'))
    forced = core.choose_action(model, current)
    assert not forced['fallback'] and forced['reason'] == 'single_legal_action'
    assert forced['canonical_action'] == 'UP' and forced['actual_action'] == 'DOWN'


def test_target_roster_with_mock_rng_only_and_replica_observation(monkeypatch):
    seeds = []
    class FixtureRandom:
        def __init__(self, seed):
            seeds.append(seed)
        def randint(self, lower, upper):
            assert (lower, upper) == (1, 10)
            return 3
        def sample(self, population, count):
            return list(population)[:count]
    monkeypatch.setattr(core.random, 'Random', FixtureRandom)
    cases = core.cohort_cases()
    assert seeds == list(range(1860200, 1860296))
    assert len(cases) == 96 and len({row['name'] for row in cases}) == 96
    assert cases[31]['name'] == 'v186_target_r01_07'
    assert all(row['horizon'] == 3 and row['board'].count(0) == row['stratum'] % 3 for row in cases)
    case = dict(name='synthetic_observation', horizon=3, replica=3, stratum=7, seed=17,
                board=[1, 1, 0, 0]+[0]*12)
    roots, work = core.observe_roots([case])
    assert roots[0]['cohort'] == roots[0]['split'] == 'TARGET'
    assert roots[0]['source_id'] == 'FRESH_REPLICA:03'
    assert work['root_ground_swipe_calls'] == 4


def test_freeze_choices_has_scalar_rank_and_five_controls_without_labels(monkeypatch):
    current, ref = deepcopy(examples()[0]), reference(examples())
    current.update(oracle_action='LEFT', action_component_fractions={'secret': []})
    common = dict(life=0, vocabulary=ref['vocabulary'], action_root_ids=ref['action_root_ids'],
                  pair_root_ids=ref['pair_root_ids'], connected_components=ref['connected_components'])
    controls = {name: dict(common, coefficients=[[0., 0., 0.] for _ in range(46)]) for name in ('RIDGE', 'LAYOUT')}
    controls.update({name: dict(common, coefficients=[[0., 0., 0.] for _ in range(6)]) for name in ('SHARED', 'OLD_SHARED')})
    leaf = dict(leaf_id=0, action_root_ids=ref['action_root_ids'], pair_root_ids=ref['pair_root_ids'],
        connected_components=ref['connected_components'], coefficients={a: [0., 0., 0.] for a in core.ACTIONS})
    controls['ONE'] = dict(life=0, mode='ONE_LATE', groups={'ALL': 0}, leaves=[leaf])
    controls['RANK'] = inference_model()
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
               'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features'}
    chooser = core.choose_action
    def checked(model, observed):
        assert set(observed) == allowed
        return chooser(model, observed)
    monkeypatch.setattr(core, 'choose_action', checked)
    def forbidden(*args, **kwargs):
        raise AssertionError('a cached frozen choice repeated a swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    before = deepcopy(controls)
    choices, work = core.freeze_choices([current], controls)
    assert controls == before and set(choices) == {*core.MODEL_NAMES, 'FALLBACK'}
    assert 'predicted_utilities' in choices['RANK'][0]['decision']
    assert 'predicted_components' not in choices['RANK'][0]['decision']
    assert work['ranking_frozen_model_choices'] == 6 and work['ranking_frozen_fallback_choices'] == 1
    assert all(len(rows) == 1 for rows in choices.values())


def test_ftol_success_with_large_gradient_is_retained_hold_not_a_model(monkeypatch):
    def premature(fun, x0, **kwargs):
        assert kwargs['method'] == 'L-BFGS-B' and kwargs['jac'] is True
        assert kwargs['options'] == dict(maxiter=1000, maxls=50, ftol=1e-15, gtol=1e-10)
        fun(x0)
        return SimpleNamespace(x=x0, success=True, status=0, message='synthetic ftol stop', nit=1, nfev=1, njev=1)
    monkeypatch.setattr(core, 'minimize', premature)
    with pytest.raises(core.RankingExecutionError) as raised:
        core.fit_ranking(examples(), reference(examples()))
    record = raised.value.record
    assert record['optimizer']['success'] and not record['accepted']
    assert record['gradient_inf'] > 1e-7
    assert record['costs']['ranking_optimizer_attempts'] == 1
    assert record['costs']['ranking_loss_gradient_calls'] == 2 and len(record['history']) == 2
    assert 'model' not in record
