"""Verify chronological snapshots, private proofs, fixed comparison and freeze."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
import pytest

from scripts import run_paid_return_views_v253 as runner

S,D,R=runner.core.OPERATORS


def empty():
    return {op:dict.fromkeys(runner.core.ALPHABETS[op],0) for op in runner.core.OPERATORS}


def plan(ready=False,impossible=False,utility='3'):
    policies=dict(reward='WAIT',goal='SHORT',risk='DETOUR_RETURN')
    return dict(utility_lower=utility,goal_impossible=impossible,query_ready=ready,
        queries={q:dict(policy=p) for q,p in policies.items()},
        query_blockers={q:[] if ready or q=='reward' else ['DETOUR_RETRY'] for q in policies},
        query_evidence=dict(queries={q:dict(policy=p,certified=ready or q=='reward',
            **(dict(comparisons=[dict(profile_id=777,other='DETOUR_RETRY',certified=ready)]) if q!='reward' else {}))
            for q,p in policies.items()},all_ready=ready,threshold=960))


def baseline(tmp_path):
    directory=tmp_path/'baseline'
    directory.mkdir()
    a,b=[],[]
    for identity in range(3):
        aa,bb=empty(),empty()
        for op in runner.core.OPERATORS:
            aa[op]['DELIVERY'],aa[op]['LOST']=384-identity,identity
            bb[op]['DELIVERY'],bb[op]['LOST']=128-identity,identity
        a.append(aa);b.append(bb)
    runner.save(directory/'source_evidence.json',[dict(life=life,a=a,b=b) for life in runner.LIVES])
    runner.save(directory/'interfaces.json',[dict(life=life,identities=[index%3 for index in range(78)],
        metadata=dict(changed_operator=S,b_to_a=[1,2,0])) for life in runner.LIVES])
    runner.save(directory/'run.json',dict(complete=True))
    runner.save(directory/'analysis.json',dict(valid=True))
    for life in runner.LIVES:
        for arm in runner.ARMS:
            tape=[]
            for context,operator in (('A',S),('B',S)):
                for identity in range(3):
                    increments=dict.fromkeys(runner.core.ALPHABETS[operator],0)
                    increments['DELIVERY']=16
                    tape.append(dict(context=context,identity=identity,operator=operator,increments=increments))
            (directory/f'probes_life_{life:02d}_{arm}.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in tape))
            runner.save(directory/f'a_phase_life_{life:02d}_{arm}.json',dict(a_paid_samples=48,released_delta=3024))
            with gzip.open(directory/f'records_life_{life:02d}_{arm}.jsonl.gz','wt') as stream:
                history=0
                for index in runner.TARGETS:
                    context='A' if index<30 or index>=54 else 'B'
                    identity=index%3
                    operator=S if context=='A' else R
                    increments=dict.fromkeys(runner.core.ALPHABETS[operator],0)
                    increments['DELIVERY']=16
                    fees=dict.fromkeys(runner.FEE_FIELDS,0)
                    fees.update(source_paid_samples=3456 if index<30 else 4608,
                        history_paid_samples=history,ordinary_history_paid_samples=history,
                        actual_probe_paid_before=48 if index<30 else 96,current_paid_samples=16,new_paid_samples=16,
                        total_reference_paid_samples=(3456+48 if index<30 else 4608+96)+history+16)
                    row=dict(life=life,arm=arm,index=index,identity=identity,spent=16,
                        case=dict(id=f'l{life}/{index}',context=context,stage='A' if index<30 else 'B' if index<54 else 'A_RETURN',
                            operating='low',retry_cost='17/20'),batches=[dict(operator=operator,increments=increments)],
                        terminal_plan=plan(index%2==0),executed_mix=[['WAIT','1']],**fees)
                    stream.write(json.dumps(row)+'\n')
                    history+=16
    return directory


def test_all_144_own_time_snapshots_exclude_future_a_and_inherited_b_counts(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    monkeypatch.setattr(runner,'BASELINE',directory)
    snapshots,fees=runner.collect_snapshots()
    assert len(snapshots)==144
    assert Counter((s['life'],s['arm']) for s in snapshots)=={(life,arm):24 for life in runner.LIVES for arm in runner.ARMS}
    chosen=[s for s in snapshots if s['life']==0 and s['arm']=='QUERY_SHARED' and s['identity']==0]
    first,last=chosen[0],chosen[-1]
    assert first['index']==54 and last['index']==75
    assert first['a_pool'][S]['DELIVERY']==544 and last['a_pool'][S]['DELIVERY']==656
    assert first['member'][S]['DELIVERY']==16 and first['a_source'][S]['DELIVERY']==384
    assert first['mapped_b_identity']==2 and first['b_source'][R]['DELIVERY']==126
    assert sum(first['b_pool'][R].values())==256
    assert sum(first['b_pool'][D].values())==128
    observed,_,transfer=runner.core.two_way_evidence(first)
    assert sum(observed[R].values())==384+256
    assert sum(observed[D].values())==384+128
    assert transfer['total_samples']==384 and S not in transfer['operators']
    assert first['retained_executed_mix']==[['WAIT','1']]
    assert first['one_way_plan']['query_evidence']['queries']['goal']['comparisons'][0]['profile_id']==777
    assert all(f['source_samples']==4608 and f['ordinary_target_samples']==1152 and f['probe_samples']==96
        and f['total_samples']==5856 for f in fees)
    assert first['a_pool'][S]['DELIVERY']==544


def test_missing_original_return_record_cannot_silently_shrink_roster(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    path=directory/'records_life_00_QUERY_SHARED.jsonl.gz'
    records=list(runner.rows(path))
    with gzip.open(path,'wt') as stream:
        stream.writelines(json.dumps(row)+'\n' for row in records if row['index']!=77)
    monkeypatch.setattr(runner,'BASELINE',directory)
    with pytest.raises(ValueError,match='all native'):
        runner.collect_snapshots()


def test_private_new_profiles_and_cache_never_copy_or_replan_one_way(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    monkeypatch.setattr(runner,'BASELINE',directory)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path)
    snapshots,_=runner.collect_snapshots()
    monkeypatch.setattr(runner,'activate_cold_caches',lambda:{})
    calls,caches=[],[]
    def new_plan(snapshot,cache,work):
        if not cache:
            caches.append(cache)
        cache['local_job']=True
        calls.append((snapshot['life'],snapshot['arm'],snapshot['index']))
        p=plan(True)
        p['case']=snapshot['case']
        certificate=dict(query='goal',chosen='SHORT',other='DETOUR_RETRY',family='S_D_FULL_R',
            projected_counts={'S':{'DELIVERY':1,'OTHER':1}},certified=True)
        p['query_evidence']['queries']['goal']['comparisons']=[certificate]
        p['query_evidence']['queries']['risk']['comparisons']=[]
        return p
    monkeypatch.setattr(runner.core,'make_two_way',new_plan)
    first=[s for s in snapshots if s['life']==0 and s['arm']=='QUERY_SHARED'][:2]
    second=[s for s in snapshots if s['life']==1 and s['arm']=='QUERY_SHARED'][:2]
    before=deepcopy((first,second))
    for life,selected in ((0,first),(1,second)):
        artifact=runner.run_life_arm(life,'QUERY_SHARED',selected)
        assert len(artifact['records'])==2 and artifact['profiles']==1
        assert all(row['one_way_plan']==original['one_way_plan'] and row['retained_executed_mix']==original['retained_executed_mix']
            for row,original in zip(artifact['records'],selected))
        assert all(row['two_way_plan']['query_evidence']['queries']['goal']['comparisons'][0]['profile_id']==0 for row in artifact['records'])
        assert all(row['one_way_plan']['query_evidence']['queries']['goal']['comparisons'][0]['profile_id']==777 for row in artifact['records'])
        profiles=list(runner.rows(runner.worker_filename('profiles',life,'QUERY_SHARED')))
        assert len(profiles)==1 and profiles[0]['profile_id']==0
    assert len(calls)==4 and len(caches)==2 and caches[0] is not caches[1]
    assert (first,second)==before


def test_summary_separates_execution_certification_resolution_and_fixed_views():
    records=[]
    for arm in runner.ARMS:
        for index in range(54,58):
            old=plan(index!=55)
            new=plan(index!=54)
            if index==56:
                old=plan(True,impossible=True,utility='0')
                new=plan(True,impossible=True,utility='0')
            records.append(dict(life=0,arm=arm,index=index,identity=0,one_way_plan=old,two_way_plan=new))
    summary=runner.summarize(records,[])
    for arm in summary['arm_summaries']:
        assert arm['views']['ONE_WAY']['query_ready']==arm['views']['TWO_WAY']['query_ready']==3
        assert arm['views']['ONE_WAY']['execution_certified']==3
        assert arm['views']['ONE_WAY']['execution_resolved']==4
        assert arm['views']['ONE_WAY']['goal_impossible']==1
        assert arm['paired']['query_ready']['gains']==arm['paired']['query_ready']['losses']==1
        assert arm['paired']['joint_ready']['gains']==arm['paired']['joint_ready']['losses']==1
    assert summary['one_way_replans']==summary['new_observations']==summary['new_truth_scoring_calls']==0
    assert summary['new_plans']==len(records)
    assert 'stage_condition_met' not in summary and summary['scientific_gate_changed'] is False


def test_all_snapshots_and_source_frozen_before_any_new_plan_submission(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'BASELINE',directory)
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'output')
    calls=[]
    monkeypatch.setattr(runner,'capture',lambda:calls.append('captured'))
    class Future:
        def __init__(self,life,arm,snapshots):
            self.life,self.arm,self.snapshots=life,arm,snapshots
        def result(self):
            records=[dict(**{key:s[key] for key in ('life','arm','index','identity','one_way_plan')},two_way_plan=s['one_way_plan']) for s in self.snapshots]
            return dict(life=self.life,arm=self.arm,records=records,model_seconds=0.,output_seconds=0.,
                worker_wall_seconds=0.,normalizer_cache_statistics={},work={},profiles=0)
    class Executor:
        def __init__(self,max_workers):
            assert max_workers==6
        def __enter__(self):
            return self
        def submit(self,function,life,arm,snapshots):
            assert calls[0]=='captured' and function is runner.run_life_arm
            saved=runner.read(runner.OUTPUT/'snapshots.json')
            protocol=runner.read(runner.OUTPUT/'run.json')
            assert len(saved)==len(protocol['roster'])==144
            assert protocol['phases']==['protocol_frozen','all_snapshots_frozen'] and not protocol['complete']
            assert len(snapshots)==24 and all(s['life']==life and s['arm']==arm for s in snapshots)
            calls.append((life,arm))
            return Future(life,arm,snapshots)
        def __exit__(self,*args):
            pass
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Executor)
    result=runner.run()
    assert len(calls)==7 and result['records']==result['snapshots']==result['new_plans']==144
    protocol=runner.read(runner.OUTPUT/'run.json')
    assert protocol['complete'] and protocol['combined_delta_per_fixed_view_upper']=='1/10'
    assert protocol['profile_namespaces']['ONE_WAY']=='original_V251_private_life_arm_file'
    assert protocol['profile_namespaces']['TWO_WAY']=='new_V253_private_life_arm_file'
