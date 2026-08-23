"""Cross-family campaign core for receipt-driven dependency invalidation V174."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from types import FunctionType, SimpleNamespace

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import construction_k7_domain_registry_extension_v174 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET_FAMILY,
)
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import TAXONOMY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.receipt_driven_minimal_invalidation_sequence_v174 import (
    run_receipt_driven_minimal_invalidation_sequence_v174,
)


TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_FAMILY)
V173R1_CAMPAIGN_ID = "418dc59c44243cb96e275539f564b1cd651664c9af19538d75f675093b8f2840"
V173R1_CAMPAIGN_BYTE_COUNT = 37_582_314
V173R1_CAMPAIGN_SHA256 = "ab871f3c8ecb6a19a8876458bb7c7e68737e7493489b89723191587d8219be46"
V173R1_VERIFICATION_ID = "223891b22ccd29e9fb8386b182e6ee1226933b33e5d9e00defe8acf8bdd7a125"
V173R1_VERIFICATION_BYTE_COUNT = 2_012
V173R1_VERIFICATION_SHA256 = "bf07867857aea2089def3b57ff99b068a9152ef92c1e8a6d03df284be79faf8f"


def receipt_driven_invalidation_campaign_config_v174():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_FAMILY] = copy.deepcopy(
        reservoir["families"][RESERVOIR_FAMILY]
    )
    config["families"][PACKET_FAMILY]["maximum_acquisition_labels"] = 2_048
    config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


_SEQUENCE_SOURCE_PROXY = SimpleNamespace(
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN,
)
_SEQUENCE_OUTPUT_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v174,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V174_DOMAIN,
)
_ANNOTATOR_GLOBALS = dict(sequence_v168.__dict__)
_ANNOTATOR_GLOBALS.update(
    domains_v154=_SEQUENCE_SOURCE_PROXY,
    domains=_SEQUENCE_OUTPUT_PROXY,
)
_ANNOTATE_V168_SHAPE = FunctionType(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168.__code__,
    _ANNOTATOR_GLOBALS,
    name="_annotate_receipt_invalidation_v168_shape_v174",
)

_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v174,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V174_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    run_certified_memoized_planner_sequence_v154=(
        run_receipt_driven_minimal_invalidation_sequence_v174
    ),
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE_V168_SHAPE,
)
_BASE_V160_OCCURRENCE = FunctionType(
    v168._BASE_V160_OCCURRENCE_V168.__code__,  # noqa: SLF001
    _V160_GLOBALS,
    name="_base_receipt_invalidation_occurrence_v174",
)

_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v174,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V174_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V174_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V166_OCCURRENCE = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_GLOBALS,
    name="_base_receipt_invalidation_v166_occurrence_v174",
)

_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v174,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V174_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166_OCCURRENCE,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V168_OCCURRENCE = FunctionType(
    v168.build_fifth_family_total_plan_receipt_set_occurrence_v168.__code__,
    _V168_GLOBALS,
    name="_base_receipt_invalidation_v168_occurrence_v174",
)


def build_receipt_driven_invalidation_occurrence_v174(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family not in (PACKET_FAMILY, RESERVOIR_FAMILY):
        raise ValueError("V174 target family is not registered")
    base = _BASE_V168_OCCURRENCE(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    sequences = (
        base["progressive_prior_sequence"],
        base["progressive_strict_sequence"],
    )
    histogram = {
        source: sum(
            sequence["online_typed_plan_source_histogram"][source]
            for sequence in sequences
        )
        for source in TAXONOMY.values()
    }
    graph_invalidations = sum(
        row["receipt_driven_graph_dependency_invalidation_count"]
        for row in sequences
    )
    graph_retentions = sum(
        row["receipt_driven_graph_dependency_retention_count"]
        for row in sequences
    )
    program_invalidations = sum(
        row["receipt_driven_compiled_program_invalidation_count"]
        for row in sequences
    )
    incremental_revalidations = sum(
        row["incrementally_revalidated_plan_receipt_count"] for row in sequences
    )
    role = (
        "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION"
        if family == PACKET_FAMILY
        else "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION"
    )
    gate = {
        key: value for key, value in base["registered_gate"].items() if key != "passed"
    }
    gate.update(
        every_plan_has_online_dependency_projection=all(
            sequence["online_plan_issuance_receipt_count"]
            == sum(
                len(episode["abstract_plan_receipts"])
                for episode in sequence["episodes"]
            )
            and sequence[
                "every_live_graph_cache_entry_has_prior_online_dependency_projection"
            ]
            is True
            for sequence in sequences
        ),
        every_execution_joins_prior_online_dependency_receipt=all(
            sequence["every_executed_action_joins_prior_online_receipt"] is True
            and sequence["online_execution_join_receipt_count"]
            == sequence["execution_step_count"]
            for sequence in sequences
        ),
        only_declared_dependencies_drive_graph_invalidation=all(
            sequence["only_receipt_declared_dependencies_drive_graph_invalidation"]
            is True
            for sequence in sequences
        ),
        unaffected_graph_dependencies_are_retained=graph_retentions > 0,
        incremental_revalidation_is_observed=incremental_revalidations > 0,
        registered_role_positive=(
            graph_invalidations > 0 and program_invalidations > 0
            if family == PACKET_FAMILY
            else graph_retentions > 0
            and incremental_revalidations > 0
            and histogram["SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE"] > 0
        ),
        factor_prior_strictly_reduces_acquisition_labels=(
            base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        ),
        query_policy_noninferior=(
            base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
        ),
        query_local_exact_overlay_remains_only_safety_authority=all(
            sequence["query_local_exact_overlay_remains_only_safety_authority"]
            is True
            and sequence[
                "receipt_dependency_lifecycle_is_model_or_safety_authority"
            ]
            is False
            for sequence in sequences
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.receipt_driven_invalidation_occurrence.v174",
        "registered_dependency_role": role,
        "online_typed_plan_source_histogram": histogram,
        "receipt_driven_graph_dependency_invalidation_count": graph_invalidations,
        "receipt_driven_graph_dependency_retention_count": graph_retentions,
        "receipt_driven_compiled_program_invalidation_count": program_invalidations,
        "incrementally_revalidated_plan_receipt_count": incremental_revalidations,
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in sequences
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in sequences
        ),
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V174_CROSS_FAMILY_COHORT",
        "receipt_dependency_lifecycle_changes_selected_action_order": False,
        "receipt_dependency_lifecycle_is_model_or_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_OCCURRENCE_V174_DOMAIN, payload
        ),
    }


def _target(args):
    return build_receipt_driven_invalidation_occurrence_v174(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        raise ValueError(f"V174 frozen predecessor changed: {name}")
    return document


def build_receipt_driven_invalidation_campaign_v174(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v173r1_campaign_raw,
    v173r1_verification_raw,
):
    predecessor = _frozen(
        v173r1_campaign_raw,
        count=V173R1_CAMPAIGN_BYTE_COUNT,
        digest=V173R1_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V173R1_CAMPAIGN_ID,
        name="V173r1 campaign",
    )
    verification = _frozen(
        v173r1_verification_raw,
        count=V173R1_VERIFICATION_BYTE_COUNT,
        digest=V173R1_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V173R1_VERIFICATION_ID,
        name="V173r1 verification",
    )
    if not (
        predecessor["registered_gate"]["passed"] is True
        and verification["producer_free_all_four_online_sources_reconstructed"]
        is True
        and verification[
            "producer_free_online_issuance_and_execution_joins_reconstructed"
        ]
        is True
    ):
        raise ValueError("V174 predecessor boundary changed")
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    histogram = {
        source: sum(row["online_typed_plan_source_histogram"][source] for row in rows)
        for source in TAXONOMY.values()
    }
    accounting = {
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        "graph_dependency_invalidations": sum(
            row["receipt_driven_graph_dependency_invalidation_count"] for row in rows
        ),
        "graph_dependency_retentions": sum(
            row["receipt_driven_graph_dependency_retention_count"] for row in rows
        ),
        "compiled_program_invalidations": sum(
            row["receipt_driven_compiled_program_invalidation_count"] for row in rows
        ),
        "incrementally_revalidated_plan_receipts": sum(
            row["incrementally_revalidated_plan_receipt_count"] for row in rows
        ),
        "factor_prior_labels_avoided": sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        "query_policy_labels_avoided": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        "sample_labels_execution_steps_derivation_planning_receipt_and_dependency_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    roles = {row["registered_dependency_role"] for row in rows}
    gate = {
        "required_occurrence_count": config["required_target_occurrence_count"],
        "passed_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "packet_and_reservoir_dependency_roles_both_present": roles
        == {
            "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION",
            "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION",
        },
        "all_four_online_plan_sources_observed": all(
            histogram[source] > 0 for source in TAXONOMY.values()
        ),
        "positive_selective_graph_invalidation_observed": accounting[
            "graph_dependency_invalidations"
        ]
        > 0,
        "positive_unaffected_graph_retention_observed": accounting[
            "graph_dependency_retentions"
        ]
        > 0,
        "positive_exact_state_program_invalidation_observed": accounting[
            "compiled_program_invalidations"
        ]
        > 0,
        "positive_incremental_revalidation_observed": accounting[
            "incrementally_revalidated_plan_receipts"
        ]
        > 0,
        "factor_prior_strictly_reduces_labels_each_occurrence": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "query_policy_noninferior_each_occurrence": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"]["certificate_failure_only_local_ground_distinctions"]
            for row in rows
        ),
        "receipt_lifecycle_not_safety_authority": all(
            row["receipt_dependency_lifecycle_is_model_or_safety_authority"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.receipt_driven_invalidation_campaign.v174",
        "preregistration_id": preregistration_id,
        "frozen_v173r1_campaign_id": V173R1_CAMPAIGN_ID,
        "frozen_v173r1_verification_id": V173R1_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "online_typed_plan_source_histogram": histogram,
        "accounting": accounting,
        "registered_gate": gate,
        "receipt_driven_minimal_invalidation_observed": gate["passed"],
        "factor_prior_sample_tax_reduction_observed": gate[
            "factor_prior_strictly_reduces_labels_each_occurrence"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V174_CROSS_FAMILY_COHORT",
        "receipt_dependency_lifecycle_changes_selected_action_order": False,
        "receipt_dependency_lifecycle_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_CAMPAIGN_V174_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_FAMILY",
    "RESERVOIR_FAMILY",
    "build_receipt_driven_invalidation_campaign_v174",
    "build_receipt_driven_invalidation_occurrence_v174",
    "receipt_driven_invalidation_campaign_config_v174",
)
