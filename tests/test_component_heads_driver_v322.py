"""Actual saved FIRST/final tables bind the two diagnostic H2 policies."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from acfqp.science import component_heads_run_v322 as driver
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_closed_loop_v313 import HeadVersions, literal_choose, read_source_weights


@pytest.mark.parametrize('task',['A','B'])
def test_saved_full_components_and_actual_h2_choice(task):
    # A missed v1 write, swapped component or wrong H2 table binding invalidates attribution.
    previous = json.loads((ROOT/'reports/reward_targets_v321/summary.json').read_text())
    source, old = previous['source_provenance']['parents'][0], previous['by_lifecycle'][0]
    initial = old['initial'][task]
    chain = [initial['head_version']]+[old['rounds'][str(n)][task]['arms']['NSTEP_QUERY']['head_version'] for n in (1,2)]
    out = ROOT/'reports/component_heads_v322/test_logs/assembly_fixture'/task
    runtime = out/'runtime'; runtime.mkdir(parents=True,exist_ok=True)
    template,_ = load_leaf(source,runtime)
    first,_ = driver._restore_first(template,chain[0],runtime)
    final,_ = driver._restore_final(template,first,chain,runtime)
    identity = dict(lifecycle=0,parent=0,context_id=initial['context_id'],arm='NSTEP_QUERY')
    reference = HeadVersions(read_source_weights(source['checkpoint']),source['checkpoint'],identity,'LOCAL_RISK')
    reference.apply(chain[0]); first_reward = reference.reward.copy(); first_win = reference.terminal.copy()
    for version in chain[1:]: reference.apply(version)
    assert np.array_equal(first.reward_weights.reshape(-1),first_reward)
    assert np.array_equal(first.risk_weights.reshape(-1),first_win)
    assert np.array_equal(final.reward_weights.reshape(-1),reference.reward)
    assert np.array_equal(final.risk_weights.reshape(-1),reference.terminal)
    board = [10,9,8,7,6,5,4,3,2,1,1,2,0,2,1,0]
    for arm in driver.NEW_ARMS:
        leaf,_,version,assembly = driver._assemble(template,first,final,chain,source,0,
            initial['context_id'],arm,runtime,out/'models')
        reward = reference.reward if arm=='REWARD_ONLY' else first_reward
        win = first_win if arm=='REWARD_ONLY' else reference.terminal
        assert np.array_equal(leaf.reward_weights.reshape(-1),reward)
        assert np.array_equal(leaf.risk_weights.reshape(-1),win)
        assert leaf.updates == first.updates and assembly['new_fit_updates'] == 0
        assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
        assert version['base_file'] == chain[0]['file'] and version['version'] == 1
        with np.load(version['file'],allow_pickle=False) as saved:
            untouched = 'terminal' if arm=='REWARD_ONLY' else 'reward'
            assert saved[untouched+'_indices'].size == saved[untouched+'_values'].size == 0
        actual = leaf.choose(board,initial['planning_belief']['estimated_p_four'])
        expected = literal_choose(board,reward,win,'LOCAL_RISK',initial['planning_belief']['estimated_p_four'])
        assert actual['action'] == expected['action'] and actual['afterstate'] == expected['afterstate']
        assert actual['value'] == pytest.approx(expected['value'],abs=1e-12)
        assert leaf.updates == first.updates
