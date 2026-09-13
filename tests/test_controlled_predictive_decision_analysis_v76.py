"""One synthetic counterexample test for tie handling and failed execution."""
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_decision_v76.analysis_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic tie, missing continuation and wrong confident acceptance; no scientific cohort.",
        ground_calls=0, training_calls=0, target_executions=0))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _choice():
    reference = dict(reward=1.0, failure=0.0, success=0.0, value=1.0)
    actual = dict(reward=1.0, failure=0.25, success=0.0, value=1.0)
    return dict(selected_action="RIGHT", root_action_legal=True, root_action_optimal_membership=True,
        root_decision_regret=0.0, optimal_actions=["LEFT", "RIGHT"], reference_action="LEFT",
        reference_metrics=reference, selected_action_oracle_metrics=actual,
        execution_verified=True, actual_metrics=actual, total_regret=0.0, continuation_regret=0.0,
        continuation_optimal=True, deltas_to_reference=dict(reward=0.0, failure=0.25, success=0.0, value=0.0),
        failure_delta=0.25, success_delta=0.0)


def test_analysis_accepts_optimal_ties_but_rejects_unverified_or_wrong_accepted_choices(tmp_path):
    spec = importlib.util.spec_from_file_location("v76_analysis_test",
        ROOT / "scripts/analyze_controlled_predictive_decisions_v76.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    queries = [f"q{index:02d}" for index in range(14)]
    cases = [f"case{index:02d}" for index in range(48)]
    manifest = dict(status="complete", target_cases=48, query_names=queries, train_query_names=queries[:6],
        source_cost_seconds=2.0, input_preparation_seconds=0.5, campaign_wall_seconds=40.0, audit_seconds=20.0,
        worker_commands={name: dict(seconds=seconds, exit_code=0, stderr_bytes=0)
                         for name, seconds in (("EXACT", 10.0), ("GREEDY", 1.0), ("RULE", 1.0), ("SELECTIVE", 3.0))})
    audit = dict(complete=True, valid_ground_models=True, h1_encoder_valid=True,
        source_target_disjoint=True, ground_counts={}, ground_seconds=10.0,
        cases=[dict(name=name, predicted_kernel_equal=True, queries=[dict(query_name=query,
            seen_query=query in queries[:6], methods={method: _choice() for method in module.METHODS},
            matched_h1={method: dict(action_legal=True, action_optimal_membership=True, metrics_equal=True)
                        for method in module.METHODS})
            for query in queries]) for name in cases])
    workers = {method: dict(method=method, ground_imports=[], forbidden_imports=[], counts={}, work={}, times={},
        cases=[dict(name=name, actions={query: dict(action="RIGHT", fallback=False, confidence=1.0, margin=1.0)
             for query in queries}, h1_actions={query: dict(action="LEFT", metrics={}) for query in queries})
             for name in cases]) for method in module.METHODS}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "source_summary.json").write_text(json.dumps(dict(synthetic_source=True)))
    (tmp_path / "audit.json").write_text(json.dumps(audit))
    for method, worker in workers.items():
        (tmp_path / f"{method}.json").write_text(json.dumps(worker))
    first = module.analyze(tmp_path)
    assert first["methods"]["RULE"]["adoption"]["eligible"]
    assert first["methods"]["RULE"]["overall"]["root_optimal"] == 672
    assert first["methods"]["RULE"]["overall"]["failure_increase_queries"] == 672
    assert first["methods"]["RULE"]["costs"]["total_seconds"] == 3.5
    assert first["actual_executed_cost_accounting"]["source_once_seconds"] == 2.0

    failed = audit["cases"][0]["queries"][0]["methods"]["RULE"]
    failed.update(execution_verified=False, actual_metrics=None, total_regret=None,
        continuation_regret=None, continuation_optimal=None, deltas_to_reference=None,
        failure_delta=None, success_delta=None)
    wrong = audit["cases"][0]["queries"][0]["methods"]["SELECTIVE"]
    wrong.update(selected_action="DOWN", root_action_optimal_membership=False,
        root_decision_regret=0.1, total_regret=0.1)
    wrong["actual_metrics"] = dict(reward=0.9, failure=0.25, success=0.0, value=0.9)
    wrong["deltas_to_reference"] = dict(reward=-0.1, failure=0.25, success=0.0, value=-0.1)
    workers["SELECTIVE"]["cases"][0]["actions"][queries[0]]["action"] = "DOWN"
    audit["cases"][0]["queries"][0]["methods"]["GREEDY"]["total_regret"] = 2e-12
    (tmp_path / "audit.json").write_text(json.dumps(audit))
    (tmp_path / "SELECTIVE.json").write_text(json.dumps(workers["SELECTIVE"]))
    second = module.analyze(tmp_path)
    assert second["integrity_valid"]
    assert not second["methods"]["RULE"]["adoption"]["eligible"]
    assert second["methods"]["RULE"]["overall"]["root_optimal"] == 672
    assert second["methods"]["RULE"]["overall"]["execution_verified"] == 671
    assert not second["methods"]["SELECTIVE"]["adoption"]["eligible"]
    assert not second["methods"]["GREEDY"]["adoption"]["eligible"]
    assert second["selective"]["groups"]["accepted_rule"]["queries"] == 672
    assert second["selective"]["groups"]["accepted_rule"]["root_optimal"] == 671
