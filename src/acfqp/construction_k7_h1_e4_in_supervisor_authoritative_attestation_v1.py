"""E5B-A same-supervisor attestation over the exact E4 authority replay.

The authoritative path accepts only the exact retained E4 context and exact
runtime types for the E3/E4 completions.  E3/E4 V1 do not retain completion
object identity, so authority comes from the full E4 semantic reconstruction,
not from a false issuer-ownership claim.  A guardian may later replay the
attestation's structure and the eight persisted output files, but that
portable replay is deliberately not a substitute for the in-process E4
authority call.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import errno
import hashlib
import os
from pathlib import Path
import stat
import threading
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_domain_registry_extension_v13 as domains_v13
from acfqp import construction_k7_h1_e3_bound_output_ordinal_continuation_v1 as e4_v1
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-A"
PROFILE_KEY = "construction_k7_h1_e4_in_supervisor_authoritative_attestation_v1"
READINESS = "E5B_PREREQUISITE_ONLY"
AUTHORITY_DISPOSITION = "IN_SUPERVISOR_E4_AUTHORITATIVE_ATTESTATION_PRESENT"
GUARDIAN_REPLAY_DISPOSITION = "STRUCTURAL_AND_PERSISTED_EIGHT_FILE_REPLAY_ONLY"

IN_SUPERVISOR_E4_AUTHORITATIVE_ATTESTATION_PRESENT = True
GUARDIAN_PERSISTED_EIGHT_FILE_REPLAY_PRESENT = True
GUARDIAN_REPLAY_SUBSTITUTES_SAME_PROCESS_AUTHORITY = False
E5B_INTEGRATED_ROUTE_EXECUTION_PRESENT = False
ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT = False
ROUTE_WIDE_PEAK_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
PEAK_SCOPE_STATUS = "PEAK_SCOPE_UNRESOLVED"
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

_PROFILE_ISSUER = object()
_ATTESTATION_ISSUER = object()
_GUARDIAN_REPLAY_ISSUER = object()
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class ConstructionK7H1E4InSupervisorAttestationV1Error(ValueError):
    """An E5B-A exact-object, identity, authority or replay invariant crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1E4InSupervisorAttestationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            f"{label} is not one exact lowercase content ID"
        ) from error


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v13.extension_content_id_v13(domain, payload)


