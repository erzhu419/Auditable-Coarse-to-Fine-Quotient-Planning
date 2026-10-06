"""Fresh suffix accounting detects pairing, terminal and inference errors."""
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_fixed_program_v167 as audit
from acfqp.science import controlled_predictive_fixed_program_v167 as core


def data():
    roots = [dict(root_id=f'{life}:{replica}:{slot}', phase='EVAL_SOURCE', life=life, query='risk1',
                  replica=replica, slot=slot, board=[0]*16)
             for life in range(4) for replica in range(4) for slot in range(2)]
    rows = []
    for root in roots:
        for suffix in range(16):
            for mode in ('H2', 'S0_B'):
                gain = 0. if mode == 'H2' else 1. if suffix < 8 else 3.
                vector = [2.+gain, 0., 1.]
                rows.append(dict(root_id=root['root_id'], phase='EVAL', heldout_life=root['life'], life=root['life'],
                                 query='risk1', replica=root['replica'], slot=root['slot'], suffix=suffix,
                                 mode=mode, arm='H2' if mode == 'H2' else 'FEEDBACK', seed=audit.seed(root, suffix),
                                 branch_id=f"{root['root_id']}:{suffix}:{mode}", status='WON', score=vector[0]*2048,
                                 steps=10, components=vector, utility=vector[0]+1,
                                 module=dict(predicate=None if mode == 'H2' else True, prefix_steps=0 if mode == 'H2' else 4,
                                             attempts=0 if mode == 'H2' else 4, exit_reason='baseline' if mode == 'H2' else 'budget')))
    return roots, rows


def test_independent_fresh_mean_variance_and_core_agree():
    roots, rows = data()
    summary = core.summarize(roots, rows)
    checks, independent = audit.check_statistics(roots, rows, summary)
    assert all(c['passed'] for c in checks), [c for c in checks if not c['passed']]
    utility = independent['comparison']['metrics']['utility']
    assert utility['mean'] == 2 and utility['mean_variance'] == pytest.approx(1/480)
    assert independent['root_rows'][0]['contrasts']['S0_B-H2']['utility']['sample_variance'] == pytest.approx(16/15)


def test_exact_fresh_seed_roster_has_512_pairs():
    roots, _ = data(); plan = audit.independent_plan(roots)
    assert len(plan) == 1024
    assert len({row['seed'] for row in plan}) == 512
    assert plan[0]['seed'] == 16750000000
    assert all(row['arm'] == ('H2' if row['mode'] == 'H2' else 'FEEDBACK') for row in plan)


@pytest.mark.parametrize('corruption', ['missing', 'duplicate', 'seed', 'cutoff', 'terminal_vector'])
def test_invalid_fresh_pair_is_retained_and_blocks_primary(corruption):
    roots, rows = data()
    if corruption == 'missing': rows.pop(1)
    elif corruption == 'duplicate': rows.append(deepcopy(rows[1]))
    elif corruption == 'seed': rows[1]['seed'] -= 100000000
    elif corruption == 'cutoff': rows[1].update(status='CUTOFF', utility=None)
    else: rows[1]['status'] = 'LOST'
    independent = audit.independent_statistics(roots, rows)
    assert not independent['complete'] and independent['root_count'] == 32
    assert not independent['root_rows'][0]['complete'] and len(independent['root_rows'][0]['pairs']) == 16
    assert independent['comparison']['metrics']['utility']['mean'] is None


def test_wrong_ci_and_pair_sign_fail_independent_checks():
    roots, rows = data(); original = core.summarize(roots, rows)
    for corruption in ('ci', 'pair_sign'):
        summary = deepcopy(original)
        if corruption == 'ci': summary['comparison']['metrics']['utility']['conditional_suffix_ci95'][0] -= .1
        else: summary['root_rows'][0]['pairs'][0]['utility_delta'] *= -1
        checks, _ = audit.check_statistics(roots, rows, summary)
        assert not all(c['passed'] for c in checks)


def test_execution_diagnostics_use_all_fresh_branches():
    _, rows = data()
    diagnostics = audit._diagnostics(rows)
    selected = next(d for d in diagnostics if d['mode'] == 'S0_B')
    assert selected['branches'] == selected['present_branches'] == selected['probe_branches'] == 512
    assert selected['mean_prefix_steps'] == 4 and selected['mean_continuation_steps'] == 6
    assert selected['continuation_branches'] == 512 and selected['same_step_fallback_branches'] == 0
