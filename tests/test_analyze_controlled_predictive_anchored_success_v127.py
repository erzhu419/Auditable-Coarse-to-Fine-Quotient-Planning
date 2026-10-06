"""Check retained labels, anchor identity, unchanged counts and heldout cohorts."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_anchored_success_v127 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_anchored_success_v127.analysis_checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, count_updates=0,
        scope='synthetic replay, prefix, scalar readout, saved-count and cohort fixtures'))
    path.write_text(json.dumps(value, indent=2)+'\n')


def original(life=0, policy='reward', episode=0, status='LOST'):
    scores = [4, 8, 16] if status != 'CUTOFF' else [4]*2000
    n = len(scores)
    return dict(life=life, policy=policy, query=policy, method='TRAIN', episode_index=episode,
        seed=analysis.old.train_seed(life, policy, episode),
        initial_board=[1, 1]+[0]*14, final_board=[11]+[0]*15 if status == 'WON' else [1]*16,
        initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
        actions=['DOWN']*n, spawned_cells=[0]*n, spawned_ranks=[1]*n, scores=scores,
        result=dict(steps=n, status=status, score=sum(scores), seconds=.1,
            components=analysis.old.components(sum(scores), status),
            utility=analysis.old.utility(sum(scores), status, policy),
            environment_counts=dict(sampled_transitions=n, initial_spawns=2,
                environment_random_draws=2*n+4, ground_explicit_swipe_calls=n)))


def replay(source, updates=None, successes=0):
    r = source['result']; n, wins = analysis.expected_labels(source); steps, status = r['steps'], r['status']
    updates = source['episode_index']*3 if updates is None else updates
    return dict(life=source['life'], policy=source['policy'], episode_index=source['episode_index'],
        source_seed=source['seed'], fit=dict(status=status, observed_afterstates=steps, updates=n,
            successes=wins, success_afterstates=wins, unique_feature_updates=4*n,
            analytic_goals=int(status == 'WON'), censored_afterstates=steps if status == 'CUTOFF' else 0),
        result=dict(steps=steps, status=status, score=r['score'], seconds=.1, retained_transitions=steps,
            environment_counts={}, updates_before=updates, updates_after=updates+n,
            successes_before=successes, successes_after=successes+wins,
            learning_counts=dict(replay_games=1, replay_swipe_calls=steps,
                replay_line_table_lookups=4*steps, replay_recorded_spawns=steps,
                training_games=1, training_observed_afterstates=steps,
                success_observation_updates=n, unique_feature_updates=4*n, count_array_writes=8*n,
                feature_address_occurrences=32*n, training_analytic_goals=int(status == 'WON'),
                censored_games=int(status == 'CUTOFF'), censored_afterstates=steps if status == 'CUTOFF' else 0)))


def outer(life=0, method='LEARNED_reward', query='risk1', age=256, replica=0):
    policy = method[7:] if method in analysis.FROZEN else method.split('_', 1)[1]
    selected = 'reward' if policy == 'GPI' else policy
    row = original(life, selected); row.update(method=method, query=query,
        checkpoint=None if method in analysis.FROZEN else age, replica=replica,
        seed=analysis.evaluation_seed(life, replica), eval_id=f'{life}/{method}/{query}/{age}/{replica}')
    r = row['result']; n = r['steps']; r['utility'] = analysis.old.utility(r['score'], r['status'], query)
    if method in analysis.FROZEN:
        r.update(source_updates_before=42, source_updates_after=42, policy_counts=dict(choose_calls=n))
        row['eval_id'] = f'{life}/{method}/{replica}'
        return row
    row['policy'] = None
    same = query == selected
    source_calls = n*(2 if policy == 'GPI' else 1)
    r.update(updates_before=[age*3]*2, updates_after=[age*3]*2,
        successes_before=[0, 0], successes_after=[0, 0],
        learning_counts=dict(choose_calls=source_calls, source_choose_calls=source_calls,
            exact_anchor_bypasses=n if query in analysis.POLICIES and policy in ('GPI', query) else 0))
    src, q = analysis.QUERIES[selected], analysis.QUERIES[query]
    anchor, success = 2., None if same else 0.
    value = anchor if same else anchor + src['failure_penalty'] - q['failure_penalty'] + (
        q['failure_penalty']+q['goal_bonus']-src['failure_penalty']-src['goal_bonus'])*success
    row.update(chosen_anchor_values=[anchor]*n, chosen_success_probabilities=[success]*n,
        chosen_values=[value]*n, policy_indices=[analysis.POLICIES.index(selected)]*n)
    return row


def test_retained_terminal_labels_unique_counts_and_zero_new_acquisition():
    source = [original(status='WON')]; rows = [replay(source[0], updates=0)]
    result = analysis.inspect_replay(rows, source, 0, 'reward', episodes=1, ages=(1,))
    assert all(result['checks'].values())
    assert result['prefixes'][1] == dict(updates=2, successes=2, constant=1., retained_transitions=3,
        unique_feature_updates=8, winning_unique_feature_updates=8)
    assert not result['cost']['environment_counts']
    rows[0]['fit']['successes'] -= 1
    assert not analysis.inspect_replay(rows, source, 0, 'reward', episodes=1)['checks']['retained_seed_labels']
    rows[0]['result']['environment_counts'] = dict(sampled_transitions=3)
    assert not analysis.inspect_replay(rows, source, 0, 'reward', episodes=1)['checks']['replay_no_acquisition']


def test_cutoff_censor_and_missing_retained_game_are_not_refunded():
    source = original(status='CUTOFF'); row = replay(source, updates=0)
    result = analysis.inspect_replay([row], [source], 0, 'reward', episodes=1, ages=(1,))
    assert all(result['checks'].values()) and result['retained_transitions'] == 2000
    assert result['prefixes'][1]['constant'] == .5 and result['prefixes'][1]['updates'] == 0
    assert not analysis.inspect_replay([], [source], 0, 'reward', episodes=1)['checks']['replay_roster']


def test_anchor_formula_prefix_count_immutability_and_exact_query_history():
    row = outer()
    assert analysis.outer_valid(row, [768, 768], [0, 0], [0., 0.])
    bad = deepcopy(row); bad['chosen_values'][0] += 1
    assert not analysis.outer_valid(bad, [768, 768], [0, 0], [0., 0.])
    bad = deepcopy(row); bad['result']['successes_after'][1] += 1
    assert not analysis.outer_valid(bad, [768, 768], [0, 0], [0., 0.])
    own = outer(query='reward'); fixed = outer(method='FROZEN_reward', query='reward')
    assert analysis.outer_valid(own, [768, 768], [0, 0], [0., 0.]) and analysis.same_history(own, fixed)
    own['actions'][1] = 'UP'
    assert not analysis.same_history(own, fixed)


def test_constant_readout_cannot_use_another_prefix_or_policy_probability():
    row = outer(method='CONSTANT_reward')
    assert analysis.outer_valid(row, [768, 768], [0, 0], [0., 0.])
    row['chosen_success_probabilities'][0] = .5; row['chosen_values'][0] += 1
    assert not analysis.outer_valid(row, [768, 768], [0, 0], [0., 0.])


def test_brier_checks_boundedness_matched_source_and_unmodified_counts():
    source = outer(method='FROZEN_reward', query='reward'); prefix = dict(updates=100, successes=10, constant=.1)
    row = dict(life=0, policy='reward', replica=0, eval_id=source['eval_id'],
        probabilities=[.1]*3, constant=.1, prefix_updates=100, prefix_successes=10,
        learning_counts=dict(success_predictions=3, count_array_reads=192))
    result = analysis.diagnostic(row, source, prefix)
    assert all(result['checks'].values()) and result['learned_sse'] == pytest.approx(result['constant_sse'])
    row['probabilities'][0] = -0.1
    assert not analysis.diagnostic(row, source, prefix)['checks']['bounded_probabilities']
    row['policy'] = 'risk_goal'
    assert not analysis.diagnostic(row, source, prefix)['checks']['diagnostic_source_path']


def test_missing_outer_game_invalidates_primary_lifecycle_comparison():
    indexed, valid = {}, {}
    for life in analysis.LIVES:
        for method in analysis.METHODS:
            for age in ((256,) if method in analysis.FROZEN else analysis.AGES):
                for query in ((method[7:],) if method in analysis.FROZEN else analysis.QUERIES):
                    for rep in range(8):
                        row = outer(life, method, query, age, rep); key = analysis.outer_key(row)
                        indexed[key], valid[key] = row, True
    assert len(indexed) == 1600
    report = analysis.summarize(indexed, valid)
    assert report['comparisons']['1024']['LEARNED_GPI_minus_FROZEN_reward']['risk8']['mean_deltas']['utility'] == 0.
    del indexed[(0, 'LEARNED_GPI', 1024, 'risk8', 7)]
    report = analysis.summarize(indexed, valid)
    assert report['comparisons']['1024']['LEARNED_GPI_minus_CONSTANT_GPI']['risk8']['mean_deltas']['utility'] is None


def test_sparse_counts_match_successful_unique_updates_and_source_anchor(tmp_path):
    prefix = dict(updates=10, successes=4, constant=.4, unique_feature_updates=40, winning_unique_feature_updates=16)
    meta = dict(schema='acfqp.anchored_success.v127', radix=11, source_query=analysis.QUERIES['reward'],
        source_updates=42, updates=10, successes=4, global_success_rate=.4)
    path = tmp_path/'cp.npz'
    def write(wins=4):
        np.savez_compressed(path, metadata=json.dumps(meta), indices=np.arange(4, dtype=np.int64),
            visits=np.full(4, 10, dtype=np.uint64), wins=np.full(4, wins, dtype=np.uint64))
    write()
    cp = dict(model_ref='cp.npz', model_bytes=path.stat().st_size, updates=10, successes=4, constant=.4,
        save_counts=dict(checkpoint_saves=1, checkpoint_scanned_entries=4*11**6,
            checkpoint_saved_addresses=4, checkpoint_saved_count_entries=8))
    assert analysis.model_valid(tmp_path, cp, prefix, 'reward', 42)
    write(5); cp['model_bytes'] = path.stat().st_size
    assert not analysis.model_valid(tmp_path, cp, prefix, 'reward', 42)


def test_full_runner_schema_keeps_actual_counts_and_rejects_short_retained_corpus(tmp_path, monkeypatch):
    from scripts import run_controlled_predictive_anchored_success_v127 as runner
    folder = tmp_path/'run'; folder.mkdir()
    inherited = dict(v120_training=[dict(queries=dict(reward=dict(training_blocks=[
        dict(environment_counts=dict(sampled_transitions=22124667))])))], deterministic_prior={},
        v126_training=dict(games=8192, environment_counts=dict(sampled_transitions=6635452)))
    capsule = dict(schema='acfqp.anchored_success.v127.source', inherited_costs=inherited, snapshots=[])
    run = dict(settings=runner.settings(), inherited_costs=inherited, status='complete', seconds=1., lifecycles=[])
    traces = {}
    for life in analysis.LIVES:
        src = dict(life=life, rule={}, models={}, training_trace=str(
            ROOT/'reports/controlled_predictive_policy_consequences_v126'/f'life_{life}'/'training.jsonl.gz'))
        capsule['snapshots'].append(src)
        data = dict(life=life, policies={}, training_trace=f'{life}/replay', control_trace=f'{life}/outer',
            diagnostic_trace=f'{life}/diag', peak_weight_bytes=6*4*11**6*8)
        run['lifecycles'].append(data)
        originals, replays, controls, diagnostics = [], [], [], []
        for policy in analysis.POLICIES:
            src['models'][policy] = dict(updates=42, nonzero_weights=7, path=str(
                ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{life}'/policy/'checkpoint_4096.npz'))
            setting = dict(source_updates_before=42, source_updates_after=42,
                source_load_counts=dict(checkpoint_loads=1, checkpoint_loaded_parameters=7), source_load_seconds=.1,
                source_setup_counts=dict(allocated_weight_bytes=4*11**6*8), source_setup_seconds=.1,
                learner_setup_counts=dict(allocated_count_bytes=2*4*11**6*8), learner_setup_seconds=.1,
                training_blocks=[], checkpoints=[])
            data['policies'][policy] = setting
            block = runner.empty_block(0)
            for episode in range(1024):
                source_row = original(life, policy, episode); replay_row = replay(source_row)
                originals.append(source_row); replays.append(replay_row); runner.add_training(block, replay_row)
                if (episode+1) % 256 == 0:
                    setting['training_blocks'].append(block); block = runner.empty_block(episode+1)
            heldout = [outer(life, 'FROZEN_'+policy, policy, replica=rep) for rep in range(8)]
            controls.extend(heldout)
            for age in analysis.AGES:
                path = folder/f'{life}_{policy}_{age}.npz'; updates = age*3
                np.savez_compressed(path, metadata=json.dumps(dict(schema='acfqp.anchored_success.v127',
                    radix=11, source_query=analysis.QUERIES[policy], source_updates=42,
                    updates=updates, successes=0, global_success_rate=0.)),
                    indices=np.arange(4, dtype=np.int64), visits=np.full(4, updates, dtype=np.uint64),
                    wins=np.zeros(4, dtype=np.uint64))
                setting['checkpoints'].append(dict(age=age, model_ref=path.name,
                    model_bytes=path.stat().st_size, updates=updates, successes=0, constant=0., save_seconds=.1,
                    save_counts=dict(checkpoint_saves=1, checkpoint_scanned_entries=4*11**6,
                        checkpoint_saved_addresses=4, checkpoint_saved_count_entries=8)))
                diagnostics.extend(dict(life=life, policy=policy, checkpoint=age, replica=row['replica'],
                    eval_id=row['eval_id'], probabilities=[0.]*3, constant=0., prefix_updates=updates,
                    prefix_successes=0, learning_counts=dict(success_predictions=3, count_array_reads=192),
                    seconds=.1) for row in heldout)
        for method in analysis.ADAPTIVE:
            for age in analysis.AGES:
                for query in analysis.QUERIES:
                    controls.extend(outer(life, method, query, age, rep) for rep in range(8))
        traces[src['training_trace']] = originals
        for key, rows in ((data['training_trace'], replays), (data['control_trace'], controls), (data['diagnostic_trace'], diagnostics)):
            traces[str(folder/key)] = rows
    (folder/'run.json').write_text(json.dumps(run)); (folder/'source_capsule.json').write_text(json.dumps(capsule))
    monkeypatch.setattr(analysis, 'read_rows', lambda path: iter(traces[str(path)]))
    monkeypatch.setattr(analysis.old.old, 'model_valid', lambda *_args: True)
    monkeypatch.chdir(tmp_path)
    result = analysis.analyze(Path('run'))
    assert [key for key, value in result['checks'].items() if not value] == ['full_retained_replay']
    assert not result['complete'] and not result['primary_complete']
    assert result['costs']['retained_replayed_transitions'] == 8192*3
    assert result['costs']['actual_new_environment_transitions'] == 1600*3
    assert result['costs']['fresh_training_environment_transitions'] == 0
    assert result['costs']['physical_outer_games'] == 1600 and result['costs']['logical_outer_rows'] == 2048
    assert result['checks']['own_query_history']
