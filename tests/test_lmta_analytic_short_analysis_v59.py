"""Hand-derived short Q and retained full values; no fresh panel or policy DP."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('short_analysis_v59', ROOT/'scripts/analyze_lmta_analytic_short_v59.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
EDGES = [(0, 2), (1, 2)]


@pytest.fixture(scope='session', autouse=True)
def development_work():
    patch, work = pytest.MonkeyPatch(), Counter()
    original_plan, original_model = A.v53.independent_plan, A.v52.independent_model
    def plan(*args):
        work['independent_short_query_checks'] += 1
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
    patch.setattr(A.v53, 'independent_plan', plan)
    patch.setattr(A.v52, 'independent_model', model)
    yield
    patch.undo()
    path = ROOT/'reports/lmta_analytic_short_v59.analysis_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'schema': 'acfqp.lmta_analytic_short_analysis_checks.v59', 'analysis_test_attempts': []}
    report['development_work'] = dict(work, new_graphs=0, new_environment_samples=0, new_environment_calls=0,
        new_implementation_planner_calls=0, new_full_policy_evaluations=0, new_RL_updates=0, new_MCTS_calls=0,
        scope='three-node hand short-window certificates; synthetic aggregation uses stubbed numeric verification')
    path.write_text(json.dumps(report, indent=2)+'\n')


def totals(rows, probabilities=None):
    result = Counter()
    for index, row in enumerate(rows):
        result.update({name: value*(probabilities[index] if probabilities else 1) for name, value in row['decision_work'].items()})
    return dict(result)


def fixture(method=A.METHODS[0]):
    depth, original = A.METHODS.index(method)+1, A.SOURCES[method]
    meta = dict(graph_id=1, nodes=3, stratum='sparse', p=.25, budget=2, horizon=3)
    data = [([0,0,0], 2,3, [0],2.75,1., (1.5,1.5,1.) if depth == 1 else (2.75,2.75,2.)),
            ([2,0,0], 1,2, [1],1.5,.5, (1.5,1.)),
            ([2,0,1], 1,2, [1],1.,.5, None),
            ([2,2,0], 0,1, [],0.,.25,None),
            ([2,2,1], 0,1, [],0.,.25,None),
            ([2,2,2], 0,1, [],0.,.5,None)]
    old_rows, rows = [], []
    for index, (status,b,h,selected,value,reach,q) in enumerate(data):
        forced = int(q is None)
        if forced:
            dp=actions=builds=terms=outcomes=analytic=probability_terms=0
        elif depth == 1:
            dp=1; actions=len(q); builds=0; analytic=actions
            terms=len(q)*(status.count(0)-1); probability_terms=terms
            outcomes=0
        else:
            dp,actions,builds,analytic,terms,probability_terms,outcomes = (6,11,3,8,12,6,5) if index == 0 else (4,5,2,3,4,2,3)
        counts = dict(planner_calls=1, forced_choice=forced, dp_states=dp, action_value_evaluations=actions,
            kernel_builds=builds, kernel_cache_hits=0, transition_outcomes=outcomes,
            target_probability_evaluations=terms, bellman_expectation_terms=outcomes,
            analytic_expectation_calls=analytic, analytic_probability_terms=probability_terms)
        old_work = {name: number for name, number in counts.items() if not name.startswith('analytic_')}
        old_work['kernel_builds'] = actions
        old_work['transition_outcomes'] = (5 if index == 0 else 3) if depth == 1 and not forced else (15 if index == 0 else 6) if not forced else 0
        old_work['bellman_expectation_terms'] = old_work['transition_outcomes']
        legal = [i for i,s in enumerate(status) if s == 0]
        old = dict(**meta, method=original, statuses=status, remaining_budget=b, remaining_days=h,
            selected=selected, value=value, reach_probability=reach, planned_value=max(q) if q else None,
            root_action_values=[dict(selected=[node], value=number) for node,number in zip(legal,q)] if q else [],
            decision_work=old_work, decision_seconds=.2)
        old_rows.append(old)
        row = {key: deepcopy(value) for key,value in old.items() if key not in ('value','reach_probability')}
        row.update(method=method, source_method=original, decision_work=counts, decision_seconds=.1)
        rows.append(row)
    probabilities = [row['reach_probability'] for row in old_rows]
    old_case = dict(**meta, method=original, status='complete', root_value=2.75, root_selected=[0],
        state_records=6, decision_work=totals(old_rows), expected_decision_work=totals(old_rows, probabilities),
        decision_seconds=1.2, expected_decision_seconds=.6)
    case = dict(**meta, method=method, source_method=original, status='complete', stop_reason=None,
        source_state_records=6, state_records=6, decision_work=totals(rows),
        source_weighted_decision_work=totals(rows, probabilities), decision_seconds=.6, source_weighted_decision_seconds=.3,
        replay_seconds=.8, replay_overhead_seconds=.2, last_limit_check_seconds=.7, serialization_seconds=.01,
        prepare_gc_seconds=.02, cleanup_seconds=.03, decision_total_seconds=.63, block_seconds=.83)
    return case, rows, old_case, old_rows


@pytest.mark.parametrize('method', A.METHODS)
def test_short_planned_values_are_not_full_policy_values(method):
    inputs = fixture(method)
    checked = A.verify_case(*inputs, EDGES, 3)
    assert checked['passed'] and checked['policy_value_preserved'], checked
    assert checked['candidate_policy_value'] == 2.75
    assert checked['independent_query_checks'] == 6
    if method == A.METHODS[0]:
        assert inputs[3][0]['planned_value'] == 1.5 != inputs[3][0]['value']
        assert inputs[1][0]['remaining_days'] == 3
        assert inputs[1][0]['decision_work']['kernel_builds'] == 0


def test_rounding_changed_action_keeps_fixed_queries_but_blocks_policy_reuse():
    inputs = fixture()
    root = inputs[1][0]
    root['root_action_values'][1]['value'] = math.nextafter(1.5, math.inf)
    root.update(selected=[1], planned_value=root['root_action_values'][1]['value'])
    checked = A.verify_case(*inputs, EDGES, 3)
    assert checked['passed'] and checked['value_agreement'], checked
    assert checked['root_action_changes'] == 1 and checked['candidate_policy_value'] is None
    summary = A.method_summary(dict(nodes=3, stratum='sparse', p=.25, seeds=[1]), A.METHODS[0],
                               [inputs[0]], [inputs[2]], [checked], True)
    assert summary['fixed_query_workload_ratios'] is not None
    assert summary['preserved_policy_decision_cost_ratios'] is summary['candidate_policy_values'] is None


def test_q_or_deleted_analytic_work_cannot_be_preservation_evidence():
    inputs = fixture()
    root = inputs[1][0]
    root['root_action_values'][0]['value'] += .1
    root['planned_value'] += .1
    root['decision_work']['analytic_expectation_calls'] -= 1
    checked = A.verify_case(*inputs, EDGES, 3)
    assert checked['errors']['Q_and_source_short_planned_value_tolerance'] == 1
    assert checked['errors']['action_value_work_partition'] == 1
    assert checked['candidate_policy_value'] is None
    assert A.costs([inputs[0]])['cleanup_seconds'] == .03


def test_partial_decision_paid_and_no_source_weighted_policy_claim():
    case, rows, old_case, old_rows = fixture(A.METHODS[1])
    rows = rows[:1]
    case.update(status='resource_limit', stop_reason='max_policy_states', state_records=1, decision_work=totals(rows),
        source_weighted_decision_work=None, source_weighted_decision_seconds=None, decision_seconds=.1,
        replay_overhead_seconds=.7, decision_total_seconds=.13)
    checked = A.verify_case(case, rows, old_case, old_rows, EDGES, 3, dict(A.LIMITS, max_policy_states=1))
    assert checked['passed'] and not checked['policy_value_preserved'], checked
    assert checked['candidate_policy_value'] is None and checked['exact_action_matches'] == 1
    summary = A.method_summary(dict(nodes=3, stratum='sparse', p=.25, seeds=[1]), A.METHODS[1],
                               [case], [old_case], [checked], True)
    assert summary['fixed_query_workload_ratios'] is summary['preserved_policy_decision_cost_ratios'] is None
    assert summary['new_costs']['decision_work']['analytic_expectation_calls'] == 8
    assert summary['new_costs']['decision_total_seconds'] == .13


def test_synthetic_roster_and_three_depth_view_require_both_short_policies(monkeypatch):
    def verified(case, rows, old_case, old_rows, edges, nodes):
        preserved = case.get('synthetic_changed') is not True
        return dict(passed=True, errors={}, status='complete', state_records=1, independent_query_checks=0,
            source_state_records=1, exact_action_matches=int(preserved), root_action_changes=int(not preserved),
            nonroot_action_changes=0, action_preserved=preserved, value_agreement=True, policy_value_preserved=preserved,
            source_policy_value=old_case['root_value'], candidate_policy_value=old_case['root_value'] if preserved else None,
            maximum_abs_source_Q_difference=0.)
    monkeypatch.setattr(A, 'verify_case', verified)
    assert A.EXPECTED_SOURCE_STATES == 188499
    monkeypatch.setattr(A, 'EXPECTED_SOURCE_STATES', 128)
    graphs, cases, states, source_cases, source_states = [], [], [], [], []
    for panel in A.PANELS:
        for graph in panel['seeds']:
            graphs.append(dict(graph_id=graph, edges=[], **{key:value for key,value in panel.items() if key != 'seeds'}))
            for method in A.METHODS:
                case, rows, old_case, old_rows = fixture(method)
                meta = dict(graph_id=graph, nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'])
                case.update(meta, state_records=1, source_state_records=1)
                old_case.update(meta, state_records=1)
                rows[0].update(meta); old_rows[0].update(meta)
                cases.append(case); states.append(rows[0]); source_cases.append(old_case); source_states.append(old_rows[0])
            source_cases.append(dict(old_case, method=A.FULL))
    manifest = dict(schema='acfqp.lmta_analytic_short.v59', status='complete', protocol=deepcopy(A.PROTOCOL),
        source_directory='reports/lmta_analytic_scale_v58', cold_decisions=True, runtime={'gc_enabled':True}, graphs=graphs,
        source_state_records=128, completed_cases=128, successful_cases=128, resource_limited_cases=0, total_state_records=128,
        new_graphs=0, new_full_policy_evaluations=0, new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        source_read_seconds=.1, graph_reconstruction_seconds=.2, data_output_seconds=.3, whole_runner_seconds=200.,
        runner_cpu_seconds=190., process_peak_rss_bytes=1000)
    old_manifest = dict(schema='acfqp.lmta_analytic_scale.v58', status='complete', graphs=graphs)
    old_analysis = dict(integrity={'passed':True}, complete_quality_evidence=True, accounting={'old_wall_seconds':150.})
    report = A.summarize(manifest, cases, states, old_manifest, old_analysis, source_cases, source_states)
    assert report['integrity']['passed'] and report['policy_value_preserved_all'], report['integrity']
    assert all(row['unified_three_depth_policy_and_work'] is not None for row in report['strata'])
    assert report['accounting']['new_replay']['state_records'] == 128
    assert report['accounting']['retained_V58'] == old_analysis['accounting']
    assert report['accounting']['data_output_seconds'] == .3
    cases[0]['synthetic_changed'] = True
    changed = A.summarize(manifest, cases, states, old_manifest, old_analysis, source_cases, source_states)
    assert changed['integrity']['passed'] and not changed['policy_value_preserved_all']
    assert changed['strata'][0]['unified_three_depth_policy_and_work'] is None
    assert changed['strata'][0]['methods'][A.METHODS[1]]['policy_value_preserved']
    assert changed['strata'][0]['methods'][A.METHODS[0]]['fixed_query_workload_ratios'] is not None
    assert all(row['unified_three_depth_policy_and_work'] is not None for row in changed['strata'][1:])
    cases.pop()
    missing = A.summarize(manifest, cases, states, old_manifest, old_analysis, source_cases, source_states)
    assert not missing['integrity']['passed']
    assert missing['accounting']['new_replay']['case_records'] == 127
    assert all(row['unified_three_depth_policy_and_work'] is None for row in missing['strata'])
