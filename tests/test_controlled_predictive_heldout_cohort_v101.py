"""Retained heldout cohort isolation and binding; synthetic payloads, no fitting."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_heldout_cohort_v101 as module

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failures = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_heldout_cohort_v101.checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(failures=request.session.testsfailed - failures,
        prediction_work=dict(WORK), new_environment_transitions=0, new_model_transitions=0,
        new_neural_model_fits=0, new_tree_fits=0, new_optimizer_steps=0,
        scope='Synthetic retained rows and hand-constructed frozen payloads; no training or simulation.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


@pytest.fixture(autouse=True)
def count_predictions(monkeypatch):
    original = module.CandidateModel.score_candidates

    def counted(self, features, work=None):
        WORK['prediction_calls'] += 1
        WORK['neural_candidate_predictions'] += len(features)
        WORK['neural_hidden_activations'] += len(features) * 16
        return original(self, features, work)

    monkeypatch.setattr(module.CandidateModel, 'score_candidates', counted)


def save(path, value):
    path.write_text(json.dumps(value))


def rows(path, values):
    with gzip.open(path, 'wt') as handle:
        for value in values:
            handle.write(json.dumps(value) + '\n')


def row(query, episode, replicas):
    features = np.zeros((5, 121))
    features[:, 0] = np.arange(5) * .1 + episode * .001
    return dict(query=query, episode=episode, board=[episode % 7 + 1] * 10 + [0] * 6,
        features=features.tolist(), utilities=[0, replicas, -1, 2, 3],
        prefix_utilities=[0, .1, -.1, .2, .3], prefix_seed=210000000000 + episode)


def source_fixture(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    lives = []
    for life in (9, 10):
        allocations = []
        for replicas in (8, 4):
            cutoff = 11 if replicas == 8 else 16
            first = [row('reward', 3, replicas), row('risk_goal', 3, replicas), row('reward', 4, replicas)]
            last = [row('risk_goal', 4, replicas), row('reward', 8, replicas),
                    row('risk_goal', 8, replicas), row('reward', 9, replicas)]
            if replicas == 4:
                last.append(row('reward', 14, replicas))
            # Future heldout rows are present in the supplied stream but are never eligible.
            last.append(row('risk_goal', 19, replicas))
            eligible = [r for r in first + last if r['episode'] < cutoff]
            coverage = {q: {role: sorted(r['episode'] for r in eligible if r['query'] == q
                and (r['episode'] % 5 == 4) == (role == 'heldout'))
                for role in ('training', 'heldout')} for q in module.QUERIES}
            training = {q: coverage[q]['training'] for q in module.QUERIES}
            stages = []
            metadata = {}
            for budget, records in ((20, first), (40, last)):
                folder = source / f'life_{life}' / f'replicas_{replicas}' / f'budget_{budget}'
                folder.mkdir(parents=True)
                rows(folder / 'candidate_roots.jsonl.gz', records)
                stages.append(dict(budget=budget, episode_cutoff=5 if budget == 20 else cutoff,
                    cumulative_roots=coverage, fit_log=dict(training_episodes=training)))
                if budget == 40:
                    for family in module.FAMILIES:
                        weights = np.zeros((121, 16))
                        weights[0, 0] = (1 if replicas == 8 else -1) * (1 if family == 'UTILITY_MSE' else -1)
                        bias, value = np.zeros(16), np.zeros(16)
                        value[0] = 1
                        payload = module.CandidateModel([weights, bias, value], np.zeros(121),
                            np.ones(121), cutoff, family, training).to_payload()
                        path = folder / f'{family.lower()}_model.json'
                        save(path, payload)
                        metadata[f'R{replicas}_{family}_DIRECT'] = dict(path=str(path), replicas=replicas,
                            budget=40, episode_cutoff=cutoff, family=family)
            allocations.append(dict(replicas=replicas, construction=stages, model_metadata=metadata,
                inherited_training_environment_transitions=40))
        lives.append(dict(id=life, allocations=allocations))
    save(source / 'run.json', dict(status='complete', settings=dict(budgets=[20, 40]), lifecycles=lives))
    save(source / 'analysis.json', dict(complete=True, actual_executed_work=dict(new_neural_model_fits=16,
        new_optimizer_steps=16000, new_tree_fits=0, new_training_environment_transitions=0,
        newly_sampled_environment_transitions=200, new_simulated_transitions=100)))
    return source


def test_all_heldout_roots_share_references_and_use_full_age_models(tmp_path):
    source = source_fixture(tmp_path)
    cohort, log = module.load_cohort(source, tmp_path / 'output')
    assert (log['unique_roots'], log['allocated_roots'], log['shared_roots']) == (8, 14, 6)
    assert all(r['episode'] % 5 == 4 and r['episode'] != 19 for r in cohort)
    assert {r['episode'] for r in cohort} == {4, 9, 14}
    counts = log['counts']
    assert counts['model_loads'] == counts['model_copies'] == 8
    assert counts['prediction_calls'] == 28
    assert counts['neural_candidate_predictions'] == 140
    assert counts['neural_hidden_activations'] == 2240
    assert counts['new_neural_model_fits'] == counts['new_environment_transitions'] == counts['new_model_transitions'] == 0
    assert log['inherited_source_work']['inherited_training_environment_transitions'] == 160
    for root in cohort:
        for allocation in root['allocations']:
            replicas = allocation['replicas']
            for family, prediction in allocation['predictions'].items():
                sign = (1 if replicas == 8 else -1) * (1 if family == 'UTILITY_MSE' else -1)
                raw = np.tanh(sign * np.asarray(root['retained_features'])[:, 0])
                assert prediction['scores'] == pytest.approx(raw - raw[0])
                assert prediction['option'] == ('SNAKE_4' if sign > 0 else 'H2')
                metadata = allocation['model_metadata'][family]
                assert metadata['checkpoint'] == (11 if replicas == 8 else 16)
                assert metadata['training_episodes'] == {'reward': [3, 8], 'risk_goal': [3, 8]}
                assert Path(metadata['path']).read_bytes() == Path(metadata['source_path']).read_bytes()


def test_old_labels_do_not_change_retained_feature_predictions(tmp_path):
    source = source_fixture(tmp_path)
    before, _ = module.load_cohort(source, tmp_path / 'before')
    for path in source.glob('life_*/replicas_*/budget_*/candidate_roots.jsonl.gz'):
        data = module._records(path)
        for record in data:
            record['utilities'] = [0, -700, 80, -90, 1000]
        rows(path, data)
    after, _ = module.load_cohort(source, tmp_path / 'after')
    for old, new in zip(before, after):
        assert old['retained_features'] == new['retained_features']
        assert [r['predictions'] for r in old['allocations']] == [r['predictions'] for r in new['allocations']]
        assert [r['old_utilities'] for r in old['allocations']] != [r['old_utilities'] for r in new['allocations']]


@pytest.mark.parametrize('field', ['board', 'features', 'prefix_utilities', 'prefix_seed'])
def test_shared_root_mismatch_is_not_silently_deduplicated(tmp_path, field):
    source = source_fixture(tmp_path)
    path = source / 'life_9/replicas_4/budget_20/candidate_roots.jsonl.gz'
    data = module._records(path)
    record = next(r for r in data if r['episode'] == 4)
    if field == 'features':
        record[field][0][0] += 1
    elif field == 'prefix_seed':
        record[field] += 1
    else:
        record[field][0] += 1
    rows(path, data)
    with pytest.raises(ValueError, match='shared root board, features or prefix stream'):
        module.load_cohort(source, tmp_path / 'output')


@pytest.mark.parametrize('change', ['heldout_in_training', 'wrong_age', 'wrong_family', 'heldout_roster'])
def test_wrong_model_or_roster_binding_fails_before_predictions(tmp_path, change):
    source = source_fixture(tmp_path)
    path = source / 'run.json'
    run = module._read(path)
    allocation = run['lifecycles'][0]['allocations'][0]
    model_path = Path(allocation['model_metadata']['R8_UTILITY_MSE_DIRECT']['path'])
    payload = module._read(model_path)
    if change == 'heldout_in_training':
        payload['training_episodes']['reward'].append(4)
    elif change == 'wrong_age':
        payload['checkpoint'] = 5
    elif change == 'wrong_family':
        payload['family'] = 'PAIRWISE_RANK'
    else:
        allocation['construction'][-1]['cumulative_roots']['reward']['heldout'].remove(4)
    save(model_path, payload)
    save(path, run)
    previous = deepcopy(WORK)
    with pytest.raises(ValueError, match='roster|supplied full model'):
        module.load_cohort(source, tmp_path / 'output')
    assert WORK == previous
