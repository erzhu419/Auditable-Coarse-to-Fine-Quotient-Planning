"""Actual FIRST heads and V319 root members complete a two-position wired diagnostic."""
import json
from pathlib import Path

import numpy as np

from acfqp.science import teacher_calibration_run_v320 as run
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]


def test_actual_first_source_groups_terminal_return_serialization_and_cost(monkeypatch):
    # Wrong retained starts, action order, paired seeds, raw accounting or serialization would block acquisition.
    out = ROOT/'reports/teacher_calibration_v320/test_logs/driver_fixture'
    runtime = out/'runtime'; runtime.mkdir(parents=True,exist_ok=True)
    previous = json.loads((ROOT/'reports/query_supervision_v319/summary.json').read_text())
    source = previous['source_provenance']['parents'][0]
    template, _ = load_leaf(source,runtime)
    monkeypatch.setattr(run,'GROUPS',2)
    row = run._run_life(template,source,previous['by_lifecycle'][0],runtime,out)
    assert json.loads((out/'lifecycle_receipts/life_0.json').read_text()) == row
    total = 0
    for number in ('1','2'):
        for task in run.TASKS:
            stage = row['stages'][number][task]
            assert stage['teacher_unchanged']
            assert stage['teacher_version'] == previous['by_lifecycle'][0]['initial'][task]['head_version']
            assert stage['selected_group_indices'] == [0,16383]
            paired = []
            for arm in run.ARMS:
                cell = stage['arms'][arm]
                with np.load(cell['source_group_artifact']['file'],allow_pickle=False) as original:
                    expected_targets = original['targetreward'][[0,16383]]
                    expected_wins = original['targetwin'][[0,16383]]
                with np.load(cell['outcome_artifact']['file'],allow_pickle=False) as saved:
                    assert saved['scores'].shape == (2,4) and np.all(saved['status']!=0)
                    assert np.array_equal(saved['original_group_indices'],[0,16383])
                    assert np.array_equal(saved['actions'],saved['new_raw_tiles'])
                    assert np.array_equal(saved['reward_return'],saved['scores']/2048.)
                    assert np.array_equal(saved['win'],saved['status']==1)
                    paired.append(saved['rollout_seeds'].copy())
                    total += int(saved['new_raw_tiles'].sum())
                    for i,group in enumerate(cell['groups']):
                        assert group['index'] == [0,16383][i]
                        for member,rep in enumerate(group['replicas']):
                            assert rep['teacher_reward'] == expected_targets[i,member]
                            assert rep['teacher_win'] == expected_wins[i,member]
                            assert rep['actual_reward'] == saved['scores'][i,member]/2048.
                            assert rep['actual_win'] == int(saved['status'][i,member]==1)
                            assert rep['seed'] == run.rollout_seed(0,task,int(number),group['index'],member)
                receipt = cell['continuation']['trace_artifact']
                with np.load(receipt['file'],allow_pickle=False) as trace:
                    assert len(trace['moves']) == sum(rep['new_raw_tiles'] for group in cell['groups'] for rep in group['replicas'])
                assert cell['continuation']['teacher_updates'] == stage['teacher_version']['updates']
            assert np.array_equal(*paired)
    costs = run.accounting(previous,[row],[dict(cpu_seconds=1.,compiler_cpu_seconds=0.)],0.,1.,3012.968096468)
    assert costs['rollouts'] == costs['reused_first_spawns'] == 64
    assert costs['new_raw_tiles'] == total and costs['fit_updates'] == 0
    assert all(p['trace_files']==p['outcome_files']==4 for p in costs['per_arm'].values())
    json.dumps(costs,allow_nan=False)
