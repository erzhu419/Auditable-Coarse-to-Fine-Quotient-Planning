"""Fresh SOURCE provenance and complete nonduplicated source/target compute cases."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_fresh_confirmation_v312 as audit


def compute():
    source = dict(worker_cpu_seconds=10., compiler_cpu_seconds=3., coordinator_cpu_seconds=2.,
        full_source_cpu_seconds=15., wall_seconds=8., includes_source_setup_training_checkpoint_save=True)
    target = dict(worker_cpu_seconds=7., compiler_cpu_seconds=2., coordinator_cpu_seconds=1.,
        wall_seconds=5., source_and_target_cpu_seconds=25., source_and_target_wall_seconds=13.)
    return target, source


def fresh_document():
    _, measured = compute()
    provenance = dict(parents=[dict(parent=i, checkpoint=f'/new_sources/parent_{i}.npz', updates=4096+i)
        for i in range(4)])
    value = dict(schema='acfqp.fresh_source.v312',status='SOURCE_COMPLETE',source_provenance=provenance,
        accounting=dict(inherited_costs_per_arm=dict(SOURCE=dict(source_training_raw_tiles=100000,
            source_training_games=16384, source_training_environment_counts=dict(initial_spawns=32768,sampled_transitions=67232),
            source_training_seconds=8., dynamics_raw_tiles=49069, dynamics_costs={},fresh_source_compute=measured))))
    return value, deepcopy(provenance)


def test_measured_new_source_and_target_cpu_and_sequential_wall_are_paid_once():
    target,source = compute()
    audit.check_source_target_compute(target,source)


@pytest.mark.parametrize('field', ['source_and_target_cpu_seconds','source_and_target_wall_seconds'])
def test_combined_cost_cannot_drop_or_double_add_source_work(field):
    target,source = compute(); target[field] += 1.
    with pytest.raises(ValueError,match='both retained|pays complete new SOURCE'):
        audit.check_source_target_compute(target,source)


def test_source_cpu_cannot_omit_compiler_time_or_count_contained_setup_again():
    target,source = compute(); source['full_source_cpu_seconds'] = 12.
    with pytest.raises(ValueError,match='without duplicate contained components'):
        audit.check_source_target_compute(target,source)
    target,source = compute(); source['full_source_cpu_seconds'] = 16.
    with pytest.raises(ValueError,match='without duplicate contained components'):
        audit.check_source_target_compute(target,source)


def test_source_setup_training_and_final_save_must_be_in_full_source_cpu():
    target,source = compute(); source['includes_source_setup_training_checkpoint_save'] = False
    with pytest.raises(ValueError,match='includes setup, actual training'):
        audit.check_source_target_compute(target,source)


def test_all_six_common_source_fields_and_complete_fresh_compute_are_carried():
    value,provenance = fresh_document()
    costs = audit.check_fresh_source_document(value,provenance)
    assert costs == value['accounting']['inherited_costs_per_arm']['SOURCE']
    assert len(costs) == 7


@pytest.mark.parametrize('schema,status', [('acfqp.linear_contribution.v311','EXPERIMENT_COMPLETE'),
    ('acfqp.fresh_source.v312','SOURCE_RUNNING')])
def test_old_value_parents_or_unfinished_new_source_are_not_fresh_confirmation_inputs(schema,status):
    value,provenance = fresh_document(); value.update(schema=schema,status=status)
    with pytest.raises(ValueError,match='terminal four-parent newly trained SOURCE'):
        audit.check_fresh_source_document(value,provenance)


def test_target_provenance_cannot_substitute_a_different_source_checkpoint():
    value,provenance = fresh_document(); provenance['parents'][0]['checkpoint'] = '/old_source/model.npz'
    with pytest.raises(ValueError,match='actual newly trained SOURCE parents'):
        audit.check_fresh_source_document(value,provenance)


def test_all_four_new_4096_game_source_histories_are_required():
    value,provenance = fresh_document()
    value['accounting']['inherited_costs_per_arm']['SOURCE']['source_training_games'] = 4096
    with pytest.raises(ValueError,match='four new 4096-game SOURCE histories'):
        audit.check_fresh_source_document(value,provenance)


def test_v312_independent_evaluation_family_cannot_reuse_v311_task_seeds():
    assert audit.evaluation_seed(3,'B',7) == 312903100007
    assert audit.warmup_seed(3,'B2',7) == 312103300007
    assert audit.training_seed(3,'A3') == 312230400000


def test_old_bootstrap_seed_cannot_reenter_fresh_source_confirmation():
    saved = dict(by_lifecycle=[],primary_contrast=audit.PRIMARY,bootstrap_draws=20000,bootstrap_seed=31100001,
        estimator='EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES')
    with pytest.raises(ValueError,match='frozen new-sequence final equal-task'):
        audit.check_result_summary(saved,[],0)


def test_fresh_endpoint_metadata_still_includes_actual_selected_bank_probability():
    records = [dict(cells=dict(A1_A=dict(estimated_p_four=.13,arms={})))]
    saved = dict(by_lifecycle=[dict(cells=dict(A1_A=dict(arms={})))])
    with pytest.raises(ValueError,match='A1_A fields'):
        audit.check_result_summary(saved,records,0)
