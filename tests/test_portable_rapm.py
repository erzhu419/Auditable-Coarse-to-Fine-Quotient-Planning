from __future__ import annotations

from fractions import Fraction
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.abstraction.behavioral import build_exact_behavioral_quotient
from acfqp.artifacts import object_id
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.domains.matching_buffer import generate_solvable_lmb
from acfqp.phase3a import _lmb_query_suite
from acfqp.planning.nominal import solve_nominal_pareto
from acfqp.portable import (
    PortableQuery,
    PortableRAPM,
    build_portable_rapm,
    dump_model,
    dump_query,
    load_model,
    load_query,
    logical_id,
)
from acfqp.portable_planner import (
    PortablePlanResult,
    audit_exact_portable_policy,
    dump_result,
    load_result,
    solve_portable_pareto,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def lmb_portable():
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    train, heldout = _lmb_query_suite(kernel)
    coverage = SuiteBuildCoverage.from_queries(
        kernel,
        tuple(record.query for record in train),
        state_cap=50_000,
    )
    quotient = build_exact_behavioral_quotient(kernel, coverage.covered_states)
    failure_targets = set(quotient.failure_targets)
    built = build_portable_rapm(
        quotient.quotient_models,
        state_ids=lambda value: object_id(value, "portable-state-source"),
        semantic_action_ids=lambda value: object_id(
            value, "portable-semantic-action-source"
        ),
        ground_action_ids=lambda value: object_id(
            value, "portable-ground-action-source"
        ),
        normalizer_rules=(
            {
                "proof_id": "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {
                        "name": "match",
                        "value": {"numerator": 1, "denominator": 1},
                    },
                    {
                        "name": "terminal_clear",
                        "value": {"numerator": 1, "denominator": 1},
                    },
                ),
                "feature_caps": (
                    {
                        "name": "match",
                        "per_step_cap": {"numerator": 1, "denominator": 1},
                        "total_cap": {"numerator": 2, "denominator": 1},
                    },
                    {
                        "name": "terminal_clear",
                        "per_step_cap": {"numerator": 2, "denominator": 1},
                        "total_cap": {"numerator": 2, "denominator": 1},
                    },
                ),
            },
            {
                "proof_id": "lmb.match_only.matches_le_n_over_3.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {
                        "name": "match",
                        "value": {"numerator": 1, "denominator": 1},
                    },
                    {
                        "name": "terminal_clear",
                        "value": {"numerator": 0, "denominator": 1},
                    },
                ),
                "feature_caps": (
                    {
                        "name": "match",
                        "per_step_cap": {"numerator": 1, "denominator": 1},
                        "total_cap": {"numerator": 2, "denominator": 1},
                    },
                ),
            },
            {
                "proof_id": "lmb.terminal_clear_only.clear_bonus.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {
                        "name": "match",
                        "value": {"numerator": 0, "denominator": 1},
                    },
                    {
                        "name": "terminal_clear",
                        "value": {"numerator": 1, "denominator": 1},
                    },
                ),
                "feature_caps": (
                    {
                        "name": "terminal_clear",
                        "per_step_cap": {"numerator": 2, "denominator": 1},
                        "total_cap": {"numerator": 2, "denominator": 1},
                    },
                ),
            },
        ),
        state_kinds=lambda state: (
            "failure"
            if state in failure_targets
            else "terminal"
            if kernel.is_terminal(state)
            else "active"
        ),
        goal_ids=kernel.registered_goals,
    )
    return kernel, quotient, built, train[0].query, heldout


