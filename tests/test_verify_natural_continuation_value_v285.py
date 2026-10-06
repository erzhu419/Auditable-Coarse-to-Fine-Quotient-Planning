"""Real receipt failures without environment draws or continuation planning."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('verify_continuation_v285',
    Path(__file__).resolve().parents[1]/'scripts/verify_natural_continuation_value_v285.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)
LOST = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]


def state_fixture():
    return dict(state_id='L00-A-0', lifecycle=0, phase='A', phase_index=0, slot=0,
        legal_actions=['DOWN', 'UP'], proxy_action='DOWN', short_action='UP', retained_action='UP',
        immediate_scores=dict(DOWN=2048, UP=4096))


def receipts():
    state = state_fixture()
    rows = []
    for batch in verify.BATCHES:
        for action in state['legal_actions']:
            # Discovery selects UP on total return even though its suffix is
            # lower; independent validation retains a genuinely negative gain.
            total = (5120 if batch == 'discovery' else 4096) if action == 'UP' else 4608
            first = state['immediate_scores'][action]
            for replica in range(32):
                rows.append(dict(action=action, batch=batch, replica_index=replica,
                    seed=verify.expected_seed(state, batch, replica), first_score=first,
                    total_score=total, total_utility=total/2048.-4.,
                    suffix_utility=(total-first)/2048.-4., status='LOST', steps=2,
                    final_board=LOST.copy()))
    return state, rows


def test_complete_independent_batches_use_total_discovery_and_keep_negative_validation():
    state, rows = receipts()
    result = verify.rebuild_state(state, rows)
    assert result['winner'] == 'UP'
    assert result['contrasts']['winner_minus_proxy'] == dict(mean=-.25, paired_mc_se=0.)
    assert result['contrasts']['short_minus_proxy']['mean'] == -.25
    assert result['contrasts']['retained_minus_proxy']['mean'] == -.25


@pytest.mark.parametrize('damage,message', [
    ('missing', 'complete 32-replica'), ('duplicate', 'duplicate'), ('seed', 'paired stream'),
    ('suffix', 'suffix utility'), ('first', 'immediate score'), ('terminal', 'legal move'),
])
def test_reachable_receipt_corruption_is_rejected(damage, message):
    state, rows = receipts()
    if damage == 'missing':
        rows.pop()
    elif damage == 'duplicate':
        rows.append(deepcopy(rows[0]))
    elif damage == 'seed':
        rows[0]['seed'] += 100
    elif damage == 'suffix':
        rows[0]['suffix_utility'] = rows[0]['total_utility']
    elif damage == 'first':
        rows[0]['first_score'] = 0
    elif damage == 'terminal':
        rows[0]['final_board'][0] = 0
    with pytest.raises(ValueError, match=message):
        verify.rebuild_state(state, rows)


def test_winning_first_action_counts_terminal_once_and_excludes_only_first_reward_from_suffix():
    state = state_fixture()
    row = dict(action='DOWN', batch='validation', replica_index=0,
        seed=verify.expected_seed(state, 'validation', 0), first_score=2048, total_score=2048,
        total_utility=5., suffix_utility=4., status='WON', steps=1, final_board=[11, 1]+[0]*14)
    verify.validate_rollout(state, row)
    row['total_utility'] = 4.
    with pytest.raises(ValueError, match='total utility'):
        verify.validate_rollout(state, row)


def test_group_phase_life_weights_and_negative_signs_are_independent():
    rows = []
    for group, base in [('uniform', -10.), ('competition', 20.)]:
        for life in range(16):
            for phase_index, phase in enumerate(verify.PHASES):
                for slot in range(4):
                    value = base + life + 2*phase_index + slot
                    rows.append(dict(group=group, lifecycle=life, phase=phase,
                        contrasts={name: dict(mean=value) for name in verify.CONTRASTS}))
    groups = verify.rebuild_groups(rows)
    assert groups['uniform'][0]['contrasts']['winner_minus_proxy'] == -6.5
    assert groups['competition'][0]['contrasts']['winner_minus_proxy'] == 23.5
    assert sum(r['contrasts']['winner_minus_proxy'] for r in groups['uniform'])/16 == 1.
    assert sum(r['contrasts']['winner_minus_proxy'] for r in groups['competition'])/16 == 31.
    assert [r['lifecycle'] for r in groups['uniform'] if r['contrasts']['winner_minus_proxy'] < 0] == list(range(7))


def test_physical_streams_and_forced_step_are_billed_separately_from_h2():
    state, _ = receipts()
    rows = [dict(status='WON', steps=1), dict(status='LOST', steps=2)]
    counts = dict(environment=dict(sampled_transitions=3, environment_random_draws=6,
        ground_explicit_swipe_calls=3, ground_state_status_calls=3,
        ground_status_internal_swipe_calls=8, ground_swipe_calls=11),
        rollout=dict(completed_rollouts=2, rng_streams_started=2,
            continuation_choose_calls=1, evaluate_calls=2, replica_streams=64),
        planning=dict(root_swipe_calls=4, learned_swipe_calls=8, second_ply_swipe_calls=4,
            leaf_choose_calls=2, generated_spawn_outcomes=2, expanded_postspawn_states=2,
            spawn_rank1_outcomes=1, spawn_rank2_outcomes=1,
            expectimax_probability_products=2, expectimax_probability_sums=2,
            value_predictions=3, table_lookups=96))
    verify.check_counts(counts, rows, [state])
    counts['environment']['environment_random_draws'] = 3
    with pytest.raises(ValueError, match='transition/RNG'):
        verify.check_counts(counts, rows, [state])
