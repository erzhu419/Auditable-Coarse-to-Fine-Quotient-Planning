"""Fresh four-replica labels, discarded budget tails, and separate prefix work."""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_candidate_data_v100 as candidates
from acfqp.science import controlled_predictive_fresh_data_v105 as module
from acfqp.science.controlled_predictive_root_coverage_v98 import source_seed, branch_seed

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_fresh_data_v105.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before, mock_work=dict(WORK),
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        neural_candidate_predictions=0, tree_fits=0, scope='synthetic acquired branches and mock model prefixes only'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def acquisition_fixture(folder, tail='branches'):
    life, board = 11, [1] * 10 + [0] * 6
    raw, roots, accepted = [], [], []
    ground, planning = Counter(), Counter()
    partition = {key: dict(source_transitions=0, branch_transitions=0, total_transitions=0)
                 for key in ('training', 'heldout', 'unincorporated')}
    source_transitions = 0
    for cursor in (7, 8, 9):
        episode, qi = divmod(cursor, 2)
        query, complete = tuple(module.QUERIES)[qi], cursor != 9
        root = dict(board=board, episode=episode, query=query, source_seed=source_seed(life, episode, query), step=1)
        count = 20 if complete else 7 if tail == 'branches' else 0
        own_source = 2 if complete or tail == 'branches' else 1
        source_transitions += own_source
        for index in range(count):
            replica, oi = divmod(index, 5)
            score_delta = oi * (128 if replica < 2 else -64)
            status = 'WON' if oi == 4 and replica % 2 else 'LOST'
            if not complete and index == count - 1:
                status = 'CUTOFF'
            work, plan = dict(sampled_transitions=3, environment_random_draws=6), dict(model_uniform_draws=12)
            raw.append(dict(root=root, option=module.OPTIONS[oi], replica=replica,
                env_seed=branch_seed(life, episode, query) + replica,
                game=dict(return_score=2048 + score_delta, status=status, work=work), planning_counts=plan))
            ground.update(work)
            planning.update(plan)
        role = ('heldout' if episode % 5 == 4 else 'training') if complete else 'unincorporated'
        for name, value in (('source_transitions', own_source), ('branch_transitions', 3 * count),
                            ('total_transitions', own_source + 3 * count)):
            partition[role][name] += value
        roots.append(dict(root=root if count else None, cursor=cursor, branch_trajectories=count,
            complete_block=complete, disposition=role, source_transitions=own_source,
            branch_transitions=count * 3, source_status='CUTOFF' if not count else 'LOST'))
        if complete:
            accepted.append(dict(root, replicas=4, heldout=episode % 5 == 4))
    used = ground['sampled_transitions'] + source_transitions
    acquisition = dict(life=life, replicas=4, budget=used, used_transitions=used, unused_budget=0,
        budget_exhausted=True, start_cursor=7, next_cursor=10, episode_cutoff=6,
        root_records=roots, completed_roots=accepted, cost_partition=partition,
        source=dict(ground_work=dict(sampled_transitions=source_transitions,
            environment_random_draws=2 * source_transitions), planning_counts=dict(model_uniform_draws=4 * source_transitions)),
        branches=dict(ground_work=dict(ground), planning_counts=dict(planning)))
    write_rows(folder / 'branch_games.jsonl.gz', raw)
    return acquisition, raw


def mock_prefix(board, query, option, replica, seed, rule):
    oi = module.OPTIONS.index(option)
    final = list(board)
    final[0] = oi + 1
    duration = 0 if option == 'H2' else int(option.split('_')[1])
    WORK['mock_prefixes'] += 1
    return dict(option=option, replica=replica, spawn_seed=seed, planning_seed=seed + 10 ** 12,
        initial_board=list(board), final_board=final, status='ACTIVE', steps_count=4,
        steps=[dict(status='ACTIVE') for _ in range(4)], direct=[oi * .1, 0, 0],
        controller=dict(events=[{}], initiation_step=0, fragment_actions=duration),
        action_paths=['fragment'] * duration + ['H2'] * (4 - duration),
        model_work=dict(synthetic_transitions=4, spawn_uniform_draws=8), planning_counts=dict(model_uniform_draws=16))


