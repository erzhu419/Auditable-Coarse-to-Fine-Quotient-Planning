"""Pure frozen-word, fresh-roster, and fixed-root paired statistics tests."""
from copy import deepcopy
from math import sqrt

import pytest

from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science.controlled_predictive_fixed_program_v167 import (
    branch_seed, build_program, build_roster, extract_candidate, summarize)


def source_fixture():
    source = dict(candidate_id='P0', first_action='UP', probe_action='LEFT',
        true_suffix=['UP', 'RIGHT', 'LEFT'], false_suffix=['LEFT', 'LEFT', 'UP'],
        fixed_suffix=['RIGHT', 'UP', 'DOWN'], occurrences=64, condition_counts=dict(true=12, false=52))
    later = dict(deepcopy(source), candidate_id='P1', occurrences=100000)
    candidates = [dict(heldout_life=0, query='risk1', candidates=[source, later]),
                  dict(heldout_life=1, query='risk1', candidates=[deepcopy(source)])]
    roster = dict(strata=[dict(stratum_id='S0', query='risk1', source_semantics={
        key: deepcopy(source[key]) for key in ('first_action', 'probe_action', 'true_suffix', 'false_suffix')})])
    return candidates, roster


def fixture(resolver=None):
    resolver = resolver or (lambda root, suffix: ([0., 1., 0.], [3., 1., 0.]))
    roots = [dict(root_id=f'EVAL_SOURCE:{life}:risk1:{replica}:{slot}', phase='EVAL_SOURCE',
        life=life, query='risk1', replica=replica, slot=slot)
        for life in range(4) for replica in range(4) for slot in range(2)]
    root_index = {root['root_id']: root for root in roots}
    outcomes = []
    for plan in build_roster(roots):
        root = root_index[plan['root_id']]
        h2, b = resolver(root, plan['suffix'])
        vector = h2 if plan['mode'] == 'H2' else b
        program = plan['mode'] == 'S0_B'
        module = dict(program=None, arm=plan['arm'], actual_word=['UP', 'LEFT', 'LEFT', 'UP'] if program else [],
            actual_probe='LEFT' if program else None, predicate=bool(plan['suffix'] % 2) if program else None,
            prefix_steps=4 if program else 0, attempts=4 if program else 0,
            exit_reason='budget' if program else 'baseline', exit_step=4 if program else 0)
        outcomes.append(dict(**plan, score=vector[0]*2048., steps=10,
            status='WON' if vector[2] else 'LOST', components=deepcopy(vector),
            utility=utility(vector, 'risk1'), module=module))
    return roots, outcomes


def test_original_fold_zero_first_match_and_exact_BB_word_preserve_source_fields():
    candidates, roster = source_fixture()
    frozen = deepcopy(candidates)
    candidate = extract_candidate(candidates, roster)
    assert candidate['candidate_id'] == 'P0' and candidate['occurrences'] == 64
    program = build_program(candidate)
    assert [program['first_action'], *program['true_suffix']] == ['UP', 'LEFT', 'LEFT', 'UP']
    assert program['true_suffix'] == program['false_suffix'] == candidate['false_suffix']
    assert program['probe_action'] == 'LEFT'
    assert program['fixed_suffix'] == candidate['fixed_suffix'] == ['RIGHT', 'UP', 'DOWN']
    program['true_suffix'][0] = 'DOWN'
    assert program['false_suffix'] == candidate['false_suffix'] == ['LEFT', 'LEFT', 'UP']
    assert candidates == frozen


def test_missing_fold_zero_semantics_does_not_choose_another_source_fold():
    candidates, roster = source_fixture()
    candidates[0]['candidates'] = []
    with pytest.raises(ValueError, match='fold-zero'):
        extract_candidate(candidates, roster)


def test_roster_has_exact_fresh_pairs_seeds_and_arms_without_risk8_branches():
    roots, _ = fixture()
    roots.append(dict(root_id='EVAL_SOURCE:0:risk8:0:0', phase='EVAL_SOURCE', life=0, query='risk8', replica=0, slot=0))
    plans = build_roster(roots)
    assert len(plans) == len({row['branch_id'] for row in plans}) == 1024
    assert len({row['seed'] for row in plans}) == 512
    assert all(row['query'] == 'risk1' and row['phase'] == 'EVAL' for row in plans)
    assert all(row['arm'] == ('H2' if row['mode'] == 'H2' else 'FEEDBACK') for row in plans)
    assert branch_seed(dict(life=3, replica=3, slot=1), 15) == 16753003115
    assert plans[0]['seed'] == plans[1]['seed'] == 16750000000


