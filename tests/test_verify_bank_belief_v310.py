"""Finite V310 execution-bank and literal-retention audit cases."""
from copy import deepcopy
from pathlib import Path
from statistics import mean
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_bank_belief_v310 as audit


def observed_fit(fours, observations=256):
    memory = audit.Memory()
    memory.consume([2]*fours+[1]*(observations-fours))
    payload = dict(method='LIBRARY', **memory.learned())
    belief = dict(memory=payload, estimated_p_four=memory.probability())
    return belief, dict(fit_memory=deepcopy(payload))


def bank_fits():
    result = {}
    for context, fours in enumerate((26, 129, 231)):
        belief, dataset = observed_fit(fours)
        audit.register_bank_belief(context, belief, dataset, result)
    return result


def execution_row(banks, selected, task='A'):
    belief = banks[str(selected)]
    return dict(evaluation_routes={task:dict(kind='ACTUAL_STAGE_ROUTE', context_id=selected)},
        planning_beliefs={task:deepcopy(belief)},
        arms={arm:dict(evaluations={task:dict(estimated_p_four=belief['estimated_p_four'])})
            for arm in audit.ARMS})


def test_each_created_context_registers_its_own_fit_prefix_and_keeps_a_copy():
    bank_beliefs = {}
    for context, fours in enumerate((26, 129, 231)):
        belief, dataset = observed_fit(fours)
        audit.register_bank_belief(context, belief, dataset, bank_beliefs)
        assert bank_beliefs[str(context)] == belief
        belief['memory']['modules'][0]['alpha'] += 1
        assert bank_beliefs[str(context)]['memory'] == dataset['fit_memory']
    assert len({belief['estimated_p_four'] for belief in bank_beliefs.values()}) == 3


@pytest.mark.parametrize('substitute', ['true_probability', 'current_detector', 'other_bank_fit', 'full_actor_end'])
def test_created_bank_rejects_true_probability_detector_other_bank_and_future_memory(substitute):
    belief, dataset = observed_fit(26)
    if substitute == 'true_probability':
        belief['estimated_p_four'] = .1
    elif substitute == 'current_detector':
        belief, _ = observed_fit(31)
    elif substitute == 'other_bank_fit':
        belief, _ = observed_fit(129)
    else:
        belief, _ = observed_fit(26, 320)
    with pytest.raises(ValueError, match='FIT-prefix belief'):
        audit.register_bank_belief(0, belief, dataset, {})


def test_a_reused_context_cannot_overwrite_its_first_fit_belief():
    banks = bank_fits(); belief, dataset = observed_fit(31)
    with pytest.raises(ValueError, match='exactly once'):
        audit.register_bank_belief(0, belief, dataset, banks)


@pytest.mark.parametrize('selected,decision', [(1, 'REUSE'), (2, 'CONFIRMED_NEW'), (1, 'CAP_REUSE_UNRESOLVED')])
def test_actual_misroute_extra_context_and_cap_fallback_execute_the_selected_bank_belief(selected, decision):
    banks = bank_fits(); row = execution_row(banks, selected)
    row['context_route'] = dict(context_id=selected, decision=decision)
    audit.check_bank_planning_beliefs(row, banks, ('A',))
    row['planning_beliefs']['A'] = deepcopy(banks['0'])
    with pytest.raises(ValueError, match='actual selected bank first FIT belief'):
        audit.check_bank_planning_beliefs(row, banks, ('A',))


@pytest.mark.parametrize('arm', audit.ARMS)
def test_each_paired_arm_must_use_actual_selected_bank_probability(arm):
    banks = bank_fits(); row = execution_row(banks, 1)
    row['arms'][arm]['evaluations']['A']['estimated_p_four'] = banks['0']['estimated_p_four']
    with pytest.raises(ValueError, match='share the actual selected bank planning probability'):
        audit.check_bank_planning_beliefs(row, banks, ('A',))


