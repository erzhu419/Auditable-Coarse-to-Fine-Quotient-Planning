"""Construction-only five-frame IPC profile for the H1 two-process route.

The profile replaces the historical ``PARENT_OUTPUT`` frame with a read-only
result verification ``WORKER_ACK``.  It freezes payload schemas and identity
binding but does not open sockets, authenticate kernel credentials, or launch
either child.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, NoReturn

from acfqp import construction_k7_h1_business_adapter_v1 as adapter_v1
from acfqp import construction_k7_h1_execution_topology_profile_v1 as topology_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_BROKER_IPC_BINDING_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_TRANSCRIPT_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_ACK_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_EOF_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_READY_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BUSINESS_RESULT_COMMIT_RECEIPT_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_WORKER_RESULT_VERIFICATION_CANDIDATE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.55"
PROFILE_KEY = "construction_k7_h1_broker_ipc_v1"
CONSTRUCTION_ONLY = True
LIVE_CHANNEL_WIRED = False
KERNEL_CREDENTIALS_VERIFIED = False
OFFICIAL_EXECUTION_ALLOWED = False

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_BROKER_IPC_PROFILE_V1_DOMAIN
BINDING_DOMAIN = CONSTRUCTION_K7_H1_BROKER_IPC_BINDING_CANDIDATE_V1_DOMAIN
TRANSCRIPT_DOMAIN = CONSTRUCTION_K7_H1_BROKER_IPC_TRANSCRIPT_CANDIDATE_V1_DOMAIN
COMMIT_CANDIDATE_DOMAIN = (
    CONSTRUCTION_K7_H1_BUSINESS_RESULT_COMMIT_RECEIPT_CANDIDATE_V1_DOMAIN
)
WORKER_VERIFICATION_CANDIDATE_DOMAIN = (
    CONSTRUCTION_K7_H1_WORKER_RESULT_VERIFICATION_CANDIDATE_V1_DOMAIN
)
ROLE_DOMAINS = {
    "WORKER_READY": CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_READY_CANDIDATE_V1_DOMAIN,
    "BUSINESS_REQUEST": CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN,
    "BUSINESS_RESULT": CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN,
    "WORKER_ACK": CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_ACK_CANDIDATE_V1_DOMAIN,
    "WORKER_EOF": CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_EOF_CANDIDATE_V1_DOMAIN,
}
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    BINDING_DOMAIN,
    *ROLE_DOMAINS.values(),
    COMMIT_CANDIDATE_DOMAIN,
    WORKER_VERIFICATION_CANDIDATE_DOMAIN,
    TRANSCRIPT_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover
    raise RuntimeError("H1 broker IPC domains are not uniquely registered")

_PROFILE_ISSUER = object()
_BINDING_ISSUER = object()
_FRAME_ISSUER = object()
_TRANSCRIPT_ISSUER = object()


class ConstructionK7H1BrokerIPCV1Error(ValueError):
    """The H1 IPC profile, binding, frame, or transcript is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1BrokerIPCV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BrokerIPCV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 digest")
    return value


class H1BrokerFrameRoleV1(str, Enum):
    WORKER_READY = "WORKER_READY"
    BUSINESS_REQUEST = "BUSINESS_REQUEST"
    BUSINESS_RESULT = "BUSINESS_RESULT"
    WORKER_ACK = "WORKER_ACK"
    WORKER_EOF = "WORKER_EOF"


FRAME_ROLES = tuple(H1BrokerFrameRoleV1)
FRAME_AUTHORS = (
    "WORKER",
    "WORKER",
    "BUSINESS",
    "WORKER",
    "WORKER",
)
FRAME_RECIPIENTS = (
    "BROKER",
    "BROKER_RELAY_TO_BUSINESS",
    "BROKER_RELAY_TO_WORKER",
    "BROKER",
    "BROKER",
)