def _with_id(payload: Mapping[str, Any], *, domain: str, id_field: str) -> dict[str, Any]:
    document = dict(payload)
    document[id_field] = _domain_id(domain, payload)
    return document


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _verify_content_object(
    document: Any,
    *,
    domain: str,
    id_field: str,
    label: str,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = _cid(payload.pop(id_field, None), label)
    if _domain_id(domain, payload) != supplied:
        _fail(f"{label} content ID changed")
    return payload


def _locked_claims() -> dict[str, Any]:
    return {
        "guardian_replay_substitutes_same_process_authority": False,
        "guardian_same_process_authority_inferred": False,
        "content_hash_is_a_signature": False,
        "same_process_private_state_adversary_resistance_claimed": False,
        "e3_completion_exact_object_identity_retained": False,
        "e4_completion_exact_object_identity_retained": False,
        "authenticated_supervisor_binding_present": False,
        "e5b_integrated_route_execution_present": False,
        "route_wide_actual_peak_authority_present": False,
        "route_wide_peak_authority_present": False,
        "production_output_leaf_authority_present": False,
        "fq11_counter_completeness_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_actual_projection_proof_issued": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "peak_scope_status": "PEAK_SCOPE_UNRESOLVED",
        "construction_only": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def _source_identity() -> dict[str, Any]:
    source = e3_v1.official_h1_exclusive_broker_source_manifest_v1().to_document()
    return {
        "h1_exclusive_broker_source_manifest_id": _cid(
            source.get("h1_exclusive_broker_source_manifest_id"),
            "E3 source manifest",
        ),
        "source_sha256": _cid(source.get("source_sha256"), "E3 source sha256"),
        "source_byte_count": source.get("source_byte_count"),
        "interpreter_sha256": _cid(
            source.get("interpreter_sha256"), "E3 interpreter sha256"
        ),
        "interpreter_byte_count": source.get("interpreter_byte_count"),
        "interpreter_device": source.get("interpreter_device"),
        "interpreter_inode": source.get("interpreter_inode"),
    }


def _profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_e4_in_supervisor_attestation_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "authority_disposition": AUTHORITY_DISPOSITION,
        "accepted_context_type": "H1E3BoundOutputContinuationContextV1",
        "accepted_e3_completion_type": "H1ExclusiveBrokerCompletionV1",
        "accepted_e4_completion_type": "H1E3BoundOutputCompletionV1",
        "current_h1_exclusive_broker_profile_id": (
            e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
        ),
        "current_h1_exclusive_broker_source_identity": _source_identity(),
        "current_h1_e3_bound_output_continuation_profile_id": (
            e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id
        ),
        "exact_retained_context_required": True,
        "exact_e3_completion_runtime_type_required": True,
        "exact_e4_completion_runtime_type_required": True,
        "e3_completion_exact_object_identity_retained": False,
        "e4_completion_exact_object_identity_retained": False,
        "e4_authoritative_verifier_call_required": True,
        "same_process_and_preparer_thread_required": True,
        "authenticated_supervisor_binding_present": False,
        "completion_context_e3_profile_source_directory_chain_required": True,
        "eight_output_inode_identities_required": True,
        "guardian_allowed_replay": GUARDIAN_REPLAY_DISPOSITION,
        "guardian_may_call_e4_authoritative_verifier": False,
        "in_supervisor_e4_authoritative_attestation_present": True,
        "guardian_persisted_eight_file_replay_present": True,
        **_locked_claims(),
    }


@dataclass(frozen=True, slots=True)
class H1E4InSupervisorAttestationProfileV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("E5B-A profile is caller-minted")
        payload = _canonical_document(self.canonical_bytes, "E5B-A profile")
        object.__setattr__(
            self,
            "profile_id",
            _domain_id(
                domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_ATTESTATION_PROFILE_V1_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.canonical_bytes, "E5B-A profile"),
            "h1_e4_in_supervisor_attestation_profile_id": self.profile_id,
        }


_PROFILE = H1E4InSupervisorAttestationProfileV1(
    _PROFILE_ISSUER, canonical_json_bytes(_profile_payload())
)


def official_h1_e4_in_supervisor_attestation_profile_v1(
) -> H1E4InSupervisorAttestationProfileV1:
    return _PROFILE


@dataclass(frozen=True, slots=True, eq=False)
class H1E4InSupervisorAuthoritativeAttestationV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    _owner_pid: int = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    attestation_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("E5B-A authoritative attestation is caller-minted")
        if self._owner_pid != os.getpid() or self._owner_thread_id != threading.get_ident():
            _fail("E5B-A authoritative attestation crossed its issuing process/thread")
        document = _canonical_document(
            self.canonical_bytes, "E5B-A authoritative attestation"
        )
        payload = _verify_content_object(
            document,
            domain=(
                domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN
            ),
            id_field="h1_e4_in_supervisor_authoritative_attestation_id",
            label="E5B-A authoritative attestation",
        )
        object.__setattr__(
            self,
            "attestation_id",
            document["h1_e4_in_supervisor_authoritative_attestation_id"],
        )
        if payload.get("authority_disposition") != AUTHORITY_DISPOSITION:
            _fail("E5B-A authoritative attestation disposition changed")

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(
            self.canonical_bytes, "E5B-A authoritative attestation"
        )

    def __copy__(self) -> NoReturn:
        _fail("E5B-A authoritative attestation cannot be copied")

    def __deepcopy__(self, _memo: Any) -> NoReturn:
        _fail("E5B-A authoritative attestation cannot be deep-copied")

    def __reduce__(self) -> NoReturn:
        _fail("E5B-A authoritative attestation cannot be pickled")


@dataclass(frozen=True, slots=True)
class H1E4GuardianPersistedReplayV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    replay_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _GUARDIAN_REPLAY_ISSUER:
            _fail("E5B-A guardian replay is caller-minted")
        document = _canonical_document(self.canonical_bytes, "E5B-A guardian replay")
        _verify_content_object(
            document,
            domain=domains_v13.CONSTRUCTION_K7_H1_E4_GUARDIAN_PERSISTED_REPLAY_V1_DOMAIN,
            id_field="h1_e4_guardian_persisted_replay_id",
            label="E5B-A guardian replay",
        )
        object.__setattr__(
            self, "replay_id", document["h1_e4_guardian_persisted_replay_id"]
        )

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(self.canonical_bytes, "E5B-A guardian replay")


_ISSUED_LOCK = threading.RLock()
_ISSUED_ATTESTATIONS: dict[
    int,
    tuple[
        H1E4InSupervisorAuthoritativeAttestationV1,
        bytes,
        int,
        int,
    ],
] = {}


def _e4_completion_document(value: Any) -> dict[str, Any]:
    if type(value) is e4_v1.H1E3BoundOutputCompletionV1:
        document = value.to_document()
    elif type(value) is dict:
        document = loads_canonical_json(canonical_json_bytes(value))
    else:
        _fail("E5B-A requires one exact-runtime-type E4 completion or persisted mapping")
    try:
        e4_v1.verify_h1_e3_bound_output_completion_structure_v1(document)
    except Exception as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A E4 completion structural replay failed"
        ) from error
    return document


