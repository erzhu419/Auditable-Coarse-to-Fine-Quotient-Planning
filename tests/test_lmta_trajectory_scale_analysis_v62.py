"""New-graph uncertainty and observed-query assembly; no production simulations."""
from collections import Counter
from copy import deepcopy
import importlib.util
from io import StringIO
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('trajectory_scale_analysis_v62',ROOT/'scripts/analyze_lmta_trajectory_scale_v62.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
WORK = Counter()


@pytest.fixture(scope='session',autouse=True)
def ledger():
    patch = pytest.MonkeyPatch()
    original = A.checker.verify_decision
    def counted(*args):
        result = original(*args)
        WORK.update(result['verification_work'])
        return result
    patch.setattr(A.checker,'verify_decision',counted)
    yield
    patch.undo()
    path = ROOT/'reports/lmta_trajectory_v62.analysis_checks.json'
    path.write_text(json.dumps(dict(schema='acfqp.lmta_trajectory_scale_analysis_checks.v62',development_work=dict(WORK,
        production_planner_calls=0,environment_calls=0,random_draws=0,new_generated_graphs=0,new_full_policy_evaluations=0,
        scope='One hand-authored two-node analytic query plus synthetic fixed-panel aggregates.')),indent=2)+'\n')


def panel_fixture():
    panel, cases, rows = A.PANELS[0], [], []
    for index, graph in enumerate(panel['seeds']):
        for method in A.METHODS:
            two = method==A.METHODS[1]
            cases.append(dict(graph_id=graph,method=method,status='complete',completed_replicates=128,
                decision_work=dict(action_value_evaluations=256 if two else 128,
                    transition_outcomes=128 if two else 0,target_probability_evaluations=384 if two else 256),
                environment_work=dict(environment_calls=384,rng_draws=768),decision_seconds=.1))
            for rep in range(128):
                rows.append(dict(graph_id=graph,method=method,replicate=rep,**{'return':2+int(two)*(index%2)}))
    return panel,cases,rows


def test_graph_t_uncertainty_keeps_between_graph_variation_and_zero_costs():
    panel,cases,rows = panel_fixture()
    result = A.panel_summary(panel,cases,rows,True)
    assert result['complete_quality_evidence']
    paired = result['quality']['paired_two_minus_one']
    assert paired['mean']==.5 and paired['degrees_of_freedom']==15
    assert paired['graph_standard_error']==pytest.approx((4/15)**.5/4)
    assert paired['fixed_panel_mc_standard_error']==0.
    assert paired['graph_simultaneous_interval'][0] < paired['graph_nominal_95_interval'][0] < .5
    assert result['quality']['method_means']=={A.METHODS[0]:2.,A.METHODS[1]:2.5}
    assert result['costs'][A.METHODS[0]]['mean_trajectory_work']['transition_outcomes']==0.
    assert result['two_over_one_work_ratios']==dict(action_value_evaluations=2.,transition_outcomes=None,target_probability_evaluations=1.5)


def test_partial_panel_keeps_all_costs_and_does_not_drop_a_graph():
    panel,cases,rows = panel_fixture()
    cases[-1].update(status='resource_limit',completed_replicates=127)
    result = A.panel_summary(panel,cases,rows,True)
    assert not result['complete_quality_evidence'] and result['quality'] is None
    assert result['two_over_one_work_ratios'] is None and len(result['graph_ids'])==16
    assert result['costs'][A.METHODS[1]]['resource_limited_blocks']==1
    assert result['costs'][A.METHODS[1]]['completed_trajectories']==2047
    assert result['costs'][A.METHODS[1]]['decision_work']['action_value_evaluations']==4096
    assert A.panel_summary(panel,*panel_fixture()[1:],False)['quality'] is None


def test_new_graph_roster_parameters_bind_without_regeneration():
    graphs = [dict(graph_id=graph,edges=[],**{k:v for k,v in panel.items() if k!='seeds'})
        for panel in A.PANELS for graph in panel['seeds']]
    assert not A.graph_errors(graphs)
    graphs[0]['graph_id']=580000
    assert A.graph_errors(graphs)['graph_roster']==1
    assert A.graph_errors(graphs)['graph_parameters']==1
    graphs[0]['graph_id']=620000
    graphs[0]['p']=.1875
    assert A.graph_errors(graphs)=={'graph_parameters':1}


def test_observed_query_checked_once_and_changed_repeat_detected():
    work = dict.fromkeys(A.checker.COUNTERS,0)
    work.update(planner_calls=1,forced_choice=0,dp_states=1,action_value_evaluations=2,
        analytic_expectation_calls=2,analytic_probability_terms=2,target_probability_evaluations=2)
    decision = dict(statuses=[0,0],remaining_budget=1,remaining_days=1,selected=[0],planned_value=1.,
        root_action_values=[dict(selected=[0],value=1.),dict(selected=[1],value=1.)],decision_work=work)
    row = dict(graph_id=620000,method=A.METHODS[0],decisions=[decision])
    changed = deepcopy(row); changed['decisions'][0]['selected']=[1]
    output, fees = StringIO(), Counter()
    certificates, checked = A.certify([row,deepcopy(row),changed],[dict(graph_id=620000,nodes=2,edges=[])],output,fees)
    assert checked['errors']=={'repeated_query_result_differs':1}
    assert checked['unique_queries']==checked['valid_queries']==len(certificates)==1
    assert fees['queries']==1 and fees['root_Q_comparisons']==2
    assert len(output.getvalue().splitlines())==1
    assert json.loads(output.getvalue())['passed'] is True
