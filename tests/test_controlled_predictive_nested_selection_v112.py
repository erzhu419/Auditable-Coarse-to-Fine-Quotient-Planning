"""Whole-history source exclusion, fixed selection and reference cost roles."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import pytest
from acfqp.science import controlled_predictive_nested_selection_v112 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_nested_selection_v112.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Synthetic cached decisions and reference summaries only; no production models, fits or scoring.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def fixture():
    roots = []
    for life in m.LIVES:
        for query in m.QUERIES:
            for episode in range(8):
                cost = life * 10 + episode
                pair_deltas = {option: [[0., 0., 0.] for _ in range(32)] for option in m.OPTIONS[1:]}
                pair_deltas['SPACE_1'] = [[1., float(query == 'risk_goal'), 0.] for _ in range(32)]
                roots.append(dict(root_id=f'{life}_{query}_{episode}', life=life, query=query, episode=episode,
                    reference_complete=True, reference_log=dict(censored_root=False, trajectories=160,
                        pair_deltas=pair_deltas, ground_work=dict(sampled_transitions=cost, ground_swipe_calls=cost * 3),
                        planning_counts=dict(model_spawn_samples=cost * 7), outcomes=dict(LOST=160))))
    decisions = []
    for pair in combinations(m.LIVES, 2):
        for root in roots:
            if root['life'] in pair:
                continue
            for hidden in m.WIDTHS:
                for stage in m.STAGES:
                    chosen = 'H2' if stage == 'HALF' else 'SPACE_1' if hidden == 4 else 'SNAKE_1'
                    event = dict(option=chosen, value=float(chosen != 'H2'), score_semantics='rank_score',
                        predictions={option: dict(value=float(option == chosen and option != 'H2')) for option in m.OPTIONS})
                    decisions.append(dict(pair_id='_'.join(map(str, pair)), root_id=root['root_id'],
                        validation_life=root['life'], method=f'POOLED_H{hidden}_{stage}', event=event))
    return roots, decisions


def select(decisions, roots):
    rows, log = m.select_updates(decisions, roots, m.LIVES, m.WIDTHS)
    WORK.update(log['counts']); WORK.update(selection_calls=1)
    return rows, log


def test_outer_reference_perturbation_cannot_change_its_selection():
    roots, decisions = fixture(); changed = deepcopy(roots)
    for root in changed:
        if root['life'] == 11:
            root['reference_log']['pair_deltas']['SPACE_1'] = [[-100., 1., 0.] for _ in range(32)]
    first, _ = select(decisions, roots)
    altered, _ = select(decisions, changed)
    assert [r for r in first if r['heldout_life'] == 11] == [r for r in altered if r['heldout_life'] == 11]
    assert [r for r in first if r['heldout_life'] == 12] != [r for r in altered if r['heldout_life'] == 12]


def test_queries_ties_and_two_train_one_validation_are_preserved():
    roots, decisions = fixture(); rows, log = select(decisions, roots)
    assert len(rows) == 16 and len(decisions) == 768
    for row in rows:
        wanted = 'FULL' if row['hidden'] == 4 and row['query'] == 'reward' else 'HALF'
        assert row['chosen_stage'] == wanted
        assert row['chosen_method'] == f"POOLED_H{row['hidden']}_{wanted}"
        assert row['mean_utility_delta'] == (1. if row['query'] == 'reward' else -3.) if row['hidden'] == 4 else row['mean_utility_delta'] == 0.
        others = set(m.LIVES) - {row['heldout_life']}
        assert set(row['source_lives']) == others
        assert {fold['validation_life'] for fold in row['validation_folds']} == others
        for fold in row['validation_folds']:
            assert len(fold['source_lives']) == 2
            assert set(fold['source_lives']) == others - {fold['validation_life']}
            assert fold['pair_id'] == '_'.join(map(str, sorted(fold['source_lives'])))
            assert len(fold['root_ids']) == 8
            assert all(root_id.startswith(str(fold['validation_life']) + '_' + row['query'] + '_')
                for root_id in fold['root_ids'])
    assert log['counts']['root_comparisons'] == 384
    assert log['counts']['cached_decision_lookups'] == 768
    assert log['counts']['neural_candidate_predictions'] == 0 and all(log['checks'].values())


def test_validation_history_cannot_be_used_in_its_training_pair():
    roots, decisions = fixture(); changed = deepcopy(decisions)
    changed[0]['pair_id'] = '11_13'
    assert changed[0]['validation_life'] == 13
    with pytest.raises(ValueError, match='two-train one-validation roster'):
        m.select_updates(changed, roots, m.LIVES, m.WIDTHS)


def test_missing_decision_root_or_reference_never_shrinks_cohort():
    roots, decisions = fixture()
    with pytest.raises(ValueError, match='complete inner decision roster'):
        m.select_updates(decisions[:-1], roots, m.LIVES, m.WIDTHS)
    with pytest.raises(ValueError, match='complete frozen root cohort'):
        m.select_updates(decisions, roots[:-1], m.LIVES, m.WIDTHS)
    changed = deepcopy(roots)
    changed[0]['reference_log']['pair_deltas']['SPACE_1'].pop()
    with pytest.raises(ValueError, match='all 32 complete paired reference replicas'):
        m.select_updates(decisions, changed, m.LIVES, m.WIDTHS)


def test_reference_cost_is_unique_and_source_validation_is_charged():
    roots, _ = fixture()
    acquisition = dict(per_history=[dict(life=life, half_transitions=256000, full_transitions=512000)
        for life in m.LIVES])
    result = m.selection_acquisition_accounting(roots, acquisition, m.LIVES)
    WORK.update(cost_accounting_calls=1)
    unique = result['unique_physical']; reference = unique['reference_work']
    expected = sum(root['reference_log']['ground_work']['sampled_transitions'] for root in roots)
    assert unique['training_environment_transitions'] == 2048000
    assert reference['roots'] == 64 and reference['trajectories'] == 10240
    assert reference['sampled_transitions'] == expected
    assert reference['ground_work']['ground_swipe_calls'] == expected * 3
    assert reference['planning_counts']['model_spawn_samples'] == expected * 7
    assert unique['training_plus_reference_environment_transitions'] == 2048000 + expected
    for fold in result['per_fold']:
        source, outer = fold['selection_validation_work'], fold['outer_evaluation_work']
        assert fold['source_training_transitions'] == fold['full_baseline_training_transitions'] == 1536000
        assert fold['half_baseline_training_transitions'] == 768000
        assert source['roots'] == 48 and source['trajectories'] == 7680
        assert outer['roots'] == 16 and outer['trajectories'] == 2560
        assert source['sampled_transitions'] + outer['sampled_transitions'] == expected
        assert fold['learning_validation_environment_transitions'] == 1536000 + source['sampled_transitions']
        assert fold['outer_evaluation_environment_transitions'] == outer['sampled_transitions']
    assert result['newly_sampled_environment_transitions'] == 0 and all(result['checks'].values())
