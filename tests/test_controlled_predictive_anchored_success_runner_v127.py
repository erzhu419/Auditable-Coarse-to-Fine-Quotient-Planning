"""Replay must not acquire data, and new-query evaluation must stay frozen."""
from collections import Counter
from types import SimpleNamespace

from scripts import run_controlled_predictive_anchored_success_v127 as runner
from tests.test_controlled_predictive_policy_consequences_runner_v126 import toy_game


def test_replay_uses_retained_episode_only_and_counts_no_acquisition(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('replay acquired new environment data')
    monkeypatch.setattr(runner,'run_episode',forbidden)
    source=dict(life=0,policy='reward',episode_index=0,seed=12601000000,
                result=dict(steps=2,status='WON',score=8))
    model=SimpleNamespace(counts=Counter(),updates=10,successes=2)
    def replay(row):
        assert row is source;model.counts['replay_swipe_calls']+=2
        return [[1]*16,[11]+[0]*15]
    def fit(boards,status):
        assert status=='WON' and len(boards)==2
        model.updates+=1;model.successes+=1
        return dict(updates=1,success_afterstates=1,unique_feature_updates=4,
                    analytic_goals=1,censored_afterstates=0)
    model.replay=replay;model.train_episode=fit
    row=runner.replay_game(model,source)
    assert row['result']['environment_counts']=={}
    assert row['result']['retained_transitions']==2
    assert row['result']['updates_after']==11 and row['result']['successes_after']==3
    assert 'actions' not in row
    block=runner.empty_block(0);runner.add_training(block,row)
    assert block['updates']==1 and block['retained_transitions']==2


def test_frozen_source_keeps_own_query_on_fresh_seed(monkeypatch):
    actor=SimpleNamespace(counts=Counter(),updates=17)
    def choose(board,q):
        assert q==runner.POLICIES['risk_goal'];actor.counts['choose_calls']+=1
        return {'action':'LEFT'}
    actor.choose=choose
    def episode(seed,act,*args):
        game=toy_game(seed);assert act(game['initial_board'],0)=='LEFT';return game
    monkeypatch.setattr(runner,'run_episode',episode)
    row,_=runner.source_game(actor,2,'risk_goal',3)
    assert row['seed']==127*100000000+90000000+200000+3
    assert row['result']['source_updates_before']==row['result']['source_updates_after']==17


def test_constant_readout_routes_correct_policy_and_does_not_fit(monkeypatch):
    from acfqp.science import controlled_predictive_anchored_success_v127 as core
    models=[SimpleNamespace(counts=Counter(),updates=10,successes=2),
            SimpleNamespace(counts=Counter(),updates=20,successes=3)]
    def choose(active,board,q,mode):
        assert active==[models[1]] and mode=='CONSTANT' and q==runner.QUERIES['risk8']
        active[0].counts['choose_calls']+=1
        return dict(action='LEFT',policy_index=0,success_probability=.15,anchor_value=2.,value=-.8)
    monkeypatch.setattr(core,'choose_gpi',choose)
    def episode(seed,act,*args):
        game=toy_game(seed);act(game['initial_board'],0);return game
    monkeypatch.setattr(runner,'run_episode',episode)
    row=runner.learned_game(models,0,'risk8','CONSTANT_risk_goal',256,0)
    assert row['policy_indices']==[1]
    assert row['chosen_success_probabilities']==[.15]
    assert row['result']['updates_before']==row['result']['updates_after']==[10,20]
    assert row['result']['successes_before']==row['result']['successes_after']==[2,3]


def test_diagnostics_use_training_prefix_constant_and_no_outer_labels():
    model=SimpleNamespace(counts=Counter())
    def predict(boards):model.counts['success_predictions']+=len(boards);return [.2]*len(boards)
    model.probabilities=predict
    row=dict(life=0,policy='reward',replica=1,eval_id='0/FROZEN_reward/1')
    cp=dict(age=256,updates=10,successes=2,constant=.2)
    observed=runner.diagnostic(model,row,toy_game(),cp)
    assert observed['constant']==.2 and observed['prefix_successes']==2
    assert observed['probabilities']==[.2]


def test_source_capsule_reuses_training_but_excludes_previous_outer_and_models():
    old=dict(snapshots=[dict(life=0,rule={},models={'reward':{'path':'V120'}})],
             inherited_costs={'v120_training':'retained'})
    analysis=dict(complete=True,costs={'training':{'games':8192},'outer':{'games':832}},
                  control={'excluded':True})
    source=runner.extract_source(old,analysis)
    assert source['inherited_costs']['v126_training']=={'games':8192}
    assert 'control' not in source and 'outer' not in source['inherited_costs']
    assert source['snapshots'][0]['training_trace'].endswith('life_0/training.jsonl.gz')
    assert source['snapshots'][0]['models']['reward']['path']=='V120'