def test_paired_CI_uses_16_suffixes_eight_roots_and_four_fixed_histories():
    def resolver(root, suffix):
        factor = (root['life']+1)*(root['replica']*2+root['slot']+1)
        return [0., 1., 0.], [(2. if suffix % 2 == 0 else 6.)*factor, 1., 0.]
    result = summarize(*fixture(resolver))
    stats = result['comparison']['metrics']['utility']
    assert result['complete'] and result['root_count'] == 32
    assert stats['mean'] == 45.
    assert stats['mean_variance'] == pytest.approx(1.59375)
    assert stats['conditional_suffix_se'] == pytest.approx(sqrt(1.59375))
    assert stats['conditional_suffix_ci95'] == pytest.approx([45-1.96*sqrt(1.59375), 45+1.96*sqrt(1.59375)])
    root = result['root_rows'][0]['contrasts']['S0_B-H2']['utility']
    assert root == dict(n=16, complete=True, mean=4., sample_variance=64/15, mean_variance=4/15)
    assert result['logical_work'] == dict(outcome_rows_supplied=1024, paired_suffixes_examined=512, component_difference_vectors=512)


def test_whole_component_gain_includes_failure_and_success_and_retains_negative_result():
    result = summarize(*fixture(lambda r, s: ([0., 0., 1.], [1., 1., 0.])))
    assert result['complete']
    pair = result['root_rows'][0]['pairs'][0]
    assert pair['component_delta'] == [1., 1., -1.] and pair['utility_delta'] == -1.
    assert pair['outcomes']['S0_B']['components'] == [1., 1., 0.]
    assert result['comparison']['metrics']['utility']['mean'] == -1.


@pytest.mark.parametrize('failure', ['missing', 'cutoff', 'seed', 'utility', 'score', 'status', 'duplicate'])
def test_incomplete_fresh_pair_keeps_every_root_and_null_affected_statistic(failure):
    roots, outcomes = fixture()
    row = outcomes[1]
    expected = dict(missing='missing_outcome', cutoff='nonterminal_outcome', seed='paired_seed_mismatch',
        utility='recorded_utility_mismatch', score='terminal_component_mismatch',
        status='terminal_component_mismatch', duplicate='duplicate_outcome')[failure]
    if failure == 'missing': outcomes.remove(row)
    elif failure == 'cutoff': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'utility': row['utility'] += 1.
    elif failure == 'score': row['score'] += 1.
    elif failure == 'status': row['status'] = 'WON'
    else: outcomes.append(deepcopy(row))
    result = summarize(roots, outcomes)
    assert not result['complete'] and result['root_count'] == 32
    assert len(result['root_rows'][0]['pairs']) == 16
    assert expected in result['root_rows'][0]['issues']
    assert result['comparison']['metrics']['utility']['mean'] is None
    if failure == 'cutoff':
        assert result['root_rows'][0]['pairs'][0]['outcomes']['S0_B']['status'] == 'CUTOFF'


def test_missing_eval_root_is_incomplete_without_replacement():
    roots, outcomes = fixture()
    missing = roots.pop()
    outcomes = [row for row in outcomes if row['root_id'] != missing['root_id']]
    result = summarize(roots, outcomes)
    assert not result['complete'] and result['root_count'] == 31
    assert all('eval_root_roster' in row['issues'] for row in result['root_rows'])


def test_prefix_probe_and_same_step_fallback_diagnostics_retain_all_modes():
    roots, outcomes = fixture()
    row = outcomes[1]
    row['module'].update(predicate=None, prefix_steps=0, attempts=1, exit_reason='illegal', exit_step=0)
    result = summarize(roots, outcomes)
    diag = next(row for row in result['program_diagnostics'] if row['mode'] == 'S0_B')
    assert result['complete'] and diag['complete'] and diag['branches'] == diag['present_branches'] == 512
    assert diag['probe_branches'] == 511 and diag['same_step_fallback_branches'] == 1
    assert diag['exit_counts'] == dict(illegal=1, budget=511)
    assert diag['mean_prefix_steps'] == 511*4/512
    assert diag['mean_continuation_steps'] == (10+511*6)/512
