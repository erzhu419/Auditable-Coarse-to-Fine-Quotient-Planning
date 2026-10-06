"""Independent geometry, weighted block estimates and split first/tail RNG replay."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_spawn_stratification_v176 as core
from scripts import analyze_controlled_predictive_spawn_stratification_v176 as audit
from scripts import run_controlled_predictive_spawn_stratification_v176 as runner
from test_spawn_stratification_runner_v176 import toy_roots
from test_spawn_stratification_core_v176 import batches

ROWS = []


def test_geometry_only_median_and_exact_native_joint_support_allocation(monkeypatch):
    for tree, one in (([13,1],[15,7,0]),([0,15],[1,2,3,4,5,6,7])):
        actual, expected = core.joint_support(tree,one), audit.joint_support(tree,one)
        assert audit._equal(actual,expected) and core.allocation(actual)==audit.allocation(expected)
        assert sum(audit.allocation(expected).values())==4*len(expected)
    roots, choices = [], []
    for cohort in audit.COHORTS:
        for life in audit.LIVES:
            for index in range(3):
                root_id = f'{cohort}:{life}:{index}'
                roots.append(dict(root_id=root_id,cohort=cohort,life=life,source_id=f'{cohort}:{life}',ordinal=index,
                    board=[index]+[1]*15,canonical_board=[index]+[1]*15,
                    actions=[dict(canonical_action=action,actual_action=action) for action in ('DOWN','LEFT')]))
                choices.append(dict(root_id=root_id,changed=True,old_difference_components=[1.e6*index,0.,0.],
                    decisions={'TREE':dict(canonical_action='DOWN'),'ONE':dict(canonical_action='LEFT')}))
    calls = []
    def swipe(board, action):
        calls.append((board,action.value)); index=board[0]
        size = ((1,1),(2,3),(2,2))[index][action.value=='LEFT']
        return tuple([0]*size+[1]*(16-size)),0,True
    monkeypatch.setattr(audit.prior.ground,'swipe_board_v1',swipe)
    selected,candidates = audit.select_geometry(roots,dict(choices=choices))
    assert len(calls)==48 and len(candidates)==24 and len(selected)==8
    assert all(row['root_id'].endswith(':2') for row in selected)
    assert [row['probe_ordinal'] for row in selected]==list(range(8))
    assert all(len(row['support'])==4 and row['draws_per_block']==16 for row in selected)
    poisoned = deepcopy(choices)
    for row in poisoned:
        row['old_difference_components']=[-1.e20,1.e20,-1.e20]
    assert audit.select_geometry(roots,dict(choices=poisoned))==(selected,candidates)


def test_weighted_strata_keep_matched_branch_costs_and_independent_block_statistics():
    roots=toy_roots(); plans=audit.branch_roster(roots)
    assert plans==runner.branch_roster(roots)
    outcomes=[]
    for plan in plans:
        reward = 10. if plan['mode']=='TREE' and (plan['stratum']==1 if plan['method']=='STRAT' else plan['suffix']>=6) else 0.
        steps=1 if plan['method']=='STRAT' else 2
        outcomes.append(dict(plan,components=[reward,1.,0.],score=2048*reward,status='LOST',utility=reward-1,steps=steps,
            module=dict(mode='FORCED_H2',life=plan['life'],forced_decisions=1,h2_calls=steps-1)))
    expected=audit.construct_batches(roots,plans,outcomes)
    assert audit._equal(runner.construct_batches(roots,plans,outcomes),expected)
    assert all(row['components'][0]==pytest.approx(1. if row['method']=='STRAT' else 2.5) for row in expected)
    assert all(row['physical_branches']==16 and row['environment_samples']==(16 if row['method']=='STRAT' else 32) for row in expected)
    assert audit._equal(core.analyze_batches(expected),audit.analyze_batches(expected))
    for kind in ('reduction','equal','full_vector'):
        rows=batches(kind); independent=audit.analyze_batches(rows)
        assert audit._equal(core.analyze_batches(rows),independent)
        assert independent['work']['batch_cost_reads']==256
        assert independent['work']['variance_difference_leave_one_block_out_estimates']==416
        if kind=='full_vector':
            stats=independent['methods']['STRAT']['metrics']
            assert stats['utility']['block_estimate_variance']==0.
            assert sum(stats[metric]['block_estimate_variance'] for metric in ('reward','failure','success'))>0
    partial=batches()[:-1]
    assert audit._equal(core.analyze_batches(partial),audit.analyze_batches(partial))
    assert not audit.analyze_batches(partial)['complete']


@pytest.mark.parametrize('method',['IID','STRAT'])
def test_independent_replay_conditions_only_first_spawn_and_preserves_fresh_tail_rng(monkeypatch,method):
    root=toy_roots()[0]; root['board']=[1,2]+[0]*14
    plan=next(row for row in runner.branch_roster([root]) if row['method']==method and row['mode']=='TREE' and row['block']==0 and row['suffix']==6)
    after=tuple([0]*16)
    monkeypatch.setattr(runner.ground,'swipe_board_v1',lambda *args:(after,0,True))
    class FakeRng:
        def __init__(self,seed):
            self.values=iter([.2,.95] if seed==plan['spawn_seed'] else [.8,.1])
        def random(self):
            return next(self.values)
    monkeypatch.setattr(runner.random,'Random',FakeRng)
    status_calls=[]
    def status(board,environment):
        status_calls.append(tuple(board)); environment['ground_state_status_calls']+=1
        return 'WON' if len(status_calls)==3 else 'ACTIVE'
    monkeypatch.setattr(runner.physical,'_status',status)
    bank={query:SimpleNamespace(counts=Counter()) for query in ('risk1','risk8')}
    bank['risk1'].choose=lambda *args:dict(action='DOWN',afterstate=list(after),score=0)
    row=runner.run_conditional_branch(bank,root,plan)
    exits={action:(after,0) for action in ('RIGHT','DOWN')}; replay_calls=[]
    def legal_exits(board):
        replay_calls.append(tuple(board))
        return ('WON' if len(replay_calls)==3 else 'ACTIVE'),exits,0
    monkeypatch.setattr(audit.prior.prior.previous,'legal_exits',legal_exits)
    monkeypatch.setattr(audit.prior.prior.planning,'planning_counts_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.local,'compact_choice_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.h1,'root_choice_checks',lambda *args:{})
    checks,_=audit.replay_branch(row,root)
    assert all(checks.values())
    assert row['spawned_cells'][1]==12 and row['spawned_ranks'][1]==1
    assert row['result']['environment_counts']['environment_random_draws']==(4 if method=='IID' else 2)
    assert row['result']['environment_counts'].get('conditioned_first_spawn_assignments',0)==(method=='STRAT')
    broken=deepcopy(row); broken['spawned_cells'][1]=3; replay_calls.clear()
    assert not audit.replay_branch(broken,root)[0]['rng']
    assert ROWS==[]
