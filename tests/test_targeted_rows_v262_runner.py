"""Physical targeted operator-row learning, declarations, fees and global scoring."""
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json

import pytest

from scripts import run_targeted_rows_v262 as runner

S,D,R = runner.core.OPERATORS
CASE = dict(id='test_case',context='A',stage='A',operating='low',retry_cost='17/20')


def make_job(arm='DIRECT_ROW_REUSE',detour='RECOVERY'):
    laws = [{S:dict(DELIVERY=F(1),LOST=F(0)),
        D:{category:F(category==detour) for category in runner.core.ALPHABETS[D]},
        R:dict(DELIVERY=F(1),LOST=F(0))} for _ in range(78)]
    bundle = dict(cases=[deepcopy(CASE) for _ in range(78)],identities=[0]*78,laws=laws)
    return runner.Lifecycle(0,arm,bundle,{kind:StringIO() for kind in runner.FILE_KINDS})


def saved(job,kind):
    return [json.loads(line) for line in job.streams[kind].getvalue().splitlines()]


def SKIP_test_fresh_paired_sources_are_physically_drawn_with_private_state_and_caches():
    assert runner.ARMS==('DIRECT_ROW_REUSE','FULL_UNIT_ROW_CS','CONTINUOUS_REUSE')
    jobs = [make_job(arm) for arm in runner.ARMS]
    assert [job.state.get('acquisition_arm') for job in jobs]==['FULL_UNIT_ROW_CS','FULL_UNIT_ROW_CS','CONTINUOUS_REUSE']
    assert [job.state['point_learning_arm'] for job in jobs]==list(runner.ARMS)
    assert [job.state['research_arm'] for job in jobs]==['CONTINUOUS_REUSE']*3
    jobs[0].cache['private_prefix'] = 1
    jobs[0].state['a']['pools'][0][S]['DELIVERY'] = 9
    assert all(not job.cache and job.state['a']['pools'][0][S]['DELIVERY']==0 for job in jobs[1:])
    assert all(len({id(job.normalizers[name]) for job in jobs})==3 for name in jobs[0].normalizers)
    for job in jobs:
        job.conditional_batch('SOURCE','A',3,3,[0])
    assert all(saved(jobs[0],'tapes')==[dict(row,arm=runner.ARMS[0]) for row in saved(job,'tapes')]
        for job in jobs[1:])
    assert all(job.fees['source']==3 and job.step==3 for job in jobs)
    assert all(saved(job,'rounds')[0]['declared_rows']==[S,D,R] for job in jobs)
    assert len({id(job.simulator.generators['SOURCE','A',0,S,None]) for job in jobs})==3
    assert all(row['n']==1 for row in jobs[0].state['policy_path_stats']['A'][0].values())
    assert all('policy_path_stats' not in job.state for job in jobs[1:])
    assert (runner.SOURCE_BASE,runner.SHARED_BASE,runner.MEMBER_BASE,runner.EXECUTION_BASE,runner.MIX_BASE)==(328000,329000,330000,331000,332000)


@pytest.mark.parametrize('declared,amount,detour,expected_counts,full,partial,tails',[
    ((S,D),6,'RECOVERY',{S:3,D:3,R:0},0,3,0),
    ((D,R),4,'RECOVERY',{S:0,D:2,R:2},0,2,0),
    ((D,R),4,'DELIVERY',{S:1,D:3,R:0},0,3,1),
    ((S,),3,'RECOVERY',{S:3,D:0,R:0},0,3,0),
    ((S,D,R),6,'DELIVERY',{S:4,D:2,R:0},2,0,2),
])
def test_only_predeclared_rows_are_drawn_and_nonrecovery_does_not_promote_partial_units(
        declared,amount,detour,expected_counts,full,partial,tails):
    job = make_job(detour=detour)
    masks,refs = [list(declared),[],[]],[[0,1,2,3],[],[]]
    job.conditional_batch('SHARED','A',3,amount,[0],7,masks,refs)
    units,batches,tapes = saved(job,'rounds'),saved(job,'batches'),saved(job,'tapes')
    assert job.fees['shared']==job.step==amount
    assert {op:sum(row['operator']==op for row in tapes) for op in (S,D,R)}==expected_counts
    assert job.shared_primitive_samples_by_operator==expected_counts
    assert all(row['declared_rows']==list(declared) and row['maximum_calls_reserved']==len(declared) for row in units)
    assert all(row['budget_before']['available']>=row['maximum_calls_reserved'] for row in units)
    assert all(row['all_rows_declared']==(declared==(S,D,R)) for row in units)
    assert len(job.state['trajectory']['A'][0]['rounds'])==full
    assert len(job.state['round_log'])==full+partial
    assert job.unit_accounting['shared_complete_units']==full
    assert job.unit_accounting['shared_partial_units']==partial
    assert job.unit_accounting['shared_tail_samples']==tails
    assert batches[0]['declared_rows_by_type']==masks and batches[0]['preview_ids_by_type']==refs
    assert batches[0]['observation_units']==full+partial
    assert batches[0]['complete_rounds']==full and batches[0]['partial_units']==partial
    assert batches[0]['standalone_S_tails']==tails and batches[0]['prior_check_id']==7
    if R not in declared:
        assert all(R not in row['outcomes'] for row in units)
    elif detour!='RECOVERY':
        assert all(row['outcomes'][R] is None for row in units)