def test_portable_rapm_roundtrip_has_complete_frozen_payload(
    lmb_portable, tmp_path: Path
) -> None:
    _, quotient, built, query, _ = lmb_portable
    model = built.model
    document = model.to_dict()

    # The document itself contains only JSON values and the loaded logical ID
    # is exactly the construction-time content ID.
    json.dumps(document, sort_keys=True)
    assert model.model_id == model.recompute_model_id()
    assert len(document["state_catalog"]) == 25
    assert {record["planning_kind"] for record in document["state_catalog"]} == {
        "active",
        "failure",
        "terminal",
    }
    assert len(document["partition"]) == quotient.cell_count == 5
    assert {record["state_id"] for record in document["state_catalog"]} == {
        state_id
        for cell in document["partition"]
        for state_id in cell["member_state_ids"]
    }
    assert document["nominal"]
    assert document["goal_ids"] == ["default"]
    assert len(document["nominal"]) == len(document["envelope"])
    assert document["concretizer_registry"]
    assert all(record["cell_id"].startswith("cell:") for record in document["partition"])
    assert all(
        record["action_id"].startswith("semantic-action:")
        for record in document["semantic_action_catalog"]
    )
    assert all(
        support["ground_action_id"].startswith("ground-action:")
        for record in document["concretizer_registry"]
        for support in record["support"]
    )

    model_path = tmp_path / "model.json"
    query_path = tmp_path / "query.json"
    dump_model(model, model_path)
    portable_query = built.query_from_spec(query)
    dump_query(portable_query, query_path)
    loaded_model = load_model(model_path)
    loaded_query = load_query(query_path, loaded_model)

    assert loaded_model == model
    assert loaded_model.model_id == model.model_id
    assert loaded_query == portable_query
    assert loaded_query.query_id == portable_query.recompute_query_id()
    query_document = loaded_query.to_dict()
    assert set(query_document) == {
        "schema",
        "model_id",
        "query_id",
        "initial_distribution",
        "horizon",
        "reward_weights",
        "normalizer",
        "normalizer_proof_id",
        "normalized_reward_weights",
        "goal_id",
        "delta",
    }
    assert sum(
        Fraction(item["probability"]["numerator"], item["probability"]["denominator"])
        for item in query_document["initial_distribution"]
    ) == 1
    assert query_document["goal_id"] == "default"
    assert query_document["normalizer_proof_id"] == query.normalizer_proof_id


def test_loaded_portable_planning_exactly_matches_in_memory_nominal(lmb_portable) -> None:
    _, quotient, built, query, _ = lmb_portable
    portable_query = built.query_from_spec(query)
    portable = solve_portable_pareto(built.model, portable_query)
    in_memory = solve_nominal_pareto(quotient.quotient_models.nominal, query)

    assert portable.selected is not None
    assert in_memory.selected is not None
    assert portable.composed_candidate_count == in_memory.composed_candidate_count
    assert [
        (point.expected_reward, point.failure_probability)
        for point in portable.frontier
    ] == [
        (point.expected_reward, point.failure_probability)
        for point in in_memory.frontier
    ]
    assert portable.selected.expected_reward == in_memory.selected.expected_reward
    assert portable.selected.failure_probability == in_memory.selected.failure_probability
    assert built.decode_policy(portable.selected.policy) == in_memory.selected.policy.as_dict()
    assert len(portable.selected.policy.decisions) == 3
    portable_audit = audit_exact_portable_policy(
        built.model, portable_query, portable.selected.policy
    )
    assert portable_audit.certified
    assert portable_audit.expected_reward == portable.selected.expected_reward
    assert portable_audit.failure_probability == portable.selected.failure_probability
    assert portable_audit.regret_upper == 0

    serialized_adapter = built.serialized_adapter()
    for entry in quotient.quotient_models.envelope.entries:
        for realization in entry.realizations:
            assert {
                action: probability
                for probability, action in serialized_adapter.concretize(
                    lmb_portable[0], realization.state, entry.action
                )
            } == {
                action: probability
                for probability, action in quotient.semantic_adapter.concretize(
                    lmb_portable[0], realization.state, entry.action
                )
            }


def test_fresh_process_cli_needs_only_model_and_cell_query(
    lmb_portable, tmp_path: Path
) -> None:
    _, _, built, query, _ = lmb_portable
    model_path = tmp_path / "portable-model.json"
    query_path = tmp_path / "portable-query.json"
    result_path = tmp_path / "portable-result.json"
    dump_model(built.model, model_path)
    portable_query = built.query_from_spec(query)
    dump_query(portable_query, query_path)

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "acfqp.portable_planner",
            "--model",
            str(model_path),
            "--query",
            str(query_path),
            "--output",
            str(result_path),
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert result_path.is_file()
    loaded_model = load_model(model_path)
    loaded_query = load_query(query_path, loaded_model)
    loaded = load_result(result_path, model=loaded_model, query=loaded_query)
    direct = solve_portable_pareto(built.model, portable_query)
    assert loaded == direct
    assert loaded.result_id == direct.result_id

    # Guard the consumption boundary at source level as well: a future edit
    # must not smuggle the physical simulator or J0/refinement into the planner.
    source = inspect.getsource(sys.modules["acfqp.portable_planner"])
    for forbidden in (
        "acfqp.domains",
        "planning.ground",
        "acfqp.refinement",
    ):
        assert forbidden not in source