@pytest.mark.parametrize('tail', ['branches', 'source'])
def test_whole_roots_replica_means_budget_tail_and_separate_model_cost(tmp_path, monkeypatch, tail):
    acquisition, raw = acquisition_fixture(tmp_path, tail)
    monkeypatch.setattr(candidates, '_simulate_prefix', mock_prefix)
    reads, original_rows = [], module._rows
    def counted_rows(path):
        reads.append(Path(path).name)
        return original_rows(path)
    monkeypatch.setattr(module, '_rows', counted_rows)
    records, log = module.load_batch(acquisition, tmp_path, None, 11)
    assert reads == ['branch_games.jsonl.gz']
    assert len(records) == 2 and log['counts']['training_roots'] == log['counts']['heldout_roots'] == 1
    assert log['counts'].get('excluded_roots', 0) == int(tail == 'branches')
    assert log['counts']['excluded_source_records'] == int(tail == 'source')
    assert log['counts']['trajectories_read'] == len(raw) and log['counts']['steps_read'] == 3 * len(raw)
    assert log['counts']['paired_replica_rows'] == 8 and log['counts']['mean_roots_verified'] == 2
    assert (log['start_cursor'], log['next_cursor'], log['episode_cutoff']) == (7, 10, 6)
    assert log['inherited_acquisition'] == acquisition
    assert sum(row['total_transitions'] for row in acquisition['cost_partition'].values()) == acquisition['used_transitions']
    assert acquisition['cost_partition']['unincorporated']['total_transitions'] > 0
    assert log['model_prefix_roots'] == 2 and log['model_prefix_trajectories'] == 320
    assert log['new_model_work']['synthetic_transitions'] == 1280
    assert log['new_planning_counts']['model_uniform_draws'] == 5120
    assert log['new_feature_counts']['candidate_feature_vectors'] == 10
    assert log['new_prefix_outcomes'] == {'ACTIVE': 320}
    for record in records:
        assert np.asarray(record['features']).shape == (5, 121)
        labels = np.asarray(record['replica_utilities'])
        assert labels.shape == (4, 5) and np.all(labels[:, 0] == 0)
        assert labels[0, 1] > 0 and labels[3, 1] < 0
        assert np.allclose(labels.mean(axis=0), record['utilities'], rtol=0, atol=1e-12)
        assert record['utilities'][1] == pytest.approx(32 / 2048)
        assert record['paired_rfs'][4] == pytest.approx([128 / 2048, -.5, .5])
        assert record['utilities'][4] == pytest.approx(128 / 2048 + (4 if record['query'] == 'risk_goal' else 0))
        assert record['prefix_seed'] == 250000000000 + 11 * 10000000 + record['episode'] * 1000 + tuple(module.QUERIES).index(record['query']) * 100
    assert list(original_rows(tmp_path / 'candidate_roots.jsonl.gz')) == records
    prefixes = list(original_rows(tmp_path / 'training_model_prefixes.jsonl.gz'))
    assert len(prefixes) == 320 and {row['root']['episode'] for row in prefixes} == {3, 4}
    assert all(row['root']['query'] != 'risk_goal' or row['root']['episode'] != 4 for row in prefixes)
    for key in ('new_environment_transitions', 'tree_fits', 'neural_model_fits', 'neural_candidate_predictions'):
        assert log['counts'][key] == 0


def test_declared_complete_root_cannot_lose_a_replica(tmp_path, monkeypatch):
    acquisition, raw = acquisition_fixture(tmp_path)
    monkeypatch.setattr(candidates, '_simulate_prefix', mock_prefix)
    write_rows(tmp_path / 'branch_games.jsonl.gz', raw[5:])
    with pytest.raises(ValueError, match='whole-root completeness'):
        module.load_batch(acquisition, tmp_path, None, 11)


def test_physical_work_mismatch_prevents_using_the_batch(tmp_path, monkeypatch):
    acquisition, _ = acquisition_fixture(tmp_path)
    acquisition['used_transitions'] -= 1
    monkeypatch.setattr(candidates, '_simulate_prefix', mock_prefix)
    with pytest.raises(ValueError, match='physical work'):
        module.load_batch(acquisition, tmp_path, None, 11)
