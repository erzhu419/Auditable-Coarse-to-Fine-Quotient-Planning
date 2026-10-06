"""Migrated frozen parameters, source-only validation and unchanged selection rule."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_direct_validation_v114 as m
from acfqp.science.controlled_predictive_capacity_ranking_v103 import initialize
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_direct_validation_v114.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Synthetic migrated model payloads, features and references; no production scoring, fit or sampling.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    root_dir = tmp_path_factory.mktemp('v114_migrated')
    old_root = Path('/retired/acfqp_v114_test')
    source = dict(status='complete', source=str(old_root / 'reports/pooled_history'),
        settings=dict(lifecycles=list(m.BUNDLES), widths=list(m.WIDTHS), feature_dim=121,
            optimizer_steps=1000, learning_rate=m.RATE, l2_coefficient=m.L2_COEFFICIENT,
            l2_reference_parameters=m.L2_REFERENCE_PARAMETERS, initialization_seed=m.SEED),
        inherited_folds=[], models=[])
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
                relative = Path('reports/pooled_history') / f'{bundle}_{method}.json'
                disk = root_dir / relative; disk.parent.mkdir(parents=True, exist_ok=True)
                disk.write_text(json.dumps(payload))
                metadata = dict(heldout_life=bundle, source_lives=sources, hidden=width, stage=stage,
                    family='UNIFORM_SHRINK', checkpoint=checkpoint, budget=checkpoint, episode_cutoff=checkpoint,
                    parameter_count=123 * width, path=str(old_root / relative))
                fold['fit_logs'][method] = dict(training_roster=training, statistics_roster=half, uniform_gamma=.3)
                fold['model_metadata'][method] = metadata
                source['models'].append(dict(heldout_life=bundle, method=method, metadata=metadata))
        source['inherited_folds'].append(fold)
    rng = np.random.default_rng(114)
    roots = []
    for life in m.BUNDLES:
        for query in m.QUERIES:
            for episode in range(8):
                deltas = {option: [[0., 0., 0.] for _ in range(32)] for option in OPTIONS[1:]}
                deltas['SPACE_1'] = [[1., float(query == 'risk_goal'), 0.] for _ in range(32)]
                roots.append(dict(root_id=f'{life}_{query}_{episode}', life=life, query=query, episode=episode,
                    features=rng.normal(size=(5, 121)).tolist(), reference_complete=True,
                    reference_log=dict(pair_deltas=deltas, censored_root=False, trajectories=160)))
    return source, roots, root_dir


@pytest.fixture(scope='module')
def baseline(fixture):
    source, roots, root_dir = fixture
    result = m.score_source_models(source, roots, root_dir)
    WORK.update(result[1]['counts']); WORK.update(scoring_calls=1)
    return result


def select(rows, roots):
    selections, log = m.select_updates(rows, roots)
    WORK.update(log['counts']); WORK.update(selection_calls=1)
    return selections, log


def controlled_decisions(rows):
    result = deepcopy(rows)
    for row in result:
        chosen = 'SPACE_1' if row['method'] == 'POOLED_H4_FULL' else 'H2'
        row['event'] = dict(option=chosen, value=float(chosen != 'H2'), score_semantics='rank_score',
            predictions={option: dict(value=float(option == chosen and option != 'H2')) for option in OPTIONS})
    return result


def test_migrated_original_parameters_source_roster_and_real_counts(fixture, baseline):
    source, roots, root_dir = fixture; decisions, log = baseline
    assert len(decisions) == 768 and all(r['bundle_id'] != r['validation_life'] for r in decisions)
    assert log['counts']['model_payloads_loaded'] == 16
    assert log['counts']['model_root_scores'] == 768
    assert log['counts']['neural_candidate_predictions'] == 3840
    assert log['counts']['neural_hidden_activations'] == 38400
    assert log['validation_source_models'] == 'three_source_deployment' and all(log['checks'].values())
    for binding in log['model_bindings']:
        retained = binding['retained_model_path']
        assert retained.startswith('/retired/acfqp_v114_test/')
        assert Path(binding['loaded_model_path']).is_relative_to(root_dir)
        row = next(r for r in source['models'] if r['heldout_life'] == binding['bundle_id'] and r['method'] == binding['method'])
        assert row['metadata']['path'] == retained
    first = decisions[0]
    features = np.asarray(next(r['features'] for r in roots if r['root_id'] == first['root_id']))
    w, b, v = initialize(121, 4)
    scores = np.tanh(features @ w + b) @ v
    expected = m._event((scores - scores[0]).tolist())
    WORK.update(neural_candidate_predictions=5, neural_hidden_activations=20, numeric_oracle_root_scores=1)
    assert first['event'] == expected


def test_scoring_never_reads_references_or_excluded_bundle_features(fixture, baseline):
    source, roots, root_dir = fixture; changed = deepcopy(roots); saved = deepcopy(source)
    for root in changed:
        root.pop('reference_log'); root.pop('reference_complete')
        if root['life'] == 11:
            root['features'] = (np.asarray(root['features']) * -1000).tolist()
    actual, log = m.score_source_models(source, changed, root_dir)
    WORK.update(log['counts']); WORK.update(scoring_calls=1)
    assert [r for r in actual if r['bundle_id'] == 11] == [r for r in baseline[0] if r['bundle_id'] == 11]
    assert source == saved


def test_excluded_history_labels_cannot_change_its_query_selection(fixture, baseline):
    _, roots, _ = fixture; decisions = controlled_decisions(baseline[0]); changed = deepcopy(roots)
    for root in changed:
        if root['life'] == 11:
            root['reference_log']['pair_deltas']['SPACE_1'] = [[-100., 1., 0.] for _ in range(32)]
    before, _ = select(decisions, roots); after, _ = select(decisions, changed)
    assert [r for r in before if r['heldout_life'] == 11] == [r for r in after if r['heldout_life'] == 11]
    assert [r for r in before if r['heldout_life'] == 12] != [r for r in after if r['heldout_life'] == 12]


def test_direct_three_source_selection_query_ties_and_rosters(fixture, baseline):
    _, roots, _ = fixture; decisions = controlled_decisions(baseline[0]); rows, log = select(decisions, roots)
    assert log['validation_source_models'] == 'three_source_deployment'
    assert len(rows) == 16 and log['counts']['root_comparisons'] == 384
    assert log['counts']['cached_decision_lookups'] == 768
    for row in rows:
        expected = 'FULL' if row['hidden'] == 4 and row['query'] == 'reward' else 'HALF'
        assert row['chosen_stage'] == expected
        if row['hidden'] == 16:
            assert row['mean_utility_delta'] == 0.
        for fold in row['validation_folds']:
            assert 'pair_id' not in fold and fold['source_lives'] == row['source_lives']
            assert fold['validation_life'] in row['source_lives'] and len(fold['root_ids']) == 8
    with pytest.raises(ValueError, match='complete direct source decision roster'):
        m.select_updates(decisions[:-1], roots)
    with pytest.raises(ValueError, match='complete frozen root cohort'):
        m.select_updates(decisions, roots[:-1])
