"""Own source charges, filtered batches, current stopping and global scoring."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import io
import json
import pytest

from scripts import run_joint_unresolved_trajectory_v255 as runner

S,D,R = runner.evidence.OPERATORS


def proof(ready):
    return dict(all_ready=ready,threshold=4320,queries={query:dict(policy=policy,certified=ready or query=='reward',comparisons=[])
        for query,policy in (('reward','WAIT'),('goal','SHORT'),('risk','DETOUR_RETURN'))})


def record(item,ready=False,paid=None,check_id=0):
    return dict(deepcopy(item),check_id=check_id,selected_check_id=check_id,
        queries={q:dict(policy=p['policy']) for q,p in proof(ready)['queries'].items()},
        trajectory=proof(ready),total_paid_samples=paid or runner.SOURCE_COST,
        model_seconds=dict(point_vectors=0.,trajectory=0.))


def artifact(life,arm,records,paid=None):
    paid = paid or runner.TOTAL_CAPS[life]
    acquisition = paid-runner.SOURCE_COST
    return dict(life=life,arm=arm,records=records,intermediate_records=12,primitive_samples=paid,source_samples=runner.SOURCE_COST,
        acquisition_samples=acquisition,acquisition_paid_by_type=[acquisition,0,0],
        stop_reason='full_cap',final_ready_by_type=[True,False,True],acquisition_batches=1,
        timings=dict.fromkeys(runner.MODEL_SCOPES,1.),observation_seconds=2.,output_seconds=3.,
        worker_wall_seconds=4.,cache_statistics={},work={})


class Simulator:
    def __init__(self):
        self.calls=[]
        self.offsets,self.steps=Counter(),Counter()
    def observe(self,phase,identity,operator):
        self.calls.append((phase,identity,operator))
        key=phase,identity,operator
        start=self.offsets[key]
        self.offsets[key]+=1
        self.steps[phase]+=1
        return dict(seed=1,draw_start=start,draw_end=start+1,
            outcome='RECOVERY' if operator==D and identity==1 else 'DELIVERY',phase_step_index=self.steps[phase])


def test_batch_eligibility_is_frozen_and_conditional_rounds_and_tails_charge_actual_units():
    states=[runner.evidence.new_type_state() for _ in range(3)]
    simulator,work,tape,rounds,paid=Simulator(),Counter(),io.StringIO(),io.StringIO(),[0,0,0]
    sampled=runner.sample_batch(0,'DIRECT_JOINT_UNRESOLVED',1,8,[1],states,simulator,0,0,2,paid,tape,rounds,work)
    assert (sampled['step'],sampled['round_id'],sampled['cursor'])==(8,2,2)
    assert paid==[0,8,0] and all(identity==1 for _,identity,_ in simulator.calls)
    assert Counter(operator for _,_,operator in simulator.calls)=={S:4,D:2,R:2}
    assert sampled['batch']['actual_samples']==8 and sampled['batch']['standalone_S_tails']==2
    assert sampled['batch']['eligible_types_frozen']==[1]
    traces=[json.loads(line) for line in rounds.getvalue().splitlines()]
    assert [row['primitive_steps'] for row in traces]==[[1,2,3],[4,5,6]]
    assert len(states[1]['rounds'])==2 and states[1]['tail_s_samples']==2
    next_batch=runner.sample_batch(0,'DIRECT_JOINT_UNRESOLVED',2,12,[0,2],states,simulator,8,2,2,paid,tape,rounds,work)
    assert next_batch['batch']['cursor_before']==2 and next_batch['cursor']==3
    assert simulator.calls[-2:]==[('ACQUISITION',0,S),('ACQUISITION',2,S)]
    assert next_batch['batch']['complete_rounds']==1  # only type2's nonrecovery pair


def test_all_eligible_matched_batches_have_identical_paid_tapes_and_continuous_cursor():
    outputs=[]
    for arm in runner.ARMS:
        simulator=Simulator()
        states=[runner.evidence.new_type_state() for _ in range(3)]
        tape,rounds,work=io.StringIO(),io.StringIO(),Counter()
        paid=[0,0,0]
        source=runner.sample_batch(0,arm,0,8,[0,1,2],states,simulator,0,0,0,paid,tape,rounds,work)
        assert paid==[0,0,0]
        acquired=runner.sample_batch(0,arm,1,14,[0,1,2],states,simulator,8,source['round_id'],source['cursor'],paid,tape,rounds,work)
        rows=[json.loads(line) for line in tape.getvalue().splitlines()]
        outputs.append([{k:v for k,v in row.items() if k!='arm'} for row in rows])
        assert acquired['step']==14 and sum(paid)==6
        assert source['cursor']==1 and rows[8]['identity']==1
    assert outputs[0]==outputs[1]


def test_sources_are_physically_drawn_twice_and_phase_streams_never_reset(monkeypatch):
    draws=[]
    def draw(generator,law,operator,increments,amount,work,progress):
        draws.append((law,operator,generator.random()))
        increments['DELIVERY']+=1
        progress['draw_end']+=1
    monkeypatch.setattr(runner,'draw',draw)
    histories=[]
    for _ in runner.ARMS:
        simulator=runner.PrimitiveSimulator(1,['a','b','c'],Counter())
        source=simulator.observe('SOURCE',2,S)
        first=simulator.observe('ACQUISITION',2,S)
        second=simulator.observe('ACQUISITION',2,S)
        assert source['seed']==301000+(1*3+2)*3
        assert first['seed']==second['seed']==302000+(1*3+2)*3
        assert first['draw_start']==0 and second['draw_start']==1
        histories.append((source,first,second))
    assert len(draws)==6 and histories[0]==histories[1]
    assert draws[:3]==draws[3:]


def test_check_case_reuses_fixed_trajectory_math_and_has_no_row_backend(monkeypatch):
    state=runner.evidence.new_type_state()
    runner.evidence.observe_round(state,{S:'DELIVERY',D:'RECOVERY',R:'LOST'},1)
    received=[]
    original=runner.evidence.trajectory_certificates
    def evaluate(rounds,case,queries,cache,work):
        received.append((rounds,case,queries))
        return original(rounds,case,queries,cache,work)
    monkeypatch.setattr(runner.evidence,'trajectory_certificates',evaluate)
    result=runner.check_case(0,runner.ARMS[1],0,0,0,state,4608,{},Counter())
    assert result['trajectory']['threshold']==4320 and result['total_paid_samples']==4608
    assert received[0][0] is state['rounds'] and received[0][2]==result['queries']
    assert result['complete_rounds']==1 and result['native_n_by_operator'][R]==1
    assert set(result['model_seconds'])=={'point_vectors','trajectory'}


@pytest.mark.parametrize('ready_at_source',[False,True])
def test_worker_rechecks_all_costs_stops_and_projects_actual_fee_without_new_proofs(monkeypatch,tmp_path,ready_at_source):
    monkeypatch.setattr(runner,'OUTPUT',tmp_path)
    monkeypatch.setattr(runner,'activate_cold_caches',lambda:{})
    roster=runner.public_roster({life:runner.task.world(life) for life in runner.LIVES})
    own=[item for item in roster if item['life']==0 and item['arm']==runner.ARMS[1]]
    batches,calls=[],[]
    def sample(life,arm,batch_id,target,eligible,states,simulator,step,round_id,cursor,paid,tape,rounds,work):
        batches.append((batch_id,step,target,tuple(eligible),cursor))
        if batch_id==0:
            for state in states:
                runner.evidence.observe_round(state,{S:'DELIVERY',D:'DELIVERY',R:None},1)
        else:
            paid[1]+=target-step
        return dict(step=target,round_id=round_id+1,cursor=2,selection_seconds=0.,update_seconds=0.,
            observation_seconds=0.,output_seconds=0.,batch=dict(batch_id=batch_id,eligible_types_frozen=list(eligible),actual_samples=target-step))
    def check(life,arm,check_id,identity,cost_index,state,paid,cache,work):
        calls.append((check_id,identity,cost_index))
        item=dict(life=life,arm=arm,kind='INTERMEDIATE_CHECK',identity=identity,cost_index=cost_index,
            index=None,case=runner.case_for(life,arm,identity,cost_index))
        return record(item,ready_at_source or check_id>0 or identity!=1,paid,check_id)
    monkeypatch.setattr(runner,'sample_batch',sample)
    monkeypatch.setattr(runner,'check_case',check)
    artifact=runner.run_life_arm(0,runner.ARMS[1],['a','b','c'],own)
    expected=4608 if ready_at_source else 4864
    assert artifact['primitive_samples']==expected and artifact['source_samples']==4608
    assert artifact['stop_reason']=='all_ready' and artifact['final_ready_by_type']==[True]*3
    assert len(calls)==(12 if ready_at_source else 24)
    if not ready_at_source:
        assert batches==[(0,0,4608,(0,1,2),0),(1,4608,4864,(1,),2)]
    assert len(artifact['records'])==60
    for projected in artifact['records']:
        assert not any(projected['model_seconds'].values())
        if projected['checkpoint_label']!='SOURCE':
            assert projected['total_paid_samples']==expected and not projected['checkpoint_reached']
            assert projected['selected_check_id']==(0 if ready_at_source else 1)
    assert len(list(runner.rows(runner.filename('checks',0,runner.ARMS[1]))))==len(calls)
    meta=list(runner.rows(runner.filename('check_meta',0,runner.ARMS[1])))
    assert len(meta[-1]['case_refs'])==12 and meta[-1]['all_ready']


def test_summary_uses_joint_net_gain_all_check_errors_and_actual_two_arm_fees():
    worlds={life:runner.task.world(life) for life in runner.LIVES}
    roster=runner.public_roster(worlds)
    assert len(roster)==360 and Counter(item['kind'] for item in roster)==dict(CHECKPOINT=216,RETURN_PROJECTION=144)
    records=[]
    for item in roster:
        hard=(1,2,1)[item['life']]
        ready=item['identity']!=hard or item['arm']==runner.ARMS[1] and item['life']==0
        records.append(record(item,ready))
    artifacts=[artifact(life,arm,[],runner.TOTAL_CAPS[life]-(100 if arm==runner.ARMS[1] else 0))
        for life in runner.LIVES for arm in runner.ARMS]
    scores=[dict(arm=arm,false_certificates=0) for arm in runner.ARMS]
    summary=runner.summarize(records,scores,scores,artifacts)
    assert summary['methods'][runner.ARMS[0]]['terminal']['query_ready']==48
    assert summary['methods'][runner.ARMS[1]]['terminal']['query_ready']==56
    assert summary['terminal_paired']['query_ready']['gains']==8 and summary['positive_qualification_signal']
    assert summary['physical_observations']==96768-300 and summary['physical_source_samples']==27648
    assert summary['model_seconds']==24. and len(summary['fee_ledger'])==6
    bad=[dict(arm=runner.ARMS[0],false_certificates=1)]
    assert not runner.summarize(records,scores,bad,artifacts)['positive_qualification_signal']
    expensive=deepcopy(artifacts)
    for job in expensive:
        if job['arm']==runner.ARMS[1]:
            job['primitive_samples']+=101
    assert not runner.summarize(records,scores,scores,expensive)['positive_qualification_signal']


def test_all_six_workers_and_all_intermediate_public_decisions_freeze_before_truth(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'output')
    worlds={life:runner.task.world(life) for life in runner.LIVES}
    monkeypatch.setattr(runner.task,'world',lambda life:worlds[life])
    events,completed=[],[]
    monkeypatch.setattr(runner,'capture',lambda:events.append('capture'))
    class Future:
        def __init__(self,life,arm,roster):
            self.life,self.arm,self.roster=life,arm,roster
        def result(self):
            completed.append((self.life,self.arm))
            records=[record(item,True) for item in self.roster]
            with runner.gzip.open(runner.filename('checks',self.life,self.arm),'wt') as stream:
                for item in self.roster[:12]:
                    auxiliary=deepcopy(item)
                    auxiliary['kind']='INTERMEDIATE_CHECK'
                    runner.write_row(stream,record(auxiliary,True))
            return artifact(self.life,self.arm,records)
    class Executor:
        def __init__(self,max_workers):
            assert max_workers==6
        def __enter__(self):
            return self
        def submit(self,function,life,arm,laws,roster):
            assert events==['capture'] and function is runner.run_life_arm
            assert len(roster)==60 and laws==worlds[life][1][:3]
            frozen=json.loads((runner.OUTPUT/'run.json').read_text())
            assert not frozen['complete'] and frozen['phases'][-1]=='source_captured'
            assert len(json.loads((runner.OUTPUT/'public_roster.json').read_text()))==360
            return Future(life,arm,roster)
        def __exit__(self,*args):
            events.append('executor_exit')
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Executor)
    scored=[]
    def score(item,law):
        assert len(completed)==6 and events==['capture','executor_exit']
        frozen=json.loads((runner.OUTPUT/'run.json').read_text())
        assert not frozen['complete'] and frozen['phases'][-1]=='all_intermediate_and_360_public_records_frozen'
        assert law==worlds[item['life']][1][item['identity']]
        scored.append(item['kind'])
        return dict(arm=item['arm'],false_certificates=0)
    monkeypatch.setattr(runner,'score_record',score)
    result=runner.run()
    assert len(scored)==432 and Counter(scored)['INTERMEDIATE_CHECK']==72
    assert result['records']==360 and result['public_pairs']==180 and result['intermediate_records']==72
    protocol=json.loads((runner.OUTPUT/'run.json').read_text())
    assert protocol['complete'] and protocol['false_certificate_scope']=='all_intermediate_and_public_decisions'
    assert protocol['trajectory_threshold']==4320 and protocol['delta_per_life_fixed_arm']=='1/20'


def test_postfreeze_false_query_certificate_counts_every_query(monkeypatch):
    item=dict(life=0,arm=runner.ARMS[1],kind='INTERMEDIATE_CHECK',identity=0,cost_index=0,index=None,case={})
    retained=record(item,True)
    monkeypatch.setattr(runner,'query_score',lambda queries,law,case:{q:dict(regret=F(1,10) if q=='risk' else F(0)) for q in queries})
    result=runner.score_record(retained,'law')
    assert result['false_certificates']==1 and result['check_id']==0
