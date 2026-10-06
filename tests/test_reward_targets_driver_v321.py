"""Actual old-head reproduction and the pre-acquisition control barrier."""
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import reward_targets_run_v321 as driver
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]


def test_actual_v319_controls_all_banks_rounds_exact_without_new_acquisition():
    # A restoration/order/update mismatch must block new target acquisition.
    previous = json.loads((ROOT/'reports/query_supervision_v319/summary.json').read_text())
    source = previous['source_provenance']['parents'][0]
    out = ROOT/'reports/reward_targets_v321/test_logs/control_fixture'
    runtime = out/'runtime'; runtime.mkdir(parents=True,exist_ok=True)
    template, _ = load_leaf(source,runtime)
    row = driver._control_life(template,source,previous['by_lifecycle'][0],runtime,out)
    assert json.loads((out/'control_receipts/life_0.json').read_text()) == row
    for number in ('1','2'):
        for task in driver.TASKS:
            stage = row['rounds'][number][task]
            assert stage['teacher_unchanged'] and set(stage['arms']) == {'OLD_FACTUAL','OLD_QUERY'}
            assert all(r['new_raw_tiles']==0 for r in stage['control_source_reads'].values())
            for distribution in driver.DISTRIBUTIONS:
                arm = 'OLD_'+distribution.split('_')[0]
                item = stage['arms'][arm]
                expected = previous['by_lifecycle'][0]['rounds'][number][task]['arms'][distribution]['head_version']
                assert item['control_match']['exact'] and item['control_match']['file'] == expected['file']
                assert item['control_match']['arrays_compared'] == 4
                assert item['updates_after']-item['updates_before']==16384


def test_control_failure_blocks_global_acquisition(monkeypatch):
    # A failed control cannot flow into any generative acquisition call.
    previous_path = ROOT/'reports/query_supervision_v319/summary.json'
    out = ROOT/'reports/reward_targets_v321/test_logs/barrier_fixture'
    if (out/'configuration.json').exists(): (out/'configuration.json').unlink()
    def bad_parent(*args, **kwargs):
        assert args[3] == 'control'
        raise ValueError('control mismatch fixture')
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            # Synchronous finite executor: fail before anything can be acquired.
            return function(*args)
    monkeypatch.setattr(driver,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(driver,'_parent',bad_parent)
    with pytest.raises(ValueError,match='control mismatch fixture'):
        driver.run(previous_path,out)
    assert not (out/'control_phase.json').exists() and not (out/'summary.json').exists()


def test_risk_matching_rejects_a_changed_win_parameter(tmp_path):
    # If reward relabeling changes WIN weights the causal intervention is invalid.
    baseline = dict(reward_indices=np.array([2]),reward_values=np.array([1.]),
        terminal_indices=np.array([5]),terminal_values=np.array([.2]))
    np.savez(tmp_path/'old.npz',**baseline)
    changed = dict(baseline,terminal_values=np.array([.3]))
    np.savez(tmp_path/'new.npz',**changed)
    with pytest.raises(ValueError,match='WIN parameters'):
        driver._match_versions(dict(file=str(tmp_path/'new.npz'),updates=1),
            dict(file=str(tmp_path/'old.npz'),updates=1),risk_only=True)
