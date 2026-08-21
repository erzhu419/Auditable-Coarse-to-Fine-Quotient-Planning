from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp import universal_mixture_three_domain_campaign_core_v58 as ground
from acfqp.generic_abstract_execution_receipt_v103 import (
    build_abstract_execution_receipt_v103,
)
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_actual_quotient_execution_receipt_v105 import (
    GenericActualQuotientExecutionReceiptV105Error,
    build_actual_quotient_execution_receipt_v105,
    verify_actual_quotient_execution_receipt_v105,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    GenericObservationQuotientGraphV105Error,
    compile_observation_quotient_graph_v105,
    plan_observation_quotient_graph_v105,
    verify_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)


def _fixture():
    config = v57.campaign_config_v57()
    adapter = ground.prior_ground._adapter("COUPLED_EXCHANGE", 589_920, config)
    batches = list(ground.ground._witness_blind_depth_frontier(adapter))[:67]
    rows = tuple(row for batch in batches for row in batch)
    candidate = synthesize_partial_factor_candidate_v15(
        tuple(row for batch in batches[:17] for row in batch),
        adapter.catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=17,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=3,
    )
    return adapter, candidate, rows


def test_v105_compiles_projected_edges_and_plans_without_residual_access():
    adapter, candidate, rows = _fixture()
    model = verify_observation_quotient_graph_v105(
        compile_observation_quotient_graph_v105(
            candidate, rows, adapter.catalogue
        ),
        candidate,
        rows,
        adapter.catalogue,
    )
    plan = plan_observation_quotient_graph_v105(
        model,
        candidate,
        rows,
        adapter.catalogue,
        adapter.encode(adapter.initial()),
        maximum_depth=12,
    )
    assert model["projected_edge_count"] > 0
    assert model["quotiented_residual_target_columns"]
    assert model["all_projected_edges_checked_by_compiled_factor_program"] is True
    assert plan["initial_action_key"] in {
        action.key for action in adapter.catalogue
    }
    assert plan["residual_coordinates_read_during_search"] is False
    assert plan["query_local_exact_overlay_remains_only_safety_authority"] is True


def test_v105_quotient_graph_rejects_rewritten_projected_edge():
    adapter, candidate, rows = _fixture()
    model = compile_observation_quotient_graph_v105(
        candidate, rows, adapter.catalogue
    )
    forged = copy.deepcopy(model)
    forged["projected_edge_rows"][0]["action_key"] += 1000
    with pytest.raises(GenericObservationQuotientGraphV105Error):
        verify_observation_quotient_graph_v105(
            forged, candidate, rows, adapter.catalogue
        )


def test_v105_receipt_binds_plan_that_entered_real_action_order():
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(7,),
        partial_proposal=(7,),
        legal_action_keys=(7, 8),
    )
    base = build_abstract_execution_receipt_v103(
        decision_index=0,
        raw_state=(1, 2, 3),
        chosen_action_key=7,
        abstract_proposal=(7,),
        partial_proposal=(7,),
        legal_action_keys=(7, 8),
        shield_receipt=shield,
    )
    plan = {
        "schema": "acfqp.generic_observation_quotient_plan.v105",
        "quotient_graph_id": "1" * 64,
        "partial_candidate_id": "2" * 64,
        "planning_source": "OBSERVATION_QUOTIENT_GRAPH",
        "initial_action_key": 7,
        "projected_action_path": [7],
        "abstract_support_branch_evaluations": 1,
        "embedded_projected_plan": {},
        "residual_coordinates_read_during_search": False,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    from acfqp.phase3e_ids import canonical_json_bytes
    import hashlib

    plan["quotient_plan_id"] = hashlib.sha256(
        b"acfqp:generic-observation-quotient-plan:v105\x00"
        + canonical_json_bytes(plan)
    ).hexdigest()
    plan["agreement_shield_receipt"] = shield
    plan[
        "legacy_two_channel_shield_carries_one_identical_quotient_proposal"
    ] = True
    wrapper = {"raw_state": [1, 2, 3], "abstract_plan": plan}
    receipt = verify_actual_quotient_execution_receipt_v105(
        build_actual_quotient_execution_receipt_v105(
            episode_index=41,
            base_execution_receipt=base,
            quotient_plan_receipt=wrapper,
        )
    )
    assert receipt["quotient_proposal_admitted_to_real_action_order"] is True
    assert receipt["chosen_action_matches_admitted_quotient_proposal"] is True
    forged = copy.deepcopy(receipt)
    forged["quotient_plan_receipt"]["abstract_plan"]["initial_action_key"] = 8
    with pytest.raises(GenericActualQuotientExecutionReceiptV105Error):
        verify_actual_quotient_execution_receipt_v105(forged)