def _output_identity_rows(completion: Mapping[str, Any]) -> list[dict[str, Any]]:
    role_documents = completion["durable_role_documents"]
    commits = completion["durable_role_commits"]
    events = completion["output_ordinal_events_53_to_60"]
    inventory = completion["ordinal_61_finalization"]["exact_directory_inventory"]
    rows: list[dict[str, Any]] = []
    for role, role_document, commit, event, inode in zip(
        e4_v1.ROLE_ORDER, role_documents, commits, events, inventory
    ):
        raw = canonical_json_bytes(role_document)
        rows.append(
            {
                "role": role,
                "normal_ordinal": e4_v1.ROLE_ORDINALS[role],
                "file_name": e4_v1.ROLE_FILE_NAMES[role],
                "construction_role_witness_id": commit[
                    "construction_role_witness_id"
                ],
                "h1_e3_bound_output_role_commit_id": commit[
                    "h1_e3_bound_output_role_commit_id"
                ],
                "h1_e3_bound_output_ordinal_event_id": event[
                    "h1_e3_bound_output_ordinal_event_id"
                ],
                "sha256": _sha(raw),
                "byte_count": len(raw),
                "device": inode["device"],
                "inode": inode["inode"],
                "mode": inode["mode"],
                "nlink": inode["nlink"],
            }
        )
    return rows


