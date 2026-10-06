"""Shared feasibility readiness, fresh physical streams and complete scoring."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_goal_feasibility_v258 as runner

S,D,R = runner.core.OPERATORS
CASE = dict(id='test_case',context='A',stage='A',operating='low',retry_cost='17/20')


def stub_plan(case,lower=F(0),impossible=False,query=True):
    return dict(case=deepcopy(case),utility_lower=lower,goal_impossible=impossible,query_ready=query,
        goal_upper=F(19,10) if impossible else F(4),box_goal_upper=F(4),risk_upper=F(0),mix=[('WAIT',F(1))],
        queries={q:dict(policy='WAIT') for q in ('reward','goal','risk')},
        query_evidence=dict(queries={q:dict(policy='WAIT',certified=query) for q in ('reward','goal','risk')},all_ready=query,threshold=4320))


def preview_job():
    job = runner.Lifecycle.__new__(runner.Lifecycle)
    job.life,job.arm,job.check_id,job.auxiliary_records = 0,runner.ARMS[0],0,0
    job.state,job.cache,job.work,job.cursors = {},{},Counter(),dict(A=0,B=0)
    job.budget = lambda:dict(available=1000)
    job.timed = lambda scope,function,*args:function(*args)
    job.retain = lambda plan,identity:deepcopy(plan)
    job.saved = []
    job.write = lambda kind,row:job.saved.append((kind,deepcopy(row)))
    return job


def test_preview_uses_full_empty_member_upcoming_plan_and_all_four_feasibility_queries(monkeypatch):
    job,calls = preview_job(),[]
    def make_plan(member,case,state,identity,index,cache,work):
        assert all(not sum(row.values()) for row in member.values())
        calls.append(dict(identity=identity,index=index,case=deepcopy(case)))
        member[S]['DELIVERY'] = 7  # every subsequent preview must get its own empty member
        return stub_plan(case,lower=2 if identity==2 else 0,impossible=identity==1,query=identity!=2)
    monkeypatch.setattr(runner.core,'make_plan',make_plan)
    monkeypatch.setattr(runner.core,'query_plan',lambda *args:pytest.fail('query-only preview would stop before execution feasibility'))
    meta = job.preview_check('A_RETURN','A',54)
    assert len(calls)==12 and all(row['index']==54 for row in calls)
    assert Counter(row['identity'] for row in calls)=={0:4,1:4,2:4}
    assert meta['ready_by_type']==[False,True,False]  # query-only, impossible+query, execution-only
    assert not meta['all_ready'] and job.auxiliary_records==12
    previews = [row for kind,row in job.saved if kind=='previews']
    assert all('utility_lower' in row['plan'] and 'box_goal_upper' in row['plan'] for row in previews)
    assert {(row['plan']['case']['operating'],row['plan']['case']['retry_cost']) for row in previews}==set(runner.PUBLIC_COSTS)


def test_shared_phase_keeps_execution_unready_type_eligible_until_full_recheck():
    job = preview_job()
    job.fees = dict(shared=0)
    checks = iter([dict(check_id=0,all_ready=False,ready_by_type=[True,False,True]),
        dict(check_id=1,all_ready=False,ready_by_type=[True,False,True]),
        dict(check_id=2,all_ready=True,ready_by_type=[True,True,True])])
    job.preview_check = lambda *args:next(checks)
    batches = []
    def conditional(phase,context,index,amount,eligible,check_id):
        batches.append(dict(phase=phase,context=context,index=index,amount=amount,eligible=list(eligible),check_id=check_id))
        job.fees['shared'] += amount
        return len(batches)-1
    job.conditional_batch = conditional
    job.shared_phase('B','B',30)
    assert [row['eligible'] for row in batches]==[[1],[1]]
    assert [row['amount'] for row in batches]==[256,256]
    phase = job.saved[-1][1]
    assert phase['stop_reason']=='all_ready' and phase['paid_samples']==512
    assert phase['check_ids']==[0,1,2]


def laws():
    return [{S:dict(DELIVERY=F(1,2),LOST=F(1,2)),
        D:dict(DELIVERY=F(0),LOST=F(0),RECOVERY=F(1)),R:dict(DELIVERY=F(1,2),LOST=F(1,2))} for _ in range(78)]


def test_new_paired_seed_streams_and_return_shared_offsets_continue():
    assert (runner.SOURCE_BASE,runner.SHARED_BASE,runner.MEMBER_BASE,runner.EXECUTION_BASE,runner.MIX_BASE)==(308000,309000,310000,311000,312000)
    a,b = (runner.Simulator(1,laws(),Counter()) for _ in range(2))
    for phase,context,identity,operator,index in [('SOURCE','A',1,S,None),('SOURCE','B',2,D,None),
            ('SHARED','A',1,S,None),('MEMBER','B',2,R,31),('EXECUTION','B',2,D,31)]:
        left,right = a.observe(phase,context,identity,operator,index),b.observe(phase,context,identity,operator,index)
        assert left==right and left['draw_start']==0 and left['draw_end']==1
        base = {'SOURCE':308000,'SHARED':309000,'MEMBER':310000,'EXECUTION':311000}[phase]
        expected = base+((1*6+(0 if context=='A' else 3)+identity)*3 if index is None else (1*78+index)*3)+runner.core.OPERATORS.index(operator)
        assert left['seed']==expected
    later = a.observe('SHARED','A',1,S)
    assert later['draw_start']==1 and later['draw_end']==2


def test_new_impossibility_stops_member_before_frozen_actual_execution(monkeypatch):
    streams = {kind:StringIO() for kind in runner.FILE_KINDS}
    bundle = dict(cases=[deepcopy(CASE) for _ in range(78)],identities=[0]*78,laws=laws())
    job = runner.Lifecycle(0,runner.ARMS[0],bundle,streams)
    monkeypatch.setattr(runner.core,'make_plan',lambda member,case,*args:stub_plan(case,impossible=True))
    monkeypatch.setattr(runner.acquisition,'choose',lambda *args:pytest.fail('new impossibility must stop member acquisition'))
    original_execute = job.execute
    def execute(index,case,identity,mix):
        saved = json.loads(streams['decisions'].getvalue().strip())
        assert saved['terminal_plan']['goal_impossible'] and saved['terminal_plan']['box_goal_upper']=='4'
        assert saved['member']==runner.core.empty()
        return original_execute(index,case,identity,mix)
    job.execute = execute
    job.target(3)
    row = job.records[0]
    assert row['spent']==0 and row['execution_resolved'] and row['query_certified'] and row['joint_completed']
    assert row['actual_execution']['actual_samples']==0 and job.remaining==71
    assert row['pooled_after_terminal']==row['pooled_after_execution']


def faulty_plan():
    plan = stub_plan(CASE,lower=F(39,20),impossible=True)
    plan.update(mix=[('SHORT',F(1))],risk_upper=F(1,20))
    return plan


def true_law():
    return {S:dict(DELIVERY=F(1,2),LOST=F(1,2)),
        D:dict(DELIVERY=F(1),LOST=F(0),RECOVERY=F(0)),R:dict(DELIVERY=F(1),LOST=F(0))}


def test_every_initial_member_numeric_claim_is_scored_even_below_execution_threshold():
    bad,good = faulty_plan(),stub_plan(CASE)
    row = dict(life=0,arm=runner.ARMS[0],index=3,identity=0,case=CASE,initial_plan=bad,
        batches=[dict(plan=good,spent=16)])
    points = runner.score_execution_history(row,true_law())
    assert len(points)==2 and points[0]['prefix_position']==0 and not points[0]['is_terminal']
    assert points[0]['utility_lower']<2 and not points[0]['false_execution_certificate']
    assert points[0]['false_utility_lower'] and points[0]['false_risk_upper'] and points[0]['risk_violation']
    assert points[0]['false_goal_upper'] and points[0]['false_impossible_certificate']
    assert not any(points[-1][field] for field in runner.EXECUTION_ERRORS)


def test_full_preview_posthoc_scoring_contains_execution_and_query_claims():
    row = dict(life=0,arm=runner.ARMS[0],preview_id=0,check_id=0,index=30,stage='B',context='B',identity=1,cost_index=0,plan=faulty_plan())
    result = runner.score_preview(row,true_law())
    assert result['index']==30 and result['preview_id']==0 and result['check_id']==0
    assert result['false_query_certificates']>0
    assert result['false_utility_lower'] and result['false_risk_upper'] and result['false_impossible_certificate']
    assert result['new_impossible_vs_box'] and result['nonlooser_goal_upper']


@pytest.mark.parametrize('scope,field',[('history','false_utility_lower'),('aux','false_risk_upper'),('history','nonlooser_goal_upper')])
def test_stage_safety_includes_all_history_and_preview_numerical_claims(monkeypatch,scope,field):
    def aggregate(rows):
        return dict(targets=len(rows),query_certified=sum(row['query_certified'] for row in rows),
            joint_completed=sum(row['joint_completed'] for row in rows),execution_certified=len(rows),goal_impossible=0,
            **dict.fromkeys(('false_query_certificates','false_execution_certificates','false_impossible_certificates','false_goal_uppers','risk_violations'),0))
    monkeypatch.setattr(runner,'aggregate',aggregate)
    results,jobs,aux,history = [],[],[],[]
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index,stage in ((3,'A'),(42,'B'),(54,'A_RETURN')):
                results.append(dict(life=life,arm=arm,index=index,stage=stage,query_certified=True,joint_completed=True,
                    execution_certified=True,goal_impossible=False,new_impossible_vs_box=False,executed=dict(violation=False),
                    actual_execution=dict(actual_samples=0,realized=dict(delivery=0,failure=0,reward=F(0),goal_utility=F(0)))))
            jobs.append(dict(life=life,arm=arm,fees=dict(source=4608,shared=1 if arm==runner.ARMS[0] else 2,member=0,execution=0),
                auxiliary_records=1,timings=dict.fromkeys(runner.MODEL_SCOPES,0.),acquisition_seconds=0.,observation_seconds=0.,
                output_seconds=0.,profiles=0,cache_statistics={},work={}))
            common = dict(life=life,arm=arm,new_impossible_vs_box=False,nonlooser_goal_upper=True,
                **dict.fromkeys(runner.EXECUTION_ERRORS,False))
            history.append(dict(common,index=3,prefix_position=0,is_terminal=False))
            aux.append(dict(common,false_query_certificates=0))
    before = runner.summarize(results,aux,history,jobs)
    assert len(before['conditions'])==8 and before['conditions']['valid_certificates_and_execution']
    selected = history if scope=='history' else aux
    selected[0][field] = False if field=='nonlooser_goal_upper' else True
    after = runner.summarize(results,aux,history,jobs)
    assert not after['conditions']['valid_certificates_and_execution']
    if field=='nonlooser_goal_upper':
        assert not after['all_goal_uppers_nonlooser_than_box']


def test_six_worker_freeze_precedes_target_history_and_full_preview_scores(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'reports/goal_feasibility_v258')
    for version in ('trajectory_lifecycle_v256','coupled_impossibility_v257'):
        folder = tmp_path/'reports'/version
        runner.save(folder/'run.json',dict(complete=True))
        runner.save(folder/'analysis.json',dict(valid=True))
        runner.save(folder/'summary.json',dict(stage_condition_met=True,method_condition_met=False))
    state = dict(completed=0,closed=False,target=0,history=0,aux=0)
    metadata = dict(changed_operator=S,b_to_a=[0,1,2],stage_ranges={})
    monkeypatch.setattr(runner.task,'world',lambda life:([deepcopy(CASE)]*78,[{}]*78,[0]*78,metadata))
    monkeypatch.setattr(runner,'capture',lambda:None)
    class Future:
        def __init__(self,life,arm): self.life,self.arm = life,arm
        def result(self):
            state['completed'] += 1
            row = dict(life=self.life,arm=self.arm,index=3,identity=0,case=CASE,actual_execution={})
            with gzip.open(runner.filename('previews',self.life,self.arm),'wt') as stream:
                runner.write_row(stream,dict(row,context='A'))
            return dict(life=self.life,arm=self.arm,records=[row],worker_wall_seconds=0.)
    class Executor:
        def __init__(self,max_workers): assert max_workers==6
        def __enter__(self): return self
        def submit(self,function,life,arm,bundle):
            assert function is runner.run_life_arm
            return Future(life,arm)
        def __exit__(self,*args): state['closed'] = True
    def check(which):
        assert state['completed']==6 and state['closed']
        assert json.loads((runner.OUTPUT/'run.json').read_text())['phases'][-1]=='all_432_targets_auxiliary_and_executions_frozen'
        state[which] += 1
    def score_history(row,law):
        check('history')
        return [dict(new_impossible_vs_box=False)]
    def evaluate(row,law):
        check('target')
        return dict(life=row['life'],arm=row['arm'])
    def score_preview(row,law):
        check('aux')
        return dict(life=row['life'],arm=row['arm'])
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Executor)
    monkeypatch.setattr(runner,'score_execution_history',score_history)
    monkeypatch.setattr(runner,'evaluate',evaluate)
    monkeypatch.setattr(runner,'score_preview',score_preview)
    monkeypatch.setattr(runner,'summarize',lambda results,aux,history,jobs:dict(records=len(results),auxiliary_records=len(aux),execution_history_snapshots=len(history)))
    summary = runner.run()
    assert state==dict(completed=6,closed=True,target=6,history=6,aux=6)
    assert summary['records']==summary['auxiliary_records']==summary['execution_history_snapshots']==6
    assert all(runner.filename('execution_history_results',life,arm).is_file() for life in runner.LIVES for arm in runner.ARMS)
