"""Compact receipt failures that change the V294 accounting or science verdict."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_conditional_bellman_v294 as audit


def fit_fixture(arm):
    banks=2 if arm.endswith('CONDITIONED') else 1;mc=arm.startswith('MC')
    game=dict(steps=3,status='WON')
    predictions=2 if mc else 4
    counts=dict(td_updates=2,table_update_occurrences=64*banks,residual_error_subtractions=2,
        skipped_winning_afterstates=1,game_sort_items=64,address_occurrence_count_visits=64,
        weighted_residual_accumulations=64*banks,game_unique_addresses=8,parameter_write_events=8*banks,
        normalization_divisions=8*banks,parameter_update_multiplications=8*banks,game_parameter_commits=1,
        source_table_lookups=32*predictions,residual_table_lookups=32*banks*predictions,
        context_basis_calls=2 if banks==2 else 0,value_predictions=predictions,
        suffix_target_assignments=3 if mc else 0,suffix_reward_additions=3 if mc else 0,
        expected_control_targets=0 if mc else 2,expected_spawn_outcomes=0 if mc else 4,
        spawn_probability_products=0 if mc else 4,spawn_probability_sums=0 if mc else 4)
    def sample(step):return dict(step=step,target=4.,prediction_before_update=1.,error=3.,model_p_four=.47)
    receipt=dict(target_kind='MC' if mc else 'EXPECTED_CONTROL',conditioned=banks==2,alpha=.0025,
        fitted_games=1,fitted_steps=3,trained_afterstates=2,counts=counts,
        learning_counts=dict(td_updates=2,table_updates=8*banks,table_update_occurrences=64*banks),
        first_sample=sample(0),last_sample=sample(1))
    return receipt,game


@pytest.mark.parametrize('arm',audit.ARMS[1:])
def test_target_operator_and_conditioned_write_counts_remain_distinct(arm):
    fit,game=fit_fixture(arm)
    assert audit.check_fit(fit,game,arm)==(2,16 if arm.endswith('CONDITIONED') else 8)
    fit['counts']['parameter_write_events']=fit['counts']['td_updates']
    with pytest.raises(ValueError,match='actual writes'):audit.check_fit(fit,game,arm)


def test_winning_afterstate_cannot_be_credited_as_a_training_sample():
    fit,game=fit_fixture('MC_BOARD');fit['trained_afterstates']=3
    with pytest.raises(ValueError,match='sample inventory'):audit.check_fit(fit,game,'MC_BOARD')


def test_heldout_error_uses_complete_game_equal_weights_and_same_inventory():
    games=[dict(episode=1,steps=2,status='LOST'),dict(episode=2,steps=101,status='WON')]
    rows=[dict(metadata=g,count=g['steps']-(g['status']=='WON'),bias=e,mse=e*e,mae=e,
        mean_prediction=e+4.,mean_factual_future_utility=4.) for g,e in zip(games,(1.,3.))]
    value=dict(game_metrics=rows,metrics=dict(bias=2.,mse=5.,mae=2.),target_counts=dict(
        suffix_games=2,suffix_target_assignments=103,suffix_reward_additions=103,skipped_winning_afterstates=1))
    assert audit.check_heldout(value,games)['mse']==5.
    value['metrics']['mse']=(2+900)/102
    with pytest.raises(ValueError,match='equal-weight'):audit.check_heldout(value,games)


def head_fixture():
    n=4*11**6;nb=8*n
    life=dict(dataset=dict(snapshots={p:dict(estimated_p_four=v) for p,v in zip(audit.PHASES,(.12,.48,.15))}),
        arms={},head_setups={},retained_A_setups={},materializations=[])
    for arm in audit.ARMS[1:]:
        banks=2 if arm.endswith('CONDITIONED') else 1
        phases={p:dict(snapshot=dict(value_updates=u)) for p,u in zip(audit.PHASES,(2,5,8))}
        life['arms'][arm]=dict(phases=phases)
        setup=dict(allocated_residual_parameters=banks*n,zero_initialized_residual_parameters=banks*n,
            allocated_residual_bytes=banks*nb,source_parameters_shared=n)
        life['head_setups'][arm]=dict(setup_counts=setup,residual_bytes_created=banks*nb)
        life['retained_A_setups'][arm]=dict(setup_counts=dict(setup,residual_parameters_copied=banks*n,
            residual_bytes_copied=banks*nb),residual_bytes_created=banks*nb,origin_value_updates=2)
        slots=[(arm+'_'+p+'_CURRENT',p,p) for p in audit.PHASES]
        slots += [(arm+'_'+p+'_FIXED_A','A',p) for p in ('B','A_prime')]
        slots += [(arm+'_B_A_PARAMETERS','B','A')]
        for purpose,belief,prefix in slots:
            life['materializations'].append(dict(purpose=purpose,model_p_four=life['dataset']['snapshots'][belief]['estimated_p_four'],
                conditioned=banks==2,private_weight_bytes=nb,origin_residual_updates=phases[prefix]['snapshot']['value_updates'],
                setup_counts=dict(allocated_weight_parameters=n,source_parameters_copied=n,
                    allocated_weight_bytes=nb,source_weight_bytes_copied=nb),
                blending_counts=dict(source_anchor_parameters_copied=n,source_anchor_bytes_copied=nb,
                    effective_table_parameters_scanned=banks*n,effective_table_multiplications=banks*n,
                    effective_table_additions=banks*n,effective_table_parameter_writes=banks*n,
                    allocated_blending_scratch_bytes=nb)))
    return life


def test_saved_A_residuals_read_current_B_p_with_original_A_parameter_prefix():
    life=head_fixture();audit.check_head_inventory(life)
    saved=next(r for r in life['materializations'] if r['purpose']=='BELLMAN_CONDITIONED_B_A_PARAMETERS')
    saved['model_p_four']=.12
    with pytest.raises(ValueError,match='observed-p'):audit.check_head_inventory(life)
    saved['model_p_four']=.48;saved['origin_residual_updates']=0
    with pytest.raises(ValueError,match='head prefix'):audit.check_head_inventory(life)


def test_materialized_head_counts_both_source_copies_and_every_bank_blend():
    life=head_fixture();audit.check_head_inventory(life)
    life['materializations'][0]['setup_counts']['source_weight_bytes_copied']=0
    with pytest.raises(ValueError,match='initialization costs'):audit.check_head_inventory(life)


def test_fresh_ranking_and_science_families_have_no_overlap():
    science={audit.evaluation_seed(l,p,g) for l in range(16) for p in range(3) for g in range(32)}
    ranking={audit.ranking_seed(l,p,a,r) for l in range(16) for p in range(3) for a in range(3) for r in range(32)}
    assert len(science)==1536 and len(ranking)==4608 and science.isdisjoint(ranking)
    assert min(science)==294900010000 and min(ranking)==294600010000
    assert all(s not in science|ranking for s in (29400003001,29400003002))


def test_signed_error_contrast_preserves_every_negative_and_worse_life():
    values=[-1.,-2.,3.,0.]*4
    saved=dict(mean=0.,ci95=[0.,0.],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(p):values[p] for p in range(4)},interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        positive_zero_negative=[4,4,8],negative_lifecycles=[i for i,v in enumerate(values) if v<0],
        better_equal_worse=[8,4,4],worse_lifecycles=[i for i,v in enumerate(values) if v>0])
    audit.check_contrast(saved,values,True,True)
    saved['worse_lifecycles']=[]
    with pytest.raises(ValueError,match='lower error'):audit.check_contrast(saved,values,True,True)


def test_full_science_summary_schema_and_no_proxy_substitution():
    from test_conditional_bellman_analysis_v294 import cohort
    from acfqp.science.conditional_bellman_analysis_v294 import analyze
    result=analyze(cohort(),draws=20);result['bootstrap_draws']=20000
    records=deepcopy(result['by_lifecycle'])
    audit.check_summary(result,records)
    result['net_gain_supported']=False
    with pytest.raises(ValueError,match='independent control gain'):audit.check_summary(result,records)
