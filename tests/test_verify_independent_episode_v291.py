from pathlib import Path
from copy import deepcopy
from statistics import mean
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_independent_episode_v291 as audit


def test_registered_seed_families_are_disjoint_for_all_64_histories():
    train={audit.training_seed(life) for life in range(64)}
    evaluate={audit.evaluation_seed(life,episode) for life in range(64) for episode in range(32)}
    warm={audit.warmup_seed(life,episode) for life in range(64) for episode in range(256)}
    assert len(train)==64 and len(evaluate)==2048 and len(warm)==16384
    assert not train&evaluate and not train&warm and not warm&evaluate
    assert max(train)<min(evaluate)


def test_old_proposed_evaluation_base_reproduces_real_training_collision():
    train={audit.training_seed(life) for life in range(64)}
    old={291500000000+life*1000000+episode for life in range(64) for episode in range(32)}
    assert train&old=={audit.training_seed(life) for life in range(30,37)}
    assert audit.evaluation_seed(0,0)==291900000000


def test_signed_64_life_endpoints_keep_parent_scope_and_negative_histories():
    values=[-1.,1.]*32
    result=dict(mean=0.,ci95=[0.,0.],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        improved_equal_worse=[32,0,32],adverse_lifecycles=list(range(0,64,2)))
    audit.check_contrast(result,values,'higher_is_better')
    result['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='adverse'):audit.check_contrast(result,values,'higher_is_better')


def warmup_row():
    steps=14
    return dict(kind='WARMUP',lifecycle=0,parent=0,
        summary=dict(seed=audit.warmup_seed(0,0),steps=steps,score=0,status='LOST',utility=-4.),
        actions=['LEFT']*steps,scores=[0]*steps,
        raw_spawns=[dict(kind='INITIAL' if i<2 else 'POST_ACTION',rank=1,cell=i%16) for i in range(steps+2)],
        final_board=[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1],
        counts=dict(environment=dict(initial_spawns=2,sampled_transitions=steps,
            environment_random_draws=2*(steps+2),ground_explicit_swipe_calls=steps,
            ground_state_status_calls=steps+1,ground_status_internal_swipe_calls=4*(steps+1),
            ground_swipe_calls=5*steps+4),
            direct=dict(choose_calls=steps,inner_choose_calls=steps,inner_learned_swipe_calls=4*steps,
                inner_line_table_lookups=16*steps,inner_value_predictions=3*steps,inner_table_lookups=96*steps)))


def test_complete_warmup_counts_initial_tiles_and_keeps_paid_threshold_overshoot():
    memory=audit.Memory();memory.consume([1]*243)
    row=warmup_row();events=audit.check_warmup(row,0,memory)
    assert memory.obs==259 and memory.n==3 and len(events)==1
    with pytest.raises(ValueError,match='beyond'):audit.check_warmup(row,1,memory)


def test_warmup_cannot_drop_initial_spawn_random_draw_cost():
    row=warmup_row();row['counts']['environment']['environment_random_draws']-=4
    with pytest.raises(ValueError,match='physical environment'):audit.check_warmup(row,0,audit.Memory())


def split_fixture():
    games=[dict(episode=i,steps=6500,score=26000,status='LOST',stream_seed=audit.training_seed(0),
        start_raw=6502*i,end_raw=6502*(i+1)) for i in range(20)]
    scores={i:[4]*6500 for i in range(20)}
    memories={i:dict(observations_seen=300+g['end_raw'],active_module_id=0,
        modules=[dict(id=0,alpha=1,beta=301+g['end_raw'],visits=1)],pending=dict(n=0,fours=0))
        for i,g in enumerate(games)}
    training=dict(after_stream=dict(post_action_spawns=131030),counts=dict(environment={},planning={},learning={}))
    ds=dict(games=[dict(g,split='FIT' if i<16 else 'HELDOUT') for i,g in enumerate(games)],
        fit_game_count=16,fit_step_end=104000,fit_end_raw=104032,fit_memory=deepcopy(memories[15]),
        costs=dict(full_A_raw_tiles=131072,fit_raw_tiles=104032,heldout_raw_tiles=26008,
            fit_steps=104000,heldout_steps=26000,excluded_tail_games=1,excluded_tail_raw_tiles=1032,
            excluded_tail_steps=1030,warmup_raw_tiles=300,full_A_acquisition_counts=training['counts']))
    return ds,games,scores,memories,training


def test_tail_is_paid_and_fit_belief_stops_before_heldout():
    ds,games,scores,memories,training=split_fixture()
    assert audit.check_split(ds,games,scores,memories,300,training)==16
    ds['costs']['excluded_tail_raw_tiles']=0
    with pytest.raises(ValueError,match='paid full'):audit.check_split(ds,games,scores,memories,300,training)
    ds['costs']['excluded_tail_raw_tiles']=1032;ds['fit_memory']=deepcopy(memories[19])
    with pytest.raises(ValueError,match='heldout/future'):audit.check_split(ds,games,scores,memories,300,training)


def test_complete_split_cannot_select_games_by_later_reward():
    ds,games,scores,memories,training=split_fixture()
    ds['games'][0]['split']='HELDOUT';ds['games'][19]['split']='FIT'
    with pytest.raises(ValueError,match='membership'):audit.check_split(ds,games,scores,memories,300,training)


def result_fixture(utility_delta=0.,cutoffs=0):
    records=[]
    for life in range(64):
        arms={}
        for index,arm in enumerate(audit.ARMS):
            arms[arm]=dict(games=32,mean_game_utility=utility_delta*index/2,wins=0,losses=32,
                cutoffs=0,cutoff_episodes=[],steps=320,
                heldout=dict(games=2,samples=20,bias=0.,mse=3.-index,mae=1.))
        records.append(dict(lifecycle=life,parent=life%4,arms=arms))
    def contrast(values,direction):
        value=mean(values)
        result=dict(mean=value,ci95=[value,value],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
            parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},
            interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')
        if direction:
            losses=values if direction=='lower_is_better' else [-v for v in values]
            result.update(improved_equal_worse=[sum(v<0 for v in losses),sum(v==0 for v in losses),sum(v>0 for v in losses)],
                adverse_lifecycles=[i for i,v in enumerate(losses) if v>0])
        if direction!='higher_is_better':result['positive_equal_negative']=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)]
        return result
    summary=dict(by_lifecycle=deepcopy(records),primary_contrast='EPISODE_MEAN_MC_minus_FROZEN',
        primary_prediction_contrast='EPISODE_MEAN_MC_minus_FROZEN',primary_prediction_metric='mse',
        bootstrap_draws=20000,bootstrap_seed=29100001,estimator='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES',complete_game_endpoints=cutoffs==0,
        independent_prediction_supported=True,independent_learning_confirmed=utility_delta>0 and cutoffs==0,
        independent_learning_status=('SUPPORTED_' if utility_delta>0 and cutoffs==0 else 'NOT_SUPPORTED_')+'CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        arms={},paired_contrasts={},heldout_contrasts={})
    for arm in audit.ARMS:
        rows=[r['arms'][arm] for r in records];heldout=[r['heldout'] for r in rows]
        summary['arms'][arm]=dict(mean_game_utility=mean(r['mean_game_utility'] for r in rows),
            **{key:sum(r[key] for r in rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(r['games'] for r in heldout),samples=sum(r['samples'] for r in heldout),
                **{key:mean(r[key] for r in heldout) for key in ('bias','mse','mae')}))
    for left,right in audit.PAIRS:
        name=left+'_minus_'+right
        summary['paired_contrasts'][name]=contrast([r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],'higher_is_better')
        summary['heldout_contrasts'][name]={key:contrast([r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records],
            None if key=='bias' else 'lower_is_better') for key in ('mse','mae','bias')}
    return summary,records


def test_improved_prediction_does_not_replace_zero_complete_game_gain():
    summary,records=result_fixture()
    audit.check_result_summary(summary,records,0)
    summary['independent_learning_confirmed']=True
    with pytest.raises(ValueError,match='prediction substituted'):audit.check_result_summary(summary,records,0)


def test_cutoff_prevents_primary_confirmation_even_with_positive_interval():
    summary,records=result_fixture(utility_delta=1.,cutoffs=1)
    audit.check_result_summary(summary,records,1)
    summary['independent_learning_confirmed']=True
    with pytest.raises(ValueError,match='prediction substituted'):audit.check_result_summary(summary,records,1)
