"""Producer-free verification for artifact-derived factor campaign V120.

This module deliberately does not import the V120 projection producer,
acquisition, campaign core, preregistration, or campaign producer.  It derives
the anonymous factor library again from the three frozen campaign byte streams
and independently replays the V120 content graph and retained V119 planner
sequence evidence.
"""

from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains59
from acfqp import construction_k7_domain_registry_extension_v120 as domains
from acfqp import construction_k7_source_unseen_residual_independent_verifier_v119 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "64f1516fa490d4a3fed96f460850113bdcd2243fd1338d663b08b1b13e6e7432"
CAMPAIGN_BYTE_COUNT = 4_177_141
CAMPAIGN_SHA256 = "d6f50c58d3f8a953b62592fb620f57c39e71fd52e29582c7cbce2f5fc05bbbfd"
PREREGISTRATION_ID = "e381fffe2276be471c7064e8642e7bf583910b4e7ff2d2897e2d3d9bdd3a6596"
V119_CAMPAIGN_ID = "611c995b93af4016bb85e070f5c1f263d6028ec424cc860e2b67da2bb9aeb3d4"
V119_VERIFICATION_ID = "2a9569ea23d23ee1f69219b36c03dd8a6f8b827a7f9f5b6c77f62587380e2e70"
V119_VERIFIER_SOURCE_SHA256 = "a9f11c4bce04c2729f057cf4e6650f0a8addf47a304e3a442267bd261dd68c5d"
FACTOR_LIBRARY_ID = "352084adc6c9dec68cb5b63976acb170aa4e02ed5004c89ebe8cd22d08e6b68a"
FAMILY = "STOCHASTIC_DUAL_BUDGET_COMPOSITION"
TARGETS = ((FAMILY, 1_032_101), (FAMILY, 1_032_102))
EPISODES = (269, 270, 271)
GENERIC_ATOMIC_OPCODE_NAMES = [f"E{index:02d}" for index in range(14)]
SOURCE_CAMPAIGN_SPECS = {
    "V117": {
        "campaign_id": "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d",
        "byte_count": 7_794_238,
        "sha256": "061a653cf1048fe01420a3159d4389b9b81eb573f97c5acfbd66fcf618d60039",
    },
    "V118": {
        "campaign_id": "0ab03c02a8b5b795860c5c96943204f8553fc6836e7dab92ef753c1fe6d86df1",
        "byte_count": 2_986_273,
        "sha256": "9afbade52f4b553ad5696e769ba6f8f1faced07fbb11b07b0f8a59991961e19d",
    },
    "V119": {
        "campaign_id": V119_CAMPAIGN_ID,
        "byte_count": 4_479_714,
        "sha256": "22565e57114973fbf1c2fc16d11785eb67c9aebcb5df2c61dc39cc0ba64e301e",
    },
}
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ArtifactDerivedFactorIndependentVerifierV120Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ArtifactDerivedFactorIndependentVerifierV120Error(message)


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V120 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v120(domain, payload):
        _fail(f"V120 {key} changed")


def _source_campaign(alias: str, raw: bytes) -> dict[str, Any]:
    spec = SOURCE_CAMPAIGN_SPECS.get(alias)
    if (
        spec is None
        or type(raw) is not bytes
        or len(raw) != spec["byte_count"]
        or hashlib.sha256(raw).hexdigest() != spec["sha256"]
    ):
        _fail("V120 factor source campaign bytes changed")
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or document.get("campaign_id") != spec["campaign_id"]
        or document.get("registered_gate", {}).get("passed") is not True
    ):
        _fail("V120 factor source campaign identity or Gate changed")
    return document


def _source_candidates(value: Any) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    def visit(item: Any) -> None:
        if type(item) is dict:
            if item.get("schema") == "acfqp.generic_partial_factor_candidate.v15":
                identity = item.get("candidate_id")
                payload = {
                    key: value for key, value in item.items() if key != "candidate_id"
                }
                if (
                    type(identity) is not str
                    or identity
                    != domains59.extension_content_id_v59(
                        domains59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
                        payload,
                    )
                ):
                    _fail("V120 source candidate identity changed")
                incumbent = result.setdefault(identity, item)
                if incumbent != item:
                    _fail("V120 repeated source candidate bytes changed")
            for nested in item.values():
                visit(nested)
        elif type(item) is list:
            for nested in item:
                visit(nested)

    visit(value)
    return [result[key] for key in sorted(result)]