def test_readonly_probe_uses_selected_bank_even_if_the_first_detector_differs():
    banks = bank_fits(); row = execution_row(banks, 2, 'B')
    row['evaluation_routes']['B']['kind'] = 'READ_ONLY_FIRST_DETECTOR'
    row['detector_belief'] = deepcopy(banks['1'])
    audit.check_bank_planning_beliefs(row, banks, ('B',))
    row['planning_beliefs']['B'] = deepcopy(row['detector_belief'])
    with pytest.raises(ValueError, match='actual selected bank first FIT belief'):
        audit.check_bank_planning_beliefs(row, banks, ('B',))


@pytest.mark.parametrize('location', ['life_bank_beliefs', 'retained_bank'])
def test_mutated_reused_bank_belief_is_rejected_in_final_receipt(location):
    expected = bank_fits(); saved = deepcopy(expected)
    banks = [dict(context_id=int(key), planning_belief=deepcopy(belief)) for key, belief in saved.items()]
    audit.check_stored_bank_beliefs(saved, banks, expected)
    if location == 'life_bank_beliefs':
        saved['0'] = deepcopy(saved['1'])
    else:
        banks[0]['planning_belief'] = deepcopy(saved['1'])
    with pytest.raises(ValueError, match='immutable'):
        audit.check_stored_bank_beliefs(saved, banks, expected)


def test_lifecycle_rejects_the_old_task_indexed_evaluation_belief_store():
    value = dict(stages=dict.fromkeys(audit.STAGES), task_detectors=dict(A={}, B={}),
        evaluation_beliefs=dict(A={}, B={}))
    with pytest.raises(ValueError, match='without task-indexed evaluation beliefs'):
        audit.check_lifecycle(value, {})


def test_lifecycle_endpoint_cell_keeps_selected_bank_probability_as_required_by_v310_summary(monkeypatch):
    """Isolate endpoint assembly from already-covered physical acquisition and costs."""
    belief, dataset = observed_fit(26); detector_b, _ = observed_fit(129)
    prototype = dict(context_id=0, observations=256, fours=26, visits=1)
    def route_check(route, detector, prototypes, looks):
        if route['created']:
            prototypes.append(deepcopy(prototype))
        return 0, route['created']
    monkeypatch.setattr(audit, 'check_detection_route', route_check)
    monkeypatch.setattr(audit, 'check_acquisition', lambda row, world:0)
    monkeypatch.setattr(audit, 'check_probe_route', lambda route, detector, prototypes:0)
    monkeypatch.setattr(audit, 'check_bank_setup', lambda setup:None)
    monkeypatch.setattr(audit, 'check_router_counts', lambda life, worlds:None)
    endpoint = dict(games=32, mean_game_utility=8., wins=32, losses=0,
        cutoffs=0, cutoff_episodes=[], steps=32)
    monkeypatch.setattr(audit, 'check_evaluation', lambda value, life, task, observed, arm:deepcopy(endpoint))
    stages = {}
    for stage in audit.STAGES:
        tasks = ('A',) if stage == 'A1' else ('A','B')
        current = 'B' if stage in ('B1','B2') else 'A'
        values = {arm:dict(fit=dict(method='NONE', trained_afterstates=0, learning_counts={}, target_counts={}),
            parameters_retained=True, processed_training_samples=0, head_updates_before=0, head_updates_after=0,
            evaluations={task:dict(estimated_p_four=belief['estimated_p_four'], game_summaries=[],
                counts={}, representation_counts={}) for task in tasks}) for arm in audit.ARMS}
        stages[stage] = dict(context_route=dict(context_id=0, created=stage=='A1'),
            detector_belief=deepcopy(detector_b if current=='B' else belief),
            fit_snapshot=deepcopy(belief) if stage=='A1' else None,
            dataset=deepcopy(dataset) if stage=='A1' else None,
            context_updates_before={arm:{'0':0} for arm in audit.LEARNERS},
            context_updates_after={arm:{'0':0} for arm in audit.LEARNERS},
            evaluation_routes={task:dict(kind='ACTUAL_STAGE_ROUTE' if task==current else 'READ_ONLY_FIRST_DETECTOR',
                context_id=0) for task in tasks}, planning_beliefs={task:deepcopy(belief) for task in tasks}, arms=values)
    bank = dict(prototype, planning_belief=deepcopy(belief), head_updates=dict.fromkeys(audit.LEARNERS,0),
        head_setup={arm:dict(private_weight_bytes=0) for arm in audit.LEARNERS})
    life = dict(lifecycle=0, parent=0, stages=stages, task_detectors=dict(A=belief,B=detector_b),
        bank_beliefs={'0':deepcopy(belief)}, context_bank=dict(banks=[bank],
            private_weight_bytes_per_arm=dict.fromkeys(audit.LEARNERS,0)))
    worlds = {(0,stage):SimpleNamespace(looks=[], games=[]) for stage in audit.STAGES}
    record, _, _ = audit.check_lifecycle(life, worlds)
    for cell in audit.CELLS:
        audit.equal_tree(record['cells'][cell], dict(estimated_p_four=belief['estimated_p_four'],
            arms={arm:endpoint for arm in audit.ARMS}), 'V310 endpoint cell contract')
    assert record['cells']['B1_B']['estimated_p_four'] != detector_b['estimated_p_four']