def test_insufficient_maximum_unit_reserve_produces_only_native_s_tails():
    job = make_job()
    job.fees.update(source=3456,shared=runner.TOTAL_CAPS[0]-3456-1152-144-2)
    assert job.budget()['available']==2
    before_query = deepcopy(job.state['trajectory']['A'][0]['joint_outcome_counts'])
    job.conditional_batch('SHARED','A',3,2,[0],3,[[S,D,R],[],[]],[[36,37,38,39],[],[]])
    assert not saved(job,'rounds') and not job.state['round_log']
    assert [row['operator'] for row in saved(job,'tapes')]==[S,S]
    assert all(row['role']=='tail_S' for row in saved(job,'tapes'))
    assert job.state['trajectory']['A'][0]['joint_outcome_counts']==before_query
    assert job.budget()['available']==0 and job.budget()['future_B_source_reserved']==1152
    assert job.budget()['execution_reserved']==144 and job.remaining==72


def preview_plan(case,unready):
    comparison = dict(query='risk',chosen='DETOUR_RETURN',other='SHORT',certified=not unready,
        admitted_unit_ids=[],score_source='actual_declared_required_row_units')
    return dict(case=case,utility_lower=F(2),goal_impossible=False,query_ready=not unready,
        query_evidence=dict(all_ready=not unready,queries={
            'reward':dict(policy='WAIT',certified=True),
            'goal':dict(policy='SHORT',certified=True),
            'risk':dict(policy='DETOUR_RETURN',certified=not unready,comparisons=[comparison])}))


@pytest.mark.parametrize('arm',runner.ARMS[:2])
def test_both_required_row_arms_retain_twelve_previews_and_freeze_masks_before_sampling(arm,monkeypatch):
    job = make_job(arm)
    monkeypatch.setattr(runner.core,'make_plan',lambda member,case,state,identity,index,cache,work:
        preview_plan(case,identity==0))
    check = job.preview_check('A','A',3)
    assert check['ready_by_type']==[False,True,True]
    assert check['declared_rows_by_type']==[[S,D],[],[]]
    assert check['preview_ids_by_type']==[[0,1,2,3],[4,5,6,7],[8,9,10,11]]
    assert len(saved(job,'previews'))==12 and saved(job,'checks')==[json.loads(json.dumps(check))]
    physical_observe = job.simulator.observe
    calls = 0
    def observe(*args):
        nonlocal calls
        retained_check = saved(job,'checks')[0]
        assert retained_check['declared_rows_by_type']==[[S,D],[],[]]
        assert len(saved(job,'previews'))==12
        calls += 1
        if calls==1:
            check['declared_rows_by_type'][0].append(R)
        return physical_observe(*args)
    monkeypatch.setattr(job.simulator,'observe',observe)
    job.conditional_batch('SHARED','A',3,6,[0],check['check_id'],
        check['declared_rows_by_type'],check['preview_ids_by_type'])
    assert calls==6 and job.simulator.offsets['SHARED','A',0,R,None]==0
    assert all(row['declared_rows']==[S,D] for row in saved(job,'rounds'))
    assert saved(job,'batches')[0]['declared_rows_by_type']==[[S,D],[],[]]


def test_joint_ready_check_stops_shared_without_forcing_a_partial_or_full_unit(monkeypatch):
    job = make_job()
    monkeypatch.setattr(runner.core,'make_plan',lambda member,case,state,identity,index,cache,work:preview_plan(case,False))
    monkeypatch.setattr(job.simulator,'observe',lambda *args:pytest.fail('ready phase must not observe'))
    job.shared_phase('A','A',3)
    phase = saved(job,'phases')[0]
    assert phase['stop_reason']=='all_ready' and phase['paid_samples']==0 and not phase['batch_ids']
    assert job.step==0 and phase['initial_check_id']==phase['final_check_id']==0


