"""Finite local-composition and matched-coverage accounting fixtures."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from scripts import analyze_controlled_predictive_factored_fragments_v139 as analysis

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    path=ROOT/'reports/controlled_predictive_factored_fragments_v139.analysis_checks.json'
    record=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,tests_run=len(request.session.items),
        environment_samples=0,model_samples=0,model_updates=0,
        scope='finite prefix novelty, fixed local footprint, runtime fitting exclusion and paired coverage'))
    path.write_text(json.dumps(record,indent=2)+'\n')


def test_local_program_footprint_counts_four_cells_instead_of_whole_board():
    program=dict(zero_mask=12,guards=[['EQ',[0,0],[1,0],True]],output_expressions=[[0,1],None,None,None],
        reward_expressions=[[0,1]],anchor_binding=[1,1,0,0])
    summary=analysis.factored_summary(dict(programs=[program],composition_footprint=[['fixed_composition',33]]))
    assert summary['num_programs']==summary['num_buckets']==1
    assert summary['total_exit_cell_slots']==summary['total_anchor_rank_copies']==4
    assert summary['total_guards']==summary['total_reward_expressions']==1
    assert summary['local_program_instructions']==6 and summary['total_instructions']==39


def test_lookup_classification_work_is_allowed_but_compilation_is_not():
    work=dict(lookup_calls=1,hits=1,exit_status_learned_swipe_calls=4)
    assert analysis.no_fit_during_lookup(work)
    for key in ('observations','compiled_programs','compile_symbolic_swipes','observation_validation_swipes','fallback_calls'):
        broken=dict(work,**{key:1})
        assert not analysis.no_fit_during_lookup(broken)


def test_spawn_rank_and_position_are_part_of_full_numeric_novelty():
    root=[1,1]+[0]*14; actions=['LEFT','DOWN']; spawns=[dict(cell=1,rank=1),dict(cell=0,rank=1)]
    binding=analysis.numeric_binding(root,actions,spawns)
    changed=deepcopy(spawns); changed[1]['rank']=2
    assert binding!=analysis.numeric_binding(root,actions,changed)
    changed=deepcopy(spawns); changed[1]['cell']=2
    assert binding!=analysis.numeric_binding(root,actions,changed)


def test_factorized_hits_only_count_if_full_exit_and_perstep_scores_match():
    truth=dict(exit_board=[1]+[0]*11+[2,1,0,0],scores=[4,0],cumulative_score=4,status='ACTIVE',duration=2)
    broken=dict(truth,scores=[0,4])
    assert analysis.prediction_metrics(broken,truth,True)['novel_correct']==0
    assert analysis.prediction_metrics(None,truth,True)['misses']==1


def test_same_prefix_coverage_contrasts_use_equal_history_weights():
    games=[]
    for life in analysis.LIVES:
        for replica in range(analysis.REPLICAS):
            row=dict(life=life,replica=replica,methods={})
            for method in analysis.METHODS:
                hits=life+1 if method.startswith('FACTORED') else 0
                row['methods'][method]=dict(windows=10,hits=hits,correct=hits,novel_windows=10,novel_hits=hits,novel_correct=hits)
            games.append(row)
    result=analysis.compare_coverage(games)
    assert result['complete'] and len(result['comparisons'])==6
    assert all(row['mean']==.25 for row in result['comparisons'])


def test_continuation_equality_detects_wrong_unselected_action_value():
    choice=dict(status='ACTIVE',action='LEFT',action_values={'LEFT':dict(value=2.),'RIGHT':dict(value=1.)})
    broken=deepcopy(choice); broken['action_values']['RIGHT']['value']=.9
    assert not analysis.continuation_equal(choice,broken,'ACTIVE')


def test_component_ids_and_eight_local_outputs_reconcile_with_runtime_work():
    work=dict(line_hits=8,line_lookup_calls=8,composition_line_gathers=8,composition_line_scatters=8,
        line_bind_calls=8,line_bound_output_cells=32,composition_board_writes=34,composition_spawn_patches=2,
        composition_action_passes=2,composition_score_additions=8,composition_cumulative_score_additions=1)
    probe=dict(hit=True,components=[0]*8,work=work)
    assert all(analysis.component_checks(probe,1).values())
    broken=deepcopy(probe); broken['components'][-1]=1
    assert not analysis.component_checks(broken,1)['local_component_ids']
    broken=deepcopy(probe); broken['work']['composition_spawn_patches']=1
    assert not analysis.component_checks(broken,1)['composition_accounting']


def test_source_window_local_anchors_include_both_oriented_action_inputs():
    window=dict(root=[1,1]+[0]*14,actions=['LEFT','DOWN'],spawns=[dict(cell=1,rank=1),dict(cell=0,rank=1)])
    lines,outcome,work=analysis.observed_lines_and_outcome(window)
    assert (1,1,0,0) in lines and (0,0,0,2) in lines and (0,0,0,1) in lines
    assert outcome['exit_board']==[1]+[0]*11+[2,1,0,0] and outcome['scores']==[4,0]
    assert work['analysis_replay_swipes']==2
