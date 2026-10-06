from copy import deepcopy
import importlib.util
from pathlib import Path
from statistics import mean

import pytest

path = Path(__file__).resolve().parents[1]/'scripts/verify_natural_online_value_v286.py'
spec = importlib.util.spec_from_file_location('verify_v286',path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
LOST = [1,2,3,4,2,3,4,5,3,4,5,6,4,5,6,7]


def planning(n,depth=2):
    return dict(choose_calls=n,root_swipe_calls=4*n,
        learned_swipe_calls=4*n,line_table_lookups=16*n,leaf_choose_calls=0)


def memory():
    m = audit.Memory()
    m.consume([1]*256)
    return m


def crossing():
    m = memory()
    m.modules.append(dict(id=1,alpha=1,beta=1,visits=0));m.active=1;m.n=62
    start = dict(board=[0]*16,pending_afterstate=[0]*16,pending_bank_id=0,episode=0,step=3,
        return_score=100,status='ACTIVE',initial_count=2,raw_tiles=5,post_action_spawns=3,
        game_start_raw=0,stream_seed=286200000000,random_draw_position=10)
    end = dict(start,board=LOST,pending_afterstate=None,pending_bank_id=None,step=5,return_score=112,
        raw_tiles=7,post_action_spawns=5,random_draw_position=14,status='LOST')
    row = dict(arm='PERSISTENT_TD',active_bank_id=1,module_id_before=1,model_p_four=.5,start=start,end=end,
        raw_spawns=[dict(episode=0,kind='POST_ACTION',cell=0,rank=1)]*2,
        actions=['DOWN','UP'],scores=[4,8],
        completed_games=[dict(episode=0,stream_seed=286200000000,start_raw=0,end_raw=7,steps=5,score=112,status='LOST')],
        counts=dict(environment=dict(sampled_transitions=2,post_action_spawns=2,raw_tile_productions=2,
            environment_random_draws=4,ground_explicit_swipe_calls=2,ground_state_status_calls=2,
            ground_status_internal_swipe_calls=8,ground_swipe_calls=10,episodes_completed=1,lost_games=1),
            planning=planning(2),learning=dict(td_updates=3,table_update_occurrences=96,value_predictions=5,table_lookups=160,table_updates=90)),
        bank_update_counts={'0':1,'1':2},td_examples=[
            dict(raw_tiles_before_update=5,episode=0,step=3,bank_id=0,kind='PREVIOUS_PENDING',target=3.,raw_target=3.,error=.1),
            dict(raw_tiles_before_update=7,episode=0,step=4,bank_id=1,kind='TERMINAL_LOSS',target=-4.,raw_target=-4.,error=-1.)])
    return row,m


def test_saved_old_bank_credit_and_terminal_loss_are_independent_of_new_bank():
    row,m = crossing()
    assert audit.check_chunk(row,2,m) == {'0':1,'1':2}


@pytest.mark.parametrize('corruption,message',[
    ('bank','TD credited'),('draws','environment ledger'),('choice','action selection'),('example','causal identity'),
])
def test_compact_corruption_is_caught(corruption,message):
    row,m = crossing()
    if corruption == 'bank': row['bank_update_counts']={'1':3}
    if corruption == 'draws': row['counts']['environment']['environment_random_draws']=2
    if corruption == 'choice': row['counts']['planning']['choose_calls']=3
    if corruption == 'example': row['td_examples'][0]['bank_id']=1
    with pytest.raises(ValueError,match=message): audit.check_chunk(row,2,m)


def test_one_initial_tile_budget_pauses_without_action_or_terminal_update():
    m=memory()
    start=dict(board=[0]*16,pending_afterstate=None,pending_bank_id=None,episode=-1,step=0,
        return_score=0,status='NOT_STARTED',initial_count=0,raw_tiles=0,post_action_spawns=0,
        game_start_raw=0,stream_seed=286200000000,random_draw_position=0)
    end=dict(start,board=[1]+[0]*15,episode=0,status='INITIALIZING',initial_count=1,raw_tiles=1,random_draw_position=2)
    row=dict(arm='FROZEN',active_bank_id=0,module_id_before=0,model_p_four=m.probability(),start=start,end=end,
        raw_spawns=[dict(episode=0,kind='INITIAL',cell=0,rank=1)],actions=[],scores=[],completed_games=[],
        counts=dict(environment=dict(initial_spawns=1,raw_tile_productions=1,environment_random_draws=2,episodes_started=1),
            planning={},learning={}),bank_update_counts={},td_examples=[])
    assert not audit.check_chunk(row,1,m)
    row['counts']['environment']['raw_tile_productions']=0
    with pytest.raises(ValueError,match='environment ledger'): audit.check_chunk(row,1,m)


def test_all_raw_memory_commits_at_exact_64_and_retains_old_module():
    m=memory()
    old=deepcopy(m.modules[0])
    assert not m.consume([2]*63)
    assert m.active == 0 and m.n == 63
    event=m.consume([2])[0]
    assert event['kind'] == 'created' and event['block_fours'] == 64
    assert m.active == 1 and m.modules[0] == old and m.obs == 320
    assert m.learned()['pending'] == {'n':0,'fours':0}


def evaluation():
    games=[dict(seed=286500000000+i,score=4096,steps=2,status='LOST',final_board=LOST,utility=-2.) for i in range(16)]
    env=dict(sampled_transitions=32,post_action_spawns=32,initial_spawns=32,raw_tile_productions=64,
        environment_random_draws=128,ground_explicit_swipe_calls=32,ground_state_status_calls=48,
        ground_status_internal_swipe_calls=192,ground_swipe_calls=224)
    return games,dict(environment=env,planning=planning(32))


def test_evaluation_fresh_seeds_full_utility_and_initial_costs():
    games,costs=evaluation()
    assert audit.check_games(games,0,0,costs)['mean_game_utility'] == -2.
    games[0]['seed']=286200000000
    with pytest.raises(ValueError,match='fresh paired'): audit.check_games(games,0,0,costs)
    games[0]['seed']=286500000000;games[0]['utility']=2.
    with pytest.raises(ValueError,match='complete utility'): audit.check_games(games,0,0,costs)


def test_direct_actual_counter_layout_uses_roots_without_h2_leaf_expansion():
    # These are the actual life0 DIRECT receipt counters, not an H2 fixture.
    counts=dict(choose_calls=10642,root_swipe_calls=42568,learned_swipe_calls=42568,
        line_table_lookups=170272,root_legal_actions=38149,legal_swipes=38149,
        learned_terminal_checks=48791,value_predictions=38149,table_lookups=1220768)
    audit.planning_counts(counts,10642,depth=1)
    counts['leaf_choose_calls']=10642
    with pytest.raises(ValueError,match='DIRECT work'): audit.planning_counts(counts,10642,depth=1)


def test_signed_life_and_parent_inputs_preserve_all_adverse_cases():
    values=[-1.,1.]*8
    saved=dict(mean=mean(values),lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        improved_equal_worse=[8,0,8],adverse_lifecycles=list(range(0,16,2)),
        parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',ci95=[0.,0.])
    audit.check_contrast(saved,values)
    saved['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='adverse lives'): audit.check_contrast(saved,values)
