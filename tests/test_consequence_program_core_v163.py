"""Executable-vector mapping fits, full-roster weighting, ties and incomplete data."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_consequence_program_v163 import (
    build_program, learn_programs as _learn_programs, mapping_from_code)
from acfqp.science.controlled_predictive_policy_modules_v151 import utility

TEMP = Path(__file__).resolve().parents[1]/'reports/v163_runtime_tmp'
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
        scope='Synthetic complete terminal-vector fixtures; tests perform no physical/native/model sampling or neural fitting.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def candidate(candidate_id='P0'):
    return dict(candidate_id=candidate_id, first_action='UP', probe_action='LEFT',
                fixed_suffix=['LEFT', 'RIGHT', 'DOWN'], true_suffix=['LEFT', 'UP', 'RIGHT'],
                false_suffix=['RIGHT', 'DOWN', 'LEFT'], occurrences=20,
                condition_counts=dict(true=10, false=10))


def fixture(query='risk1', candidates=None, resolver=None):
    candidates = [candidate()] if candidates is None else candidates
    roots = [dict(root_id=f'{life}:{query}:{slot}', life=life, query=query, slot=slot)
             for life in range(3) for slot in range(4)]
    rows = []
    for root in roots:
        for suffix in range(4):
            predicate = suffix % 2 == 0
            baseline = [0., 1., 0.]
            if resolver is None:
                a, b = ([6., 1., 0.], [0., 0., 1.]) if predicate else ([0., 0., 1.], [6., 1., 0.])
            else:
                predicate, a, b, baseline = resolver(root, suffix)
            vectors = [('H2', baseline, None)]+[(p['candidate_id']+'_'+arm, vector, predicate)
                for p in candidates for arm, vector in (('A', a), ('B', b))]
            for mode, vector, observed in vectors:
                rows.append(dict(heldout_life=3, root_id=root['root_id'], life=root['life'],
                    query=query, suffix=suffix, mode=mode, seed=10+suffix,
                    components=vector, status='WON' if vector[2] else 'LOST',
                    utility=utility(vector, query), module=dict(predicate=observed)))
    return [dict(heldout_life=3, query=query, candidates=candidates)], roots, rows


def learn_programs(cells, roots, rows):
    WORK.update(learning_calls=1, synthetic_outcome_rows_supplied=len(rows))
    result = _learn_programs(cells, roots, rows)
    for cell in result:
        WORK.update(cell['learning_counts'])
    return result


def score(cell, code, index=0):
    return next(row for row in cell['candidate_scores'][index]['mapping_scores'] if row['mapping_code'] == code)


def test_build_program_copies_whole_suffixes_and_preserves_probe_and_fixed_twin():
    original = candidate(); before = deepcopy(original)
    for code in ('AA', 'AB', 'BA', 'BB'):
        program = build_program(original, mapping_from_code(code))
        suffixes = {'A': original['true_suffix'], 'B': original['false_suffix']}
        assert program['true_suffix'] == suffixes[code[0]]
        assert program['false_suffix'] == suffixes[code[1]]
        assert program['first_action'] == original['first_action']
        assert program['probe_action'] == original['probe_action']
        assert program['fixed_suffix'] == original['fixed_suffix']
        program['true_suffix'][0] = 'DOWN'
        assert original == before


def test_same_realizable_consequence_vectors_choose_opposite_query_maps():
    risk1 = learn_programs(*fixture('risk1'))[0]
    risk8 = learn_programs(*fixture('risk8'))[0]
    assert risk1['complete'] and risk8['complete']
    assert risk1['candidate_scores'][0]['learned_mapping'] == 'AB'
    assert risk8['candidate_scores'][0]['learned_mapping'] == 'BA'
    assert risk1['programs']['LEARNED']['train_gain'] == 6.
    assert risk8['programs']['LEARNED']['train_gain'] == 16.
    assert risk1['programs']['GLOBAL']['mapping'] == mapping_from_code('AA')
    assert risk8['programs']['GLOBAL']['mapping'] == mapping_from_code('AA')
    assert risk1['programs']['LEARNED']['train_gain']-risk1['programs']['GLOBAL']['train_gain'] == 2.
    assert risk8['programs']['LEARNED']['train_gain']-risk8['programs']['GLOBAL']['train_gain'] == 5.


def test_modal_mapping_selects_actual_terminal_vectors_without_componentwise_optimism():
    cell = learn_programs(*fixture('risk8'))[0]
    modal = score(cell, 'AB'); learned = score(cell, 'BA')
    assert modal['component_delta'] == [6., 0., 0.] and modal['train_gain'] == 6.
    assert learned['component_delta'] == [0., -1., 1.] and learned['train_gain'] == 16.
    assert cell['programs']['MODAL']['program'] == candidate()
    assert cell['programs']['MATCH_MODAL']['mapping'] == mapping_from_code('AB')
    assert cell['programs']['FIXED'] == dict(candidate_id='P0', mapping=None, program=candidate(), train_gain=None)
    assert cell['learning_counts'] == dict(weight_updates=0, candidate_pairs_examined=48,
        mapping_vector_selections=192, mapping_root_means=48, mapping_history_means=12,
        mapping_scores=4, learned_branch_tables=1)


def test_full_roster_weighting_preserves_rare_predicate_probability():
    def resolver(root, suffix):
        predicate = root['slot'] == 0 or (root['slot'] == 1 and suffix == 0)
        reward = 6. if root['slot'] == 0 else 1. if predicate else 4.
        return predicate, [reward, 1., 0.], [4., 1., 0.], [0., 1., 0.]
    cell = learn_programs(*fixture(resolver=resolver))[0]
    assert cell['candidate_scores'][0]['learned_mapping'] == 'AA'
    assert score(cell, 'AA')['train_gain']-score(cell, 'BA')['train_gain'] == .3125
    assert cell['candidate_scores'][0]['condition_counts'] == dict(true=15, false=33, none=0)


def test_none_noop_rows_keep_full_weight_and_support_need_not_exist_in_each_history():
    def resolver(root, suffix):
        if root['life'] == 0 and root['slot'] == 0 and suffix == 0:
            return True, [7., 1., 0.], [0., 1., 0.], [0., 1., 0.]
        if root['life'] == 0 and root['slot'] == 0 and suffix == 1:
            return False, [0., 1., 0.], [8., 1., 0.], [0., 1., 0.]
        return None, [6., 1., 0.], [6., 1., 0.], [0., 1., 0.]
    cell = learn_programs(*fixture(resolver=resolver))[0]
    assert cell['complete'] and cell['candidate_scores'][0]['learned_mapping'] == 'AB'
    assert cell['candidate_scores'][0]['condition_counts'] == dict(true=1, false=1, none=46)
    assert score(cell, 'AB')['train_gain'] == pytest.approx(291/48)


def test_negative_winner_and_mapping_and_candidate_ties_remain_selected():
    def resolver(root, suffix):
        return suffix % 2 == 0, [1., 1., 0.], [1., 1., 0.], [4., 1., 0.]
    cell = learn_programs(*fixture(candidates=[candidate('P0'), candidate('P1')], resolver=resolver))[0]
    assert cell['complete']
    assert all(row['learned_mapping'] == row['global_mapping'] == 'AA' for row in cell['candidate_scores'])
    assert cell['programs']['MODAL']['candidate_id'] == cell['programs']['LEARNED']['candidate_id'] == 'P0'
    assert cell['programs']['LEARNED']['train_gain'] == -3.
    assert cell['programs']['LEARNED']['mapping'] == mapping_from_code('AA')


def test_mapping_change_and_candidate_selection_have_separate_matched_controls():
    cells, roots, rows = fixture(candidates=[candidate('P0'), candidate('P1')])
    for row in rows:
        if row['mode'] == 'P0_A': row['components'] = [4., 1., 0.]
        if row['mode'] == 'P0_B': row['components'] = [4., 1., 0.]
        if row['mode'] == 'P1_A': row['components'] = [0. if row['module']['predicate'] else 10., 1., 0.]
        if row['mode'] == 'P1_B': row['components'] = [10. if row['module']['predicate'] else 0., 1., 0.]
        row['status'] = 'LOST'; row['utility'] = utility(row['components'], row['query'])
    cell = learn_programs(cells, roots, rows)[0]
    assert cell['programs']['MODAL']['candidate_id'] == 'P0'
    assert cell['programs']['LEARNED']['candidate_id'] == 'P1'
    assert cell['programs']['LEARNED']['mapping'] == mapping_from_code('BA')
    assert cell['programs']['MATCH_MODAL']['candidate_id'] == cell['programs']['GLOBAL']['candidate_id'] == 'P1'
    assert cell['programs']['MATCH_MODAL']['train_gain'] == 0.
    assert cell['programs']['GLOBAL']['train_gain'] == 5.


@pytest.mark.parametrize('problem,issue', [
    ('missing', 'missing_pair'), ('cutoff', 'nonterminal_pair'),
    ('predicate', 'predicate_mismatch'), ('none', 'none_outcome_mismatch'),
    ('support', 'predicate_support'), ('root', 'root_roster')])
def test_incomplete_candidate_stops_fold_without_selecting_around_it(problem, issue):
    cells, roots, rows = fixture(candidates=[candidate('P0'), candidate('P1')])
    row = next(row for row in rows if row['mode'] == 'P1_B')
    if problem == 'missing': rows.remove(row)
    elif problem == 'cutoff': row.update(status='CUTOFF', utility=None)
    elif problem == 'predicate': row['module']['predicate'] = False
    elif problem == 'none':
        row['module']['predicate'] = None
        next(a for a in rows if a['root_id'] == row['root_id'] and a['suffix'] == row['suffix'] and a['mode'] == 'P1_A')['module']['predicate'] = None
    elif problem == 'support':
        for item in rows:
            if item['mode'].startswith('P1_'): item['module']['predicate'] = True
    else: roots.pop()
    cell = learn_programs(cells, roots, rows)[0]
    assert not cell['complete'] and cell['programs'] == {}
    assert issue in cell['candidate_scores'][1]['issues']
    assert 'learned_branch_tables' not in cell['learning_counts']
    assert cell['learning_counts']['candidate_pairs_examined'] == (88 if problem == 'root' else 96)


def test_heldout_roots_and_other_fold_outcomes_are_excluded_before_fields():
    cells, roots, rows = fixture()
    roots += [dict(life=3, query='risk1'), dict(life=0, query='risk8')]
    rows += [dict(heldout_life=0, query='risk1'), dict(heldout_life=3, query='risk8')]
    cell = learn_programs(cells, roots, rows)[0]
    assert cell['complete'] and cell['train_lives'] == [0, 1, 2]
    assert cell['learning_counts']['candidate_pairs_examined'] == 48


def test_empty_source_candidate_is_incomplete_without_dummy_program_or_work():
    cell = learn_programs(*fixture(candidates=[]))[0]
    assert not cell['complete'] and cell['programs'] == {} and cell['candidate_scores'] == []
    assert cell['learning_counts'] == dict(weight_updates=0)
