"""Own-prefix roster, unchanged fees, and global bound-before-truth barrier."""
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
import pytest

from scripts import run_coupled_impossibility_v257 as runner


def fixture_baseline(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'BASELINE',tmp_path/'reports/trajectory_lifecycle_v256')
    monkeypatch.setattr(runner,'OUTPUT',tmp_path/'reports/coupled_impossibility_v257')
    monkeypatch.setattr(runner,'LIVES',(0,))
    monkeypatch.setattr(runner,'TARGETS',(30,31))
    monkeypatch.setattr(runner,'EXPECTED_SNAPSHOTS',8)
    monkeypatch.setattr(runner,'EXPECTED_PRIMARY',1)
    runner.save(runner.BASELINE/'run.json',dict(complete=True))
    runner.save(runner.BASELINE/'analysis.json',dict(valid=True))
    originals = {}
    for arm in runner.ARMS:
        rows = []
        for index in runner.TARGETS:
            case = dict(context='B',stage='B',operating='low',retry_cost='17/20',id=f'case{index}')
            initial = dict(case=case,goal_upper='3',query_ready=True,goal_impossible=False,
                evidence_counts=dict(own_prefix=index),joint_constraints=dict(original_event=index))
            terminal = dict(initial,evidence_counts=dict(own_prefix=index,member=16))
            rows.append(dict(index=index,identity=index-30,case=case,initial_plan=initial,
                batches=[dict(spent=16,operator='SHORT_PASS',increments=dict(DELIVERY=16,LOST=0),plan=terminal)],
                terminal_plan=terminal,spent=16,member=dict(S=dict(DELIVERY=16)),
                query_certified=True,execution_certified=index==31,execution_resolved=index==31,
                goal_impossible=False,joint_completed=index==31,budget_terminal=dict(paid=index),budget_after=dict(paid=index+1)))
        originals[arm] = deepcopy(rows)
        with gzip.open(runner.BASELINE/f'records_life_00_{arm}.jsonl.gz','wt') as stream:
            for row in rows:
                runner.write_row(stream,row)
        runner.save(runner.BASELINE/f'worker_artifacts_life_00_{arm}.json',dict(fees=dict(source=4608,shared=100,member=32,execution=2)))
    return originals


def result_for(record):
    return dict(snapshot_id=record['snapshot_id'],false_old_upper=False,false_new_upper=False,false_impossible_certificate=False)


def bound_for(upper=F(23,10)):
    return dict(old_goal_upper=F(3),upper=upper,reduction=3-upper,old_impossible=False,new_impossible=upper<2)


def test_complete_own_prefix_roster_primary_observables_full_history_and_fees(tmp_path,monkeypatch):
    originals = fixture_baseline(tmp_path,monkeypatch)
    monkeypatch.setattr(runner.task,'world',lambda *args:pytest.fail('truth cannot select snapshots'))
    snapshots,terminals,primary,fees = runner.collect_snapshots()
    assert len(snapshots)==8 and len(terminals)==4 and len(primary)==1
    assert [row['snapshot_ids'] for row in terminals]==[[0,1],[2,3],[4,5],[6,7]]
    assert primary[0]['index']==30 and primary[0]['snapshot_ids']==[0,1]
    assert primary[0]['retained_record']==originals[runner.ARMS[0]][0]
    assert [row['prefix_position'] for row in snapshots]==[0,1]*4
    assert [row['is_terminal'] for row in snapshots]==[False,True]*4
    assert snapshots[0]['plan']['evidence_counts']==dict(own_prefix=30)
    assert snapshots[1]['plan']['evidence_counts']==dict(own_prefix=30,member=16)
    assert all(row['total_samples']==4742 for row in fees)
    assert all(row['fees']==dict(source=4608,shared=100,member=32,execution=2) for row in fees)
    snapshots[0]['plan']['evidence_counts']['own_prefix'] = -1
    assert originals[runner.ARMS[0]][0]['initial_plan']['evidence_counts']['own_prefix']==30
    assert primary[0]['retained_record']['initial_plan']['evidence_counts']['own_prefix']==30


