"""A real retained life detects wrong bootstrap/metadata/support wiring before the cohort."""
import json
import numpy as np
from acfqp.science import retention_run_v318 as runner
from acfqp.science.retention_facts_v318 import iter_a_lifecycles


def test_actual_reproduction_and_counterfactual_use_correct_frozen_heads(monkeypatch):
    root=runner.Path(runner.__file__).resolve().parents[3]
    out=root/'reports/retention_mechanism_v318/runtime/tests/driver'
    out.mkdir(parents=True,exist_ok=True)
    document=json.loads((root/'reports/greedy_targets_v317/summary.json').read_text())
    source=document['source_provenance']['parents'][0]
    template,_=runner.load_leaf(source,out)
    stream=iter_a_lifecycles(document,0)
    try:life,datasets,receipt=next(stream)
    finally:stream.close()
    calls=[]
    def fake_evaluation(*args,**kwargs):
        if len(args)==7:
            head,base,support,p,true_p,seeds,runtime=args
            assert not head.reward_weights.flags.writeable and not base.risk_weights.flags.writeable
            assert support['keys'].dtype==np.uint64 and not support['keys'].flags.writeable
            support_counts={'membership_queries':1,'base_head_queries':1,'updated_head_queries':0}
        else:
            head,p,true_p,seeds,runtime=args
            assert not head.reward_weights.flags.writeable
            support_counts={}
        assert true_p==.1
        calls.append(list(seeds))
        return dict(game_summaries=[dict(seed=int(seed),score=0,steps=0,status='LOST',utility=-4.) for seed in seeds],
            counts=dict(environment={},planning={}),support_counts=support_counts,cpu_seconds=0.,seconds=0.)
    monkeypatch.setattr(runner,'evaluate_split',fake_evaluation)
    monkeypatch.setattr(runner,'evaluate_localized',fake_evaluation)
    result=runner._run_life(template,source,life,datasets,receipt,out,out)
    assert len(calls)==4 and all(seeds==calls[0] for seeds in calls)
    assert result['reproduction']['head_exact'] and result['reproduction']['targets_exact']
    fit=result['counterfactual']['fit'];version=result['counterfactual']['head_version']
    assert fit['bootstrap_version']==result['source_versions']['FIRST']
    assert fit['current_start_version']==result['source_versions']['R1']
    assert version['base_file']==result['source_versions']['R1']['file']
    assert fit['learning_counts']==result['reproduction']['fit']['learning_counts']
    with np.load(fit['target_artifact']['file'],allow_pickle=False) as saved:
        metadata=json.loads(str(saved['metadata_json']))
    assert metadata['bootstrap_mode']=='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD'
    assert metadata['current_start_version']==result['source_versions']['R1']
    assert len(result['probe_rows'])==8
    for r in ('1','2'):
        support=result['supports'][r]
        assert support['metadata']['fit_step_end']==datasets[r]['fit_step_end']
        assert support['metadata']['source_batch']['actor_version']==life['initial']['A']['head_versions']['FIRST_LOCAL']
    saved=json.loads((out/'lifecycle_receipts'/f"life_{life['lifecycle']}.json").read_text())
    assert 'keys' not in saved['supports']['1']
    counts=runner.accounting(document,[result],[dict(cpu_seconds=2.,compiler_cpu_seconds=3.)],4.,8.)
    assert counts['new_training_raw_tiles']==0 and counts['new_evaluation_games']==128
    assert counts['new_diagnostic_cpu_seconds']==9.