def identity(score):
    return dict(game_summaries=[dict(score=score)], counts=dict(planning={}), representation_counts={})


def test_frozen_source_repeats_by_task_and_probability_not_only_task_or_bank():
    previous = {}; banks = bank_fits()
    audit.check_evaluation_identity(previous, identity(4), 'SOURCE', 'A', 0, 0, banks['0'])
    audit.check_evaluation_identity(previous, identity(8), 'SOURCE', 'A', 1, 0, banks['1'])
    audit.check_evaluation_identity(previous, identity(12), 'SOURCE', 'B', 0, 0, banks['0'])
    audit.check_evaluation_identity(previous, identity(4), 'SOURCE', 'A', 2, 0, banks['0'])
    assert len(previous) == 3
    with pytest.raises(ValueError, match='exact paired terminal outcomes'):
        audit.check_evaluation_identity(previous, identity(16), 'SOURCE', 'A', 2, 0, banks['0'])


@pytest.mark.parametrize('arm', audit.LEARNERS)
def test_learner_repeated_identity_keeps_task_context_updates_and_probability(arm):
    previous = {}; banks = bank_fits()
    audit.check_evaluation_identity(previous, identity(4), arm, 'A', 0, 100, banks['0'])
    audit.check_evaluation_identity(previous, identity(8), arm, 'A', 1, 100, banks['1'])
    audit.check_evaluation_identity(previous, identity(12), arm, 'A', 0, 200, banks['0'])
    audit.check_evaluation_identity(previous, identity(16), arm, 'B', 0, 100, banks['0'])
    with pytest.raises(ValueError, match='exact paired terminal outcomes'):
        audit.check_evaluation_identity(previous, identity(20), arm, 'A', 0, 100, banks['0'])


def literal_contrast(values):
    assert len(set(values)) == 1
    value = values[0]
    return dict(mean=value, ci95=[value, value],
        lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(parent):mean(values[parent::4]) for parent in range(4)},
        interval_scope=audit.INTERVAL_SCOPE,
        improved_equal_worse=[64*int(value>0), 64*int(value==0), 64*int(value<0)],
        adverse_lifecycles=list(range(64)) if value<0 else [])


