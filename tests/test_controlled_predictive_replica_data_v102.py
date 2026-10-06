"""Retained V102 labels preserve whole original replica blocks and feature binding."""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_replica_data_v102 as module


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_replica_data_v102.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0, scope='synthetic retained data fixtures only'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def retained_batch(tmp_path, replicas=8, partial='missing'):
    v98, v100, output = (tmp_path / name for name in ('v98', 'v100', 'output'))
    for folder in (v98, v100, output):
        folder.mkdir()
    board, raw, roots, accepted, saved = [1] * 10 + [0] * 6, [], [], [], []
    ground, planning = Counter(), Counter()
    for cursor in (6, 7, 8, 9):
        episode, qi = divmod(cursor, 2)
        root = dict(board=board, query=tuple(module.QUERIES)[qi], episode=episode)
        complete = cursor != 9
        count = replicas if complete or partial == 'cutoff' else replicas // 2
        group = []
        for replica in range(count):
            for oi, option in enumerate(module.OPTIONS):
                delta = oi * (6 if replica < replicas // 2 else -2)
                status = 'WON' if oi == 4 and replica % 2 else 'LOST'
                if not complete and partial == 'cutoff' and replica == replicas - 1 and oi == 4:
                    status = 'CUTOFF'
                work = dict(sampled_transitions=3, environment_random_draws=6)
                controller_work = dict(model_uniform_draws=12)
                row = dict(root=root, option=option, replica=replica,
                    game=dict(return_score=2048 + 128 * delta, status=status, work=work),
                    planning_counts=controller_work)
                group.append(row)
                ground.update(work)
                planning.update(controller_work)
        raw.extend(group)
        roots.append(dict(root=root, branch_trajectories=len(group), complete_block=complete))
        if not complete:
            continue
        accepted.append(root)
        paired = []
        for oi in range(len(module.OPTIONS)):
            targets = []
            for replica in range(replicas):
                game, reference = group[replica * 5 + oi]['game'], group[replica * 5]['game']
                targets.append([a - b for a, b in zip(
                    module._target(game['return_score'], game['status']),
                    module._target(reference['return_score'], reference['status']))])
            paired.append(np.mean(targets, axis=0).tolist())
        saved.append(dict(root, features=[[cursor + oi / 10 + j / 10000 for j in range(121)] for oi in range(5)],
            utilities=[module._utility(target, module.QUERIES[root['query']]) for target in paired],
            paired_rfs=paired, prefix_utilities=[0, 0.1, -0.1, 0.2, -0.2], prefix_seed=2000 + cursor))
    source = dict(ground_work=dict(sampled_transitions=8, environment_random_draws=16),
                  planning_counts=dict(model_uniform_draws=32))
    acquisition = dict(life=9, replicas=replicas, budget=ground['sampled_transitions'] + 8,
        used_transitions=ground['sampled_transitions'] + 8, start_cursor=6, next_cursor=10, episode_cutoff=6,
        root_records=roots, completed_roots=accepted, source=source,
        branches=dict(ground_work=dict(ground), planning_counts=dict(planning)))
    (v98 / 'construction.json').write_text(json.dumps(dict(acquisition=acquisition)))
    feature_data = dict(start_cursor=6, next_cursor=10, episode_cutoff=6,
        new_model_work=dict(synthetic_transitions=1920), new_planning_counts=dict(model_uniform_draws=7680),
        new_feature_counts=dict(candidate_feature_vectors=15), new_prefix_outcomes=dict(ACTIVE=480),
        model_prefix_trajectories=480, model_prefix_roots=3)
    (v100 / 'construction.json').write_text(json.dumps(dict(data=feature_data)))
    write_rows(v98 / 'branch_games.jsonl.gz', raw)
    write_rows(v100 / 'candidate_roots.jsonl.gz', saved)
    return v98, v100, output, acquisition, raw, saved


@pytest.mark.parametrize('replicas', [4, 8])
@pytest.mark.parametrize('partial', ['missing', 'cutoff'])
def test_complete_blocks_conflicts_feature_reuse_and_all_costs(tmp_path, monkeypatch, replicas, partial):
    v98, v100, output, acquisition, raw, saved = retained_batch(tmp_path, replicas, partial)
    read_calls, original_rows = Counter(), module._rows
    def counted_rows(path):
        read_calls[Path(path).name] += 1
        return original_rows(path)
    monkeypatch.setattr(module, '_rows', counted_rows)
    records, log = module.load_batch(v98, v100, output)
    assert read_calls == {'branch_games.jsonl.gz': 1, 'candidate_roots.jsonl.gz': 1}
    assert len(records) == 3
    assert log['counts']['training_roots'] == 2 and log['counts']['heldout_roots'] == 1
    assert log['counts']['excluded_roots'] == 1
    assert log['counts']['mean_roots_verified'] == 3
    assert log['counts']['paired_replica_rows'] == 3 * replicas
    assert log['counts']['trajectories_read'] == len(raw)
    assert log['counts']['steps_read'] == 3 * len(raw)
    assert log['counts']['cutoff_trajectories_read'] == int(partial == 'cutoff')
    assert log['inherited_acquisition'] == acquisition
    assert log['inherited_ground_work']['sampled_transitions'] == acquisition['used_transitions']
    assert log['inherited_planning_counts']['model_uniform_draws'] == 12 * len(raw) + 32
    assert log['inherited_feature_prefixes']['model_work']['synthetic_transitions'] == 1920
    assert log['inherited_feature_prefixes']['trajectories'] == 480
    for field in ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                  'neural_candidate_predictions', 'model_prefix_trajectories'):
        assert log['counts'][field] == 0
    for record, old in zip(records, saved):
        labels = np.asarray(record['replica_utilities'])
        assert labels.shape == (replicas, 5) and np.all(labels[:, 0] == 0)
        assert np.all(labels[:replicas // 2, 1] > 0) and np.all(labels[replicas // 2:, 1] < 0)
        assert np.allclose(labels.mean(axis=0), old['utilities'], rtol=0, atol=1e-12)
        assert {k: v for k, v in record.items() if k != 'replica_utilities'} == old
    assert list(original_rows(output / 'candidate_roots.jsonl.gz')) == records
    assert log['max_mean_utility_difference'] <= 1e-12


@pytest.mark.parametrize('field', ['board', 'utilities'])
def test_changed_source_root_or_terminal_mean_is_rejected(tmp_path, field):
    v98, v100, output, _, _, saved = retained_batch(tmp_path)
    saved[0][field][0] += 1
    write_rows(v100 / 'candidate_roots.jsonl.gz', saved)
    with pytest.raises(ValueError, match='root roster|terminal means'):
        module.load_batch(v98, v100, output)


def test_declared_eight_replica_block_cannot_be_truncated_to_four(tmp_path):
    v98, v100, output, _, raw, _ = retained_batch(tmp_path, replicas=8)
    write_rows(v98 / 'branch_games.jsonl.gz', [row for row in raw
        if row['root']['episode'] != 3 or row['root']['query'] != 'reward' or row['replica'] < 4])
    with pytest.raises(ValueError, match='whole-root completeness'):
        module.load_batch(v98, v100, output)
