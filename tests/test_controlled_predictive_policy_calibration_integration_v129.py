"""Exercise the complete V129 file schema without loading models or sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

import pytest

from scripts import run_controlled_predictive_policy_calibration_v129 as runner
from test_analyze_controlled_predictive_policy_calibration_v129 import (
    ROOT, analysis, control, fit_row, original, snapshot,
)


@pytest.fixture(scope='module', autouse=True)
def integration_ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_policy_calibration_v129.integration_checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(tests=1, failures=request.session.testsfailed-before,
        seconds=perf_counter()-started, newly_sampled_environment_transitions=0,
        native_model_calls=0, optimizer_updates=0,
        scope='Full analyzer schema with synthetic in-memory traces; reported fixture transitions are not sampled data'))
    path.write_text(json.dumps(log, indent=2)+'\n')


def test_complete_schema_preserves_all_phases_and_accounts_without_new_sampling(tmp_path, monkeypatch):
    traces, fits, panels, evaluations, cases = {}, [], [], [], []
    snapshots = [snapshot(life) for life in analysis.LIVES]
    for source in snapshots:
        life = source['life']
        state = analysis.expected_state(source)
        loads = {p: dict(source_updates=42, count_updates=100, count_successes=10,
            source_load_counts=dict(checkpoint_loads=1, checkpoint_loaded_parameters=7),
            count_load_counts=dict(checkpoint_loads=1, checkpoint_loaded_addresses=4,
                checkpoint_loaded_count_entries=8),
            source_setup_counts={}, count_setup_counts={}, source_setup_seconds=.01,
            count_setup_seconds=.01, source_load_seconds=.02, count_load_seconds=.03)
            for p in analysis.POLICIES}
        common = dict(life=life, loads=loads, model_state_before=state,
            model_state_after=deepcopy(state))
        training = [original(life, p, episode) for p in analysis.POLICIES for episode in range(1024)]
        rows = [fit_row(row) for row in training]
        traces[Path(source['training_trace'])] = training
        fit_path = f'life_{life}/fit.jsonl.gz'
        traces[tmp_path/fit_path] = rows
        totals = {p: dict(n=0, target_sum=0., anchor_sum=0., residual_sum=0.,
            offset=1., counts=Counter(), setup_counts={}, setup_seconds=.01)
            for p in analysis.POLICIES}
        replay_counts, replay_seconds = Counter(), 0.
        for row in rows:
            total, fitted = totals[row['policy']], row['fit']
            for key in ('n', 'target_sum', 'anchor_sum', 'residual_sum'):
                total[key] += fitted[key]
            total['counts'].update(fitted['work'])
            replay_counts.update(row['replay_counts'])
            replay_seconds += row['replay_seconds']
        fits.append(dict(common, trace=fit_path, episodes={p: 1024 for p in analysis.POLICIES},
            policies=totals, replay_counts=replay_counts, replay_seconds=replay_seconds))

        roots = [original(life, p, method='ROOT_'+p, replica=rep)
            for p in analysis.POLICIES for rep in range(2)]
        panel_path = f'life_{life}/acquisition.jsonl.gz'
        traces[tmp_path/panel_path] = roots
        panels.append(dict(common, trace=panel_path, prediction_counts={}))
        for row in roots:
            for index in (128, 512):
                cases.append(dict(case_id=len(cases), life=life, policy=row['policy'],
                    replica=row['replica'], index=index, source_eval_id=row['eval_id'],
                    available=False, board=None, root_id=None))

        controls = [original(life, p, method='FROZEN_'+p, replica=rep)
            for p in analysis.POLICIES for rep in range(8)]
        controls += [control(life, method, query, rep) for method in analysis.METHODS
            for query in analysis.QUERIES for rep in range(8)]
        forced_path, control_path = f'life_{life}/continuations.jsonl.gz', f'life_{life}/control.jsonl.gz'
        traces[tmp_path/forced_path], traces[tmp_path/control_path] = [], controls
        evaluations.append(dict(common, forced_trace=forced_path, control_trace=control_path,
            peak_weight_bytes=100+life))

    inherited = dict(retained_source_training_transitions=987654, charged_again=False)
    files = {
        'run.json': dict(status='complete', settings=runner.settings(), seconds=1.,
            inherited_costs=inherited, fit_lifecycles=fits, panel_lifecycles=panels, lifecycles=evaluations),
        'source_capsule.json': dict(schema='acfqp.policy_calibration.v129.source',
            snapshots=snapshots, inherited_costs=inherited),
        'calibration.json': dict(schema='acfqp.policy_calibration.v129.frozen',
            lifecycles=[dict(life=life, offsets={p: 1. for p in analysis.POLICIES}) for life in analysis.LIVES]),
        'roster.json': dict(schema='acfqp.policy_calibration.v129.roster', cases=cases,
            roots=[], physical_attempts=0, logical_attempts=0),
    }
    for name, payload in files.items():
        (tmp_path/name).write_text(json.dumps(payload))
    monkeypatch.setattr(analysis, 'read_rows', lambda path: iter(traces[Path(path)]))
    report = analysis.analyze(tmp_path)
    (tmp_path/'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')

    # The formal retained-transition budget is intentionally not synthesized.
    assert {key for key, valid in report['checks'].items() if not valid} == {'source_fit_budget'}
    assert not report['complete'] and not report['primary_complete']
    costs = report['costs']
    assert costs['retained_training_transitions'] == 16384
    assert costs['fitting_counts']['calibration_games'] == 8192
    assert costs['fitting_counts']['source_table_lookups'] == 32*16384
    assert costs['replay_counts']['replay_swipe_calls'] == 16384
    assert costs['source_load_counts']['checkpoint_loads'] == 24
    assert costs['count_load_counts']['checkpoint_loaded_count_entries'] == 24*8
    assert costs['root_acquisition']['games'] == 16
    assert costs['physical_control_games'] == 320 and costs['logical_control_rows'] == 384
    assert costs['physical_forced_attempts'] == costs['logical_forced_attempts'] == 0
    assert costs['actual_new_environment_transitions'] == 672  # Synthetic record accounting only.
    assert costs['fresh_training_environment_transitions'] == costs['model_spawn_samples'] == 0
    assert costs['peak_resident_weight_bytes_per_life'] == 103
    assert report['inherited_work'] == inherited
    assert report['panel_coverage'] == dict(case_slots=32, available_cases=0, unique_roots=0)
    assert report['control']['comparisons']['CAL_LEARNED_minus_UNCAL_LEARNED']['risk8']['mean_deltas']['utility'] == 0.