def retention_summary(after_cell):
    records = []
    for life in range(64):
        cells = {}
        for cell in audit.CELLS:
            utilities = dict(SOURCE=6., CONTEXT_MC=7., CONTEXT_LOCAL=8.)
            if cell == after_cell:
                utilities = dict(SOURCE=2., CONTEXT_MC=6., CONTEXT_LOCAL=7.)
            cells[cell] = dict(arms={arm:dict(games=32, mean_game_utility=u, wins=32,
                losses=0, cutoffs=0, cutoff_episodes=[], steps=32) for arm,u in utilities.items()})
        records.append(dict(lifecycle=life, parent=life%4, cells=cells))
    summary = dict(by_lifecycle=records, primary_contrast=audit.PRIMARY, bootstrap_draws=20000,
        bootstrap_seed=31000001, estimator='EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        cells={}, final_ab_contrasts={}, current_task_sequence_contrasts={}, checkpoint_contrasts={}, arms={})
    for cell in audit.CELLS:
        stage, task = cell.split('_')
        summary['cells'][cell] = dict(stage=stage, task=task, paired_contrasts={}, arms={})
        for arm in audit.ARMS:
            values = [row['cells'][cell]['arms'][arm] for row in records]
            summary['cells'][cell]['arms'][arm] = dict(mean_game_utility=mean(v['mean_game_utility'] for v in values),
                **{key:sum(v[key] for v in values) for key in ('games','wins','losses','cutoffs','steps')})
        for left,right in audit.PAIRS:
            summary['cells'][cell]['paired_contrasts'][left+'_minus_'+right] = literal_contrast(
                [a-b for a,b in zip(audit.endpoint(records,cell,left),audit.endpoint(records,cell,right))])
    for left,right in audit.PAIRS:
        for field,cells in (('final_ab_contrasts', ('A3_A','A3_B')),
                ('current_task_sequence_contrasts', ('A1_A','B1_B','A2_A','B2_B','A3_A'))):
            summary[field][left+'_minus_'+right] = literal_contrast([mean(
                row['cells'][cell]['arms'][left]['mean_game_utility']-row['cells'][cell]['arms'][right]['mean_game_utility']
                for cell in cells) for row in records])
    for name,(after,before) in audit.CHECKPOINTS.items():
        summary['checkpoint_contrasts'][name] = {arm:literal_contrast([a-b for a,b in zip(
            audit.endpoint(records,after,arm),audit.endpoint(records,before,arm))]) for arm in audit.ARMS}
    for arm in audit.ARMS:
        rows = [row['cells'][cell]['arms'][arm] for row in records for cell in audit.CELLS]
        value = {key:sum(row[key] for row in rows) for key in ('games','wins','losses','cutoffs','steps')}
        value['mean_final_ab_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A3_A','A3_B')) for row in records)
        value['mean_current_task_sequence_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A1_A','B1_B','A2_A','B2_B','A3_A')) for row in records)
        summary['arms'][arm] = value
    statuses = {name:('SUPPORTED_LOSS' if contrasts['CONTEXT_LOCAL']['mean']<0 else 'SUPPORTED_NONDECREASE')
        for name,contrasts in summary['checkpoint_contrasts'].items()}
    summary.update(complete_game_endpoints=True, primary_local_over_mc_supported=True,
        primary_local_over_mc_status='SUPPORTED_'+audit.INTERVAL_SCOPE, final_net_gain_supported=True,
        final_task_gain_supported=dict(A=True,B=True), final_dual_task_gain_supported=True,
        retention_status=statuses, retention_supported=False, retained_gain_supported=False)
    return summary, records


@pytest.mark.parametrize('name', audit.CHECKPOINTS)
def test_negative_actual_local_retention_is_kept_even_when_source_adjusted_change_is_positive(name):
    after,before = audit.CHECKPOINTS[name]
    summary, records = retention_summary(after)
    audit.check_result_summary(summary, records, 0)
    contrast = summary['checkpoint_contrasts'][name]['CONTEXT_LOCAL']
    assert contrast['mean'] == -1. and summary['retention_status'][name] == 'SUPPORTED_LOSS'
    assert summary['checkpoint_contrasts'][name]['SOURCE']['mean'] == -4.
    summary['checkpoint_contrasts'][name]['CONTEXT_LOCAL'] = literal_contrast([3.]*64)
    summary['retention_status'][name] = 'SUPPORTED_NONDECREASE'
    summary['retention_supported'] = summary['retained_gain_supported'] = True
    with pytest.raises(ValueError, match='signed paired whole-life mean'):
        audit.check_result_summary(summary, records, 0)
