"""Finite compact routed receipts, distinct from the new science streams."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_routed_bellman_v295 as audit


def routed_fit():
    def sample(step):return dict(step=step,target=4.,prediction_before_update=1.,error=3.,model_p_four=.47)
    assigned={'0':2,'1':1,'2':0};old={'0':5,'1':5,'2':0};by={}
    for module,n in assigned.items():
        by[module]=dict(trained_afterstates=n,old_value_updates=old[module],new_value_updates=old[module]+n,
            game_unique_addresses=8 if n else 0,
            learning_counts=dict(td_updates=n,table_updates=16 if n else 0,table_update_occurrences=64*n),
            first_sample=sample(0 if module=='0' else 2) if n else None,
            last_sample=sample(1 if module=='0' else 2) if n else None)
    counts=dict(td_updates=3,routed_sample_expert_reads=3,expected_control_targets=3,residual_error_subtractions=3,
        game_sort_items=96,address_occurrence_count_visits=96,routed_gradient_expert_address_visits=96,
        table_update_occurrences=192,weighted_residual_accumulations=192,routed_expert_address_pairs=16,
        routed_expert_parameter_commits=2,game_unique_addresses=8,game_parameter_commits=1,
        parameter_write_events=32,normalization_divisions=32,parameter_update_multiplications=32,
        routed_parameter_pointer_views=3,source_table_lookups=160,residual_table_lookups=320,
        value_predictions=5,context_basis_calls=3,expected_spawn_outcomes=6,
        spawn_probability_products=6,spawn_probability_sums=6)
    fit=dict(routed=True,conditioned=True,target_kind='EXPECTED_CONTROL',alpha=.0025,fitted_games=1,
        fitted_steps=3,trained_afterstates=3,counts=counts,module_updates=assigned,by_module=by,
        learning_counts=dict(td_updates=3,table_updates=32,table_update_occurrences=192),
        residual_pointer_array_bytes=24,dense_expert_weight_stack_bytes=0,
        first_sample=sample(0),last_sample=sample(2))
    return fit,dict(steps=3,status='LOST'),assigned,old


def test_global_samples_exclude_inherited_copies_and_writes_sum_expert_addresses():
    values=routed_fit();assert audit.check_routed_fit(*values)==(3,32)
    fit=values[0];fit['counts']['parameter_write_events']=16
    with pytest.raises(ValueError,match='true routed writes'):audit.check_routed_fit(*values)


def test_inactive_expert_is_not_written_or_credited_samples():
    values=routed_fit();values[0]['by_module']['2']['new_value_updates']=1
    with pytest.raises(ValueError,match='own samples'):audit.check_routed_fit(*values)


def test_pointer_views_do_not_hide_a_dense_weight_stack():
    values=routed_fit();values[0]['dense_expert_weight_stack_bytes']=32
    with pytest.raises(ValueError,match='hidden dense'):audit.check_routed_fit(*values)


def test_science_stream_family_is_fresh_and_pairing_reuses_only_declared_seeds():
    seeds={audit.evaluation_seed(l,p,g) for l in range(16) for p in range(3) for g in range(32)}
    assert len(seeds)==1536 and min(seeds)==295900010000
    assert 29500003001 not in seeds and 294900010000 not in seeds


def route_data():
    games={p:dict(episode=i,start_raw=i*audit.RAW,end_raw=i*audit.RAW+10,
        steps=8,status='LOST',phase=p) for i,p in enumerate(audit.PHASES)}
    timeline={p:[dict(kind='GAME_COMPLETE',raw_index=g['end_raw'],metadata=g,
        pure_phase=p,exclusion_reason=None,fit=True)] for p,g in games.items()}
    timeline['A'].insert(0,dict(kind='created',raw_index=3,previous_module_id=0,module_id=1))
    timeline['B'].insert(0,dict(kind='created',raw_index=audit.RAW+10,previous_module_id=1,module_id=2))
    timeline['A_prime'].insert(0,dict(kind='reactivated',raw_index=2*audit.RAW+3,previous_module_id=2,module_id=1))
    data=dict(warmup_module_ids=[0],warmup_modules=[dict(id=0)],initial_active_module_id=0,routing_timeline=timeline,
        phases={p:dict(fit_games=[g],heldout_games=[]) for p,g in games.items()},
        snapshots={p:dict(memory=dict(active_module_id=1 if p!='B' else 2,
            modules=[dict(id=m) for m in range(2 if p=='A' else 3)])) for p in audit.PHASES},
        costs=dict(routing_event_inventory=dict(created=2,reactivated=1),retained_route_records=6))
    return data,games


def test_before_action_module_uses_consumed_raw_and_excludes_terminal_winning_sample():
    data,games=route_data();audit.check_routes(data)
    assert audit.module_sample_positions(data,games['A'])=={'0':[0],'1':list(range(1,8))}
    # B expert is born only at the terminal spawn; it receives no action label in this game.
    assert audit.module_sample_positions(data,games['B'])=={'1':list(range(8))}
    games['A_prime']['status']='WON'
    assert audit.module_sample_positions(data,games['A_prime'])=={'2':[0],'1':list(range(1,7))}


def test_birth_at_terminal_is_processed_before_fitting_the_completed_game():
    data,_=route_data();data['routing_timeline']['B'].reverse()
    with pytest.raises(ValueError,match='routing must precede'):audit.check_routes(data)


def test_reactivation_preserves_original_known_expert_instead_of_phase_selected_birth():
    data,_=route_data();data['snapshots']['A_prime']['memory']['active_module_id']=0
    with pytest.raises(ValueError,match='actual observed reactivation'):audit.check_routes(data)


def test_counterfactual_birth_copies_its_own_prior_updates_not_current_B_updates():
    n=4*11**6;size=n*8
    receipt=dict(residual_bytes_created=2*size,origin_value_updates=5,seconds=.01,cpu_seconds=.01,
        setup_counts=dict(allocated_residual_bytes=2*size,allocated_residual_parameters=2*n,
            zero_initialized_residual_parameters=2*n,source_parameters_shared=n,
            residual_parameters_copied=2*n,residual_bytes_copied=2*size))
    audit.check_copy(receipt,5)
    # A no-update expert remains at prefix 5 even if the current B expert has advanced to 7.
    with pytest.raises(ValueError,match='own preceding parameter prefix'):audit.check_copy(receipt,7)


def diagnostic_summary():
    def games(utility):return dict(games=32,mean_game_utility=utility,wins=0,losses=32,cutoffs=0,steps=320)
    records=[]
    for life in range(16):
        arms={}
        for arm,values in (('FROZEN',[2.,2.,2.]),('SMOOTH_BELLMAN',[1.,1.,1.]),('ROUTED_BELLMAN',[2.5,1.,1.])):
            phases={p:dict(games(v),heldout=dict(mse=2.,mae=1.,bias=0.),
                retention_probe=games(values[0])) for p,v in zip(audit.PHASES,values)}
            phases['B']['a_head_on_B']=games(values[1] if arm=='FROZEN' else values[1]-.5)
            arms[arm]=dict(mean_game_utility=sum(values)/3,heldout=dict(mse=2.,mae=1.,bias=0.),phases=phases)
        records.append(dict(lifecycle=life,parent=life%4,arms=arms,actual_A_prime_module=1,saved_A_module=0,
            A_prime_same_observed_module=False))
    def contrast(values):
        center=sum(values)/16
        return dict(mean=center,ci95=[center,center],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
            parent_mean_deltas={str(p):sum(values[p::4])/4 for p in range(4)},
            improved_equal_worse=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],
            adverse_lifecycles=[i for i,v in enumerate(values) if v<0],interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')
    summary=dict(by_lifecycle=records,arms={},paired_contrasts={},phase_contrasts={p:{} for p in audit.PHASES},
        correction_contrasts={},retention_contrasts={},science_cutoffs=0,complete_game_endpoints=True,
        net_gain_supported=False,correction_supported=True,actual_A_prime_same_observed_module=0,
        physical_science_games=8704,logical_science_game_references=10752,bootstrap_seed=29500001,bootstrap_draws=20000,
        primary_contrast='ROUTED_BELLMAN_minus_FROZEN',estimator='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES',
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')
    for arm in audit.ARMS:
        row=records[0]['arms'][arm];phases={p:dict(audit.aggregate([r['arms'][arm]['phases'][p] for r in records]),
            heldout=row['heldout'],retention_probe=audit.aggregate([r['arms'][arm]['phases'][p]['retention_probe'] for r in records])) for p in audit.PHASES}
        summary['arms'][arm]=dict(mean_game_utility=row['mean_game_utility'],heldout=row['heldout'],phases=phases,
            **{k:sum(v[k] for v in phases.values()) for k in ('games','wins','losses','cutoffs','steps')})
        summary['correction_contrasts'][arm]=contrast([r['arms'][arm]['phases']['B']['mean_game_utility']-
            r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records])
        summary['retention_contrasts'][arm]={label:dict(contrast([0.]*16),direction='ZERO_OBSERVED_CHANGE')
            for label in ('after_B','restoration','final_vs_A')}
    for left,right in audit.PAIRS:
        name=left+'_minus_'+right
        summary['paired_contrasts'][name]=contrast([r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
        for p in audit.PHASES:summary['phase_contrasts'][p][name]=contrast([r['arms'][left]['phases'][p]['mean_game_utility']-
            r['arms'][right]['phases'][p]['mean_game_utility'] for r in records])
    return summary,records


def test_routing_improvement_and_zero_known_A_change_do_not_replace_net_gain():
    summary,records=diagnostic_summary();audit.check_summary(summary,records)
    assert summary['paired_contrasts']['ROUTED_BELLMAN_minus_SMOOTH_BELLMAN']['mean']>0
    assert summary['paired_contrasts']['ROUTED_BELLMAN_minus_FROZEN']['mean']<0
    summary['net_gain_supported']=True
    with pytest.raises(ValueError,match='independent primary benefit'):audit.check_summary(summary,records)


def test_all_adverse_signed_lives_are_retained():
    summary,records=diagnostic_summary();summary['paired_contrasts']['ROUTED_BELLMAN_minus_FROZEN']['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='adverse lives retained'):audit.check_summary(summary,records)
