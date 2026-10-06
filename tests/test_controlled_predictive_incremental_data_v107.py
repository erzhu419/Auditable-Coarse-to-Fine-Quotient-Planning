"""The half-budget statistics belong to the original batch, not a cutoff-only reslice."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_incremental_data_v107 as module
from acfqp.science.controlled_predictive_replica_ranking_v102 import pair_gamma

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    read_rows, gamma = module._rows, module.pair_gamma
    def counted_rows(path):
        rows = read_rows(path)
        WORK['candidate_files_read'] += 1
        WORK['candidate_records_read'] += len(rows)
        return rows
    def counted_gamma(*args, **kwargs):
        WORK['training_statistics_recomputations'] += 1
        return gamma(*args, **kwargs)
    module._rows, module.pair_gamma = counted_rows, counted_gamma
    yield
    module._rows, module.pair_gamma = read_rows, gamma
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_incremental_data_v107.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before, fixture_work=dict(WORK),
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        neural_candidate_predictions=0, new_feature_vectors=0,
        scope='compact synthetic candidate records and unchanged half-model payload fixtures'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def record(episode, query, amplitude=1):
    # Large heldout and second-batch values make accidental inclusion in half statistics visible.
    base = 10 ** 6 if episode == 4 or (episode == 5 and query == 'risk_goal') else episode
    features = [[base + candidate / 8 + feature / 1024 for feature in range(121)] for candidate in range(5)]
    for row in features:
        row[-1] = 3.
    labels = [[amplitude * candidate * (2 if replica % 2 else -1) / 8 for candidate in range(5)] for replica in range(4)]
    utility = np.mean(labels, axis=0).tolist()
    return dict(board=[episode + 1] * 10 + [0] * 6, episode=episode, query=query, features=features,
        replica_utilities=labels, utilities=utility, paired_rfs=[[value, 0, 0] for value in utility],
        prefix_utilities=[0, .1, -.1, .2, -.2], prefix_seed=250000000000 + episode)


def fixture_source(tmp_path):
    source, life = tmp_path / 'v105', 11
    batches = [[record(0, 'reward'), record(0, 'risk_goal'), record(4, 'reward', 1000000), record(5, 'reward')],
               [record(5, 'risk_goal', 1000000), record(6, 'reward'), record(9, 'risk_goal')]]
    stages, cumulative, paths = [], [], []
    for index, batch in enumerate(batches):
        budget, start, end, cutoff = (256000, 0, 11, 6) if index == 0 else (512000, 11, 20, 11)
        folder = source / f'life_{life}' / 'replicas_4' / f'budget_{budget}'
        folder.mkdir(parents=True)
        path = folder / 'candidate_roots.jsonl.gz'
        write_rows(path, batch)
        paths.append(path)
        acquisition = dict(life=life, replicas=4, start_cursor=start, next_cursor=end, episode_cutoff=cutoff,
            completed_roots=[{key: row[key] for key in ('board', 'episode', 'query')} for row in batch])
        counts = dict(complete_roots=len(batch), training_roots=sum(row['episode'] % 5 != 4 for row in batch),
                      heldout_roots=sum(row['episode'] % 5 == 4 for row in batch))
        data = dict(start_cursor=start, next_cursor=end, episode_cutoff=cutoff, counts=counts)
        cumulative.extend(batch)
        coverage = {query: {role: sorted(row['episode'] for row in cumulative
            if row['query'] == query and (row['episode'] % 5 == 4) == (role == 'heldout'))
            for role in ('training', 'heldout')} for query in module.QUERIES}
        stages.append(dict(budget=budget, episode_cutoff=cutoff, acquisition=acquisition, data=data,
            cumulative_roots=coverage, cumulative_root_count=len(cumulative)))
    training = [row for row in batches[0] if row['episode'] % 5 != 4]
    x = np.asarray([row['features'] for row in training])
    mean, scale = x.mean(axis=(0, 1)), x.std(axis=(0, 1))
    scale[scale == 0] = 1.
    gamma = float(pair_gamma([row['utilities'] for row in training], [row['replica_utilities'] for row in training]).mean())
    episodes = {query: sorted(row['episode'] for row in training if row['query'] == query) for query in module.QUERIES}
    metadata, payloads, model_paths = {}, {}, {}
    for hidden in (4, 16):
        name = f'R4_H{hidden}_UNIFORM_SHRINK_DIRECT_FROZEN_HALF'
        path = paths[0].parent / f'{name.lower()}_model.json'
        payload = dict(schema='fixture', hidden=hidden, checkpoint=6, family='UNIFORM_SHRINK',
            training_episodes=episodes, mean=mean.tolist(), scale=scale.tolist(), uniform_gamma=gamma,
            parameters=[np.full((121, hidden), hidden / 100).tolist(), [0.] * hidden, [1.] * hidden],
            optimizer_steps=1000)
        path.write_text(json.dumps(payload))
        payloads[str(hidden)], model_paths[str(hidden)] = payload, path
        metadata[name] = dict(replicas=4, budget=256000, hidden=hidden, episode_cutoff=6,
                             family='UNIFORM_SHRINK', path=str(path))
    allocation = dict(life=life, replicas=4, construction=stages, model_metadata=metadata)
    return source, allocation, batches, paths, payloads, model_paths


def test_exact_first_batch_statistics_exclude_heldout_and_new_same_episode_query(tmp_path):
    source, allocation, batches, _, original_payloads, _ = fixture_source(tmp_path)
    allocation_before = deepcopy(allocation)
    records, payloads, log = module.load_training(source, 11, allocation)
    assert records == batches[0] + batches[1]
    assert payloads == original_payloads and allocation == allocation_before
    assert (log['half_cutoff'], log['full_cutoff']) == (6, 11)
    assert log['half'] == dict(records=4, training_roots=3, heldout_roots=1,
                              training_episodes={'reward': [0, 5], 'risk_goal': [0]})
    assert log['full'] == dict(records=7, training_roots=5, heldout_roots=2,
                              training_episodes={'reward': [0, 5, 6], 'risk_goal': [0, 5]})
    # The second increment really contains a new query below the half cutoff.
    assert batches[1][0]['episode'] < log['half_cutoff'] and batches[1][0]['query'] == 'risk_goal'
    assert max(payloads['4']['mean']) < 10 and payloads['4']['uniform_gamma'] < 1
    assert payloads['4']['scale'][-1] == 1
    assert log['counts']['files_read'] == 4 and log['counts']['records_read'] == 7
    assert log['counts']['half_payload_files_read'] == 2 and all(log['checks'].values())
    for field in ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                  'neural_candidate_predictions', 'new_feature_vectors', 'model_prefix_trajectories'):
        assert log['counts'][field] == 0


@pytest.mark.parametrize('fault', ['duplicate', 'omission'])
def test_stage_duplicate_or_omission_cannot_silently_change_training_data(tmp_path, fault):
    source, allocation, batches, paths, _, _ = fixture_source(tmp_path)
    changed = deepcopy(batches[1])
    if fault == 'duplicate':
        changed.append(deepcopy(batches[0][0]))
    else:
        changed.pop()
    write_rows(paths[1], changed)
    with pytest.raises(ValueError, match='complete incremental root roster'):
        module.load_training(source, 11, allocation)


def test_half_payload_statistics_must_exactly_match_original_training_batch(tmp_path):
    source, allocation, _, _, payloads, model_paths = fixture_source(tmp_path)
    payloads['4']['mean'][0] += 1e-12
    model_paths['4'].write_text(json.dumps(payloads['4']))
    with pytest.raises(ValueError, match='half normalization'):
        module.load_training(source, 11, allocation)


def test_replica_labels_must_reproduce_the_original_root_mean(tmp_path):
    source, allocation, batches, paths, _, _ = fixture_source(tmp_path)
    batches[0][0]['replica_utilities'][0][1] += 1
    write_rows(paths[0], batches[0])
    with pytest.raises(ValueError, match='replica means'):
        module.load_training(source, 11, allocation)
