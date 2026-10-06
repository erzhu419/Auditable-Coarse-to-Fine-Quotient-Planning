"""Synthetic fixed-root selection, identification, and paired-weight checks."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_policy_modules_v151 import utility
from acfqp.science.controlled_predictive_program_headroom_v165 import (
    build_roster, evaluate as _evaluate, semantic_key)

TEMP = Path(__file__).resolve().parents[1]/'reports/v165_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=0, real_training_updates=0, native_planner_calls=0,
        symbolic_learning_work=dict(WORK), scope='Synthetic coherent terminal-vector fixtures; no physical or native sampling.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def fixture(resolver=None, baseline=None, learned=None):
    resolver = resolver or (lambda root, suffix: (suffix % 2 == 0, [4., 1., 0.], [1., 1., 0.]))
    baseline = baseline or [0., 1., 0.]
    learned = learned or dict(true='A', false='B')
    candidates, programs = [], []
    for life in range(4):
        for query in ('risk1', 'risk8'):
            candidate = dict(candidate_id=f'P{life}', first_action='UP', probe_action='LEFT',
                true_suffix=['LEFT', 'UP', 'RIGHT'], false_suffix=['RIGHT', 'DOWN', 'LEFT'],
                fixed_suffix=['DOWN', 'UP', 'LEFT'] if life % 2 else ['LEFT', 'RIGHT', 'UP'],
                occurrences=100-life, condition_counts=dict(true=3+life, false=20-life))
            candidates.append(dict(heldout_life=life, query=query, candidates=[candidate]))
            programs.append(dict(heldout_life=life, query=query, complete=True,
                programs=dict(LEARNED=dict(candidate_id=candidate['candidate_id'], mapping=deepcopy(learned)),
                              GLOBAL=dict(candidate_id=candidate['candidate_id'], mapping=dict(true='A', false='A')))))
    roots = [dict(root_id=f'TRAIN_SOURCE:{life}:{query}:{slot}', phase='TRAIN_SOURCE',
                  life=life, query=query, replica=slot//2, slot=slot%2)
             for life in range(4) for query in ('risk1', 'risk8') for slot in range(4)]
    plans, outcomes = [], []
    for root in roots:
        for fold in range(4):
            if fold == root['life']:
                continue
            for suffix in range(4):
                predicate, a, b = resolver(root, suffix)
                for mode in ('H2', f'P{fold}_A', f'P{fold}_B'):
                    plan = dict(root_id=root['root_id'], heldout_life=fold, suffix=suffix, mode=mode,
                        seed=10000+fold*1000+root['life']*100+root['replica']*10+root['slot']*4+suffix,
                        branch_id=f'{root["root_id"]}:fold{fold}:{suffix}:{mode}')
                    plans.append(plan)
                    vector = baseline if mode == 'H2' else a if mode.endswith('_A') else b
                    path = dict(actual_word=['UP'] if predicate is None else ['UP', 'LEFT'], actual_probe='LEFT',
                        prefix_steps=0 if predicate is None else 2, attempts=1 if predicate is None else 2,
                        exit_reason='illegal' if predicate is None else 'budget', exit_step=0 if predicate is None else 2,
                        predicate=None if mode == 'H2' else predicate)
                    outcomes.append(dict(**plan, life=root['life'], query=root['query'],
                        score=vector[0]*2048., steps=3, status='WON' if vector[2] else 'LOST',
                        components=deepcopy(vector), utility=utility(vector, root['query']), module=path))
    return candidates, programs, roots, plans, outcomes


def run(data):
    candidates, programs, roots, plans, outcomes = data
    roster = build_roster(candidates, programs, roots, plans)
    result = _evaluate(roster, outcomes)
    WORK.update(evaluation_calls=1, synthetic_outcome_rows_supplied=len(outcomes))
    WORK.update(result['logical_work'])
    return roster, result


def comparison(result, contrast, query='risk1', split='primary'):
    return next(row for row in result['splits'][split]['comparisons']
                if (row['query'], row['contrast']) == (query, contrast))


def test_semantic_matching_ignores_ids_frequencies_and_fixed_suffix():
    data = fixture()
    left, right = data[0][0]['candidates'][0], data[0][2]['candidates'][0]
    assert left['candidate_id'] != right['candidate_id'] and left['fixed_suffix'] != right['fixed_suffix']
    assert semantic_key(left) == semantic_key(right)
    roster, result = run(data)
    assert roster['complete'] and roster['root_count'] == 32 and result['complete']
    assert [cell['donor']['heldout_life'] for cell in roster['cells']] == [1, 1, 0, 0, 0, 0, 0, 0]
    assert sum(len(root['branches']) for cell in roster['cells'] for root in cell['roots']) == 384
    assert result['logical_work']['outcome_triples_examined'] == 128
    assert result['logical_work']['root_choice_fits'] == 64
    assert result['logical_work']['refit_cell_fits'] == 16
    assert result['new_environment_samples'] == result['native_planner_calls'] == result['real_training_updates'] == 0


def test_first_matching_donor_is_kept_when_metadata_is_missing():
    data = fixture()
    bad = next(plan for plan in data[3] if plan['root_id'] == data[2][0]['root_id'] and plan['heldout_life'] == 1)
    data[3].remove(bad)
    roster, result = run(data)
    assert roster['cells'][0]['donor']['heldout_life'] == 1
    assert 'missing_branch_metadata' in roster['cells'][0]['roots'][0]['issues']
    assert not result['complete'] and result['root_count'] == 32
    assert comparison(result, 'ROOT-BIT_REFIT')['metrics']['utility']['mean'] is None


def test_missing_semantics_stays_unknown_without_candidate_replacement():
    data = fixture()
    data[0][0]['candidates'][0]['true_suffix'] = ['UP', 'UP', 'UP']
    roster, result = run(data)
    assert roster['cells'][0]['donor'] is None
    assert roster['cells'][0]['issues'] == ['semantic_donor_missing']
    assert len(roster['cells'][0]['roots']) == 4 and result['root_count'] == 32
    assert not result['complete']


def test_rare_true_false_and_nonentering_world_keeps_full_roster_weight():
    def resolver(root, suffix):
        if root['replica'] == 1 and root['slot'] == 1:
            return None, [5., 1., 0.], [5., 1., 0.]
        if root['replica'] == 0 and root['slot'] == 0 and suffix == 0:
            return True, [6., 1., 0.], [0., 1., 0.]
        return False, [2., 1., 0.], [3., 1., 0.]
    _, result = run(fixture(resolver))
    cell = result['splits']['primary']['cells'][0]
    assert cell['leaf_evidence']['true']['support'] == 1
    assert cell['leaf_evidence']['false']['support'] == 5
    assert cell['leaf_evidence']['true']['component_delta_A_minus_B'] == [.75, 0., 0.]
    assert cell['leaf_evidence']['false']['component_delta_A_minus_B'] == [-.625, 0., 0.]
    assert comparison(result, 'ROOT-BIT_REFIT')['metrics']['utility']['mean'] == -.25
    reverse = result['splits']['reverse']['cells'][0]
    assert reverse['leaf_evidence']['true']['support'] == 0
    assert reverse['leaf_evidence']['true']['component_delta_A_minus_B'] is None
    assert reverse['allowed_mapping_codes'] == ['AA', 'AB']
    none = result['splits']['primary']['root_rows'][3]
    assert none['selected_arm'] == 'A'
    assert all(trial['predicate'] is None and trial['modes']['A']['components'] == trial['modes']['B']['components']
               for trial in none['test_trials'])


def test_unseen_leaf_keeps_frozen_learned_assignment_instead_of_source_assignment():
    _, result = run(fixture(lambda r, s: (True, [5., 1., 0.], [0., 1., 0.]),
                           learned=dict(true='B', false='A')))
    cell = result['splits']['primary']['cells'][0]
    assert cell['leaf_evidence']['false']['prior_assignment'] == 'A'
    assert cell['leaf_evidence']['false']['utility_delta_A_minus_B'] is None
    assert cell['allowed_mapping_codes'] == ['AA', 'BA'] and cell['bit_refit_mapping_code'] == 'AA'
    assert comparison(result, 'ROOT-LEARNED')['metrics']['utility']['mean'] == 5.
    assert comparison(result, 'ROOT-BIT_REFIT')['metrics']['utility']['mean'] == 0.


def test_root_information_can_outperform_shared_bit_refit():
    def resolver(root, suffix):
        return (True, [3., 1., 0.], [0., 1., 0.]) if root['replica'] == 0 else (True, [0., 1., 0.], [3., 1., 0.])
    _, result = run(fixture(resolver))
    assert comparison(result, 'ROOT-BIT_REFIT')['metrics']['utility']['mean'] == 1.5
    assert comparison(result, 'ROOT-GLOBAL_REFIT')['metrics']['utility']['mean'] == 1.5
    assert result['splits']['primary']['root_choices'][0]['counts'] == dict(A=8, B=8)


def test_selection_never_fits_scoring_half_and_reverse_remains_secondary():
    def resolver(root, suffix):
        return (True, [1., 1., 0.], [3., 1., 0.]) if suffix < 2 else (True, [5., 1., 0.], [0., 1., 0.])
    _, result = run(fixture(resolver))
    assert all(row['selected_arm'] == 'B' for row in result['splits']['primary']['root_rows'])
    assert all(row['selected_arm'] == 'A' for row in result['splits']['reverse']['root_rows'])
    assert comparison(result, 'ROOT-H2')['metrics']['utility']['mean'] == 0.
    assert comparison(result, 'ROOT-H2', split='reverse')['metrics']['utility']['mean'] == 1.
    assert comparison(result, 'TEST_ROOT_MEAN_ORACLE-ROOT')['metrics']['utility']['mean'] == 5.


def test_ties_choose_A_and_negative_winners_remain_reported():
    _, result = run(fixture(lambda r, s: (True, [1., 1., 0.], [1., 1., 0.]), baseline=[5., 1., 0.]))
    assert all(row['selected_arm'] == 'A' for row in result['splits']['primary']['root_rows'])
    assert all(cell['bit_refit_mapping_code'] == 'AB' and cell['global_refit_mapping_code'] == 'AA'
               for cell in result['splits']['primary']['cells'])
    assert comparison(result, 'ROOT-H2')['metrics']['utility']['mean'] == -4.


def test_whole_vectors_respect_query_utility_without_component_maxima():
    _, result = run(fixture(lambda r, s: (True, [6., 1., 0.], [0., 0., 1.])))
    rows = result['splits']['primary']['root_rows']
    assert all(row['selected_arm'] == ('A' if row['query'] == 'risk1' else 'B') for row in rows)
    assert all(trial['modes']['ROOT']['components'] == ([6., 1., 0.] if row['query'] == 'risk1' else [0., 0., 1.])
               for row in rows for trial in row['test_trials'])


def test_paired_suffix_CI_propagates_exact_root_and_history_weights():
    def resolver(root, suffix):
        factor = (root['life']+1)*(root['replica']*2+root['slot']+1)
        return True, [(2. if suffix % 2 == 0 else 6.)*factor, 1., 0.], [0., 1., 0.]
    _, result = run(fixture(resolver))
    stats = comparison(result, 'A-H2')['metrics']['utility']
    assert stats['mean'] == 25.
    assert stats['mean_variance'] == 14.0625
    assert stats['conditional_suffix_se'] == 3.75
    assert stats['conditional_suffix_ci95'] == pytest.approx([17.65, 32.35])
    root = result['splits']['primary']['root_rows'][0]['contrasts']['A-H2']['utility']
    assert root == dict(n=2, complete=True, mean=4., sample_variance=8., mean_variance=4.)


@pytest.mark.parametrize('failure', ['missing', 'nonterminal', 'seed', 'predicate', 'none_outcome', 'none_path', 'utility'])
def test_incomplete_pairs_preserve_all_32_roots(failure):
    data = fixture(lambda r, s: (None, [2., 1., 0.], [2., 1., 0.]) if s == 3 else (True, [4., 1., 0.], [1., 1., 0.]))
    row = next(row for row in data[4] if row['root_id'] == data[2][0]['root_id']
               and row['heldout_life'] == 1 and row['mode'] == 'P1_B' and row['suffix'] == 3)
    expected = {'missing': 'missing_outcome', 'nonterminal': 'nonterminal_outcome',
        'seed': 'outcome_seed_mismatch', 'predicate': 'predicate_mismatch',
        'none_outcome': 'none_outcome_mismatch', 'none_path': 'none_path_mismatch', 'utility': 'recorded_utility_mismatch'}[failure]
    if failure == 'missing': data[4].remove(row)
    elif failure == 'nonterminal': row.update(status='CUTOFF', utility=None)
    elif failure == 'seed': row['seed'] += 1
    elif failure == 'predicate': row['module']['predicate'] = True
    elif failure == 'none_outcome': row['steps'] += 1
    elif failure == 'none_path': row['module']['attempts'] += 1
    else: row['utility'] += 1.
    _, result = run(data)
    root = result['splits']['primary']['root_rows'][0]
    assert result['root_count'] == 32 and not result['complete'] and not root['complete']
    assert expected in root['issues']
    assert comparison(result, 'ROOT-BIT_REFIT')['metrics']['utility']['mean'] is None


def test_frozen_global_mapping_must_be_constant_on_same_candidate():
    data = fixture()
    data[1][0]['programs']['GLOBAL']['mapping'] = dict(true='A', false='B')
    roster, result = run(data)
    assert 'global_mapping_not_constant_same_candidate' in roster['cells'][0]['issues']
    assert not result['complete'] and result['root_count'] == 32
