"""Exercise campaign stopping with paid synthetic blocks and hand-built graphs."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from time import perf_counter

import networkx as nx
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('coverage_runner_v63', ROOT/'scripts/run_lmta_graph_coverage_v63.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture(scope='module', autouse=True)
def accounting(request):
    started, failures = perf_counter(), request.session.testsfailed
    data = dict(mock_campaigns=0, mock_block_calls=0, hand_graph_constructions=0,
                mock_paid_action_values=0, mock_decisions=0, mock_environment_calls=0)
    yield data
    target = ROOT/'reports/lmta_graph_coverage_v63.runner_checks.json'
    report = json.loads(target.read_text()) if target.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_graph_coverage_runner_v63.py',
        new_failures=request.session.testsfailed-failures, **data,
        actual_planner_calls=0, actual_environment_calls=0, sampled_graphs=0, random_draws=0,
        wall_seconds=perf_counter()-started,
        scope='Runner campaigns use explicit tiny fixture protocols, hand graphs and paid synthetic blocks; prerequisite checks use small JSON fixtures. No main graph generator or production simulator runs.'))
    target.write_text(json.dumps(report,indent=2)+'\n')


def campaign(tmp_path, monkeypatch, accounting, scenario):
    protocol = deepcopy(runner.PROTOCOL)
    protocol.update(nodes=2, graph_ids=[-630,-629], replicates=1, budget=1, horizon=1,
                    limits=dict(max_planner_action_values=10,max_decisions=100,max_wall_seconds=10.),
                    campaign_limits=dict(max_planner_action_values=15,max_wall_seconds=50.))
    if scenario in ('wall_inside','wall_before'):
        protocol['campaign_limits']['max_wall_seconds'] = 5.
    clock, calls, generated = {'now':0.}, [], []
    monkeypatch.setattr(runner,'PROTOCOL',protocol)
    monkeypatch.setattr(runner,'SOURCES',[])
    monkeypatch.setattr(runner,'perf_counter',lambda: clock['now'])
    def collect():
        if scenario=='wall_before':
            clock['now'] += .25
        return 0
    monkeypatch.setattr(runner.gc,'collect',collect)

    def previous():
        if scenario=='wall_before':
            clock['now'] += 6.

    def generated_graph(nodes, graph_id, p):
        assert graph_id in [-630,-629] and nodes==2
        generated.append(graph_id)
        accounting['hand_graph_constructions'] += 1
        graph = nx.DiGraph()
        graph.add_nodes_from(range(nodes))
        graph.add_edge(0,1)
        return graph

    def block(graph, graph_id, method, replicates, budget, horizon, limits):
        calls.append(dict(graph_id=graph_id,method=method,limits=limits))
        reason, elapsed, actions = None, 1., 1
        if scenario=='actions':
            reason, actions = 'max_planner_action_values', limits['max_planner_action_values']+1
        elif scenario=='block_continue' and len(calls)==1:
            reason, actions = 'max_planner_action_values', limits['max_planner_action_values']
        elif scenario=='wall_inside':
            reason, elapsed = 'max_wall_seconds', limits['max_wall_seconds']+1.
        clock['now'] += elapsed
        status, env = ('resource_limit',0) if reason else ('complete',1)
        accounting['mock_block_calls'] += 1
        accounting['mock_paid_action_values'] += actions
        accounting['mock_decisions'] += 1
        accounting['mock_environment_calls'] += env
        work = dict(planner_calls=1,action_value_evaluations=actions)
        row = dict(graph_id=graph_id,method=method,replicate=0,status=status,stop_reason=reason,
            **{'return':None if reason else 1}, decisions=[dict(decision_work=work,
                next_statuses=None if reason else [2,0],reward=None if reason else 1,
                environment_work=dict(environment_calls=env))])
        case = dict(graph_id=graph_id,method=method,nodes=2,status=status,stop_reason=reason,
            requested_replicates=1,completed_replicates=env,trajectory_records=1,decision_records=1,
            decision_work=work,environment_work=dict(environment_calls=env),
            decision_seconds=elapsed,environment_seconds=0.,wall_seconds=elapsed)
        return case,[row]

    monkeypatch.setattr(runner,'require_previous',previous)
    monkeypatch.setattr(runner,'generate_graph',generated_graph)
    monkeypatch.setattr(runner,'run_block',block)
    accounting['mock_campaigns'] += 1
    output = tmp_path/'run'
    runner.run(output)
    manifest = json.loads((output/'manifest.json').read_text())
    cases = [json.loads(line) for line in (output/'cases.jsonl').read_text().splitlines()]
    rows = [json.loads(line) for line in (output/'trajectories.jsonl').read_text().splitlines()]
    assert generated==[-630,-629]
    assert [item['graph_id'] for item in manifest['graphs']]==generated
    assert manifest['new_graphs']==2 and manifest['completed_blocks']==len(calls)==len(cases)
    return manifest,cases,rows,calls


def test_global_action_remainder_charges_trigger_and_skips_suffix(tmp_path,monkeypatch,accounting):
    manifest,cases,rows,calls = campaign(tmp_path,monkeypatch,accounting,'actions')
    assert [call['limits']['max_planner_action_values'] for call in calls]==[10,4]
    assert [case['campaign_actions_before'] for case in cases]==[0,11]
    assert [case['stop_scope'] for case in cases]==['block','campaign']
    assert manifest['campaign_action_values']==16
    assert manifest['terminal_reason']=='campaign_resource_limit'
    assert manifest['campaign_stop_reason']=='max_planner_action_values'
    assert manifest['skipped_blocks']==[dict(graph_id=-629,method=m) for m in runner.METHODS[::-1]]
    assert len(rows)==2 and all(row['decisions'][0]['next_statuses'] is None for row in rows)


def test_block_limit_continues_in_balanced_method_order(tmp_path,monkeypatch,accounting):
    manifest,cases,rows,calls = campaign(tmp_path,monkeypatch,accounting,'block_continue')
    assert [(call['graph_id'],call['method']) for call in calls]==[
        (-630,runner.METHODS[0]),(-630,runner.METHODS[1]),(-629,runner.METHODS[1]),(-629,runner.METHODS[0])]
    assert manifest['status']=='complete' and manifest['terminal_reason']=='finished_roster'
    assert manifest['skipped_blocks']==[] and manifest['campaign_stop_reason'] is None
    assert manifest['campaign_elapsed_at_stop'] is None
    assert manifest['resource_limited_blocks']==1 and manifest['successful_blocks']==3
    assert manifest['campaign_action_values']==13 and manifest['completed_trajectories']==3


def test_campaign_wall_limit_is_passed_to_paid_block(tmp_path,monkeypatch,accounting):
    manifest,cases,rows,calls = campaign(tmp_path,monkeypatch,accounting,'wall_inside')
    assert len(calls)==1 and calls[0]['limits']['max_wall_seconds']==5.
    assert cases[0]['stop_scope']=='campaign' and cases[0]['campaign_elapsed_before']==0.
    assert manifest['campaign_stop_reason']=='max_wall_seconds'
    assert manifest['campaign_elapsed_at_stop']==6. and len(manifest['skipped_blocks'])==3
    assert rows[0]['decisions'][0]['environment_work']['environment_calls']==0


def test_prerequisite_wall_time_can_stop_before_any_block(tmp_path,monkeypatch,accounting):
    manifest,cases,rows,calls = campaign(tmp_path,monkeypatch,accounting,'wall_before')
    assert calls==cases==rows==[]
    assert manifest['source_read_seconds']==6. and manifest['campaign_elapsed_at_stop']==6.25
    assert manifest['unexecuted_prepare_gc_seconds']==.25
    assert manifest['campaign_stop_reason']=='max_wall_seconds' and len(manifest['skipped_blocks'])==4
    assert manifest['campaign_action_values']==0


def test_previous_incomplete_dense_panels_do_not_reject_completed_sparse_panel(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'FROZEN',{})
    previous = tmp_path/runner.PREVIOUS
    calibration = tmp_path/runner.CALIBRATION
    previous.mkdir(parents=True)
    calibration.mkdir(parents=True)
    (previous/'manifest.json').write_text(json.dumps(dict(status='complete')))
    analysis = dict(integrity=dict(passed=True),complete_trajectory_evidence=False,
        panels=[dict(nodes=15,stratum='sparse',complete_quality_evidence=True),
                dict(nodes=15,stratum='dense',complete_quality_evidence=False)])
    (previous/'analysis.json').write_text(json.dumps(analysis))
    (calibration/'analysis.json').write_text(json.dumps(dict(integrity=dict(passed=True),
        complete_trajectory_evidence=True,calibration_consistent=True)))
    runner.require_previous()
    analysis['panels'][0]['complete_quality_evidence'] = False
    (previous/'analysis.json').write_text(json.dumps(analysis))
    with pytest.raises(AssertionError,match='sparse-15'):
        runner.require_previous()