def test_dump_load_result_and_all_content_bindings_reject_tampering(
    lmb_portable, tmp_path: Path
) -> None:
    _, _, built, query, heldout = lmb_portable
    portable_query = built.query_from_spec(query)
    result = solve_portable_pareto(built.model, portable_query)
    result_path = tmp_path / "result.json"
    dump_result(result, result_path)
    assert load_result(
        result_path, model=built.model, query=portable_query
    ) == result

    model_document = built.model.to_dict()
    model_document["nominal"][0]["model"]["failure_probability"]["numerator"] += 1
    with pytest.raises(ValueError, match="model_id mismatch"):
        PortableRAPM.from_dict(model_document)

    # Even a re-signed container cannot change an internally content-addressed
    # cell/action identifier without being rejected by structural validation.
    payload = built.model.to_dict()
    payload.pop("model_id")
    payload["semantic_action_catalog"][0]["action_id"] = "semantic-action:" + "0" * 64
    with pytest.raises(ValueError, match="content ID mismatch"):
        PortableRAPM.from_payload(payload)

    query_document = portable_query.to_dict()
    query_document["delta"]["numerator"] += 1
    with pytest.raises(ValueError, match="query_id mismatch"):
        PortableQuery.from_dict(query_document, built.model)

    other_query = built.query_from_spec(heldout[-1].query)
    with pytest.raises(ValueError, match="result/query mismatch"):
        PortablePlanResult.from_dict(
            result.to_dict(), model=built.model, query=other_query
        )

    other_payload = built.model.to_dict()
    other_payload.pop("model_id")
    other_payload["horizon"] -= 1
    other_model = PortableRAPM.from_payload(other_payload)
    with pytest.raises(ValueError, match="query/model mismatch"):
        solve_portable_pareto(other_model, portable_query)

    result_document = result.to_dict()
    result_document["composed_candidate_count"] += 1
    with pytest.raises(ValueError, match="result_id mismatch"):
        PortablePlanResult.from_dict(
            result_document, model=built.model, query=portable_query
        )


def test_portable_model_cannot_treat_an_actionless_active_cell_as_terminal(
    lmb_portable,
) -> None:
    _, _, built, _, _ = lmb_portable
    payload = built.model.to_dict()
    payload.pop("model_id")
    kind_by_state = {
        record["state_id"]: record["planning_kind"]
        for record in payload["state_catalog"]
    }
    active_cell = next(
        cell["cell_id"]
        for cell in payload["partition"]
        if all(
            kind_by_state[state_id] == "active"
            for state_id in cell["member_state_ids"]
        )
    )
    payload["nominal"] = [
        entry for entry in payload["nominal"] if entry["cell_id"] != active_cell
    ]
    payload["semantic_action_catalog"] = [
        entry
        for entry in payload["semantic_action_catalog"]
        if entry["cell_id"] != active_cell
    ]
    with pytest.raises(ValueError, match="active/action cell mismatch"):
        PortableRAPM.from_payload(payload)


def test_portable_model_requires_complete_realizations_and_exact_nominal_average(
    lmb_portable,
) -> None:
    _, _, built, _, _ = lmb_portable

    incomplete = built.model.to_dict()
    incomplete.pop("model_id")
    envelope_entry = next(
        entry for entry in incomplete["envelope"] if len(entry["realizations"]) > 1
    )
    removed_state_id = envelope_entry["realizations"].pop()["state_id"]
    key = (envelope_entry["cell_id"], envelope_entry["action_id"])
    nominal_entry = next(
        entry
        for entry in incomplete["nominal"]
        if (entry["cell_id"], entry["action_id"]) == key
    )
    nominal_entry["model"]["realization_count"] -= 1
    incomplete["concretizer_registry"] = [
        entry
        for entry in incomplete["concretizer_registry"]
        if not (
            entry["state_id"] == removed_state_id
            and entry["action_id"] == key[1]
        )
    ]
    with pytest.raises(ValueError, match="every active member"):
        PortableRAPM.from_payload(incomplete)

    inconsistent = built.model.to_dict()
    inconsistent.pop("model_id")
    feature = inconsistent["nominal"][0]["model"]["reward_features"][0]["value"]
    feature["numerator"] += feature["denominator"]
    with pytest.raises(ValueError, match="exact envelope average"):
        PortableRAPM.from_payload(inconsistent)


