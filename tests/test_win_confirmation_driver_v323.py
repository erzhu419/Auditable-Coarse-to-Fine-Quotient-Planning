"""The frozen candidate restores the actual FIRST reward and saved WIN parameters."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from acfqp.science import win_confirmation_run_v323 as driver
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_closed_loop_v313 import HeadVersions, literal_choose, read_source_weights


@pytest.mark.parametrize('task',['A','B'])
def test_actual_saved_candidate_restore_and_h2_without_learning(task):
    # Treating the relative candidate as a full head or changing FIRST reward invalidates confirmation.
    previous = json.loads((ROOT/'reports/component_heads_v322/summary.json').read_text())
    source, old = previous['source_provenance']['parents'][0], previous['by_lifecycle'][0]
    initial = old['initial'][task]; version = old['cells'][task]['WIN_ONLY']['head_version']
    runtime = ROOT/'reports/win_confirmation_v323/test_logs/restore_fixture'/task
    runtime.mkdir(parents=True,exist_ok=True)
    template,_ = load_leaf(source,runtime)
    first,_ = driver._restore_first(template,initial['head_version'],runtime)
    candidate,setup = driver._restore_candidate(template,first,version,runtime)
    identity = dict(lifecycle=0,parent=0,context_id=initial['context_id'],arm='WIN_ONLY')
    reference = HeadVersions(read_source_weights(source['checkpoint']),source['checkpoint'],identity,'LOCAL_RISK')
    reference.apply(initial['head_version']); reference.apply(version)
    assert setup['restored_version'] == version and setup['delta_restore']['file'] == version['file']
    assert np.array_equal(candidate.reward_weights,first.reward_weights)
    assert np.array_equal(candidate.reward_weights.reshape(-1),reference.reward)
    assert np.array_equal(candidate.risk_weights.reshape(-1),reference.terminal)
    assert candidate.updates == first.updates == version['updates']
    assert not candidate.reward_weights.flags.writeable and not candidate.risk_weights.flags.writeable
    board = [10,9,8,7,6,5,4,3,2,1,1,2,0,2,1,0]
    actual = candidate.choose(board,initial['planning_belief']['estimated_p_four'])
    expected = literal_choose(board,reference.reward,reference.terminal,'LOCAL_RISK',initial['planning_belief']['estimated_p_four'])
    assert actual['action'] == expected['action'] and actual['afterstate'] == expected['afterstate']
    assert actual['value'] == pytest.approx(expected['value'],abs=1e-12)
    assert candidate.updates == first.updates
    assert [driver.evaluation_seed(0,task,i) for i in range(64)] == [323900000000+(100000 if task=='B' else 0)+i for i in range(64)]
