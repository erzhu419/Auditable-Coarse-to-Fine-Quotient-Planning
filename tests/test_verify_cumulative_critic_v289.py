from pathlib import Path
from copy import deepcopy
from statistics import mean
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_cumulative_critic_v289 as audit


def test_anchors_use_only_fixed_nonwinning_time_positions():
    assert audit.anchor_positions(10)==[0,3,6,9]
    assert audit.anchor_positions(5)==[0,1,2,4]
    assert audit.anchor_positions(3)==[0,1,2]
    assert audit.anchor_positions(1)==[0]
    with pytest.raises(ValueError):audit.anchor_positions(0)


def test_fit_prefixes_have_exact_ceil_quarters_and_full_endpoint():
    assert audit.fixed_prefixes(110)==[0,28,55,83,110]
    assert audit.fixed_prefixes(113)==[0,29,57,85,113]


def test_factual_mc_target_excludes_current_score_and_winning_afterstate():
    assert audit.factual_targets([2048,4096,8192],'LOST')==[2.,0.,-4.]
    assert audit.factual_targets([2048,4096,8192],'WON')==[10.,8.]


def test_anchor_errors_weight_games_equally_not_all_samples():
    anchors=[dict(episode=0,target=0.)]+[dict(episode=1,target=0.)]*4
    metrics=audit.panel_metrics(anchors,[4.,0.,0.,0.,0.])
    assert metrics==dict(bias=2.,mse=8.,mae=2.)
    with pytest.raises(ValueError):audit.panel_metrics(anchors,[4.])


def test_h2_reference_uses_validation_suffix_plus_first_score():
    queries={'UP':dict(first_score=2048,discovery=[100.]*32,validation=[3.]*32),
             'LEFT':dict(first_score=0,validation=[5.]*32)}
    assert audit.h2_reference('UP',queries)==4.
    assert audit.h2_reference('LEFT',queries)-audit.h2_reference('UP',queries)==1.
    with pytest.raises(ValueError):audit.h2_reference('RIGHT',queries)


def test_positive_runs_preserve_recovery_and_zero_boundaries():
    assert audit.positive_run_description([0.,2.,3.,-1.,0.,2.])==dict(
        first_positive_index=1,positive_runs=[[1,2],[5,5]],final_positive_run=[5,5])
    assert audit.positive_run_description([0.,2.,-1.])['final_positive_run'] is None


def test_h2_argmax_ties_and_reference_delta_have_correct_direction():
    queries={'UP':dict(first_score=2048,validation=[3.]*32),
             'LEFT':dict(first_score=0,validation=[5.]*32)}
    row=dict(frozen_action_values={'UP':3.,'LEFT':2.},mc_action_values={'UP':4.,'LEFT':4.},
        frozen_action='UP',mc_action='LEFT',reference_q={'UP':4.,'LEFT':5.})
    metrics=audit.h2_board_metrics(row,queries)
    assert metrics==dict(action_disagreement=1,validation_utility_delta=1.,
        frozen_reference_regret=1.,mc_reference_regret=0.,predicted_frozen_action_margin=0.)
    row['mc_action']='UP'
    with pytest.raises(ValueError,match='argmax'):audit.h2_board_metrics(row,queries)


def test_positive_mse_is_harm_but_positive_reference_return_is_gain():
    values=[-1.,1.]*8
    signed=dict(mean=0.,ci95=[0.,0.],lifecycle_values={str(i):v for i,v in enumerate(values)},
        negative_equal_positive=[8,0,8],parent_means={str(p):mean(values[p::4]) for p in range(4)},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',quality_direction='negative_is_better',
        improved_equal_worse=[8,0,8],adverse_lifecycles=list(range(1,16,2)))
    audit.check_contrast(signed,values,'negative_is_better')
    signed.update(quality_direction='positive_is_better',adverse_lifecycles=list(range(0,16,2)))
    audit.check_contrast(signed,values,'positive_is_better')
    signed['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='direction'):audit.check_contrast(signed,values,'positive_is_better')


def test_changed_reconstruction_cpu_is_new_cost_not_changed_acquisition():
    previous=dict(games=[dict(steps=3)],costs=dict(full_A_raw_tiles=5,processing_cpu_seconds=1.))
    saved=deepcopy(previous);saved['costs']['processing_cpu_seconds']=2.
    audit.check_dataset(saved,previous)
    saved['costs']['full_A_raw_tiles']=6
    with pytest.raises(ValueError,match='acquisition'):audit.check_dataset(saved,previous)


def test_anchor_prediction_error_corruption_is_rejected():
    expected=audit.panel_metrics([dict(episode=0,target=1.)],[3.])
    saved=dict(expected);saved['mse']=3.
    with pytest.raises(ValueError,match='anchor errors'):
        audit.compare_metrics(saved,expected,'anchor errors')
