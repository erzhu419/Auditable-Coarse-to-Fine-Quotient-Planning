"""Runner controls must preserve source policies and keep evaluation read-only."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

from scripts import run_controlled_predictive_policy_consequences_v126 as runner


def toy_game(seed=1):
    board=[1,1]+[0]*14;after=[2]+[0]*15;following=[2,1]+[0]*14
    return dict(seed=seed,initial_board=board,initial_spawns=[dict(cell=0,rank=1),dict(cell=1,rank=1)],
        final_board=following,status='LOST',return_score=4,steps_count=1,seconds=.01,
        work=dict(sampled_transitions=1,initial_spawns=2),
        steps=[dict(board=board,afterstate=after,next_board=following,action='LEFT',
                    score=4,status='LOST',spawned_cell=1,spawned_rank=1)])


def test_source_capsule_excludes_router_observations_and_newer_models():
    previous=dict(snapshots=[dict(life=0,rule={'goal_rank':11},models={'reward':{'path':'v120.npz'}},
                                  initial_ranks=[1,2],initial_rank_sources={'path':'v122.gz'})],
                  inherited_costs={'v120_training':[1]})
    extracted=runner.extract_source(previous)
    assert set(extracted['snapshots'][0])=={'life','rule','models'}
    extracted['snapshots'][0]['models']['reward']['path']='changed'
    assert previous['snapshots'][0]['models']['reward']['path']=='v120.npz'


def test_source_actor_keeps_original_query_and_separate_seed(monkeypatch):
    actor=SimpleNamespace(counts=Counter(),updates=7);seen=[]
    def choose(board,query):
        seen.append(deepcopy(query));actor.counts['choose_calls']+=1
        return {'action':'LEFT'}
    actor.choose=choose
    def episode(seed,action,p_four,max_steps):
        game=toy_game(seed);assert action(game['initial_board'],0)=='LEFT'
        assert p_four==.1 and max_steps==2000
        return game
    monkeypatch.setattr(runner,'run_episode',episode)
    row,_=runner.source_game(actor,2,'risk_goal',replica=3)
    assert seen==[runner.POLICIES['risk_goal']]
    assert row['seed']==runner.evaluation_seed(2,3)
    assert row['result']['source_updates_before']==row['result']['source_updates_after']==7
    assert row['result']['learning_counts']=={}
    assert row['result']['utility']==4/2048-4


def test_fit_receives_whole_ended_episode_and_retains_censored_acquisition():
    model=SimpleNamespace(counts=Counter(),updates=0);received=[]
    def fit(afterstates,scores,status):
        received.append((afterstates,scores,status));model.counts['censored_afterstates']+=1
        return dict(status=status,observed_afterstates=1,updates=0,analytic_goals=0,
                    censored_afterstates=1,target_sums=[0.,0.,0.])
    model.train_episode=fit
    game=toy_game();game['status']='CUTOFF'
    row=dict(life=0,policy='reward',episode_index=0,result=runner.result(game,'reward'))
    raw=runner.fit_game(model,row,game)
    assert received==[([game['steps'][0]['afterstate']],[4],'CUTOFF')]
    assert raw['result']['environment_counts']['sampled_transitions']==1
    assert raw['result']['updates_after']==0 and raw['fit']['censored_afterstates']==1
    block=runner.empty_block(0);runner.add_training(block,row)
    assert block['environment_counts']['sampled_transitions']==1 and block['updates']==0


def test_single_policy_readout_uses_its_own_vector_and_records_no_updates(monkeypatch):
    from acfqp.science import controlled_predictive_policy_consequences_v126 as core
    models=[SimpleNamespace(counts=Counter(),updates=3),SimpleNamespace(counts=Counter(),updates=5)]
    def choose(active,board,query):
        assert active==[models[1]] and query==runner.QUERIES['risk8']
        active[0].counts['choose_calls']+=1
        return dict(action='LEFT',policy_index=0,consequences=[2.,.25,.75],value=2.+4/2048+4.)
    monkeypatch.setattr(core,'choose_gpi',choose)
    def episode(seed,action,*args):
        game=toy_game(seed);action(game['initial_board'],0);return game
    monkeypatch.setattr(runner,'run_episode',episode)
    row=runner.learned_game(models,0,'risk8','POLICY_risk_goal',256,0)
    assert row['policy_indices']==[1] and row['chosen_vectors']==[[2.,.25,.75]]
    assert row['result']['updates_before']==row['result']['updates_after']==[3,5]
    assert row['result']['learning_counts']=={'choose_calls':1}


def test_training_and_outer_seed_rosters_are_disjoint_and_training_unique():
    training=[runner.train_seed(life,policy,episode) for life in runner.LIVES
              for policy in runner.POLICIES for episode in range(runner.TRAIN_EPISODES)]
    outer={runner.evaluation_seed(life,replica) for life in runner.LIVES for replica in range(runner.REPLICAS)}
    assert len(set(training))==8192 and len(outer)==32 and not set(training)&outer