def _attestation_payload(completion: Mapping[str, Any]) -> dict[str, Any]:
    role_zero = completion["durable_role_documents"][0]
    source_identity = _source_identity()
    raw_completion = canonical_json_bytes(completion)
    return {
        "schema": "acfqp.k7_h1_e4_in_supervisor_authoritative_attestation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e4_in_supervisor_attestation_profile_id": _PROFILE.profile_id,
        "authority_disposition": AUTHORITY_DISPOSITION,
        "readiness": READINESS,
        "identity_chain": {
            "h1_e3_bound_output_completion_id": completion[
                "h1_e3_bound_output_completion_id"
            ],
            "e4_completion_sha256": _sha(raw_completion),
            "e4_completion_byte_count": len(raw_completion),
            "h1_e3_bound_output_continuation_context_id": completion[
                "h1_e3_bound_output_continuation_context_id"
            ],
            "h1_exclusive_broker_completion_id": completion[
                "h1_exclusive_broker_completion_id"
            ],
            "e3_session_nonce": completion["e3_session_nonce"],
            "h1_e3_bound_output_continuation_profile_id": (
                e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id
            ),
            "h1_exclusive_broker_profile_id": (
                e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
            ),
            "h1_exclusive_broker_source_identity": source_identity,
            "caller_binding_id": role_zero["caller_binding_id"],
            "logical_occurrence_id": role_zero["logical_occurrence_id"],
            "route_attempt_id": role_zero["route_attempt_id"],
        },
        "output_directory_identity": completion["writer_allocation"][
            "output_directory"
        ],
        "persisted_output_identities": _output_identity_rows(completion),
        "same_process_authority_evidence": {
            "exact_retained_context_object_verified": True,
            "exact_e3_completion_runtime_type_verified": True,
            "exact_e4_completion_runtime_type_verified": True,
            "e3_completion_exact_object_identity_retained": False,
            "e4_completion_exact_object_identity_retained": False,
            "context_preparer_process_and_thread_matched": True,
            "e4_authoritative_verifier_invoked": True,
            "e4_authoritative_verifier_returned_true": True,
            "full_completion_reconstruction_and_persisted_bytes_replayed": True,
            "authenticated_supervisor_binding_present": False,
        },
        "guardian_replay_contract": {
            "allowed_disposition": GUARDIAN_REPLAY_DISPOSITION,
            "structural_completion_replay_allowed": True,
            "persisted_eight_file_replay_allowed": True,
            "exact_retained_context_available_to_guardian": False,
            "e4_authoritative_verifier_call_allowed": False,
            "may_substitute_same_process_authority": False,
        },
        "in_supervisor_e4_authoritative_attestation_present": True,
        "guardian_persisted_eight_file_replay_present": True,
        **_locked_claims(),
    }


def _assert_exact_input_chain(
    *,
    context: e4_v1.H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1,
) -> dict[str, Any]:
    if type(context) is not e4_v1.H1E3BoundOutputContinuationContextV1:
        _fail("E5B-A requires the exact retained E4 context")
    if type(e3_completion) is not e3_v1.H1ExclusiveBrokerCompletionV1:
        _fail("E5B-A requires the exact E3 completion runtime type")
    if type(e4_completion) is not e4_v1.H1E3BoundOutputCompletionV1:
        _fail("E5B-A requires the exact E4 completion runtime type")
    context_document = context.to_document()
    if (
        context_document.get("preparer_pid") != os.getpid()
        or context_document.get("preparer_thread_id") != threading.get_ident()
    ):
        _fail("E5B-A authority crossed the E4 preparer process/thread")
    try:
        authoritative = e4_v1.verify_h1_e3_bound_output_completion_v1(
            completion=e4_completion,
            context=context,
            e3_completion=e3_completion,
        )
    except Exception as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A exact E4 authoritative replay failed"
        ) from error
    if authoritative is not True:
        _fail("E5B-A exact E4 authoritative verifier did not return true")
    completion_document = _e4_completion_document(e4_completion)
    e3_document = e3_completion.to_document()
    role_zero = completion_document["durable_role_documents"][0]
    source_identity = _source_identity()
    if (
        context.context_id
        != completion_document["h1_e3_bound_output_continuation_context_id"]
        or context_document.get("caller_binding_id") != role_zero["caller_binding_id"]
        or context_document.get("logical_occurrence_id") != role_zero["logical_occurrence_id"]
        or context_document.get("route_attempt_id") != role_zero["route_attempt_id"]
        or context_document.get("output_directory")
        != completion_document["writer_allocation"]["output_directory"]
        or e3_document.get("h1_exclusive_broker_completion_id")
        != completion_document["h1_exclusive_broker_completion_id"]
        or e3_document.get("session_nonce") != completion_document["e3_session_nonce"]
        or e3_document.get("prebound_output_continuation_context_id")
        != context.context_id
        or e3_document.get("authority_disposition") != "BROKER_EXCLUSIVE_PRESENT"
        or e3_document.get("h1_exclusive_broker_profile_id")
        != e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
        or e3_document.get("h1_exclusive_broker_source_manifest_id")
        != source_identity["h1_exclusive_broker_source_manifest_id"]
    ):
        _fail("E5B-A completion/context/E3/profile/source identity chain crossed")
    return completion_document


