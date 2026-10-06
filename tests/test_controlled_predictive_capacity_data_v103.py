"""V103 reuses compact stage records and separates inherited reads from new work."""
import copy
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_capacity_data_v103 as module


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_capacity_data_v103.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0,
        scope='synthetic compact retained-record fixtures only'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def retained_stage(tmp_path, replicas=8):
    folder, output = tmp_path / 'v102', tmp_path / 'v103'
    folder.mkdir()
    output.mkdir()
    records = []
    for index, episode in enumerate((2, 3, 4)):
        labels = [[(2 if replica % 2 else -1) * option / 16 for option in range(5)]
                  for replica in range(replicas)]
        utilities = np.mean(labels, axis=0).tolist()
        records.append(dict(board=[index + 1] * 10 + [0] * 6,
            query=('reward' if index == 1 else 'risk_goal'), episode=episode,
            features=[[index + option / 10 + f / 10000 for f in range(121)] for option in range(5)],
            utilities=utilities, paired_rfs=[[u, 0, 0] for u in utilities],
            replica_utilities=labels, prefix_utilities=[0, 1, -1, 2, -2], prefix_seed=21000 + index))
    acquisition = dict(replicas=replicas, episode_cutoff=7, start_cursor=4, next_cursor=10,
        used_transitions=256000, completed_roots=[{k: row[k] for k in ('board', 'query', 'episode')}
                                               for row in records])
    data = dict(replicas=replicas, episode_cutoff=7, start_cursor=4, next_cursor=10,
        inherited_acquisition=acquisition,
        inherited_ground_work=dict(sampled_transitions=256000, environment_random_draws=512000),
        inherited_planning_counts=dict(model_uniform_draws=1024000),
        inherited_feature_prefixes=dict(model_work=dict(synthetic_transitions=1920),
            planning_counts=dict(model_uniform_draws=7680), feature_counts=dict(candidate_feature_vectors=15),
            outcomes=dict(ACTIVE=480), trajectories=480, roots=3),
        counts=dict(complete_roots=3, training_roots=2, heldout_roots=1,
                    trajectories_read=3 * replicas * 5 + 7, steps_read=255900,
                    excluded_roots=1, excluded_trajectories_read=7, paired_replica_rows=3 * replicas),
        max_mean_utility_difference=0, seconds=12.5)
    stage = dict(budget=256000, episode_cutoff=7, data=data)
    (folder / 'construction.json').write_text(json.dumps(stage))
    write_rows(folder / 'candidate_roots.jsonl.gz', records)
    return folder, output, stage, records


@pytest.mark.parametrize('replicas', [4, 8])
def test_reuse_exact_records_and_order_with_inherited_costs_only(tmp_path, monkeypatch, replicas):
    folder, output, stage, original = retained_stage(tmp_path, replicas)
    paths, original_rows = [], module._rows
    def counted_rows(path):
        paths.append(Path(path))
        return original_rows(path)
    monkeypatch.setattr(module, '_rows', counted_rows)
    records, log = module.load_batch(folder, output)
    assert paths == [folder / 'candidate_roots.jsonl.gz']
    assert records == original
    assert list(original_rows(output / 'candidate_roots.jsonl.gz')) == original
    for field in module.INHERITED_FIELDS:
        assert log[field] == stage['data'][field]
    assert log['inherited_v102_data_counts'] == stage['data']['counts']
    assert 'trajectories_read' not in log['counts'] and 'steps_read' not in log['counts']
    assert log['counts']['roots_read'] == log['counts']['mean_roots_verified'] == 3
    assert log['counts']['training_roots'] == 2 and log['counts']['heldout_roots'] == 1
    for key in ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                'neural_candidate_predictions', 'model_prefix_trajectories'):
        assert log['counts'][key] == 0
    assert log['max_mean_utility_difference'] == 0
    assert all(len(record['replica_utilities']) == replicas for record in records)
    assert records[0]['replica_utilities'][0][1] < 0 < records[0]['replica_utilities'][1][1]


@pytest.mark.parametrize('field', ['features', 'replica_utilities'])
def test_changed_retained_dimensions_are_rejected(tmp_path, field):
    folder, output, _, records = retained_stage(tmp_path)
    records[0][field] = records[0][field][:-1]
    write_rows(folder / 'candidate_roots.jsonl.gz', records)
    with pytest.raises(ValueError, match='dimensions'):
        module.load_batch(folder, output)


def test_replica_mean_disagreement_is_rejected(tmp_path):
    folder, output, _, records = retained_stage(tmp_path)
    records[0]['replica_utilities'][0][1] += 1
    write_rows(folder / 'candidate_roots.jsonl.gz', records)
    with pytest.raises(ValueError, match='terminal means'):
        module.load_batch(folder, output)


def test_record_order_must_match_original_complete_stage_roster(tmp_path):
    folder, output, _, records = retained_stage(tmp_path)
    write_rows(folder / 'candidate_roots.jsonl.gz', records[::-1])
    with pytest.raises(ValueError, match='ordered stage roster'):
        module.load_batch(folder, output)


def test_stage_cursor_must_match_inherited_acquisition(tmp_path):
    folder, output, stage, _ = retained_stage(tmp_path)
    changed = copy.deepcopy(stage)
    changed['data']['start_cursor'] += 1
    (folder / 'construction.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='acquisition interval'):
        module.load_batch(folder, output)
