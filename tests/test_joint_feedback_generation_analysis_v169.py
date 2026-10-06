"""Independent source labels, paid conditional vectors and fixed-root uncertainty."""
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_joint_feedback_generation_v169 as audit
from acfqp.science import controlled_predictive_joint_feedback_generation_v169 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from test_joint_feedback_generation_core_v169 import program, source_game, selection_fixture, eval_fixture


def enriched_selection(phase='G1', **kwargs):
    cells, roots, rows = selection_fixture(phase, **kwargs)
    for row in rows:
        module = row['module']
        candidate = module['program']
        observed = module['predicate'] is not None
        module.update(actual_word=[] if candidate is None else [candidate['first_action']]+(candidate['true_suffix'] if observed else []),
                      prefix_steps=0 if candidate is None else 4 if observed else 0,
                      attempts=0 if candidate is None else 4 if observed else 1,
                      exit_reason='baseline' if candidate is None else 'budget' if observed else 'illegal',
                      exit_step=0 if not observed else 4)
    return cells, roots, rows


def test_ground_source_labels_counts_and_roster_match_learned_generator():
    rows = [source_game(life, replica) for life in range(4) for replica in range(4)]
    for row in rows: row['result']['steps'] = len(row['actions'])
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'), ((1, .9), (2, .1)), 'uniform')
    independent = audit.source_candidates(rows)
    for heldout in range(4):
        actual = core.source_candidates(rows, {life: rule for life in range(4) if life != heldout}, heldout)
        assert audit._equal(actual, independent[heldout])
        assert independent[heldout]['counts']['source_state_reconstructions'] == 96
        assert independent[heldout]['counts']['fragment_windows'] == 60
        assert independent[heldout]['counts']['source_games'] == 12
    removed = audit.source_candidates(rows[:-1])
    assert not removed[0]['complete'] and 'source_game_roster' in removed[0]['issues']


def test_independent_eight_gene_mutation_roster_and_arm_binding():
    parents = [program('DOWN'), program('LEFT')]
    before = deepcopy(parents)
    assert audit.mutations(parents) == core.mutate(parents)
    assert len(audit.mutations(parents)) == 50
    assert audit.mutations(parents)[1]['program'] == audit.mutations(parents)[2]['program']
    assert audit.executable(parents[0], 'B') == core.executable(parents[0], 'B')
    assert parents == before


def test_independent_conditional_selection_and_best_same_candidate_twin():
    for phase in ('G1', 'G2', 'FINAL'):
        cells, roots, rows = enriched_selection(phase,
            resolver=lambda root, suffix, candidate, arm, observed:
                [10. if candidate['candidate_slot'] == (1 if phase == 'FINAL' else 2) and (arm == 'A') == observed else 1., 1., 0.])
        independent = audit.select_parents(cells, roots, rows)
        assert audit._equal(core.choose_parents(cells, roots, rows, phase), independent)
        assert independent[0]['selected_slots'][0] == (1 if phase == 'FINAL' else 2)
        assert independent[0]['slot_scores'][independent[0]['selected_slots'][0]]['train_component_mean'] == [10., 1., 0.]
        if phase == 'FINAL': assert independent[0]['selected_twin'] == 'A'


@pytest.mark.parametrize('corruption', ['seed', 'duplicate', 'predicate', 'unobserved_path'])
def test_bad_unselected_paid_pair_blocks_all_selection(corruption):
    cells, roots, rows = enriched_selection(predicate=lambda root, suffix: None)
    row = next(row for row in rows if row['mode'] == 'P49_B')
    if corruption == 'seed': row['seed'] += 1
    elif corruption == 'duplicate': rows.append(deepcopy(row))
    elif corruption == 'predicate': row['module']['predicate'] = False
    else: row['module']['exit_reason'] = 'terminal'
    independent = audit.select_parents(cells, roots, rows)[0]
    assert not independent['complete'] and independent['selected_parents'] == []
    assert len(independent['slot_scores']) == 50 and not independent['slot_scores'][49]['complete']


def test_absent_false_support_and_negative_winners_are_kept():
    cells, roots, rows = enriched_selection(predicate=lambda root, suffix: True,
        resolver=lambda root, suffix, candidate, arm, observed: [1., 1., 0.])
    for row in rows:
        if row['mode'] == 'H2': row.update(score=10.*2048., components=[10., 1., 0.], utility=9.)
    independent = audit.select_parents(cells, roots, rows)[0]
    assert audit._equal(core.choose_parents(cells, roots, rows, 'G1')[0], independent)
    assert independent['complete'] and all(score['train_gain'] == -9. for score in independent['slot_scores'])
    assert independent['slot_scores'][0]['predicate_counts'] == {'true': 12}


def test_independent_eval_ci_and_actual_feedback_exposure():
    roots, rows = eval_fixture()
    independent = audit.eval_summary(roots, rows)
    assert audit._equal(core.summarize_eval(roots, rows), independent)
    stats = independent['comparisons'][0]['metrics']['utility']
    assert stats['mean'] == 44. and stats['mean_variance'] == pytest.approx(1.59375)
    assert independent['feedback_diagnostics'] == dict(predicate_observed_branches=512, suffixes_differ_from_twin=256, roots_with_both_predicates=32)
    rows[0].update(status='CUTOFF', utility=None)
    incomplete = audit.eval_summary(roots, rows)
    assert not incomplete['complete'] and len(incomplete['root_rows']) == 32
    assert all(row['metrics']['utility']['mean'] is None for row in incomplete['comparisons'])