def issue_h1_e4_in_supervisor_authoritative_attestation_v1(
    *,
    context: e4_v1.H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1,
) -> H1E4InSupervisorAuthoritativeAttestationV1:
    """Call the E4 authority in its supervisor and bind the complete ID chain."""

    completion_document = _assert_exact_input_chain(
        context=context,
        e3_completion=e3_completion,
        e4_completion=e4_completion,
    )
    document = _with_id(
        _attestation_payload(completion_document),
        domain=(
            domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN
        ),
        id_field="h1_e4_in_supervisor_authoritative_attestation_id",
    )
    attestation = H1E4InSupervisorAuthoritativeAttestationV1(
        _ATTESTATION_ISSUER,
        canonical_json_bytes(document),
        os.getpid(),
        threading.get_ident(),
    )
    with _ISSUED_LOCK:
        _ISSUED_ATTESTATIONS[id(attestation)] = (
            attestation,
            attestation.canonical_bytes,
            os.getpid(),
            threading.get_ident(),
        )
    return attestation


def verify_h1_e4_in_supervisor_attestation_structure_v1(
    *,
    attestation: H1E4InSupervisorAuthoritativeAttestationV1 | dict[str, Any],
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1 | dict[str, Any],
) -> bool:
    """Replay IDs and all fields; this portable check is not E4 authority."""

    document = (
        attestation.to_document()
        if type(attestation) is H1E4InSupervisorAuthoritativeAttestationV1
        else attestation
    )
    payload = _verify_content_object(
        document,
        domain=(
            domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN
        ),
        id_field="h1_e4_in_supervisor_authoritative_attestation_id",
        label="E5B-A authoritative attestation",
    )
    completion_document = _e4_completion_document(e4_completion)
    expected = _attestation_payload(completion_document)
    if payload != expected:
        _fail("E5B-A attestation differs from the complete E4 identity reconstruction")
    return True


def verify_h1_e4_in_supervisor_authoritative_attestation_v1(
    *,
    attestation: H1E4InSupervisorAuthoritativeAttestationV1,
    context: e4_v1.H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1,
) -> bool:
    """Reperform the exact authority call and validate the issued process object."""

    if type(attestation) is not H1E4InSupervisorAuthoritativeAttestationV1:
        _fail("E5B-A authority verifier requires one exact issued attestation")
    with _ISSUED_LOCK:
        retained = _ISSUED_ATTESTATIONS.get(id(attestation))
    if (
        retained is None
        or retained[0] is not attestation
        or retained[1] != attestation.canonical_bytes
        or retained[2] != os.getpid()
        or retained[3] != threading.get_ident()
        or attestation._owner_pid != os.getpid()
        or attestation._owner_thread_id != threading.get_ident()
    ):
        _fail("E5B-A authoritative attestation is not exact in its issuing process/thread")
    completion_document = _assert_exact_input_chain(
        context=context,
        e3_completion=e3_completion,
        e4_completion=e4_completion,
    )
    expected = _with_id(
        _attestation_payload(completion_document),
        domain=(
            domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN
        ),
        id_field="h1_e4_in_supervisor_authoritative_attestation_id",
    )
    if attestation.to_document() != expected:
        _fail("E5B-A authoritative attestation changed after exact issuance")
    return True


def _close_definitively(descriptor: int) -> bool:
    try:
        os.close(descriptor)
        return True
    except OSError as error:
        try:
            os.fstat(descriptor)
        except OSError as probe:
            if probe.errno == errno.EBADF:
                return True
        return error.errno == errno.EBADF


