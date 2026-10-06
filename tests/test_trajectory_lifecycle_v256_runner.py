"""Four real fee components, legal execution feedback and full-cohort barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import io
import json
import pytest

from scripts import run_trajectory_lifecycle_v256 as runner

S,D,R=runner.core.OPERATORS


def bundle(life=0):
    cases,laws,identities,metadata=runner.task.world(life)
    return dict(cases=cases,laws=laws,identities=identities,metadata=metadata)


def job(monkeypatch):
    monkeypatch.setattr(runner,'activate_cold_caches',lambda:{})
    streams={kind:io.StringIO() for kind in runner.FILE_KINDS}
    return runner.Lifecycle(0,runner.ARMS[0],bundle(),streams)


class Simulator:
    def __init__(self):
        self.calls=[]
        self.offsets=Counter()
    def observe(self,phase,context,identity,operator,index=None):
        self.calls.append((phase,context,identity,operator,index))
        key=phase,context,identity,operator,index
        start=self.offsets[key]
        self.offsets[key]+=1
        return dict(seed=1,draw_start=start,draw_end=start+1,outcome='RECOVERY' if operator==D else 'DELIVERY')


def plan(case,resolved=False,query=False):
    return dict(case=case,mix=[('SHORT',F(1))],risk_upper=F(1,20),utility_lower=F(3) if resolved else F(1),
        goal_upper=F(4),goal_impossible=False,queries={q:dict(policy=p) for q,p in (('reward','WAIT'),('goal','SHORT'),('risk','SHORT'))},
        query_ready=query,query_evidence=dict(all_ready=query,threshold=4320,queries={q:dict(policy=p,certified=query or q=='reward',comparisons=[])
            for q,p in (('reward','WAIT'),('goal','SHORT'),('risk','SHORT'))}))


def test_available_budget_reserves_current_execution_and_future_B_without_doublecharging():
    fees=dict(source=3456,shared=4000,member=16,execution=3)
    assert runner.available_budget(14144,fees,72)==14144-3456-4000-16-3-1152-144
    partly=deepcopy(fees)
    partly['source']+=400
    assert runner.available_budget(14144,partly,72)==runner.available_budget(14144,fees,72)
    partly['source']=4608
    assert runner.available_budget(14144,partly,72)==runner.available_budget(14144,fees,72)
    executed=deepcopy(partly)
    executed['execution']+=1
    assert runner.available_budget(14144,executed,71)==runner.available_budget(14144,partly,72)+1


def test_shared_return_stream_continues_and_source_member_execution_use_separate_seeds(monkeypatch):
    calls=[]
    def draw(generator,law,operator,increments,amount,work,progress):
        calls.append((operator,generator.random()))
        increments['DELIVERY']+=1
        progress['draw_end']+=1
    monkeypatch.setattr(runner,'draw',draw)
    simulator=runner.Simulator(1,bundle(1)['laws'],Counter())
    source=simulator.observe('SOURCE','A',2,S)
    first=simulator.observe('SHARED','A',2,S)
    simulator.observe('SHARED','B',1,D)
    returned=simulator.observe('SHARED','A',2,S)
    member=simulator.observe('MEMBER','A',2,S,54)
    executed=simulator.observe('EXECUTION','A',2,S,54)
    assert source['seed']==303000+(1*6+2)*3
    assert first['seed']==returned['seed']==304000+(1*6+2)*3
    assert (first['draw_start'],returned['draw_start'])==(0,1)
    rng=runner.random.Random(first['seed'])
    assert calls[1][1]==rng.random() and calls[3][1]==rng.random()
    assert member['seed']==305000+(1*78+54)*3 and executed['seed']==306000+(1*78+54)*3


def test_conditional_source_shared_tails_enter_only_their_legal_native_evidence(monkeypatch):
    active=job(monkeypatch)
    active.simulator=Simulator()
    active.conditional_batch('SOURCE','A',3,8,[0,1,2])
    assert active.fees==dict(source=8,shared=0,member=0,execution=0)
    assert active.cursors['A']==1 and len(active.state['round_log'])==2
    assert sum(t['tail_s_samples'] for t in active.state['trajectory']['A'])==2
    assert sum(sum(row.values()) for pool in active.state['a']['pools'] for row in pool.values())==8
    batch=json.loads(active.streams['batches'].getvalue())
    assert batch['complete_rounds']==2 and batch['standalone_S_tails']==2
    active.conditional_batch('SHARED','A',54,3,[1],0)
    assert active.state['round_log'][-1]['identity']==1 and active.fees['shared']==3
    assert active.cursors['A']==2


def test_shared_has_no_quota_clamps_remaining_budget_and_rechecks_current_all12(monkeypatch):
    active=job(monkeypatch)
    active.fees['source']=3456
    active.fees['shared']=runner.TOTAL_CAPS[0]-4608-144-5
    active.simulator=Simulator()
    calls=[]
    def check(stage,context,index):
        calls.append((stage,context,index))
        return dict(check_id=len(calls)-1,ready_by_type=[True,False,True],all_ready=False)
    monkeypatch.setattr(active,'preview_check',check)
    active.shared_phase('A','A',3)
    assert len(calls)==2 and active.budget()['available']==0
    batch=json.loads(active.streams['batches'].getvalue())
    assert batch['actual_samples']==5 and batch['eligible_types_frozen']==[1]
    assert batch['standalone_S_tails']==2
    phase=json.loads(active.streams['phases'].getvalue())
    assert phase['paid_samples']==5 and phase['stop_reason']=='budget_exhausted'
    monkeypatch.setattr(active,'preview_check',lambda *args:dict(check_id=2,ready_by_type=[True]*3,all_ready=True))
    active.shared_phase('A_RETURN','A',54)
    phases=[json.loads(line) for line in active.streams['phases'].getvalue().splitlines()]
    assert phases[-1]['paid_samples']==0 and phases[-1]['stop_reason']=='all_ready'


@pytest.mark.parametrize('policy,expected_fee,expected_terminal',[
    ('WAIT',0,'ABORT'),('SHORT',1,'WON'),('DETOUR_RETURN',1,'ABORT'),('DETOUR_RETRY',2,'WON')])
def test_actual_execution_legal_cost_and_feedback_excludes_current_member_and_direct(monkeypatch,policy,expected_fee,expected_terminal):
    active=job(monkeypatch)
    active.simulator=Simulator()
    member=runner.core.empty()
    before=deepcopy((active.state['trajectory'],active.state['round_log'],member))
    actual=active.execute(3,active.bundle['cases'][3],0,[(policy,F(1))])
    assert actual['actual_samples']==expected_fee and active.fees['execution']==expected_fee
    assert actual['realized']['terminal']==expected_terminal and actual['released_execution_reserve']==2-expected_fee
    assert (active.state['trajectory'],active.state['round_log'],member)==before
    assert sum(sum(row.values()) for row in active.state['a']['pools'][0].values())==expected_fee
    assert active.remaining==71 and actual['mix_seed']==307003
    if policy=='DETOUR_RETURN':
        assert actual['realized']['failure']==actual['realized']['delivery']==0
    if policy=='DETOUR_RETRY':
        assert actual['realized']['reward']==-runner.core.native.mechanics.robust.learning.COST_PRIOR[active.bundle['cases'][3]['operating']][1]-F(active.bundle['cases'][3]['retry_cost'])


def test_member_stops_at_execution_resolution_even_if_direct_unresolved_and_terminal_is_flushed_before_execution(monkeypatch):
    active=job(monkeypatch)
    active.simulator=Simulator()
    def make(member,case,state,identity,index,cache,work):
        return plan(case,sum(member[S].values())>=16,False)
    monkeypatch.setattr(runner.core,'make_plan',make)
    monkeypatch.setattr(runner.acquisition,'choose',lambda *args:dict(operator=S,reason='original_execution_case'))
    original=active.execute
    def execute(index,case,identity,mix):
        decision=json.loads(active.streams['decisions'].getvalue())
        assert decision['terminal_plan']['utility_lower']=='3' and decision['executed_mix']==[['WAIT','1']]
        assert sum(decision['member'][S].values())==16 and active.remaining==72
        return original(index,case,identity,mix)
    monkeypatch.setattr(active,'execute',execute)
    active.target(3)
    row=active.records[0]
    assert row['spent']==16 and len(row['batches'])==1 and row['stop_reason']=='direct_unresolved_no_shared_budget'
    assert row['execution_resolved'] and not row['joint_completed'] and row['actual_execution']['actual_samples']==0
    assert active.fees['member']==16 and len(active.state['round_log'])==0
    assert active.acquisition_seconds<=active.timings['planning']


def test_terminal_plan_and_member_do_not_absorb_actual_nonwait_execution_feedback(monkeypatch):
    active=job(monkeypatch)
    active.simulator=Simulator()
    monkeypatch.setattr(runner.core,'make_plan',lambda member,case,*args:plan(case,True,True))
    active.target(3)
    row=active.records[0]
    assert row['spent']==0 and row['joint_completed'] and row['actual_execution']['actual_samples']==1
    assert sum(sum(counts.values()) for counts in row['member'].values())==0
    assert row['pooled_after_terminal'][S]['DELIVERY']==0 and row['pooled_after_execution'][S]['DELIVERY']==1
    assert active.state['round_log']==[] and row['budget_before']['execution_reserved']==144
    assert row['budget_after']['execution_reserved']==142


def test_direct_private_profiles_deduplicate_proofs_and_keep_actual_source_refs(monkeypatch):
    active=job(monkeypatch)
    case=active.bundle['cases'][3]
    certificate=dict(query='goal',chosen='SHORT',other='DETOUR_RETURN',certified=False,
        admitted_round_ids=[1,5],required_rows=[S,D],n=2,admitted_by_context=dict(A=1,B=1),cross_context=True)
    p=plan(case,True,False)
    p['query_evidence']['queries']['goal']['comparisons']=[certificate]
    one=active.retain(p,1)
    two=active.retain(deepcopy(p),1)
    assert one==two and len(active.profile_ids)==1
    profiles=[json.loads(line) for line in active.streams['profiles'].getvalue().splitlines()]
    assert profiles[0]['certificate']['admitted_round_ids']==[1,5]
    assert profiles[0]['query_identity']==1 and profiles[0]['case']['context']==case['context']
    assert one['query_evidence']['queries']['goal']['comparisons']==[dict(profile_id=0,other='DETOUR_RETURN',certified=False)]


def result(life,arm,index):
    stage='A' if index<30 else 'B' if index<54 else 'A_RETURN'
    point=dict(false_query_certificates=0,false_execution_certificate=False,false_impossible_certificate=False,
        goal_upper_ok=True,violation=False,coverage=True,actual_utility=F(3))
    actual=dict(actual_samples=0,realized=dict(reward=F(0),failure=0,delivery=0,goal_utility=F(0)))
    return dict(life=life,arm=arm,index=index,stage=stage,spent=0,model_seconds=0.,history=[point],terminal=point,
        executed=deepcopy(point),execution_certified=True,goal_impossible=False,query_certified=True,
        joint_completed=True,fallback=False,budget_exhausted=False,actual_execution=actual)


def artifact(life,arm,records):
    return dict(life=life,arm=arm,records=records,auxiliary_records=12,fees=dict(source=4608,shared=0,member=0,execution=0),
        timings=dict.fromkeys(runner.MODEL_SCOPES,0.),acquisition_seconds=0.,observation_seconds=0.,output_seconds=0.,
        profiles=0,cache_statistics={},work={},worker_wall_seconds=0.)


def test_advancement_keeps_expected_risk_separate_from_realized_failures_and_checks_all_aux():
    results=[result(life,arm,index) for life in runner.LIVES for arm in runner.ARMS for index in runner.TARGETS]
    artifacts=[artifact(life,arm,[]) for life in runner.LIVES for arm in runner.ARMS]
    artifacts[1]['fees']['member']=16
    artifacts[0]['fees']['execution']=1
    results[0]['actual_execution']['actual_samples']=1
    results[0]['actual_execution']['realized']['failure']=1
    summary=runner.summarize(results,[],artifacts)
    assert summary['stage_condition_met'] and summary['methods'][runner.ARMS[0]]['realized_failure']==1
    assert not summary['realized_failures_are_certificate_errors'] and summary['physical_source_samples']==27648
    assert summary['new_environment_observations']==27665 and len(summary['conditions'])==8
    bad=[dict(arm=runner.ARMS[0],false_query_certificates=1)]
    assert not runner.summarize(results,bad,artifacts)['conditions']['valid_certificates_and_execution']


def test_all_432_target_and_auxiliary_decisions_and_actual_executions_freeze_before_truth(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'output')
    prerequisite=tmp_path/'reports/joint_unresolved_trajectory_v255'
    prerequisite.mkdir(parents=True)
    for name,data in (('run',dict(complete=True)),('analysis',dict(valid=True)),('summary',dict(positive_qualification_signal=True))):
        runner.save(prerequisite/f'{name}.json',data)
    worlds={life:runner.task.world(life) for life in runner.LIVES}
    monkeypatch.setattr(runner.task,'world',lambda life:worlds[life])
    events,completed=[],[]
    monkeypatch.setattr(runner,'capture',lambda:events.append('capture'))
    class Future:
        def __init__(self,life,arm):
            self.life,self.arm=life,arm
        def result(self):
            completed.append((self.life,self.arm))
            records=[dict(life=self.life,arm=self.arm,index=index,actual_execution=result(self.life,self.arm,index)['actual_execution']) for index in runner.TARGETS]
            with runner.gzip.open(runner.filename('previews',self.life,self.arm),'wt') as stream:
                for identity in range(3):
                    for cost_index in range(4):
                        runner.write_row(stream,dict(life=self.life,arm=self.arm,context='A',identity=identity,
                            cost_index=cost_index,preview_id=identity*4+cost_index))
            return artifact(self.life,self.arm,records)
    class Executor:
        def __init__(self,max_workers):
            assert max_workers==6
        def __enter__(self):
            return self
        def submit(self,function,life,arm,bundle):
            assert events==['capture'] and function is runner.run_life_arm
            frozen=json.loads((runner.OUTPUT/'run.json').read_text())
            assert not frozen['complete'] and frozen['phases'][-1]=='source_captured'
            assert bundle['laws']==worlds[life][1]
            assert (runner.OUTPUT/'cases.json').exists() and (runner.OUTPUT/'interfaces.json').exists()
            return Future(life,arm)
        def __exit__(self,*args):
            events.append('executor_exit')
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Executor)
    scored=[]
    def assert_frozen():
        assert len(completed)==6 and events==['capture','executor_exit']
        frozen=json.loads((runner.OUTPUT/'run.json').read_text())
        assert not frozen['complete'] and frozen['phases'][-1]=='all_432_targets_auxiliary_and_executions_frozen'
    def evaluate(row,law):
        assert_frozen()
        assert law==worlds[row['life']][1][row['index']]
        scored.append('target')
        return result(row['life'],row['arm'],row['index'])
    def preview(row,law):
        assert_frozen()
        assert law==worlds[row['life']][1][row['identity']]
        scored.append('preview')
        return dict(arm=row['arm'],false_query_certificates=0)
    monkeypatch.setattr(runner,'evaluate',evaluate)
    monkeypatch.setattr(runner,'score_preview',preview)
    summary=runner.run()
    assert Counter(scored)==dict(target=432,preview=72) and summary['records']==432
    protocol=json.loads((runner.OUTPUT/'run.json').read_text())
    assert protocol['complete'] and protocol['execution_risk_limit']=='1/20'
    assert protocol['confidence_scope']=='per_life_fixed_arm_query_plus_execution_1/10_not_whole_cohort'
