"""A real out-of-cohort chain catches private target/version and budget mistakes."""
import gzip
import json
import numpy as np

from acfqp.science import local_target_run_v314 as run
from acfqp.science.native_value_stream_v286 import NativeValueStream
from acfqp.science.natural_model_revision_v281 import load_leaf


def test_real_fixed_actor_local_targets_and_cost_closure(monkeypatch):
    root=run.Path(run.__file__).resolve().parents[3]
    out=root/'reports/local_targets_v314/runtime/tests/driver_life20'
    out.mkdir(parents=True,exist_ok=True)
    document=json.loads((root/'reports/fresh_source_v312/source_summary.json').read_text())
    source=document['source_provenance']['parents'][0]
    monkeypatch.setattr(run,'LIVES',1)
    monkeypatch.setattr(run,'INITIAL_RAW',8192)
    monkeypatch.setattr(run,'ROUND_RAW',8192)
    calls=[]
    def static_probe(leaf,life,task,belief,runtime,engine,version=None):
        assert not leaf.weights.flags.writeable
        if version is not None:
            assert version['updates']==leaf.updates
            assert not leaf.risk_weights.flags.writeable
            if version['version']==0:
                with np.load(version['file']) as z:
                    idx=z['reward_indices']; assert np.array_equal(leaf.reward_weights.reshape(-1)[idx],z['reward_values'])
                    idx=z['terminal_indices']; assert np.array_equal(leaf.risk_weights.reshape(-1)[idx],z['terminal_values'])
        calls.append((task,None if version is None else version['arm']))
        return dict(game_summaries=[dict(seed=run.evaluation_seed(life,task,e),score=0,steps=0,
            status='LOST',utility=-4.) for e in range(32)],estimated_p_four=belief['estimated_p_four'],
            head_version=version,counts=dict(environment={},planning={}),cpu_seconds=0.,seconds=0.)
    monkeypatch.setattr(run,'_evaluate',static_probe)
    template,_=load_leaf(source,out); engine=NativeValueStream(template,314899999999,out)
    try:
        with gzip.open(out/'trace.jsonl.gz','wt') as stream:
            life=run._run_lifecycle(template,source,20,out,out,engine,lambda row:stream.write(json.dumps(row)+'\n'))
    finally:
        engine.close()
    assert life['initial_context_precondition_met'] and len(calls)==12
    for task in run.TASKS:
        first=life['initial'][task]['head_versions']['FIRST_LOCAL']
        for r in ('1','2'):
            batch=life['rounds'][r][task]
            assert list(batch['collectors'])==['FIXED_FIRST']
            assert batch['collectors']['FIXED_FIRST']['actor_version']==first
            assert batch['inactive_head_versions_before']==batch['inactive_head_versions_after']
            mc,td=batch['arms']['MC_LOCAL'],batch['arms']['TD_LOCAL']
            assert mc['fit']['trained_afterstates']==td['fit']['trained_afterstates']==batch['quota']
            assert mc['fit']['learning_counts']['table_updates']==td['fit']['learning_counts']['table_updates']
            expected=first if r=='1' else life['rounds']['1'][task]['arms']['TD_LOCAL']['head_version']
            assert td['fit']['bootstrap_version']==expected
            assert td['fit']['frozen_batch_start_bootstrap']
            artifact=td['fit']['target_artifact']
            with np.load(artifact['file']) as z:
                assert z['targetkind'].shape==(td['fit']['fitted_steps'],)
                assert np.count_nonzero(z['targetkind'])==batch['quota']
                metadata=json.loads(str(z['metadata_json']))
                assert metadata['bootstrap_version']==expected
            assert td['head_version']['base_file']==expected['file']
    account=run.build_accounting(document['accounting']['inherited_costs_per_arm']['SOURCE'],[life],
        [dict(cpu_seconds=3.,compiler_cpu_seconds=2.,trace_bytes=1)],5.,8.)
    assert account['post_raw_tiles']==4*8192 and account['post_physical_acquisitions']==4
    assert account['target_files']==4 and account['version_files']==10
    assert account['new_evaluation_games']==384
    assert account['new_target_cpu_seconds']==10.
    assert account['economic_source_and_target_cpu_seconds']==10.+document['accounting']['inherited_costs_per_arm']['SOURCE']['fresh_source_compute']['full_source_cpu_seconds']
    assert account['economic_training_raw_tiles_per_arm']['TD_LOCAL']-account['economic_training_raw_tiles_per_arm']['FIRST_LOCAL']==4*8192
    assert not account['source_physical_training_repeated']