_PAYLOAD_FIELDS = {
    H1BrokerFrameRoleV1.WORKER_READY: frozenset(
        {"worker_role_instance_id", "ready_candidate"}
    ),
    H1BrokerFrameRoleV1.BUSINESS_REQUEST: frozenset(
        {
            "h1_production_business_request_candidate_id",
            "request_ordinal",
            "sealed_request_fd_is_payload_carrier",
            "worker_frame_is_authorization_signal_only",
        }
    ),
    H1BrokerFrameRoleV1.BUSINESS_RESULT: frozenset(
        {
            "h1_production_business_result_candidate_id",
            "business_result_sha256",
            "business_result_byte_count",
            "business_result_commit_receipt_candidate_id",
            "outcome",
            "relay_same_canonical_frame_to_worker",
            "commit_receipt_authority",
            "commit_receipt_runtime_verification_pending",
        }
    ),
    H1BrokerFrameRoleV1.WORKER_ACK: frozenset(
        {
            "h1_production_business_result_candidate_id",
            "business_result_sha256",
            "business_result_byte_count",
            "business_result_commit_receipt_candidate_id",
            "worker_result_verification_candidate_id",
            "read_only_distinct_ofd_authority",
            "worker_verification_authority",
            "worker_runtime_verification_pending",
        }
    ),
    H1BrokerFrameRoleV1.WORKER_EOF: frozenset(
        {"worker_ack_candidate_id", "clean_close_candidate"}
    ),
}

_BINDING_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_broker_ipc_profile_id",
        "h1_execution_topology_profile_id",
        "h1_production_business_request_candidate_id",
        "current_access_candidate_id",
        "formal_v7_decision_candidate_id",
        "RouteDecisionContext_id",
        "decision_point_id",
        "formal_v7_route_upper_id",
        "formal_v7_route_decision_id",
        "structural_id",
        "query_id",
        "selected_plan_id",
        "threshold_profile_id",
        "BuildEpoch_id",
        "kernel_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
        "exact_infeasibility_identity_id",
        "durable_proof_id",
        "h1_search_semantics_bridge_id",
        "search_semantics_id",
        "search_semantics_structural_id",
        "search_semantics_kernel_id",
        "search_semantics_derived_query_id",
        "search_semantics_threshold_profile_id",
        "search_semantics_reward_profile_id",
        "search_semantics_policy_class_id",
        "search_semantics_complete_search_profile_id",
        "kernel_replay_document_id",
        "query_replay_document_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "ground_fallback_cap_profile_id",
        "counter_registry_id",
        "route_decision_freeze_barrier_id",
        "predecision_read_barrier_sequence",
        "decision_verification_sequence",
        "route_decision_freeze_sequence",
        "request_issuance_sequence",
        "broker_execution_spec_id",
        "session_nonce",
        "frame_count",
        "live_sender_credentials_verified",
        "live_channel_wired",
        "production_binding_authority",
        "production_consumers_must_reject_candidate",
        "official_execution_allowed",
        "construction_only",
    }
)


def _validate_payload(role: H1BrokerFrameRoleV1, payload: dict[str, Any]) -> None:
    if type(payload) is not dict or frozenset(payload) != _PAYLOAD_FIELDS[role]:
        _fail(f"{role.value} payload fields are not exact")
    if role is H1BrokerFrameRoleV1.WORKER_READY:
        _cid(payload["worker_role_instance_id"], "worker role instance")
        if payload["ready_candidate"] is not True:
            _fail("WORKER_READY candidate flag must be exact true")
    elif role is H1BrokerFrameRoleV1.BUSINESS_REQUEST:
        _cid(
            payload["h1_production_business_request_candidate_id"],
            "business request candidate",
        )
        if (
            type(payload["request_ordinal"]) is not int
            or payload["request_ordinal"] != 0
            or payload["sealed_request_fd_is_payload_carrier"] is not True
            or payload["worker_frame_is_authorization_signal_only"] is not True
        ):
            _fail("BUSINESS_REQUEST payload values are invalid")
    elif role is H1BrokerFrameRoleV1.BUSINESS_RESULT:
        for key in (
            "h1_production_business_result_candidate_id",
            "business_result_commit_receipt_candidate_id",
        ):
            _cid(payload[key], key)
        _sha(payload["business_result_sha256"], "business result")
        if (
            type(payload["business_result_byte_count"]) is not int
            or payload["business_result_byte_count"] <= 0
            or payload["outcome"] not in {"INFEASIBLE_CERTIFIED", "CAP_EXHAUSTED"}
            or payload["relay_same_canonical_frame_to_worker"] is not True
            or payload["commit_receipt_authority"] is not False
            or payload["commit_receipt_runtime_verification_pending"] is not True
        ):
            _fail("BUSINESS_RESULT payload values are invalid")
    elif role is H1BrokerFrameRoleV1.WORKER_ACK:
        for key in (
            "h1_production_business_result_candidate_id",
            "business_result_commit_receipt_candidate_id",
            "worker_result_verification_candidate_id",
        ):
            _cid(payload[key], key)
        _sha(payload["business_result_sha256"], "worker result")
        if (
            type(payload["business_result_byte_count"]) is not int
            or payload["business_result_byte_count"] <= 0
            or payload["read_only_distinct_ofd_authority"] is not False
            or payload["worker_verification_authority"] is not False
            or payload["worker_runtime_verification_pending"] is not True
        ):
            _fail("WORKER_ACK payload values are invalid")
    else:
        _cid(payload["worker_ack_candidate_id"], "worker ACK candidate")
        if payload["clean_close_candidate"] is not True:
            _fail("WORKER_EOF candidate close flag must be exact true")


