"""Real saved-array separation, evaluator binding, paired primary and cutoff HOLD."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_component_heads_v322 as audit


def saved_heads(tmp_path, arm='REWARD_ONLY'):
    from test_native_reward_targets_v321 import fixture
    from acfqp.science.closed_loop_versions_v313 import save_version, snapshot_weights
    native = fixture()
    source = dict(parent=0, checkpoint='saved_source_fixture.npz')
    first_version = save_version(native, source, 0, 0, 'FIRST_LOCAL', 0, tmp_path/'FIRST_LOCAL_v0.npz')
    full = SimpleNamespace(kind=native.kind, model=native.model, updates=native.updates,
        reward_weights=native.reward_weights.copy(), risk_weights=native.risk_weights.copy())
    chain = [first_version]
    indices = np.arange(full.reward_weights.size).reshape(full.reward_weights.shape)
    for number in (1, 2):
        before = snapshot_weights(full)
        full.reward_weights += (indices % 13)*.006*number
        full.risk_weights += (indices % 11)*.04*number
        full.updates += 16384
        chain.append(save_version(full, source, 0, 0, 'NSTEP_QUERY', number,
            tmp_path/f'NSTEP_QUERY_v{number}.npz', base=chain[-1], previous=before))
    hybrid = SimpleNamespace(kind=native.kind, model=native.model, updates=native.updates,
        reward_weights=(full.reward_weights if arm == 'REWARD_ONLY' else native.reward_weights).copy(),
        risk_weights=(native.risk_weights if arm == 'REWARD_ONLY' else full.risk_weights).copy())
    version = save_version(hybrid, source, 0, 0, arm, 1, tmp_path/f'{arm}_v1.npz',
        base=first_version, previous=snapshot_weights(native))
    reward = 'NSTEP_QUERY' if arm == 'REWARD_ONLY' else 'FIRST_LOCAL'
    win = 'FIRST_LOCAL' if arm == 'REWARD_ONLY' else 'NSTEP_QUERY'
    assembly = dict(method='SAVED_COMPONENT_CROSSOVER_NO_FIT', reward_source=reward, win_source=win,
        reward_source_versions=chain if reward == 'NSTEP_QUERY' else chain[:1],
        win_source_versions=chain if win == 'NSTEP_QUERY' else chain[:1],
        new_fit_updates=0, weights_frozen=True, parameter_updates_counter=native.updates,
        component_copy_parameters=native.reward_weights.size, component_copy_bytes=native.reward_weights.nbytes,
        complete_component_equality=True, cpu_seconds=0., wall_seconds=0.)
    identity = dict(lifecycle=0, parent=0, context_id=0, arm='NSTEP_QUERY')
    weights = native.model.weights.reshape(-1)
    first = audit.reconstruct(weights, source['checkpoint'], identity, chain[:1])
    updated = audit.reconstruct(weights, source['checkpoint'], identity, chain)
    return dict(item=dict(head_version=version, assembly=assembly), arm=arm, first=first, updated=updated,
        chain=chain, source_weights=weights, checkpoint=source['checkpoint'], identity=identity), native


@pytest.mark.parametrize('arm', audit.NEW_ARMS)
def test_actual_saved_first_chain_hybrid_tables_and_supported_h2_match_literal_reader(tmp_path, arm):
    # A crossed tensor or reconstructed sparse-write order error changes the mechanism.
    from test_native_reward_targets_v321 import BOARD
    from verify_closed_loop_v313 import equal_tree, literal_choose
    value, native = saved_heads(tmp_path, arm)
    head = audit.check_hybrid(**value)
    native.reward_weights.flags.writeable = native.risk_weights.flags.writeable = True
    native.reward_weights[:] = head.reward.reshape(native.reward_weights.shape)
    native.risk_weights[:] = head.terminal.reshape(native.risk_weights.shape)
    native.freeze()
    actual = native.choose(BOARD, .375)
    expected = literal_choose(BOARD, head.reward, head.terminal, 'LOCAL_RISK', .375, radix=native.radix)
    equal_tree({key: actual[key] for key in expected}, expected, 'literal saved-component H2 agrees with the supported native evaluator entrypoint')
    unchanged = 'terminal' if arm == 'REWARD_ONLY' else 'reward'
    assert value['item']['head_version'][unchanged+'_indices_count'] == 0
    assert value['item']['head_version']['updates'] == value['chain'][0]['updates']


@pytest.mark.parametrize('arm', audit.NEW_ARMS)
def test_changed_selected_sparse_parameter_is_rejected(tmp_path, arm):
    # Reading the full tables must detect a wrong saved component, not just metadata.
    value, _ = saved_heads(tmp_path, arm)
    receipt = value['item']['head_version']; path = Path(receipt['file'])
    with np.load(path) as saved: arrays = {name: saved[name].copy() for name in saved.files}
    component = 'reward' if arm == 'REWARD_ONLY' else 'terminal'
    arrays[component+'_values'][0] += .1
    np.savez_compressed(path, **arrays); receipt['saved_bytes'] = path.stat().st_size
    with pytest.raises(ValueError, match='complete hybrid table'):
        audit.check_hybrid(**value)


@pytest.mark.parametrize('field', ['win_source', 'new_fit_updates', 'weights_frozen', 'component_copy_bytes'])
def test_changed_component_ownership_fit_or_paid_copy_is_rejected(tmp_path, field):
    value, _ = saved_heads(tmp_path)
    assembly = value['item']['assembly']
    assembly[field] = {'win_source': 'NSTEP_QUERY', 'new_fit_updates': 1,
        'weights_frozen': False, 'component_copy_bytes': assembly['component_copy_bytes']+8}[field]
    with pytest.raises(ValueError, match='assembly records'):
        audit.check_hybrid(**value)


def test_hybrid_cannot_invent_training_updates_or_another_base(tmp_path):
    value, _ = saved_heads(tmp_path); value['item']['head_version']['updates'] += 16384
    with pytest.raises(ValueError, match='updates remain the FIRST'):
        audit.check_hybrid(**value)
    value['item']['head_version']['updates'] = value['chain'][0]['updates']
    value['item']['head_version']['base_file'] = value['chain'][-1]['file']
    with pytest.raises(ValueError, match='actual FIRST v0'):
        audit.check_hybrid(**value)


def test_actual_prior_evaluation_binding_detects_wrong_head_seed_and_cost():
    # A correct parameter file evaluated under a different head/stream is invalid.
    root = Path(__file__).resolve().parents[1]
    row = json.loads((root/'reports/reward_targets_v321/summary.json').read_text())['by_lifecycle'][0]
    value = row['final_evaluations']['A']['NSTEP_QUERY']; version = value['head_version']
    belief = row['initial']['A']['planning_belief']['estimated_p_four']
    actual = audit.check_evaluation(value, 0, 'A', belief, version)
    assert actual == np.mean([game['utility'] for game in value['game_summaries']])
    corrupt = deepcopy(value); corrupt['head_version'] = row['initial']['A']['head_version']
    with pytest.raises(ValueError, match='actual immutable own head'):
        audit.check_evaluation(corrupt, 0, 'A', belief, version)
    corrupt = deepcopy(value); corrupt['game_summaries'][0]['seed'] += 1
    with pytest.raises(ValueError, match='paired V321'):
        audit.check_evaluation(corrupt, 0, 'A', belief, version)
    corrupt = deepcopy(value); corrupt['counts']['environment']['raw_tile_productions'] += 1
    with pytest.raises(ValueError, match='winning-action spawns'):
        audit.check_evaluation(corrupt, 0, 'A', belief, version)


def test_frozen_reader_configuration_matches_producer():
    from acfqp.science.component_heads_run_v322 import configuration
    source = Path(__file__).resolve().parents[1]/'reports/reward_targets_v321/summary.json'
    assert configuration(source) == audit.expected_configuration(source)


def records(rows):
    return [dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={task: {arm:
        float(np.mean([game['utility'] for game in item['evaluation']['game_summaries']]))
        for arm, item in cells.items()} for task, cells in row['cells'].items()}) for row in rows]


def test_independent_paired_effects_keep_primary_growth_and_retention_separate():
    from test_component_heads_analysis_v322 import cohort
    from acfqp.science.component_heads_analysis_v322 import summarize
    rows = cohort(); result = summarize(rows)
    audit.check_analysis(result, records(rows), rows)
    corrupt = deepcopy(result); corrupt['primary'] = corrupt['final_ab_contrasts']['REWARD_ONLY_minus_FIRST_LOCAL']
    with pytest.raises(ValueError, match='sole primary cannot be swapped'):
        audit.check_analysis(corrupt, records(rows), rows)
    corrupt = deepcopy(result); corrupt['final_ab_contrasts']['WIN_ONLY_minus_FIRST_LOCAL']['lifecycle_values']['0'] += 1
    with pytest.raises(ValueError, match='paired component effect vector'):
        audit.check_analysis(corrupt, records(rows), rows)
    corrupt = deepcopy(result); corrupt['restored_growth_supported'] = False
    with pytest.raises(ValueError, match='separate evidence requirements'):
        audit.check_analysis(corrupt, records(rows), rows)


@pytest.mark.parametrize('arm', ['FIRST_LOCAL', 'REWARD_ONLY'])
def test_any_reused_or_new_cutoff_holds_every_terminal_contrast(arm):
    from test_component_heads_analysis_v322 import cohort
    from acfqp.science.component_heads_analysis_v322 import summarize
    rows = cohort(); rows[3]['cells']['B'][arm]['evaluation']['game_summaries'][2]['status'] = 'CUTOFF'
    result = summarize(rows); audit.check_analysis(result, records(rows), rows)
    assert result['primary'] is None and not result['bootstrap_executed']
    corrupt = deepcopy(result); corrupt['task_contrasts']['A']['REWARD_ONLY_minus_NSTEP_QUERY'] = dict(mean=1.)
    with pytest.raises(ValueError, match='suppresses every terminal'):
        audit.check_analysis(corrupt, records(rows), rows)
