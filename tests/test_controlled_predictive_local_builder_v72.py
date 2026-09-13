"""Preserve exact model IDs and route omitted H1 observations on two H2 fixtures."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_compositional_contract_v69 import load_model, model_payload
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_symbolic_contract_v71 import build_model as v71_build
from acfqp.science.controlled_predictive_symbolic_successors_v71 import compile_rule
from acfqp.science.controlled_predictive_local_builder_v72 import build_model as v72_build


ROOT = Path(__file__).resolve().parents[1]
BOARDS = (
    (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10),
    (10, 10, 3, 4, 1, 2, 3, 6, 5, 6, 7, 8, 7, 8, 9, 10),
)
LEDGER = dict(builds=[], rule_compilations=0, route_count=0, routing_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_local_v72.integration_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Same two fixed H2 development boards as V71; no main-cohort roots.",
        ground_calls=0, fit_calls=0, planning_calls=0,
        model_builds=len(LEDGER["builds"]), **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def active_encoding(build):
    return {key: cell for key, cell in build.encoding.items()
            if build.model.terminal[cell] == "ACTIVE"}


def test_local_builder_preserves_exact_models_and_routes_omitted_h1_boards():
    rule = LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))
    terminal = compile_rule(rule)
    LEDGER["rule_compilations"] += 1
    spec = importlib.util.spec_from_file_location("v72_integration_worker",
        ROOT / "scripts/query_controlled_predictive_local_v72.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    for board_index, board in enumerate(BOARDS):
        for variant in ("FULL", "COMPOSED"):
            baseline = v71_build(board, 2, rule, terminal, variant)
            LEDGER["builds"].append(dict(board_index=board_index, board=list(board), horizon=2,
                method="V71", variant=variant, counts=baseline.counts,
                elapsed_seconds=baseline.elapsed_seconds))
            candidate = v72_build(board, 2, rule, terminal, variant)
            LEDGER["builds"].append(dict(board_index=board_index, board=list(board), horizon=2,
                method="V72", variant=variant, counts=candidate.counts,
                elapsed_seconds=candidate.elapsed_seconds))
            assert model_payload(candidate) == model_payload(baseline)
            expected = active_encoding(baseline)
            actual = active_encoding(candidate)
            if variant == "FULL":
                assert actual == expected
            else:
                assert actual == {key: cell for key, cell in expected.items() if key[0] > 1}
                assert all(h > 1 for h, _ in candidate.encoding)
                assert candidate.counts["h1_boards_generated"] == 0
                package = dict(schema="acfqp.observation_package.v72", kernel=model_payload(candidate),
                    router=dict(kind="LOCAL_H1", labels=[[h, list(observation), cell]
                        for (h, observation), cell in actual.items()]))
                compiled, loaded_rule = load_model(package["kernel"])
                route, _ = worker.make_router(package, compiled, loaded_rule)
                for (h, observation), cell in expected.items():
                    if h == 1:
                        LEDGER["route_count"] += 1
                        assert route(observation, h, LEDGER["routing_work"]) == cell
    assert len(LEDGER["builds"]) == 8
    assert LEDGER["route_count"] > 0