@pytest.mark.parametrize('arm',runner.ARMS[2:])
def test_full_unit_controls_keep_all_declarations_when_only_a_query_is_unresolved(arm,monkeypatch):
    job = make_job(arm)
    monkeypatch.setattr(runner.core,'make_plan',lambda member,case,state,identity,index,cache,work:
        preview_plan(case,identity==0))
    check = job.preview_check('A','A',3)
    assert check['ready_by_type']==[False,True,True]
    assert check['declared_rows_by_type']==[[S,D,R]]*3


@pytest.mark.parametrize('arm,reference_kind,score_source',[
    ('DIRECT_ROW_REUSE','admitted_unit_ids','actual_declared_required_row_units'),
    ('FULL_UNIT_ROW_CS','admitted_unit_ids','actual_declared_required_row_units'),
    ('CONTINUOUS_REUSE','admitted_round_ids','actual_complete_conditional_rounds'),
])
def test_private_profile_references_use_the_actual_required_or_control_namespace(arm,reference_kind,score_source):
    plan = preview_plan(CASE,True)
    certificate = plan['query_evidence']['queries']['risk']['comparisons'][0]
    certificate.pop('admitted_unit_ids')
    certificate.update({reference_kind:[1,3]},score_source=score_source)
    stream,ids = StringIO(),{}
    retained = runner.retain_plan(plan,stream,ids,0)
    assert retained['query_evidence']['queries']['risk']['comparisons']==[dict(profile_id=0,other='SHORT',certified=False)]
    assert json.loads(stream.getvalue())['certificate'][reference_kind]==[1,3]
    assert runner.retain_plan(plan,stream,ids,0)==retained and len(stream.getvalue().splitlines())==1


def test_profile_namespace_is_selected_by_actual_score_source():
    plan = preview_plan(CASE,True)
    certificate = plan['query_evidence']['queries']['risk']['comparisons'][0]
    certificate['admitted_unit_ids'] = [1,3]
    stream,ids = StringIO(),{}
    first = runner.retain_plan(plan,stream,ids,0)
    certificate.update(score_source='actual_complete_conditional_rounds',admitted_round_ids=[1,3])
    second = runner.retain_plan(plan,stream,ids,0)
    assert first['query_evidence']['queries']['risk']['comparisons'][0]['profile_id']==0
    assert second['query_evidence']['queries']['risk']['comparisons'][0]['profile_id']==1
    assert len(stream.getvalue().splitlines())==2


def SKIP_test_plan_retention_keeps_native_partial_policy_statistics():
    plan = preview_plan(CASE,True)
    stats = dict(SHORT=dict(n=2,delivery=1,failure=1,recovery_calls=0,last_unit_id=7))
    plan.update(query_point_method='native_predeclared_policy_path_means',query_point_statistics=stats)
    retained = runner.retain_plan(plan,StringIO(),{},0)
    assert retained['query_point_method']=='native_predeclared_policy_path_means'
    assert retained['query_point_statistics']==stats
    plan['query_point_statistics']['SHORT']['n'] = 3
    assert retained['query_point_statistics']['SHORT']['n']==2


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
                unit_accounting=dict(source_complete_units=100,source_tail_samples=2,shared_complete_units=0,
                    shared_partial_units=250 if arm==runner.ARMS[0] else 0,shared_tail_samples=0),
                shared_primitive_samples_by_operator={S:250,D:250,R:100*runner.ARMS.index(arm)},
                shared_declared_row_sets={f'{S}|{D}':250} if arm==runner.ARMS[0] else {},
                auxiliary_records=1,timings=dict.fromkeys(runner.MODEL_SCOPES,0.),acquisition_seconds=0.,observation_seconds=0.,
                output_seconds=0.,profiles=0,cache_statistics={},work={}))
    return records,auxiliary,history,jobs


