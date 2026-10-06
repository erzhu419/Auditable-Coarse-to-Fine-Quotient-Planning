"""Reject wrong suffix labels, mutable evaluation and incomplete query cohorts."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_policy_consequences_v126 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_policy_consequences_v126.analysis_checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed - before,
        environment_samples=0, model_samples=0, component_updates=0,
        scope='synthetic target, accounting, model-file and heldout-cohort fixtures'))
    path.write_text(json.dumps(value, indent=2) + '\n')


def row(episode=0, status='LOST', method='TRAIN', query='reward', life=0, replica=0, age=256):
    scores = [4, 8, 16] if status != 'CUTOFF' else [4] * 2000
    n = len(scores); targets = analysis.suffix_targets(scores, status); m = len(targets)
    training = method == 'TRAIN'; frozen = method in analysis.FROZEN
    policy = method[7:] if frozen else query if training else None
    learn = dict(training_games=1, training_observed_afterstates=n, mc_updates=m,
        component_updates=3*m, component_predictions=3*m, table_lookups=96*m,
        table_update_occurrences=96*m, table_updates=96*m,
        training_analytic_goals=int(status == 'WON'), censored_games=int(status == 'CUTOFF'),
        censored_afterstates=n if status == 'CUTOFF' else 0) if training else (
            {} if frozen else dict(choose_calls=n*(2 if method == 'GPI' else 1)))
    r = dict(score=sum(scores), status=status, steps=n, seconds=.1,
        components=analysis.components(sum(scores), status),
        utility=analysis.utility(sum(scores), status, query),
        environment_counts=dict(sampled_transitions=n, initial_spawns=2,
            environment_random_draws=2*n+4, ground_explicit_swipe_calls=n),
        learning_counts=learn, policy_counts=dict(choose_calls=n) if training or frozen else {})
    if training or frozen:
        r.update(source_updates_before=42, source_updates_after=42)
    if training:
        r.update(updates_before=episode*m, updates_after=(episode+1)*m)
    elif not frozen:
        r.update(updates_before=[age*3, age*3], updates_after=[age*3, age*3])
    value = dict(life=life, policy=policy, query=query, method=method, episode_index=episode,
        checkpoint=None if training or frozen else age, replica=replica,
        seed=analysis.train_seed(life, policy, episode) if training else analysis.evaluation_seed(life, replica),
        result=r, initial_board=[1, 1]+[0]*14, final_board=([11]+[0]*15 if status == 'WON' else [1]*16),
        initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
        actions=['DOWN']*n, spawned_cells=[0]*n, spawned_ranks=[1]*n, scores=scores)
    if training:
        value['fit'] = dict(status=status, observed_afterstates=n, updates=m,
            analytic_goals=int(status == 'WON'), censored_afterstates=n if status == 'CUTOFF' else 0,
            target_sums=targets.sum(axis=0).tolist(), head_updates=[m]*3)
    else:
        value['eval_id'] = f'{life}/{method}/{replica}' if frozen else f'{life}/{method}/{query}/{age}/{replica}'
        if not frozen:
            vector = [1., .25, .75]; q = analysis.QUERIES[query]
            value.update(chosen_vectors=[vector[:] for _ in scores],
                chosen_values=[q['reward_weight']*(score/2048+vector[0])-q['failure_penalty']*vector[1]+q['goal_bonus']*vector[2] for score in scores],
                policy_indices=[1 if method == 'POLICY_risk_goal' else 0]*n)
    return value


def test_suffix_labels_exclude_current_reward_and_skip_analytic_winning_tail():
    assert np.array_equal(analysis.suffix_targets([4, 8, 16], 'LOST'), [[24/2048, 1, 0], [16/2048, 1, 0], [0, 1, 0]])
    assert np.array_equal(analysis.suffix_targets([4, 8, 16], 'WON'), [[24/2048, 0, 1], [16/2048, 0, 1]])
    good = row(status='WON'); assert analysis.fit_valid(good)
    for component in range(3):
        bad = deepcopy(good); bad['fit']['target_sums'][component] += 1
        assert not analysis.fit_valid(bad)


def test_cutoffs_cost_real_samples_but_have_no_mc_labels():
    value = row(status='CUTOFF')
    found = analysis.inspect_training([value], 0, 'reward', 42, episodes=1, ages=(1,))
    assert all(found['checks'].values())
    assert found['cost']['environment_counts']['sampled_transitions'] == 2000
    assert found['prefixes'][1]['updates'] == 0 and found['diagnostics']['censored_afterstates'] == 2000
    value['fit']['updates'] = 1
    assert not analysis.inspect_training([value], 0, 'reward', 42, episodes=1)['checks']['monte_carlo_targets']


def test_source_policy_update_drift_and_component_count_mismatch_fail():
    rows = [row(episode=i) for i in range(3)]
    assert all(analysis.inspect_training(rows, 0, 'reward', 42, episodes=3, ages=(3,))['checks'].values())
    rows[1]['result']['source_updates_after'] += 1
    rows[2]['result']['learning_counts']['component_updates'] -= 1
    checks = analysis.inspect_training(rows, 0, 'reward', 42, episodes=3)['checks']
    assert not checks['source_policy_immutable'] and not checks['learning_counters']


def test_readout_scalarization_seed_policy_identity_and_readonly_checks():
    good = row(method='GPI', query='risk8')
    assert analysis.outer_valid(good, [768, 768])
    changed = deepcopy(good); changed['chosen_vectors'][0][1] = 0.
    assert not analysis.outer_valid(changed, [768, 768])
    changed = deepcopy(good); changed['result']['updates_after'][0] += 1
    assert not analysis.outer_valid(changed, [768, 768])
    good['seed'] += 1
    assert not analysis.outer_valid(good, [768, 768])
    fixed = row(method='FROZEN_risk_goal', query='risk_goal')
    assert analysis.outer_valid(fixed, 42)
    fixed['query'] = 'risk8'
    assert not analysis.outer_valid(fixed, 42)


def test_frozen_reweighting_and_missing_game_preserve_lifecycle_boundary():
    indexed, valid = {}, {}
    for life in analysis.LIVES:
        for method in analysis.METHODS:
            for age in ((256,) if method in analysis.FROZEN else analysis.AGES):
                for query in ((method[7:],) if method in analysis.FROZEN else analysis.QUERIES):
                    for rep in range(8):
                        value = row(life=life, method=method, query=query, age=age, replica=rep)
                        key = analysis.outer_key(value); indexed[key], valid[key] = value, True
    assert len(indexed) == 832
    report = analysis.summarize(indexed, valid)
    assert report['methods']['FROZEN_reward']['1024']['risk8']['lifecycle_mean']['utility'] == 28/2048-8
    del indexed[(0, 'GPI', 1024, 'risk8', 7)]
    report = analysis.summarize(indexed, valid)
    assert report['comparisons']['1024']['GPI_minus_FROZEN_reward']['risk8']['mean_deltas']['utility'] is None
    assert report['methods']['GPI']['256']['risk8']['complete']


def test_source_path_calibration_uses_matched_policy_and_training_only_constant():
    source = row(method='FROZEN_reward'); targets = analysis.suffix_targets(source['scores'], 'LOST')
    prefix = dict(updates=123, constant=[.1, .5, .5])
    value = dict(life=0, policy='reward', checkpoint=256, replica=0, eval_id=source['eval_id'],
        predictions=targets.tolist(), constant=prefix['constant'], prefix_updates=123, seconds=0.,
        learning_counts=dict(vector_predictions=3, component_predictions=9, table_lookups=288))
    result = analysis.diagnostic(value, source, prefix)
    assert all(result['checks'].values()) and result['sum_squared_error'] == [0., 0., 0.]
    value['predictions'][0][1] = 2.
    assert analysis.diagnostic(value, source, prefix)['out_of_range'][1] == 1
    value['constant'] = [1., 1., 1.]
    assert not analysis.diagnostic(value, source, prefix)['checks']['diagnostic_training_prefix']
    value['policy'] = 'risk_goal'
    assert not analysis.diagnostic(value, source, prefix)['checks']['diagnostic_source_path']


def test_saved_vector_model_rejects_one_head_update_mismatch(tmp_path, monkeypatch):
    folder = tmp_path / 'run'; folder.mkdir()
    path = folder / 'cp.npz'
    meta = dict(schema='acfqp.policy_consequences.v126', radix=11,
        components=list(analysis.COMPONENTS), updates=10, head_updates=[10]*3)
    def write():
        np.savez_compressed(path, metadata=json.dumps(meta), indices=np.array([0, 9]), values=np.array([1., 2.]))
    write()
    cp = dict(model_ref='cp.npz', model_bytes=path.stat().st_size, updates=10,
        save_counts=dict(checkpoint_saves=1, checkpoint_scanned_parameters=3*4*11**6, checkpoint_saved_parameters=2))
    monkeypatch.chdir(tmp_path)
    assert analysis.model_valid(Path('run').resolve(), cp)
    meta['head_updates'][2] += 1; write(); cp['model_bytes'] = path.stat().st_size
    assert not analysis.model_valid(folder, cp)


def test_full_runner_schema_reconciles_without_recharging_frozen_games(tmp_path, monkeypatch):
    from scripts import run_controlled_predictive_policy_consequences_v126 as runner
    folder = tmp_path / 'run'; folder.mkdir()
    inherited = dict(v120_training=[dict(queries=dict(reward=dict(training_blocks=[
        dict(environment_counts=dict(sampled_transitions=22124667))])))], deterministic_prior={})
    capsule = dict(schema='acfqp.policy_consequences.v126.source', snapshots=[], inherited_costs=inherited)
    run = dict(settings=runner.settings(), inherited_costs=inherited, status='complete', seconds=1., lifecycles=[])
    traces = {}
    for life in analysis.LIVES:
        src = dict(life=life, rule={}, models={}); capsule['snapshots'].append(src)
        data = dict(life=life, policies={}, training_trace=f'{life}/train', control_trace=f'{life}/outer',
            diagnostic_trace=f'{life}/diag', peak_weight_bytes=8*4*11**6*8)
        run['lifecycles'].append(data)
        train, outer, diag = [], [], []
        for policy in analysis.POLICIES:
            src['models'][policy] = dict(updates=42, nonzero_weights=7,
                path=str(ROOT / 'reports/controlled_predictive_ntuple_learning_v120' / f'life_{life}' / policy / 'checkpoint_4096.npz'))
            setting = dict(source_updates_before=42, source_updates_after=42,
                source_load_counts=dict(checkpoint_loads=1, checkpoint_loaded_parameters=7), source_load_seconds=.1,
                source_setup_counts=dict(allocated_weight_bytes=4*11**6*8), source_setup_seconds=.1,
                learner_setup_counts=dict(allocated_weight_bytes=3*4*11**6*8), learner_setup_seconds=.1,
                checkpoints=[], training_blocks=[])
            data['policies'][policy] = setting
            block = runner.empty_block(0)
            for episode in range(1024):
                value = row(episode=episode, life=life, query=policy); train.append(value)
                runner.add_training(block, value)
                if (episode+1) % 256 == 0:
                    setting['training_blocks'].append(block); block = runner.empty_block(episode+1)
            constant = (analysis.suffix_targets([4, 8, 16], 'LOST').sum(axis=0)/3).tolist()
            heldout = [row(method='FROZEN_'+policy, query=policy, life=life, replica=r) for r in range(8)]
            outer.extend(heldout)
            for age in analysis.AGES:
                path = folder / f'{life}_{policy}_{age}.npz'
                np.savez_compressed(path, metadata=json.dumps(dict(schema='acfqp.policy_consequences.v126',
                    radix=11, components=list(analysis.COMPONENTS), updates=age*3, head_updates=[age*3]*3)),
                    indices=np.array([0]), values=np.array([1.]))
                setting['checkpoints'].append(dict(age=age, model_ref=path.name,
                    model_bytes=path.stat().st_size, updates=age*3, constant=constant,
                    save_seconds=.1, save_counts=dict(checkpoint_saves=1,
                        checkpoint_scanned_parameters=3*4*11**6, checkpoint_saved_parameters=1)))
                for source in heldout:
                    diag.append(dict(life=life, policy=policy, checkpoint=age, replica=source['replica'],
                        eval_id=source['eval_id'], predictions=analysis.suffix_targets(source['scores'], 'LOST').tolist(),
                        constant=constant, prefix_updates=age*3, seconds=.1,
                        learning_counts=dict(vector_predictions=3, component_predictions=9, table_lookups=288)))
        for method in analysis.LEARNED:
            for age in analysis.AGES:
                for query in analysis.QUERIES:
                    outer.extend(row(method=method, query=query, life=life, replica=r, age=age) for r in range(8))
        for path, rows in ((data['training_trace'], train), (data['control_trace'], outer), (data['diagnostic_trace'], diag)):
            traces[str(folder/path)] = rows
    (folder/'run.json').write_text(json.dumps(run)); (folder/'source_capsule.json').write_text(json.dumps(capsule))
    monkeypatch.setattr(analysis, 'read_rows', lambda path: iter(traces[str(path)]))
    monkeypatch.setattr(analysis.old, 'model_valid', lambda *_args: True)
    monkeypatch.chdir(tmp_path)
    result = analysis.analyze(Path('run'))
    assert result['complete'] and result['primary_complete'], result['checks']
    assert result['costs']['physical_outer_games'] == 832 and result['costs']['logical_outer_rows'] == 1280
    assert result['costs']['actual_environment_transitions'] == (8192+832)*3
    assert result['diagnostics']['lifecycle_mean_mse']['reward']['1024']['learned'] == dict(reward=0., failure=0., success=0.)
