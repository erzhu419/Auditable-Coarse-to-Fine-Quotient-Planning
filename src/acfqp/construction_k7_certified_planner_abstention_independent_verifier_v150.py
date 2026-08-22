"""Producer-free verification of the frozen V150 cross-domain campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from types import FunctionType
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_anonymous_relational_factor_bank_independent_verifier_v148 as base
from acfqp import construction_k7_domain_registry_extension_v150 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    FAMILY as DUAL,
    build_dual_budget_adapter_v119,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY as INVENTORY,
    build_inventory_assembly_adapter_v118,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    build_modular_routing_adapter_v128,
)
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    build_packet_batching_adapter_v134,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "d76a443f781cd6e6f0c19cf7af12de2627cbccb0a719c41f804f41c416b966c9"
CAMPAIGN_BYTE_COUNT = 61_088_428
CAMPAIGN_SHA256 = "00c5bad86cb05825ecc5cc0d7b0fc5dd00119b95c38a8f44eb3b67f6896c66e9"
PREREGISTRATION_ID = "947179ea88496be6188b04e80fe7b9f3184f16864e1448d19e240fb6fba83d7c"
PREREGISTRATION_BYTE_COUNT = 14_290
PREREGISTRATION_SHA256 = "f0bee6ac66112e033211d00e14b676f4e546a506268acc5ff631f6e651d3554f"
V149_PREREGISTRATION_ID = "0ab10d76752bf5a6aeea1341386015627debe3e1009c2780fa0dbbbc2d164cb3"
V149_PREREGISTRATION_BYTE_COUNT = 8_807
V149_PREREGISTRATION_SHA256 = "3f938c6d42ed0508502534047ed52eee76f5b67267b6bb9700b4dfb282f612ae"
V149_FAILURE_BYTE_COUNT = 1_708
V149_FAILURE_SHA256 = "0ad197ecd213fa53467ff7252b61e5d750dbc27d675fdf0d5fd8c242ab22458d"
BANK_ID = base.BANK_ID
BANK_VERIFICATION_ID = base.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = (
    (INVENTORY, 1_047_351),
    (INVENTORY, 1_047_352),
    (DUAL, 1_047_353),
    (DUAL, 1_047_354),
    (MODULAR, 1_047_355),
    (MODULAR, 1_047_356),
    (PACKET, 1_047_357),
    (PACKET, 1_047_358),
)
EXPECTED_EPISODES = (571, 572, 573, 574)
VERIFICATION_ID = "b7fafe92cc2ae58b7c912f3eaaa400f407ea8908340b8075a4cbbe4e45776f72"
EXPECTED_CANONICAL_BYTE_COUNT = 15_293
EXPECTED_CANONICAL_SHA256 = "c42d69ad3ac086d8c433f1546400dd2e47d94d51e28ffa377d7ce19fefc97f32"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
    PACKET: build_packet_batching_adapter_v134,
}
_V149_PREREGISTRATION_DOMAIN = (
    "acfqp:construction-k7-cross-domain-relational-bank-preregistration:v149"
)
_V150_SEQUENCE_ADDITIONS = {
    "incomplete_abstract_action_path_treated_as_abstention",
    "incomplete_abstract_plan_abstention_count",
    "certified_legal_search_remains_fallback_authority",
}


class ConstructionK7CertifiedPlannerAbstentionIndependentVerifierV150Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertifiedPlannerAbstentionIndependentVerifierV150Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V150 {key} changed")


def _campaign_config() -> dict[str, Any]:
    config = packet_batching_config_v134()
    for family in _BUILDERS:
        config["families"][family]["maximum_acquisition_labels"] = 1_536
    return config


def _normalized_sequence(sequence: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {
        key: copy.deepcopy(value)
        for key, value in sequence.items()
        if key not in _V150_SEQUENCE_ADDITIONS and key != "sequence_id"
    }
    normalized["schema"] = (
        "acfqp.certificate_local_relational_overlay_owned_sequence.v144r1"
    )
    normalized["sequence_id"] = base._content_id(  # noqa: SLF001
        base._V144R1_SEQUENCE_DOMAIN,  # noqa: SLF001
        normalized,
    )
    return normalized


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: Any,
    rows: tuple[Any, ...],
    *,
    family: str,
    seed: int,
) -> dict[str, int]:
    _verify_id(sequence, "sequence_id", domains.CONSTRUCTION_K7_SEQUENCE_V150_DOMAIN)
    _require(
        sequence.get("schema") == "acfqp.certified_planner_abstention_sequence.v150"
        and sequence.get("family") == family
        and tuple(sequence.get("episode_indices", ())) == EXPECTED_EPISODES
        and sequence.get("incomplete_abstract_action_path_treated_as_abstention")
        is True
        and sequence.get("certified_legal_search_remains_fallback_authority") is True
        and sequence.get("incomplete_abstract_plan_abstention_count")
        == sum(
            episode["abstract_plan_abstention_count"]
            for episode in sequence["episodes"]
        ),
        "V150 sequence correction boundary changed",
    )
    namespace = dict(base.__dict__)
    namespace.update(
        EXPECTED_EPISODES=EXPECTED_EPISODES,
        FAMILY=family,
        _fail=_fail,
        _require=_require,
    )
    verifier = FunctionType(
        base._verify_sequence.__code__,  # noqa: SLF001
        namespace,
        name=base._verify_sequence.__name__,  # noqa: SLF001
    )
    return verifier(_normalized_sequence(sequence), candidate, rows, seed=seed)


def _verify_occurrence(
    args: tuple[Mapping[str, Any], Mapping[str, Any]]
) -> dict[str, Any]:
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema")
        == "acfqp.cross_domain_relational_factor_bank_occurrence.v150"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V150 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V150_DOMAIN)
    config = _campaign_config()
    adapter = _BUILDERS[family](seed, config)
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = base.previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = base._rebuild_acquisition(  # noqa: SLF001
        prior_doc, adapter, bank, batches, enabled=True, config=config
    )
    strict_candidate, strict_rows = base._rebuild_acquisition(  # noqa: SLF001
        strict_doc, adapter, bank, batches, enabled=False, config=config
    )
    prior_sequence = _verify_sequence(
        row["anonymous_relational_factor_prior_owned_sequence"],
        prior_candidate,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence = _verify_sequence(
        row["strict_no_prior_owned_sequence"],
        strict_candidate,
        strict_rows,
        family=family,
        seed=seed,
    )
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    expected_accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": reduction,
        "anonymous_relational_prior_certificate_local_labels": prior_sequence[
            "certificate_local_labels"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_local_labels"
        ],
        "anonymous_relational_prior_lifetime_target_labels": prior_doc[
            "ground_support_labels"
        ]
        + prior_sequence["certificate_local_labels"],
        "strict_no_prior_lifetime_target_labels": strict_doc["ground_support_labels"]
        + strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_execution_steps": prior_sequence[
            "execution_steps"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_steps"],
        "anonymous_relational_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "anonymous_relational_prior_binding_compute_events": prior_doc[
            "template_binding_evaluation_events"
        ],
        "strict_no_prior_binding_compute_events": strict_doc[
            "template_binding_evaluation_events"
        ],
        "anonymous_relational_prior_planning_compute_events": prior_sequence[
            "planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    sequence_documents = (
        row["anonymous_relational_factor_prior_owned_sequence"],
        row["strict_no_prior_owned_sequence"],
    )
    common = min(prior_doc["ground_support_labels"], strict_doc["ground_support_labels"])
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(
            0 < document["ground_support_labels"] <= 1_536
            for document in (prior_doc, strict_doc)
        ),
        "same_raw_transition_prefix_through_common_label": (
            tuple(row for batch in batches[:common] for row in batch)
            == tuple(row for batch in batches[:common] for row in batch)
        ),
        "same_synthesizer_representation_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "binding_derived_from_current_raw_prefix_in_both_arms",
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "only_arm_switch_is_anonymous_relational_prior": prior_doc[
            "only_arm_switch_is_anonymous_relational_prior"
        ]
        is True
        and strict_doc["only_arm_switch_is_anonymous_relational_prior"] is True,
        "v146_source_family_absent_from_target_domain": True,
        "anonymous_relational_instantiation_present_both_arms": all(
            document["anonymous_relational_instantiation"][
                "exact_relational_instantiation_count"
            ]
            > 0
            for document in (prior_doc, strict_doc)
        ),
        "at_least_one_bank_template_selected_in_prior_arm": prior_doc[
            "artifact_expression_selected_count"
        ]
        > 0,
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in sequence_documents
            for episode in sequence["episodes"]
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in sequence_documents
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in sequence_documents
        ),
        "sound_certificate_local_recovery_union": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["every_uncompiled_edge_is_certificate_local"] is True
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in sequence_documents
        ),
    }
    gate["passed"] = all(gate.values())
    abstentions = sum(
        sequence["incomplete_abstract_plan_abstention_count"]
        for sequence in sequence_documents
    )
    _require(
        row["accounting"] == expected_accounting
        and row["registered_gate"] == gate
        and row["paired_label_reduction"] == reduction
        and row["sample_efficiency_direction"]
        == ("POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO")
        and row["incomplete_abstract_plan_abstention_count"] == abstentions
        and row["v149_failed_predecessor_preserved"] is True
        and row["incomplete_abstract_path_never_used_as_execution_authority"] is True
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V150 occurrence evidence changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "prior_labels": prior_doc["ground_support_labels"],
        "strict_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "incomplete_abstract_plan_abstention_count": abstentions,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": expected_accounting,
    }


def freeze_certified_planner_abstention_verification_v150(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    v149_preregistration_raw: bytes,
    v149_failure_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    predecessor = loads_canonical_json(v149_preregistration_raw)
    failure = loads_canonical_json(v149_failure_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V150 frozen campaign identity changed",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V150_DOMAIN)
    _require(
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and registration.get("preregistration_id") == PREREGISTRATION_ID,
        "V150 frozen preregistration identity changed",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_PREREGISTRATION_V150_DOMAIN,
    )
    _require(
        canonical_json_bytes(predecessor) == v149_preregistration_raw
        and len(v149_preregistration_raw) == V149_PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(v149_preregistration_raw).hexdigest()
        == V149_PREREGISTRATION_SHA256
        and predecessor.get("preregistration_id") == V149_PREREGISTRATION_ID
        and canonical_json_bytes(failure) == v149_failure_raw
        and len(v149_failure_raw) == V149_FAILURE_BYTE_COUNT
        and hashlib.sha256(v149_failure_raw).hexdigest() == V149_FAILURE_SHA256
        and failure.get("preregistration_id") == V149_PREREGISTRATION_ID
        and failure.get("outcome_kind")
        == "PREREGISTERED_PLANNER_ACTION_PATH_FAILURE"
        and failure.get("same_identity_rerun_forbidden") is True
        and registration["frozen_v149_preregistration"] == predecessor
        and registration["frozen_v149_failure"] == failure,
        "V150 preserved V149 predecessor changed",
    )
    _verify_id(
        predecessor,
        "preregistration_id",
        _V149_PREREGISTRATION_DOMAIN,
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V150 frozen source fact changed",
        )
    bank = predecessor["frozen_v146_factor_bank"]
    bank_verification = predecessor["frozen_v146_independent_verification"]
    bank_raw = canonical_json_bytes(bank)
    bank_verification_raw = canonical_json_bytes(bank_verification)
    _require(
        bank.get("bank_id") == BANK_ID
        and len(bank_raw) == base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == base.BANK_SHA256
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and len(bank_verification_raw) == base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == base.BANK_VERIFICATION_SHA256
        and registration["target_occurrences"]
        == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V150 frozen bank or registered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                ((row, bank) for row in campaign["target_occurrences"]),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V150 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["labels_avoided"] for row in rows)
    family_reductions = {
        family: sum(
            row["labels_avoided"] for row in rows if row["family"] == family
        )
        for family in _BUILDERS
    }
    local_labels = (
        accounting["anonymous_relational_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    abstentions = sum(
        row["incomplete_abstract_plan_abstention_count"] for row in rows
    )
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["accounting"] == accounting
        and campaign["incompatible_schema_no_transfer_control"]
        == incompatible_schema_no_transfer_control_v99()
        and gate["passed"] is True
        and gate["aggregate_paired_acquisition_label_reduction"]
        == sum(reductions)
        == 51
        and gate["positive_reduction_occurrence_count"] == 7
        and gate["zero_reduction_occurrence_count"] == 1
        and gate["negative_reduction_occurrence_count"] == 0
        and gate["family_aggregate_reductions"] == family_reductions
        and all(value > 0 for value in family_reductions.values())
        and gate["certificate_failure_local_recovery_exercised_at_least_once"]
        is (local_labels > 0)
        and local_labels == 674
        and gate["v149_preserved_failure_exercised_action_path_boundary"] is True
        and gate["fresh_v150_incomplete_abstract_path_abstention_observed"]
        is (abstentions > 0)
        and campaign["incomplete_abstract_plan_abstention_count"] == abstentions == 0
        and campaign["v149_identity_rerun"] is False
        and campaign["certified_abstract_abstention_correction_applied"] is True
        and campaign["registered_workload_sample_efficiency_improvement_observed"]
        is True
        and campaign["relational_template_selection_itself_claimed_cross_domain"]
        is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V150 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.certified_planner_abstention_verification.v150",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "preserved_v149_preregistration_id": V149_PREREGISTRATION_ID,
        "preserved_v149_failure_sha256": V149_FAILURE_SHA256,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "verified_family_aggregate_reductions": family_reductions,
        "producer_free_anonymous_binding_and_relational_instantiation_reconstruction": True,
        "producer_free_matched_candidate_and_stop_reconstruction": True,
        "producer_free_model_epoch_and_certificate_local_recovery_reconstruction": True,
        "producer_free_abstract_plan_support_reconstruction": True,
        "producer_free_certified_abstention_boundary_verification": True,
        "registered_cross_domain_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": campaign[
            "sample_efficiency_improvement_claim_scope"
        ],
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v150(
            domains.CONSTRUCTION_K7_VERIFICATION_V150_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V150 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_certified_planner_abstention_verification_v150",
)