def test_portable_query_binds_goal_reward_normalizer_and_v0_risk_registry(
    lmb_portable,
) -> None:
    _, _, built, query, _ = lmb_portable
    portable_query = built.query_from_spec(query)
    document = portable_query.to_dict()

    assert document["goal_id"] == query.goal
    assert document["normalizer"] == {
        "numerator": query.normalizer.numerator,
        "denominator": query.normalizer.denominator,
    }
    assert document["normalizer_proof_id"] == query.normalizer_proof_id

    initial = tuple(
        (
            Fraction(item["probability"]["numerator"], item["probability"]["denominator"]),
            item["cell_id"],
        )
        for item in document["initial_distribution"]
    )
    raw_weights = tuple(
        (
            item["name"],
            Fraction(item["value"]["numerator"], item["value"]["denominator"]),
        )
        for item in document["reward_weights"]
    )
    with pytest.raises(ValueError, match="unknown goal"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            raw_weights,
            query.normalizer,
            query.normalizer_proof_id,
            "unregistered",
            query.delta,
        )
    with pytest.raises(ValueError, match="one of"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            raw_weights,
            query.normalizer,
            query.normalizer_proof_id,
            query.goal,
            Fraction(1, 3),
        )
    with pytest.raises(ValueError, match="unregistered normalizer proof"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            raw_weights,
            query.normalizer,
            "forged.normalizer.proof.v1",
            query.goal,
            query.delta,
        )
    with pytest.raises(ValueError, match="below its registered deterministic bound"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            raw_weights,
            Fraction(1, 100),
            query.normalizer_proof_id,
            query.goal,
            query.delta,
        )
    with pytest.raises(ValueError, match="do not match.*proof basis"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            (("match", Fraction(1)), ("terminal_clear", Fraction(0))),
            Fraction(2),
            "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
            query.goal,
            Fraction(0),
        )
    with pytest.raises(ValueError, match="do not match.*proof basis"):
        PortableQuery.from_cells(
            built.model,
            initial,
            query.horizon,
            (("match", Fraction(0)), ("terminal_clear", Fraction(1))),
            Fraction(2),
            "lmb.match_only.matches_le_n_over_3.v1",
            query.goal,
            query.delta,
        )


def test_portable_coverage_contract_rejects_resigned_boundary_weakening(
    lmb_portable,
) -> None:
    _, _, built, _, _ = lmb_portable
    payload = built.model.to_dict()
    payload.pop("model_id")
    payload["coverage"]["reuse_outside_coverage_forbidden"] = False
    payload["coverage_id"] = logical_id("coverage", payload["coverage"])
    with pytest.raises(ValueError, match="forbid reuse outside"):
        PortableRAPM.from_payload(payload)

    payload = built.model.to_dict()
    payload.pop("model_id")
    payload["coverage"]["external_ground_path"] = "/untrusted/coverage.json"
    payload["coverage_id"] = logical_id("coverage", payload["coverage"])
    with pytest.raises(ValueError, match="invalid field set"):
        PortableRAPM.from_payload(payload)


def test_portable_normalizer_rule_requires_complete_explicit_reward_basis(
    lmb_portable,
) -> None:
    _, _, built, _, _ = lmb_portable
    payload = built.model.to_dict()
    payload.pop("model_id")
    match_only = next(
        rule
        for rule in payload["normalizer_rules"]
        if rule["proof_id"] == "lmb.match_only.matches_le_n_over_3.v1"
    )
    match_only["reward_basis"] = [
        item for item in match_only["reward_basis"] if item["name"] == "match"
    ]
    with pytest.raises(ValueError, match="complete reward registry"):
        PortableRAPM.from_payload(payload)
