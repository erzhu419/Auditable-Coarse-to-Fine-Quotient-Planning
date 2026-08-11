"""Independent bytes-only replay of the K7 causal-promotion output bundle.

This verifier consumes only the eight committed canonical JSON byte strings.
It does not import or call the causal-promotion fixture, worker, supervisor, or
occurrence renderer.  It independently replays the portable source/runtime
identity graph, sealed-worker budget attestation, twelve stage vectors, all
202 occurrence records, the 182-term projection, final output-byte equation,
and construction-specific typed terminal.

The verification is evaluation-lane evidence.  It does not re-execute the
sealed worker or reread its original source files, close a logical occurrence,
run the Counter Completeness/Workload Economics Gates, or authorize official
execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN,
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_sealed_executor_v1 import (
    RuntimeManifestCapProfileV1,
    RuntimeTreeManifestV1,
)
from acfqp.routing_v1 import (
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
    TypedVerificationAttestationV1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.81"
PROFILE_KEY = (
    "v075_k7_causal_promotion_complete_bundle_independent_verifier_v1"
)

VERIFICATION_PROFILE_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
)
SEMANTIC_VERIFIER_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
)

REQUIRED_ROLES = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
STAGE_PLAN = (
    "PREOPEN_COMMON_PREFIX",
    "INITIAL_ACQUISITION",
    "INITIAL_MODEL_BUILD",
    "FAILED_ABSTRACT_PREFIX",
    "OPEN_INCREMENTAL_ACQUISITION",
    "OPEN_CHECKPOINT_REPLANNING",
    "OPEN_CHECKPOINT_REPLANNING",
    "OPEN_INCREMENTAL_ACQUISITION",
    "OPEN_CHECKPOINT_REPLANNING",
    "OPEN_INCREMENTAL_ACQUISITION",
    "OPEN_CHECKPOINT_REPLANNING",
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION",
)
SHARED_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
DERIVED_PATHS = {
    "process.exit_failures": 0,
    "process.exit_successes": 1,
    "route.attempts": 1,
    "route.failures": 1,
    "route.successes": 0,
    "solver.attempts": 0,
    "solver.failures": 0,
    "solver.successes": 0,
}

EXPECTED_PARENT_INTEGRITY = (
    "runtime-preparation-replayed",
    "runtime-cas-resolved",
    "private-runtime-lease-replayed",
    "child-completion-observed",
    "trace-canonical-and-content-id-replayed",
    "twelve-stage-event-chains-replayed",
    "science-summary-identity-chain-replayed",
    "resource-formulas-reconciled",
)
EXPECTED_PARENT_PROTOCOL = (
    "request-identity-frozen-before-launch",
    "fresh-python-I-argv-executed",
    "single-process-launch-observed",
    "quiet-stdout-stderr-enforced",
    "worker-trace-schema-enforced",
    "stage-order-and-owner-chain-enforced",
    "terminal-route-reconciliation-enforced",
    "operational-cutoff-precedes-accounting-provenance",
)
EXPECTED_CHILD_INTEGRITY = tuple(
    sorted(
        (
            "request-canonical-and-content-id-replayed",
            "terminal-identity-chain-replayed",
            "budget-closure-semantic-verification-consumed",
            "twelve-stage-inventory-replayed",
            "science-summary-derived-from-live-result",
            *(f"stage-{index:02d}-event-to-vector-replay" for index in range(1, 13)),
        )
    )
)
EXPECTED_CHILD_PROTOCOL = tuple(
    sorted(
        (
            "request-construction-only-profile-bound",
            "budget-exhaustion-route-outcome-replayed",
            "construction-terminal-mapping-prerequisites-frozen",
            "route-and-solver-reconciliation-derived",
            *(f"stage-{index:02d}-owner-and-sequence-binding" for index in range(1, 13)),
        )
    )
)

_SOURCE_MODULE_DOMAIN = "acfqp:v075-construction-source-module:v2"
_SOURCE_CLOSURE_DOMAIN = "acfqp:v075-construction-source-closure:v2"
_BUDGET_CAP_DOMAIN = "acfqp:v075-live-causal-promotion-cap-profile:v3"
_BUDGET_REPLAY_DOMAIN = "acfqp:v075-live-causal-promotion-budget-replay:v3"
_BUDGET_CLOSURE_DOMAIN = "acfqp:v075-live-causal-promotion-budget-closure:v3"
_BUDGET_VERIFICATION_DOMAIN = (
    "acfqp:v075-live-causal-promotion-budget-closure-verification:v3"
)
_PROMOTION_VERIFICATION_DOMAIN = (
    "acfqp:v075-live-batched-causal-promotion-bundle-verification:v3"
)

_VERIFICATION_ISSUER = object()


class V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
    ValueError
):
    """A portable role, identity, value, projection, or terminal failed."""


def _fail(message: str) -> NoReturn:
    raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _raw_domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            f"{label} bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are not one canonical object")
    return document


def _exact_fields(document: Mapping[str, Any], fields: set[str], label: str) -> None:
    try:
        require_exact_fields(document, fields, context=label)
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            str(error)
        ) from error


def _verify_source_closure(document: Mapping[str, Any]) -> str:
    closure_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "closure_rule",
        "root_modules",
        "modules",
        "module_ids",
        "module_count",
        "all_sources_regular_files",
        "all_source_paths_symlink_free",
        "caller_supplied_source_bytes_replayed",
        "construction_only",
        "closure_id",
    }
    module_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "module_name",
        "relative_path",
        "is_package",
        "source_sha256",
        "source_byte_count",
        "static_local_imports",
        "regular_file_verified",
        "symlink_free_verified",
        "module_id",
    }
    _exact_fields(document, closure_fields, "construction source closure")
    modules = document["modules"]
    roots = document["root_modules"]
    module_ids = document["module_ids"]
    if (
        document["schema"] != "acfqp.v075_construction_source_closure.v2"
        or document["schema_version"] != "2.0.0"
        or document["profile_key"] != "v075_construction_source_runtime_v2"
        or document["closure_rule"]
        != "RECURSIVE_STATIC_MULTIROOT_LOCAL_ACFQP_IMPORTS"
        or type(modules) is not list
        or type(roots) is not list
        or type(module_ids) is not list
        or not modules
        or document["module_count"] != len(modules)
        or len(module_ids) != len(modules)
        or document["all_sources_regular_files"] is not True
        or document["all_source_paths_symlink_free"] is not True
        or document["caller_supplied_source_bytes_replayed"] is not True
        or document["construction_only"] is not True
    ):
        _fail("construction source closure contract changed")
    names: list[str] = []
    expected_ids: list[str] = []
    present: set[str] = set()
    for row in modules:
        if type(row) is not dict:
            _fail("construction source module is not one object")
        _exact_fields(row, module_fields, "construction source module")
        payload = dict(row)
        supplied = payload.pop("module_id")
        _cid(supplied, "construction source module")
        if supplied != _raw_domain_id(_SOURCE_MODULE_DOMAIN, payload):
            _fail("construction source module content ID changed")
        name = row["module_name"]
        imports = row["static_local_imports"]
        if (
            type(name) is not str
            or not name
            or type(row["relative_path"]) is not str
            or not row["relative_path"]
            or type(row["is_package"]) is not bool
            or type(row["source_byte_count"]) is not int
            or row["source_byte_count"] <= 0
            or type(imports) is not list
            or imports != sorted(set(imports))
            or row["regular_file_verified"] is not True
            or row["symlink_free_verified"] is not True
        ):
            _fail("construction source module semantics changed")
        _cid(row["source_sha256"], "construction source digest")
        names.append(name)
        expected_ids.append(supplied)
        present.add(name)
    if (
        names != sorted(set(names))
        or module_ids != expected_ids
        or roots != sorted(set(roots))
        or not set(roots) <= present
        or "acfqp" not in present
        or any(not set(row["static_local_imports"]) <= present for row in modules)
    ):
        _fail("construction source dependency closure changed")
    payload = dict(document)
    supplied = payload.pop("closure_id")
    if supplied != _raw_domain_id(_SOURCE_CLOSURE_DOMAIN, payload):
        _fail("construction source closure content ID changed")
    return supplied


def _verify_preparation(document: Mapping[str, Any]) -> tuple[str, RuntimeTreeManifestV1]:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "source_closure",
        "runtime_manifest",
        "runtime_manifest_cap_profile",
        "runtime_entrypoint",
        "private_runtime_lease_required",
        "runtime_tree_build_charged_to_occurrence",
        "construction_only",
        "official_execution_allowed",
        "causal_promotion_runtime_preparation_id",
    }
    _exact_fields(document, fields, "causal-promotion runtime preparation")
    try:
        manifest = RuntimeTreeManifestV1.from_dict(document["runtime_manifest"])
        cap = RuntimeManifestCapProfileV1.from_dict(
            document["runtime_manifest_cap_profile"]
        )
    except Exception as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            "runtime manifest or cap profile failed replay"
        ) from error
    closure = document["source_closure"]
    closure_id = _verify_source_closure(closure)
    source_rows = closure["modules"]
    if (
        document["schema"]
        != "acfqp.v075_k7_causal_promotion_runtime_preparation.v1"
        or document["schema_version"] != "1.0.0"
        or document["profile_key"]
        != "v075_k7_causal_promotion_accounted_executor_v1"
        or document["runtime_entrypoint"]
        != "acfqp/v075_k7_causal_promotion_accounted_runtime_v1.py"
        or document["private_runtime_lease_required"] is not True
        or document["runtime_tree_build_charged_to_occurrence"] is not False
        or document["construction_only"] is not True
        or document["official_execution_allowed"] is not False
        or closure["root_modules"]
        != ["acfqp.v075_k7_causal_promotion_accounted_runtime_v1"]
        or len(source_rows) != len(manifest.entries)
        or cap.tree_passes != 4
    ):
        _fail("runtime preparation contract changed")
    for source, entry in zip(source_rows, manifest.entries):
        if (
            source["relative_path"] != entry.relative_path
            or source["source_byte_count"] != entry.size_bytes
            or source["source_sha256"] != entry.sha256
        ):
            _fail("source closure/runtime manifest row join changed")
    payload = dict(document)
    supplied = payload.pop("causal_promotion_runtime_preparation_id")
    if supplied != content_id(
        V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN,
        payload,
    ):
        _fail("runtime preparation content ID changed")
    if closure_id != closure["closure_id"]:
        _fail("runtime preparation source closure crossed")
    return supplied, manifest


def _verify_request(
    document: Mapping[str, Any],
    *,
    preparation_id: str,
    runtime_tree_id: str,
) -> str:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "runtime_preparation_id",
        "runtime_tree_id",
        "construction_fixture_marker",
        "construction_only",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "supervised_request_id",
    }
    _exact_fields(document, fields, "causal-promotion supervised request")
    payload = dict(document)
    supplied = payload.pop("supervised_request_id")
    if (
        document["schema"]
        != "acfqp.v075_k7_causal_promotion_supervised_request.v1"
        or document["schema_version"] != "1.0.0"
        or document["profile_key"]
        != "v075_k7_causal_promotion_accounted_executor_v1"
        or document["runtime_preparation_id"] != preparation_id
        or document["runtime_tree_id"] != runtime_tree_id
        or type(document["construction_fixture_marker"]) is not str
        or not document["construction_fixture_marker"]
        or document["construction_only"] is not True
        or document["fresh_heldout_accessed"] is not False
        or document["official_execution_allowed"] is not False
        or supplied
        != content_id(
            V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN,
            payload,
        )
    ):
        _fail("supervised request contract or content ID changed")
    return supplied


_BUDGET_ATTESTATION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "occurrence_id",
    "budget_closure_id",
    "budget_closure_verification_id",
    "cap_profile_id",
    "trusted_budget_replay_id",
    "promotion_bundle_id",
    "final_model_epoch_id",
    "final_proof_id",
    "final_frontier_id",
    "executed_round_count",
    "executed_promotion_draw_count",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "budget_closure",
    "budget_closure_verification",
    "sealed_worker_exact_budget_closure_verification_consumed",
    "registered_cap_replayed_before_terminal_mapping",
    "worker_outcome_string_used_as_authority",
    "construction_specific_semantic_authority",
    "generic_trusted_budget_replay_v1_implemented",
    "logical_occurrence_closed",
    "campaign_closure_issued",
    "official_execution_allowed",
    "budget_replay_attestation_id",
}


def _verify_budget_attestation(document: Mapping[str, Any]) -> str:
    _exact_fields(
        document,
        _BUDGET_ATTESTATION_FIELDS,
        "budget replay attestation",
    )
    payload = dict(document)
    supplied = payload.pop("budget_replay_attestation_id")
    if supplied != content_id(
        V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN,
        payload,
    ):
        _fail("budget replay attestation content ID changed")
    closure = document["budget_closure"]
    verification = document["budget_closure_verification"]
    if type(closure) is not dict or type(verification) is not dict:
        _fail("budget replay attestation lacks nested evidence")
    cap = closure.get("cap_profile")
    replay = closure.get("trusted_budget_replay")
    promotion_verification = closure.get("promotion_bundle_verification")
    observer = closure.get("observer_closure")
    if not all(
        type(row) is dict
        for row in (cap, replay, promotion_verification, observer)
    ):
        _fail("budget replay nested evidence is malformed")
    _exact_fields(
        cap,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "child_operator_profile_id",
            "worker_cap_profile_id",
            "maximum_promotion_rounds",
            "promotion_draws_per_round",
            "maximum_total_promotion_draws",
            "selection_rule",
            "post_run_cap_adjustment_allowed",
            "candidate_required_before_total_lift",
            "cap_profile_id",
        },
        "budget cap profile",
    )
    _exact_fields(
        replay,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "cap_profile_id",
            "promotion_bundle_id",
            "promotion_bundle_verification_id",
            "final_model_epoch_id",
            "final_proof_id",
            "final_frontier_id",
            "decision_ids",
            "barrier_ids",
            "executed_round_count",
            "executed_promotion_draw_count",
            "registered_round_budget_exactly_replayed",
            "registered_draw_budget_exactly_replayed",
            "final_proof_still_failed",
            "candidate_present",
            "infeasibility_proven",
            "selected_fq9_terminal_class",
            "selected_fq9_terminal_code",
            "trusted_budget_replay_id",
        },
        "trusted budget replay",
    )
    _exact_fields(
        promotion_verification,
        {
            "schema",
            "schema_version",
            "bundle_id",
            "child_execution_bundle_id",
            "final_model_epoch_id",
            "final_proof_id",
            "outcome",
            "executed_round_count",
            "all_decisions_exactly_replayed",
            "all_signed_appends_exactly_replayed",
            "all_model_and_proof_barriers_exactly_replayed",
            "observer_closed",
            "official_execution_allowed",
            "verification_id",
        },
        "promotion bundle verification",
    )
    _exact_fields(
        observer,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "batch_journal_closure_id",
            "control_closure_id",
            "reconciliation_id",
            "head_ids",
            "intent_ids",
            "append_receipt_ids",
            "support_freeze_ids",
            "support_freeze_count",
            "official_execution_allowed",
            "production_authorizing",
            "process_isolation_provided",
            "python_wrapper_is_not_process_isolation",
            "trusted_in_process_wrapper_order_replayed",
            "single_private_boundary_atomicity_proven",
            "exclusive_signer_ownership_proven",
            "wrapper_signer_reference_cleared_after_both_closures",
            "terminal_class",
        },
        "observer closure",
    )
    cap_payload = dict(cap)
    cap_id = cap_payload.pop("cap_profile_id", None)
    replay_payload = dict(replay)
    replay_id = replay_payload.pop("trusted_budget_replay_id", None)
    promotion_payload = dict(promotion_verification)
    promotion_verification_id = promotion_payload.pop("verification_id", None)
    closure_payload_keys = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "occurrence_id",
        "promotion_bundle_id",
        "promotion_bundle_verification_id",
        "cap_profile_id",
        "trusted_budget_replay_id",
        "final_model_epoch_id",
        "final_proof_id",
        "batch_journal_closure_id",
        "control_closure_id",
        "control_reconciliation_id",
        "final_head_id",
        "append_count",
        "total_accepted_draw_count",
        "observer_closed_and_exactly_reconciled",
        "terminal_scope",
        "selected_terminal_class",
        "selected_terminal_code",
        "conditional_normalization_target_selected",
        "semantic_terminal_verifier_status",
        "terminal_artifact_issued",
        "terminal_artifact_issuance_allowed",
        "counter_records_issued",
        "work_vector_issued",
        "official_execution_allowed",
    }
    _exact_fields(
        closure,
        closure_payload_keys
        | {
            "cap_profile",
            "trusted_budget_replay",
            "promotion_bundle_verification",
            "observer_closure",
            "closure_id",
        },
        "budget closure",
    )
    _exact_fields(
        verification,
        {
            "schema",
            "schema_version",
            "closure_id",
            "promotion_bundle_id",
            "trusted_budget_replay_id",
            "control_reconciliation_id",
            "final_model_epoch_id",
            "terminal_class",
            "terminal_code",
            "promotion_bundle_exactly_replayed",
            "registered_budget_exactly_replayed",
            "signed_observer_closure_exactly_reconciled",
            "terminal_artifact_issued",
            "official_execution_allowed",
            "verification_id",
        },
        "budget closure verification",
    )
    closure_payload = {key: closure[key] for key in closure_payload_keys}
    verification_payload = dict(verification)
    verification_id = verification_payload.pop("verification_id", None)
    if (
        cap_id != _raw_domain_id(_BUDGET_CAP_DOMAIN, cap_payload)
        or replay_id != _raw_domain_id(_BUDGET_REPLAY_DOMAIN, replay_payload)
        or promotion_verification_id
        != _raw_domain_id(_PROMOTION_VERIFICATION_DOMAIN, promotion_payload)
        or closure.get("closure_id")
        != _raw_domain_id(_BUDGET_CLOSURE_DOMAIN, closure_payload)
        or verification_id
        != _raw_domain_id(_BUDGET_VERIFICATION_DOMAIN, verification_payload)
    ):
        _fail("budget replay nested content ID changed")
    decisions = replay.get("decision_ids")
    barriers = replay.get("barrier_ids")
    if (
        type(decisions) is not list
        or type(barriers) is not list
        or len(decisions) != 2
        or len(barriers) != 2
        or any(_cid(value, "budget decision") != value for value in decisions)
        or any(_cid(value, "budget barrier") != value for value in barriers)
        or cap.get("maximum_promotion_rounds") != 2
        or cap.get("promotion_draws_per_round") != 2_048
        or cap.get("maximum_total_promotion_draws") != 4_096
        or cap.get("selection_rule")
        != "MAX_INTERVAL_WIDTH_SUM_THEN_MAX_OTHER_UPPER_THEN_MIN_ROW_ID"
        or replay.get("executed_round_count") != 2
        or replay.get("executed_promotion_draw_count") != 4_096
        or replay.get("registered_round_budget_exactly_replayed") is not True
        or replay.get("registered_draw_budget_exactly_replayed") is not True
        or replay.get("final_proof_still_failed") is not True
        or replay.get("candidate_present") is not False
        or replay.get("infeasibility_proven") is not False
        or promotion_verification.get("outcome")
        != "PROMOTION_BUDGET_EXHAUSTED"
        or promotion_verification.get("executed_round_count") != 2
        or closure.get("observer_closed_and_exactly_reconciled") is not True
        or closure.get("selected_terminal_class")
        != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or closure.get("selected_terminal_code") != "ATTEMPT_BUDGET_EXHAUSTED"
        or verification.get("registered_budget_exactly_replayed") is not True
        or verification.get("signed_observer_closure_exactly_reconciled")
        is not True
        or document["executed_round_count"] != 2
        or document["executed_promotion_draw_count"] != 4_096
        or document["terminal_scope"] != "ROUTE_ATTEMPT"
        or document["terminal_class"]
        != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or document["terminal_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
        or document[
            "sealed_worker_exact_budget_closure_verification_consumed"
        ]
        is not True
        or document["registered_cap_replayed_before_terminal_mapping"] is not True
        or document["worker_outcome_string_used_as_authority"] is not False
        or document["construction_specific_semantic_authority"] is not True
        or document["generic_trusted_budget_replay_v1_implemented"] is not False
        or document["logical_occurrence_closed"] is not False
        or document["campaign_closure_issued"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("budget replay registered-cap semantics changed")
    if (
        document["occurrence_id"] != closure.get("occurrence_id")
        or document["budget_closure_id"] != closure.get("closure_id")
        or document["budget_closure_verification_id"] != verification_id
        or document["cap_profile_id"] != cap_id
        or document["trusted_budget_replay_id"] != replay_id
        or document["promotion_bundle_id"] != closure.get("promotion_bundle_id")
        or document["final_model_epoch_id"] != closure.get("final_model_epoch_id")
        or document["final_proof_id"] != closure.get("final_proof_id")
        or document["final_frontier_id"] != replay.get("final_frontier_id")
        or verification.get("closure_id") != closure.get("closure_id")
        or verification.get("promotion_bundle_id")
        != closure.get("promotion_bundle_id")
        or verification.get("trusted_budget_replay_id") != replay_id
        or closure.get("cap_profile_id") != cap_id
        or closure.get("trusted_budget_replay_id") != replay_id
        or closure.get("promotion_bundle_verification_id")
        != promotion_verification_id
        or replay.get("promotion_bundle_verification_id")
        != promotion_verification_id
    ):
        _fail("budget replay attestation identity graph crossed")
    for key in (
        "occurrence_id",
        "budget_closure_id",
        "budget_closure_verification_id",
        "cap_profile_id",
        "trusted_budget_replay_id",
        "promotion_bundle_id",
        "final_model_epoch_id",
        "final_proof_id",
        "final_frontier_id",
    ):
        _cid(document[key], f"budget replay {key}")
    return supplied


TRACE_FIELDS = {
    "artifact_role",
    "schema",
    "schema_version",
    "profile_key",
    "supervised_request_id",
    "runtime_preparation_id",
    "runtime_tree_id",
    "science_summary",
    "budget_replay_attestation",
    "recorded_stages",
    "business_hash_invocations",
    "child_integrity_obligations",
    "child_protocol_obligations",
    "child_self_peak_working_bytes_diagnostic",
    "hash_measurement_window_start",
    "hash_measurement_window_end",
    "accounting_provenance_hashes_excluded",
    "global_hashlib_sha256_constructor_hook_present",
    "construction_only",
    "fresh_heldout_accessed",
    "formal_counter_record_issued_by_worker",
    "occurrence_vector_issued_by_worker",
    "official_execution_allowed",
    "operational_trace_id",
}


def _verify_trace(
    document: Mapping[str, Any],
    raw: bytes,
    *,
    preparation_id: str,
    request_id: str,
    runtime_tree_id: str,
) -> tuple[str, dict[str, Any], tuple[live_v3.RecordedStageWorkV3, ...]]:
    _exact_fields(document, TRACE_FIELDS, "causal-promotion operational trace")
    payload = dict(document)
    supplied = payload.pop("operational_trace_id")
    if (
        document["artifact_role"] != "OPERATIONAL_TRACE"
        or document["schema"]
        != "acfqp.v075_k7_causal_promotion_operational_trace.v2"
        or document["schema_version"] != "2.0.0"
        or document["profile_key"]
        != "v075_k7_causal_promotion_accounted_runtime_v1"
        or document["runtime_preparation_id"] != preparation_id
        or document["supervised_request_id"] != request_id
        or document["runtime_tree_id"] != runtime_tree_id
        or supplied
        != content_id(
            V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN,
            payload,
        )
        or document["hash_measurement_window_start"]
        != "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS"
        or document["hash_measurement_window_end"]
        != "AFTER_STAGE_AND_TERMINAL_REPLAY_BEFORE_TRACE_PROVENANCE"
        or document["accounting_provenance_hashes_excluded"] is not True
        or document["global_hashlib_sha256_constructor_hook_present"] is not True
        or document["construction_only"] is not True
        or document["fresh_heldout_accessed"] is not False
        or document["formal_counter_record_issued_by_worker"] is not False
        or document["occurrence_vector_issued_by_worker"] is not False
        or document["official_execution_allowed"] is not False
        or canonical_json_bytes(dict(document)) != raw
    ):
        _fail("operational trace contract or content ID changed")
    if (
        document["child_integrity_obligations"] != list(EXPECTED_CHILD_INTEGRITY)
        or document["child_protocol_obligations"] != list(EXPECTED_CHILD_PROTOCOL)
        or type(document["business_hash_invocations"]) is not int
        or document["business_hash_invocations"] <= 0
        or type(document["child_self_peak_working_bytes_diagnostic"]) is not int
        or document["child_self_peak_working_bytes_diagnostic"] <= 0
    ):
        _fail("operational trace measurement inventory changed")
    budget_id = _verify_budget_attestation(document["budget_replay_attestation"])
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    rows = document["recorded_stages"]
    if type(rows) is not list or len(rows) != 12:
        _fail("operational trace must retain exactly twelve stages")
    try:
        stages = tuple(
            live_v3.RecordedStageWorkV3.from_document(
                row,
                registry,
                stage_profile,
                comparison,
                actual,
            )
            for row in rows
        )
    except Exception as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            "portable stage graph failed independent replay"
        ) from error
    if tuple(row.stage_start.stage_kind.value for row in stages) != STAGE_PLAN:
        _fail("portable stage plan changed")
    science = document["science_summary"]
    if type(science) is not dict:
        _fail("science summary is not one object")
    expected_science_fields = {
        "occurrence_id",
        "accounted_occurrence_id",
        "owned_accounting_result_id",
        "schedule_id",
        "schedule_verification_id",
        "root_execution_id",
        "root_model_epoch_id",
        "causal_child_authorization_id",
        "causal_child_execution_bundle_id",
        "causal_promotion_bundle_id",
        "budget_closure_id",
        "budget_closure_verification_id",
        "budget_replay_attestation_id",
        "terminal_class",
        "terminal_code",
        "route_attempts",
        "route_successes",
        "route_failures",
        "solver_attempts",
        "solver_successes",
        "solver_failures",
        "observer_closed_and_exactly_reconciled",
        "stage_instance_count",
        "stage_local_counter_record_count",
    }
    _exact_fields(science, expected_science_fields, "science summary")
    for key in (
        "occurrence_id",
        "accounted_occurrence_id",
        "owned_accounting_result_id",
        "schedule_id",
        "schedule_verification_id",
        "root_execution_id",
        "root_model_epoch_id",
        "causal_child_authorization_id",
        "causal_child_execution_bundle_id",
        "causal_promotion_bundle_id",
        "budget_closure_id",
        "budget_closure_verification_id",
        "budget_replay_attestation_id",
    ):
        _cid(science[key], f"science summary {key}")
    attestation = document["budget_replay_attestation"]
    if (
        science["budget_replay_attestation_id"] != budget_id
        or science["occurrence_id"] != attestation["occurrence_id"]
        or science["budget_closure_id"] != attestation["budget_closure_id"]
        or science["budget_closure_verification_id"]
        != attestation["budget_closure_verification_id"]
        or science["terminal_class"] != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or science["terminal_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
        or (
            science["route_attempts"],
            science["route_successes"],
            science["route_failures"],
        )
        != (1, 0, 1)
        or (
            science["solver_attempts"],
            science["solver_successes"],
            science["solver_failures"],
        )
        != (0, 0, 0)
        or science["observer_closed_and_exactly_reconciled"] is not True
        or science["stage_instance_count"] != 12
        or science["stage_local_counter_record_count"] != 2_424
    ):
        _fail("science summary semantics or attestation join changed")
    return supplied, science, stages


def _verify_measurement(
    document: Mapping[str, Any],
    *,
    preparation_id: str,
    request_id: str,
    request_bytes: int,
    trace_id: str,
    trace_bytes: int,
    trace_document: Mapping[str, Any],
    manifest: RuntimeTreeManifestV1,
    source_closure_id: str,
    science: Mapping[str, Any],
) -> tuple[str, dict[str, int]]:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "runtime_preparation_id",
        "runtime_tree_id",
        "source_closure_id",
        "supervised_request_id",
        "operational_trace_id",
        "occurrence_id",
        "accounted_occurrence_id",
        "owned_accounting_result_id",
        "runtime_file_count",
        "runtime_total_bytes",
        "runtime_manifest_document_bytes",
        "request_bytes",
        "operational_trace_bytes",
        "child_wait4_peak_bytes",
        "parent_hash_invocations",
        "child_hash_invocations",
        "parent_integrity_obligations",
        "child_integrity_obligations",
        "parent_protocol_obligations",
        "child_protocol_obligations",
        "fixed_pre_output_values",
        "pre_output_mounted_bytes_peak",
        "mounted_peak_final_formula",
        "output_counter_record_pending_fixed_point_and_commit",
        "process_exit_successes",
        "process_exit_failures",
        "read_value_kind",
        "staged_value_kind",
        "working_value_kind",
        "construction_only",
        "formal_counter_records_issued_here",
        "official_execution_allowed",
        "shared_measurement_id",
    }
    _exact_fields(document, fields, "causal-promotion shared measurement")
    numeric_fields = (
        "runtime_file_count",
        "runtime_total_bytes",
        "runtime_manifest_document_bytes",
        "request_bytes",
        "operational_trace_bytes",
        "child_wait4_peak_bytes",
        "parent_hash_invocations",
        "child_hash_invocations",
    )
    if any(type(document[key]) is not int or document[key] <= 0 for key in numeric_fields):
        _fail("shared measurement requires positive exact numeric evidence")
    fixed = {
        "common.hash_invocations": (
            document["parent_hash_invocations"]
            + document["child_hash_invocations"]
        ),
        "common.integrity_checks": (
            len(EXPECTED_PARENT_INTEGRITY) + len(EXPECTED_CHILD_INTEGRITY)
        ),
        "common.protocol_checks": (
            len(EXPECTED_PARENT_PROTOCOL) + len(EXPECTED_CHILD_PROTOCOL)
        ),
        "io.read_bytes": (
            document["runtime_manifest_document_bytes"]
            + 6 * document["runtime_total_bytes"]
            + document["request_bytes"]
            + document["operational_trace_bytes"]
        ),
        "io.staged_bytes": (
            document["runtime_total_bytes"] + document["request_bytes"]
        ),
        "memory.working_bytes_peak": document["child_wait4_peak_bytes"],
        "process.launches": 1,
    }
    expected_rows = [
        {"path": path, "value": value} for path, value in sorted(fixed.items())
    ]
    payload = dict(document)
    supplied = payload.pop("shared_measurement_id")
    if (
        document["schema"]
        != "acfqp.v075_k7_causal_promotion_shared_measurement.v1"
        or document["schema_version"] != "1.0.0"
        or document["profile_key"]
        != "v075_k7_causal_promotion_accounted_executor_v1"
        or document["runtime_preparation_id"] != preparation_id
        or document["runtime_tree_id"] != manifest.runtime_tree_id
        or document["source_closure_id"] != source_closure_id
        or document["supervised_request_id"] != request_id
        or document["operational_trace_id"] != trace_id
        or document["occurrence_id"] != science["occurrence_id"]
        or document["accounted_occurrence_id"] != science["accounted_occurrence_id"]
        or document["owned_accounting_result_id"]
        != science["owned_accounting_result_id"]
        or document["runtime_file_count"] != len(manifest.entries)
        or document["runtime_total_bytes"] != manifest.total_bytes
        or document["runtime_manifest_document_bytes"]
        != len(canonical_json_bytes(manifest.to_dict()))
        or document["request_bytes"] != request_bytes
        or document["operational_trace_bytes"] != trace_bytes
        or document["child_hash_invocations"]
        != trace_document["business_hash_invocations"]
        or document["parent_integrity_obligations"]
        != list(EXPECTED_PARENT_INTEGRITY)
        or document["child_integrity_obligations"]
        != list(EXPECTED_CHILD_INTEGRITY)
        or document["parent_protocol_obligations"]
        != list(EXPECTED_PARENT_PROTOCOL)
        or document["child_protocol_obligations"]
        != list(EXPECTED_CHILD_PROTOCOL)
        or document["fixed_pre_output_values"] != expected_rows
        or document["pre_output_mounted_bytes_peak"]
        != manifest.total_bytes + request_bytes + trace_bytes
        or document["mounted_peak_final_formula"]
        != "max(pre_output_peak,io.output_bytes)"
        or document["output_counter_record_pending_fixed_point_and_commit"]
        is not True
        or document["process_exit_successes"] != 1
        or document["process_exit_failures"] != 0
        or document["construction_only"] is not True
        or document["formal_counter_records_issued_here"] is not False
        or document["official_execution_allowed"] is not False
        or supplied
        != content_id(
            V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN,
            payload,
        )
    ):
        _fail("shared measurement formula, identity, or boundary changed")
    return supplied, fixed


def _verify_aggregation_and_accounting(
    documents: Mapping[str, Mapping[str, Any]],
    *,
    output_bytes: int,
    output_profile_id: str,
    occurrence_id: str,
    execution_id: str,
    trace_id: str,
    measurement_id: str,
    pre_output_peak: int,
    fixed_values: Mapping[str, int],
    stages: tuple[live_v3.RecordedStageWorkV3, ...],
) -> tuple[
    WorkVectorV1,
    ComparisonVectorV1,
    ActualProjectionProofV1,
]:
    registry = registry_v6.official_counter_registry_v6()
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry,
        comparison_profile,
    )
    counter_set = documents["COUNTER_RECORD_SET"]
    work_artifact = documents["WORK_VECTOR"]
    comparison_artifact = documents["COMPARISON_VECTOR"]
    proof_artifact = documents["ACTUAL_PROJECTION_PROOF"]
    _exact_fields(
        counter_set,
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "io.output_bytes",
            "counter_record_count",
            "path_aggregations",
            "counter_records",
        },
        "counter record set",
    )
    for role, document, nested in (
        ("WORK_VECTOR", work_artifact, "work_vector"),
        ("COMPARISON_VECTOR", comparison_artifact, "comparison_vector"),
        (
            "ACTUAL_PROJECTION_PROOF",
            proof_artifact,
            "actual_projection_proof",
        ),
    ):
        _exact_fields(
            document,
            {"artifact_role", "schema", "io.output_bytes", nested},
            role.lower(),
        )
        if document["artifact_role"] != role or document["io.output_bytes"] != output_bytes:
            _fail(f"{role} wrapper changed")
    if (
        counter_set["artifact_role"] != "COUNTER_RECORD_SET"
        or counter_set["schema"]
        != "acfqp.v075_k7_causal_promotion_counter_record_set.v1"
        or counter_set["occurrence_id"] != occurrence_id
        or counter_set["io.output_bytes"] != output_bytes
        or counter_set["counter_record_count"] != 202
        or type(counter_set["path_aggregations"]) is not list
        or type(counter_set["counter_records"]) is not list
        or len(counter_set["path_aggregations"]) != 202
        or len(counter_set["counter_records"]) != 202
        or work_artifact["schema"]
        != "acfqp.v075_k7_causal_promotion_work_vector_artifact.v1"
        or comparison_artifact["schema"]
        != "acfqp.v075_k7_causal_promotion_comparison_vector_artifact.v1"
        or proof_artifact["schema"]
        != "acfqp.v075_k7_causal_promotion_projection_artifact.v1"
    ):
        _fail("formal accounting wrapper inventory changed")
    try:
        vector_document = work_artifact["work_vector"]
        _exact_fields(
            vector_document,
            {
                "schema",
                "counter_registry_id",
                "subject_id",
                "route_kind",
                "counter_record_ids",
                "records",
                "work_vector_id",
            },
            "V6 WorkVector",
        )
        if (
            vector_document["schema"] != "acfqp.work_vector.v1"
            or type(vector_document["records"]) is not list
            or type(vector_document["counter_record_ids"]) is not list
        ):
            _fail("V6 WorkVector schema changed")
        vector_records = tuple(
            CounterRecordV1.from_dict(row)
            for row in vector_document["records"]
        )
        if vector_document["counter_record_ids"] != [
            row.record_id for row in vector_records
        ]:
            _fail("V6 WorkVector record IDs changed")
        vector = WorkVectorV1(
            vector_document["counter_registry_id"],
            vector_document["subject_id"],
            vector_document["route_kind"],
            vector_records,
        )
        if (
            vector_document["work_vector_id"] != vector.work_vector_id
            or vector.counter_registry_id != registry.registry_id
            or tuple(row.path for row in vector.records)
            != registry.required_paths
        ):
            _fail("V6 WorkVector identity or registry binding changed")
        projected = ComparisonVectorV1.from_dict(
            comparison_artifact["comparison_vector"]
        )
        proof = ActualProjectionProofV1.from_dict(
            proof_artifact["actual_projection_proof"]
        )
    except Exception as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            "formal vector or projection artifact failed replay"
        ) from error
    if (
        vector.subject_id != occurrence_id
        or vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or tuple(row.path for row in vector.records) != registry.required_paths
        or counter_set["counter_records"]
        != [row.to_dict() for row in vector.records]
    ):
        _fail("WorkVector subject, path inventory, or CounterRecord set changed")
    stage_records = tuple(
        {record.path: record for record in stage.work_vector.records}
        for stage in stages
    )
    if any(tuple(sorted(rows)) != registry.required_paths for rows in stage_records):
        _fail("stage path inventory changed")
    if any(rows[path].value != 0 for rows in stage_records for path in SHARED_PATHS):
        _fail("stage shared-resource placeholder became nonzero")
    aggregation_fields = {
        "schema",
        "schema_version",
        "occurrence_id",
        "supervised_execution_id",
        "path",
        "reducer",
        "value",
        "stage_record_ids",
        "source_kind",
        "source_evidence_id",
        "output_fixed_point_profile_id",
        "output_candidate",
        "all_stage_instances_retained",
        "shared_stage_placeholders_replaced_not_summed",
        "path_aggregation_id",
    }
    for index, path in enumerate(registry.required_paths):
        row = counter_set["path_aggregations"][index]
        if type(row) is not dict:
            _fail("path aggregation is not one object")
        _exact_fields(row, aggregation_fields, "path aggregation")
        leaf = registry.by_path[path]
        stage_path_records = tuple(rows[path] for rows in stage_records)
        if path == "io.output_bytes":
            expected_value = output_bytes
            source_kind = "OUTPUT_FIXED_POINT"
            source_id = output_profile_id
        elif path == "io.mounted_bytes_peak":
            expected_value = max(pre_output_peak, output_bytes)
            source_kind = "SHARED_MEASUREMENT"
            source_id = measurement_id
        elif path in fixed_values:
            expected_value = fixed_values[path]
            source_kind = "SHARED_MEASUREMENT"
            source_id = measurement_id
        elif path in DERIVED_PATHS:
            expected_value = DERIVED_PATHS[path]
            source_kind = "SEMANTIC_DERIVED_RECONCILIATION"
            source_id = trace_id
        elif leaf.reducer is ReducerEnum.SUM:
            expected_value = sum(record.value for record in stage_path_records)
            source_kind = "STAGE_SUM"
            source_id = execution_id
        else:
            expected_value = max(record.value for record in stage_path_records)
            source_kind = "STAGE_MAX"
            source_id = execution_id
        payload = dict(row)
        aggregation_id = payload.pop("path_aggregation_id")
        if (
            row["schema"]
            != "acfqp.v075_k7_causal_promotion_path_aggregation.v1"
            or row["schema_version"] != "1.0.0"
            or row["occurrence_id"] != occurrence_id
            or row["supervised_execution_id"] != execution_id
            or row["path"] != path
            or row["reducer"] != leaf.reducer.value
            or row["value"] != expected_value
            or row["stage_record_ids"]
            != [record.record_id for record in stage_path_records]
            or row["source_kind"] != source_kind
            or row["source_evidence_id"] != source_id
            or row["output_fixed_point_profile_id"]
            != (output_profile_id if path == "io.output_bytes" else None)
            or row["output_candidate"]
            != (output_bytes if path == "io.output_bytes" else None)
            or row["all_stage_instances_retained"] is not True
            or row["shared_stage_placeholders_replaced_not_summed"]
            is not (path in SHARED_PATHS)
            or aggregation_id
            != content_id(
                V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN,
                payload,
            )
            or vector.records[index].value != expected_value
            or vector.records[index].recorder_id != aggregation_id
            or counter_set["counter_records"][index]
            != vector.records[index].to_dict()
        ):
            _fail(f"path aggregation or CounterRecord changed for {path}")
        try:
            vector.records[index].verify_against(leaf)
        except Exception as error:
            raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
                f"CounterRecord metadata changed for {path}"
            ) from error
    values = vector.values
    if (
        values["route.attempts"]
        != values["route.successes"] + values["route.failures"]
        or values["solver.attempts"]
        != values["solver.successes"] + values["solver.failures"]
        or values["process.launches"]
        != values["process.exit_successes"] + values["process.exit_failures"]
        or any(
            value
            for path, value in values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )
    ):
        _fail("occurrence work reconciliation or failed-prefix exclusivity changed")
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in actual_profile.terms:
        contribution = values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    expected_projected = ComparisonVectorV1(
        comparison_profile.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple(sorted(axes.items())),
    )
    expected_proof = ActualProjectionProofV1(
        actual_profile.actual_projection_profile_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        vector.work_vector_id,
        expected_projected.comparison_vector_id,
        LaneEnum.OPERATIONAL,
        ActualWorkScope.COMMON_PREFIX,
        len(actual_profile.terms),
    )
    if (
        projected != expected_projected
        or proof != expected_proof
        or proof.projection_term_count != 182
    ):
        _fail("182-term actual projection changed")
    return vector, projected, proof


def _verify_terminal(
    document: Mapping[str, Any],
    *,
    output_bytes: int,
    budget_attestation: Mapping[str, Any],
    occurrence_id: str,
    accounted_occurrence_id: str,
    execution_id: str,
    vector: WorkVectorV1,
    comparison: ComparisonVectorV1,
    proof: ActualProjectionProofV1,
) -> TerminalArtifactV1:
    fields = {
        "artifact_role",
        "schema",
        "schema_version",
        "profile_key",
        "io.output_bytes",
        "route_decision_context",
        "route_attempt",
        "budget_terminal_derivation_attestation",
        "terminal_artifact",
        "semantic_terminal_artifact_issued",
        "construction_specific_terminal_authority",
        "generic_trusted_budget_replay_v1_implemented",
        "logical_occurrence_closed",
        "campaign_closure_issued",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
    }
    _exact_fields(document, fields, "causal-promotion terminal bundle")
    context = document["route_decision_context"]
    attempt = document["route_attempt"]
    derivation = document["budget_terminal_derivation_attestation"]
    if not all(type(row) is dict for row in (context, attempt, derivation)):
        _fail("terminal bundle nested documents are malformed")
    _exact_fields(
        context,
        {
            "schema",
            "schema_version",
            "profile_key",
            "logical_occurrence_id",
            "accounted_occurrence_id",
            "supervised_execution_id",
            "budget_replay_attestation_id",
            "route_kind",
            "terminal_scope",
            "construction_specific_context",
            "generic_marginal_route_decision_present",
            "official_execution_allowed",
            "route_decision_context_id",
        },
        "terminal route context",
    )
    _exact_fields(
        attempt,
        {
            "schema",
            "schema_version",
            "profile_key",
            "logical_occurrence_id",
            "route_decision_context_id",
            "route_attempt_index",
            "budget_replay_attestation_id",
            "terminal_class",
            "terminal_code",
            "logical_occurrence_closed",
            "official_execution_allowed",
            "route_attempt_id",
        },
        "terminal route attempt",
    )
    _exact_fields(
        derivation,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "logical_occurrence_id",
            "route_decision_context_id",
            "route_attempt_id",
            "budget_replay_attestation_id",
            "budget_closure_id",
            "budget_closure_verification_id",
            "trusted_budget_replay_id",
            "actual_work_vector_id",
            "actual_comparison_vector_id",
            "actual_projection_proof_id",
            "counter_record_count",
            "projection_term_count",
            "route_attempt_count",
            "route_success_count",
            "route_failure_count",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "sealed_worker_budget_replay_joined_to_formal_actual_work",
            "failed_route_work_preserved",
            "worker_outcome_string_used_as_authority",
            "generic_trusted_budget_replay_v1_implemented",
            "construction_specific_terminal_authority",
            "terminal_is_plan_certificate",
            "terminal_is_infeasibility_certificate",
            "logical_occurrence_closed",
            "campaign_closure_issued",
            "counter_completeness_gate_passed",
            "workload_economics_gate_passed",
            "official_scalar_cost",
            "official_N_break_even",
            "official_execution_allowed",
            "terminal_derivation_attestation_id",
        },
        "budget terminal derivation",
    )
    context_payload = dict(context)
    context_id = context_payload.pop("route_decision_context_id", None)
    attempt_payload = dict(attempt)
    attempt_id = attempt_payload.pop("route_attempt_id", None)
    derivation_payload = dict(derivation)
    derivation_id = derivation_payload.pop(
        "terminal_derivation_attestation_id", None
    )
    if (
        document["artifact_role"] != "TERMINAL_ARTIFACT"
        or document["schema"]
        != "acfqp.v075_k7_causal_promotion_terminal_artifact_bundle.v1"
        or document["schema_version"] != "1.0.0"
        or document["profile_key"]
        != "v075_k7_causal_promotion_terminal_authority_v1"
        or document["io.output_bytes"] != output_bytes
        or context_id
        != content_id(
            V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN,
            context_payload,
        )
        or attempt_id
        != content_id(
            V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN,
            attempt_payload,
        )
        or derivation_id
        != content_id(
            V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN,
            derivation_payload,
        )
        or context.get("logical_occurrence_id") != occurrence_id
        or context.get("accounted_occurrence_id") != accounted_occurrence_id
        or context.get("supervised_execution_id") != execution_id
        or context.get("budget_replay_attestation_id")
        != budget_attestation["budget_replay_attestation_id"]
        or context.get("route_kind") != "ABSTRACT_FAILED_PREFIX"
        or context.get("terminal_scope") != "ROUTE_ATTEMPT"
        or context.get("construction_specific_context") is not True
        or context.get("generic_marginal_route_decision_present") is not False
        or context.get("official_execution_allowed") is not False
        or attempt.get("logical_occurrence_id") != occurrence_id
        or attempt.get("route_decision_context_id") != context_id
        or attempt.get("route_attempt_index") != 1
        or attempt.get("budget_replay_attestation_id")
        != budget_attestation["budget_replay_attestation_id"]
        or attempt.get("terminal_class")
        != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or attempt.get("terminal_code") != "ATTEMPT_BUDGET_EXHAUSTED"
        or attempt.get("logical_occurrence_closed") is not False
        or attempt.get("official_execution_allowed") is not False
        or derivation.get("logical_occurrence_id") != occurrence_id
        or derivation.get("route_decision_context_id") != context_id
        or derivation.get("route_attempt_id") != attempt_id
        or derivation.get("budget_replay_attestation_id")
        != budget_attestation["budget_replay_attestation_id"]
        or derivation.get("budget_closure_id")
        != budget_attestation["budget_closure_id"]
        or derivation.get("budget_closure_verification_id")
        != budget_attestation["budget_closure_verification_id"]
        or derivation.get("trusted_budget_replay_id")
        != budget_attestation["trusted_budget_replay_id"]
        or derivation.get("actual_work_vector_id") != vector.work_vector_id
        or derivation.get("actual_comparison_vector_id")
        != comparison.comparison_vector_id
        or derivation.get("actual_projection_proof_id")
        != proof.actual_projection_proof_id
        or derivation.get("counter_record_count") != 202
        or derivation.get("projection_term_count") != 182
        or (
            derivation.get("route_attempt_count"),
            derivation.get("route_success_count"),
            derivation.get("route_failure_count"),
        )
        != (1, 0, 1)
        or derivation.get("construction_specific_terminal_authority") is not True
        or derivation.get("generic_trusted_budget_replay_v1_implemented") is not False
        or derivation.get("terminal_is_plan_certificate") is not False
        or derivation.get("terminal_is_infeasibility_certificate") is not False
        or derivation.get("logical_occurrence_closed") is not False
        or derivation.get("campaign_closure_issued") is not False
        or derivation.get("counter_completeness_gate_passed") is not False
        or derivation.get("workload_economics_gate_passed") is not False
        or derivation.get("official_scalar_cost") is not None
        or derivation.get("official_N_break_even") is not None
        or derivation.get("official_execution_allowed") is not False
        or document["semantic_terminal_artifact_issued"] is not True
        or document["construction_specific_terminal_authority"] is not True
        or document["generic_trusted_budget_replay_v1_implemented"] is not False
        or document["logical_occurrence_closed"] is not False
        or document["campaign_closure_issued"] is not False
        or document["counter_completeness_gate_status"]
        != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        or document["workload_economics_gate_status"]
        != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["official_execution_allowed"] is not False
    ):
        _fail("typed terminal derivation or bounded claims changed")
    try:
        terminal = TerminalArtifactV1.from_dict(document["terminal_artifact"])
    except Exception as error:
        raise V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error(
            "TerminalArtifactV1 failed strict replay"
        ) from error
    expected = TerminalArtifactV1(
        terminal_scope="ROUTE_ATTEMPT",
        terminal_class=TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
        terminal_code=TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
        route_decision_context_id=context_id,
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt_id,
        decision_point_id=TypedNotApplicable(
            "construction budget closure has no marginal route decision point"
        ),
        transaction_id=TypedNotApplicable(
            "construction promotion rounds are not Phase-3E local transactions"
        ),
        actual_work_vector_id=vector.work_vector_id,
        evidence_attestation_ids=tuple(
            sorted(
                (
                    budget_attestation["budget_replay_attestation_id"],
                    derivation_id,
                )
            )
        ),
        actual_comparison_vector_id=comparison.comparison_vector_id,
        actual_projection_proof_id=proof.actual_projection_proof_id,
        marginal_work_aggregation_proof_id=TypedNotApplicable(
            "construction failed-prefix work is one occurrence vector"
        ),
        route_decision_freeze_attestation_id=TypedNotApplicable(
            "construction path did not perform dynamic marginal routing"
        ),
        access_event_log_id=TypedNotApplicable(
            "construction path predates the official access-order runner"
        ),
    )
    if terminal != expected or terminal.to_dict() != document["terminal_artifact"]:
        _fail("typed TerminalArtifact differs from exact reconstruction")
    return terminal


def _verification_profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_k7_causal_promotion_complete_bundle_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "required_roles": list(REQUIRED_ROLES),
        "portable_source_identity_replay_required": True,
        "sealed_worker_budget_attestation_replay_required": True,
        "twelve_stage_replay_required": True,
        "complete_202_record_reconstruction_required": True,
        "exact_182_term_projection_required": True,
        "typed_terminal_reconstruction_required": True,
        "worker_reexecution_allowed": False,
        "producer_renderer_import_allowed": False,
        "evaluation_lane_only": True,
        "official_execution_allowed": False,
    }


VERIFICATION_PROFILE_ID = content_id(
    VERIFICATION_PROFILE_DOMAIN,
    _verification_profile_payload(),
)
SEMANTIC_VERIFIER_ID = content_id(
    SEMANTIC_VERIFIER_DOMAIN,
    {
        "schema": "acfqp.v075_k7_causal_promotion_complete_bundle_semantic_verifier.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "verification_profile_id": VERIFICATION_PROFILE_ID,
        "module": (
            "acfqp.v075_k7_causal_promotion_complete_bundle_"
            "independent_verifier_v1"
        ),
        "entrypoint": (
            "verify_v075_k7_causal_promotion_complete_bundle_bytes_v1"
        ),
        "producer_implementation_reused": False,
    },
)


@dataclass(frozen=True, slots=True)
class CausalPromotionCompleteBundleVerificationV1:
    _issuer: InitVar[object]
    occurrence_id: str
    supervised_execution_id: str
    operational_trace_id: str
    budget_replay_attestation_id: str
    terminal_artifact_id: str
    work_vector_id: str
    comparison_vector_id: str
    projection_proof_id: str
    output_bytes: int
    role_bindings: tuple[tuple[str, int, str], ...]
    evaluation_work_record: CounterRecordV1 = field(repr=False)
    typed_attestation: TypedVerificationAttestationV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("complete-bundle verification is caller-minted")
        for value, label in (
            (self.occurrence_id, "verification occurrence"),
            (self.supervised_execution_id, "verification execution"),
            (self.operational_trace_id, "verification trace"),
            (self.budget_replay_attestation_id, "verification budget attestation"),
            (self.terminal_artifact_id, "verification terminal"),
            (self.work_vector_id, "verification WorkVector"),
            (self.comparison_vector_id, "verification ComparisonVector"),
            (self.projection_proof_id, "verification projection proof"),
        ):
            _cid(value, label)
        if (
            type(self.output_bytes) is not int
            or self.output_bytes <= 0
            or type(self.role_bindings) is not tuple
            or tuple(row[0] for row in self.role_bindings) != REQUIRED_ROLES
            or any(
                type(row) is not tuple
                or len(row) != 3
                or type(row[1]) is not int
                or row[1] <= 0
                or _cid(row[2], "verified role digest") != row[2]
                for row in self.role_bindings
            )
            or sum(row[1] for row in self.role_bindings) != self.output_bytes
            or self.evaluation_work_record.path
            != "evaluation.semantic_protocol_checks"
            or self.evaluation_work_record.lane is not LaneEnum.EVALUATION
            or self.typed_attestation.verification_lane is not LaneEnum.EVALUATION
            or self.typed_attestation.artifact_id != self.terminal_artifact_id
            or self.typed_attestation.logical_occurrence_id != self.occurrence_id
        ):
            _fail("complete-bundle verification evidence is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_complete_bundle_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": VERIFICATION_PROFILE_ID,
            "semantic_verifier_id": SEMANTIC_VERIFIER_ID,
            "logical_occurrence_id": self.occurrence_id,
            "supervised_execution_id": self.supervised_execution_id,
            "operational_trace_id": self.operational_trace_id,
            "budget_replay_attestation_id": self.budget_replay_attestation_id,
            "terminal_artifact_id": self.terminal_artifact_id,
            "actual_work_vector_id": self.work_vector_id,
            "actual_comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.projection_proof_id,
            "counter_record_count": 202,
            "projection_term_count": 182,
            "role_bindings": [
                {"artifact_role": role, "byte_count": size, "bytes_sha256": digest}
                for role, size, digest in self.role_bindings
            ],
            "io.output_bytes": self.output_bytes,
            "evaluation_work_counter_record": self.evaluation_work_record.to_dict(),
            "typed_verification_attestation": self.typed_attestation.to_dict(),
            "all_eight_canonical_roles_replayed": True,
            "portable_source_and_runtime_identity_graph_replayed": True,
            "sealed_worker_budget_attestation_replayed": True,
            "twelve_stage_graphs_replayed": True,
            "all_202_counter_records_reconstructed": True,
            "all_182_operational_leaves_projected_exactly_once": True,
            "typed_attempt_budget_terminal_reconstructed": True,
            "output_byte_fixed_point_equation_replayed": True,
            "worker_reexecuted_by_independent_verifier": False,
            "original_source_files_reread_by_independent_verifier": False,
            "producer_renderer_imported": False,
            "verification_lane": "EVALUATION",
            "logical_occurrence_closed": False,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "complete_bundle_verification_id": self.verification_id,
        }


def verify_v075_k7_causal_promotion_complete_bundle_bytes_v1(
    role_bytes: Mapping[str, bytes],
) -> CausalPromotionCompleteBundleVerificationV1:
    """Independently replay one complete ordered eight-role byte bundle."""

    if type(role_bytes) is not dict or tuple(role_bytes) != REQUIRED_ROLES:
        _fail("complete bundle must contain the exact ordered eight roles")
    documents = {
        role: _canonical_object(role_bytes[role], role)
        for role in REQUIRED_ROLES
    }
    for role in REQUIRED_ROLES:
        if documents[role].get("artifact_role") != role:
            _fail(f"portable role label changed for {role}")
    manifest_document = documents["OUTPUT_MANIFEST"]
    _exact_fields(
        manifest_document,
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "output_bytes_fixed_point_profile_id",
            "io.output_bytes",
            "ordered_preceding_roles",
            "output_manifest_self_extent_excluded_from_preceding_rows",
            "required_role_order",
        },
        "output manifest",
    )
    output_bytes = sum(len(role_bytes[role]) for role in REQUIRED_ROLES)
    preceding = [
        {
            "artifact_role": role,
            "byte_count": len(role_bytes[role]),
            "bytes_sha256": hashlib.sha256(role_bytes[role]).hexdigest(),
        }
        for role in REQUIRED_ROLES[:-1]
    ]
    if (
        manifest_document["schema"]
        != "acfqp.v075_k7_causal_promotion_output_manifest.v1"
        or manifest_document["io.output_bytes"] != output_bytes
        or manifest_document["ordered_preceding_roles"] != preceding
        or manifest_document[
            "output_manifest_self_extent_excluded_from_preceding_rows"
        ]
        is not True
        or manifest_document["required_role_order"] != list(REQUIRED_ROLES)
    ):
        _fail("output manifest or final byte fixed-point equation changed")
    output_profile_id = _cid(
        manifest_document["output_bytes_fixed_point_profile_id"],
        "output fixed-point profile",
    )

    business = documents["BUSINESS_RESULT"]
    _exact_fields(
        business,
        {
            "artifact_role",
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "accounted_occurrence_id",
            "owned_accounting_result_id",
            "budget_closure_id",
            "shared_measurement_id",
            "runtime_preparation",
            "supervised_request",
            "shared_measurement",
            "terminal_target_class",
            "terminal_target_code",
            "construction_only",
            "official_execution_allowed",
        },
        "business result",
    )
    if (
        business["schema"]
        != "acfqp.v075_k7_causal_promotion_business_result.v2"
        or business["schema_version"] != "2.0.0"
        or business["profile_key"]
        != "v075_k7_causal_promotion_occurrence_accounting_v1"
        or business["terminal_target_class"]
        != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or business["terminal_target_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
        or business["construction_only"] is not True
        or business["official_execution_allowed"] is not False
    ):
        _fail("business-result contract changed")
    preparation_id, runtime_manifest = _verify_preparation(
        business["runtime_preparation"]
    )
    request_id = _verify_request(
        business["supervised_request"],
        preparation_id=preparation_id,
        runtime_tree_id=runtime_manifest.runtime_tree_id,
    )
    trace_id, science, stages = _verify_trace(
        documents["OPERATIONAL_TRACE"],
        role_bytes["OPERATIONAL_TRACE"],
        preparation_id=preparation_id,
        request_id=request_id,
        runtime_tree_id=runtime_manifest.runtime_tree_id,
    )
    measurement_id, fixed_values = _verify_measurement(
        business["shared_measurement"],
        preparation_id=preparation_id,
        request_id=request_id,
        request_bytes=len(canonical_json_bytes(business["supervised_request"])),
        trace_id=trace_id,
        trace_bytes=len(role_bytes["OPERATIONAL_TRACE"]),
        trace_document=documents["OPERATIONAL_TRACE"],
        manifest=runtime_manifest,
        source_closure_id=business["runtime_preparation"]["source_closure"]["closure_id"],
        science=science,
    )
    occurrence_id = _cid(business["occurrence_id"], "business occurrence")
    accounted_occurrence_id = _cid(
        business["accounted_occurrence_id"], "accounted occurrence"
    )
    if (
        occurrence_id != science["occurrence_id"]
        or occurrence_id != manifest_document["occurrence_id"]
        or business["accounted_occurrence_id"] != science["accounted_occurrence_id"]
        or business["owned_accounting_result_id"]
        != science["owned_accounting_result_id"]
        or business["budget_closure_id"] != science["budget_closure_id"]
        or business["shared_measurement_id"] != measurement_id
    ):
        _fail("business, trace, measurement, or output manifest crossed")
    vector, comparison, proof = _verify_aggregation_and_accounting(
        documents,
        output_bytes=output_bytes,
        output_profile_id=output_profile_id,
        occurrence_id=occurrence_id,
        execution_id=measurement_id,
        trace_id=trace_id,
        measurement_id=measurement_id,
        pre_output_peak=business["shared_measurement"][
            "pre_output_mounted_bytes_peak"
        ],
        fixed_values=fixed_values,
        stages=stages,
    )
    budget_attestation = documents["OPERATIONAL_TRACE"][
        "budget_replay_attestation"
    ]
    terminal = _verify_terminal(
        documents["TERMINAL_ARTIFACT"],
        output_bytes=output_bytes,
        budget_attestation=budget_attestation,
        occurrence_id=occurrence_id,
        accounted_occurrence_id=accounted_occurrence_id,
        execution_id=measurement_id,
        vector=vector,
        comparison=comparison,
        proof=proof,
    )
    registry = registry_v6.official_counter_registry_v6()
    leaf = registry.by_path["evaluation.semantic_protocol_checks"]
    evaluation_work = CounterRecordV1(
        registry.registry_id,
        leaf.path,
        1,
        True,
        SEMANTIC_VERIFIER_ID,
        leaf.semantics_id,
        leaf.owner,
        leaf.unit,
        leaf.lane,
        leaf.scope,
        leaf.reducer,
    )
    terminal_bundle = documents["TERMINAL_ARTIFACT"]
    context = terminal_bundle["route_decision_context"]
    attempt = terminal_bundle["route_attempt"]
    attestation = TypedVerificationAttestationV1(
        artifact_id=terminal.terminal_artifact_id,
        artifact_schema_id="TerminalArtifactV1",
        artifact_role="TERMINAL_CLASSIFICATION",
        route_decision_context_id=context["route_decision_context_id"],
        structural_id=runtime_manifest.runtime_tree_id,
        query_id=occurrence_id,
        selected_plan_id=budget_attestation["final_proof_id"],
        threshold_profile_id=budget_attestation["cap_profile_id"],
        build_epoch_id=budget_attestation["final_model_epoch_id"],
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt["route_attempt_id"],
        decision_point_id=TypedNotApplicable(
            "construction terminal has no marginal decision point"
        ),
        transaction_id=TypedNotApplicable(
            "construction promotion rounds are not local transactions"
        ),
        semantic_verifier_id=SEMANTIC_VERIFIER_ID,
        verification_profile_id=VERIFICATION_PROFILE_ID,
        verification_result="ATTEMPT_CLOSURE_NONCERTIFICATE",
        verification_work_counter_record_id=evaluation_work.record_id,
        verified_at_protocol_step=1,
        verification_lane=LaneEnum.EVALUATION,
    )
    bindings = tuple(
        (
            role,
            len(role_bytes[role]),
            hashlib.sha256(role_bytes[role]).hexdigest(),
        )
        for role in REQUIRED_ROLES
    )
    return CausalPromotionCompleteBundleVerificationV1(
        _VERIFICATION_ISSUER,
        occurrence_id,
        measurement_id,
        trace_id,
        budget_attestation["budget_replay_attestation_id"],
        terminal.terminal_artifact_id,
        vector.work_vector_id,
        comparison.comparison_vector_id,
        proof.actual_projection_proof_id,
        output_bytes,
        bindings,
        evaluation_work,
        attestation,
    )


def verify_v075_k7_causal_promotion_complete_bundle_directory_v1(
    directory: str | Path,
) -> CausalPromotionCompleteBundleVerificationV1:
    """Read the exact eight role files, then invoke the bytes-only verifier."""

    root = Path(directory).resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        _fail("complete-bundle directory must be one real directory")
    expected = tuple(sorted(f"{role}.json" for role in REQUIRED_ROLES))
    if tuple(sorted(path.name for path in root.iterdir())) != expected:
        _fail("complete-bundle directory role inventory changed")
    return verify_v075_k7_causal_promotion_complete_bundle_bytes_v1(
        {role: (root / f"{role}.json").read_bytes() for role in REQUIRED_ROLES}
    )


__all__ = (
    "CausalPromotionCompleteBundleVerificationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_ROLES",
    "SCHEMA_VERSION",
    "SEMANTIC_VERIFIER_ID",
    "VERIFICATION_PROFILE_ID",
    "V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error",
    "verify_v075_k7_causal_promotion_complete_bundle_bytes_v1",
    "verify_v075_k7_causal_promotion_complete_bundle_directory_v1",
)