def _directory_names(descriptor: int) -> tuple[str, ...]:
    try:
        names = os.listdir(descriptor)
    except (OSError, TypeError) as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian could not inventory the output directory"
        ) from error
    if any(type(name) is not str or name in {".", ".."} for name in names):
        _fail("E5B-A guardian observed a malformed output name")
    return tuple(sorted(names))


def _directory_fd_identity(descriptor: int) -> dict[str, Any]:
    try:
        row = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian lost one directory descriptor"
        ) from error
    return {
        "device": int(row.st_dev),
        "inode": int(row.st_ino),
        "mode": stat.S_IMODE(row.st_mode),
        "is_directory": stat.S_ISDIR(row.st_mode),
    }


def _directory_path_identity(
    path: str | os.PathLike[str],
    *,
    directory_fd: int | None = None,
) -> dict[str, Any]:
    try:
        row = os.stat(path, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian lost one bound directory name"
        ) from error
    return {
        "device": int(row.st_dev),
        "inode": int(row.st_ino),
        "mode": stat.S_IMODE(row.st_mode),
        "is_directory": stat.S_ISDIR(row.st_mode),
    }


def _file_identity(descriptor: int) -> dict[str, Any]:
    try:
        row = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian lost one output descriptor"
        ) from error
    return {
        "device": int(row.st_dev),
        "inode": int(row.st_ino),
        "mode": stat.S_IMODE(row.st_mode),
        "nlink": int(row.st_nlink),
        "byte_count": int(row.st_size),
        "is_regular": stat.S_ISREG(row.st_mode),
    }


def _path_identity(directory_fd: int, name: str) -> dict[str, Any]:
    try:
        row = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian lost one output name"
        ) from error
    return {
        "device": int(row.st_dev),
        "inode": int(row.st_ino),
        "mode": stat.S_IMODE(row.st_mode),
        "nlink": int(row.st_nlink),
        "byte_count": int(row.st_size),
        "is_regular": stat.S_ISREG(row.st_mode),
    }


def _pread_exact(descriptor: int, extent: int) -> bytes:
    if type(extent) is not int or not 0 <= extent <= e4_v1.MAX_ROLE_BYTES:
        _fail("E5B-A guardian output extent crossed the E4 cap")
    try:
        raw = os.pread(descriptor, extent + 1, 0)
    except OSError as error:
        raise ConstructionK7H1E4InSupervisorAttestationV1Error(
            "E5B-A guardian could not read one output file"
        ) from error
    if len(raw) != extent:
        _fail("E5B-A guardian output extent changed during replay")
    return raw


