"""Observer-signed execution and replanning barrier for V3 causal children.

This module consumes one exact
``V075LiveBatchedCausalChildAuthorizationV3`` while the V2 controlled observer
is still open at the authorization's root head.  Every selected row is
appended as D64 discovery, an observer-owned complete-support freeze, and
V8192 validation.  The resulting signed prefix is compiled into one child
``V075LiveIncrementalModelEpochV2`` and may be consumed only through the typed
barrier emitted here.

The selected discovery and validation artifacts are byte-identical projections
of the existing V2 controlled semantic schemas.  Their selection and causal
ownership remain bound by the V3 authorization and verification IDs.  This is
still a construction boundary: it does not close the observer, issue a plan
certificate, create K7 CounterRecords, or classify a campaign terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_batched_causal_child_authority_v3 as causal
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.62.0"
PROFILE_KEY = "v075_live_batched_causal_child_execution_v3"
MAX_CANONICAL_INPUT_BYTES = 128 * 1024 * 1024

PRODUCTION_INTEGRATION_READY = False
OBSERVER_CLOSE_PERFORMED = False
TERMINAL_CLASSIFICATION_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
COUNTER_RECORD_ISSUANCE_ALLOWED = False

DOMAIN_TAGS = {
    "executed_row": "acfqp:v075-live-batched-causal-executed-row:v3",
    "ledger": "acfqp:v075-live-batched-causal-execution-ledger:v3",
    "ledger_verification": (
        "acfqp:v075-live-batched-causal-execution-verification:v3"
    ),
    "barrier": "acfqp:v075-live-batched-causal-replanning-barrier:v3",
    "barrier_verification": (
        "acfqp:v075-live-batched-causal-replanning-verification:v3"
    ),
    "bundle": "acfqp:v075-live-batched-causal-execution-bundle:v3",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("live batched causal execution domains must be unique")


class V075LiveBatchedCausalExecutionV3InvariantViolation(ValueError):
    """The authorization, signed append set, child epoch, or barrier changed."""


def _fail(message: str) -> NoReturn:
    raise V075LiveBatchedCausalExecutionV3InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075LiveBatchedCausalExecutionV3InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalExecutionV3InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_CANONICAL_INPUT_BYTES:
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalExecutionV3InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


_ROW_ISSUER = object()
_LEDGER_ISSUER = object()
_LEDGER_VERIFICATION_ISSUER = object()
_BARRIER_ISSUER = object()
_BARRIER_VERIFICATION_ISSUER = object()
_BUNDLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalExecutedRowV3:
    _issuer: object = field(repr=False, compare=False)
    candidate_id: str
    child_binding_id: str
    row_binding_id: str
    discovery_artifact_id: str
    discovery_append_receipt_id: str
    discovery_batch_id: str
    support_freeze_id: str
    validation_artifact_id: str
    validation_append_receipt_id: str
    validation_batch_id: str
    _executed_row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.candidate_id, "executed causal candidate"),
            (self.child_binding_id, "executed causal child binding"),
            (self.row_binding_id, "executed causal child row"),
            (self.discovery_artifact_id, "executed discovery artifact"),
            (
                self.discovery_append_receipt_id,
                "executed discovery receipt",
            ),
            (self.discovery_batch_id, "executed discovery batch"),
            (self.support_freeze_id, "executed support freeze"),
            (self.validation_artifact_id, "executed validation artifact"),
            (
                self.validation_append_receipt_id,
                "executed validation receipt",
            ),
            (self.validation_batch_id, "executed validation batch"),
        ):
            _cid(value, label)
        if self._issuer is not _ROW_ISSUER:
            _fail("executed causal row is caller-minted")
        object.__setattr__(
            self,
            "_executed_row_id",
            _hash("executed_row", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_executed_row.v3",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "child_binding_id": self.child_binding_id,
            "row_binding_id": self.row_binding_id,
            "discovery_semantic_artifact_id": self.discovery_artifact_id,
            "discovery_append_receipt_id": (
                self.discovery_append_receipt_id
            ),
            "discovery_batch_id": self.discovery_batch_id,
            "support_freeze_id": self.support_freeze_id,
            "validation_semantic_artifact_id": self.validation_artifact_id,
            "validation_append_receipt_id": (
                self.validation_append_receipt_id
            ),
            "validation_batch_id": self.validation_batch_id,
            "discovery_draw_count": dynamic.CHILD_DISCOVERY_DRAWS,
            "validation_draw_count": dynamic.CHILD_VALIDATION_DRAWS,
            "executed_exactly_once": True,
            "observer_signed_append_chain": True,
        }

    @property
    def executed_row_id(self) -> str:
        return self._executed_row_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "executed_row_id": self.executed_row_id}


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalExecutionLedgerV3:
    _issuer: object = field(repr=False, compare=False)
    authorization_id: str
    authorization_verification_id: str
    source_v2_child_closure_id: str
    source_model_epoch_id: str
    source_head_id: str
    resulting_head_id: str
    open_prefix_verification_id: str
    executed_rows: tuple[V075LiveBatchedCausalExecutedRowV3, ...]
    _ledger_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authorization_id, "causal execution authorization"),
            (
                self.authorization_verification_id,
                "causal execution authorization verification",
            ),
            (
                self.source_v2_child_closure_id,
                "causal execution source V2 closure",
            ),
            (self.source_model_epoch_id, "causal execution source epoch"),
            (self.source_head_id, "causal execution source head"),
            (self.resulting_head_id, "causal execution resulting head"),
            (
                self.open_prefix_verification_id,
                "causal execution open prefix",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _LEDGER_ISSUER
            or self.source_head_id == self.resulting_head_id
            or type(self.executed_rows) is not tuple
            or not self.executed_rows
            or self.executed_rows
            != tuple(
                sorted(self.executed_rows, key=lambda item: item.row_binding_id)
            )
            or len({item.row_binding_id for item in self.executed_rows})
            != len(self.executed_rows)
        ):
            _fail("live batched causal execution ledger is malformed")
        object.__setattr__(self, "_ledger_id", _hash("ledger", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_execution_ledger.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization_id,
            "authorization_verification_id": (
                self.authorization_verification_id
            ),
            "source_v2_child_closure_id": self.source_v2_child_closure_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_head_id": self.resulting_head_id,
            "open_prefix_verification_id": self.open_prefix_verification_id,
            "executed_row_ids": [
                item.executed_row_id for item in self.executed_rows
            ],
            "executed_row_binding_ids": [
                item.row_binding_id for item in self.executed_rows
            ],
            "executed_row_count": len(self.executed_rows),
            "all_authorized_rows_executed_exactly_once": True,
            "unauthorized_row_execution_present": False,
            "observer_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def ledger_id(self) -> str:
        return self._ledger_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "executed_rows": [item.to_document() for item in self.executed_rows],
            "ledger_id": self.ledger_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalExecutionVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    ledger_id: str
    authorization_id: str
    resulting_head_id: str
    executed_row_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.ledger_id, "causal ledger verification ledger"),
            (
                self.authorization_id,
                "causal ledger verification authorization",
            ),
            (self.resulting_head_id, "causal ledger verification head"),
            *(
                (value, "causal ledger verification row")
                for value in self.executed_row_ids
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _LEDGER_VERIFICATION_ISSUER
            or type(self.executed_row_ids) is not tuple
            or not self.executed_row_ids
            or len(set(self.executed_row_ids)) != len(self.executed_row_ids)
        ):
            _fail("causal execution verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("ledger_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_batched_causal_execution_verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "ledger_id": self.ledger_id,
            "authorization_id": self.authorization_id,
            "resulting_head_id": self.resulting_head_id,
            "executed_row_ids": list(self.executed_row_ids),
            "semantic_replay_complete": True,
            "observer_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_authorization_verification(
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
) -> causal.V075LiveBatchedCausalChildVerificationV3:
    frontier = authorization.source_closure.source_epoch.proof.failed_frontier
    if frontier is None:
        _fail("causal authorization source frontier is absent")
    return causal.V075LiveBatchedCausalChildVerificationV3(
        causal._VERIFICATION_ISSUER,  # noqa: SLF001
        authorization.authorization_id,
        authorization.source_closure.source_epoch.model_epoch_id,
        frontier.frontier_id,
        authorization.source_closure.closure_id,
        authorization.selected_candidate_ids,
        authorization.selected_row_binding_ids,
        authorization.incremental_draw_count,
    )


def _exact_prefix(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    claimed: control.V075OpenControlledBatchPrefixVerificationV2,
    portable_replay: bool,
) -> control.V075OpenControlledBatchPrefixVerificationV2:
    if type(claimed) is not control.V075OpenControlledBatchPrefixVerificationV2:
        _fail("causal execution requires one exact open prefix")
    try:
        exact = (
            control.verify_v075_open_controlled_batch_prefix_v2(
                heads=claimed.heads,
                appends=claimed.appends,
                support_freezes=claimed.support_freezes,
            )
            if portable_replay
            else control.validate_v075_trusted_owned_open_prefix_v2(
                claimed=claimed,
                occurrence_identity=(
                    authorization.source_closure.source_epoch
                    .occurrence_identity
                ),
            )
        )
    except Exception as error:
        raise V075LiveBatchedCausalExecutionV3InvariantViolation(
            "causal execution open prefix exact replay failed"
        ) from error
    if (
        exact.verification_id != claimed.verification_id
        or exact.to_document() != claimed.to_document()
    ):
        _fail("causal execution open prefix changed")
    return exact


def _freeze_ledger(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    portable_replay: bool,
) -> V075LiveBatchedCausalExecutionLedgerV3:
    if (
        type(authorization)
        is not causal.V075LiveBatchedCausalChildAuthorizationV3
        or authorization.outcome
        is not causal.V075LiveBatchedCausalChildOutcomeV3.AUTHORIZED
    ):
        _fail("causal execution requires one exact authorized union")
    exact_verification = _exact_authorization_verification(authorization)
    if (
        type(authorization_verification)
        is not causal.V075LiveBatchedCausalChildVerificationV3
        or authorization_verification.verification_id
        != exact_verification.verification_id
        or authorization_verification.to_document()
        != exact_verification.to_document()
    ):
        _fail("causal execution authorization verification is foreign")
    prefix = _exact_prefix(
        authorization=authorization,
        claimed=open_prefix_verification,
        portable_replay=portable_replay,
    )
    source = authorization.source_closure.source_epoch.open_prefix_verification
    if (
        prefix.occurrence_id
        != authorization.source_closure.source_epoch.occurrence_identity.occurrence_id
        or prefix.zero_head_id != source.zero_head_id
        or prefix.head_ids[: len(source.head_ids)] != source.head_ids
        or prefix.receipt_ids[: len(source.receipt_ids)] != source.receipt_ids
        or prefix.support_freeze_ids[: len(source.support_freeze_ids)]
        != source.support_freeze_ids
    ):
        _fail("causal execution prefix is not an exact source extension")
    new_appends = prefix.appends[len(source.appends) :]
    new_freezes = prefix.support_freezes[len(source.support_freezes) :]
    expected_count = len(authorization.discovery_intents)
    if (
        len(new_appends) != 2 * expected_count
        or len(new_freezes) != expected_count
    ):
        _fail("causal execution prefix is partial or contains extra work")
    appends_by_artifact: dict[str, control.V075ControlledBatchAppendV2] = {}
    for append in new_appends:
        artifact_id = append.intent.semantic_authority.semantic_artifact_id
        if artifact_id in appends_by_artifact:
            _fail("causal execution repeated one semantic artifact")
        appends_by_artifact[artifact_id] = append
    expected_artifacts = {
        item.intent_id for item in authorization.discovery_intents
    } | {
        item.template_id for item in authorization.validation_templates
    }
    if set(appends_by_artifact) != expected_artifacts:
        _fail("causal execution semantic artifact set is incomplete")
    freezes_by_row = {item.row_binding_id: item for item in new_freezes}
    if len(freezes_by_row) != expected_count:
        _fail("causal execution support freeze set is incomplete")
    templates = {
        item.discovery_intent.intent_id: item
        for item in authorization.validation_templates
    }
    role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    executed = []
    for discovery in authorization.discovery_intents:
        template = templates.get(discovery.intent_id)
        if template is None:
            _fail("causal discovery lacks its validation template")
        discovery_append = appends_by_artifact[discovery.intent_id]
        validation_append = appends_by_artifact[template.template_id]
        support = freezes_by_row.get(discovery.row_binding.row_binding_id)
        discovery_intent = discovery_append.intent
        validation_intent = validation_append.intent
        if (
            support is None
            or discovery_intent.semantic_authority.role is not role
            or discovery_intent.semantic_authority.schema is not schema
            or discovery_intent.semantic_authority.semantic_verification_id
            != exact_verification.verification_id
            or discovery_intent.semantic_authority.stage
            is not control.V075ControlledBatchStageV2.CHILD_DISCOVERY
            or discovery_intent.semantic_authority.round_index != 0
            or discovery_intent.semantic_authority.support_freeze_id
            is not None
            or discovery_intent.stream_identity != discovery.stream_identity
            or discovery_intent.accepted_draw_start != 1
            or discovery_intent.accepted_draw_count
            != dynamic.CHILD_DISCOVERY_DRAWS
            or discovery_intent.accepted_draw_cap
            != dynamic.CHILD_DISCOVERY_DRAWS
            or support.discovery_append.receipt.receipt_id
            != discovery_append.receipt.receipt_id
            or validation_intent.semantic_authority.role is not role
            or validation_intent.semantic_authority.schema is not schema
            or validation_intent.semantic_authority.semantic_verification_id
            != exact_verification.verification_id
            or validation_intent.semantic_authority.stage
            is not control.V075ControlledBatchStageV2.CHILD_VALIDATION
            or validation_intent.semantic_authority.round_index != 0
            or validation_intent.semantic_authority.support_freeze_id
            != support.freeze_id
            or validation_intent.stream_identity
            != control.derive_v075_controlled_validation_stream_v2(
                support_freeze=support
            )
            or validation_intent.accepted_draw_start != 1
            or validation_intent.accepted_draw_count
            != dynamic.CHILD_VALIDATION_DRAWS
            or validation_intent.accepted_draw_cap
            != (
                dynamic.CHILD_VALIDATION_DRAWS
                + dynamic.MAXIMUM_PROMOTION_ROUNDS * dynamic.PROMOTION_DRAWS
            )
        ):
            _fail("causal execution row differs from exact D64/V8192 intent")
        executed.append(
            V075LiveBatchedCausalExecutedRowV3(
                _ROW_ISSUER,
                discovery.candidate_id,
                discovery.child_binding_id,
                discovery.row_binding.row_binding_id,
                discovery.intent_id,
                discovery_append.receipt.receipt_id,
                discovery_append.batch.batch_id,
                support.freeze_id,
                template.template_id,
                validation_append.receipt.receipt_id,
                validation_append.batch.batch_id,
            )
        )
    return V075LiveBatchedCausalExecutionLedgerV3(
        _LEDGER_ISSUER,
        authorization.authorization_id,
        exact_verification.verification_id,
        authorization.source_closure.closure_id,
        authorization.source_closure.source_epoch.model_epoch_id,
        authorization.source_closure.source_epoch.head_id,
        prefix.current_head_id,
        prefix.verification_id,
        tuple(sorted(executed, key=lambda item: item.row_binding_id)),
    )


def freeze_v075_live_batched_causal_execution_ledger_v3(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
) -> V075LiveBatchedCausalExecutionLedgerV3:
    return _freeze_ledger(
        authorization=authorization,
        authorization_verification=authorization_verification,
        open_prefix_verification=open_prefix_verification,
        portable_replay=False,
    )


def verify_v075_live_batched_causal_execution_ledger_bytes_v3(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    claimed_bytes: bytes,
) -> tuple[
    V075LiveBatchedCausalExecutionLedgerV3,
    V075LiveBatchedCausalExecutionVerificationV3,
]:
    document = _strict_document(claimed_bytes, "causal execution ledger")
    expected = _freeze_ledger(
        authorization=authorization,
        authorization_verification=authorization_verification,
        open_prefix_verification=open_prefix_verification,
        portable_replay=True,
    )
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("causal execution ledger differs from exact replay")
    verification = V075LiveBatchedCausalExecutionVerificationV3(
        _LEDGER_VERIFICATION_ISSUER,
        expected.ledger_id,
        expected.authorization_id,
        expected.resulting_head_id,
        tuple(item.executed_row_id for item in expected.executed_rows),
    )
    return expected, verification


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalReplanningBarrierV3:
    _issuer: object = field(repr=False, compare=False)
    authorization_id: str
    authorization_verification_id: str
    execution_ledger_id: str
    execution_verification_id: str
    source_model_epoch_id: str
    source_head_id: str
    resulting_model_epoch_id: str
    resulting_head_id: str
    resulting_open_prefix_verification_id: str
    resulting_numerical_model_id: str
    resulting_proof_id: str
    resulting_outcome: planning.V075NumericalOutcomeV2
    authorized_row_binding_ids: tuple[str, ...]
    source_row_binding_ids: tuple[str, ...]
    _barrier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authorization_id, "causal barrier authorization"),
            (
                self.authorization_verification_id,
                "causal barrier authorization verification",
            ),
            (self.execution_ledger_id, "causal barrier ledger"),
            (
                self.execution_verification_id,
                "causal barrier ledger verification",
            ),
            (self.source_model_epoch_id, "causal barrier source epoch"),
            (self.source_head_id, "causal barrier source head"),
            (
                self.resulting_model_epoch_id,
                "causal barrier resulting epoch",
            ),
            (self.resulting_head_id, "causal barrier resulting head"),
            (
                self.resulting_open_prefix_verification_id,
                "causal barrier resulting prefix",
            ),
            (
                self.resulting_numerical_model_id,
                "causal barrier resulting model",
            ),
            (self.resulting_proof_id, "causal barrier resulting proof"),
            *(
                (value, "causal barrier row")
                for value in (
                    *self.authorized_row_binding_ids,
                    *self.source_row_binding_ids,
                )
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _BARRIER_ISSUER
            or self.source_model_epoch_id == self.resulting_model_epoch_id
            or self.source_head_id == self.resulting_head_id
            or type(self.resulting_outcome) is not planning.V075NumericalOutcomeV2
            or type(self.authorized_row_binding_ids) is not tuple
            or not self.authorized_row_binding_ids
            or self.authorized_row_binding_ids
            != tuple(sorted(set(self.authorized_row_binding_ids)))
            or type(self.source_row_binding_ids) is not tuple
            or not self.source_row_binding_ids
            or self.source_row_binding_ids
            != tuple(sorted(set(self.source_row_binding_ids)))
            or set(self.authorized_row_binding_ids)
            & set(self.source_row_binding_ids)
        ):
            _fail("live batched causal replanning barrier is malformed")
        object.__setattr__(
            self,
            "_barrier_id",
            _hash("barrier", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_replanning_barrier.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization_id,
            "authorization_verification_id": (
                self.authorization_verification_id
            ),
            "execution_ledger_id": self.execution_ledger_id,
            "execution_verification_id": self.execution_verification_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_head_id": self.resulting_head_id,
            "resulting_open_prefix_verification_id": (
                self.resulting_open_prefix_verification_id
            ),
            "resulting_numerical_model_id": self.resulting_numerical_model_id,
            "resulting_proof_id": self.resulting_proof_id,
            "resulting_outcome": self.resulting_outcome.value,
            "authorized_row_binding_ids": list(
                self.authorized_row_binding_ids
            ),
            "source_row_binding_ids": list(self.source_row_binding_ids),
            "changed_row_binding_ids": list(self.authorized_row_binding_ids),
            "reused_row_binding_ids": list(self.source_row_binding_ids),
            "all_authorized_rows_added_exactly_once": True,
            "no_extra_or_missing_modeled_row": True,
            "source_rows_reused_byte_identically": True,
            "parent_epoch_and_signed_prefix_exactly_bound": True,
            "replanning_allowed": True,
            "observer_closed": False,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def barrier_id(self) -> str:
        return self._barrier_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "barrier_id": self.barrier_id}


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalBarrierVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    barrier_id: str
    authorization_id: str
    execution_ledger_id: str
    source_model_epoch_id: str
    resulting_model_epoch_id: str
    resulting_proof_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.barrier_id, "causal barrier verification barrier"),
            (
                self.authorization_id,
                "causal barrier verification authorization",
            ),
            (self.execution_ledger_id, "causal barrier verification ledger"),
            (
                self.source_model_epoch_id,
                "causal barrier verification source epoch",
            ),
            (
                self.resulting_model_epoch_id,
                "causal barrier verification resulting epoch",
            ),
            (
                self.resulting_proof_id,
                "causal barrier verification resulting proof",
            ),
        ):
            _cid(value, label)
        if self._issuer is not _BARRIER_VERIFICATION_ISSUER:
            _fail("causal barrier verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("barrier_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_batched_causal_replanning_"
                "barrier_verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "barrier_id": self.barrier_id,
            "authorization_id": self.authorization_id,
            "execution_ledger_id": self.execution_ledger_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_proof_id": self.resulting_proof_id,
            "semantic_replay_complete": True,
            "replanning_allowed": True,
            "observer_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_ledger_verification(
    ledger: V075LiveBatchedCausalExecutionLedgerV3,
) -> V075LiveBatchedCausalExecutionVerificationV3:
    return V075LiveBatchedCausalExecutionVerificationV3(
        _LEDGER_VERIFICATION_ISSUER,
        ledger.ledger_id,
        ledger.authorization_id,
        ledger.resulting_head_id,
        tuple(item.executed_row_id for item in ledger.executed_rows),
    )


def _freeze_barrier(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    execution_ledger: V075LiveBatchedCausalExecutionLedgerV3,
    execution_verification: V075LiveBatchedCausalExecutionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    portable_replay: bool,
) -> V075LiveBatchedCausalReplanningBarrierV3:
    exact_auth_verification = _exact_authorization_verification(authorization)
    exact_ledger = _freeze_ledger(
        authorization=authorization,
        authorization_verification=authorization_verification,
        open_prefix_verification=resulting_epoch.open_prefix_verification,
        portable_replay=portable_replay,
    )
    exact_ledger_verification = _exact_ledger_verification(exact_ledger)
    if (
        authorization_verification.to_document()
        != exact_auth_verification.to_document()
        or execution_ledger.ledger_id != exact_ledger.ledger_id
        or execution_ledger.canonical_bytes != exact_ledger.canonical_bytes
        or execution_verification.to_document()
        != exact_ledger_verification.to_document()
    ):
        _fail("causal replanning lineage differs from exact execution replay")
    source = authorization.source_closure.source_epoch
    if (
        type(resulting_epoch) is not live_model.V075LiveIncrementalModelEpochV2
        or resulting_epoch.parent_epoch is not source
        or resulting_epoch.occurrence_identity != source.occurrence_identity
        or resulting_epoch.route is not planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        or resulting_epoch.head_id != execution_ledger.resulting_head_id
        or resulting_epoch.open_prefix_verification.verification_id
        != execution_ledger.open_prefix_verification_id
        or resulting_epoch.proof.model.model_id
        != resulting_epoch.model.model_id
    ):
        _fail("causal resulting epoch is not the exact parent/prefix successor")
    authorized = authorization.selected_row_binding_ids
    source_rows = tuple(
        sorted(item.row_binding_id for item in source.model.rows)
    )
    resulting_rows = tuple(
        sorted(item.row_binding_id for item in resulting_epoch.model.rows)
    )
    if (
        resulting_epoch.changed_row_binding_ids != authorized
        or resulting_epoch.reused_row_binding_ids != source_rows
        or resulting_rows != tuple(sorted((*source_rows, *authorized)))
        or tuple(item.row_binding_id for item in execution_ledger.executed_rows)
        != authorized
    ):
        _fail("causal resulting model differs from authorized row union")
    return V075LiveBatchedCausalReplanningBarrierV3(
        _BARRIER_ISSUER,
        authorization.authorization_id,
        exact_auth_verification.verification_id,
        exact_ledger.ledger_id,
        exact_ledger_verification.verification_id,
        source.model_epoch_id,
        source.head_id,
        resulting_epoch.model_epoch_id,
        resulting_epoch.head_id,
        resulting_epoch.open_prefix_verification.verification_id,
        resulting_epoch.model.model_id,
        resulting_epoch.proof.proof_id,
        resulting_epoch.proof.outcome,
        authorized,
        source_rows,
    )


def freeze_v075_live_batched_causal_replanning_barrier_v3(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    execution_ledger: V075LiveBatchedCausalExecutionLedgerV3,
    execution_verification: V075LiveBatchedCausalExecutionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> V075LiveBatchedCausalReplanningBarrierV3:
    return _freeze_barrier(
        authorization=authorization,
        authorization_verification=authorization_verification,
        execution_ledger=execution_ledger,
        execution_verification=execution_verification,
        resulting_epoch=resulting_epoch,
        portable_replay=False,
    )


def verify_v075_live_batched_causal_replanning_barrier_bytes_v3(
    *,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
    execution_ledger: V075LiveBatchedCausalExecutionLedgerV3,
    execution_verification: V075LiveBatchedCausalExecutionVerificationV3,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveBatchedCausalReplanningBarrierV3,
    V075LiveBatchedCausalBarrierVerificationV3,
]:
    document = _strict_document(claimed_bytes, "causal replanning barrier")
    expected = _freeze_barrier(
        authorization=authorization,
        authorization_verification=authorization_verification,
        execution_ledger=execution_ledger,
        execution_verification=execution_verification,
        resulting_epoch=resulting_epoch,
        portable_replay=True,
    )
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("causal replanning barrier differs from exact replay")
    verification = V075LiveBatchedCausalBarrierVerificationV3(
        _BARRIER_VERIFICATION_ISSUER,
        expected.barrier_id,
        expected.authorization_id,
        expected.execution_ledger_id,
        expected.source_model_epoch_id,
        expected.resulting_model_epoch_id,
        expected.resulting_proof_id,
    )
    return expected, verification


class V075LiveBatchedCausalExecutionOutcomeV3(str, Enum):
    CHILD_MODEL_READY_FOR_VERIFIED_REPLANNING = (
        "CHILD_MODEL_READY_FOR_VERIFIED_REPLANNING"
    )


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalExecutionBundleV3:
    _issuer: object = field(repr=False, compare=False)
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    )
    ledger: V075LiveBatchedCausalExecutionLedgerV3
    ledger_verification: V075LiveBatchedCausalExecutionVerificationV3
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    barrier: V075LiveBatchedCausalReplanningBarrierV3
    barrier_verification: V075LiveBatchedCausalBarrierVerificationV3
    outcome: V075LiveBatchedCausalExecutionOutcomeV3
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BUNDLE_ISSUER
            or type(self.authorization)
            is not causal.V075LiveBatchedCausalChildAuthorizationV3
            or type(self.authorization_verification)
            is not causal.V075LiveBatchedCausalChildVerificationV3
            or type(self.ledger) is not V075LiveBatchedCausalExecutionLedgerV3
            or type(self.ledger_verification)
            is not V075LiveBatchedCausalExecutionVerificationV3
            or type(self.resulting_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.barrier)
            is not V075LiveBatchedCausalReplanningBarrierV3
            or type(self.barrier_verification)
            is not V075LiveBatchedCausalBarrierVerificationV3
            or self.outcome
            is not (
                V075LiveBatchedCausalExecutionOutcomeV3
                .CHILD_MODEL_READY_FOR_VERIFIED_REPLANNING
            )
            or self.ledger.authorization_id
            != self.authorization.authorization_id
            or self.barrier.execution_ledger_id != self.ledger.ledger_id
            or self.barrier.resulting_model_epoch_id
            != self.resulting_epoch.model_epoch_id
            or self.barrier_verification.barrier_id != self.barrier.barrier_id
        ):
            _fail("live batched causal execution bundle is malformed")
        object.__setattr__(self, "_bundle_id", _hash("bundle", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_execution_bundle.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization.authorization_id,
            "authorization_verification_id": (
                self.authorization_verification.verification_id
            ),
            "execution_ledger_id": self.ledger.ledger_id,
            "execution_verification_id": (
                self.ledger_verification.verification_id
            ),
            "resulting_model_epoch_id": self.resulting_epoch.model_epoch_id,
            "resulting_numerical_model_id": self.resulting_epoch.model.model_id,
            "resulting_proof_id": self.resulting_epoch.proof.proof_id,
            "resulting_outcome": self.resulting_epoch.proof.outcome.value,
            "replanning_barrier_id": self.barrier.barrier_id,
            "replanning_barrier_verification_id": (
                self.barrier_verification.verification_id
            ),
            "outcome": self.outcome.value,
            "observer_closed": False,
            "semantic_terminal_issued": False,
            "counter_records_issued": 0,
            "production_integration_ready": PRODUCTION_INTEGRATION_READY,
            "official_execution_allowed": False,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization": self.authorization.to_document(),
            "authorization_verification": (
                self.authorization_verification.to_document()
            ),
            "execution_ledger": self.ledger.to_document(),
            "execution_verification": self.ledger_verification.to_document(),
            "resulting_epoch": self.resulting_epoch.to_document(),
            "replanning_barrier": self.barrier.to_document(),
            "replanning_barrier_verification": (
                self.barrier_verification.to_document()
            ),
            "bundle_id": self.bundle_id,
        }


def execute_v075_live_batched_causal_children_v3(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    authorization: causal.V075LiveBatchedCausalChildAuthorizationV3,
    authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ),
) -> V075LiveBatchedCausalExecutionBundleV3:
    """Execute one exact union while leaving the owner-controlled observer open."""

    if (
        type(controller)
        is not control.V075ConstructionControlledPrivateObserverV2
        or type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or schedule.occurrence
        != authorization.source_closure.source_epoch.occurrence_identity
    ):
        _fail("causal executor controller or schedule was transplanted")
    exact_authorization, exact_verification = (
        causal.verify_v075_live_batched_causal_child_authorization_bytes_v3(
            source_epoch=authorization.source_closure.source_epoch,
            namespace=namespace,
            claimed_bytes=authorization.canonical_bytes,
        )
    )
    if (
        exact_authorization.authorization_id != authorization.authorization_id
        or exact_verification.to_document()
        != authorization_verification.to_document()
    ):
        _fail("causal executor authorization verification changed")
    source_prefix = authorization.source_closure.source_epoch.open_prefix_verification
    current_prefix = controller.freeze_owned_open_prefix_v2()
    if (
        current_prefix.verification_id != source_prefix.verification_id
        or current_prefix.to_document() != source_prefix.to_document()
    ):
        _fail("causal executor did not start at the authorization source head")
    templates = {
        item.discovery_intent.intent_id: item
        for item in authorization.validation_templates
    }
    source_append_count = len(controller.controlled_appends)
    source_freeze_count = len(controller.support_freezes)
    role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    for discovery in authorization.discovery_intents:
        template = templates.get(discovery.intent_id)
        if template is None:
            _fail("causal executor discovery lacks validation template")
        discovery_intent = controller.prepare_batch_intent_v2(
            stream_identity=discovery.stream_identity,
            semantic_authority_role=role,
            semantic_authority_schema=schema,
            semantic_artifact_id=discovery.intent_id,
            semantic_verification_id=exact_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_DISCOVERY_DRAWS,
            accepted_draw_cap=dynamic.CHILD_DISCOVERY_DRAWS,
        )
        discovery_append = controller.execute_batch_intent_v2(
            discovery_intent
        )
        support = controller.freeze_complete_support_v2(
            discovery_append=discovery_append
        )
        validation_stream = (
            control.derive_v075_controlled_validation_stream_v2(
                support_freeze=support
            )
        )
        validation_intent = controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            semantic_authority_role=role,
            semantic_authority_schema=schema,
            semantic_artifact_id=template.template_id,
            semantic_verification_id=exact_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_VALIDATION,
            round_index=0,
            support_freeze_id=support.freeze_id,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_VALIDATION_DRAWS,
            accepted_draw_cap=(
                dynamic.CHILD_VALIDATION_DRAWS
                + dynamic.MAXIMUM_PROMOTION_ROUNDS * dynamic.PROMOTION_DRAWS
            ),
        )
        controller.execute_batch_intent_v2(validation_intent)
    expected_count = len(authorization.discovery_intents)
    if (
        len(controller.controlled_appends) - source_append_count
        != 2 * expected_count
        or len(controller.support_freezes) - source_freeze_count
        != expected_count
    ):
        _fail("causal executor appended partial or extra observation work")
    prefix = controller.freeze_owned_open_prefix_v2()
    ledger = freeze_v075_live_batched_causal_execution_ledger_v3(
        authorization=authorization,
        authorization_verification=exact_verification,
        open_prefix_verification=prefix,
    )
    ledger, ledger_verification = (
        verify_v075_live_batched_causal_execution_ledger_bytes_v3(
            authorization=authorization,
            authorization_verification=exact_verification,
            open_prefix_verification=prefix,
            claimed_bytes=ledger.canonical_bytes,
        )
    )
    resulting_epoch = live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=schedule.occurrence,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=prefix,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        parent_epoch=authorization.source_closure.source_epoch,
    )
    barrier = freeze_v075_live_batched_causal_replanning_barrier_v3(
        authorization=authorization,
        authorization_verification=exact_verification,
        execution_ledger=ledger,
        execution_verification=ledger_verification,
        resulting_epoch=resulting_epoch,
    )
    barrier, barrier_verification = (
        verify_v075_live_batched_causal_replanning_barrier_bytes_v3(
            authorization=authorization,
            authorization_verification=exact_verification,
            execution_ledger=ledger,
            execution_verification=ledger_verification,
            resulting_epoch=resulting_epoch,
            claimed_bytes=barrier.canonical_bytes,
        )
    )
    return V075LiveBatchedCausalExecutionBundleV3(
        _BUNDLE_ISSUER,
        authorization,
        exact_verification,
        ledger,
        ledger_verification,
        resulting_epoch,
        barrier,
        barrier_verification,
        (
            V075LiveBatchedCausalExecutionOutcomeV3
            .CHILD_MODEL_READY_FOR_VERIFIED_REPLANNING
        ),
    )


__all__ = (
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "V075LiveBatchedCausalBarrierVerificationV3",
    "V075LiveBatchedCausalExecutedRowV3",
    "V075LiveBatchedCausalExecutionBundleV3",
    "V075LiveBatchedCausalExecutionLedgerV3",
    "V075LiveBatchedCausalExecutionOutcomeV3",
    "V075LiveBatchedCausalExecutionV3InvariantViolation",
    "V075LiveBatchedCausalExecutionVerificationV3",
    "V075LiveBatchedCausalReplanningBarrierV3",
    "execute_v075_live_batched_causal_children_v3",
    "freeze_v075_live_batched_causal_execution_ledger_v3",
    "freeze_v075_live_batched_causal_replanning_barrier_v3",
    "verify_v075_live_batched_causal_execution_ledger_bytes_v3",
    "verify_v075_live_batched_causal_replanning_barrier_bytes_v3",
)
