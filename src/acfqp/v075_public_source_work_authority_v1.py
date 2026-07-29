"""Law-free verifier for the public V0-075 source-work artifacts.

The expensive source replay runs in a historical, source-only process.  The
production campaign must not import that historical implementation graph.
This authority therefore consumes only the three canonical public artifacts
written by the replay controller:

* the complete source-work materialization;
* its exact-replay verification; and
* the controller completion status.

Every content identity and cross-artifact relationship needed by the
production campaign is recomputed from bytes.  No V0-072 module, source
observer, target observer, private law, or caller-supplied counter total is
loaded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_public_source_work_authority_v1"
MATERIALIZER_PROFILE_KEY = "v075_source_offline_work_materializer_v1"
CONTROLLER_PROFILE_KEY = "v075_source_replay_materialization_controller_v1"
MAX_MATERIALIZATION_BYTES = 64 * 1024
MAX_VERIFICATION_BYTES = 16 * 1024
MAX_STATUS_BYTES = 32 * 1024

CAMPAIGN_COUNTER_FIELD_ORDER = (
    "physical_unique_observer_draws",
    "physical_unique_random_word_calls",
    "physical_unique_rejections",
    "logical_direct_rebuild_observer_draws",
    "logical_quotient_rebuild_observer_draws",
    "unique_support_epoch_count",
    "promoted_support_epoch_count",
    "promoted_outcome_count",
    "base_model_build_count",
    "coordinate_candidate_model_build_count",
    "expansion_candidate_model_build_count",
    "promoted_model_build_count",
    "direct_audit_count",
    "base_quotient_audit_count",
    "coordinate_candidate_audit_count",
    "expansion_causal_counterfactual_audit_count",
    "promoted_replan_audit_count",
    "fallback_exact_state_action_rows",
    "standalone_exact_state_action_rows",
    "operational_exact_support_queries",
    "operational_exact_probability_queries",
)

DOMAIN_TAGS = {
    "campaign_counters": (
        "acfqp:observation-support-campaign:campaign_counters:v1"
    ),
    "counter_document_digest": (
        "acfqp:v075-source-offline-counter-document-digest:v1"
    ),
    "materialization": (
        "acfqp:v075-source-offline-work-materialization:v1"
    ),
    "verification": (
        "acfqp:v075-source-offline-work-materialization-verification:v1"
    ),
    "controller_status": (
        "acfqp:v075-source-replay-materialization-status:v1"
    ),
    "public_bundle": (
        "acfqp:v075-verified-public-source-work-bundle:v1"
    ),
}

_MATERIALIZATION_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_recipe_id",
    "source_campaign_id",
    "source_campaign_verification_id",
    "source_archive_id",
    "production_archive_verification_id",
    "independent_archive_attestation_id",
    "source_archive_component_id",
    "campaign_counters_id",
    "campaign_counter_document_digest",
    "campaign_counter_field_order",
    "offline_sample_draw_count",
    "offline_random_word_call_count",
    "offline_rejection_count",
    "materialization_status",
    "source_reconstruction_replay_consumed",
    "source_reconstruction_replay_executed_by_materializer",
    "caller_counter_input_accepted",
    "zero_substitution_allowed",
    "sample_draw_offline_work_nonzero",
    "sample_draw_offline_work_replayable",
    "counter_completeness_claimed",
    "comparison_work_vector_materialized",
    "economics_available",
    "official_scalar_cost",
    "official_N_break_even",
    "workload_economics_gate_status",
    "source_only",
    "proposal_only",
    "may_certify",
    "target_execution_allowed",
    "campaign_counters",
    "materialization_id",
}

_COUNTER_KEYS = {
    "schema",
    "schema_version",
    *CAMPAIGN_COUNTER_FIELD_ORDER,
    "sample_advantage_metric",
    "counter_completeness_claimed",
    "counters_id",
}

_VERIFICATION_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "source_recipe_id",
    "source_campaign_id",
    "campaign_counters_id",
    "materialization_id",
    "recomputed_materialization_id",
    "materialization_bytes_sha256",
    "exact_replay_object_compared",
    "source_reconstruction_replay_executed_by_verifier",
    "caller_counter_input_accepted",
    "counter_completeness_claimed",
    "economics_available",
    "target_execution_allowed",
    "valid",
    "verification_id",
}

_STATUS_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "snapshot_preflight_id",
    "controller_code_manifest_id",
    "source_only_bypass_evidence_id",
    "source_only_readiness_id",
    "same_process_protocol_id",
    "source_graph_verification_id",
    "blocker",
    "source_only_snapshot_eligible",
    "current_code_production_ready",
    "production_replay_status",
    "production_materialization_status",
    "source_replay_id",
    "source_replay_object_persisted",
    "source_replay_object_consumed_same_process",
    "source_work_materialization_id",
    "source_work_verification_id",
    "source_child_launched",
    "sample_draws_started",
    "materialization_artifact_written",
    "verification_artifact_written",
    "counter_document_accepted",
    "pickle_transport_accepted",
    "caller_supplied_expected_ids_accepted",
    "current_tree_recomputation_used_as_source_replay",
    "generic_recipe_freeze_helper_called",
    "confirmatory_manifest_imported",
    "official_execution_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "target_access",
    "hidden_law_access",
    "status_id",
}


class V075PublicSourceWorkAuthorityViolation(ValueError):
    """Public source-work bytes or their identity graph are invalid."""


def _fail(message: str) -> None:
    raise V075PublicSourceWorkAuthorityViolation(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PublicSourceWorkAuthorityViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075PublicSourceWorkAuthorityViolation(
            "public source-work content identity cannot be derived"
        ) from error


def _load(raw: Any, *, cap: int, field_name: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{field_name} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075PublicSourceWorkAuthorityViolation(
            f"{field_name} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{field_name} is not one canonical object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{field_name} has an invalid field set")


def _verify_counter_document(value: Any) -> dict[str, Any]:
    _exact_keys(value, _COUNTER_KEYS, "source campaign counters")
    item = dict(value)
    if (
        item["schema"]
        != "acfqp.observation_support_campaign_counters.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["sample_advantage_metric"]
        != "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
        or item["counter_completeness_claimed"] is not False
        or any(
            type(item[name]) is not int or item[name] < 0
            for name in CAMPAIGN_COUNTER_FIELD_ORDER
        )
        or item["physical_unique_observer_draws"] <= 0
        or item["physical_unique_random_word_calls"] <= 0
        or item["physical_unique_random_word_calls"]
        != (
            item["physical_unique_observer_draws"]
            + item["physical_unique_rejections"]
        )
        or item["base_model_build_count"] <= 0
        or item["direct_audit_count"] <= 0
        or item["base_quotient_audit_count"] <= 0
        or item["operational_exact_support_queries"] != 0
        or item["operational_exact_probability_queries"] != 0
    ):
        _fail("source campaign counter contract or reconciliation changed")
    claimed = _cid(item["counters_id"], "source campaign counters")
    payload = dict(item)
    payload.pop("counters_id")
    if claimed != _hash(DOMAIN_TAGS["campaign_counters"], payload):
        _fail("source campaign counter identity does not match its values")
    return item


def _verify_materialization(raw: bytes) -> dict[str, Any]:
    item = _load(
        raw,
        cap=MAX_MATERIALIZATION_BYTES,
        field_name="source work materialization",
    )
    _exact_keys(item, _MATERIALIZATION_KEYS, "source work materialization")
    expected_flags = (
        item["schema"]
        == "acfqp.v075_source_offline_work_materialization.v1"
        and item["schema_version"] == SCHEMA_VERSION
        and item["proposed_contract_version"] == PROPOSED_CONTRACT_VERSION
        and item["profile_key"] == MATERIALIZER_PROFILE_KEY
        and item["campaign_counter_field_order"]
        == list(CAMPAIGN_COUNTER_FIELD_ORDER)
        and item["materialization_status"]
        == "CAMPAIGN_COUNTERS_REPLAY_MATERIALIZED_ECONOMICS_UNAVAILABLE"
        and item["source_reconstruction_replay_consumed"] is True
        and item["source_reconstruction_replay_executed_by_materializer"]
        is False
        and item["caller_counter_input_accepted"] is False
        and item["zero_substitution_allowed"] is False
        and item["sample_draw_offline_work_nonzero"] is True
        and item["sample_draw_offline_work_replayable"] is True
        and item["counter_completeness_claimed"] is False
        and item["comparison_work_vector_materialized"] is False
        and item["economics_available"] is False
        and item["official_scalar_cost"] is None
        and item["official_N_break_even"] is None
        and item["workload_economics_gate_status"] == "NOT_RUN"
        and item["source_only"] is True
        and item["proposal_only"] is True
        and item["may_certify"] is False
        and item["target_execution_allowed"] is False
    )
    if not expected_flags:
        _fail("source work materialization contract changed")
    counter = _verify_counter_document(item["campaign_counters"])
    identity_names = (
        "source_recipe_id",
        "source_campaign_id",
        "source_campaign_verification_id",
        "source_archive_id",
        "production_archive_verification_id",
        "independent_archive_attestation_id",
        "source_archive_component_id",
    )
    identities = tuple(_cid(item[name], name) for name in identity_names)
    counter_id = _cid(item["campaign_counters_id"], "campaign counters")
    if len(set((*identities, counter_id))) != len(identities) + 1:
        _fail("source work aliases incompatible artifact roles")
    if (
        counter_id != counter["counters_id"]
        or item["campaign_counter_document_digest"]
        != _hash(DOMAIN_TAGS["counter_document_digest"], counter)
        or item["offline_sample_draw_count"]
        != counter["physical_unique_observer_draws"]
        or item["offline_random_word_call_count"]
        != counter["physical_unique_random_word_calls"]
        or item["offline_rejection_count"]
        != counter["physical_unique_rejections"]
    ):
        _fail("source work materialization counter binding changed")
    claimed = _cid(item["materialization_id"], "source work materialization")
    payload = dict(item)
    payload.pop("campaign_counters")
    payload.pop("materialization_id")
    if claimed != _hash(DOMAIN_TAGS["materialization"], payload):
        _fail("source work materialization identity is invalid")
    return item


def _verify_verification(
    raw: bytes,
    *,
    materialization_raw: bytes,
    materialization: Mapping[str, Any],
) -> dict[str, Any]:
    item = _load(
        raw,
        cap=MAX_VERIFICATION_BYTES,
        field_name="source work verification",
    )
    _exact_keys(item, _VERIFICATION_KEYS, "source work verification")
    if (
        item["schema"]
        != "acfqp.v075_source_offline_work_materialization_verification.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != MATERIALIZER_PROFILE_KEY
        or item["source_recipe_id"] != materialization["source_recipe_id"]
        or item["source_campaign_id"] != materialization["source_campaign_id"]
        or item["campaign_counters_id"]
        != materialization["campaign_counters_id"]
        or item["materialization_id"] != materialization["materialization_id"]
        or item["recomputed_materialization_id"]
        != materialization["materialization_id"]
        or item["materialization_bytes_sha256"]
        != hashlib.sha256(materialization_raw).hexdigest()
        or item["exact_replay_object_compared"] is not True
        or item["source_reconstruction_replay_executed_by_verifier"]
        is not False
        or item["caller_counter_input_accepted"] is not False
        or item["counter_completeness_claimed"] is not False
        or item["economics_available"] is not False
        or item["target_execution_allowed"] is not False
        or item["valid"] is not True
    ):
        _fail("source work verification does not close")
    claimed = _cid(item["verification_id"], "source work verification")
    payload = dict(item)
    payload.pop("verification_id")
    if claimed != _hash(DOMAIN_TAGS["verification"], payload):
        _fail("source work verification identity is invalid")
    return item


def _verify_status(
    raw: bytes,
    *,
    materialization: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    item = _load(
        raw,
        cap=MAX_STATUS_BYTES,
        field_name="source replay controller status",
    )
    _exact_keys(item, _STATUS_KEYS, "source replay controller status")
    for name in (
        "snapshot_preflight_id",
        "controller_code_manifest_id",
        "source_only_bypass_evidence_id",
        "source_only_readiness_id",
        "same_process_protocol_id",
        "source_graph_verification_id",
    ):
        _cid(item[name], name)
    if (
        item["schema"]
        != "acfqp.v075_source_replay_materialization_status.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != CONTROLLER_PROFILE_KEY
        or item["blocker"] is not None
        or item["source_only_snapshot_eligible"] is not True
        or item["current_code_production_ready"] is not True
        or item["production_replay_status"] != "COMPLETED"
        or item["production_materialization_status"] != "COMPLETED"
        or item["source_replay_id"] is not None
        or item["source_replay_object_persisted"] is not False
        or item["source_replay_object_consumed_same_process"] is not True
        or item["source_work_materialization_id"]
        != materialization["materialization_id"]
        or item["source_work_verification_id"]
        != verification["verification_id"]
        or item["source_child_launched"] is not False
        or item["sample_draws_started"] is not True
        or item["materialization_artifact_written"] is not True
        or item["verification_artifact_written"] is not True
        or item["counter_document_accepted"] is not False
        or item["pickle_transport_accepted"] is not False
        or item["caller_supplied_expected_ids_accepted"] is not False
        or item["current_tree_recomputation_used_as_source_replay"] is not False
        or item["generic_recipe_freeze_helper_called"] is not False
        or item["confirmatory_manifest_imported"] is not False
        or item["official_execution_allowed"] is not False
        or item["official_scalar_cost"] is not None
        or item["official_N_break_even"] is not None
        or item["counter_completeness_gate_status"] != "NOT_RUN"
        or item["workload_economics_gate_status"] != "NOT_RUN"
        or item["target_access"] is not False
        or item["hidden_law_access"] is not False
    ):
        _fail("source replay controller did not close the source-only protocol")
    claimed = _cid(item["status_id"], "source replay status")
    payload = dict(item)
    payload.pop("status_id")
    if claimed != _hash(DOMAIN_TAGS["controller_status"], payload):
        _fail("source replay controller status identity is invalid")
    return item


_BUNDLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075VerifiedPublicSourceWorkBundleV1:
    """Issuer-only law-free source-work boundary for production consumers."""

    _issuer: object
    materialization_id: str
    verification_id: str
    controller_status_id: str
    source_recipe_id: str
    source_campaign_id: str
    source_campaign_verification_id: str
    source_archive_id: str
    source_archive_component_id: str
    campaign_counters_id: str
    offline_draw_count: int
    offline_random_word_call_count: int
    offline_rejection_count: int
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _BUNDLE_ISSUER:
            _fail("public source-work bundle was not authority-issued")
        identities = tuple(
            _cid(getattr(self, name), name)
            for name in (
                "materialization_id",
                "verification_id",
                "controller_status_id",
                "source_recipe_id",
                "source_campaign_id",
                "source_campaign_verification_id",
                "source_archive_id",
                "source_archive_component_id",
                "campaign_counters_id",
            )
        )
        if len(set(identities)) != len(identities):
            _fail("public source-work bundle aliases artifact roles")
        if (
            type(self.offline_draw_count) is not int
            or self.offline_draw_count <= 0
            or type(self.offline_random_word_call_count) is not int
            or type(self.offline_rejection_count) is not int
            or self.offline_rejection_count < 0
            or self.offline_random_word_call_count
            != self.offline_draw_count + self.offline_rejection_count
        ):
            _fail("public source-work bundle has invalid native work")
        object.__setattr__(
            self,
            "_bundle_id",
            _hash(DOMAIN_TAGS["public_bundle"], self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_verified_public_source_work_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "materialization_id": self.materialization_id,
            "materialization_verification_id": self.verification_id,
            "source_replay_controller_status_id": self.controller_status_id,
            "source_recipe_id": self.source_recipe_id,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_archive_id": self.source_archive_id,
            "source_archive_component_id": self.source_archive_component_id,
            "campaign_counters_id": self.campaign_counters_id,
            "offline_sample_draw_count": self.offline_draw_count,
            "offline_random_word_call_count": (
                self.offline_random_word_call_count
            ),
            "offline_rejection_count": self.offline_rejection_count,
            "source_replay_completed": True,
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
            "target_access": False,
            "hidden_law_access": False,
            "counter_completeness_claimed": False,
            "economics_available": False,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def verify_v075_public_source_work_artifacts_v1(
    *,
    materialization_raw: bytes,
    verification_raw: bytes,
    controller_status_raw: bytes,
) -> V075VerifiedPublicSourceWorkBundleV1:
    """Verify three public artifacts and mint the production-safe boundary."""

    materialization = _verify_materialization(materialization_raw)
    verification = _verify_verification(
        verification_raw,
        materialization_raw=materialization_raw,
        materialization=materialization,
    )
    status = _verify_status(
        controller_status_raw,
        materialization=materialization,
        verification=verification,
    )
    counter = materialization["campaign_counters"]
    return V075VerifiedPublicSourceWorkBundleV1(
        _BUNDLE_ISSUER,
        materialization["materialization_id"],
        verification["verification_id"],
        status["status_id"],
        materialization["source_recipe_id"],
        materialization["source_campaign_id"],
        materialization["source_campaign_verification_id"],
        materialization["source_archive_id"],
        materialization["source_archive_component_id"],
        materialization["campaign_counters_id"],
        counter["physical_unique_observer_draws"],
        counter["physical_unique_random_word_calls"],
        counter["physical_unique_rejections"],
    )


__all__ = [
    "CAMPAIGN_COUNTER_FIELD_ORDER",
    "CONTROLLER_PROFILE_KEY",
    "DOMAIN_TAGS",
    "MATERIALIZER_PROFILE_KEY",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075PublicSourceWorkAuthorityViolation",
    "V075VerifiedPublicSourceWorkBundleV1",
    "verify_v075_public_source_work_artifacts_v1",
]