def _replay_persisted_eight_files(
    *,
    completion: Mapping[str, Any],
    output_directory: str | os.PathLike[str],
) -> dict[str, Any]:
    directory = Path(os.path.abspath(os.fspath(output_directory)))
    expected_directory = completion["writer_allocation"]["output_directory"]
    if directory.name != expected_directory["basename"]:
        _fail("E5B-A guardian crossed the bound output parent/name")
    parent_fd = os.open(
        directory.parent,
        os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
    )
    directory_fd = -1
    retained_file_descriptors: list[int] = []
    try:
        expected_parent_identity = {
            "device": expected_directory["parent_device"],
            "inode": expected_directory["parent_inode"],
            "mode": expected_directory["parent_mode"],
            "is_directory": True,
        }
        parent_identity = _directory_fd_identity(parent_fd)
        parent_path_identity = _directory_path_identity(directory.parent)
        if (
            parent_identity != expected_parent_identity
            or parent_path_identity != parent_identity
        ):
            _fail("E5B-A guardian crossed the bound output parent/name")
        directory_fd = os.open(
            directory.name,
            os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC | _O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        expected_child_identity = {
            "device": expected_directory["device"],
            "inode": expected_directory["inode"],
            "mode": expected_directory["mode"],
            "is_directory": True,
        }
        directory_identity = _directory_fd_identity(directory_fd)
        directory_name_identity = _directory_path_identity(
            directory.name, directory_fd=parent_fd
        )
        if (
            directory_identity != expected_child_identity
            or directory_name_identity != directory_identity
        ):
            _fail("E5B-A guardian crossed the bound output directory inode")
        if _directory_names(directory_fd) != tuple(
            sorted(e4_v1.ROLE_FILE_NAMES.values())
        ):
            _fail("E5B-A guardian found an omitted, extra or renamed output")
        rows = _output_identity_rows(completion)
        documents = completion["durable_role_documents"]
        seen: set[tuple[int, int]] = set()
        observed_total = 0
        for expected, role_document in zip(rows, documents):
            descriptor = os.open(
                expected["file_name"],
                os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            retained_file_descriptors.append(descriptor)
            before = _file_identity(descriptor)
            path_before = _path_identity(directory_fd, expected["file_name"])
            raw = _pread_exact(descriptor, before["byte_count"])
            after = _file_identity(descriptor)
            path_after = _path_identity(directory_fd, expected["file_name"])
            inode_key = (before["device"], before["inode"])
            expected_inode = {
                "device": expected["device"],
                "inode": expected["inode"],
                "mode": expected["mode"],
                "nlink": expected["nlink"],
                "byte_count": expected["byte_count"],
                "is_regular": True,
            }
            if (
                before != after
                or before != path_before
                or after != path_after
                or before != expected_inode
                or before["mode"] != 0o400
                or before["nlink"] != 1
                or inode_key in seen
                or raw != canonical_json_bytes(role_document)
                or _sha(raw) != expected["sha256"]
                or len(raw) != expected["byte_count"]
            ):
                _fail("E5B-A guardian found changed durable output bytes or identity")
            seen.add(inode_key)
            observed_total += len(raw)
        final_file_inventory = [
            _path_identity(directory_fd, expected["file_name"])
            for expected in rows
        ]
        final_retained_inventory = [
            _file_identity(descriptor) for descriptor in retained_file_descriptors
        ]
        after_directory = _directory_fd_identity(directory_fd)
        final_directory_name_identity = _directory_path_identity(
            directory.name, directory_fd=parent_fd
        )
        final_parent_identity = _directory_fd_identity(parent_fd)
        final_parent_path_identity = _directory_path_identity(directory.parent)
        expected_file_inventory = [
            {
                "device": expected["device"],
                "inode": expected["inode"],
                "mode": expected["mode"],
                "nlink": expected["nlink"],
                "byte_count": expected["byte_count"],
                "is_regular": True,
            }
            for expected in rows
        ]
        if (
            after_directory != directory_identity
            or final_directory_name_identity != directory_identity
            or final_parent_identity != parent_identity
            or final_parent_path_identity != parent_identity
            or final_file_inventory != expected_file_inventory
            or final_retained_inventory != expected_file_inventory
            or _directory_names(directory_fd)
            != tuple(sorted(e4_v1.ROLE_FILE_NAMES.values()))
        ):
            _fail("E5B-A guardian output directory changed during replay")
        return {
            "output_directory_identity": directory_identity,
            "persisted_role_count": len(rows),
            "persisted_output_bytes": observed_total,
            "eight_distinct_output_inodes": len(seen) == len(e4_v1.ROLE_ORDER),
        }
    finally:
        close_failed = False
        for descriptor in reversed(retained_file_descriptors):
            close_failed = not _close_definitively(descriptor) or close_failed
        if directory_fd >= 0:
            close_failed = not _close_definitively(directory_fd) or close_failed
        close_failed = not _close_definitively(parent_fd) or close_failed
        if close_failed:
            _fail("E5B-A guardian could not close its retained replay descriptors")


def replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
    *,
    attestation: H1E4InSupervisorAuthoritativeAttestationV1 | dict[str, Any],
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1 | dict[str, Any],
    output_directory: str | os.PathLike[str],
) -> H1E4GuardianPersistedReplayV1:
    """Perform only the portable structural and eight-file guardian replay."""

    completion_document = _e4_completion_document(e4_completion)
    verify_h1_e4_in_supervisor_attestation_structure_v1(
        attestation=attestation,
        e4_completion=completion_document,
    )
    attestation_document = (
        attestation.to_document()
        if type(attestation) is H1E4InSupervisorAuthoritativeAttestationV1
        else attestation
    )
    replay = _replay_persisted_eight_files(
        completion=completion_document,
        output_directory=output_directory,
    )
    payload = {
        "schema": "acfqp.k7_h1_e4_guardian_persisted_replay.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_e4_in_supervisor_attestation_profile_id": _PROFILE.profile_id,
        "h1_e4_in_supervisor_authoritative_attestation_id": attestation_document[
            "h1_e4_in_supervisor_authoritative_attestation_id"
        ],
        "h1_e3_bound_output_completion_id": completion_document[
            "h1_e3_bound_output_completion_id"
        ],
        "guardian_replay_disposition": GUARDIAN_REPLAY_DISPOSITION,
        "attestation_structure_replayed": True,
        "e4_completion_structure_replayed": True,
        "persisted_eight_file_replay_complete": True,
        **replay,
        "same_process_e4_authoritative_verifier_invoked": False,
        "exact_retained_context_available": False,
        "same_process_authority_reperformed": False,
        "same_process_authority_inferred": False,
        "may_substitute_same_process_authority": False,
        "readiness": READINESS,
        **_locked_claims(),
    }
    document = _with_id(
        payload,
        domain=domains_v13.CONSTRUCTION_K7_H1_E4_GUARDIAN_PERSISTED_REPLAY_V1_DOMAIN,
        id_field="h1_e4_guardian_persisted_replay_id",
    )
    return H1E4GuardianPersistedReplayV1(
        _GUARDIAN_REPLAY_ISSUER, canonical_json_bytes(document)
    )


if not domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
    domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
) or not domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
    domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
) or not domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
    domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12
):  # pragma: no cover - import-time invariant
    raise RuntimeError("E5B-A V13 domains crossed an earlier additive registry")


