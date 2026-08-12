from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_catalogue_query_router_v1 as subject
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_heldout_cross_structural_campaign_v1 import (
    child_campaigns,
)


@pytest.fixture(scope="module")
def catalogue(child_campaigns):
    return catalogue_v1.build_heldout_reusable_model_catalogue_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
    )


def _occurrence(label: str) -> str:
    return hashlib.sha256(f"heldout-catalogue-occurrence:{label}".encode()).hexdigest()


def test_domains_and_public_surface_are_narrow() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutCatalogueQueryRouterV1Error",
        "HeldoutCatalogueAbstractPlanV1",
        "HeldoutCatalogueConstructionRequestV1",
        "HeldoutCatalogueQueryResultV1",
        "HeldoutCatalogueQueryV1",
        "LOCAL_DOMAINS",
        "run_heldout_catalogue_query_v1",
        "verify_heldout_catalogue_query_result_v1",
    }
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("checkpoint_recertification" in name for name in imported)
    assert not any("ground" in name or "exact_evaluation" in name for name in imported)


@pytest.mark.parametrize(
    ("context_key", "family"),
    (("opaque_graph_w5_v0", "W5"), ("opaque_graph_k6_v0", "K6")),
)
def test_exact_hit_forms_one_fresh_multistep_plan_with_zero_ground(
    catalogue,
    child_campaigns,
    context_key: str,
    family: str,
) -> None:
    result = subject.run_heldout_catalogue_query_v1(
        catalogue,
        observer.public_context_by_key_v1(context_key),
        logical_occurrence_id=_occurrence(f"hit-{family}"),
        occurrence_ordinal=7,
        selected_reuse_result_bytes=child_campaigns[family]["reuse_bytes"],
    )
    document = result.to_document()
    assert document["routing_outcome"] == "ABSTRACT_PLAN_CERTIFIED"
    assert document["abstract_planner_invocations"] == 1
    assert document["model_construction_invocations"] == 0
    assert document["observer_call_count"] == 0
    assert document["ground_draw_count"] == 0
    assert document["ground_solver_invocations"] == 0
    assert document["cross_structural_model_transfer_attempted"] is False
    assert document["plan"]["multi_step_plan_formed_in_selected_abstract_model"] is True
    assert document["plan"]["conditional_statistical_plan_certificate_issued"] is True
    assert document["plan"]["formal_exact_iid_plan_certificate"] is False
    subject.verify_heldout_catalogue_query_result_v1(
        result,
        selected_reuse_result_bytes=child_campaigns[family]["reuse_bytes"],
    )


def test_operational_hit_invokes_planner_exactly_once_and_never_observer(
    catalogue,
    child_campaigns,
    monkeypatch,
) -> None:
    calls = 0
    actual_solver = robust.solve_quotient_robust_h2_v1

    def counted_solver(*args, **kwargs):
        nonlocal calls
        calls += 1
        return actual_solver(*args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("catalogue hit touched observer or ground path")

    monkeypatch.setattr(robust, "solve_quotient_robust_h2_v1", counted_solver)
    monkeypatch.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    result = subject.run_heldout_catalogue_query_v1(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("single-plan"),
        occurrence_ordinal=8,
        selected_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
    )
    assert result.plan is not None
    assert calls == 1


def test_nearby_structure_miss_is_no_access_construction_request(
    catalogue,
    monkeypatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("MODEL_MISS parsed a model or invoked a planner")

    monkeypatch.setattr(
        robust, "replay_partial_support_interval_model_bytes_v1", forbidden
    )
    monkeypatch.setattr(robust, "solve_quotient_robust_h2_v1", forbidden)
    monkeypatch.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    result = subject.run_heldout_catalogue_query_v1(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0"),
        logical_occurrence_id=_occurrence("model-miss"),
        occurrence_ordinal=9,
        selected_reuse_result_bytes=None,
    )
    document = result.to_document()
    request = document["construction_request"]
    assert document["routing_outcome"] == "CONSTRUCTION_REQUIRED"
    assert document["selected_quotient_model_id"] is None
    assert document["abstract_planner_invocations"] == 0
    assert request["activation_state"] == "PREPARED_NO_ACCESS"
    assert request["reason"] == "MODEL_MISS_NO_REGISTERED_WORLD_MODEL"
    assert request["ground_access_authorized_here"] is False
    assert request["next_required_action"] == (
        "ENTER_OBSERVATION_DRIVEN_CONSTRUCTION_AND_CERTIFICATE_PIPELINE"
    )
    subject.verify_heldout_catalogue_query_result_v1(
        result, selected_reuse_result_bytes=None
    )


def test_model_miss_rejects_nearby_model_bytes(catalogue, child_campaigns) -> None:
    with pytest.raises(
        subject.ConstructionK7HeldoutCatalogueQueryRouterV1Error,
        match="must not receive nearby model bytes",
    ):
        subject.run_heldout_catalogue_query_v1(
            catalogue,
            observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0"),
            logical_occurrence_id=_occurrence("miss-transfer"),
            occurrence_ordinal=10,
            selected_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        )


def test_exact_hit_rejects_crossed_family_bytes(catalogue, child_campaigns) -> None:
    with pytest.raises(
        subject.ConstructionK7HeldoutCatalogueQueryRouterV1Error,
        match="catalogued immutable source",
    ):
        subject.run_heldout_catalogue_query_v1(
            catalogue,
            observer.public_context_by_key_v1("opaque_graph_w5_v0"),
            logical_occurrence_id=_occurrence("crossed-family"),
            occurrence_ordinal=11,
            selected_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        )


def test_query_identity_is_fresh_while_model_identity_is_reused(
    catalogue,
    child_campaigns,
) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_k6_v0")
    first = subject.run_heldout_catalogue_query_v1(
        catalogue,
        context,
        logical_occurrence_id=_occurrence("fresh-a"),
        occurrence_ordinal=12,
        selected_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
    )
    second = subject.run_heldout_catalogue_query_v1(
        catalogue,
        context,
        logical_occurrence_id=_occurrence("fresh-b"),
        occurrence_ordinal=13,
        selected_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
    )
    assert first.query.query_id != second.query.query_id
    assert first.plan is not None and second.plan is not None
    assert first.plan.audit.model_id == second.plan.audit.model_id
    assert first.plan.audit.audit_id == second.plan.audit.audit_id
    assert first.plan.plan_id != second.plan.plan_id


def test_owner_bound_result_mutation_is_rejected(catalogue, child_campaigns) -> None:
    result = subject.run_heldout_catalogue_query_v1(
        catalogue,
        observer.public_context_by_key_v1("opaque_graph_w5_v0"),
        logical_occurrence_id=_occurrence("tamper"),
        occurrence_ordinal=14,
        selected_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
    )
    original = result.query.selection_outcome
    try:
        object.__setattr__(result.query, "selection_outcome", "MODEL_MISS")
        with pytest.raises(subject.ConstructionK7HeldoutCatalogueQueryRouterV1Error):
            subject.verify_heldout_catalogue_query_result_v1(
                result,
                selected_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            )
    finally:
        object.__setattr__(result.query, "selection_outcome", original)
