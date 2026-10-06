"""Frozen fresh streams, missing triggers and retained censored references."""
from collections import Counter
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_fresh_targets_v113 as module

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_fresh_targets_v113.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before, fixture_work=dict(WORK),
        newly_sampled_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        scope='mock collectors and hand-written prefix/reference traces; unchanged real reference audit'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def read_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


@pytest.fixture
def acquisition(monkeypatch):
    options = dict(missing=None, cutoff=False, bad_prefix=False)
    calls, prefix_calls = [], []
    rule = object()
    monkeypatch.setattr(module, 'LearnedDynamics', SimpleNamespace(from_payload=lambda payload: rule))
    def collect(life, episode, query, supplied_rule, max_steps):
        assert life == module.SOURCE_LIFE_BASE + 15 and supplied_rule is rule and max_steps == 2000
        calls.append((life, query, episode))
        WORK['mock_source_games'] += 1
        seed = 8300000 + life * 10000 + episode
        sparse, trigger = [1, 1] + [0] * 14, [1] * 12 + [0] * 4
        absent = options['missing'] == (query, episode)
        steps = [{'board': sparse}, {'board': sparse if absent else trigger}]
        status = 'CUTOFF' if options['cutoff'] else 'LOST'
        game = dict(seed=seed, steps=steps, steps_count=2, status=status,
            work=dict(sampled_transitions=2, environment_random_draws=8))
        planning = dict(model_uniform_draws=8)
        root = None if absent else dict(board=trigger, step=1, query=query, episode=episode, source_seed=seed)
        raw = dict(query=query, episode=episode, env_seed=seed, model_seed=seed + 1000000,
            game=game, planning_counts=planning,
            controller=dict(events=[], fragment_actions=0, selected_option=None))
        log = dict(games=1, roots=int(root is not None), ground_work=game['work'],
            planning_counts=planning, outcomes={status: 1}, seconds=.01)
        return root, raw, log
    def candidates(board, query, supplied_rule, seed, replicas):
        assert supplied_rule is rule and replicas == 32
        prefix_calls.append((query, seed))
        traces = [dict(option=option, replica=replica, initial_board=board,
            spawn_seed=seed + replica, planning_seed=seed + replica + 1000000000000)
            for replica in range(replicas) for option in module.OPTIONS]
        WORK['mock_prefix_trajectories'] += len(traces)
        log = dict(trajectories=len(traces), model_work=dict(synthetic_transitions=len(traces)),
            planning_counts=dict(model_uniform_draws=4 * len(traces)),
            feature_counts=dict(candidate_feature_vectors=5), outcomes={'ACTIVE': len(traces)},
            wiring=dict(spawn_uniforms_aligned=not options['bad_prefix']), seconds=.02)
        return [[candidate / 10] * 121 for candidate in range(5)], [0, .1, .2, .3, .4], traces, log
    monkeypatch.setattr(module, 'collect_source', collect)
    monkeypatch.setattr(module, 'build_candidates', candidates)
    return options, calls, prefix_calls


def test_frozen_sources_and_candidate_prefixes_are_complete_and_retained(tmp_path, acquisition):
    _, calls, prefixes = acquisition
    result = module.build_target_history(15, tmp_path, {})
    assert len(calls) == len(prefixes) == len(result['roots']) == 16
    assert all(result['checks'].values()) and result['missing_roots'] == []
    assert result['source_log']['ground_work']['sampled_transitions'] == 32
    assert result['prefix_log']['trajectories'] == result['prefix_log']['model_work']['synthetic_transitions'] == 2560
    assert result['prefix_log']['feature_counts']['candidate_feature_vectors'] == 80
    first = result['roots'][0]
    assert first['root_id'] == '15_reward_0' and first['step'] == 1
    assert first['prefix_seed'] == 253000000000 + 15 * 10000000
    assert len(read_rows(tmp_path / 'life_15/source_games.jsonl.gz')) == 16
    raw = read_rows(tmp_path / 'life_15/model_prefixes.jsonl.gz')
    assert len(raw) == 2560 and all('features' not in row for row in raw)


def test_missing_trigger_is_retained_without_replacement(tmp_path, acquisition):
    options, calls, prefixes = acquisition
    options['missing'] = ('reward', 2)
    result = module.build_target_history(15, tmp_path, {})
    assert len(calls) == 16 and len(prefixes) == len(result['roots']) == 15
    assert len(result['missing_roots']) == 1 and result['missing_roots'][0]['root_id'] == '15_reward_2'
    assert result['missing_roots'][0]['reason'] == 'no_h2_trigger'
    assert all(result['checks'].values())


