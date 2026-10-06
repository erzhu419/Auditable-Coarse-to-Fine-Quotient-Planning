"""Finite fragment-output, novelty and frozen continuation fixtures."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_guarded_fragments_v138 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_guarded_fragments_v138.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,tests_run=len(request.session.items),
        environment_samples=0,model_samples=0,model_updates=0,
        scope='finite deterministic fragment outputs, exact novelty, coverage weighting and continuation root values'))
    path.write_text(json.dumps(record,indent=2)+'\n')


def test_postspawn_exit_and_perstep_reward_are_both_required():
    outcome,work = analysis.ground_outcome([1,1]+[0]*14,['LEFT','DOWN'],[dict(cell=1,rank=1),dict(cell=0,rank=1)])
    assert outcome == dict(exit_board=[1]+[0]*11+[2,1,0,0],scores=[4,0],cumulative_score=4,status='ACTIVE',duration=2)
    assert work['analysis_replay_swipes'] == 2
    result = analysis.prediction_metrics(outcome,outcome,True)
    assert result['correct'] == result['novel_correct'] == 1
    broken = deepcopy(outcome); broken['exit_board'][0] = 0
    assert analysis.prediction_metrics(broken,outcome,True)['wrong'] == 1
    broken = deepcopy(outcome); broken['scores'] = [0,4]
    assert analysis.prediction_metrics(broken,outcome,True)['rewards_correct'] == 0


def test_winning_fragment_retains_actual_winning_spawn():
    root = [10,9,9,0]+[0]*12
    outcome,_ = analysis.ground_outcome(root,['RIGHT','RIGHT'],[dict(cell=0,rank=1),dict(cell=0,rank=1)])
    assert outcome == dict(exit_board=[1,0,1,11]+[0]*12,scores=[1024,2048],cumulative_score=3072,status='WON',duration=2)


def test_numeric_novelty_includes_actions_and_all_spawn_values():
    root = [1,1]+[0]*14; actions = ['LEFT','DOWN']; spawns = [dict(cell=1,rank=1),dict(cell=0,rank=1)]
    key = analysis.numeric_binding(root,actions,spawns)
    assert key == analysis.numeric_binding(list(root),list(actions),deepcopy(spawns))
    changed = deepcopy(spawns); changed[1]['rank'] = 2
    assert key != analysis.numeric_binding(root,actions,changed)
    assert key != analysis.numeric_binding(root,['RIGHT','DOWN'],spawns)
    changed_root = list(root); changed_root[0] = 2
    assert key != analysis.numeric_binding(changed_root,actions,spawns)


def test_misses_remain_in_denominator_and_wrong_hits_are_not_reuse():
    truth,_ = analysis.ground_outcome([1,1]+[0]*14,['LEFT','DOWN'],[dict(cell=1,rank=1),dict(cell=0,rank=1)])
    hit = analysis.prediction_metrics(truth,truth,True)
    miss = analysis.prediction_metrics(None,truth,True)
    totals = {key:hit[key]+miss[key] for key in hit}
    assert analysis.coverage(totals)['novel_exact_coverage'] == .5
    assert analysis.coverage(totals)['hit_accuracy'] == 1.
    wrong = dict(truth,cumulative_score=5)
    assert analysis.prediction_metrics(wrong,truth,True)['novel_correct'] == 0


def test_coverage_weights_each_game_and_history_equally():
    games=[]
    for life in analysis.LIVES:
        for replica in range(analysis.REPLICAS):
            n = 100 if replica == 0 else 1; hits = n if replica == 0 else 0
            counts=dict(windows=n,hits=hits,correct=hits,novel_windows=n,novel_hits=hits,novel_correct=hits)
            games.append(dict(life=life,replica=replica,methods={'MODULE_64':counts}))
    result=analysis.coverage_summary(games,['MODULE_64'])
    assert result['complete']
    assert result['cells'][0]['mean_history']['exact_coverage'] == 1/16
    assert result['cells'][0]['pooled']['exact_coverage'] == 100/115


def test_continuation_compares_every_legal_root_value_not_only_choice():
    value=dict(status='ACTIVE',action='LEFT',action_values={'LEFT':dict(value=2.),'RIGHT':dict(value=1.)})
    assert analysis.continuation_equal(value,deepcopy(value),'ACTIVE')
    broken=deepcopy(value); broken['action_values']['RIGHT']['value'] += .01
    assert not analysis.continuation_equal(value,broken,'ACTIVE')
    assert analysis.continuation_equal(dict(status='WON'),dict(status='WON'),'WON')
    assert not analysis.continuation_equal(dict(status='LOST'),dict(status='WON'),'WON')


def test_snapshot_footprint_is_read_from_persistent_programs():
    fragment=dict(zero_mask=3,actions=['LEFT','DOWN'],spawn_cells=[1,0],guards=[['EQ',[0,0],[1,0],True]],
        exit_expressions=[[0,1]]+[None]*15,reward_expressions_by_step=[[[0,1]],[]],
        anchor_binding=[1,1]+[0]*14+[1,2],instruction_footprint=[['guard_predicates',1],['exit_cell_assignments',16],['reward_terms',1]])
    payload=dict(kind='guarded',fragments=[fragment])
    summary=analysis.snapshot_summary(payload)
    assert summary['num_programs'] == summary['total_guards'] == summary['total_exit_expressions'] == 1
    assert summary['total_instructions'] == 18
    assert analysis.snapshot_bindings(payload) == {analysis.numeric_binding([1,1]+[0]*14,['LEFT','DOWN'],[dict(cell=1,rank=1),dict(cell=0,rank=2)])}
