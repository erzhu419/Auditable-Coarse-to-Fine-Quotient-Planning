"""Producer-free verifier for the complete V170 abstract-plan taxonomy."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v168 as domains_v168
from acfqp import construction_k7_domain_registry_extension_v170 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CONTRACT_ID = "bb751f90d592f289cfcf1c00041a6b1f0579dc95c93a01b76a0598f0c2a0ae66"
CONTRACT_BYTE_COUNT = 2_820
CONTRACT_SHA256 = "f527daa87f4389bfedd501ccb1eba21066413457bef1904abbaa5a7fec751575"
V168_CAMPAIGN_ID = "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
V168_CAMPAIGN_BYTE_COUNT = 25_586_483
V168_CAMPAIGN_SHA256 = "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5"
AUDIT_ID = "0372043e8d6a3277070488777e3f0dc5f33702abb2b72a8fcabc12a60dd35944"
AUDIT_BYTE_COUNT = 1_193_174
AUDIT_SHA256 = "24e90f4af2da248de54c233931f7d6aefcc89eeb3b1c3b6a8ac3fe5cd81599a2"
V106_PLAN_DOMAIN = "acfqp:generic-legality-conditioned-quotient-plan:v106"
TAXONOMY = {
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "OBSERVATION_QUOTIENT_GRAPH",
    ): "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
    ): "DIRECT_COMPILED_PROGRAM_ORDER",
    (
        "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
    ): "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    (
        "acfqp.generic_projected_program_memo_plan.v115",
        "COMPILED_FACTOR_PROGRAM_MEMOIZED",
    ): "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
}
VERIFICATION_ID = "f9b7570d565cb160d80aafadd9d4bcf49abdcb7879d782c597fd9f955cfa4217"
EXPECTED_CANONICAL_BYTE_COUNT = 1_537
EXPECTED_CANONICAL_SHA256 = (
    "a4bcb3aff4f465a66c6dabd06c6427871d6418e027258d6fe9bde0da2a0541c3"
)


class ConstructionK7CompleteAbstractPlanReceiptTaxonomyIndependentVerifierV170Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CompleteAbstractPlanReceiptTaxonomyIndependentVerifierV170Error(
        message
    )


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _plan_id(plan: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in plan.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    if plan["schema"] == "acfqp.generic_legality_conditioned_quotient_plan.v106":
        return _content_id(V106_PLAN_DOMAIN, payload)
    if plan["schema"] == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109":
        return domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
    if plan["schema"] == "acfqp.generic_projected_program_memo_plan.v115":
        return domains_v115.extension_content_id_v115(
            domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        )
    _fail("V170 independent verifier found unknown plan schema")


def _typed_expected(occurrence, arm, sequence, episode, ordinal, wrapper):
    if type(wrapper) is not dict or set(wrapper) != {"raw_state", "abstract_plan"}:
        _fail("V170 independent wrapper shape changed")
    plan = wrapper["abstract_plan"]
    raw_state = wrapper["raw_state"]
    if type(plan) is not dict or type(raw_state) is not list:
        _fail("V170 independent wrapper type changed")
    typed_source = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if typed_source is None:
        _fail("V170 independent verifier found unknown planning source")
    identity = _plan_id(plan)
    if not (
        plan.get("legality_conditioned_quotient_plan_id") == identity
        and plan.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and plan.get("complete_ground_world_model_claimed") is False
        and type(plan.get("initial_action_key")) is int
        and plan["initial_action_key"]
        in plan.get("exact_legal_action_keys_at_initial_state", [])
        and type(plan.get("projected_action_path")) is list
        and plan["projected_action_path"]
        and plan["projected_action_path"][0] == plan["initial_action_key"]
    ):
        _fail("V170 independent plan identity or safety boundary changed")
    ground_values = [
        plan[name]
        for name in (
            "ground_transition_accessed_during_abstract_search",
            "ground_transition_accessed_during_dependency_revalidation",
            "ground_transition_accessed_during_program_memo_reuse",
        )
        if name in plan
    ]
    if ground_values != [False]:
        _fail("V170 independent ground-transition boundary changed")
    payload = {
        "schema": "acfqp.typed_abstract_plan_receipt.v170",
        "source_v168_occurrence_id": occurrence["occurrence_id"],
        "source_v168_sequence_id": sequence["sequence_id"],
        "target_family": occurrence["target_family"],
        "seed": occurrence["seed"],
        "arm": arm,
        "episode_index": episode["episode_index"],
        "plan_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": typed_source,
        "source_plan_id": identity,
        "source_wrapper_sha256": _sha(wrapper),
        "raw_state_sha256": _sha(raw_state),
        "initial_action_key": plan["initial_action_key"],
        "projected_action_count": len(plan["projected_action_path"]),
        "ground_transition_accessed_during_abstract_reasoning": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
        "typed_receipt_changes_planning_or_execution": False,
        "typed_receipt_is_safety_authority": False,
    }
    return {
        **payload,
        "typed_plan_receipt_id": domains.extension_content_id_v170(
            domains.CONSTRUCTION_K7_TYPED_PLAN_RECEIPT_V170_DOMAIN, payload
        ),
    }


def _join_expected(
    occurrence, arm, sequence, episode, execution, typed_receipts, wrappers
):
    if not (
        type(execution) is dict
        and execution.get("schema")
        == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
        and execution.get("receipt_is_observation_not_safety_authority") is True
        and execution.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and type(execution.get("quotient_plan_receipt")) is dict
    ):
        _fail("V170 independent V109 execution boundary changed")
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    if execution.get("actual_dependency_revalidated_execution_receipt_id") != source_id:
        _fail("V170 independent V109 execution identity changed")
    target = canonical_json_bytes(execution["quotient_plan_receipt"])
    matches = [
        index
        for index, wrapper in enumerate(wrappers)
        if canonical_json_bytes(wrapper) == target
    ]
    if len(matches) != 1:
        _fail("V170 independent execution join is not unique")
    ordinal = matches[0]
    typed = typed_receipts[ordinal]
    plan = execution["quotient_plan_receipt"]["abstract_plan"]
    if not (
        execution["episode_index"] == episode["episode_index"]
        and execution["raw_state"] == execution["quotient_plan_receipt"]["raw_state"]
        and execution["quotient_plan_id"] == plan["legality_conditioned_quotient_plan_id"]
        and execution["quotient_proposed_action_key"] == plan["initial_action_key"]
        and execution["chosen_action_key"] in execution["legal_action_keys"]
    ):
        _fail("V170 independent plan/execution join changed")
    payload = {
        "schema": "acfqp.typed_plan_execution_join_receipt.v170",
        "source_v168_occurrence_id": occurrence["occurrence_id"],
        "source_v168_sequence_id": sequence["sequence_id"],
        "target_family": occurrence["target_family"],
        "seed": occurrence["seed"],
        "arm": arm,
        "episode_index": episode["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "typed_plan_receipt_id": typed["typed_plan_receipt_id"],
        "source_plan_ordinal": ordinal,
        "typed_plan_source": typed["typed_plan_source"],
        "raw_state_sha256": typed["raw_state_sha256"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "quotient_proposal_admitted_to_real_action_order": execution[
            "quotient_proposal_admitted_to_real_action_order"
        ],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "actual_action_ordering_source": execution["actual_action_ordering_source"],
        "source_receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "typed_join_changes_planning_or_execution": False,
        "typed_join_is_safety_authority": False,
    }
    return {
        **payload,
        "execution_join_receipt_id": domains.extension_content_id_v170(
            domains.CONSTRUCTION_K7_EXECUTION_JOIN_RECEIPT_V170_DOMAIN, payload
        ),
    }


def _verify_episode_row(actual, occurrence, arm, sequence, episode):
    wrappers = episode["abstract_plan_receipts"]
    typed = [
        _typed_expected(occurrence, arm, sequence, episode, ordinal, wrapper)
        for ordinal, wrapper in enumerate(wrappers)
    ]
    if len({row["source_wrapper_sha256"] for row in typed}) != len(typed):
        _fail("V170 independent duplicate plan instance")
    joins = [
        _join_expected(
            occurrence,
            arm,
            sequence,
            episode,
            execution,
            typed,
            wrappers,
        )
        for execution in episode["actual_legality_conditioned_execution_receipts"]
    ]
    histogram = {
        source: sum(row["typed_plan_source"] == source for row in typed)
        for source in TAXONOMY.values()
    }
    expected = {
        "schema": "acfqp.complete_abstract_plan_receipt_episode.v170",
        "source_v168_occurrence_id": occurrence["occurrence_id"],
        "source_v168_sequence_id": sequence["sequence_id"],
        "target_family": occurrence["target_family"],
        "seed": occurrence["seed"],
        "arm": arm,
        "episode_index": episode["episode_index"],
        "typed_plan_receipts": typed,
        "typed_plan_receipt_count": len(typed),
        "typed_plan_source_histogram": histogram,
        "execution_join_receipts": joins,
        "execution_join_receipt_count": len(joins),
        "execution_step_count": episode["execution_steps"],
        "untyped_abstract_plan_receipt_count": 0,
        "unjoined_executed_action_count": 0,
        "all_abstract_plan_instances_typed": len(typed) == len(wrappers),
        "all_executed_actions_joined": len(joins) == episode["execution_steps"],
    }
    if actual != expected:
        _fail("V170 independent episode reconstruction changed")
    return typed, joins


def freeze_complete_abstract_plan_receipt_taxonomy_verification_v170(
    audit_raw: bytes,
    contract_raw: bytes,
    v168_campaign_raw: bytes,
) -> bytes:
    audit = loads_canonical_json(audit_raw)
    contract = loads_canonical_json(contract_raw)
    campaign = loads_canonical_json(v168_campaign_raw)
    if not (
        canonical_json_bytes(audit) == audit_raw
        and len(audit_raw) == AUDIT_BYTE_COUNT
        and hashlib.sha256(audit_raw).hexdigest() == AUDIT_SHA256
        and audit.get("audit_id") == AUDIT_ID
    ):
        _fail("V170 frozen audit changed")
    if not (
        canonical_json_bytes(contract) == contract_raw
        and len(contract_raw) == CONTRACT_BYTE_COUNT
        and hashlib.sha256(contract_raw).hexdigest() == CONTRACT_SHA256
        and contract.get("contract_id") == CONTRACT_ID
    ):
        _fail("V170 frozen contract changed")
    if not (
        canonical_json_bytes(campaign) == v168_campaign_raw
        and len(v168_campaign_raw) == V168_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v168_campaign_raw).hexdigest() == V168_CAMPAIGN_SHA256
        and campaign.get("campaign_id") == V168_CAMPAIGN_ID
        and campaign.get("registered_gate", {}).get("passed") is True
    ):
        _fail("V170 frozen campaign changed")
    actual_rows = audit.get("episode_rows")
    if type(actual_rows) is not list:
        _fail("V170 audit episode inventory changed")
    row_index = 0
    typed_ids = []
    join_ids = []
    histogram = {source: 0 for source in TAXONOMY.values()}
    for occurrence in campaign["target_occurrences"]:
        for arm, key in (
            ("ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON", "progressive_prior_sequence"),
            ("STRICT_NO_PRIOR", "progressive_strict_sequence"),
        ):
            sequence = occurrence[key]
            sequence_payload = {
                name: value for name, value in sequence.items() if name != "sequence_id"
            }
            if sequence.get("sequence_id") != domains_v168.extension_content_id_v168(
                domains_v168.CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN, sequence_payload
            ):
                _fail("V170 independent source sequence changed")
            flat = [
                receipt
                for episode in sequence["episodes"]
                for receipt in episode["actual_legality_conditioned_execution_receipts"]
            ]
            if flat != sequence["all_actual_legality_conditioned_execution_receipts"]:
                _fail("V170 independent sequence execution join changed")
            for episode in sequence["episodes"]:
                if row_index >= len(actual_rows):
                    _fail("V170 audit omitted episode row")
                typed, joins = _verify_episode_row(
                    actual_rows[row_index], occurrence, arm, sequence, episode
                )
                row_index += 1
                typed_ids.extend(row["typed_plan_receipt_id"] for row in typed)
                join_ids.extend(row["execution_join_receipt_id"] for row in joins)
                for row in typed:
                    histogram[row["typed_plan_source"]] += 1
    if row_index != len(actual_rows):
        _fail("V170 audit added episode row")
    root_checks = {
        "episode_row_count": 16,
        "typed_plan_receipt_count": len(typed_ids),
        "execution_join_receipt_count": len(join_ids),
        "typed_plan_source_histogram": histogram,
        "untyped_abstract_plan_receipt_count": 0,
        "unjoined_executed_action_count": 0,
        "post_hoc_taxonomy_not_new_target_campaign": True,
        "favorable_window_selected": False,
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(audit.get(key) != value for key, value in root_checks.items()):
        _fail("V170 audit root semantics changed")
    if not (
        audit.get("schema")
        == "acfqp.complete_abstract_plan_receipt_taxonomy_audit.v170"
        and audit.get("contract_id") == CONTRACT_ID
        and audit.get("source_v168_campaign_id") == V168_CAMPAIGN_ID
        and audit.get("registered_gate", {}).get("passed") is True
        and audit.get("audit_id")
        == domains.extension_content_id_v170(
            domains.CONSTRUCTION_K7_AUDIT_V170_DOMAIN,
            {key: value for key, value in audit.items() if key != "audit_id"},
        )
    ):
        _fail("V170 audit identity or gate changed")
    payload = {
        "schema": "acfqp.complete_abstract_plan_receipt_taxonomy_verification.v170",
        "audit_id": AUDIT_ID,
        "contract_id": CONTRACT_ID,
        "source_v168_campaign_id": V168_CAMPAIGN_ID,
        "verified_episode_row_count": row_index,
        "verified_typed_plan_receipt_count": len(typed_ids),
        "verified_execution_join_receipt_count": len(join_ids),
        "verified_typed_plan_source_histogram": histogram,
        "typed_plan_receipt_id_sequence_sha256": _sha(typed_ids),
        "execution_join_receipt_id_sequence_sha256": _sha(join_ids),
        "producer_free_every_plan_instance_reconstructed": True,
        "producer_free_every_execution_join_reconstructed": True,
        "unknown_plan_source_count": 0,
        "unjoined_executed_action_count": 0,
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
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
        "verification_id": domains.extension_content_id_v170(
            domains.CONSTRUCTION_K7_VERIFICATION_V170_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V170 frozen verification changed")
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_complete_abstract_plan_receipt_taxonomy_verification_v170",
)
