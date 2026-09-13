"""Fresh small-policy certificates and provenance assembly; no target main run."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('changed_policy_analysis_v60', ROOT/'scripts/analyze_lmta_changed_policy_v60.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


@pytest.fixture(scope='session', autouse=True)
def development_work():
    patch, work = pytest.MonkeyPatch(), Counter()
    original_plan, original_model = A.v53.independent_plan, A.v52.independent_model
    def plan(*args):
        work['independent_query_checks'] += 1
        return original_plan(*args)
    def model(*args):
        work['independent_model_constructions'] += 1
        score, kernel = original_model(*args)
        def outcomes(*inputs):
            before = kernel.cache_info()
            result = kernel(*inputs)
            after = kernel.cache_info()
            work['independent_kernel_calls'] += 1
            work['independent_kernel_builds'] += after.misses-before.misses
            work['independent_kernel_cache_hits'] += after.hits-before.hits
            if after.misses > before.misses:
                work['independent_transition_outcomes_created'] += len(result)
            return result
        return score, outcomes
    patch.setattr(A.v53,'independent_plan',plan)
    patch.setattr(A.v52,'independent_model',model)
    yield
    patch.undo()
    path = ROOT/'reports/lmta_changed_policy_v60.analysis_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'schema':'acfqp.lmta_changed_policy_analysis_checks.v60','analysis_test_attempts':[]}
    report['development_work'] = dict(work, new_graphs=0, new_environment_samples=0, new_environment_calls=0,
        new_implementation_planner_calls=0, new_production_policy_evaluations=0, new_RL_updates=0, new_MCTS_calls=0,
        scope='three-node hand-certificate enumeration; synthetic provenance test stubs certificate math')
    path.write_text(json.dumps(report,indent=2)+'\n')


def hand_case():
    meta = dict(graph_id=A.GRAPH, nodes=3, stratum='dense', p=.5625, budget=2, horizon=3, method=A.METHOD)
    data = [([0,0,0],2,3,[0],2.75,1.,[1.5,1.5,1.]),
            ([2,0,0],1,2,[1],1.5,.5,[1.5,1.]),
            ([2,0,1],1,2,[1],1.,.5,None),
            ([2,2,0],0,1,[],0.,.25,None),
            ([2,2,1],0,1,[],0.,.25,None),
            ([2,2,2],0,1,[],0.,.5,None)]
    rows = []
    for status,b,h,selected,value,reach,q in data:
        forced = int(q is None)
        actions = len(q) if q else 0
        terms = actions*(status.count(0)-1)
        counts = dict(planner_calls=1, forced_choice=forced, dp_states=1-forced,
            action_value_evaluations=actions, analytic_expectation_calls=actions, analytic_probability_terms=terms,
            target_probability_evaluations=terms, kernel_builds=0, kernel_cache_hits=0,
            transition_outcomes=0, bellman_expectation_terms=0)
        legal = [i for i,s in enumerate(status) if s == 0]
        rows.append(dict(**meta, statuses=status, remaining_budget=b, remaining_days=h, selected=selected,
            value=value, reach_probability=reach, planned_value=max(q) if q else None,
            root_action_values=[dict(selected=[node],value=number) for node,number in zip(legal,q)] if q else [],
            decision_seconds=.1, decision_work=counts))
    work, expected = Counter(), Counter()
    for row in rows:
        work.update(row['decision_work'])
        expected.update({name:number*row['reach_probability'] for name,number in row['decision_work'].items()})
    case = dict(**meta,status='complete',stop_reason=None,value_source='V60_full_policy_evaluation',control_method=None,
        root_value=2.75,root_selected=[0],state_records=6,decision_work=dict(work),expected_decision_work=dict(expected),
        decision_seconds=.6,expected_decision_seconds=.3,wall_seconds=.8,evaluation_seconds=.2,
        last_limit_check_seconds=.7,serialization_seconds=.01,prepare_gc_seconds=.02,cleanup_seconds=.03,
        decision_total_seconds=.63,block_seconds=.83,
        evaluation_work=dict(new_full_policy_backups=6,retained_value_reads=0,occupancy_probability_terms=5))
    return case,rows,[(0,2),(1,2)],3


def test_complete_fresh_policy_all_successors_and_analytic_counts():
    inputs = hand_case()
    checked = A.verify_case(*inputs)
    assert checked['passed'] and checked['quality_verified'],checked
    assert checked['full_policy_equations'] == 6
    assert checked['planned_roots'] == 2 and checked['forced_roots'] == 4
    assert A.costs(inputs[0])['decision_total_seconds'] == .63
    assert inputs[1][0]['planned_value'] == 1.5 != inputs[0]['root_value']


def test_wrong_full_value_strict_action_or_analytic_fee_is_detected():
    case,rows,edges,nodes = hand_case()
    rows[0]['root_action_values'][1]['value'] += 5e-12
    rows[0]['decision_work']['kernel_builds'] = 1
    case['decision_work']['kernel_builds'] = 1
    case['expected_decision_work']['kernel_builds'] = 1
    checked = A.verify_case(case,rows,edges,nodes)
    assert checked['errors']['reported_strict_choice'] == 1
    assert checked['errors']['single_window_analytic_work'] == 1
    case,rows,edges,nodes = hand_case()
    case['root_value'] = rows[0]['value'] = 2.8
    checked = A.verify_case(case,rows,edges,nodes)
    assert checked['errors']['full_policy_bellman'] == 1


def test_resource_limit_charges_partial_and_cannot_supply_complete_quality():
    case,rows,edges,nodes = hand_case()
    rows = rows[:1]
    rows[0].update(value=None,reach_probability=None)
    case.update(status='resource_limit',stop_reason='max_policy_states',root_value=None,root_selected=None,
        state_records=1,decision_work=dict(rows[0]['decision_work']),expected_decision_work=None,
        expected_decision_seconds=None,decision_seconds=.1,evaluation_seconds=.7,decision_total_seconds=.13,
        evaluation_work=dict(new_full_policy_backups=0,retained_value_reads=0,occupancy_probability_terms=0))
    checked = A.verify_case(case,rows,edges,nodes,dict(A.LIMITS,max_policy_states=1))
    assert checked['passed'] and not checked['quality_verified'],checked
    assert A.costs(case)['decision_work']['analytic_expectation_calls'] == 3
    assert A.costs(case)['expected_decision_work'] is None
    assert A.costs(case)['decision_total_seconds'] == .13


def test_changed_value_and_new_states_merge_with_exact_reuse_provenance(monkeypatch):
    # This test isolates aggregation; independent policy equations are checked above.
    monkeypatch.setattr(A,'verify_case',lambda *args:dict(passed=True,errors={},quality_verified=True,
        planned_roots=0,forced_roots=0,full_policy_equations=0))
    graph_rows,old_cases,replay_cases,certificates = [],[],[],[]
    for panel in A.v59.PANELS:
        for graph in panel['seeds']:
            graph_rows.append(dict(graph_id=graph,edges=[],**{key:value for key,value in panel.items() if key!='seeds'}))
            for original,method in zip(A.v59.SOURCE_METHODS,A.v59.METHODS):
                case = dict(graph_id=graph,nodes=panel['nodes'],stratum=panel['stratum'],p=panel['p'],
                    budget=2,horizon=3,method=original,status='complete',root_value=2.5,state_records=3,
                    decision_work={'planner_calls':3,'action_value_evaluations':5},
                    expected_decision_work={'planner_calls':3,'action_value_evaluations':5},
                    decision_seconds=.6,expected_decision_seconds=.3)
                old_cases.append(case)
                replay_cases.append(dict(case,method=method,source_method=original,
                    source_weighted_decision_work=case['expected_decision_work'],source_weighted_decision_seconds=.2))
                target = (graph,method)==(A.GRAPH,A.METHOD)
                certificates.append(dict(graph_id=graph,method=method,passed=True,value_agreement=True,
                    source_policy_value=2.5,policy_value_preserved=not target,action_preserved=not target,
                    candidate_policy_value=None if target else 2.5))
            old_cases.append(dict(case,method=A.v59.FULL,root_value=3.))
    graph = next(row for row in graph_rows if row['graph_id']==A.GRAPH)
    rowmeta = dict(graph_id=A.GRAPH,method=A.SOURCE_METHOD)
    old_rows = [dict(**rowmeta,statuses=[0]*9,remaining_budget=2,remaining_days=3,value=2.5,reach_probability=1.),
        dict(**rowmeta,**A.CHANGED_STATE,value=.3,reach_probability=.1),
        dict(**rowmeta,statuses=[2]*9,remaining_budget=0,remaining_days=1,value=0.,reach_probability=.9)]
    new_rows = [dict(old_rows[0],method=A.METHOD,value=2.7),dict(old_rows[1],method=A.METHOD,value=.4,reach_probability=.2),
        dict(old_rows[2],method=A.METHOD,statuses=[1]*9,reach_probability=.8)]
    case = hand_case()[0]
    case.update(nodes=9,root_value=2.7,state_records=3)
    manifest = dict(schema='acfqp.lmta_changed_policy.v60',status='complete',protocol=A.PROTOCOL,
        source_directories=A.SOURCE_DIRS,graph=graph,cold_decisions=True,runtime={'gc_enabled':True},
        completed_cases=1,successful_cases=1,resource_limited_cases=0,total_state_records=3,
        new_graphs=0,new_full_policy_evaluations=1,new_environment_samples=0,new_environment_calls=0,new_RL_updates=0,new_MCTS_calls=0,
        source_read_seconds=.1,graph_reconstruction_seconds=.2,data_output_seconds=.3,whole_runner_seconds=1.,
        runner_cpu_seconds=.9,process_peak_rss_bytes=1000)
    old_manifest = dict(schema='acfqp.lmta_analytic_scale.v58',status='complete',graphs=graph_rows)
    old_analysis = dict(integrity={'passed':True},complete_quality_evidence=True,accounting={'old_58':10.})
    replay_analysis = dict(integrity=dict(passed=True,terminal_execution_complete=True,case_validations=certificates),accounting={'old_59':5.})
    inputs=(manifest,case,new_rows,old_manifest,old_analysis,old_cases,old_rows,replay_analysis,replay_cases)
    report = A.summarize(*inputs)
    assert report['integrity']['passed'] and report['complete_unified_policy_evidence'],report['integrity']
    assert report['target_policy_comparison']['root_value_difference'] == pytest.approx(.2)
    change=report['target_policy_comparison']['known_changed_state']
    assert change['full_value_difference'] == pytest.approx(.1) and change['reach_probability_difference'] == pytest.approx(.1)
    assert report['target_policy_comparison']['reachable_state_sets'] == dict(old_count=3,new_count=3,shared_count=2,newly_reachable_count=1,no_longer_reachable_count=1)
    target = next(point for group in report['unified_three_depth_strata'] for point in group['per_graph'] if point['graph_id']==A.GRAPH)
    assert target['values'][A.METHOD] == 2.7
    assert target['provenance'][A.METHOD] == 'V60_fresh_full_policy_evaluation'
    assert target['provenance'][A.v59.METHODS[1]] == 'V59_preserved_policy_reuse'
    assert report['preserved_reuse_count'] == 127 and report['target_action_preservation_claim'] is False
    assert report['accounting']['new_full_policy_evaluations'] == 1
    assert not next(row for row in certificates if (row['graph_id'],row['method'])==(A.GRAPH,A.METHOD))['policy_value_preserved']
    certificates[0]['policy_value_preserved']=False
    invalid = A.summarize(*inputs)
    assert not invalid['integrity']['passed'] and invalid['unified_three_depth_strata'] is None
    assert invalid['accounting']['new_case']['cleanup_seconds'] == .03
