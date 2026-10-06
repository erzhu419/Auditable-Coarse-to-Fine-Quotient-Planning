"""Synthetic mechanics only; the real fresh seeds are never drawn here."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_fresh_h3_confirmation_v184 as core
from acfqp.science import controlled_predictive_compositional_contract_v69 as contract


def cache():
    board = [0]*16
    tokens = [['cell', i, value] for i, value in enumerate(board)]
    tokens += [['horizontal', 4*r+c, 0, 0] for r in range(4) for c in range(3)]
    tokens += [['vertical', 4*r+c, 0, 0] for r in range(3) for c in range(4)]
    return dict(aggregate=[0]*6, tokens=tokens)


def root():
    return dict(root_id='synthetic', source_id='FRESH_REPLICA:00', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=.25, LEFT=.5), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=cache(), LEFT=cache()))


def models():
    actions = core.exact.ACTIONS
    action_ids = {action: [f'train:{i}' for i in range(4)] for action in actions}
    pair_ids = {f'{a}|{b}': [f'train:{i}' for i in range(4)] for a, b in combinations(actions, 2)}
    support = dict(action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=[list(actions)])
    vocabulary = sorted(cache()['tokens'], key=tuple)
    model = dict(life=0, vocabulary=vocabulary, coefficients=[[0., 0., 0.] for _ in range(46)], **support)
    leaf = dict(leaf_id=0, coefficients={action: [0., 0., 0.] for action in actions}, **deepcopy(support))
    return dict(RIDGE=deepcopy(model), LAYOUT=deepcopy(model),
        SHARED=dict(life=0, coefficients=[[0., 0., 0.] for _ in range(6)], **deepcopy(support)),
        ONE=dict(life=0, mode='ONE_LATE', groups={'ALL': 0}, leaves=[leaf]))


def test_generator_geometry_and_seed_roster_with_mock_rng_only(monkeypatch):
    seeds, draws, samples = [], [], []
    class FixtureRandom:
        def __init__(self, seed):
            seeds.append(seed)
        def randint(self, lower, upper):
            draws.append((lower, upper))
            return 3
        def sample(self, population, count):
            samples.append((list(population), count))
            return list(population)[:count]
    monkeypatch.setattr(core.random, 'Random', FixtureRandom)
    cases = core.fresh_cases()
    assert seeds == list(range(core.SEED_BASE, core.SEED_BASE+96))
    assert len(draws) == 96*16 and set(draws) == {(1, 10)}
    assert len(samples) == 96 and len({case['name'] for case in cases}) == 96
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    for ordinal, case in enumerate(cases):
        replica, index = divmod(ordinal, 24)
        left, right = edges[index]
        assert case['name'] == f'v184_h3_r{replica:02d}_{index:02d}'
        assert case['replica'] == replica and case['stratum'] == index and case['horizon'] == 3
        assert case['board'][left] == case['board'][right] == 1+index % 10
        assert case['board'].count(0) == index % 3
        assert left not in samples[ordinal][0] and right not in samples[ordinal][0]


def test_observation_preserves_native_transport_and_replica_provenance():
    case = dict(name='synthetic_observation', horizon=3, replica=2, stratum=5,
                seed=17, board=[1, 1, 0, 0]+[0]*12)
    roots, work = core.observe_roots([case])
    observed = roots[0]
    assert observed['source_id'] == 'FRESH_REPLICA:02'
    assert observed['cohort'] == 'FRESH' and observed['ordinal'] == 0
    assert observed['replica'] == 2 and observed['stratum'] == 5 and observed['seed'] == 17
    assert observed['horizon'] == 3 and observed['board'] == case['board']
    assert set(observed['action_map']) == set(observed['legal_actions'])
    assert observed['fallback_action'] in observed['legal_actions']
    assert observed['immediate_rewards'][observed['fallback_action']] == max(observed['immediate_rewards'].values())
    assert work['root_board_transforms'] == 8 and work['root_ground_swipe_calls'] == 4
    assert 'action_components' not in observed


def test_all_frozen_models_bind_cached_observations_without_labels_or_updates(monkeypatch):
    observed, frozen = root(), models()
    observed.update(action_components={'secret': []}, action_component_fractions={'secret': []},
                    oracle_action='DOWN', teacher_action_native='DOWN')
    before = deepcopy(frozen)
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
               'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features'}
    for module in (core.layout, core.shared, core.exact):
        chooser = module.choose_action
        def checked(model, observable, chooser=chooser):
            assert set(observable) == allowed
            return chooser(model, observable)
        monkeypatch.setattr(module, 'choose_action', checked)
    def forbidden(*args, **kwargs):
        raise AssertionError('a cached choice repeated a ground swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    choices, work = core.freeze_choices([observed], frozen)
    assert frozen == before
    assert set(choices) == {*core.MODEL_NAMES, 'FALLBACK'}
    for mode, rows in choices.items():
        assert len(rows) == 1 and rows[0]['mode'] == mode
        assert rows[0]['canonical_action'] == 'LEFT' and rows[0]['actual_action'] == 'RIGHT'
        assert not rows[0]['fallback']
    assert observed['action_features'] == dict(DOWN=[0]*6, LEFT=[0]*6)
    assert work['fresh_model_choices'] == 4 and work['fresh_fallback_choices'] == 1
    assert work['layout_feature_cache_hits'] == 3 and work['shared_feature_cache_hits'] == 1
    assert 'layout_ground_swipe_calls' not in work and 'shared_ground_swipe_calls' not in work


def test_first_cache_computes_only_four_swipes_shared_uses_same_aggregates(monkeypatch):
    case = dict(name='synthetic_feature', horizon=3, replica=0, stratum=0,
                seed=19, board=[1, 0, 0, 0]+[0]*12)
    roots, _ = core.observe_roots([case])
    calls, swipe = [], core.layout.ground.swipe_board_v1
    def counted(board, action):
        calls.append(action.value)
        return swipe(board, action)
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', counted)
    choices, work = core.freeze_choices(roots, models())
    assert calls == list(core.exact.ACTIONS)
    assert work['layout_ground_swipe_calls'] == 4 and work['layout_feature_maps_computed'] == 1
    assert work['layout_feature_cache_hits'] == 2 and work['shared_feature_cache_hits'] == 1
    assert 'shared_ground_swipe_calls' not in work
    assert roots[0]['action_features'] == {a: record['aggregate'] for a, record in roots[0]['layout_features'].items()}
    assert all(len(rows) == 1 for rows in choices.values())


def synthetic_build():
    class Rule:
        def to_payload(self):
            return {'synthetic': True}
        @classmethod
        def from_payload(cls, payload):
            assert payload == {'synthetic': True}
            return cls()
    cells = {0: (0, 'CUTOFF'), 1: (1, 'ACTIVE'), 2: (2, 'ACTIVE'),
             3: (3, 'ACTIVE'), 4: (0, 'WON'), 5: (0, 'LOST')}
    board = lambda value: (value,)+tuple([0]*15)
    encoding = {(h, board(state)): state for state, (h, _) in cells.items()}
    rows = {(1, 'DOWN'): ((0, Fraction(1, 8), Fraction(1, 2)), (4, Fraction(1, 8), Fraction(1, 2))),
            (2, 'LEFT'): ((1, Fraction(1, 4), Fraction(1)),),
            (3, 'DOWN'): ((2, Fraction(0), Fraction(1)),),
            (3, 'LEFT'): ((2, Fraction(1, 2), Fraction(1)),)}
    built = SimpleNamespace(model=SimpleNamespace(layers={s: h for s, (h, _) in cells.items()},
        terminal={s: status for s, (_, status) in cells.items()}, roots=(3,)),
        rule=Rule(), variant='FULL', encoding=encoding, exact_rows=rows,
        counts={'concrete_states': 6}, elapsed_seconds=0.)
    return built, Rule


def test_full_build_native_teacher_and_exact_vector_pipeline_on_synthetic_kernel(monkeypatch):
    built, rule_type = synthetic_build()
    calls = []
    def builder(board, horizon, rule, variant, max_states):
        calls.append((board, horizon, rule, variant, max_states))
        return built
    monkeypatch.setattr(core, 'build_model', builder)
    monkeypatch.setattr(core, 'load_model', lambda payload: contract.load_model(payload, rule_type))
    native_plan = core.plan
    def planner(compiled, query):
        assert query.reward_weight == query.failure_penalty == query.goal_bonus == 1.
        return native_plan(compiled, query)
    monkeypatch.setattr(core, 'plan', planner)
    case, rule = dict(board=[3]+[0]*15), object()
    result = core.exact_labels(case, rule)
    assert calls == [(tuple(case['board']), 3, rule, 'FULL', 200000)]
    native = result['native']
    assert native['root_index'] == 0 and native['root_cell'] == 3
    assert native['status'] == 'ACTIVE' and native['horizon'] == 3 and native['teacher_action'] == 'LEFT'
    assert native['action_components']['DOWN'] == [.375, 0., .5]
    assert native['action_component_fractions']['LEFT'] == [[7, 8], [0, 1], [1, 2]]
    assert [(row['horizon'], row['action']) for row in result['teacher_policy']] == [(1, 'DOWN'), (2, 'LEFT'), (3, 'LEFT')]
    assert all(set(row) == {'board', 'horizon', 'action'} for row in result['teacher_policy'])
    assert result['costs']['teacher_export']['teacher_encoding_records_read'] == 6
    assert result['costs']['teacher_export']['teacher_policy_records'] == 3
    assert result['costs']['compilation']['payload_rows'] == 4
    assert set(result) == {'native', 'teacher_policy', 'costs'}  # No full kernel retention.


def test_unsupported_fresh_roots_are_retained_with_observable_fallback():
    frozen, observed = models(), root()
    for mode in ('RIDGE', 'LAYOUT', 'SHARED'):
        frozen[mode]['action_root_ids']['LEFT'] = []
    frozen['ONE']['leaves'][0]['action_root_ids']['LEFT'] = []
    choices, work = core.freeze_choices([observed], frozen)
    for mode in core.MODEL_NAMES:
        assert len(choices[mode]) == 1 and choices[mode][0]['fallback']
        assert choices[mode][0]['canonical_action'] == observed['fallback_action']
    assert not choices['FALLBACK'][0]['fallback']
    assert work['fresh_model_choices'] == 4


def test_state_cap_failure_preserves_paid_build_cost_and_stops_before_plan(monkeypatch):
    error = ValueError('synthetic complete model cap')
    error.counts, error.elapsed_seconds = {'concrete_states': 200000}, .25
    def fail(*args, **kwargs):
        assert kwargs['max_states'] == 200000
        raise error
    def forbidden(*args, **kwargs):
        raise AssertionError('failed complete build must not open a teacher plan')
    monkeypatch.setattr(core, 'build_model', fail)
    monkeypatch.setattr(core, 'plan', forbidden)
    with pytest.raises(ValueError) as raised:
        core.exact_labels(dict(board=[0]*16), object())
    assert raised.value is error and error.operation == 'construction'
    assert error.counts == {'concrete_states': 200000} and error.elapsed_seconds == .25
