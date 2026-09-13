"""One H3 integration check for exact direct models and portable H1/H2 routing."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_compositional_contract_v69 import load_model, model_payload
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_symbolic_successors_v71 import compile_rule
from acfqp.science.controlled_predictive_local_builder_v72 import build_model as v72_build
from acfqp.science.controlled_predictive_grouped_builder_v73 import build_model as v73_build


ROOT = Path(__file__).resolve().parents[1]
BOARDS = (
    (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10),
    (10, 10, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10),
)
LEDGER = dict(builds=[], rule_compilations=0, route_count=0,
              routes_by_h=Counter(), reference_support_work=Counter(),
              reference_routing_work=Counter(), routing_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_grouped_v73.integration_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Two fixed dense development boards at H3; no registered target roots.",
        ground_calls=0, fit_calls=0, planning_calls=0,
        model_builds=len(LEDGER["builds"]), **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def active_encoding(build):
    return {key: cell for key, cell in build.encoding.items()
            if build.model.terminal[cell] == "ACTIVE"}


def test_direct_h2_build_keeps_exact_ids_rows_and_all_observation_routes():
    rule = LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))
    terminal = compile_rule(rule)
    LEDGER["rule_compilations"] += 1
    spec = importlib.util.spec_from_file_location("v73_integration_worker",
        ROOT / "scripts/query_controlled_predictive_grouped_v73.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    for board_index, board in enumerate(BOARDS):
        baseline = v72_build(board, 3, rule, terminal, "COMPOSED")
        LEDGER["builds"].append(dict(board_index=board_index, board=list(board), horizon=3,
            method="V72_BASE", counts=baseline.counts, elapsed_seconds=baseline.elapsed_seconds))
        baseline_payload = model_payload(baseline)
        expected = active_encoding(baseline)
        reference_package = dict(kernel=baseline_payload, router=dict(kind="LOCAL_H1",
            labels=[[h, list(observation), cell] for (h, observation), cell in expected.items()]))
        baseline_compiled, loaded_rule = load_model(baseline_payload)
        reference_route, _ = worker._h1_worker().make_router(reference_package, baseline_compiled, loaded_rule)
        # V72 omits H1 board labels. Recover only this tiny fixture's support
        # from its retained H2 boards and use its existing H1 decoder as oracle.
        for (h, observation), _ in tuple(expected.items()):
            if h != 2:
                continue
            _, moves = rule.classify(observation, LEDGER["reference_support_work"])
            for _, moved, score in moves:
                for _, status, child, _ in terminal.successors(moved, score, 1,
                        LEDGER["reference_support_work"]):
                    if status == "ACTIVE":
                        cell = reference_route(child, 1, LEDGER["reference_routing_work"])
                        assert cell is not None
                        expected[1, child] = cell
        for grouping in (False, True):
            candidate = v73_build(board, 3, rule, terminal, grouping)
            LEDGER["builds"].append(dict(board_index=board_index, board=list(board), horizon=3,
                method="V73_GROUP" if grouping else "V73_EACH", counts=candidate.counts,
                elapsed_seconds=candidate.elapsed_seconds))
            assert model_payload(candidate) == baseline_payload
            actual = active_encoding(candidate)
            assert actual == {key: cell for key, cell in expected.items() if key[0] > 2}
            assert all(h > 2 for h, _ in candidate.encoding)
            assert candidate.counts["h1_boards_generated"] == candidate.counts["h2_boards_generated"] == 0
            package = dict(schema="acfqp.observation_package.v73", kernel=model_payload(candidate),
                router=dict(kind="LOCAL_H2", grouping=grouping,
                    labels=[[h, list(observation), cell] for (h, observation), cell in actual.items()]))
            compiled, candidate_rule = load_model(package["kernel"])
            route, _ = worker.make_router(package, compiled, candidate_rule)
            for (h, observation), cell in expected.items():
                LEDGER["route_count"] += 1
                LEDGER["routes_by_h"][h] += 1
                assert route(observation, h, LEDGER["routing_work"]) == cell
    assert len(LEDGER["builds"]) == 6
    assert all(LEDGER["routes_by_h"][h] > 0 for h in (1, 2, 3))
