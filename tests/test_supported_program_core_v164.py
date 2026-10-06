"""Partial identification keeps unseen source leaves distinct from terminal fits."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_supported_program_v164 import learn_programs as _learn_programs
from acfqp.science.controlled_predictive_policy_modules_v151 import utility

TEMP = Path(__file__).resolve().parents[1]/'reports/v164_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=0, real_training_updates=0, native_planner_calls=0,
        symbolic_learning_work=dict(WORK),
        scope='Synthetic terminal-vector fixtures for new support constraints; no physical/native/model sampling or neural fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def fixture(resolver, query='risk1', candidate_count=1):
    candidates = [dict(candidate_id=f'P{i}', first_action='UP', probe_action='LEFT',
        fixed_suffix=['LEFT', 'RIGHT', 'DOWN'], true_suffix=['LEFT', 'UP', 'RIGHT'],
        false_suffix=['RIGHT', 'DOWN', 'LEFT'], occurrences=20,
        condition_counts=dict(true=10, false=10)) for i in range(candidate_count)]
    roots = [dict(root_id=f'{life}:{query}:{slot}', life=life, query=query, slot=slot)
             for life in range(3) for slot in range(4)]
    rows = []
    for root in roots:
        for suffix in range(4):
            for mode in ['H2']+[f'P{i}_{arm}' for i in range(candidate_count) for arm in ('A', 'B')]:
                predicate, a, b = resolver(root, suffix, mode)
                vector = [0., 1., 0.] if mode == 'H2' else a if mode.endswith('_A') else b
                rows.append(dict(heldout_life=3, root_id=root['root_id'], life=root['life'],
                    query=query, suffix=suffix, mode=mode, seed=10+suffix,
                    components=vector, status='WON' if vector[2] else 'LOST',
                    utility=utility(vector, query), module=dict(predicate=None if mode == 'H2' else predicate)))
    return [dict(heldout_life=3, query=query, candidates=candidates)], roots, rows


def learn_programs(cells, roots, rows):
    WORK.update(learning_calls=1, synthetic_outcome_rows_supplied=len(rows))
    result = _learn_programs(cells, roots, rows)
    for cell in result: WORK.update(cell['learning_counts'])
    return result


def test_unseen_false_keeps_source_B_null_estimate_and_single_observed_global_is_defined():
    def resolver(root, suffix, mode):
        predicate = None if root['slot'] == 3 and root['life'] < 2 else True
        return (predicate, [4., 1., 0.], [4., 1., 0.]) if predicate is None else (True, [3., 1., 0.], [1., 1., 0.])
    cell = learn_programs(*fixture(resolver))[0]
    item = cell['candidate_scores'][0]
    assert cell['complete'] and not cell['all_predicates_identified']
    assert not cell['selected_program_all_predicates_identified']
    assert item['condition_counts'] == dict(true=40, false=0, none=8)
    assert item['allowed_mapping_codes'] == ['AB', 'BB'] and item['learned_mapping'] == 'AB'
    assert item['predicate_evidence']['false'] == dict(support=0, provenance='source_prior',
        component_delta_A_minus_B=None, utility_delta_A_minus_B=None,
        prior_assignment='B', allowed_assignments=['B'])
    assert item['predicate_evidence']['true']['component_delta_A_minus_B'] == pytest.approx([40/24, 0., 0.])
    assert item['predicate_evidence']['true']['provenance'] == 'terminal_estimated'
    assert cell['programs']['LEARNED']['program']['false_suffix'] == cell['programs']['FIXED']['program']['false_suffix']
    assert cell['programs']['GLOBAL']['mapping'] == dict(true='A', false='A')
    assert cell['learning_counts'] == dict(weight_updates=0, terminal_supported_assignments=1,
        retained_source_assignments=1, candidate_pairs_examined=48, evidence_vector_selections=48,
        evidence_root_means=12, evidence_history_means=3, evidence_estimates=1,
        mapping_vector_selections=192, mapping_root_means=48, mapping_history_means=12,
        mapping_scores=4, learned_branch_tables=1)


def test_unseen_true_keeps_source_A_while_observed_false_updates_and_global_can_choose_BB():
    cell = learn_programs(*fixture(lambda r, s, m: (False, [1., 1., 0.], [5., 1., 0.])))[0]
    item = cell['candidate_scores'][0]
    assert item['allowed_mapping_codes'] == ['AA', 'AB']
    assert item['learned_mapping'] == 'AB' and item['global_mapping'] == 'BB'
    assert item['predicate_evidence']['true']['prior_assignment'] == 'A'
    assert item['predicate_evidence']['true']['component_delta_A_minus_B'] is None
    assert cell['programs']['LEARNED']['program']['true_suffix'] == cell['programs']['FIXED']['program']['true_suffix']
    assert cell['learning_counts']['retained_source_assignments'] == 1


def test_both_unseen_is_executable_source_AB_with_no_terminal_leaf_estimates():
    cell = learn_programs(*fixture(lambda r, s, m: (None, [4., 1., 0.], [4., 1., 0.])))[0]
    item = cell['candidate_scores'][0]
    assert cell['complete'] and not item['all_predicates_identified']
    assert item['allowed_mapping_codes'] == ['AB'] and item['learned_mapping'] == 'AB'
    assert len(item['mapping_scores']) == 4 and item['global_mapping'] == 'AA'
    assert cell['programs']['LEARNED']['program'] == cell['programs']['FIXED']['program']
    assert all(leaf['component_delta_A_minus_B'] is None and leaf['provenance'] == 'source_prior'
               for leaf in item['predicate_evidence'].values())
    assert cell['learning_counts']['retained_source_assignments'] == 2
    assert cell['learning_counts']['terminal_supported_assignments'] == 0
    assert 'evidence_vector_selections' not in cell['learning_counts']


def test_observed_terminal_vectors_update_query_specific_mapping_and_identification():
    def resolver(root, suffix, mode):
        return (True, [6., 1., 0.], [0., 0., 1.]) if suffix % 2 == 0 else (False, [0., 0., 1.], [6., 1., 0.])
    risk1 = learn_programs(*fixture(resolver, 'risk1'))[0]
    risk8 = learn_programs(*fixture(resolver, 'risk8'))[0]
    assert risk1['candidate_scores'][0]['learned_mapping'] == 'AB'
    assert risk8['candidate_scores'][0]['learned_mapping'] == 'BA'
    assert risk1['all_predicates_identified'] and risk8['selected_program_all_predicates_identified']
    assert risk1['candidate_scores'][0]['predicate_evidence']['true']['component_delta_A_minus_B'] == [3., .5, -.5]
    assert risk8['candidate_scores'][0]['predicate_evidence']['true']['utility_delta_A_minus_B'] == -5.
    assert risk1['learning_counts']['terminal_supported_assignments'] == 2
    assert risk1['learning_counts']['retained_source_assignments'] == 0


def test_cutoff_still_stops_fold_and_reports_incomplete_terminal_evidence():
    cells, roots, rows = fixture(lambda r, s, m: (True, [3., 1., 0.], [1., 1., 0.]))
    next(row for row in rows if row['mode'] == 'P0_B').update(status='CUTOFF', utility=None)
    cell = learn_programs(cells, roots, rows)[0]
    item = cell['candidate_scores'][0]
    assert not cell['complete'] and cell['programs'] == {}
    assert item['issues'] == ['nonterminal_pair']
    assert item['predicate_evidence']['true']['provenance'] == 'terminal_incomplete'
    assert item['predicate_evidence']['true']['component_delta_A_minus_B'] is None
    assert item['predicate_evidence']['false']['provenance'] == 'source_prior'
    assert item['allowed_mapping_codes'] == [] and item['mapping_scores'] == []
    assert cell['learning_counts']['terminal_supported_assignments'] == cell['learning_counts']['retained_source_assignments'] == 0


def test_indicator_weighted_evidence_preserves_rare_state_probability_and_full_vectors():
    def resolver(root, suffix, mode):
        predicate = root['slot'] == 0 or (root['slot'] == 1 and suffix == 0)
        reward = 6. if root['slot'] == 0 else 1. if predicate else 4.
        return predicate, [reward, 1., 0.], [4., 1., 0.]
    cell = learn_programs(*fixture(resolver))[0]
    item = cell['candidate_scores'][0]
    assert item['predicate_evidence']['true']['component_delta_A_minus_B'] == [.3125, 0., 0.]
    assert item['predicate_evidence']['false']['component_delta_A_minus_B'] == [0., 0., 0.]
    assert item['learned_mapping'] == 'AA'
    assert item['predicate_evidence']['false']['provenance'] == 'terminal_estimated'
    assert item['predicate_evidence']['false']['support'] == 33


def test_selected_program_identification_is_separate_from_other_partial_candidates():
    def resolver(root, suffix, mode):
        if mode.startswith('P0_'):
            return True, [1., 1., 0.], [0., 1., 0.]
        return (True, [6., 1., 0.], [0., 1., 0.]) if suffix % 2 == 0 else (False, [0., 1., 0.], [6., 1., 0.])
    cell = learn_programs(*fixture(resolver, candidate_count=2))[0]
    assert cell['complete'] and not cell['all_predicates_identified']
    assert cell['programs']['LEARNED']['candidate_id'] == 'P1'
    assert cell['selected_program_all_predicates_identified']
    assert cell['learning_counts']['terminal_supported_assignments'] == 3
    assert cell['learning_counts']['retained_source_assignments'] == 1