@dataclass(frozen=True, slots=True)
class H1BrokerIPCProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("H1 broker IPC profile is issuer-owned")
        object.__setattr__(self, "_profile_id", content_id(PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_broker_ipc_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "frame_roles": [role.value for role in FRAME_ROLES],
            "frame_authors": list(FRAME_AUTHORS),
            "frame_recipients": list(FRAME_RECIPIENTS),
            "business_request_payload_delivery": "SEALED_INHERITED_REQUEST_FD",
            "business_request_frame_semantics": "WORKER_AUTHORIZATION_SIGNAL_RELAYED_BY_BROKER",
            "business_result_frame_relayed_to_worker": True,
            "worker_result_access": "READ_ONLY_DISTINCT_OFD",
            "legacy_parent_output_frame_allowed": False,
            "scm_rights_allowed": False,
            "fixed_inherited_fds_required": True,
            "payload_semantics_frozen": True,
            "binding_frame_and_transcript_domains_are_candidate_only": True,
            "commit_and_worker_evidence_are_typed_candidates": True,
            "production_ipc_authority_present": False,
            "live_channel_wired": False,
            "kernel_credentials_verified": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def profile_id(self) -> str:
        if content_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("H1 broker IPC profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_broker_ipc_profile_id": self.profile_id}


_OFFICIAL_PROFILE = H1BrokerIPCProfileV1(_PROFILE_ISSUER)


def official_h1_broker_ipc_profile_v1() -> H1BrokerIPCProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class H1BusinessResultCommitReceiptCandidateV1:
    _issuer: InitVar[object]
    business_result_candidate_id: str
    business_result_sha256: str
    business_result_byte_count: int
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FRAME_ISSUER:
            _fail("business-result commit receipt candidate is issuer-owned")
        _cid(self.business_result_candidate_id, "business result candidate")
        _sha(self.business_result_sha256, "business result")
        if (
            type(self.business_result_byte_count) is not int
            or self.business_result_byte_count <= 0
        ):
            _fail("business-result candidate extent must be a positive exact int")
        object.__setattr__(
            self,
            "_candidate_id",
            content_id(COMMIT_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_business_result_commit_receipt_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_business_result_candidate_id": (
                self.business_result_candidate_id
            ),
            "business_result_sha256": self.business_result_sha256,
            "business_result_byte_count": self.business_result_byte_count,
            "write_observed": False,
            "fsync_observed": False,
            "linkat_observed": False,
            "rename_noreplace_observed": False,
            "directory_fsync_observed": False,
            "reread_observed": False,
            "business_exit_before_relay_observed": False,
            "commit_receipt_authority": False,
            "production_consumers_must_reject_candidate": True,
            "construction_only": True,
        }

    @property
    def candidate_id(self) -> str:
        if content_id(COMMIT_CANDIDATE_DOMAIN, self._payload()) != self._candidate_id:
            _fail("business-result commit receipt candidate changed")
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "business_result_commit_receipt_candidate_id": self.candidate_id,
        }


def freeze_business_result_commit_receipt_candidate_v1(
    *, business_result: adapter_v1.H1ProductionBusinessResultCandidateV1
) -> H1BusinessResultCommitReceiptCandidateV1:
    if type(business_result) is not adapter_v1.H1ProductionBusinessResultCandidateV1:
        _fail("commit receipt candidate requires an exact business-result candidate")
    _ = business_result.result_id
    return H1BusinessResultCommitReceiptCandidateV1(
        _FRAME_ISSUER,
        business_result.result_id,
        business_result.sha256,
        business_result.byte_count,
    )


@dataclass(frozen=True, slots=True)
class H1WorkerResultVerificationCandidateV1:
    _issuer: InitVar[object]
    commit_candidate: H1BusinessResultCommitReceiptCandidateV1
    topology_profile_id: str
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _FRAME_ISSUER
            or type(self.commit_candidate)
            is not H1BusinessResultCommitReceiptCandidateV1
        ):
            _fail("worker result-verification candidate is issuer-owned")
        _ = self.commit_candidate.candidate_id
        _cid(self.topology_profile_id, "execution topology profile")
        object.__setattr__(
            self,
            "_candidate_id",
            content_id(WORKER_VERIFICATION_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        commit = self.commit_candidate
        return {
            "schema": "acfqp.h1_worker_result_verification_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": self.topology_profile_id,
            "h1_production_business_result_candidate_id": (
                commit.business_result_candidate_id
            ),
            "business_result_sha256": commit.business_result_sha256,
            "business_result_byte_count": commit.business_result_byte_count,
            "business_result_commit_receipt_candidate_id": commit.candidate_id,
            "read_only_distinct_ofd_observed": False,
            "canonical_reread_observed": False,
            "worker_verification_authority": False,
            "production_consumers_must_reject_candidate": True,
            "construction_only": True,
        }

    @property
    def candidate_id(self) -> str:
        if (
            content_id(WORKER_VERIFICATION_CANDIDATE_DOMAIN, self._payload())
            != self._candidate_id
        ):
            _fail("worker result-verification candidate changed")
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "worker_result_verification_candidate_id": self.candidate_id,
        }


def freeze_worker_result_verification_candidate_v1(
    *,
    commit_candidate: H1BusinessResultCommitReceiptCandidateV1,
    topology: topology_v1.H1ExecutionTopologyProfileV1,
) -> H1WorkerResultVerificationCandidateV1:
    official = topology_v1.official_h1_execution_topology_profile_v1()
    if (
        type(commit_candidate) is not H1BusinessResultCommitReceiptCandidateV1
        or type(topology) is not topology_v1.H1ExecutionTopologyProfileV1
        or topology.to_document() != official.to_document()
    ):
        _fail("worker verification candidate inputs are not exact")
    return H1WorkerResultVerificationCandidateV1(
        _FRAME_ISSUER, commit_candidate, topology.profile_id
    )


@dataclass(frozen=True, slots=True)
class H1BrokerIPCBindingV1:
    _issuer: InitVar[object]
    fields: dict[str, Any]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BINDING_ISSUER
            or type(self.fields) is not dict
            or frozenset(self.fields) != _BINDING_FIELDS
        ):
            _fail("H1 broker IPC binding is issuer-owned")
        for name in _BINDING_FIELDS - {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "predecision_read_barrier_sequence",
            "decision_verification_sequence",
            "route_decision_freeze_sequence",
            "request_issuance_sequence",
            "frame_count",
            "live_sender_credentials_verified",
            "live_channel_wired",
            "production_binding_authority",
            "production_consumers_must_reject_candidate",
            "official_execution_allowed",
            "construction_only",
        }:
            _cid(self.fields[name], name)
        if (
            self.fields["schema"] != "acfqp.h1_broker_ipc_binding_candidate.v1"
            or self.fields["schema_version"] != SCHEMA_VERSION
            or self.fields["proposed_contract_version"]
            != PROPOSED_CONTRACT_VERSION
            or self.fields["profile_key"] != PROFILE_KEY
            or type(self.fields["predecision_read_barrier_sequence"]) is not int
            or type(self.fields["decision_verification_sequence"]) is not int
            or type(self.fields["route_decision_freeze_sequence"]) is not int
            or type(self.fields["request_issuance_sequence"]) is not int
            or not (
                self.fields["predecision_read_barrier_sequence"]
                < self.fields["decision_verification_sequence"]
                < self.fields["route_decision_freeze_sequence"]
                < self.fields["request_issuance_sequence"]
            )
            or type(self.fields["frame_count"]) is not int
            or self.fields["frame_count"] != 5
            or self.fields["live_sender_credentials_verified"] is not False
            or self.fields["live_channel_wired"] is not False
            or self.fields["production_binding_authority"] is not False
            or self.fields["production_consumers_must_reject_candidate"] is not True
            or self.fields["official_execution_allowed"] is not False
            or self.fields["construction_only"] is not True
        ):
            _fail("H1 broker IPC binding values are invalid")
        canonical_json_bytes(self.fields)
        object.__setattr__(self, "_binding_id", content_id(BINDING_DOMAIN, self.fields))

    def _payload(self) -> dict[str, Any]:
        return dict(self.fields)

    @property
    def binding_id(self) -> str:
        if content_id(BINDING_DOMAIN, self._payload()) != self._binding_id:
            _fail("H1 broker IPC binding changed")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_broker_ipc_binding_id": self.binding_id}


