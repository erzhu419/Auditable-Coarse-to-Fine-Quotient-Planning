"""One real out-of-cohort lifecycle tests the driver/version/budget integration."""
import gzip
import json
from pathlib import Path

import numpy as np

from acfqp.science import closed_loop_run_v313 as run
from acfqp.science.closed_loop_versions_v313 import terminal_weights
from acfqp.science.native_value_stream_v286 import NativeValueStream
from acfqp.science.natural_model_revision_v281 import load_leaf


def test_real_closed_loop_collectors_use_previous_private_heads_and_close_costs(monkeypatch):
    root=Path(run.__file__).resolve().parents[3]
    out=root/'reports/closed_loop_v313/runtime/tests/driver_life20'
    out.mkdir(parents=True,exist_ok=True)
    source_summary=json.loads((root/'reports/fresh_source_v312/source_summary.json').read_text())
    source=source_summary['source_provenance']['parents'][0]
    monkeypatch.setattr(run,'INITIAL_RAW',8192)
    monkeypatch.setattr(run,'ROUND_RAW',8192)
    monkeypatch.setattr(run,'LIVES',1)
    calls=[]

    def static_probe(leaf,life,task,belief,runtime,engine,version=None,direct=False):
        assert not leaf.weights.flags.writeable
        if version is not None:
            assert version['updates']==leaf.updates and version['head_kind']==leaf.kind
            assert not terminal_weights(leaf).flags.writeable
            with np.load(version['file']) as z:
                # Original frozen heads remain their saved real parameters at final DIRECT.
                if version['version']==0:
                    idx=z['reward_indices'][:32]; assert np.array_equal(leaf.reward_weights.reshape(-1)[idx],z['reward_values'][:32])
                    idx=z['terminal_indices'][:32]; assert np.array_equal(terminal_weights(leaf).reshape(-1)[idx],z['terminal_values'][:32])
        calls.append((task,None if version is None else version['arm'],direct))
        return dict(game_summaries=[dict(seed=run.evaluation_seed(life,task,e),score=0,steps=0,
            status='LOST',utility=-4.) for e in range(32)],estimated_p_four=belief['estimated_p_four'],
            head_version=version,counts=dict(environment={},planning={}),cpu_seconds=0.,seconds=0.)

    monkeypatch.setattr(run,'_evaluate',static_probe)
    template,_=load_leaf(source,out)
    engine=NativeValueStream(template,313899999999,out)
    try:
        with gzip.open(out/'trace.jsonl.gz','wt') as stream:
            row=run._run_lifecycle(template,source,20,out,out,engine,
                lambda x:stream.write(json.dumps(x)+'\n'))
    finally:
        engine.close()
    assert row['initial_context_precondition_met']
    assert len(calls)==26
    for task in run.TASKS:
        first=row['initial'][task]['head_versions']['FIRST_LOCAL']
        one=row['rounds']['1'][task]; two=row['rounds']['2'][task]
        assert one['collectors']['SHARED_LOCAL']['actor_version']==first
        assert two['collectors']['FIXED_LOCAL']['actor_version']==first
        assert two['collectors']['CLOSED_LOCAL']['actor_version']==one['arms']['CLOSED_LOCAL']['head_version']
        assert two['collectors']['CLOSED_LINEAR']['actor_version']==one['arms']['CLOSED_LINEAR']['head_version']
        assert one['arms']['CLOSED_LOCAL']['head_version']['file']!=one['arms']['FIXED_LOCAL']['head_version']['file']
        for r in (one,two):
            assert all(v['fit']['trained_afterstates']==r['quota'] for v in r['arms'].values())
            assert r['inactive_head_versions_before']==r['inactive_head_versions_after']
            assert all(v['head_version']['changed_parameters']>0 for v in r['arms'].values())
    cost=source_summary['accounting']['inherited_costs_per_arm']['SOURCE']
    a=run.build_accounting(cost,[row],[dict(cpu_seconds=3.,compiler_cpu_seconds=2.,trace_bytes=1)],5.,8.)
    assert a['post_raw_tiles']==10*8192
    assert a['post_physical_acquisitions']==10 and a['new_evaluation_games']==832
    assert len(set(a['fit_states_per_updating_arm'].values()))==1
    assert a['new_target_cpu_seconds']==10.
    assert a['economic_source_and_target_cpu_seconds']==cost['fresh_source_compute']['full_source_cpu_seconds']+10.
    assert a['economic_training_raw_tiles_per_arm']['CLOSED_LOCAL']-a['economic_training_raw_tiles_per_arm']['FIRST_LOCAL']==4*8192
    assert not a['source_physical_training_repeated']


def test_domain_precondition_retains_partial_raw_and_worker_hold(monkeypatch,tmp_path):
    monkeypatch.setattr(run,'LIVES',1)
    monkeypatch.setattr(run,'load_leaf',lambda *args:(object(),{}))
    class Engine:
        def __init__(self,*args):pass
        def close(self):pass
    monkeypatch.setattr(run,'NativeValueStream',Engine)
    def blocked(template,source,life,runtime,output,engine,emit):
        emit(dict(kind='WARMUP',raw_spawns=[{},{}]))
        emit(dict(kind='CONTEXT_PRECONDITION_FAILED',lifecycle=life))
        raise ValueError('distinct confirmed initial bank is unavailable')
    monkeypatch.setattr(run,'_run_lifecycle',blocked)
    p=run._run_parent(dict(parent=0),tmp_path)
    assert p['status']=='COHORT_HOLD' and p['lifecycles']==[]
    assert p['paid_raw_tiles']==2 and p['canonical_rows']==3
    assert p['failure']['lifecycle']==0
    assert p['failure']['reason']=='INITIAL_BANK_PRECONDITION_NOT_MET'
    assert p['cpu_seconds']>=0 and p['compiler_cpu_seconds']>=0
    with gzip.open(p['trace_file'],'rt') as trace:
        assert json.loads(trace.readlines()[-1])['kind']=='COHORT_HOLD'
