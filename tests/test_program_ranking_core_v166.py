"""Coherent synthetic ranking reversals and reward/risk noise accounting."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

import pytest

from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science.controlled_predictive_program_ranking_v166 import build_roster, evaluate

TEMP = Path(__file__).resolve().parents[1]/'reports/v166_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    failures = request.session.testsfailed-before
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=failures, exit_code=int(bool(failures)), wall_seconds=perf_counter()-started,
        stdout_ref='reports/v166_runtime_tmp/core_tests.stdout.log', stderr_ref='reports/v166_runtime_tmp/core_tests.stderr.log',
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        real_training_updates=0, native_planner_calls=0, symbolic_learning_work=dict(WORK),
        scope='Coherent synthetic compact-vector fixtures; no environment/model/native sampling or fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def fixture(resolver=None):
    resolver = resolver or (lambda root, suffix, semantic: (True, [4., 1., 0.], [1., 1., 0.]))
    candidates, programs = [], []
    for life in range(4):
        for query in ('risk1', 'risk8'):
            pool = [dict(candidate_id=f'P{2*life+semantic}', first_action='UP' if semantic == 0 else 'DOWN',
                probe_action='LEFT', true_suffix=['LEFT', 'UP', 'RIGHT'] if semantic == 0 else ['DOWN', 'UP', 'LEFT'],
                false_suffix=['RIGHT', 'DOWN', 'LEFT'], fixed_suffix=['UP']*3, occurrences=20+life)
                for semantic in range(2 if query == 'risk1' else 1)]
            selected = life % 2 if query == 'risk1' else 0
            candidates.append(dict(heldout_life=life, query=query, candidates=pool))
            programs.append(dict(heldout_life=life, query=query,
                programs=dict(LEARNED=dict(candidate_id=pool[selected]['candidate_id']))))
    roots = [dict(root_id=f'TRAIN_SOURCE:{life}:{query}:{position}', phase='TRAIN_SOURCE',
        life=life, query=query, replica=position//2, slot=position%2, board=[0]*16)
        for life in range(4) for query in ('risk1', 'risk8') for position in range(4)]
    plans, outcomes = [], []
    for root in roots:
        for fold in range(4):
            if fold == root['life']: continue
            for suffix in range(4):
                for mode, semantic in [('H2', 0)]+[(f'P{2*fold+s}_{arm}', s)
                        for s in range(2 if root['query'] == 'risk1' else 1) for arm in ('A', 'B')]:
                    predicate, a, b = resolver(root, suffix, semantic)
                    vector = [0., 1., 0.] if mode == 'H2' else a if mode.endswith('_A') else b
                    plan = dict(branch_id=f'{root["root_id"]}:fold{fold}:{suffix}:{mode}', root_id=root['root_id'],
                        heldout_life=fold, suffix=suffix, mode=mode,
                        seed=10000+fold*1000+root['life']*100+root['replica']*10+root['slot']*4+suffix)
                    plans.append(plan)
                    outcomes.append(dict(**plan, life=root['life'], query=root['query'], score=vector[0]*2048.,
                        steps=3, status='WON' if vector[2] else 'LOST', components=deepcopy(vector),
                        utility=utility(vector, root['query']), module=dict(predicate=None if mode == 'H2' else predicate,
                            actual_word=['UP'] if predicate is None else ['UP', 'LEFT'], actual_probe='LEFT',
                            prefix_steps=0 if predicate is None else 2, attempts=1 if predicate is None else 2,
                            exit_reason='illegal' if predicate is None else 'budget', exit_step=0 if predicate is None else 2)))
    return candidates, programs, roots, plans, outcomes


def run(data):
    candidates, programs, roots, plans, outcomes = data
    roster = build_roster(candidates, programs, roots, plans)
    retained = {branch['branch_id'] for stratum in roster['strata'] for history in stratum['histories']
                for root in history['roots'] for branch in root['branches']}
    rows = [row for row in outcomes if row['branch_id'] in retained]
    result = evaluate(roster, rows)
    WORK.update(evaluation_calls=1)
    WORK.update(result['logical_work'])
    return roster, result


def summary(result, contrast='A-B', stratum='S0', group='half01'):
    return next(row for row in result['groups'][group]['stratum_summaries']
                if (row['stratum_id'], row['contrast']) == (stratum, contrast))


def test_semantic_union_counts_separate_shared_physical_H2_from_logical_pairs():
    roster, result = run(fixture())
    assert roster['counts'] == dict(semantic_strata=3, strata_per_query=dict(risk1=2, risk8=1),
        semantic_roots=48, unique_root_states=32, logical_triplets=192, logical_branch_references=576,
        present_branch_references=576, unique_physical_branch_rows=512)
    assert [s['selected_by'] for s in roster['strata']] == [
        [dict(target_life=0, candidate_id='P0'), dict(target_life=2, candidate_id='P4')],
        [dict(target_life=1, candidate_id='P3'), dict(target_life=3, candidate_id='P7')],
        [dict(target_life=life, candidate_id=f'P{2*life}') for life in range(4)]]
    assert result['complete'] and result['logical_work']['outcome_rows_supplied'] == 512
    assert result['logical_work']['logical_triplets_examined'] == 192
    assert result['logical_work']['logical_contrast_vectors'] == 1152
    assert 'query_summaries' not in result['groups']['full03']
    assert result['new_environment_samples'] == result['real_training_updates'] == result['native_planner_calls'] == 0


def test_first_metadata_donor_is_not_replaced_after_missing_branch():
    data = fixture()
    bad = next(row for row in data[3] if row['root_id'] == data[2][0]['root_id']
               and row['heldout_life'] == 1 and row['mode'] == 'P2_A' and row['suffix'] == 0)
    data[3].remove(bad)
    roster, result = run(data)
    history = roster['strata'][0]['histories'][0]
    assert history['donor']['heldout_life'] == 1
    assert 'missing_branch_metadata' in history['roots'][0]['issues']
    assert not result['complete'] and result['semantic_root_count'] == 48


def test_utility_decomposition_keeps_whole_vectors_and_counts_one_terminal_discordance():
    _, result = run(fixture(lambda r, s, k: (True, [6., 1., 0.], [0., 0., 1.])))
    risk1, risk8 = summary(result, group='full03'), summary(result, stratum='S2', group='full03')
    assert risk1['metrics']['utility']['mean'] == 4. and risk8['metrics']['utility']['mean'] == -10.
    assert risk1['metrics']['reward_effect']['mean'] == risk8['metrics']['reward_effect']['mean'] == 6.
    assert risk8['metrics']['failure_effect']['mean'] == risk8['metrics']['success_effect']['mean'] == -8.
    assert risk8['metrics']['risk_effect']['mean'] == -16.
    assert risk8['discordance']['terminal_discordant'] == 64
    assert risk1['discordance']['utility_failure_preference_discordant'] == 64
    assert risk8['discordance']['utility_failure_preference_discordant'] == 0
    pair = result['groups']['full03']['root_rows'][0]['pairs'][0]
    assert pair['outcomes']['A']['components'] == [6., 1., 0.]
    assert pair['outcomes']['B']['components'] == [0., 0., 1.]
    assert pair['contrasts']['A-B']['component_delta'] == [6., 1., -1.]


def test_reward_risk_variance_and_covariance_propagate_fixed_weights():
    def resolver(root, suffix, semantic):
        return (True, [0., 1., 0.], [0., 1., 0.]) if suffix % 2 == 0 else (True, [6., 0., 1.], [0., 1., 0.])
    _, result = run(fixture(resolver))
    root = result['groups']['half01']['root_rows'][0]['variance_decomposition']['A-B']
    assert root == dict(n=2, complete=True, utility_sample_variance=32., reward_sample_variance=18.,
        risk_sample_variance=2., utility_mean_variance=16., reward_mean_variance=9., risk_mean_variance=1.,
        reward_risk_sample_covariance=6., reward_risk_mean_covariance=3.)
    aggregate = summary(result)['variance_decomposition']
    assert aggregate == dict(complete=True, utility_mean_variance=1., reward_mean_variance=.5625,
        risk_mean_variance=.0625, reward_risk_mean_covariance=.1875)
    assert aggregate['utility_mean_variance'] == aggregate['reward_mean_variance']+aggregate['risk_mean_variance']+2*aggregate['reward_risk_mean_covariance']
    assert summary(result)['metrics']['utility']['conditional_suffix_ci95'] == pytest.approx([2.04, 5.96])
    assert summary(result, stratum='S2')['variance_decomposition']['utility_mean_variance'] == 7.5625


def test_negative_reward_risk_covariance_is_not_discarded():
    def resolver(root, suffix, semantic):
        return (True, [6., 1., 0.], [0., 0., 1.]) if suffix % 2 == 0 else (True, [0., 0., 1.], [0., 1., 0.])
    _, result = run(fixture(resolver))
    root = result['groups']['half01']['root_rows'][0]['variance_decomposition']['A-B']
    assert root['reward_risk_sample_covariance'] == -12.
    assert root['utility_sample_variance'] == 2.


def test_half_sign_flips_and_tie_changes_are_separate():
    def resolver(root, suffix, semantic):
        if root['slot'] == 0:
            return (True, [3., 1., 0.], [0., 1., 0.]) if suffix < 2 else (True, [0., 1., 0.], [3., 1., 0.])
        return (True, [0., 1., 0.], [0., 1., 0.]) if suffix < 2 else (True, [3., 1., 0.], [0., 1., 0.])
    _, result = run(fixture(resolver))
    history = next(row for row in result['stability']['history_rows'] if row['stratum_id'] == 'S0' and row['life'] == 0 and row['contrast'] == 'A-B')
    assert history['half01_sign'] == 1 and history['half23_sign'] == 0
    assert history['tie_change'] and not history['sign_flip']
    assert history['root_sign_flips'] == 2 and history['root_tie_changes'] == 2
    stratum = next(row for row in result['stability']['stratum_rows'] if row['stratum_id'] == 'S0' and row['contrast'] == 'A-B')
    assert stratum['root_sign_flips'] == 8 and stratum['history_tie_changes'] == 4


def test_none_prefix_is_retained_as_identical_A_B_and_zero_AB_rank_noise():
    _, result = run(fixture(lambda r, s, k: (None, [5., 1., 0.], [5., 1., 0.])))
    assert result['complete']
    assert summary(result, group='full03')['metrics']['utility']['mean'] == 0.
    assert summary(result, group='full03')['discordance']['terminal_discordant'] == 0
    assert all(row['contrasts']['A-B']['half01_sign'] == row['contrasts']['A-B']['half23_sign'] == 0
               for row in result['stability']['root_rows'])


@pytest.mark.parametrize('failure', ['missing', 'nonterminal', 'seed', 'predicate', 'none_path', 'utility', 'score', 'status'])
def test_invalid_pairs_keep_all_semantic_roots_and_null_affected_stratum(failure):
    data = fixture(lambda r, s, k: (None, [2., 1., 0.], [2., 1., 0.]) if s == 3 else (True, [4., 1., 0.], [1., 1., 0.]))
    row = next(row for row in data[4] if row['root_id'] == data[2][0]['root_id']
               and row['heldout_life'] == 1 and row['mode'] == 'P2_B' and row['suffix'] == 3)
    expected = dict(missing='missing_outcome', nonterminal='nonterminal_outcome', seed='outcome_seed_mismatch',
        predicate='predicate_mismatch', none_path='none_path_mismatch', utility='recorded_utility_mismatch',
        score='terminal_component_mismatch', status='terminal_component_mismatch')[failure]
    if failure == 'missing': data[4].remove(row)
    elif failure == 'nonterminal': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'predicate': row['module']['predicate'] = True
    elif failure == 'none_path': row['module']['attempts'] += 1
    elif failure == 'utility': row['utility'] += 1.
    elif failure == 'score': row['score'] += 1.
    else: row['status'] = 'WON'
    _, result = run(data)
    root = result['groups']['full03']['root_rows'][0]
    assert result['semantic_root_count'] == 48 and not result['complete']
    assert expected in root['issues'] and len(root['pairs']) == 4
    assert summary(result)['metrics']['utility']['mean'] is None


def test_shared_missing_H2_invalidates_both_semantic_references_without_deleting_roots():
    data = fixture()
    row = next(row for row in data[4] if row['root_id'] == data[2][0]['root_id']
               and row['heldout_life'] == 1 and row['mode'] == 'H2' and row['suffix'] == 0)
    data[4].remove(row)
    _, result = run(data)
    assert result['semantic_root_count'] == 48 and result['complete_semantic_root_count'] == 46
    assert summary(result)['metrics']['utility']['mean'] is None
    assert summary(result, stratum='S1')['metrics']['utility']['mean'] is None
    assert summary(result, stratum='S2')['complete']