__all__ = (
    "AUTHORITY_DISPOSITION",
    "COUNTER_COMPLETENESS_GATE",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "ConstructionK7H1E4InSupervisorAttestationV1Error",
    "E5B_INTEGRATED_ROUTE_EXECUTION_PRESENT",
    "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "FQ11_COUNTER_COMPLETENESS_PRESENT",
    "GUARDIAN_PERSISTED_EIGHT_FILE_REPLAY_PRESENT",
    "GUARDIAN_REPLAY_DISPOSITION",
    "GUARDIAN_REPLAY_SUBSTITUTES_SAME_PROCESS_AUTHORITY",
    "H1E4GuardianPersistedReplayV1",
    "H1E4InSupervisorAttestationProfileV1",
    "H1E4InSupervisorAuthoritativeAttestationV1",
    "IN_SUPERVISOR_E4_AUTHORITATIVE_ATTESTATION_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PEAK_SCOPE_STATUS",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "ROUTE_WIDE_ACTUAL_PEAK_AUTHORITY_PRESENT",
    "ROUTE_WIDE_PEAK_AUTHORITY_PRESENT",
    "SCHEMA_VERSION",
    "WORKLOAD_ECONOMICS_GATE",
    "issue_h1_e4_in_supervisor_authoritative_attestation_v1",
    "official_h1_e4_in_supervisor_attestation_profile_v1",
    "replay_h1_e4_attestation_and_persisted_files_for_guardian_v1",
    "verify_h1_e4_in_supervisor_attestation_structure_v1",
    "verify_h1_e4_in_supervisor_authoritative_attestation_v1",
)
