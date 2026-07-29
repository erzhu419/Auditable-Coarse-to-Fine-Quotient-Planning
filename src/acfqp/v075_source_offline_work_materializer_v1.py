"""Materialize replayed V0-072 source work without inventing economics.

The compact V0-072 reconstruction recipe retains only the campaign-counter
content identity.  It does not contain the counter values and therefore
cannot by itself produce an operational WorkVector.  This module accepts
exactly one already-completed ``SourceReconstructionReplayV1`` and preserves
the exact ``CampaignCounterSummaryV1`` carried by that replay.

The resulting artifact deliberately makes narrower claims:

* the historical sample-draw work is nonzero and replay-bound;
* every native field of ``CampaignCounterSummaryV1`` is serialized;
* the upstream counter's own completeness claim remains false; and
* workload economics, a comparison WorkVector, and scalar cost remain
  unavailable.

No source reconstruction, observer call, target input, or caller-supplied
counter value is accepted by the materializer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1
from acfqp import v075_frozen_source_proposal_archive_v1 as source_boundary_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_source_offline_work_materializer_v1"
MAX_CANONICAL_MATERIALIZATION_BYTES = 64 * 1024
PRODUCTION_INTEGRATION_REPLAY_STATUS = "NOT_RUN"
MATERIALIZATION_STATUS = (
    "CAMPAIGN_COUNTERS_REPLAY_MATERIALIZED_ECONOMICS_UNAVAILABLE"
)

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
    "counter_document_digest": (
        "acfqp:v075-source-offline-counter-document-digest:v1"
    ),
    "materialization": (
        "acfqp:v075-source-offline-work-materialization:v1"
    ),
    "verification": (
        "acfqp:v075-source-offline-work-materialization-verification:v1"
    ),
    "production_status": (
        "acfqp:v075-source-offline-work-production-integration-status:v1"
    ),
}


class V075SourceOfflineWorkMaterializationViolation(ValueError):
    """An offline-work replay boundary or serialized artifact is invalid."""


def _fail(message: str) -> None:
    raise V075SourceOfflineWorkMaterializationViolation(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            "offline-work content identity cannot be derived"
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _exact_mapping(
    value: Any,
    *,
    keys: set[str],
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} has an invalid field set")
    return value


def _strict_load(raw: Any) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_MATERIALIZATION_BYTES
    ):
        _fail("offline-work bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            "offline-work bytes are not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("offline-work bytes are not one canonical object")
    return document


def _counter_type_is_frozen() -> None:
    upstream = tuple(
        item.name for item in fields(campaign_v1.CampaignCounterSummaryV1)
    )
    if upstream != CAMPAIGN_COUNTER_FIELD_ORDER:
        _fail("upstream campaign counter schema changed")


def _counter_document(
    value: campaign_v1.CampaignCounterSummaryV1,
) -> dict[str, Any]:
    _counter_type_is_frozen()
    if type(value) is not campaign_v1.CampaignCounterSummaryV1:
        _fail("source replay does not carry the exact campaign counter type")
    document = value.to_document()
    expected_keys = {
        "schema",
        "schema_version",
        *CAMPAIGN_COUNTER_FIELD_ORDER,
        "sample_advantage_metric",
        "counter_completeness_claimed",
        "counters_id",
    }
    if (
        type(document) is not dict
        or set(document) != expected_keys
        or document["schema"]
        != "acfqp.observation_support_campaign_counters.v1"
        or document["schema_version"] != campaign_v1.SCHEMA_VERSION
        or document["sample_advantage_metric"]
        != "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
        or document["counter_completeness_claimed"] is not False
        or document["counters_id"] != value.counters_id
        or any(
            type(document[name]) is not int or document[name] < 0
            for name in CAMPAIGN_COUNTER_FIELD_ORDER
        )
    ):
        _fail("source campaign counter document changed or overstates coverage")
    _cid(document["counters_id"], "source campaign counters")
    if (
        value.physical_unique_observer_draws <= 0
        or value.physical_unique_random_word_calls <= 0
        or value.physical_unique_random_word_calls
        != (
            value.physical_unique_observer_draws
            + value.physical_unique_rejections
        )
    ):
        _fail("source sample-draw offline work must be nonzero and reconciled")
    return document


def _counter_from_document(
    document: Any,
) -> campaign_v1.CampaignCounterSummaryV1:
    _counter_type_is_frozen()
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            *CAMPAIGN_COUNTER_FIELD_ORDER,
            "sample_advantage_metric",
            "counter_completeness_claimed",
            "counters_id",
        },
        field_name="source campaign counter document",
    )
    if (
        item["schema"] != "acfqp.observation_support_campaign_counters.v1"
        or item["schema_version"] != campaign_v1.SCHEMA_VERSION
        or item["sample_advantage_metric"]
        != "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
        or item["counter_completeness_claimed"] is not False
    ):
        _fail("source campaign counter contract changed")
    try:
        result = campaign_v1.CampaignCounterSummaryV1(
            **{
                name: item[name]
                for name in CAMPAIGN_COUNTER_FIELD_ORDER
            }
        )
    except (
        TypeError,
        campaign_v1.ObservationSupportCampaignInvariantViolation,
    ) as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            "source campaign counters do not reconcile"
        ) from error
    if (
        _counter_document(result) != item
        or result.counters_id != _cid(
            item["counters_id"],
            "source campaign counters",
        )
    ):
        _fail("source campaign counter identity differs from its full values")
    return result


def _counter_document_digest(
    counter: campaign_v1.CampaignCounterSummaryV1,
) -> str:
    return _content_id("counter_document_digest", _counter_document(counter))


def _replay_identity_tuple(
    replay: recipe_v1.SourceReconstructionReplayV1,
) -> tuple[str, ...]:
    """Validate and return the complete source identity chain."""

    if type(replay) is not recipe_v1.SourceReconstructionReplayV1:
        _fail("materializer requires exact SourceReconstructionReplayV1")
    source_campaign = replay.source_campaign
    verification = replay.source_verification
    archive = replay.archive
    production = replay.production_verification
    independent = replay.independent_attestation
    component = replay.component
    if (
        type(source_campaign) is not campaign_v1.ObservationSupportCampaignV1
        or type(verification)
        is not campaign_v1.ObservationSupportCampaignVerificationV1
        or type(source_campaign.counters)
        is not campaign_v1.CampaignCounterSummaryV1
    ):
        _fail("source replay campaign/counter types are not exact")
    counter = source_campaign.counters
    _counter_document(counter)
    try:
        identities = (
            _cid(replay.recipe_id, "source reconstruction recipe"),
            _cid(source_campaign.campaign_id, "source campaign"),
            _cid(verification.verification_id, "source campaign verification"),
            _cid(archive.archive_id, "source archive"),
            _cid(
                production.verification_id,
                "production archive verification",
            ),
            _cid(
                independent.verification_id,
                "independent archive attestation",
            ),
            _cid(component.component_id, "source archive component"),
            _cid(counter.counters_id, "source campaign counters"),
        )
    except AttributeError as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            "source replay identity graph is incomplete"
        ) from error
    if len(set(identities)) != len(identities):
        _fail("source replay reuses one identity across incompatible roles")

    campaign_id = identities[1]
    campaign_verification_id = identities[2]
    archive_id = identities[3]
    production_id = identities[4]
    independent_id = identities[5]
    try:
        valid = (
            verification.campaign_id == campaign_id
            and verification.replayed_campaign_id == campaign_id
            and verification.same_implementation_full_replay is True
            and verification.independent_implementation_claimed is False
            and verification.valid is True
            and archive.source_campaign_id == campaign_id
            and archive.source_campaign_verification_id
            == campaign_verification_id
            and archive.source_frozen is True
            and archive.proposal_only is True
            and archive.may_certify is False
            and production.archive_id == archive_id
            and production.replayed_archive_id == archive_id
            and production.source_campaign_id == campaign_id
            and production.source_campaign_verification_id
            == campaign_verification_id
            and production.valid is True
            and independent.archive_id == archive_id
            and independent.independently_recomputed_archive_id == archive_id
            and independent.source_campaign_id == campaign_id
            and independent.source_campaign_verification_id
            == campaign_verification_id
            and independent.valid is True
            and component.archive.archive_id == archive_id
            and component.production_verification.verification_id
            == production_id
            and component.independent_attestation.verification_id
            == independent_id
            and source_campaign.physical_unique_observer_draws
            == counter.physical_unique_observer_draws
            and source_campaign.aggregate_direct_unique_observer_draws
            == counter.logical_direct_rebuild_observer_draws
            and source_campaign.aggregate_quotient_unique_observer_draws
            == counter.logical_quotient_rebuild_observer_draws
            and source_campaign.official_execution_allowed is False
            and source_campaign.official_scalar_cost is None
            and source_campaign.official_N_break_even is None
            and source_campaign.COUNTER_COMPLETENESS_GATE_NOT_RUN is True
        )
    except AttributeError as error:
        raise V075SourceOfflineWorkMaterializationViolation(
            "source replay relationship graph is incomplete"
        ) from error
    if not valid:
        _fail("source replay identity/work relationships do not close")
    return identities


@dataclass(frozen=True, slots=True)
class V075SourceOfflineWorkMaterializationV1:
    source_recipe_id: str
    source_campaign_id: str
    source_campaign_verification_id: str
    source_archive_id: str
    production_archive_verification_id: str
    independent_archive_attestation_id: str
    source_archive_component_id: str
    campaign_counters: campaign_v1.CampaignCounterSummaryV1
    _materialization_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        identity_values = (
            _cid(self.source_recipe_id, "materialized source recipe"),
            _cid(self.source_campaign_id, "materialized source campaign"),
            _cid(
                self.source_campaign_verification_id,
                "materialized source campaign verification",
            ),
            _cid(self.source_archive_id, "materialized source archive"),
            _cid(
                self.production_archive_verification_id,
                "materialized production archive verification",
            ),
            _cid(
                self.independent_archive_attestation_id,
                "materialized independent archive attestation",
            ),
            _cid(
                self.source_archive_component_id,
                "materialized source archive component",
            ),
        )
        if len(set(identity_values)) != len(identity_values):
            _fail("materialization aliases incompatible source identity roles")
        _counter_document(self.campaign_counters)
        if self.campaign_counters.counters_id in set(identity_values):
            _fail("campaign counter identity aliases another source role")
        object.__setattr__(
            self,
            "_materialization_id",
            _content_id("materialization", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        counter = self.campaign_counters
        return {
            "schema": "acfqp.v075_source_offline_work_materialization.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_archive_id": self.source_archive_id,
            "production_archive_verification_id": (
                self.production_archive_verification_id
            ),
            "independent_archive_attestation_id": (
                self.independent_archive_attestation_id
            ),
            "source_archive_component_id": self.source_archive_component_id,
            "campaign_counters_id": counter.counters_id,
            "campaign_counter_document_digest": (
                _counter_document_digest(counter)
            ),
            "campaign_counter_field_order": list(
                CAMPAIGN_COUNTER_FIELD_ORDER
            ),
            "offline_sample_draw_count": (
                counter.physical_unique_observer_draws
            ),
            "offline_random_word_call_count": (
                counter.physical_unique_random_word_calls
            ),
            "offline_rejection_count": counter.physical_unique_rejections,
            "materialization_status": MATERIALIZATION_STATUS,
            "source_reconstruction_replay_consumed": True,
            "source_reconstruction_replay_executed_by_materializer": False,
            "caller_counter_input_accepted": False,
            "zero_substitution_allowed": False,
            "sample_draw_offline_work_nonzero": True,
            "sample_draw_offline_work_replayable": True,
            "counter_completeness_claimed": False,
            "comparison_work_vector_materialized": False,
            "economics_available": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
            "target_execution_allowed": False,
        }

    @property
    def materialization_id(self) -> str:
        return self._materialization_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_counters": _counter_document(self.campaign_counters),
            "materialization_id": self.materialization_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def materialize_v075_source_offline_work_v1(
    replay: recipe_v1.SourceReconstructionReplayV1,
) -> V075SourceOfflineWorkMaterializationV1:
    """Materialize counters from an exact replay; accepts no other inputs."""

    identities = _replay_identity_tuple(replay)
    result = V075SourceOfflineWorkMaterializationV1(
        *identities[:7],
        replay.source_campaign.counters,
    )
    if len(result.canonical_bytes) > MAX_CANONICAL_MATERIALIZATION_BYTES:
        _fail("source offline-work materialization exceeds its byte cap")
    return result


def _materialization_from_document(
    document: Any,
) -> V075SourceOfflineWorkMaterializationV1:
    item = _exact_mapping(
        document,
        keys={
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
        },
        field_name="source offline-work materialization",
    )
    if (
        item["schema"]
        != "acfqp.v075_source_offline_work_materialization.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["campaign_counter_field_order"]
        != list(CAMPAIGN_COUNTER_FIELD_ORDER)
        or item["materialization_status"] != MATERIALIZATION_STATUS
        or item["source_reconstruction_replay_consumed"] is not True
        or item["source_reconstruction_replay_executed_by_materializer"]
        is not False
        or item["caller_counter_input_accepted"] is not False
        or item["zero_substitution_allowed"] is not False
        or item["sample_draw_offline_work_nonzero"] is not True
        or item["sample_draw_offline_work_replayable"] is not True
        or item["counter_completeness_claimed"] is not False
        or item["comparison_work_vector_materialized"] is not False
        or item["economics_available"] is not False
        or item["official_scalar_cost"] is not None
        or item["official_N_break_even"] is not None
        or item["workload_economics_gate_status"] != "NOT_RUN"
        or item["source_only"] is not True
        or item["proposal_only"] is not True
        or item["may_certify"] is not False
        or item["target_execution_allowed"] is not False
    ):
        _fail("source offline-work materialization contract changed")
    counter = _counter_from_document(item["campaign_counters"])
    result = V075SourceOfflineWorkMaterializationV1(
        item["source_recipe_id"],
        item["source_campaign_id"],
        item["source_campaign_verification_id"],
        item["source_archive_id"],
        item["production_archive_verification_id"],
        item["independent_archive_attestation_id"],
        item["source_archive_component_id"],
        counter,
    )
    if (
        item["campaign_counters_id"] != counter.counters_id
        or item["campaign_counter_document_digest"]
        != _counter_document_digest(counter)
        or item["offline_sample_draw_count"]
        != counter.physical_unique_observer_draws
        or item["offline_random_word_call_count"]
        != counter.physical_unique_random_word_calls
        or item["offline_rejection_count"]
        != counter.physical_unique_rejections
        or result.materialization_id
        != _cid(item["materialization_id"], "source work materialization")
    ):
        _fail("source offline-work materialization derivation changed")
    return result


def load_v075_source_offline_work_materialization_v1(
    raw: bytes,
    *,
    expected_materialization_id: str,
    expected_source_recipe_id: str,
    expected_source_campaign_id: str,
    expected_campaign_counters_id: str,
) -> V075SourceOfflineWorkMaterializationV1:
    """Strictly load an externally bound canonical materialization."""

    result = _materialization_from_document(_strict_load(raw))
    claimed = (
        result.materialization_id,
        result.source_recipe_id,
        result.source_campaign_id,
        result.campaign_counters.counters_id,
    )
    expected = (
        _cid(expected_materialization_id, "expected work materialization"),
        _cid(expected_source_recipe_id, "expected source recipe"),
        _cid(expected_source_campaign_id, "expected source campaign"),
        _cid(expected_campaign_counters_id, "expected campaign counters"),
    )
    if claimed != expected or result.canonical_bytes != raw:
        _fail("source offline-work external identity binding changed")
    return result


@dataclass(frozen=True, slots=True)
class V075SourceOfflineWorkMaterializationVerificationV1:
    source_recipe_id: str
    source_campaign_id: str
    campaign_counters_id: str
    materialization_id: str
    recomputed_materialization_id: str
    materialization_bytes_sha256: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        identities = tuple(
            _cid(value, name)
            for value, name in (
                (self.source_recipe_id, "verified source recipe"),
                (self.source_campaign_id, "verified source campaign"),
                (self.campaign_counters_id, "verified campaign counters"),
                (self.materialization_id, "verified work materialization"),
                (
                    self.recomputed_materialization_id,
                    "recomputed work materialization",
                ),
                (
                    self.materialization_bytes_sha256,
                    "work materialization byte digest",
                ),
            )
        )
        if (
            self.materialization_id
            != self.recomputed_materialization_id
            or len(set(identities[:4])) != 4
        ):
            _fail("source offline-work verification is stale or role-confused")
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_source_offline_work_materialization_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "source_campaign_id": self.source_campaign_id,
            "campaign_counters_id": self.campaign_counters_id,
            "materialization_id": self.materialization_id,
            "recomputed_materialization_id": (
                self.recomputed_materialization_id
            ),
            "materialization_bytes_sha256": (
                self.materialization_bytes_sha256
            ),
            "exact_replay_object_compared": True,
            "source_reconstruction_replay_executed_by_verifier": False,
            "caller_counter_input_accepted": False,
            "counter_completeness_claimed": False,
            "economics_available": False,
            "target_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_source_offline_work_independently_v1(
    *,
    replay: recipe_v1.SourceReconstructionReplayV1,
    claimed: V075SourceOfflineWorkMaterializationV1,
) -> V075SourceOfflineWorkMaterializationVerificationV1:
    """Re-materialize from the exact replay and compare complete bytes."""

    if type(claimed) is not V075SourceOfflineWorkMaterializationV1:
        _fail("independent work verifier requires the exact artifact type")
    recomputed = materialize_v075_source_offline_work_v1(replay)
    if (
        recomputed.materialization_id != claimed.materialization_id
        or recomputed.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("claimed offline work differs from exact replay materialization")
    return V075SourceOfflineWorkMaterializationVerificationV1(
        claimed.source_recipe_id,
        claimed.source_campaign_id,
        claimed.campaign_counters.counters_id,
        claimed.materialization_id,
        recomputed.materialization_id,
        hashlib.sha256(claimed.canonical_bytes).hexdigest(),
    )


def verify_v075_source_offline_work_bytes_independently_v1(
    *,
    replay: recipe_v1.SourceReconstructionReplayV1,
    raw: bytes,
) -> V075SourceOfflineWorkMaterializationVerificationV1:
    """Recompute external expectations before loading untrusted bytes."""

    recomputed = materialize_v075_source_offline_work_v1(replay)
    claimed = load_v075_source_offline_work_materialization_v1(
        raw,
        expected_materialization_id=recomputed.materialization_id,
        expected_source_recipe_id=recomputed.source_recipe_id,
        expected_source_campaign_id=recomputed.source_campaign_id,
        expected_campaign_counters_id=(
            recomputed.campaign_counters.counters_id
        ),
    )
    return verify_v075_source_offline_work_independently_v1(
        replay=replay,
        claimed=claimed,
    )


@dataclass(frozen=True, slots=True)
class V075SourceOfflineWorkProductionIntegrationStatusV1:
    expected_source_recipe_id: str
    expected_source_campaign_id: str
    expected_source_campaign_verification_id: str
    expected_source_archive_id: str
    expected_source_archive_component_id: str
    expected_campaign_counters_id: str
    _status_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = tuple(
            _cid(value, name)
            for value, name in (
                (self.expected_source_recipe_id, "expected source recipe"),
                (self.expected_source_campaign_id, "expected source campaign"),
                (
                    self.expected_source_campaign_verification_id,
                    "expected source campaign verification",
                ),
                (self.expected_source_archive_id, "expected source archive"),
                (
                    self.expected_source_archive_component_id,
                    "expected source archive component",
                ),
                (
                    self.expected_campaign_counters_id,
                    "expected source campaign counters",
                ),
            )
        )
        if (
            len(set(values)) != len(values)
            or values
            != (
                source_boundary_v1.EXPECTED_SOURCE_RECIPE_ID,
                source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_ID,
                source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID,
                source_boundary_v1.EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID,
                source_boundary_v1.EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID,
                source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID,
            )
        ):
            _fail("production integration status identity scope changed")
        object.__setattr__(
            self,
            "_status_id",
            _content_id("production_status", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_source_offline_work_production_integration_status.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "expected_source_recipe_id": self.expected_source_recipe_id,
            "expected_source_campaign_id": self.expected_source_campaign_id,
            "expected_source_campaign_verification_id": (
                self.expected_source_campaign_verification_id
            ),
            "expected_source_archive_id": self.expected_source_archive_id,
            "expected_source_archive_component_id": (
                self.expected_source_archive_component_id
            ),
            "expected_campaign_counters_id": (
                self.expected_campaign_counters_id
            ),
            "integration_replay_status": PRODUCTION_INTEGRATION_REPLAY_STATUS,
            "materialization_id": None,
            "counter_values_serialized": False,
            "source_reconstruction_replay_calls": 0,
            "counter_completeness_claimed": False,
            "economics_available": False,
            "official_execution_allowed": False,
            "target_execution_allowed": False,
        }

    @property
    def status_id(self) -> str:
        return self._status_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "status_id": self.status_id}


def freeze_v075_source_offline_work_production_integration_status_v1(
) -> V075SourceOfflineWorkProductionIntegrationStatusV1:
    """Record that the expensive production source replay has not run."""

    return V075SourceOfflineWorkProductionIntegrationStatusV1(
        source_boundary_v1.EXPECTED_SOURCE_RECIPE_ID,
        source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_ID,
        source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID,
        source_boundary_v1.EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID,
        source_boundary_v1.EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID,
        source_boundary_v1.EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID,
    )


__all__ = [
    "CAMPAIGN_COUNTER_FIELD_ORDER",
    "DOMAIN_TAGS",
    "MATERIALIZATION_STATUS",
    "MAX_CANONICAL_MATERIALIZATION_BYTES",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_REPLAY_STATUS",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075SourceOfflineWorkMaterializationV1",
    "V075SourceOfflineWorkMaterializationVerificationV1",
    "V075SourceOfflineWorkMaterializationViolation",
    "V075SourceOfflineWorkProductionIntegrationStatusV1",
    "freeze_v075_source_offline_work_production_integration_status_v1",
    "load_v075_source_offline_work_materialization_v1",
    "materialize_v075_source_offline_work_v1",
    "verify_v075_source_offline_work_bytes_independently_v1",
    "verify_v075_source_offline_work_independently_v1",
]
