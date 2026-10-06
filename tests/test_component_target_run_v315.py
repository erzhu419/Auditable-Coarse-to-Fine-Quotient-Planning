"""A real native reconstruction/probe chain catches mixed-table driver mistakes."""
import json
from pathlib import Path

from acfqp.science import component_target_run_v315 as run


def test_real_frozen_bank_driver_uses_selected_tables_without_fitting(monkeypatch):
    root=Path(run.__file__).resolve().parents[3]
    runtime=root/'reports/component_targets_v315/runtime/tests/driver'
    prior=json.loads((root/'reports/local_targets_v314/summary.json').read_text())
    old=prior['by_lifecycle'][0]; source=prior['source_provenance']['parents'][0]
    template,_=run.load_leaf(source,runtime)
    originals={}; actual_restore=run.restore_head; calls=[]
    def restore(template,version,runtime):
        leaf,receipt=actual_restore(template,version,runtime)
        originals[version['arm']]=leaf
        return leaf,receipt
    def evaluate(leaf,p,environment,seeds,runtime,max_steps):
        arm=run.ARMS[len(calls)]; reward,win=run.COMPONENTS[arm]
        assert leaf.reward_weights is originals[reward].reward_weights
        assert leaf.risk_weights is originals[win].risk_weights
        assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
        assert p==old['initial']['A']['planning_belief']['estimated_p_four'] and environment==.1
        assert seeds==[315899000000+episode for episode in range(32)]
        calls.append(arm)
        return dict(game_summaries=[],counts=dict(environment={},planning={}),cpu_seconds=0.,seconds=0.)
    monkeypatch.setattr(run,'restore_head',restore)
    monkeypatch.setattr(run,'evaluate_split',evaluate)
    monkeypatch.setattr(run,'evaluation_seed',lambda life,task,episode:315899000000+episode)
    result=run._run_task(template,old,'A',runtime)
    assert calls==list(run.ARMS)
    assert len(result['head_restorations'])==3
    p=result['estimated_p_four']
    for arm,(reward,win) in run.COMPONENTS.items():
        state=result['component_states'][arm]
        assert state['before']==state['after']
        assert state['new_fit_states']==state['new_parameter_writes']==state['weight_copy_parameters']==0
        assert result['head_components'][arm]['reward_version']['arm']==reward
        assert result['head_components'][arm]['win_version']['arm']==win
        probe=result['action_probes'][arm][0]
        leaf=run.combine_heads(originals[reward],originals[win])
        assert probe['chosen']==leaf.choose(probe['board'],p)
        assert probe['seed']==315899000000 and probe['repeated_initial_random_draws']==4
