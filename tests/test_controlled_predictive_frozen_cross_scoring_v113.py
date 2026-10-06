"""Frozen source model and choice binding on reference-free new roots."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_frozen_cross_scoring_v113 as m
from acfqp.science.controlled_predictive_capacity_ranking_v103 import initialize

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_frozen_cross_scoring_v113.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Synthetic serialized models and target features; no production payloads, training or environment sampling.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    folder = tmp_path_factory.mktemp('v113_models')
    source = dict(status='complete', settings=dict(lifecycles=list(m.BUNDLES), widths=list(m.WIDTHS),
        feature_dim=121, optimizer_steps=1000, learning_rate=m.RATE, l2_coefficient=m.L2_COEFFICIENT,
        l2_reference_parameters=m.L2_REFERENCE_PARAMETERS, initialization_seed=m.SEED),
        inherited_folds=[], models=[], selections=[])
    for bundle in m.BUNDLES:
        sources = [life for life in m.BUNDLES if life != bundle]
        half = [[life, query, 0] for life in sources for query in m.QUERIES]
        full = half + [[life, query, 1] for life in sources for query in m.QUERIES]
        fold = dict(heldout_life=bundle, source_lives=sources,
            data_log=dict(half=dict(training_roster=half), full=dict(training_roster=full)),
            fit_logs={}, model_metadata={})
        for width in m.WIDTHS:
            for stage, checkpoint in zip(m.STAGES, (256000, 512000)):
                method = f'POOLED_H{width}_{stage}'
                training = half if stage == 'HALF' else full
                parameters = [p + (.01 if stage == 'FULL' else 0.) for p in initialize(121, width)]
                model = m.CandidateModel(parameters, np.zeros(121), np.ones(121), checkpoint,
                    'UNIFORM_SHRINK', m._episodes(training), .3, 1000)
                payload = model.to_payload()
                payload['update'] = dict(heldout_life=bundle, source_lives=sources, stage=stage,
                    training_roster=training, statistics_roster=half, optimizer_state='reset_zero_moments',
                    new_optimizer_steps=1000, inherited_parameter_steps=0 if stage == 'HALF' else 1000,
                    parameter_lineage_steps=1000 if stage == 'HALF' else 2000)
                path = folder / f'{bundle}_{method}.json'
                path.write_text(json.dumps(payload))
                metadata = dict(heldout_life=bundle, source_lives=sources, hidden=width, stage=stage,
                    family='UNIFORM_SHRINK', checkpoint=checkpoint, budget=checkpoint, episode_cutoff=checkpoint,
                    parameter_count=123 * width, path=str(path))
                fold['fit_logs'][method] = dict(training_roster=training, statistics_roster=half, uniform_gamma=.3)
                fold['model_metadata'][method] = metadata
                source['models'].append(dict(heldout_life=bundle, method=method, metadata=metadata))
            for query in m.QUERIES:
                stage = 'FULL' if (width == 4) == (query == 'reward') else 'HALF'
                source['selections'].append(dict(heldout_life=bundle, hidden=width, query=query,
                    source_lives=sources, chosen_stage=stage, chosen_method=f'POOLED_H{width}_{stage}'))
        source['inherited_folds'].append(fold)
    rng = np.random.default_rng(113)
    roots = [dict(root_id=f'{life}_{query}_{episode}', life=life, query=query, episode=episode,
        features=rng.normal(size=(5, 121)).tolist()) for life in m.TARGETS for query in m.QUERIES for episode in range(8)]
    return source, roots


@pytest.fixture(scope='module')
def baseline(fixture):
    result = m.score_frozen_models(*fixture)
    WORK.update(result[2]['counts']); WORK.update(scoring_calls=1)
    return result


def test_full_cross_counts_and_exact_query_frozen_derivation(fixture, baseline):
    source, roots = fixture; models, decisions, log = baseline
    assert len(models) == 16 and len(decisions) == 1536
    assert log['counts']['model_root_scores'] == 1024
    assert log['counts']['neural_candidate_predictions'] == 5120
    assert log['counts']['neural_hidden_activations'] == 51200
    assert log['counts']['derived_decisions'] == log['counts']['cached_decision_lookups'] == 512
    assert all(log['checks'].values())
    learned = {(r['bundle_id'], r['root_id'], r['method']): r['event'] for r in decisions if r['method'] in m.METHODS}
    root_index = {r['root_id']: r for r in roots}
    choices = {(r['heldout_life'], r['hidden'], r['query']): r for r in source['selections']}
    paths = {(r['heldout_life'], r['method']): r['metadata']['path'] for r in source['models']}
    for row in decisions:
        assert row['target_life'] in m.TARGETS and row['bundle_id'] in m.BUNDLES
        if row['method'].startswith('SELECTED_'):
            width = int(row['method'].split('H')[1])
            choice = choices[row['bundle_id'], width, root_index[row['root_id']]['query']]
            assert row['chosen_method'] == choice['chosen_method']
            assert row['chosen_model_path'] == paths[row['bundle_id'], row['chosen_method']]
            actual = learned[row['bundle_id'], row['root_id'], row['chosen_method']]
            assert row['event'] == actual and row['event'] is not actual
    assert models[0]['metadata'] == source['models'][0]['metadata']
    assert models[0]['metadata'] is not source['models'][0]['metadata']


def test_new_references_absent_or_perturbed_cannot_change_scores_or_choices(fixture, baseline):
    source, roots = fixture; changed = deepcopy(roots); saved = deepcopy(source)
    for root in changed:
        root['reference_log'] = {'pair_deltas': 'unusable values must never be read'}
        root['reference_complete'] = False
    actual = m.score_frozen_models(source, changed)
    WORK.update(actual[2]['counts']); WORK.update(scoring_calls=1)
    assert actual[:2] == baseline[:2]
    assert actual[2]['choices_binding'] == baseline[2]['choices_binding']
    assert source == saved


def test_payload_roster_cannot_add_target_history(fixture, tmp_path):
    source, roots = fixture; changed = deepcopy(source)
    row = changed['models'][0]; bundle, method = row['heldout_life'], row['method']
    payload = json.loads(Path(row['metadata']['path']).read_text())
    payload['update']['training_roster'][0][0] = 15
    path = tmp_path / 'wrong_source.json'; path.write_text(json.dumps(payload))
    row['metadata']['path'] = str(path)
    fold = next(f for f in changed['inherited_folds'] if f['heldout_life'] == bundle)
    fold['model_metadata'][method]['path'] = str(path)
    with pytest.raises(ValueError, match='frozen payload differs'):
        m.score_frozen_models(changed, roots)
    WORK.update(model_payloads_loaded=1, rejected_payload_loads=1)


def test_changed_choice_missing_roots_and_changed_recipe_are_rejected(fixture):
    source, roots = fixture; changed = deepcopy(source)
    changed['selections'][0]['chosen_method'] = 'POOLED_H4_HALF'
    assert changed['selections'][0]['chosen_stage'] == 'FULL'
    with pytest.raises(ValueError, match='retained choice differs'):
        m.score_frozen_models(changed, roots)
    with pytest.raises(ValueError, match='all 64 new target roots'):
        m.score_frozen_models(source, roots[:-1])
    changed = deepcopy(source); changed['settings']['learning_rate'] *= 2
    with pytest.raises(ValueError, match='unchanged V112 source recipe'):
        m.score_frozen_models(changed, roots)