@pytest.mark.parametrize('failure',['incomplete_roster','terminal_not_last_prefix'])
def test_invalid_settled_roster_stops_before_bounds(tmp_path,monkeypatch,failure):
    fixture_baseline(tmp_path,monkeypatch)
    path = runner.BASELINE/f'records_life_00_{runner.ARMS[0]}.jsonl.gz'
    records = list(runner.rows(path))
    if failure=='incomplete_roster':
        records.pop()
    else:
        records[0]['terminal_plan']['goal_upper'] = '99'
    with gzip.open(path,'wt') as stream:
        for row in records:
            runner.write_row(stream,row)
    with pytest.raises(ValueError,match='chronological|terminal'):
        runner.collect_snapshots()


def test_earliest_certificate_reports_observed_history_not_counterfactual_savings(tmp_path,monkeypatch):
    fixture_baseline(tmp_path,monkeypatch)
    snapshots,terminals,primary,fees = runner.collect_snapshots()
    records = [dict(row,bound=bound_for(F(19,10) if row['snapshot_id']==1 else F(23,10))) for row in snapshots]
    results = [result_for(row) for row in records]
    summary = runner.summarize(records,results,terminals,primary,fees,[])
    first = summary['primary_histories'][0]['earliest_newly_certified_prefix']
    assert first==dict(snapshot_id=1,prefix_position=1,spent=16,upper=F(19,10))
    assert summary['primary']['newly_impossible']==1 and summary['method_condition_met']
    assert summary['retained_fee_ledger']==fees
    assert summary['new_environment_observations']==0 and not summary['lifecycle_cost_savings_measured']
    assert not summary['scientific_gate_changed'] and not summary['u006_started']


def test_false_impossibility_is_detected_at_true_optimum_equal_two(monkeypatch):
    monkeypatch.setattr(runner,'oracle_goal',lambda case,law:F(2))
    record = dict(snapshot_id=0,life=0,arm=runner.ARMS[0],index=30,identity=0,prefix_position=0,is_terminal=True,
        case={},bound=bound_for(F(1999,1000)))
    result = runner.score(record,{})
    assert result['false_new_upper'] and result['false_impossible_certificate'] and not result['truly_impossible']
    record['bound'] = bound_for(F(2))
    boundary = runner.score(record,{})
    assert not boundary['false_new_upper'] and not boundary['false_impossible_certificate']


def test_all_workers_and_disk_bounds_finish_before_any_world_or_score(tmp_path,monkeypatch):
    fixture_baseline(tmp_path,monkeypatch)
    state = dict(captured=False,completed=0,closed=False,scored=0)
    monkeypatch.setattr(runner,'capture',lambda:state.update(captured=True))
    class Future:
        def __init__(self,life,arm,snapshots):
            self.args = life,arm,snapshots
        def result(self):
            life,arm,snapshots = self.args
            assert state['captured'] and not state['scored']
            assert len(list(runner.rows(runner.OUTPUT/'snapshots.jsonl.gz')))==8
            with gzip.open(runner.filename('records',life,arm),'wt') as stream:
                for snapshot in snapshots:
                    runner.write_row(stream,dict(snapshot,bound=bound_for(),model_seconds=F(0)))
            state['completed'] += 1
            return dict(life=life,arm=arm,model_seconds=0.,output_seconds=0.,worker_wall_seconds=0.,work={},normalizer_cache_statistics={})
    class Executor:
        def __init__(self,max_workers):
            assert max_workers==6
        def __enter__(self):
            return self
        def submit(self,function,life,arm,snapshots):
            assert function is runner.run_life_arm
            return Future(life,arm,snapshots)
        def __exit__(self,*args):
            state['closed'] = True
    def world(life):
        assert state['completed']==2 and state['closed'] and not state['scored']
        assert runner.read(runner.OUTPUT/'run.json')['phases'][-1]=='all_bounds_frozen'
        assert sum(len(list(runner.rows(runner.filename('records',0,arm)))) for arm in runner.ARMS)==8
        return None,[{}]*78
    def score(record,law):
        assert state['completed']==2 and state['closed']
        state['scored'] += 1
        return result_for(record)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Executor)
    monkeypatch.setattr(runner.task,'world',world)
    monkeypatch.setattr(runner,'score',score)
    summary = runner.run()
    assert state['scored']==8 and summary['records']==8 and summary['terminal_records']==4
    assert not summary['conditions']['all_primary_terminal_impossibilities']
    assert runner.read(runner.OUTPUT/'run.json')['complete']
    assert summary['retained_fee_ledger'][0]['total_samples']==4742
