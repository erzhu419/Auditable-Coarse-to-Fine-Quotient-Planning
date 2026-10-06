"""Net control remains distinct from stored experts and known-context probes."""
from copy import deepcopy

import pytest

from acfqp.science.routed_bellman_analysis_v295 import ARMS,PHASES,PAIRS,PRIMARY,analyze,evaluation_seed
from acfqp.science.conditional_bellman_analysis_v294 import science_seed as previous_seed


def games(life,phase,value):
    return [dict(seed=evaluation_seed(life,phase,i),utility=value,status='LOST',steps=10+i)
            for i in range(32)]


def cohort():
    rows=[]
    for life in range(16):
        snapshots={p:dict(estimated_p_four=probability,memory=dict(active_module_id=module))
            for p,probability,module in zip(PHASES,(.12,.48,.15),(7,9,7))}
        heldout={p:[dict(episode=i*10+1),dict(episode=i*10+2)] for i,p in enumerate(PHASES)}
        arms={}
        for arm,shift in zip(ARMS,(0.,-1.,2.)):
            phases={}
            for i,phase in enumerate(PHASES):
                current=games(life,i,life+i+shift)
                probe=games(life,0,life+shift-(1. if i==1 and arm=='SMOOTH_BELLMAN' else 0.))
                phases[phase]=dict(game_summaries=current,
                    snapshot=dict(estimated_p_four=snapshots[phase]['estimated_p_four'],active_module_id=(7,9,7)[i],
                        selected_value_module_id=(7,9,7)[i] if arm=='ROUTED_BELLMAN' else None),
                    heldout=dict(game_metrics=[dict(metadata=meta,count=count,mse=value+shift,mae=value/2,bias=-1.)
                        for meta,count,value in zip(heldout[phase],(4,99),(10.,20.))]),
                    retention_probe=dict(game_summaries=current if i==0 else probe,
                        model_p_four=.12,environment_p_four=.1,depth=2,shared_with_current=i==0,
                        selected_value_module_id=7 if arm=='ROUTED_BELLMAN' else None))
            phases['B']['a_head_on_B']=dict(game_summaries=phases['B']['game_summaries'] if arm=='FROZEN'
                    else games(life,1,life+1.+shift-2.),
                model_p_four=.48,environment_p_four=.5,depth=2,shared_with_current=arm=='FROZEN',
                selected_value_module_id=9 if arm=='ROUTED_BELLMAN' else None)
            arms[arm]=dict(phases=phases,expert_storage_bytes=999999,value_updates=123)
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms,
            dataset=dict(snapshots=snapshots,phases={p:dict(heldout_games=heldout[p]) for p in PHASES})))
    return rows


def test_literal_net_primary_mechanism_and_three_phase_equal_game_weights():
    result=analyze(cohort(),draws=20)
    assert set(result['paired_contrasts'])=={a+'_minus_'+b for a,b in PAIRS}
    assert result['primary_contrast']==PRIMARY
    assert result['paired_contrasts'][PRIMARY]['mean']==2.
    assert result['paired_contrasts']['ROUTED_BELLMAN_minus_SMOOTH_BELLMAN']['mean']==3.
    assert result['paired_contrasts']['SMOOTH_BELLMAN_minus_FROZEN']['mean']==-1.
    assert result['net_gain_supported'] and result['physical_science_games']==8704
    assert result['logical_science_game_references']==10752
    rows=cohort()
    for row in rows:
        for i,(phase,shift) in enumerate(zip(PHASES,(2.,-2.,6.))):
            for game in row['arms']['ROUTED_BELLMAN']['phases'][phase]['game_summaries']:
                game['utility']=row['lifecycle']+i+shift
    changed=analyze(rows,draws=20)
    assert changed['paired_contrasts'][PRIMARY]['mean']==2.
    assert [changed['phase_contrasts'][p][PRIMARY]['mean'] for p in PHASES]==[2.,-2.,6.]
    assert changed['arms']['ROUTED_BELLMAN']['games']==16*3*32