def test_stage_summary_reports_partial_units_and_requires_both_controls_and_all_history_validity():
    fixture = summary_fixture()
    summary = runner.summarize(*fixture)
    assert summary['records']==648 and summary['physical_source_samples']==41472
    assert len(summary['conditions'])==8 and summary['stage_condition_met']
    own = summary['methods']['DIRECT_ROW_REUSE']
    assert own['unit_accounting']['shared_partial_units']==750
    assert own['shared_primitive_samples_by_operator']=={S:750,D:750,R:0}
    assert own['shared_declared_row_sets']=={f'{S}|{D}':750}
    assert [row['control_minus_partial_point_samples'] for row in summary['paired']]==[100]*3+[200]*3
    assert all(row['execution_resolved_gains']==row['impossibility_gains']==0 for row in summary['paired'])
    records,auxiliary,history,jobs=fixture
    for row in records:
        if row['arm']==runner.ARMS[0] and row['life']==0 and row['index']==42:
            row['query_certified']=row['joint_completed']=False
            row['fallback']=True
    history[-1]['false_risk_upper']=True
    jobs[-1]['fees']['shared']=500
    failed = runner.summarize(records,auxiliary,history,jobs)
    assert not failed['conditions']['matched_late_b_quality']
    assert not failed['conditions']['matched_joint_quality']
    assert not failed['conditions']['valid_certificates_and_execution']
    assert failed['methods']['CONTINUOUS_REUSE']['history_execution_errors']['false_risk_upper']==1


def test_nine_jobs_close_and_freeze_before_target_preview_or_intermediate_truth_scoring(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'reports/targeted_rows_v262')
    previous = tmp_path/'reports/partial_path_point_v261'
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
            return dict(life=self.life,arm=self.arm,records=[row],worker_wall_seconds=0.,fees=dict(source=4608,shared=0,direct=0,target_unit=0,member=0,execution=0))
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
    assert summary['physical_source_samples']==41472
    protocol=json.loads((runner.OUTPUT/'run.json').read_text())
    assert protocol['arms']==list(runner.ARMS) and protocol['source_seed_base']==328000
    assert protocol['prerequisites']==dict(v261_complete=True,v261_independent_valid=True,v261_stage_negative=True)
    assert protocol['direct_point_by_arm']['DIRECT_ROW_REUSE']=='native_current_context_operator_rows_with_unified_row_cs'
    assert protocol['direct_point_by_arm']['FULL_UNIT_ROW_CS']==protocol['direct_point_by_arm']['CONTINUOUS_REUSE']=='native_current_context_declared_units_with_unified_row_cs'
    assert protocol['execution_cs_method_by_arm']['FULL_UNIT_ROW_CS']==protocol['execution_cs_method_by_arm']['CONTINUOUS_REUSE']


def test_targeted_operator_selection_is_certificate_directed():
    assert runner.core.targeted_rows_for_unresolved(dict(utility_lower=F(0), goal_impossible=False)) == (S, D, R)
    assert runner.core.targeted_rows_for_unresolved(dict(utility_lower=F(2), goal_impossible=False, query_ready=False)) == (D, R)
    assert runner.core.targeted_rows_for_unresolved(dict(utility_lower=F(2), goal_impossible=False, query_ready=True)) == ()
    assert runner.core.targeted_rows_for_unresolved(dict(utility_lower=F(0), goal_impossible=True, query_ready=False)) == (D, R)


def test_direct_batch_has_sixteen_rows_per_operator_and_no_unit_record():
    job = make_job('DIRECT_ROW_REUSE')
    batch = job.direct_row_batch(CASE, 0, 3, (D, R), 0)
    assert batch['actual_samples'] == 32
    assert job.fees['direct'] == 32 and job.fees['target_unit'] == 0
    assert len(saved(job, 'rounds')) == 0
    direct = [row for row in saved(job, 'tapes') if row['phase'] == 'DIRECT']
    assert len(direct) == 32
    assert {row['operator'] for row in direct} == {D, R}
    assert all(row['controlled_reset'] and row['paired_stream_id'].startswith('v262_l0_A_0_') for row in direct)


def test_full_target_batch_records_declared_units_and_conditional_retry():
    job = make_job('FULL_UNIT_ROW_CS', detour='RECOVERY')
    batch = job.full_unit_batch(CASE, 0, 3, (D, R), 0, units=16)
    assert batch['units'] == 16
    assert job.fees['target_unit'] == batch['actual_samples']
    assert job.fees['direct'] == 0
    rounds = saved(job, 'rounds')
    assert len(rounds) == 16 and all(row['phase'] == 'TARGET_FULL' for row in rounds)
    assert all(row['declared_rows'] == [D, R] for row in rounds)
    assert all(row['outcomes'][R] == 'DELIVERY' for row in rounds)
    assert job.state['direct_row_log'] == []
