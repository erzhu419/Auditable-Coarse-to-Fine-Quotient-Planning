"""Fresh SOURCE compute survives the consumer and is counted once with targets."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import fresh_confirmation_run_v312 as core

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def recorded_target_shape():
    # Only an actual ledger shape for accounting tests; never experimental input.
    return json.loads((ROOT/'reports/linear_contribution_v311/summary.json').read_text())


def source_compute():
    return dict(worker_cpu_seconds=12., compiler_cpu_seconds=2., coordinator_cpu_seconds=1.,
        full_source_cpu_seconds=15., wall_seconds=7., includes_source_setup_training_checkpoint_save=True)


def test_combined_cost_carries_all_source_cpu_once(recorded_target_shape):
    d = recorded_target_shape
    inherited = dict(d['accounting']['inherited_costs_per_arm']['SOURCE'], fresh_source_compute=source_compute())
    result = core.build_accounting(inherited, d['by_lifecycle'], d['parent_receipts'], 3., 5.)
    expected = 15.+3.+sum(p['cpu_seconds']+p['compiler_cpu_seconds'] for p in d['parent_receipts'])
    assert result['source_and_target_cpu_seconds']==pytest.approx(expected)
    assert result['source_and_target_wall_seconds']==12.
    for costs in result['inherited_costs_per_arm'].values():
        assert costs['fresh_source_compute']==source_compute()


def test_old_value_bundle_is_rejected_before_freezing(tmp_path, recorded_target_shape):
    path = tmp_path/'old-source.json'
    path.write_text(json.dumps(dict(schema=recorded_target_shape['schema'],
        status='EXPERIMENT_COMPLETE', source_provenance=recorded_target_shape['source_provenance'])))
    with pytest.raises(ValueError, match='completed fresh value-training SOURCE'):
        core.run(path, tmp_path/'consumer')
    assert not (tmp_path/'consumer/configuration.json').exists()


def test_completed_fresh_source_consumer_keeps_compute_receipt(tmp_path, monkeypatch, recorded_target_shape):
    d = recorded_target_shape
    source = dict(schema='acfqp.fresh_source.v312', status='SOURCE_COMPLETE',
        source_provenance=deepcopy(d['source_provenance']),
        accounting=dict(inherited_costs_per_arm=dict(SOURCE=dict(
            d['accounting']['inherited_costs_per_arm']['SOURCE'], fresh_source_compute=source_compute()))))
    path = tmp_path/'fresh-source.json'; path.write_text(json.dumps(source))
    receipts = {r['parent']:dict(r, lifecycles=[life for life in d['by_lifecycle'] if life['parent']==r['parent']])
        for r in d['parent_receipts']}
    class Job:
        def __init__(self, value): self.value=value
        def result(self): return self.value
    class Pool:
        def __init__(self, max_workers): assert max_workers==4
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, parent, output): return Job(receipts[parent['parent']])
    monkeypatch.setattr(core, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(core, 'as_completed', lambda jobs: jobs)
    # Seed/endpoint analysis is tested independently; this isolates input handoff.
    monkeypatch.setattr(core, 'summarize', lambda _: d['summary'])
    result = core.run(path, tmp_path/'consumer')
    assert result['schema']=='acfqp.fresh_confirmation.v312'
    assert result['accounting']['inherited_costs_per_arm']['SOURCE']['fresh_source_compute']==source_compute()
    assert result['settings']['seed_evaluation']==312900000000
    assert result['settings']['context_initialization']=='FRESH_SOURCE_PARENT_FOR_EVERY_NEW_BANK'
