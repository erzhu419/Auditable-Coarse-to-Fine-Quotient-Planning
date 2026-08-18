from __future__ import annotations

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp import universal_mixture_three_domain_campaign_core_v58 as ground
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    exact_partial_factor_replay_v15,
    partial_factor_bit_codelength_stop_update_v15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
    synthesize_partial_factor_candidate_v15,
)


def test_v15_factor_projection_contains_programs_but_no_target_slots():
    library = V51_FACTOR_TEMPLATE_PROJECTION
    assert library["source_v51_verification_id"] == (
        "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
    )
    assert len(library["cross_schema_subprograms"]) == 3
    assert library["target_slot_inventory_supplied"] is False
    assert library["semantic_names_supplied"] is False


def test_v15_partial_factor_bindings_are_observation_derived_and_replay_exactly():
    config = v57.campaign_config_v57()
    adapter = ground.prior_ground._adapter("MAINTENANCE_CASCADE", 589_930, config)
    batches = list(ground.ground._witness_blind_depth_frontier(adapter))[:3]
    rows = tuple(row for batch in batches for row in batch)
    candidate = synthesize_partial_factor_candidate_v15(
        rows,
        adapter.catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=3,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=3,
    )
    document = candidate.public_document
    assert len(document["compiled_factor_assignments"]) >= 3
    assert document["unknown_residual_target_columns"]
    assert document["target_slot_inventory_supplied_by_prior"] is False
    assert document["target_bindings_derived_from_raw_observations"] is True
    assert document["complete_world_model_claimed"] is False
    assert document["planning_authority_present"] is False
    assert exact_partial_factor_replay_v15(
        candidate, rows, adapter.catalogue
    )["exact"]


def test_v15_partial_planner_uses_only_compiled_factor_projection():
    config = v57.campaign_config_v57()
    adapter = ground.prior_ground._adapter("MAINTENANCE_CASCADE", 589_930, config)
    batches = list(ground.ground._witness_blind_depth_frontier(adapter))[:21]
    rows = tuple(row for batch in batches for row in batch)
    candidate = synthesize_partial_factor_candidate_v15(
        tuple(row for batch in batches[:10] for row in batch),
        adapter.catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=10,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=3,
    )
    plan = plan_partial_factor_program_v15(
        candidate,
        rows,
        adapter.catalogue,
        adapter.encode(adapter.initial()),
        maximum_depth=12,
    )
    assert plan["action_keys"]
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["complete_world_model_claimed"] is False


def test_v15_partial_stop_uses_true_bits_and_separate_universal_evidence():
    config = v57.campaign_config_v57()
    adapter = ground.prior_ground._adapter("MAINTENANCE_CASCADE", 589_930, config)
    batches = list(ground.ground._witness_blind_depth_frontier(adapter))[:18]
    rows = tuple(row for batch in batches for row in batch)
    candidate = synthesize_partial_factor_candidate_v15(
        tuple(row for batch in batches[:10] for row in batch),
        adapter.catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=10,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=3,
    )
    stop = partial_factor_bit_codelength_stop_update_v15(
        candidate,
        rows,
        adapter.catalogue,
        candidate_epoch=0,
        invalidated_candidate_count=0,
        post_issuance_exact_prediction_success_count=8,
        global_alpha_denominator=20,
    )
    assert stop["heuristic_mdl_information_units_consumed"] is False
    assert stop["predictive_evidence_to_mdl_credit_consumed"] is False
    assert stop["unknown_residual_outputs_transmitted_or_claimed"] is False
    assert stop["partial_two_part_codelength_savings_bits"] >= 0
    assert stop["stopped"] is True


def test_v15_observation_graph_plan_checks_every_edge_with_compiled_program():
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
    plan = plan_partial_factor_observation_graph_v15(
        candidate, rows, adapter.catalogue, adapter.encode(adapter.initial())
    )
    assert plan["action_keys"]
    assert plan["compiled_factor_program_checked_each_abstract_edge"] is True
    assert plan["ground_transition_accessed_during_abstract_search"] is False
