"""Replay the source occurrence's failure-triggered causal recovery chain.

The input is the additive recovery-export operational trace.  Its native
twelve-stage accounting and reusable BuildEpoch are replayed first.  This
module then verifies the exact root and successor planning proofs, binds the
failed root frontier to the causal authorization, binds the authorized rows
to the first successor ledger, checks the monotone four-epoch lineage, and
requires incremental ground draws to occur only after the registered failed
abstract-prefix stage.

The result is intentionally limited to the original construction occurrence.
It is not a fresh-query observer handoff, plan certificate, campaign closure,
or official execution authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_k7_causal_promotion_accounted_executor_v1 as executor_v1
from acfqp import v075_k7_causal_promotion_terminal_authority_v1 as terminal_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN,
    CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_REPLAY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.85"
PROFILE_KEY = "construction_k7_causal_recovery_chain_v1"

SOURCE_CHAIN_DOMAIN = CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("causal recovery chain domain is not central")

_RESULT_ISSUER = object()

_EPOCH_DOMAIN = "acfqp:v075-live-incremental-model-epoch:v2"
_ROW_SOURCE_DOMAIN = "acfqp:v075-live-incremental-row-source-binding:v2"
_AUTHORIZATION_DOMAIN = "acfqp:v075-live-batched-causal-child-authorization:v3"
_AUTHORIZATION_VERIFICATION_DOMAIN = (
    "acfqp:v075-live-batched-causal-child-verification:v3"
)
_EXECUTED_ROW_DOMAIN = "acfqp:v075-live-batched-causal-executed-row:v3"
_EXECUTION_LEDGER_DOMAIN = "acfqp:v075-live-batched-causal-execution-ledger:v3"
_EXECUTION_BUNDLE_DOMAIN = "acfqp:v075-live-batched-causal-execution-bundle:v3"
_PROMOTION_BUNDLE_DOMAIN = "acfqp:v075-live-batched-causal-promotion-bundle:v3"

_CHAIN_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_id",
    "root_model_epoch_id",
    "root_numerical_model_id",
    "root_proof_id",
    "root_frontier_id",
    "causal_child_authorization_id",
    "causal_child_authorization_verification_id",
    "causal_child_execution_bundle_id",
    "causal_promotion_bundle_id",
    "final_model_epoch_id",
    "final_numerical_model_id",
    "final_proof_id",
    "final_frontier_id",
    "root_model_epoch",
    "root_numerical_proof",
    "causal_child_authorization",
    "causal_child_authorization_verification",
    "causal_child_execution_bundle",
    "causal_promotion_bundle",
    "final_model_epoch",
    "final_numerical_proof",
    "root_failed_proof_precedes_causal_authorization",
    "authorization_target_access_count",
    "authorization_kernel_call_count",
    "ground_acquisition_executed_after_authorization",
    "immutable_successor_epoch_present",
    "post_recovery_replanning_present",
    "source_occurrence_recovery_only",
    "fresh_query_rebinding_performed",
    "local_ground_recovery_authority_for_fresh_query",
    "final_plan_certificate_issued",
    "official_execution_allowed",
    "causal_recovery_chain_id",
}

_EPOCH_PAYLOAD_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "terminal_scope",
    "terminal_class",
    "occurrence_id",
    "target_tape_namespace_id",
    "context_id",
    "arm",
    "head_id",
    "epoch_index",
    "parent_epoch_id",
    "open_prefix_verification_id",
    "append_receipt_ids",
    "support_freeze_ids",
    "route",
    "row_source_binding_ids",
    "numerical_model_id",
    "numerical_proof_id",
    "changed_row_binding_ids",
    "reused_row_binding_ids",
    "compiled_row_count",
    "reused_row_count",
    "full_proof_recompute_count",
    "unchanged_source_digest_requires_byte_identical_row",
    "full_numerical_proof_recomputed_each_epoch",
    "operational_parent_validation",
    "operational_parent_registry_is_not_portable_verification",
    "operational_parent_deep_snapshot_sha256_verified",
    "portable_verifier_recursively_verifies_parent_chain",
    "portable_verifier_uses_full_control_prefix_replay_each_epoch",
    "portable_verifier_recompiles_root_and_changed_rows",
    "portable_verifier_inherits_unchanged_rows_from_verified_parent",
    "complete_support_freeze_required_per_row",
    "validation_epoch_set",
    "operational_incremental_prefix_scope",
    "per_draw_records_used",
    "private_law_access",
    "official_execution_allowed",
    "production_authorizing",
    "plan_certificate",
    "infeasibility_certificate",
}
_EPOCH_FIELDS = _EPOCH_PAYLOAD_FIELDS | {
    "row_sources",
    "model",
    "proof",
    "model_epoch_id",
}

_AUTH_NESTED_FIELDS = {
    "source_v2_child_closure",
    "operator_profile",
    "candidates",
    "discovery_intents",
    "validation_templates",
}
_AUTH_PAYLOAD_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_model_epoch_id",
    "source_numerical_model_id",
    "source_proof_id",
    "source_frontier_id",
    "source_head_id",
    "source_v2_child_closure_id",
    "source_v2_child_closure_status",
    "operator_profile_id",
    "authorization_outcome",
    "candidate_ids",
    "selected_candidate_ids",
    "selected_child_state_ids",
    "selected_row_binding_ids",
    "discovery_intent_ids",
    "discovery_candidate_bindings",
    "validation_template_ids",
    "selected_child_catalogue_count",
    "selected_new_action_row_count",
    "incremental_draw_count",
    "maximum_new_child_action_rows",
    "maximum_incremental_draws",
    "selection_rule",
    "no_operator_control_retained",
    "all_root_support_descriptors_examined_by_control",
    "only_failed_frontier_successors_selected",
    "complete_selected_child_catalogues",
    "frozen_before_target_access",
    "observer_calls",
    "kernel_calls",
    "world_model_rows_written",
    "production_integration_ready",
    "plan_certificate",
    "infeasibility_certificate",
}


class ConstructionK7CausalRecoveryChainV1Error(ValueError):
    """The causal identity chain, ordering, or replanning proof changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CausalRecoveryChainV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CausalRecoveryChainV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _raw_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _exact_fields(document: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != expected:
        _fail(f"{label} field set changed")
    return document


def _replay_epoch(document: Any) -> tuple[str, planning_v2.V075NumericalPlanningProofV2]:
    epoch = _exact_fields(document, _EPOCH_FIELDS, "recovery model epoch")
    payload = {key: epoch[key] for key in _EPOCH_PAYLOAD_FIELDS}
    epoch_id = _cid(epoch["model_epoch_id"], "recovery model epoch")
    if (
        epoch["schema"] != "acfqp.v075_live_incremental_model_epoch.v2"
        or epoch_id != _raw_id(_EPOCH_DOMAIN, payload)
        or epoch["route"] != "ADAPTIVE_QUOTIENT"
        or epoch["full_numerical_proof_recomputed_each_epoch"] is not True
        or epoch["private_law_access"] is not False
        or epoch["plan_certificate"] is not False
        or epoch["official_execution_allowed"] is not False
    ):
        _fail("recovery model epoch contract changed")
    model_raw = canonical_json_bytes(epoch["model"])
    proof_raw = canonical_json_bytes(epoch["proof"])
    model = planning_v2.replay_v075_numerical_model_bytes_v2(model_raw)
    proof = planning_v2.replay_v075_numerical_proof_bytes_v2(proof_raw)
    rows = epoch["row_sources"]
    if type(rows) is not list or not rows:
        _fail("recovery model epoch row sources are absent")
    binding_ids: list[str] = []
    numerical_row_ids: list[str] = []
    for row in rows:
        if type(row) is not dict or "binding_id" not in row:
            _fail("recovery row source is malformed")
        row_payload = dict(row)
        binding_id = row_payload.pop("binding_id")
        if binding_id != _raw_id(_ROW_SOURCE_DOMAIN, row_payload):
            _fail("recovery row source content ID changed")
        binding_ids.append(binding_id)
        numerical_row_ids.append(row["numerical_row_id"])
    if (
        epoch["numerical_model_id"] != model.model_id
        or epoch["numerical_proof_id"] != proof.proof_id
        or proof.model.model_id != model.model_id
        or epoch["row_source_binding_ids"] != binding_ids
        or numerical_row_ids != [row.row_id for row in model.rows]
        or epoch["compiled_row_count"] != len(epoch["changed_row_binding_ids"])
        or epoch["reused_row_count"] != len(epoch["reused_row_binding_ids"])
    ):
        _fail("recovery epoch model, proof, or row identity crossed")
    return epoch_id, proof


def _replay_authorization(document: Any) -> dict[str, Any]:
    expected = _AUTH_PAYLOAD_FIELDS | _AUTH_NESTED_FIELDS | {"authorization_id"}
    auth = _exact_fields(document, expected, "causal authorization")
    payload = {key: auth[key] for key in _AUTH_PAYLOAD_FIELDS}
    if (
        auth["authorization_id"] != _raw_id(_AUTHORIZATION_DOMAIN, payload)
        or auth["schema"]
        != "acfqp.v075_live_batched_causal_child_authorization.v3"
        or auth["authorization_outcome"]
        != "BATCHED_CAUSAL_CHILD_ACQUISITION_AUTHORIZED"
        or not auth["selected_row_binding_ids"]
        or auth["selected_new_action_row_count"]
        != len(auth["selected_row_binding_ids"])
        or auth["observer_calls"] != 0
        or auth["kernel_calls"] != 0
        or auth["world_model_rows_written"] != 0
        or auth["frozen_before_target_access"] is not True
        or auth["only_failed_frontier_successors_selected"] is not True
        or auth["plan_certificate"] is not False
    ):
        _fail("causal authorization semantics changed")
    return auth


def _replay_authorization_verification(document: Any) -> dict[str, Any]:
    fields = {
        "schema",
        "schema_version",
        "authorization_id",
        "source_model_epoch_id",
        "source_frontier_id",
        "source_v2_child_closure_id",
        "selected_candidate_ids",
        "selected_row_binding_ids",
        "incremental_draw_count",
        "exact_semantic_replay_complete",
        "observer_execution_performed",
        "target_access_performed",
        "plan_certificate",
        "verification_id",
    }
    value = _exact_fields(document, fields, "causal authorization verification")
    payload = dict(value)
    supplied = payload.pop("verification_id")
    if (
        supplied != _raw_id(_AUTHORIZATION_VERIFICATION_DOMAIN, payload)
        or value["exact_semantic_replay_complete"] is not True
        or value["observer_execution_performed"] is not False
        or value["target_access_performed"] is not False
    ):
        _fail("causal authorization verification changed")
    return value


def _record_value(stage: Mapping[str, Any], path: str) -> int:
    rows = stage["work_vector"]["records"]
    matches = [row for row in rows if row.get("path") == path]
    if len(matches) != 1 or matches[0].get("observed") is not True:
        _fail(f"stage lacks one native record for {path}")
    value = matches[0].get("value")
    if type(value) is not int or value < 0:
        _fail(f"stage record {path} is not one nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class CausalRecoveryChainReplayV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    reusable_build_epoch_envelope_id: str
    occurrence_id: str
    root_model_epoch_id: str
    root_proof_id: str
    root_frontier_id: str
    causal_child_authorization_id: str
    first_successor_epoch_id: str
    final_model_epoch_id: str
    final_proof_id: str
    final_frontier_id: str
    authorized_row_count: int
    incremental_ground_draw_count: int
    replanning_epoch_count: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("causal recovery replay is caller-minted")
        for value, label in (
            (self.source_operational_trace_id, "source trace"),
            (self.reusable_build_epoch_envelope_id, "BuildEpoch envelope"),
            (self.occurrence_id, "source occurrence"),
            (self.root_model_epoch_id, "root epoch"),
            (self.root_proof_id, "root proof"),
            (self.root_frontier_id, "root frontier"),
            (self.causal_child_authorization_id, "causal authorization"),
            (self.first_successor_epoch_id, "first successor epoch"),
            (self.final_model_epoch_id, "final epoch"),
            (self.final_proof_id, "final proof"),
            (self.final_frontier_id, "final frontier"),
        ):
            _cid(value, label)
        if (
            type(self.authorized_row_count) is not int
            or self.authorized_row_count <= 0
            or type(self.incremental_ground_draw_count) is not int
            or self.incremental_ground_draw_count <= 0
            or self.replanning_epoch_count != 3
        ):
            _fail("causal recovery replay counts changed")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_causal_recovery_chain_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "reusable_build_epoch_envelope_id": self.reusable_build_epoch_envelope_id,
            "occurrence_id": self.occurrence_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "root_proof_id": self.root_proof_id,
            "root_frontier_id": self.root_frontier_id,
            "causal_child_authorization_id": self.causal_child_authorization_id,
            "first_successor_epoch_id": self.first_successor_epoch_id,
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_proof_id": self.final_proof_id,
            "final_frontier_id": self.final_frontier_id,
            "authorized_row_count": self.authorized_row_count,
            "incremental_ground_draw_count": self.incremental_ground_draw_count,
            "replanning_epoch_count": self.replanning_epoch_count,
            "root_and_successor_proofs_exactly_recomputed": True,
            "root_failed_frontier_bound_to_authorization": True,
            "authorization_precedes_incremental_ground_draws": True,
            "incremental_ground_distinctions_only_after_failed_prefix": True,
            "immutable_successor_epoch_chain_replayed": True,
            "source_occurrence_recovery_only": True,
            "fresh_query_rebinding_performed": False,
            "fresh_query_local_recovery_authorized": False,
            "nested_observer_artifact_full_portable_replay_claimed": False,
            "final_plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("causal recovery replay changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "causal_recovery_chain_replay_id": self.result_id}


def replay_construction_k7_causal_recovery_chain_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
) -> CausalRecoveryChainReplayV1:
    build_epoch = build_v1.verify_reusable_build_epoch_authority_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        envelope_bytes=build_epoch_envelope_bytes,
    )
    trace = loads_canonical_json(source_trace_bytes)
    if (
        type(trace) is not dict
        or set(trace) != executor_v1.RECOVERY_EXPORT_TRACE_KEYS
        or trace["schema"] != executor_v1.RECOVERY_EXPORT_TRACE_SCHEMA
    ):
        _fail("causal recovery source trace contract changed")
    chain = _exact_fields(
        trace["causal_recovery_chain"], _CHAIN_FIELDS, "causal recovery chain"
    )
    chain_payload = dict(chain)
    chain_id = chain_payload.pop("causal_recovery_chain_id")
    if (
        chain_id != content_id(SOURCE_CHAIN_DOMAIN, chain_payload)
        or trace["causal_recovery_chain_id"] != chain_id
        or chain["source_occurrence_recovery_only"] is not True
        or chain["fresh_query_rebinding_performed"] is not False
        or chain["local_ground_recovery_authority_for_fresh_query"] is not False
        or chain["final_plan_certificate_issued"] is not False
        or chain["official_execution_allowed"] is not False
    ):
        _fail("causal recovery chain content or claim boundary changed")

    root_epoch_id, root_proof = _replay_epoch(chain["root_model_epoch"])
    final_epoch_id, final_proof = _replay_epoch(chain["final_model_epoch"])
    if (
        canonical_json_bytes(root_proof.to_document())
        != canonical_json_bytes(chain["root_numerical_proof"])
        or canonical_json_bytes(final_proof.to_document())
        != canonical_json_bytes(chain["final_numerical_proof"])
        or root_proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        or final_proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        or root_proof.failed_frontier is None
        or final_proof.failed_frontier is None
    ):
        _fail("causal recovery root/final proof replay changed")
    auth = _replay_authorization(chain["causal_child_authorization"])
    auth_verification = _replay_authorization_verification(
        chain["causal_child_authorization_verification"]
    )
    if (
        auth["source_model_epoch_id"] != root_epoch_id
        or auth["source_numerical_model_id"] != root_proof.model.model_id
        or auth["source_proof_id"] != root_proof.proof_id
        or auth["source_frontier_id"] != root_proof.failed_frontier.frontier_id
        or auth_verification["authorization_id"] != auth["authorization_id"]
        or auth_verification["source_model_epoch_id"] != root_epoch_id
        or auth_verification["source_frontier_id"]
        != root_proof.failed_frontier.frontier_id
        or auth_verification["selected_row_binding_ids"]
        != auth["selected_row_binding_ids"]
    ):
        _fail("failed root frontier was not bound to causal authorization")

    child = chain["causal_child_execution_bundle"]
    promotion = chain["causal_promotion_bundle"]
    if type(child) is not dict or type(promotion) is not dict:
        _fail("causal recovery execution or promotion bundle is absent")
    ledger = child.get("execution_ledger")
    child_epoch = child.get("resulting_epoch")
    if type(ledger) is not dict or type(child_epoch) is not dict:
        _fail("causal child ledger or successor epoch is absent")
    executed_rows = ledger.get("executed_rows")
    if type(executed_rows) is not list or not executed_rows:
        _fail("causal child execution contains no rows")
    for row in executed_rows:
        if type(row) is not dict:
            _fail("causal executed row is malformed")
        row_payload = dict(row)
        row_id = row_payload.pop("executed_row_id", None)
        if row_id != _raw_id(_EXECUTED_ROW_DOMAIN, row_payload):
            _fail("causal executed row ID changed")
    ledger_payload = dict(ledger)
    ledger_payload.pop("executed_rows", None)
    ledger_id = ledger_payload.pop("ledger_id", None)
    if (
        ledger_id != _raw_id(_EXECUTION_LEDGER_DOMAIN, ledger_payload)
        or ledger.get("authorization_id") != auth["authorization_id"]
        or ledger.get("source_model_epoch_id") != root_epoch_id
        or ledger.get("executed_row_binding_ids")
        != auth["selected_row_binding_ids"]
        or ledger.get("executed_row_count") != len(executed_rows)
        or ledger.get("unauthorized_row_execution_present") is not False
    ):
        _fail("authorized rows and causal execution ledger crossed")
    first_successor_id, first_successor_proof = _replay_epoch(child_epoch)
    child_payload = dict(child)
    for nested in (
        "authorization",
        "authorization_verification",
        "execution_ledger",
        "execution_verification",
        "resulting_epoch",
        "replanning_barrier",
        "replanning_barrier_verification",
    ):
        child_payload.pop(nested, None)
    child_bundle_id = child_payload.pop("bundle_id", None)
    if (
        child_bundle_id != _raw_id(_EXECUTION_BUNDLE_DOMAIN, child_payload)
        or child.get("authorization_id") != auth["authorization_id"]
        or child.get("execution_ledger_id") != ledger_id
        or child.get("resulting_model_epoch_id") != first_successor_id
        or child.get("resulting_proof_id") != first_successor_proof.proof_id
        or canonical_json_bytes(child.get("authorization"))
        != canonical_json_bytes(auth)
    ):
        _fail("causal child execution bundle identity crossed")

    promotion_epochs = promotion.get("resulting_epochs")
    if type(promotion_epochs) is not list or len(promotion_epochs) != 2:
        _fail("causal promotion epoch count changed")
    replayed_promotion_epochs = [_replay_epoch(row) for row in promotion_epochs]
    lineage = [chain["root_model_epoch"], child_epoch, *promotion_epochs]
    for index in range(1, len(lineage)):
        if lineage[index]["parent_epoch_id"] != lineage[index - 1]["model_epoch_id"]:
            _fail("causal recovery successor epoch lineage crossed")
    promotion_payload = dict(promotion)
    for nested in (
        "decisions",
        "decision_verifications",
        "resulting_epochs",
        "replanning_barriers",
        "replanning_barrier_verifications",
    ):
        promotion_payload.pop(nested, None)
    promotion_bundle_id = promotion_payload.pop("bundle_id", None)
    if (
        promotion_bundle_id != _raw_id(_PROMOTION_BUNDLE_DOMAIN, promotion_payload)
        or promotion.get("child_execution_bundle_id") != child_bundle_id
        or promotion.get("outcome") != "PROMOTION_BUDGET_EXHAUSTED"
        or promotion.get("promotion_rounds_executed") != 2
        or promotion.get("final_model_epoch_id") != final_epoch_id
        or promotion.get("final_proof_id") != final_proof.proof_id
        or replayed_promotion_epochs[-1][0] != final_epoch_id
        or canonical_json_bytes(promotion_epochs[-1])
        != canonical_json_bytes(chain["final_model_epoch"])
    ):
        _fail("causal promotion bundle or final epoch crossed")

    terminal_v1.verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1(
        trace["budget_replay_attestation"]
    )
    budget = trace["budget_replay_attestation"]
    if (
        budget["final_model_epoch_id"] != final_epoch_id
        or budget["final_proof_id"] != final_proof.proof_id
        or budget["final_frontier_id"] != final_proof.failed_frontier.frontier_id
        or budget["promotion_bundle_id"] != promotion_bundle_id
    ):
        _fail("causal recovery final proof crossed its budget closure")

    stages = trace["recorded_stages"]
    incremental_path = "acquisition.incremental_engine_ground_draws"
    pre_failure_draws = sum(_record_value(stage, incremental_path) for stage in stages[:4])
    post_failure_draws = sum(_record_value(stage, incremental_path) for stage in stages[4:])
    if pre_failure_draws != 0 or post_failure_draws <= 0:
        _fail("incremental ground draws did not follow the failed prefix")

    science = trace["science_summary"]
    if (
        chain["occurrence_id"] != build_epoch.source_occurrence_id
        or chain["occurrence_id"] != science["occurrence_id"]
        or chain["root_model_epoch_id"] != root_epoch_id
        or chain["root_proof_id"] != root_proof.proof_id
        or chain["root_frontier_id"] != root_proof.failed_frontier.frontier_id
        or chain["causal_child_authorization_id"] != auth["authorization_id"]
        or chain["causal_child_execution_bundle_id"] != child_bundle_id
        or chain["causal_promotion_bundle_id"] != promotion_bundle_id
        or chain["final_model_epoch_id"] != final_epoch_id
        or chain["final_proof_id"] != final_proof.proof_id
        or chain["final_frontier_id"] != final_proof.failed_frontier.frontier_id
        or science["causal_child_authorization_id"] != auth["authorization_id"]
        or science["causal_child_execution_bundle_id"] != child_bundle_id
        or science["causal_promotion_bundle_id"] != promotion_bundle_id
    ):
        _fail("causal recovery top-level identity chain crossed")

    return CausalRecoveryChainReplayV1(
        _RESULT_ISSUER,
        build_epoch.source_operational_trace_id,
        build_epoch.envelope_id,
        build_epoch.source_occurrence_id,
        root_epoch_id,
        root_proof.proof_id,
        root_proof.failed_frontier.frontier_id,
        auth["authorization_id"],
        first_successor_id,
        final_epoch_id,
        final_proof.proof_id,
        final_proof.failed_frontier.frontier_id,
        len(auth["selected_row_binding_ids"]),
        post_failure_draws,
        3,
    )


def verify_construction_k7_causal_recovery_chain_bytes_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    replay_bytes: bytes,
) -> CausalRecoveryChainReplayV1:
    expected = replay_construction_k7_causal_recovery_chain_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
    )
    if (
        type(replay_bytes) is not bytes
        or canonical_json_bytes(loads_canonical_json(replay_bytes)) != replay_bytes
        or canonical_json_bytes(expected.to_document()) != replay_bytes
    ):
        _fail("causal recovery replay bytes differ from exact reconstruction")
    return expected


__all__ = [
    "CausalRecoveryChainReplayV1",
    "ConstructionK7CausalRecoveryChainV1Error",
    "LOCAL_DOMAINS",
    "replay_construction_k7_causal_recovery_chain_v1",
    "verify_construction_k7_causal_recovery_chain_bytes_v1",
]
