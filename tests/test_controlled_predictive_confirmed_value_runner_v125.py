"""Synthetic-engine timing fixtures; no environment sampling or native training."""
from collections import Counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_confirmed_value_v125 as runner
from acfqp.science.controlled_predictive_confirmed_value_v125 import ConfirmedValueBank

AFTER=(1,)+(0,)*15
WARMUP=[2]*26+[1]*230


class Value:
    def __init__(self, n=65, status='LOST'):
        self.rule=SimpleNamespace(goal_rank=11)
        self.counts,self.setup_counts=Counter(),Counter()
        self.setup_seconds=0.
        self.updates=0
        self.weights=np.zeros(4)
        self.n,self.status=n,status
        self.timeline=[]

    def choose(self,board,query):
        self.counts['choose_calls']+=1
        i=self.counts['choose_calls']
        self.timeline.append(('choose',i))
        after=((11,)+(0,)*15) if self.status=='WON' and i==self.n else AFTER
        return dict(action='UP',afterstate=after,value=float(i),bank_id=0)

    def update(self,afterstate,target,alpha):
        self.timeline.append(('update',target))
        self.updates+=1
        self.counts['td_updates']+=1
        self.counts['table_update_occurrences']+=32


def engine(n,status):
    def run(seed,act,p_four,max_steps):
        steps=[]
        for i in range(n):
            board=(1,1)+(0,)*14
            action=act(board,i)
            steps.append(dict(action=action,spawned_cell=1,spawned_rank=1,score=0))
        final=((11,1)+(0,)*14) if status=='WON' else (1,1)+(0,)*14
        return dict(initial_board=(1,1)+(0,)*14,initial_spawns=[(0,1),(1,1)],
            final_board=final,steps=steps,steps_count=n,return_score=0,status=status,seconds=0.,
            work=dict(sampled_transitions=n,initial_spawns=2,environment_random_draws=2*n+4,
                ground_explicit_swipe_calls=n))
    return run


@pytest.mark.parametrize('status',['LOST','WON','CUTOFF'])
def test_delayed_game_chooses_before_commit_and_keeps_terminal_queue(monkeypatch,status):
    monkeypatch.setattr(runner,'run_episode',engine(65,status))
    source=Value(status=status)
    model=ConfirmedValueBank(source,WARMUP,runner.ROOT/'reports/v125_runner_test_build',method='DELAY')
    row,raw=runner.td_game(model,0,'risk_goal','B','DELAY',episode=0,max_steps=65)
    assert len(raw['td_targets'])==len(raw['target_context_ids'])==65
    assert raw['td_targets'][:64]==list(map(float,range(2,66)))
    assert raw['td_targets'][-1]==(-4. if status=='LOST' else None)
    assert len(raw['commit_events'])==1 and raw['commit_events'][0]['applied']==64
    assert model.updates==64 and len(model.pending_transitions)==1
    assert row['result']['pending_after']==1 and row['result']['pending_before']==0
    assert source.timeline[64]==('choose',65)
    assert source.timeline[65]==('update',2.)
    assert raw['context_ids']==[0]*65
    assert model.router.observations_seen==321


@pytest.mark.parametrize('status',['LOST','WON','CUTOFF'])
def test_immediate_control_retains_original_next_choice_timing(monkeypatch,status):
    monkeypatch.setattr(runner,'run_episode',engine(65,status))
    model=Value(status=status)
    row,raw=runner.td_game(model,0,'risk_goal','B','CONT',episode=0,max_steps=65)
    assert model.timeline[:3]==[('choose',1),('choose',2),('update',2.)]
    assert model.updates==65-(status!='LOST')
    assert not raw['routing_events'] and not raw['td_targets']


def test_evaluation_discards_td_queue_without_mutating_training_state(monkeypatch):
    monkeypatch.setattr(runner,'run_episode',engine(2,'LOST'))
    model=ConfirmedValueBank(Value(n=2),WARMUP,runner.ROOT/'reports/v125_runner_test_build',method='DELAY')
    model.observe(1);model.finish_transition(AFTER,0,1.,0)
    actor=model.evaluation_copy()
    before=model.to_payload()
    row,raw=runner.td_game(actor,0,'reward','B','DELAY',checkpoint=0,replica=0,max_steps=2)
    assert model.to_payload()==before
    assert actor.updates==model.updates==0 and not actor.pending_transitions
    assert len(raw['context_ids'])==2 and not raw['td_targets'] and not raw['commit_events']
    assert row['result']['router_observations_after']-row['result']['router_observations_before']==2
    assert row['result']['learning_counts']['evaluation_weight_views']==1


def test_fresh_seeds_pair_methods_but_separate_training_and_outer_cohorts():
    assert runner.train_seed(0,'reward','B',0)==12501000000
    assert runner.train_seed(3,'risk_goal','A_RETURN',1)==12536000001
    assert runner.evaluation_seed(3,'A_RETURN',7)==12590310007
    assert len({runner.train_seed(life,query,phase,episode)
        for life in range(4) for query in runner.QUERIES for phase in runner.PHASES
        for episode in (0,1,9999)})==48