def freeze_h1_broker_ipc_binding_v1(
    *,
    request: adapter_v1.H1ProductionBusinessRequestCandidateV1,
    topology: topology_v1.H1ExecutionTopologyProfileV1,
    broker_execution_spec_id: str,
    session_nonce: str,
) -> H1BrokerIPCBindingV1:
    if type(request) is not adapter_v1.H1ProductionBusinessRequestCandidateV1:
        _fail("H1 IPC binding requires its exact retained business request")
    request_document = request.to_document()
    official_topology = topology_v1.official_h1_execution_topology_profile_v1()
    if type(topology) is not topology_v1.H1ExecutionTopologyProfileV1 or topology.to_document() != official_topology.to_document():
        _fail("H1 IPC binding requires the exact execution topology")
    _cid(broker_execution_spec_id, "broker execution spec")
    _cid(session_nonce, "broker session nonce")
    fields = {
        "schema": "acfqp.h1_broker_ipc_binding_candidate.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_broker_ipc_profile_id": _OFFICIAL_PROFILE.profile_id,
        "h1_execution_topology_profile_id": topology.profile_id,
        "h1_production_business_request_candidate_id": request.request_id,
        "current_access_candidate_id": request_document["current_access_candidate_id"],
        "formal_v7_decision_candidate_id": request_document[
            "formal_v7_decision_candidate_id"
        ],
        "RouteDecisionContext_id": request_document["RouteDecisionContext_id"],
        "decision_point_id": request_document["decision_point_id"],
        "formal_v7_route_upper_id": request_document["formal_v7_route_upper_id"],
        "formal_v7_route_decision_id": request_document["formal_v7_route_decision_id"],
        "structural_id": request_document["structural_id"],
        "query_id": request_document["query_id"],
        "selected_plan_id": request_document["selected_plan_id"],
        "threshold_profile_id": request_document["threshold_profile_id"],
        "BuildEpoch_id": request_document["BuildEpoch_id"],
        "kernel_id": request_document["kernel_id"],
        "reward_profile_id": request_document["reward_profile_id"],
        "policy_class_id": request_document["policy_class_id"],
        "complete_search_profile_id": request_document[
            "complete_search_profile_id"
        ],
        "exact_infeasibility_identity_id": request_document[
            "exact_infeasibility_identity_id"
        ],
        "durable_proof_id": request_document["durable_proof_id"],
        "h1_search_semantics_bridge_id": request_document[
            "h1_search_semantics_bridge_id"
        ],
        "search_semantics_id": request_document["search_semantics_id"],
        "search_semantics_structural_id": request_document[
            "search_semantics_structural_id"
        ],
        "search_semantics_kernel_id": request_document[
            "search_semantics_kernel_id"
        ],
        "search_semantics_derived_query_id": request_document[
            "search_semantics_derived_query_id"
        ],
        "search_semantics_threshold_profile_id": request_document[
            "search_semantics_threshold_profile_id"
        ],
        "search_semantics_reward_profile_id": request_document[
            "search_semantics_reward_profile_id"
        ],
        "search_semantics_policy_class_id": request_document[
            "search_semantics_policy_class_id"
        ],
        "search_semantics_complete_search_profile_id": request_document[
            "search_semantics_complete_search_profile_id"
        ],
        "kernel_replay_document_id": request_document[
            "kernel_replay_document_id"
        ],
        "query_replay_document_id": request_document[
            "query_replay_document_id"
        ],
        "ground_fallback_cap_profile_id": request_document["ground_fallback_cap_profile_id"],
        "counter_registry_id": request_document["counter_registry_id"],
        "logical_occurrence_id": request_document["logical_occurrence_id"],
        "route_attempt_id": request_document["route_attempt_id"],
        "route_decision_freeze_barrier_id": request_document[
            "route_decision_freeze_barrier_id"
        ],
        "route_decision_freeze_sequence": request_document[
            "route_decision_freeze_sequence"
        ],
        "predecision_read_barrier_sequence": request_document[
            "predecision_read_barrier_sequence"
        ],
        "decision_verification_sequence": request_document[
            "decision_verification_sequence"
        ],
        "request_issuance_sequence": request_document[
            "request_issuance_sequence"
        ],
        "broker_execution_spec_id": broker_execution_spec_id,
        "session_nonce": session_nonce,
        "frame_count": 5,
        "live_sender_credentials_verified": False,
        "live_channel_wired": False,
        "production_binding_authority": False,
        "production_consumers_must_reject_candidate": True,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    return H1BrokerIPCBindingV1(_BINDING_ISSUER, fields)


@dataclass(frozen=True, slots=True)
class _H1BrokerFrameV1:
    _issuer: InitVar[object]
    role: H1BrokerFrameRoleV1
    binding_id: str
    sequence: int
    predecessor_id: str
    payload: dict[str, Any]
    _frame_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FRAME_ISSUER:
            _fail("H1 broker frame is issuer-owned")
        try:
            object.__setattr__(self, "role", H1BrokerFrameRoleV1(self.role))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1BrokerIPCV1Error("H1 frame role is invalid") from error
        _cid(self.binding_id, "H1 frame binding")
        _cid(self.predecessor_id, "H1 frame predecessor")
        if (
            type(self.sequence) is not int
            or self.sequence != FRAME_ROLES.index(self.role) + 1
            or type(self.payload) is not dict
        ):
            _fail("H1 frame sequence or payload is invalid")
        _validate_payload(self.role, self.payload)
        canonical_json_bytes(self.payload)
        object.__setattr__(self, "_frame_id", content_id(ROLE_DOMAINS[self.role.value], self._payload()))

    def _payload(self) -> dict[str, Any]:
        index = self.sequence - 1
        return {
            "schema": (
                f"acfqp.h1_broker_ipc_{self.role.value.lower()}_candidate.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_broker_ipc_binding_id": self.binding_id,
            "frame_role": self.role.value,
            "frame_author": FRAME_AUTHORS[index],
            "frame_recipient": FRAME_RECIPIENTS[index],
            "frame_sequence": self.sequence,
            "predecessor_id": self.predecessor_id,
            "payload": dict(self.payload),
            "kernel_sender_credentials_verified": False,
            "frame_authority": False,
            "production_consumers_must_reject_candidate": True,
            "construction_only": True,
        }

    @property
    def frame_id(self) -> str:
        if content_id(ROLE_DOMAINS[self.role.value], self._payload()) != self._frame_id:
            _fail("H1 broker frame changed")
        return self._frame_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_broker_ipc_frame_id": self.frame_id}


def _frame(
    binding: H1BrokerIPCBindingV1,
    role: H1BrokerFrameRoleV1,
    predecessor_id: str,
    payload: dict[str, Any],
) -> _H1BrokerFrameV1:
    if type(binding) is not H1BrokerIPCBindingV1:
        _fail("H1 frame requires one exact binding")
    _ = binding.binding_id
    return _H1BrokerFrameV1(
        _FRAME_ISSUER,
        role,
        binding.binding_id,
        FRAME_ROLES.index(role) + 1,
        predecessor_id,
        payload,
    )


def issue_worker_ready_v1(
    *, binding: H1BrokerIPCBindingV1, worker_role_instance_id: str
) -> _H1BrokerFrameV1:
    _cid(worker_role_instance_id, "worker role instance")
    return _frame(
        binding,
        H1BrokerFrameRoleV1.WORKER_READY,
        binding.binding_id,
        {
            "worker_role_instance_id": worker_role_instance_id,
            "ready_candidate": True,
        },
    )


def issue_business_request_v1(
    *, binding: H1BrokerIPCBindingV1, worker_ready: _H1BrokerFrameV1
) -> _H1BrokerFrameV1:
    if (
        type(worker_ready) is not _H1BrokerFrameV1
        or worker_ready.role is not H1BrokerFrameRoleV1.WORKER_READY
        or worker_ready.binding_id != binding.binding_id
    ):
        _fail("BUSINESS_REQUEST does not descend from exact WORKER_READY")
    return _frame(
        binding,
        H1BrokerFrameRoleV1.BUSINESS_REQUEST,
        worker_ready.frame_id,
        {
            "h1_production_business_request_candidate_id": binding.fields["h1_production_business_request_candidate_id"],
            "request_ordinal": 0,
            "sealed_request_fd_is_payload_carrier": True,
            "worker_frame_is_authorization_signal_only": True,
        },
    )


def issue_business_result_v1(
    *,
    binding: H1BrokerIPCBindingV1,
    business_request: _H1BrokerFrameV1,
    business_result: adapter_v1.H1ProductionBusinessResultCandidateV1,
    commit_candidate: H1BusinessResultCommitReceiptCandidateV1,
) -> _H1BrokerFrameV1:
    if (
        type(business_request) is not _H1BrokerFrameV1
        or business_request.role is not H1BrokerFrameRoleV1.BUSINESS_REQUEST
        or business_request.binding_id != binding.binding_id
        or type(business_result) is not adapter_v1.H1ProductionBusinessResultCandidateV1
        or business_result.to_document()["h1_production_business_request_candidate_id"]
        != binding.fields["h1_production_business_request_candidate_id"]
        or type(commit_candidate)
        is not H1BusinessResultCommitReceiptCandidateV1
        or commit_candidate.business_result_candidate_id
        != business_result.result_id
        or commit_candidate.business_result_sha256 != business_result.sha256
        or commit_candidate.business_result_byte_count != business_result.byte_count
    ):
        _fail("BUSINESS_RESULT does not bind the exact request/frame chain")
    return _frame(
        binding,
        H1BrokerFrameRoleV1.BUSINESS_RESULT,
        business_request.frame_id,
        {
            "h1_production_business_result_candidate_id": business_result.result_id,
            "business_result_sha256": business_result.sha256,
            "business_result_byte_count": business_result.byte_count,
            "business_result_commit_receipt_candidate_id": (
                commit_candidate.candidate_id
            ),
            "outcome": business_result.to_document()["outcome"],
            "relay_same_canonical_frame_to_worker": True,
            "commit_receipt_authority": False,
            "commit_receipt_runtime_verification_pending": True,
        },
    )


def issue_worker_ack_v1(
    *,
    binding: H1BrokerIPCBindingV1,
    business_result: _H1BrokerFrameV1,
    worker_verification_candidate: H1WorkerResultVerificationCandidateV1,
) -> _H1BrokerFrameV1:
    if (
        type(business_result) is not _H1BrokerFrameV1
        or business_result.role is not H1BrokerFrameRoleV1.BUSINESS_RESULT
        or business_result.binding_id != binding.binding_id
        or type(worker_verification_candidate)
        is not H1WorkerResultVerificationCandidateV1
        or worker_verification_candidate.commit_candidate.candidate_id
        != business_result.payload[
            "business_result_commit_receipt_candidate_id"
        ]
    ):
        _fail("WORKER_ACK does not descend from exact BUSINESS_RESULT")
    payload = business_result.payload
    return _frame(
        binding,
        H1BrokerFrameRoleV1.WORKER_ACK,
        business_result.frame_id,
        {
            "h1_production_business_result_candidate_id": payload["h1_production_business_result_candidate_id"],
            "business_result_sha256": payload["business_result_sha256"],
            "business_result_byte_count": payload["business_result_byte_count"],
            "business_result_commit_receipt_candidate_id": payload[
                "business_result_commit_receipt_candidate_id"
            ],
            "worker_result_verification_candidate_id": (
                worker_verification_candidate.candidate_id
            ),
            "read_only_distinct_ofd_authority": False,
            "worker_verification_authority": False,
            "worker_runtime_verification_pending": True,
        },
    )


def issue_worker_eof_v1(
    *, binding: H1BrokerIPCBindingV1, worker_ack: _H1BrokerFrameV1
) -> _H1BrokerFrameV1:
    if (
        type(worker_ack) is not _H1BrokerFrameV1
        or worker_ack.role is not H1BrokerFrameRoleV1.WORKER_ACK
        or worker_ack.binding_id != binding.binding_id
    ):
        _fail("WORKER_EOF does not descend from exact WORKER_ACK")
    return _frame(
        binding,
        H1BrokerFrameRoleV1.WORKER_EOF,
        worker_ack.frame_id,
        {
            "worker_ack_candidate_id": worker_ack.frame_id,
            "clean_close_candidate": True,
        },
    )


@dataclass(frozen=True, slots=True)
class H1BrokerIPCTranscriptV1:
    _issuer: InitVar[object]
    binding: H1BrokerIPCBindingV1
    frames: tuple[_H1BrokerFrameV1, ...]
    _transcript_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TRANSCRIPT_ISSUER
            or type(self.binding) is not H1BrokerIPCBindingV1
            or type(self.frames) is not tuple
            or tuple(frame.role for frame in self.frames) != FRAME_ROLES
        ):
            _fail("H1 IPC transcript is not the exact five-frame stream")
        predecessor = self.binding.binding_id
        for sequence, frame in enumerate(self.frames, start=1):
            if (
                type(frame) is not _H1BrokerFrameV1
                or frame.binding_id != self.binding.binding_id
                or frame.sequence != sequence
                or frame.predecessor_id != predecessor
            ):
                _fail("H1 IPC transcript chain is discontinuous")
            predecessor = frame.frame_id
        business = self.frames[2].payload
        ack = self.frames[3].payload
        shared_result_fields = (
            "h1_production_business_result_candidate_id",
            "business_result_sha256",
            "business_result_byte_count",
            "business_result_commit_receipt_candidate_id",
        )
        if (
            any(ack.get(name) != business.get(name) for name in shared_result_fields)
            or "worker_result_verification_candidate_id" not in ack
        ):
            _fail("WORKER_ACK does not verify the exact BUSINESS_RESULT tuple")
        _cid(
            ack["worker_result_verification_candidate_id"],
            "worker result verification candidate",
        )
        object.__setattr__(self, "_transcript_id", content_id(TRANSCRIPT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_broker_ipc_transcript_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_broker_ipc_binding_id": self.binding.binding_id,
            "frames": [frame.to_document() for frame in self.frames],
            "frame_count": len(self.frames),
            "five_frame_order_complete": True,
            "live_channel_wired": False,
            "kernel_credentials_verified": False,
            "transcript_authority": False,
            "production_consumers_must_reject_candidate": True,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def transcript_id(self) -> str:
        if content_id(TRANSCRIPT_DOMAIN, self._payload()) != self._transcript_id:
            _fail("H1 IPC transcript changed")
        return self._transcript_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_broker_ipc_transcript_id": self.transcript_id}


def freeze_h1_broker_ipc_transcript_v1(
    *,
    binding: H1BrokerIPCBindingV1,
    worker_ready: _H1BrokerFrameV1,
    business_request: _H1BrokerFrameV1,
    business_result: _H1BrokerFrameV1,
    worker_ack: _H1BrokerFrameV1,
    worker_eof: _H1BrokerFrameV1,
) -> H1BrokerIPCTranscriptV1:
    return H1BrokerIPCTranscriptV1(
        _TRANSCRIPT_ISSUER,
        binding,
        (worker_ready, business_request, business_result, worker_ack, worker_eof),
    )


__all__ = (
    "CONSTRUCTION_ONLY",
    "ConstructionK7H1BrokerIPCV1Error",
    "FRAME_AUTHORS",
    "FRAME_RECIPIENTS",
    "FRAME_ROLES",
    "H1BrokerFrameRoleV1",
    "H1BusinessResultCommitReceiptCandidateV1",
    "H1BrokerIPCBindingV1",
    "H1BrokerIPCProfileV1",
    "H1BrokerIPCTranscriptV1",
    "H1WorkerResultVerificationCandidateV1",
    "KERNEL_CREDENTIALS_VERIFIED",
    "LIVE_CHANNEL_WIRED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "freeze_h1_broker_ipc_binding_v1",
    "freeze_h1_broker_ipc_transcript_v1",
    "freeze_business_result_commit_receipt_candidate_v1",
    "freeze_worker_result_verification_candidate_v1",
    "issue_business_request_v1",
    "issue_business_result_v1",
    "issue_worker_ack_v1",
    "issue_worker_eof_v1",
    "issue_worker_ready_v1",
    "official_h1_broker_ipc_profile_v1",
)
