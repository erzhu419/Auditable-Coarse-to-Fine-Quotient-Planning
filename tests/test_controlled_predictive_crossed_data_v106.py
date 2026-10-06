"""Feature reconstruction reuses retained outcomes and exactly matches the original input builder."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_candidate_data_v100 as original
from acfqp.science import controlled_predictive_crossed_data_v106 as module

WORK, FEATURE_WORK = Counter(), Counter()
METHODS = ['H2_ONLY', 'PREFIX_ONLY_DIRECT', 'R4_H4_UNIFORM_SHRINK_DIRECT', 'R4_H16_UNIFORM_SHRINK_DIRECT',
    'R4_H4_UNIFORM_SHRINK_DIRECT_FROZEN_HALF', 'R4_H16_UNIFORM_SHRINK_DIRECT_FROZEN_HALF']


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    recover = module.recover_features
    def counted_recovery(*args, **kwargs):
        result = recover(*args, **kwargs)
        WORK['feature_recovery_calls'] += 1
        FEATURE_WORK.update(result[2])
        return result
    module.recover_features = counted_recovery
    yield
    module.recover_features = recover
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_crossed_data_v106.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before, mock_work=dict(WORK), feature_counts=dict(FEATURE_WORK),
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        neural_candidate_predictions=0, scope='pure feature recovery and synthetic retained-prefix fixtures'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def mock_prefix(board, query, option, replica, seed, rule):
    WORK['mock_prefixes_constructed'] += 1
    oi = module.OPTIONS.index(option)
    status = 'WON' if oi == 4 and replica == 1 else 'LOST' if oi == 3 and replica == 2 else 'ACTIVE'
    steps = 2 if status != 'ACTIVE' else 4
    duration = 0 if option == 'H2' else min(int(option.split('_')[1]), steps)
    final = list(board)
    final[0] = oi + 1
    return dict(option=option, replica=replica, spawn_seed=seed, planning_seed=seed + 10 ** 12,
        initial_board=list(board), final_board=final, status=status, steps_count=steps,
        steps=[dict(status='ACTIVE') for _ in range(steps - 1)] + [dict(status=status)],
        direct=[oi / 8 + replica / 1024, float(status == 'LOST'), float(status == 'WON')],
        controller=dict(events=[{}], initiation_step=0, fragment_actions=duration),
        action_paths=['fragment'] * duration + ['H2'] * (steps - duration),
        model_work=dict(synthetic_transitions=steps, spawn_uniform_draws=2 * steps),
        planning_counts=dict(model_uniform_draws=4 * steps))


def make_prefixes(board, query, seed=42):
    return [mock_prefix(board, query, option, replica, seed + replica, None)
            for replica in range(32) for option in module.OPTIONS]


@pytest.mark.parametrize('query', list(module.QUERIES))
def test_recovery_is_exactly_original_v100_features_and_utilities(tmp_path, monkeypatch, query):
    monkeypatch.setattr(original, '_simulate_prefix', mock_prefix)
    board = [1] * 10 + [0] * 6
    features, direct, raw, log = original.build_candidates(board, query, None, 42)
    WORK['original_feature_calls'] += 1
    FEATURE_WORK.update(log['feature_counts'])
    recovered, utilities, counts = module.recover_features(board, query, raw)
    assert recovered == features and utilities == direct and counts == log['feature_counts']
    assert counts == dict(board_feature_rows=321, paired_feature_rows=160, candidate_feature_vectors=5)
    # A pure recovery remains available even when all simulation is prohibited.
    def forbidden(*args, **kwargs):
        raise AssertionError('feature recovery must not call the original sampler')
    monkeypatch.setattr(original, '_simulate_prefix', forbidden)
    assert module.recover_features(board, query, raw) == (recovered, utilities, counts)


@pytest.mark.parametrize('fault', ['roster', 'board', 'seed'])
def test_recovery_rejects_mismatched_retained_prefixes(fault):
    board = [1] * 10 + [0] * 6
    raw = make_prefixes(board, 'reward')
    if fault == 'roster':
        raw.pop()
    elif fault == 'board':
        raw[0]['initial_board'][0] += 1
    else:
        raw[1]['spawn_seed'] += 1
    with pytest.raises(ValueError, match='roster|board|streams'):
        module.recover_features(board, 'reward', raw)


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def source_fixture(tmp_path):
    source, output = tmp_path / 'v105', tmp_path / 'v106'
    source.mkdir()
    output.mkdir()
    board, source_lives, all_raw = [1] * 10 + [0] * 6, [], {}
    templates = {query: make_prefixes(board, query, 0) for query in module.QUERIES}
    recovered = {query: module.recover_features(board, query, raw) for query, raw in templates.items()}
    for life in module.LIFECYCLES:
        references, rows = [], []
        folder = source / f'life_{life}' / 'evaluation'
        folder.mkdir(parents=True)
        for episode in range(8):
            for qi, query in enumerate(module.QUERIES):
                root = dict(life=life, query=query, episode=episode, board=board, step=3,
                    source_seed=10590000 + life * 100 + episode)
                direct = recovered[query][1]
                selected = max(range(5), key=lambda index: direct[index])
                event = dict(board=board, step=3, option=module.OPTIONS[selected], value=direct[selected],
                    predicted_advantage=None, predictions={option: dict(value=value) for option, value in zip(module.OPTIONS, direct)},
                    score_semantics='prefix_utility')
                predictions = {method: deepcopy(event) for method in METHODS[1:]}
                for method in METHODS[2:]:
                    predictions[method]['score_semantics'] = 'rank_score'
                references.append(dict(root=deepcopy(root), predictions=predictions,
                    terminal_log=dict(trajectories=160, pair_deltas={option: [[.1, 0, 0]] * 32 for option in module.OPTIONS[1:]},
                        ground_work=dict(sampled_transitions=1600), planning_counts=dict(model_uniform_draws=6400)),
                    reference_complete=True, audit=dict(trajectory_roster_complete=True)))
                seed = 251000000000 + life * 10000000 + qi * 1000000 + episode * 1000
                for raw in templates[query]:
                    row = dict(raw, method='PREFIX_ONLY_DIRECT', query=query, episode=episode,
                        spawn_seed=seed + raw['replica'], planning_seed=seed + raw['replica'] + 10 ** 12)
                    rows.append(row)
                # Other method prefixes are counted as reads but never used to reconstruct inputs.
                rows.append(dict(method=METHODS[2], irrelevant_retained_prefix=True))
        all_raw[life] = rows
        write_rows(folder / 'model_prefixes.jsonl.gz', rows)
        source_lives.append(dict(id=life, evaluation=dict(validation=dict(roots=references, missing_roots=[]))))
    run = dict(status='complete', settings=dict(lifecycles=list(module.LIFECYCLES), queries=module.QUERIES,
        evaluation_replicas=8, prefix_replicas=32, methods=METHODS, synthetic_seed_base=251000000000), lifecycles=source_lives)
    return source, output, run, all_raw, recovered


def test_full_cohort_reuses_original_inputs_events_and_references(tmp_path, monkeypatch):
    source, output, run, raw, expected = source_fixture(tmp_path)
    reads, read_rows = Counter(), module._rows
    def counted_rows(path):
        reads[str(path)] += 1
        return read_rows(path)
    monkeypatch.setattr(module, '_rows', counted_rows)
    roots, log = module.load_cohort(source, output, run)
    assert [root['root_id'] for root in roots] == [f'life_{life}_{query}_{episode}'
        for life in module.LIFECYCLES for query in module.QUERIES for episode in range(8)]
    assert reads == {str(source / f'life_{life}' / 'evaluation/model_prefixes.jsonl.gz'): 1 for life in module.LIFECYCLES}
    assert log['counts']['rows_read'] == 64 * 161 and log['counts']['retained_prefixes'] == 64 * 160
    assert log['counts']['roots'] == 64 and log['counts']['recovered_candidate_vectors'] == 320
    assert all(log['checks'].values())
    assert log['feature_counts'] == dict(board_feature_rows=64 * 321, paired_feature_rows=64 * 160, candidate_feature_vectors=320)
    assert log['inherited_prefix_model_work']['synthetic_transitions'] == 64 * (160 * 4 - 4)
    for name in ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                 'neural_candidate_predictions', 'new_selector_calls'):
        assert log['counts'][name] == 0
    for root in roots:
        assert root['features'] == expected[root['query']][0] and root['prefix_utilities'] == expected[root['query']][1]
        life = next(item for item in run['lifecycles'] if item['id'] == root['life'])
        old = next(item for item in life['evaluation']['validation']['roots']
                   if item['root']['query'] == root['query'] and item['root']['episode'] == root['episode'])
        assert root['original_predictions'] == old['predictions']
        assert root['reference_log'] == old['terminal_log']
        assert root['reference_audit'] == old['audit'] and root['reference_complete'] == old['reference_complete']
    assert json.loads((output / 'cohort.json').read_text()) == dict(roots=roots, log=log)


@pytest.mark.parametrize('fault', ['score', 'choice'])
def test_original_prefix_decision_must_reproduce_exactly(tmp_path, fault):
    source, output, run, _, _ = source_fixture(tmp_path)
    event = run['lifecycles'][0]['evaluation']['validation']['roots'][0]['predictions']['PREFIX_ONLY_DIRECT']
    if fault == 'score':
        event['predictions']['SPACE_1']['value'] += 1e-12
    else:
        event['option'] = 'H2'
    with pytest.raises(ValueError, match='recovered prefix scores|recovered prefix choice'):
        module.load_cohort(source, output, run)