def test_fixed_parent_resampling_keeps_whole_lives_and_analysis_is_readonly():
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            for game,control in zip(row['arms']['ROUTED_BELLMAN']['phases'][phase]['game_summaries'],
                                    row['arms']['FROZEN']['phases'][phase]['game_summaries']):
                game['utility']=control['utility']+row['parent']+1.
    before=deepcopy(rows); result=analyze(rows,draws=40)
    assert rows==before and result==analyze(list(reversed(rows)),draws=40)
    primary=result['paired_contrasts'][PRIMARY]
    assert primary['ci95']==[2.5,2.5]
    assert primary['parent_mean_deltas']=={str(p):p+1. for p in range(4)}
    assert result['bootstrap_seed']==29500001
    assert result['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('context',['saved_A_module','saved_A_p'])
def test_B_no_update_reference_requires_same_current_observed_module_and_belief(context):
    rows=cohort(); reference=rows[0]['arms']['ROUTED_BELLMAN']['phases']['B']['a_head_on_B']
    if context=='saved_A_module': reference['selected_value_module_id']=7
    else: reference['model_p_four']=.12
    with pytest.raises(ValueError,match='identical observed route and belief'):
        analyze(rows,draws=20)
    correct=analyze(cohort(),draws=20)
    assert correct['correction_contrasts']['ROUTED_BELLMAN']['mean']==2.
    assert correct['correction_contrasts']['FROZEN']['ci95']==[0.,0.]


def test_known_A_expert_retention_does_not_replace_actual_return_routing_or_net_gain():
    rows=cohort()
    for row in rows:
        row['dataset']['snapshots']['A_prime']['memory']['active_module_id']=10
        for arm in ARMS:
            current=row['arms'][arm]['phases']['A_prime']
            current['snapshot']['active_module_id']=10
            if arm=='ROUTED_BELLMAN':
                current['snapshot']['selected_value_module_id']=10
                for game in current['game_summaries']: game['utility']=row['lifecycle']+2.-8.
    result=analyze(rows,draws=20)
    assert result['actual_A_prime_same_observed_module']==0
    assert all(r['actual_A_prime_module']==10 and r['saved_A_module']==7
               and not r['A_prime_same_observed_module'] for r in result['by_lifecycle'])
    retained=result['retention_contrasts']['ROUTED_BELLMAN']
    assert retained['after_B']['ci95']==[0.,0.] and retained['final_vs_A']['ci95']==[0.,0.]
    assert retained['final_vs_A']['direction']=='ZERO_OBSERVED_CHANGE'
    assert result['paired_contrasts'][PRIMARY]['mean']==pytest.approx(-4./3.)
    assert not result['net_gain_supported'] and result['correction_supported']
    assert 'Saved expert storage' in result['retention_interpretation']


def test_actual_return_cannot_be_forced_to_saved_A_expert():
    rows=cohort(); row=rows[0]
    row['dataset']['snapshots']['A_prime']['memory']['active_module_id']=10
    for arm in ARMS: row['arms'][arm]['phases']['A_prime']['snapshot']['active_module_id']=10
    # The routed arm still selects saved module 7; the observed route says 10.
    with pytest.raises(ValueError,match='original observed active module and p'):
        analyze(rows,draws=20)


@pytest.mark.parametrize('endpoint',['shared_A','shared_source_B','unshared_B_counterpart'])
def test_each_physical_cutoff_is_counted_once_and_blocks_net_confirmation(endpoint):
    rows=cohort()
    if endpoint=='shared_A':
        target=rows[0]['arms']['ROUTED_BELLMAN']['phases']['A']['game_summaries']
    elif endpoint=='shared_source_B':
        target=rows[0]['arms']['FROZEN']['phases']['B']['game_summaries']
    else:
        target=rows[0]['arms']['ROUTED_BELLMAN']['phases']['B']['a_head_on_B']['game_summaries']
    target[0]['status']='CUTOFF'
    result=analyze(rows,draws=20)
    assert result['science_cutoffs']==1 and not result['complete_game_endpoints']
    assert not result['net_gain_supported'] and not result['correction_supported']
    assert result['physical_science_games']==8704 and result['logical_science_game_references']==10752


def test_new_science_families_do_not_overlap_previous_campaign_or_test_fixtures():
    current={evaluation_seed(l,p,e) for l in range(16) for p in range(3) for e in range(32)}
    previous={previous_seed(l,p,e) for l in range(16) for p in range(3) for e in range(32)}
    assert len(current)==1536 and min(current)==295900010000 and current.isdisjoint(previous)
    assert current.isdisjoint(range(29500003000,29500004000))
    rows=cohort(); rows[0]['arms']['ROUTED_BELLMAN']['phases']['B']['game_summaries'].pop()
    with pytest.raises(ValueError,match='all 32 fresh paired'):
        analyze(rows,draws=20)


def test_factual_holdout_is_whole_game_weighted_and_does_not_override_control_outcomes():
    result=analyze(cohort(),draws=20)
    assert result['arms']['FROZEN']['heldout']['mse']==15.
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            current=row['arms']['ROUTED_BELLMAN']['phases'][phase]
            for game,control in zip(current['game_summaries'],row['arms']['FROZEN']['phases'][phase]['game_summaries']):
                game['utility']=control['utility']-1.
            for game in current['heldout']['game_metrics']: game['mse']=0.
    worse=analyze(rows,draws=20)
    assert worse['arms']['ROUTED_BELLMAN']['heldout']['mse']==0.
    assert worse['paired_contrasts'][PRIMARY]['ci95']==[-1.,-1.] and not worse['net_gain_supported']
