"""Finite actual SOURCE traces, TD timing, sparse saves and measured-cost cases."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.fresh_source_v312 import train_game

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_fresh_source_v312 as audit


@pytest.fixture(scope='module')
def actual_source_prefix():
    capsule = json.loads((ROOT/'reports/controlled_predictive_ntuple_learning_v120/source_capsule.json').read_text())
    runtime = ROOT/'reports/fresh_source_v312/test_runtime/independent_source'
    model = NtupleValue(LearnedDynamics.from_payload(capsule['snapshots'][0]['rule']),runtime)
    model.setup_counts['zero_initialized_weight_parameters'] = model.weights.size
    records = [train_game(model,0,episode)[1] for episode in range(2)]
    path = runtime/'prefix_checkpoint.npz'; receipt = model.save(path)
    return records,path,receipt,dict(model.setup_counts)


def test_two_actual_new_source_games_reconstruct_physics_rng_reads_writes_and_td_order(actual_source_prefix):
    records,_,_,_ = actual_source_prefix
    state = audit.SourceTrace(0)
    for record in records:
        state.game(deepcopy(record))
    assert state.games == 2
    assert state.updates == records[-1]['result']['updates_after']
    assert state.raw == sum(row['result']['steps']+2 for row in records)


def test_source_seed_family_is_fresh_and_parent_disjoint():
    assert audit.source_seed(0,0) == 31201010000
    assert audit.source_seed(3,4095) == 31201314095


@pytest.mark.parametrize('field', ['seed','spawned_ranks','scores','decision_updates_before','previous_update_targets'])
def test_actual_source_trace_rejects_old_seed_wrong_physics_and_early_td_update(actual_source_prefix,field):
    value = deepcopy(actual_source_prefix[0][0])
    if field == 'seed':
        value[field] -= 1
        expected = 'fresh ordered risk_goal'
    elif field == 'spawned_ranks':
        value[field][0] = 3-value[field][0]
        expected = 'actual p_four 0.1 world'
    elif field == 'scores':
        value[field][0] += 4
        expected = 'merge score is physically exact'
    elif field == 'decision_updates_before':
        value[field][1] += 1
        expected = 'before updating the previous afterstate'
    else:
        value[field][1] += .5
        expected = 'pre-update chosen action value as TD target'
    with pytest.raises(ValueError,match=expected):
        audit.SourceTrace(0).game(value)


@pytest.mark.parametrize('field', ['td_updates','table_updates','table_lookups','learned_terminal_checks'])
def test_actual_source_learning_work_cannot_omit_updates_multiplicities_or_prediction_reads(actual_source_prefix,field):
    value = deepcopy(actual_source_prefix[0][0]); value['result']['learning_counts'][field] -= 1
    with pytest.raises(ValueError,match='multiplicity-preserving TD parameter writes'):
        audit.SourceTrace(0).game(value)


def test_source_raw_count_cannot_exclude_initial_tiles(actual_source_prefix):
    value = deepcopy(actual_source_prefix[0][0]); value['result']['environment_counts']['initial_spawns'] = 0
    with pytest.raises(ValueError,match='every initial terminal and censored'):
        audit.SourceTrace(0).game(value)


@pytest.mark.parametrize('status', ['WON','LOST','CUTOFF'])
def test_source_terminal_update_and_actual_last_state_exclusion(status):
    updates = 10-int(status!='LOST')
    value = dict(terminal_update=status=='LOST', analytic_terminal=status=='WON',
        censored_last_update=status=='CUTOFF', terminal_update_target=-4. if status=='LOST' else None,
        result=dict(updates_after=40+updates))
    assert audit.check_terminal_update(value,status,10,40) == updates
    value['result']['updates_after'] += 1
    with pytest.raises(ValueError,match='winning and cutoff last-state exclusions'):
        audit.check_terminal_update(value,status,10,40)


def test_terminal_loss_target_is_minus_four_not_a_win_bonus():
    value = dict(terminal_update=True, analytic_terminal=False, censored_last_update=False,
        terminal_update_target=4., result=dict(updates_after=10))
    with pytest.raises(ValueError,match='LOST fits its final afterstate once'):
        audit.check_terminal_update(value,'LOST',10,0)


def test_final_sparse_checkpoint_preserves_the_actual_new_update_history(actual_source_prefix):
    records,path,receipt,setup = actual_source_prefix
    state = audit.SourceTrace(0)
    for value in records:
        state.game(value)
    saved = audit.check_checkpoint(path,state,receipt,setup)
    assert saved['checkpoint_saves'] == 1 and saved['checkpoint_scanned_parameters'] == 4*11**6
    wrong = dict(receipt,updates=receipt['updates']-1)
    with pytest.raises(ValueError,match='independently counted new TD updates'):
        audit.check_checkpoint(path,state,wrong,setup)


def test_new_source_cpu_includes_compiler_once_without_readding_setup_and_save():
    value = dict(worker_cpu_seconds=7.,compiler_cpu_seconds=2.,coordinator_cpu_seconds=1.,
        full_source_cpu_seconds=10.,includes_source_setup_training_checkpoint_save=True)
    audit.check_source_compute(value)
    value['full_source_cpu_seconds'] += 1.
    with pytest.raises(ValueError,match='exactly once'):
        audit.check_source_compute(value)