def _normalized(expression: Any, target: int) -> Any:
    action_fields: dict[int, int] = {}
    state_columns: dict[int, int] = {}

    def visit(item: Any) -> Any:
        if type(item) is not list or not item:
            return item
        if item[0] == "E00":
            if item[1] == target:
                return ["S", "SELF"]
            state_columns.setdefault(item[1], len(state_columns))
            return ["S", state_columns[item[1]]]
        if item[0] == "E01":
            action_fields.setdefault(item[1], len(action_fields))
            return ["A", action_fields[item[1]]]
        return [item[0], *(visit(value) for value in item[1:])]

    return visit(expression)


def _artifact_library(source_campaign_bytes: Mapping[str, bytes]) -> dict[str, Any]:
    if type(source_campaign_bytes) is not dict or set(source_campaign_bytes) != set(
        SOURCE_CAMPAIGN_SPECS
    ):
        _fail("V120 source campaign inventory changed")
    campaigns = {
        alias: _source_campaign(alias, source_campaign_bytes[alias])
        for alias in sorted(source_campaign_bytes)
    }
    candidates = {
        alias: _source_candidates(document) for alias, document in campaigns.items()
    }
    if any(not rows for rows in candidates.values()):
        _fail("V120 source campaign exposes no candidate")
    origins_by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized_by_signature: dict[str, tuple[str, Any]] = {}
    for alias, rows in candidates.items():
        for candidate in rows:
            state_width = candidate.get("state_width")
            action_width = candidate.get("action_field_width")
            assignments = candidate.get("compiled_factor_assignments")
            if (
                type(state_width) is not int
                or type(action_width) is not int
                or type(assignments) is not list
                or not assignments
            ):
                _fail("V120 source candidate shape changed")
            for assignment in assignments:
                target = assignment.get("target_column")
                result_type = assignment.get("result_type")
                expression = assignment.get("expression")
                if (
                    type(target) is not int
                    or result_type not in {"INT", "FINITE_INT_SUPPORT"}
                    or type(expression) is not list
                ):
                    _fail("V120 source factor assignment changed")
                normalized = _normalized(expression, target)
                signature_payload = {
                    "result_type": result_type,
                    "normalized_expression": normalized,
                }
                signature = hashlib.sha256(
                    canonical_json_bytes(signature_payload)
                ).hexdigest()
                incumbent = normalized_by_signature.setdefault(
                    signature, (result_type, normalized)
                )
                if incumbent != (result_type, normalized):
                    _fail("V120 normalized signature collision")
                origins_by_signature[signature].append(
                    {
                        "source_campaign_alias": alias,
                        "source_campaign_id": campaigns[alias]["campaign_id"],
                        "source_candidate_id": candidate["candidate_id"],
                        "source_schema_pair": [state_width, action_width],
                        "source_target_column": target,
                    }
                )
    templates = []
    origin_rows = []
    for signature in sorted(origins_by_signature):
        result_type, normalized = normalized_by_signature[signature]
        origins = sorted(origins_by_signature[signature], key=canonical_json_bytes)
        schema_pairs = sorted({tuple(row["source_schema_pair"]) for row in origins})
        if len(schema_pairs) < 2:
            continue
        templates.append(
            {
                "signature_sha256": signature,
                "result_type": result_type,
                "normalized_expression": normalized,
                "source_schema_pairs": [list(row) for row in schema_pairs],
            }
        )
        origin_rows.append(
            {
                "signature_sha256": signature,
                "distinct_schema_pair_count": len(schema_pairs),
                "origin_count": len(origins),
                "origins": origins,
            }
        )
    payload = {
        "schema": "acfqp.artifact_derived_factor_library.v120",
        "source_campaigns": [
            {
                "alias": alias,
                **SOURCE_CAMPAIGN_SPECS[alias],
                "unique_partial_candidate_count": len(candidates[alias]),
            }
            for alias in sorted(campaigns)
        ],
        "minimum_distinct_schema_pair_support": 2,
        "derived_subprograms": templates,
        "derivation_origins": origin_rows,
        "candidate_document_count": sum(len(rows) for rows in candidates.values()),
        "normalization_rule": "ALPHA_RENAME_STATE_AND_ACTION_REFERENCES_WITH_TARGET_AS_SELF",
        "semantic_family_names_used_for_subprogram_selection": False,
        "target_slot_inventory_supplied": False,
        "ground_transition_prediction_authority_present": False,
        "complete_world_model_claimed": False,
    }
    identity = domains.extension_content_id_v120(
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_LIBRARY_V120_DOMAIN,
        payload,
    )
    projection = {
        "schema": "acfqp.cross_schema_factor_template_projection.v15",
        "source_factor_library_id": identity,
        "cross_schema_subprograms": templates,
        "target_slot_inventory_supplied": False,
        "semantic_names_supplied": False,
    }
    result = {
        **payload,
        "factor_library_id": identity,
        "v15_partial_synthesizer_projection": projection,
        "projection_derived_only_from_frozen_candidate_artifacts": True,
        "hand_written_factor_template_count": 0,
    }
    if identity != FACTOR_LIBRARY_ID or len(templates) != 3:
        _fail("V120 independently derived factor library changed")
    return result


