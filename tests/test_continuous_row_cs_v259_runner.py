"""Three private arms, both-control advancement, and nine-job scoring barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_continuous_row_cs_v259 as runner

S,D,R = runner.core.OPERATORS
CASE = dict(id='test_case',context='A',stage='A',operating='low',retry_cost='17/20')


def synthetic_laws():
    return [{S:dict(DELIVERY=F(1,2),LOST=F(1,2)),D:dict(DELIVERY=F(0),LOST=F(0),RECOVERY=F(1)),
        R:dict(DELIVERY=F(1,2),LOST=F(1,2))} for _ in range(78)]


def test_fixed_three_arms_private_state_caches_and_physically_drawn_paired_sources():
    assert runner.ARMS==('CONTINUOUS_REUSE','TRAJECTORY_REUSE','TRAJECTORY_REBUILD')
    bundle = dict(cases=[deepcopy(CASE) for _ in range(78)],identities=[0]*78,laws=synthetic_laws())
    jobs = [runner.Lifecycle(0,arm,bundle,{kind:StringIO() for kind in runner.FILE_KINDS}) for arm in runner.ARMS]
    assert [job.state['research_arm'] for job in jobs]==list(runner.ARMS)
    assert [job.state['trajectory_arm'] for job in jobs]==['TRAJECTORY_REUSE','TRAJECTORY_REUSE','TRAJECTORY_REBUILD']
    jobs[0].cache['private_prefix'] = 1
    jobs[0].state['a']['pools'][0][S]['DELIVERY'] = 9
    assert all(not job.cache and job.state['a']['pools'][0][S]['DELIVERY']==0 for job in jobs[1:])
    for name in jobs[0].normalizers:
        assert len({id(job.normalizers[name]) for job in jobs})==3
    observations = [job.simulator.observe('SOURCE','A',0,S) for job in jobs]
    assert observations[0]==observations[1]==observations[2]
    assert observations[0]['seed']==313000
    assert all(job.simulator.offsets['SOURCE','A',0,S,None]==1 for job in jobs)
    assert len({id(job.simulator.generators['SOURCE','A',0,S,None]) for job in jobs})==3
    assert (runner.SOURCE_BASE,runner.SHARED_BASE,runner.MEMBER_BASE,runner.EXECUTION_BASE,runner.MIX_BASE)==(313000,314000,315000,316000,317000)


def summary_fixture():
    records,auxiliary,history,jobs = [],[],[],[]
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index in runner.TARGETS:
                stage = 'A' if index<27 else 'B' if index<54 else 'A_RETURN'
                records.append(dict(life=life,arm=arm,index=index,stage=stage,spent=0,query_certified=True,
                    joint_completed=True,execution_certified=True,goal_impossible=False,new_impossible_vs_box=False,
                    fallback=False,budget_exhausted=False,model_seconds=0.,history=[],executed=dict(violation=False,actual_utility=F(0)),
                    actual_execution=dict(actual_samples=0,realized=dict(delivery=0,failure=0,reward=F(0),goal_utility=F(0)))))
                history.append(dict(life=life,arm=arm,index=index,prefix_position=0,is_terminal=True,new_impossible_vs_box=False,
                    nonlooser_goal_upper=True,**dict.fromkeys(runner.EXECUTION_ERRORS,False)))
            auxiliary.append(dict(life=life,arm=arm,new_impossible_vs_box=False,nonlooser_goal_upper=True,false_query_certificates=0,
                **dict.fromkeys(runner.EXECUTION_ERRORS,False)))
            jobs.append(dict(life=life,arm=arm,fees=dict(source=4608,shared=500+100*runner.ARMS.index(arm),member=0,execution=0),
                auxiliary_records=1,timings=dict.fromkeys(runner.MODEL_SCOPES,0.),acquisition_seconds=0.,observation_seconds=0.,
                output_seconds=0.,profiles=0,cache_statistics={},work={}))
    return records,auxiliary,history,jobs


def test_all648_targets_and41472_physical_sources_are_charged_with_both_paired_controls():
    summary = runner.summarize(*summary_fixture())
    assert summary['records']==648 and summary['physical_source_samples']==41472
    assert set(summary['methods'])==set(runner.ARMS)
    assert all(method['fees']['source']==13824 for method in summary['methods'].values())
    assert len(summary['conditions'])==8 and summary['stage_condition_met']
    assert [(row['control'],row['life']) for row in summary['paired']]==[(arm,life) for arm in runner.ARMS[1:] for life in runner.LIVES]
    assert all(row['query_gains']==row['query_losses']==row['joint_gains']==row['joint_losses']==0 for row in summary['paired'])
    assert all(row['execution_resolved_gains']==row['execution_resolved_losses']==row['impossibility_gains']==row['impossibility_losses']==0
        for row in summary['paired'])
    assert [row['control_minus_continuous_samples'] for row in summary['paired']]==[100]*3+[200]*3
    assert summary['new_environment_observations']==41472+3*(500+600+700)


def test_paired_impossibility_and_resolution_gains_are_distinct_from_own_box_solver_gain():
    records,auxiliary,history,jobs=summary_fixture()
    for row in records:
        if row['life']!=0 or row['index'] not in (30,31):
            continue
        row['execution_certified']=False
        row['goal_impossible']=(row['index']==30 and row['arm']!=runner.ARMS[1]) or (row['index']==31 and row['arm']!=runner.ARMS[0])
        row['joint_completed']=row['goal_impossible']
        row['fallback']=not row['joint_completed']
    summary=runner.summarize(records,auxiliary,history,jobs)
    assert summary['methods'][runner.ARMS[0]]['new_impossible_vs_box']==0
    reuse=next(row for row in summary['paired'] if row['life']==0 and row['control']==runner.ARMS[1])
    rebuild=next(row for row in summary['paired'] if row['life']==0 and row['control']==runner.ARMS[2])
    assert reuse['execution_resolved_gains']==reuse['impossibility_gains']==1
    assert reuse['execution_resolved_losses']==reuse['impossibility_losses']==1
    assert rebuild['execution_resolved_gains']==rebuild['impossibility_gains']==0
    assert rebuild['execution_resolved_losses']==rebuild['impossibility_losses']==1
    assert reuse['query_gains']==reuse['query_losses']==rebuild['query_gains']==rebuild['query_losses']==0


@pytest.mark.parametrize('control',runner.ARMS[1:])
@pytest.mark.parametrize('index,condition',[(42,'matched_late_b_quality'),(54,'matched_a_return_quality')])
def test_each_quality_control_must_be_met_even_if_other_control_matches(control,index,condition):
    records,auxiliary,history,jobs = summary_fixture()
    other = next(arm for arm in runner.ARMS[1:] if arm!=control)
    for row in records:
        if row['life']==0 and row['index']==index and row['arm'] in (runner.ARMS[0],other):
            row['query_certified']=row['joint_completed']=False
            row['fallback']=True
    summary = runner.summarize(records,auxiliary,history,jobs)
    assert summary['conditions']['late_b_quality'] and summary['conditions']['a_return_quality']
    assert not summary['conditions'][condition] and not summary['conditions']['matched_joint_quality']
    own = next(row for row in summary['paired'] if row['life']==0 and row['control']==control)
    matched = next(row for row in summary['paired'] if row['life']==0 and row['control']==other)
    assert own['query_losses']==own['joint_losses']==1 and own['query_gains']==own['joint_gains']==0
    assert matched['query_losses']==matched['joint_losses']==0


@pytest.mark.parametrize('control',runner.ARMS[1:])
def test_cost_saving_must_be_strict_against_each_control(control):
    records,auxiliary,history,jobs = summary_fixture()
    for job in jobs:
        job['fees']['shared']=500 if job['arm'] in (runner.ARMS[0],control) else 600
    summary = runner.summarize(records,auxiliary,history,jobs)
    assert not summary['conditions']['actual_acquisition_saving']
    assert all(row['control_minus_continuous_samples']==0 for row in summary['paired'] if row['control']==control)


def test_continuous_stage_validity_also_covers_control_intermediate_claims():
    records,auxiliary,history,jobs = summary_fixture()
    point = next(row for row in history if row['arm']==runner.ARMS[2])
    point.update(is_terminal=False,false_risk_upper=True)
    summary = runner.summarize(records,auxiliary,history,jobs)
    assert not summary['conditions']['valid_certificates_and_execution']
    assert summary['methods'][runner.ARMS[2]]['history_execution_errors']['false_risk_upper']==1
    assert summary['methods'][runner.ARMS[0]]['history_execution_errors']['false_risk_upper']==0


def test_nine_jobs_with_six_workers_freeze_before_all_three_truth_scoring_paths(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'reports/continuous_row_cs_v259')
    previous = tmp_path/'reports/goal_feasibility_v258'
    runner.save(previous/'run.json',dict(complete=True))
    runner.save(previous/'analysis.json',dict(valid=True))
    runner.save(previous/'summary.json',dict(stage_condition_met=False))
    state = dict(completed=0,closed=False,target=0,history=0,aux=0)
    metadata = dict(changed_operator=S,b_to_a=[0,1,2],stage_ranges={})
    monkeypatch.setattr(runner.task,'world',lambda life:([deepcopy(CASE)]*78,[{}]*78,[0]*78,metadata))
    monkeypatch.setattr(runner,'capture',lambda:None)
    class Future:
        def __init__(self,life,arm): self.life,self.arm=life,arm
        def result(self):
            state['completed']+=1
            row=dict(life=self.life,arm=self.arm,index=3,identity=0,case=CASE,actual_execution={})
            with gzip.open(runner.filename('previews',self.life,self.arm),'wt') as stream:
                runner.write_row(stream,dict(row,context='A'))
            return dict(life=self.life,arm=self.arm,records=[row],worker_wall_seconds=0.,fees=dict(source=4608,shared=0,member=0,execution=0))
    class Executor:
        def __init__(self,max_workers): assert max_workers==6
        def __enter__(self): return self
        def submit(self,function,life,arm,bundle):
            assert function is runner.run_life_arm
            return Future(life,arm)
        def __exit__(self,*args): state['closed']=True
    def check(which):
        assert state['completed']==9 and state['closed']
        assert json.loads((runner.OUTPUT/'run.json').read_text())['phases'][-1]=='all_648_targets_auxiliary_and_executions_frozen'
        state[which]+=1
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
    monkeypatch.setattr(runner,'summarize',lambda results,aux,history,jobs:dict(records=len(results),auxiliary_records=len(aux),
        execution_history_snapshots=len(history),physical_source_samples=sum(job['fees']['source'] for job in jobs)))
    summary=runner.run()
    assert state==dict(completed=9,closed=True,target=9,history=9,aux=9)
    assert summary['records']==summary['auxiliary_records']==summary['execution_history_snapshots']==9
    assert summary['physical_source_samples']==41472
    protocol=json.loads((runner.OUTPUT/'run.json').read_text())
    assert protocol['arms']==list(runner.ARMS) and protocol['source_seed_base']==313000
    assert protocol['continuous_active_pool_streams']==12 and protocol['continuous_reserved_pool_streams']==18 and protocol['member_streams']==216
    assert protocol['prerequisites']==dict(v258_complete=True,v258_independent_valid=True,v258_stage_negative=True)
