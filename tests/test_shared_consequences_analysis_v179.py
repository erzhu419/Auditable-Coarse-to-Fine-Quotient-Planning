"""Independent rotations, weighted SVD and preserved deployment semantics."""
from collections import Counter
from copy import deepcopy
import numpy as np
import pytest

from acfqp.science import controlled_predictive_shared_consequences_v179 as core
from scripts import analyze_controlled_predictive_shared_consequences_v179 as audit
from scripts import run_controlled_predictive_shared_consequences_v179 as runner


def test_manual_no_reflection_rotation_features_and_cache_counts():
    board = [1, 2, 3, 0, 1, 0, 4, 4, 10, 10, 5, 0, 0, 6, 0, 7]
    root = dict(canonical_board=board)
    own_work, production_work = Counter(), Counter()
    actual = audit.action_features_from_root(root, own_work)
    assert actual == core.action_features_from_root(root, production_work)
    assert own_work == production_work
    rotated = audit.action_features_from_root(dict(canonical_board=list(audit.rotate_to_down(board, 'RIGHT'))))
    transport = {'DOWN': 'LEFT', 'LEFT': 'UP', 'RIGHT': 'DOWN', 'UP': 'RIGHT'}
    assert all(actual[action] == rotated[transport[action]] for action in actual)
    cached = dict(root, action_features=actual, action_components={'DOWN': [1000., 0., 1.]})
    own_cache, production_cache = Counter(), Counter()
    assert audit.action_features_from_root(cached, own_cache) == core.action_features_from_root(cached, production_cache)
    assert own_cache == production_cache == Counter(shared_feature_cache_hits=1, shared_cached_feature_reads=6*len(actual))


def examples(rank_deficient):
    coefficients = np.array([[.1, -.1, .1], [.2, .1, -.1], [.05, -.05, .05], [.1, .02, -.02], [.01, -.01, .02], [.03, .01, -.01]])
    rows = []
    for ordinal in range(48):
        if ordinal == 15:
            continue
        features = [1, 1, 0, 0, 0, 0] if rank_deficient else [int(i == ordinal % 6) for i in range(6)]
        tail = np.array(features)@coefficients
        reward = .25 if ordinal % 2 else .125
        rows.append(dict(root_id=f'r:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{ordinal//4:02d}', canonical_board=[0]*16,
            legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': reward, 'LEFT': .1},
            action_features={'DOWN': features, 'LEFT': [0]*6},
            action_components={'DOWN': [float(tail[0]+reward+.4), float(tail[1]+.3), float(tail[2]+.4)], 'LEFT': [.5, .3, .4]},
            provenance={'kind': 'exact H3'}))
    return rows


@pytest.mark.parametrize('rank_deficient', [False, True])
def test_weighted_svd_full_payload_minimum_norm_and_supported_choices(rank_deficient):
    rows = examples(rank_deficient); original = deepcopy(rows)
    actual, expected = audit.fit_model(rows), core.fit_model(rows)
    assert audit.exact._equal(actual, expected) and audit.exact._equal(expected, actual)
    assert actual['rank'] == (1 if rank_deficient else 6)
    assert actual['fit_counts'] == expected['fit_counts'] and actual['feature_counts'] == expected['feature_counts']
    assert actual['source_root_counts']['DESIGN_SOURCE:03'] == 3
    if rank_deficient:
        assert actual['coefficients'][0] == pytest.approx(actual['coefficients'][1])
        assert np.max(np.abs(np.array(actual['coefficients'][2:]))) < 1e-12
    root = dict(rows[0], fallback_action='DOWN', action_map={'DOWN': 'UP', 'LEFT': 'RIGHT'})
    decision, reference = audit.choose_action(actual, root), core.choose_action(expected, root)
    assert audit.exact._equal(decision, reference) and audit.exact._equal(reference, decision)
    assert decision['work'] == reference['work'] and decision['support'] == reference['support']
    root['action_components'] = {'DOWN': [1000., 0., 1.], 'LEFT': [-1000., 1., 0.]}
    assert audit.choose_action(actual, root) == decision
    assert rows == original


def test_alias_ceiling_keeps_signed_gap_and_sorted_representative_ties():
    roots, labels = {}, {}; choices = {name: {} for name in ('SHARED', 'STRUCTURE', 'RAW')}
    for cohort in ('SOURCE', 'TARGET'):
        root = dict(root_id=cohort, source_id='design:0', legal_actions=['DOWN', 'LEFT', 'UP'],
                    immediate_rewards={'DOWN': 0., 'LEFT': 0., 'UP': .1},
                    action_features={'DOWN': [0]*6, 'LEFT': [0, 1, 0, 0, 0, 0], 'UP': [0]*6})
        roots[cohort] = [root]
        labels[cohort] = [dict(root_id=cohort, action_components={'DOWN': [1., 0., 1.], 'LEFT': [.2, .2, 0.], 'UP': [.1, .1, 0.]})]
        for name, action in (('SHARED', 'UP'), ('STRUCTURE', 'LEFT'), ('RAW', 'DOWN')):
            choices[name][cohort] = [dict(root_id=cohort, mode=mode, canonical_action=action if mode == 'TREE' else 'DOWN' if mode == 'ONE' else 'UP', fallback=False)
                                      for mode in ('TREE', 'ONE', 'FALLBACK')]
    models = {name: dict(nodes=[dict(kind='leaf')], candidate_records=[]) for name in ('STRUCTURE', 'RAW')}
    models['SHARED'] = {}
    actual, expected = audit.summarize(roots, labels, choices, models), runner.summarize(roots, labels, choices, models)
    assert audit.exact._equal(actual, expected) and audit.exact._equal(expected, actual)
    record = actual['feature_alias']['TARGET']['root_records'][0]
    assert record['restricted_action'] == 'LEFT'  # Class insertion would choose UP.
    assert record['restricted_minus_one_utility'] == pytest.approx(-2.)
    assert record['oracle_minus_restricted'] == pytest.approx(2.)
    assert record['same_feature_pairs'][0]['continuation_components'] == pytest.approx([1., -.1, 1.])
    assert actual['shared_minus_raw']['TARGET']['diagnostics']['new_positive_regret_roots'] == 1
    assert actual['SHARED']['model_kind'] == 'SHARED' and 'learned_splits' not in actual['SHARED']