def _v119_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V119_VERIFIER_SOURCE_SHA256
        or previous.CAMPAIGN_ID != V119_CAMPAIGN_ID
        or previous.VERIFICATION_ID != V119_VERIFICATION_ID
    ):
        _fail("V120 frozen producer-free V119 verifier changed")
    namespace = dict(previous.__dict__)
    namespace["EPISODES"] = EPISODES
    originals = {
        name: value
        for name, value in previous.__dict__.items()
        if type(value) is FunctionType and value.__module__ == previous.__name__
    }
    for name, value in originals.items():
        clone = FunctionType(
            value.__code__,
            namespace,
            name=value.__name__,
            argdefs=value.__defaults__,
            closure=value.__closure__,
        )
        clone.__kwdefaults__ = value.__kwdefaults__
        namespace[name] = clone
    return namespace


def _candidate(document: Any, library: Mapping[str, Any]) -> dict[str, int]:
    if type(document) is not dict:
        _fail("V120 candidate type changed")
    payload = {key: value for key, value in document.items() if key != "candidate_id"}
    assignments = document.get("compiled_factor_assignments")
    unknown = document.get("unknown_residual_target_columns")
    signatures = {
        row["signature_sha256"] for row in library["derived_subprograms"]
    }
    if (
        document.get("candidate_id")
        != domains.extension_content_id_v120(
            domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_ACQUISITION_V120_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or document.get("source_factor_library_id") != library["factor_library_id"]
        or type(assignments) is not list
        or len(assignments) < 3
        or any(
            type(row) is not dict
            or type(row.get("target_column")) is not int
            or row.get("result_type") not in {"INT", "FINITE_INT_SUPPORT"}
            or type(row.get("expression")) is not list
            or row.get("signature_sha256") not in signatures
            for row in assignments
        )
        or type(unknown) is not list
        or not unknown
        or sorted(set(unknown)) != unknown
        or set(unknown) & {row["target_column"] for row in assignments}
        or document.get("target_slot_inventory_supplied_by_prior") is not False
        or document.get("target_bindings_derived_from_raw_observations") is not True
        or document.get("semantic_names_used") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("planning_authority_present") is not False
    ):
        _fail("V120 candidate identity or boundary changed")
    return {
        "compiled_factor_assignment_count": len(assignments),
        "unknown_residual_target_column_count": len(unknown),
    }


def _acquisition(
    document: Any, library: Mapping[str, Any], family: str, seed: int
) -> dict[str, int]:
    _content(
        document,
        "acquisition_id",
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_ACQUISITION_V120_DOMAIN,
    )
    counts = _candidate(document.get("candidate"), library)
    labels = document.get("ground_support_labels")
    rows = document.get("raw_transition_count")
    stop = document.get("terminal_stop_update")
    if (
        document.get("schema") != "acfqp.artifact_derived_partial_acquisition.v120"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "ARTIFACT_DERIVED_ANONYMOUS_FACTOR_PRIOR_ON"
        or document.get("factor_prior_enabled") is not True
        or document.get("artifact_factor_library_id") != library["factor_library_id"]
        or document.get("artifact_factor_subprogram_count") != 3
        or document.get("hand_written_factor_template_count") != 0
        or type(labels) is not int
        or labels <= 0
        or type(rows) is not int
        or rows <= 0
        or type(document.get("raw_transition_sha256")) is not str
        or len(document["raw_transition_sha256"]) != 64
        or type(stop) is not dict
        or stop.get("stopped") is not True
        or document.get("same_witness_blind_raw_prefix_as_strict_control") is not True
        or document.get(
            "factor_projection_derived_only_from_frozen_candidate_artifacts"
        )
        is not True
        or document.get("partial_prediction_scope_only") is not True
        or document.get("unknown_residual_outputs_claimed") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("planning_authority_present") is not False
        or document.get("reachable_frontier_exhaustion_input_consumed") is not False
        or document.get("heuristic_mdl_information_units_consumed") is not False
        or document.get("predictive_evidence_to_mdl_credit_consumed") is not False
    ):
        _fail("V120 partial acquisition semantics changed")
    return {**counts, "ground_support_labels": labels, "raw_transition_count": rows}


def _strict(document: Any, partial: Mapping[str, Any], family: str, seed: int) -> None:
    _content(
        document,
        "strict_control_id",
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_STRICT_CONTROL_V120_DOMAIN,
    )
    if (
        document.get("schema")
        != "acfqp.artifact_derived_strict_complete_model_control.v120"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "STRICT_NO_PRIOR_SINGLE_MATCHED_PREFIX_ATTEMPT"
        or document.get("factor_prior_enabled") is not False
        or document.get("ground_support_labels") != partial.get("ground_support_labels")
        or document.get("raw_transition_count") != partial.get("raw_transition_count")
        or document.get("raw_transition_sha256")
        != partial.get("raw_transition_sha256")
        or document.get("matched_partial_acquisition_id")
        != partial.get("acquisition_id")
        or document.get("generic_atomic_composition_max_depth") != 3
        or document.get("generic_atomic_opcode_names") != GENERIC_ATOMIC_OPCODE_NAMES
        or document.get("attempt_count") != 1
        or document.get("outcome_kind")
        != "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR"
        or document.get("complete_candidate") is not None
        or document.get("constructor_error_type")
        != "GenericAtomicExpressionWorldModelV4Error"
        or document.get("typed_rejection_is_not_domain_infeasibility") is not True
        or document.get("typed_rejection_is_not_planning_failure") is not True
        or document.get("strict_control_used_for_safety_authority") is not False
        or document.get("sample_efficiency_sign_claimed") is not False
    ):
        _fail("V120 strict matched-prefix control changed")


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    library: Mapping[str, Any],
    namespace: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_OCCURRENCE_V120_DOMAIN,
    )
    partial = document.get("partial_prior_acquisition")
    strict = document.get("strict_no_prior_complete_model_control")
    sequence = document.get("genesis_authorized_program_branch_sequence")
    if (
        document.get("schema") != "acfqp.artifact_derived_factor_occurrence.v120"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("artifact_factor_library") != library
        or document.get("artifact_factor_library_id") != library["factor_library_id"]
        or type(partial) is not dict
        or type(strict) is not dict
        or type(sequence) is not dict
    ):
        _fail("V120 occurrence identity changed")
    candidate_counts = _acquisition(partial, library, family, seed)
    _strict(strict, partial, family, seed)
    try:
        sequence_counts = namespace["_sequence"](
            sequence, partial["candidate"], namespace["_v117_namespace"]()
        )
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V120 retained planner sequence reconstruction failed: {exc}")
    base = sequence["genesis_authorized_base_sequence"]
    accounting = {
        "partial_prior_acquisition_labels": partial["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": sequence_counts["planning_compute"],
        "matched_uncached_planning_compute_events": sequence_counts[
            "uncached_compute"
        ],
        "planning_compute_events_avoided_against_uncached": sequence_counts[
            "uncached_compute"
        ]
        - sequence_counts["planning_compute"],
        "dependency_derivation_compute_events": sequence_counts[
            "dependency_derivation_compute_events"
        ],
        "same_epoch_genesis_authorized_cache_hits": sequence_counts[
            "same_epoch_genesis_authorized_cache_hits"
        ],
        "program_branch_cache_hits": sequence_counts["branch_hits"],
        "artifact_library_derivation_candidate_documents": library[
            "candidate_document_count"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_library_derivation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": True,
        "candidate_uses_artifact_derived_factor_library": True,
        "hand_written_factor_template_count_zero": True,
        "three_cross_schema_subprograms_derived": True,
        "factor_library_reconstructed_from_frozen_candidate_artifacts": True,
        "partial_candidate_retains_unknown_higher_order_residual": candidate_counts[
            "unknown_residual_target_column_count"
        ]
        > 0,
        "minimum_reusable_factor_count_derived": candidate_counts[
            "compiled_factor_assignment_count"
        ]
        >= 3,
        "strict_control_uses_exact_partial_raw_prefix": True,
        "strict_control_outcome_retained_without_selection": True,
        "same_epoch_genesis_authorization_observed": sequence_counts[
            "same_epoch_genesis_authorized_cache_hits"
        ]
        > 0,
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in base["episodes"]
        ),
        "certificate_failure_only_query_discipline_clean": base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_matches_full_v105_rebuild": base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("genesis_authorized_program_branch_sequence_id")
        != sequence.get("sequence_id")
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("artifact_derived_partial_world_model_pipeline_verified")
        != gate["passed"]
        or document.get("target_family_present_in_historical_artifact_inventory")
        is not True
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("strict_complete_model_required_for_planning") is not False
        or document.get("strict_control_outcome_used_for_gate_selection") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V120 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **candidate_counts,
        **accounting,
    }


def verify_artifact_derived_factor_campaign_bytes_v120(
    raw: bytes, source_campaign_bytes: Mapping[str, bytes]
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V120 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V120 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_CAMPAIGN_V120_DOMAIN,
    )
    library = _artifact_library(source_campaign_bytes)
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.artifact_derived_factor_campaign.v120"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v119_success_campaign_id") != V119_CAMPAIGN_ID
        or document.get("v119_success_verification_id") != V119_VERIFICATION_ID
        or document.get("artifact_factor_library_id") != FACTOR_LIBRARY_ID
        or document.get("artifact_factor_library") != library
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V120 campaign inventory changed")
    namespace = _v119_namespace()
    replay = [
        _occurrence(row, family, seed, library, namespace)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    accounting_keys = tuple(rows[0]["accounting"])
    accounting = {
        **{
            key: sum(row["accounting"][key] for row in rows)
            for key in accounting_keys
            if type(rows[0]["accounting"][key]) is int
        },
        "historical_artifact_labels_not_recharged_to_target": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_library_derivation_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    ood = document.get("incompatible_schema_no_transfer_control")
    strict_ood = (
        type(ood) is dict
        and ood.get("exact_interface_match") is False
        and ood.get("learned_structure_prior_delivered") is False
        and ood.get("strict_ood_no_transfer") is True
    )
    passed = all(row["gate_passed"] for row in replay) and strict_ood
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "artifact_factor_library_shared_exactly_across_occurrences": True,
        "hand_written_factor_template_count_zero": True,
        "every_occurrence_retains_unknown_residual_and_completes_planning": all(
            row["unknown_residual_target_column_count"] > 0
            and row["gate_passed"]
            for row in replay
        ),
        "same_epoch_genesis_authorization_verified": all(
            row["same_epoch_genesis_authorized_cache_hits"] > 0 for row in replay
        ),
        "strict_control_outcomes_retained_without_gate_selection": True,
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("target_occurrence_ids")
        != [row["occurrence_id"] for row in rows]
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "registered_artifact_derived_partial_world_model_pipeline_verified"
        )
        != passed
        or document.get("target_family_present_in_historical_artifact_inventory")
        is not True
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("strict_complete_model_required_for_planning") is not False
        or document.get("strict_control_outcome_used_for_gate_selection") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V120 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.artifact_derived_factor_verification.v120",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v119_success_verification_id": V119_VERIFICATION_ID,
        "artifact_factor_library_id": FACTOR_LIBRARY_ID,
        "verification_status": "REGISTERED_V120_ARTIFACT_DERIVED_FACTOR_PIPELINE_VERIFIED",
        "producer_free_artifact_factor_library_reconstruction": True,
        "producer_free_candidate_acquisition_and_content_graph_reconstruction": True,
        "producer_free_v113_sequence_and_v119_genesis_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v120_full_ground_dynamics_rederivation_performed": False,
        "target_family_present_in_historical_artifact_inventory": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "sample_efficiency_improvement_claimed": False,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_artifact_derived_factor_verification_v120(
    raw: bytes, source_campaign_bytes: Mapping[str, bytes]
) -> bytes:
    payload = verify_artifact_derived_factor_campaign_bytes_v120(
        raw, source_campaign_bytes
    )
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v120(
            domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_VERIFICATION_V120_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V120 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_artifact_derived_factor_verification_v120",
    "verify_artifact_derived_factor_campaign_bytes_v120",
)