def test_source_cutoff_after_trigger_does_not_discard_the_legal_root(tmp_path, acquisition):
    acquisition[0]['cutoff'] = True
    result = module.build_target_history(15, tmp_path, {})
    assert len(result['roots']) == 16 and result['missing_roots'] == []
    assert result['source_log']['outcomes'] == {'CUTOFF': 16} and all(result['checks'].values())


def test_prefix_wiring_failure_preserves_partial_cost_and_raw_evidence(tmp_path, acquisition):
    acquisition[0]['bad_prefix'] = True
    with pytest.raises(ValueError, match='candidate features or retained prefixes'):
        module.build_target_history(15, tmp_path, {})
    folder = tmp_path / 'life_15'
    record = json.loads((folder / 'target_history.json').read_text())
    assert not record['checks']['prefix_wiring_match'] and record['source_log']['games'] == 1
    assert len(read_rows(folder / 'model_prefixes.jsonl.gz')) == record['prefix_log']['trajectories'] == 160


@pytest.fixture
def references(monkeypatch):
    options = dict(censored=False, corrupt_seed=False)
    monkeypatch.setattr(module, 'LearnedDynamics', SimpleNamespace(from_payload=lambda payload: 'fixture-rule'))
    root = dict(root_id='15_reward_0', life=15, query='reward', episode=0,
        board=[1] * 12 + [0] * 4, features=[[0] * 121 for _ in range(5)])
    def sample(received_root, rule, life, replicas, max_steps):
        assert received_root is root and rule == 'fixture-rule'
        assert life == module.SOURCE_LIFE_BASE + 15 and replicas == 32 and max_steps == 2000
        ground, planning, outcomes = Counter(), Counter(), Counter()
        raw = []
        for replica in range(replicas):
            seed = 8310000000 + life * 10000000 + replica
            for option in module.OPTIONS:
                status = 'CUTOFF' if options['censored'] and replica == 0 and option == 'H2' else 'LOST'
                work, plan = dict(sampled_transitions=1, environment_random_draws=2), dict(model_uniform_draws=4)
                row = dict(option=option, replica=replica, env_seed=seed, model_seed=seed + 1000000000000,
                    game=dict(initial_board=root['board'], seed=seed, steps_count=1, work=work, status=status),
                    controller=dict(initiation_step=0, selected_option=option, events=[{}],
                        fragment_actions=0 if option == 'H2' else 1), planning_counts=plan)
                raw.append(row)
                ground.update(work); planning.update(plan); outcomes[status] += 1
        if options['corrupt_seed']:
            raw[0]['env_seed'] += 1
        WORK['mock_reference_trajectories'] += len(raw)
        WORK['real_reference_audits'] += 1
        pairs = {} if options['censored'] else {option: [[0., 0., 0.]] * replicas for option in module.OPTIONS[1:]}
        log = dict(roots=1, rows=len(pairs), trajectories=len(raw), censored_root=options['censored'],
            ground_work=dict(ground), planning_counts=dict(planning), outcomes=dict(outcomes),
            pair_deltas=pairs, model_rng_streams=len(raw), model_uniform_draws=planning['model_uniform_draws'], seconds=.01)
        return [], raw, log
    monkeypatch.setattr(module, 'sample_root', sample)
    return options, root


@pytest.mark.parametrize('censored', [False, True])
def test_reference_retains_all_arms_and_censoring_without_retry(tmp_path, references, censored):
    options, root = references
    options['censored'] = censored
    record = module.reference_job(root, tmp_path, {})
    assert record['reference_complete'] is not censored and all(record['reference_audit'].values())
    assert record['reference_log']['trajectories'] == 160
    raw = read_rows(tmp_path / 'life_15/references/reward_0/games.jsonl.gz')
    assert len(raw) == 160 and Counter(row['block'] for row in raw) == {'A': 80, 'B': 80}
    assert all('features' not in row and row['root_id'] == root['root_id'] for row in raw)


def test_reference_execution_failure_is_saved_before_exception(tmp_path, references):
    options, root = references
    options['corrupt_seed'] = True
    with pytest.raises(ValueError, match='reference execution'):
        module.reference_job(root, tmp_path, {})
    folder = tmp_path / 'life_15/references/reward_0'
    record = json.loads((folder / 'reference.json').read_text())
    assert not record['reference_complete'] and not record['reference_audit']['paired_fresh_streams']
    assert len(read_rows(folder / 'games.jsonl.gz')) == 160
