"""Strong-authority completion of the frozen K7 V1 reconciliation DAG.

V1 remains byte-for-byte historical: it proves process and solver families
and retains a typed blocker for the route family.  This successor consumes a
fresh replay of the production occurrence/cutoff semantic authority, derives
the exact route outcome ``1 / 0 / 1``, and joins those three new proofs to the
five unchanged V1 proofs.  It issues no CounterRecord or vector.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_k7_derived_reconciliation_v1 as v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_COMPLETE_DERIVED_RECONCILIATION_READINESS_V2_DOMAIN,
    CONSTRUCTION_K7_EXACT_ROUTE_DERIVED_PATH_PROOF_V2_DOMAIN,
    CONSTRUCTION_K7_ROUTE_TERMINAL_SEMANTIC_DEPENDENCY_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.26"
PROFILE_KEY = "construction_k7_derived_reconciliation_v2"

ROUTE_DEPENDENCY_V2_DOMAIN = (
    CONSTRUCTION_K7_ROUTE_TERMINAL_SEMANTIC_DEPENDENCY_V2_DOMAIN
)
ROUTE_PATH_PROOF_V2_DOMAIN = CONSTRUCTION_K7_EXACT_ROUTE_DERIVED_PATH_PROOF_V2_DOMAIN
COMPLETE_READINESS_V2_DOMAIN = (
    CONSTRUCTION_K7_COMPLETE_DERIVED_RECONCILIATION_READINESS_V2_DOMAIN
)
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    ROUTE_DEPENDENCY_V2_DOMAIN,
    ROUTE_PATH_PROOF_V2_DOMAIN,
    COMPLETE_READINESS_V2_DOMAIN,
)
if not set(REQUESTED_PHASE3E_DOMAIN_TAGS).issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 V2 reconciliation domains must be centrally registered")

ROUTE_PATHS = (
    "route.attempts",
    "route.failures",
    "route.successes",
)
V1_BASE_PATHS = tuple(path for path in v1.DERIVED_PATHS if path not in ROUTE_PATHS)
ROUTE_AUTHORITY_REPLAY_INPUT_KEYS = (
    "cutoff_attestation",
    "evidence_closure",
    "identity_join",
    "operational_output_bytes",
    "output_bundle",
    "owned_result",
    "owner_event_candidates",
    "receipt_set",
    "request_replay",
    "role_manifest",
    "runtime_envelope",
    "source_envelope",
    "verified_envelope",
)

ROUTE_BOUND_FACT_KEYS = tuple(
    sorted(
        (
            "authority_bundle_id",
            "boundary_profile_id",
            "charged_output_bytes",
            "counter_registry_id",
            "decision_point_id",
            "execution_profile_id",
            "logical_occurrence_id",
            "measurement_cutoff_marker_id",
            "measurement_start_marker_id",
            "measurement_window_id",
            "occurrence_authority_id",
            "operational_cutoff_authority_id",
            "operational_output_sha256",
            "ordered_chain_node_count",
            "owned_partial_result_id",
            "owner_event_candidate_set_id",
            "owner_event_execution_binding_id",
            "partial_native_terminal_id",
            "partial_native_transcript_id",
            "portable_request_replay_id",
            "production_role_manifest_id",
            "production_runtime_envelope_id",
            "route_attempt_count",
            "route_attempt_id",
            "route_attempt_outcome",
            "route_failure_count",
            "route_identity_id",
            "route_success_count",
            "runtime_business_result_byte_count",
            "runtime_business_result_id",
            "runtime_business_result_sha256",
            "schedule_id",
            "scientific_occurrence_id",
            "source_archive_byte_count",
            "source_archive_sha256",
            "source_snapshot_id",
            "source_v3_envelope_id",
            "stage_profile_id",
            "structural_cutoff_attestation_id",
            "structural_identity_join_id",
            "terminal_closure_observation_id",
            "terminal_kind",
            "terminal_status",
            "transcript_document_sha256",
            "verified_nine_envelope_id",
        )
    )
)

_ROUTE_DEPENDENCY_ISSUER = object()
_ROUTE_PROOF_ISSUER = object()
_READINESS_ISSUER = object()


class ConstructionK7DerivedReconciliationV2Error(ValueError):
    """A strong route authority or complete eight-path join is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DerivedReconciliationV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DerivedReconciliationV2Error(
            f"{label} must be one exact content ID"
        ) from error


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("V2 reconciliation used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _exact_facts(
    rows: Any,
) -> tuple[tuple[str, str | int], ...]:
    if type(rows) is not tuple:
        _fail("route bound facts must be one exact tuple")
    keys: list[str] = []
    for row in rows:
        if type(row) is not tuple or len(row) != 2:
            _fail("route bound facts contain one malformed row")
        key, value = row
        if type(key) is not str or not key:
            _fail("route bound facts contain one invalid key")
        if not (
            (type(value) is int and value >= 0)
            or (type(value) is str and bool(value))
        ):
            _fail("route bound facts contain one invalid value")
        keys.append(key)
    if len(set(keys)) != len(keys):
        _fail("route bound facts contain a duplicate key")
    if tuple(sorted(keys)) != tuple(keys) or tuple(keys) != ROUTE_BOUND_FACT_KEYS:
        _fail("route bound facts are missing, extra, or noncanonical")
    return rows


@dataclass(frozen=True, slots=True)
class K7RouteTerminalSemanticDependencyV2:
    """Exact route facts issued only after full occurrence-authority replay."""

    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    logical_occurrence_id: str
    verified_nine_envelope_id: str
    authority_bundle_id: str
    bound_facts: tuple[tuple[str, str | int], ...]
    exact_values: tuple[tuple[str, int], ...]
    semantic_checks: tuple[str, ...]
    _dependency_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.counter_registry_id, "route dependency registry"),
            (self.stage_profile_id, "route dependency stage profile"),
            (self.logical_occurrence_id, "route dependency occurrence"),
            (self.verified_nine_envelope_id, "route dependency verified-nine"),
            (self.authority_bundle_id, "route dependency authority bundle"),
        ):
            _cid(value, label)
        if (
            _issuer is not _ROUTE_DEPENDENCY_ISSUER
            or _exact_facts(self.bound_facts) != self.bound_facts
            or self.exact_values
            != (
                ("root_terminal.route_failures", 1),
                ("root_terminal.route_successes", 0),
            )
            or type(self.semantic_checks) is not tuple
            or tuple(sorted(self.semantic_checks)) != self.semantic_checks
            or len(set(self.semantic_checks)) != len(self.semantic_checks)
            or not self.semantic_checks
        ):
            _fail("route semantic dependency is caller-minted or incomplete")
        facts = dict(self.bound_facts)
        for key in (
            "authority_bundle_id",
            "boundary_profile_id",
            "counter_registry_id",
            "decision_point_id",
            "execution_profile_id",
            "logical_occurrence_id",
            "measurement_cutoff_marker_id",
            "measurement_start_marker_id",
            "measurement_window_id",
            "occurrence_authority_id",
            "operational_cutoff_authority_id",
            "owned_partial_result_id",
            "owner_event_candidate_set_id",
            "owner_event_execution_binding_id",
            "partial_native_terminal_id",
            "partial_native_transcript_id",
            "portable_request_replay_id",
            "production_role_manifest_id",
            "production_runtime_envelope_id",
            "route_attempt_id",
            "route_identity_id",
            "runtime_business_result_id",
            "schedule_id",
            "scientific_occurrence_id",
            "source_snapshot_id",
            "source_v3_envelope_id",
            "stage_profile_id",
            "structural_cutoff_attestation_id",
            "structural_identity_join_id",
            "terminal_closure_observation_id",
            "verified_nine_envelope_id",
        ):
            _cid(facts[key], f"route bound fact {key}")
        for key in (
            "operational_output_sha256",
            "runtime_business_result_sha256",
            "source_archive_sha256",
            "transcript_document_sha256",
        ):
            _sha256(facts[key], f"route bound fact {key}")
        for key in (
            "charged_output_bytes",
            "ordered_chain_node_count",
            "route_attempt_count",
            "route_failure_count",
            "route_success_count",
            "runtime_business_result_byte_count",
            "source_archive_byte_count",
        ):
            _nonnegative(facts[key], f"route bound fact {key}")
        if (
            facts["counter_registry_id"] != self.counter_registry_id
            or facts["stage_profile_id"] != self.stage_profile_id
            or facts["logical_occurrence_id"] != self.logical_occurrence_id
            or facts["verified_nine_envelope_id"]
            != self.verified_nine_envelope_id
            or facts["authority_bundle_id"] != self.authority_bundle_id
            or facts["terminal_status"] != "CHILD_ACTION_ROW_CAP_EXCEEDED"
            or facts["terminal_kind"] != "COMPLETED"
            or facts["route_attempt_outcome"] != "FAILURE"
            or facts["route_attempt_count"] != 1
            or facts["route_success_count"] != 0
            or facts["route_failure_count"] != 1
            or facts["route_attempt_count"]
            != facts["route_success_count"] + facts["route_failure_count"]
            or facts["runtime_business_result_byte_count"] <= 0
            or facts["source_archive_byte_count"] <= 0
            or facts["ordered_chain_node_count"] <= 0
        ):
            _fail("route bound facts differ from the exact replayed 1/0/1 outcome")
        object.__setattr__(
            self,
            "_dependency_id",
            _local_id(ROUTE_DEPENDENCY_V2_DOMAIN, self._payload()),
        )

    @property
    def by_fact(self) -> dict[str, str | int]:
        return dict(self.bound_facts)

    @property
    def by_external_key(self) -> dict[str, int]:
        return dict(self.exact_values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_route_terminal_semantic_dependency.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "occurrence_cutoff_semantic_authority_bundle_id": (
                self.authority_bundle_id
            ),
            "bound_facts": [
                {"key": key, "value": value}
                for key, value in self.bound_facts
            ],
            "exact_values": [
                {"key": key, "value": value}
                for key, value in self.exact_values
            ],
            "semantic_checks": list(self.semantic_checks),
            "occurrence_authority_fresh_replay_complete": True,
            "actual_business_result_bytes_publicly_replayed": True,
            "status_only_evidence_rejected": True,
            "counter_records_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def dependency_id(self) -> str:
        current = _local_id(ROUTE_DEPENDENCY_V2_DOMAIN, self._payload())
        if current != self._dependency_id:
            _fail("route semantic dependency changed after issuance")
        return self._dependency_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_semantic_dependency_id": self.dependency_id}


def derive_route_terminal_semantic_dependency_v2(
    *,
    verified_nine: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    authority_bundle: occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2,
    replay_inputs: Mapping[str, Any],
) -> K7RouteTerminalSemanticDependencyV2:
    """Freshly replay the strong authority and bind it to verified-nine."""

    if type(verified_nine) is not verified_v1.K7VerifiedNineSharedResourceEnvelopeV1:
        _fail("route dependency requires one exact verified-nine envelope")
    try:
        verified_nine._assert_current()  # noqa: SLF001 - predecessor replay
    except Exception as error:
        raise ConstructionK7DerivedReconciliationV2Error(
            "verified-nine predecessor failed replay"
        ) from error
    if type(authority_bundle) is not (
        occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2
    ):
        _fail("route dependency requires one exact occurrence/cutoff authority")
    if (
        type(replay_inputs) is not dict
        or tuple(sorted(replay_inputs)) != ROUTE_AUTHORITY_REPLAY_INPUT_KEYS
    ):
        _fail("route authority requires its exact independent replay input set")
    try:
        replayed = (
            occurrence_v2.replay_k7_occurrence_cutoff_semantic_authorities_v2(
                authority_bundle,
                **replay_inputs,
            )
        )
        occurrence = replayed.occurrence_authority
        cutoff = replayed.cutoff_authority
        authority_id = replayed.bundle_id
        occurrence_id = occurrence.authority_id
        cutoff_id = cutoff.authority_id
    except Exception as error:
        raise ConstructionK7DerivedReconciliationV2Error(
            "route authority independent replay failed"
        ) from error
    source = verified_nine.source_envelope
    if (
        replayed.to_document() != authority_bundle.to_document()
        or occurrence.counter_registry_id != source.counter_registry_id
        or occurrence.stage_profile_id != source.stage_profile_id
        or occurrence.logical_occurrence_id != source.occurrence_id
        or occurrence.production_runtime_envelope_id
        != source.production_runtime_envelope_id
        or occurrence.source_v3_envelope_id != source.envelope_id
        or occurrence.verified_nine_source_envelope_id
        != verified_nine.verified_envelope_id
        or occurrence.portable_request_replay_id
        != source.production_runtime_replay_id
        or occurrence.route_attempt_id != source.route_attempt_id
        or occurrence.decision_point_id != source.decision_point_id
        or occurrence.measurement_window_id != source.measurement_window_id
        or occurrence.terminal_closure_observation_id
        != source.terminal_closure_observation_id
        or cutoff.occurrence_authority_id != occurrence_id
        or cutoff.measurement_window_id != source.measurement_window_id
        or cutoff.terminal_closure_observation_id
        != source.terminal_closure_observation_id
        or occurrence.route_attempt_count != 1
        or occurrence.route_success_count != 0
        or occurrence.route_failure_count != 1
    ):
        _fail("route authority crossed its verified-nine execution context")
    facts: tuple[tuple[str, str | int], ...] = tuple(
        sorted(
            (
                ("authority_bundle_id", authority_id),
                ("boundary_profile_id", occurrence.boundary_profile_id),
                ("charged_output_bytes", cutoff.charged_output_bytes),
                ("counter_registry_id", occurrence.counter_registry_id),
                ("decision_point_id", occurrence.decision_point_id),
                ("execution_profile_id", occurrence.execution_profile_id),
                ("logical_occurrence_id", occurrence.logical_occurrence_id),
                ("measurement_cutoff_marker_id", cutoff.measurement_cutoff_marker_id),
                ("measurement_start_marker_id", cutoff.measurement_start_marker_id),
                ("measurement_window_id", occurrence.measurement_window_id),
                ("occurrence_authority_id", occurrence_id),
                ("operational_cutoff_authority_id", cutoff_id),
                ("operational_output_sha256", occurrence.operational_output_sha256),
                ("ordered_chain_node_count", len(occurrence.ordered_chain_node_ids)),
                ("owned_partial_result_id", occurrence.owned_partial_result_id),
                ("owner_event_candidate_set_id", occurrence.owner_event_candidate_set_id),
                ("owner_event_execution_binding_id", occurrence.owner_event_execution_binding_id),
                ("partial_native_terminal_id", occurrence.transcript_terminal_id),
                ("partial_native_transcript_id", occurrence.partial_native_transcript_id),
                ("portable_request_replay_id", occurrence.portable_request_replay_id),
                ("production_role_manifest_id", occurrence.production_role_manifest_id),
                ("production_runtime_envelope_id", occurrence.production_runtime_envelope_id),
                ("route_attempt_count", occurrence.route_attempt_count),
                ("route_attempt_id", occurrence.route_attempt_id),
                ("route_attempt_outcome", occurrence.route_attempt_outcome),
                ("route_failure_count", occurrence.route_failure_count),
                ("route_identity_id", occurrence.route_identity_id),
                ("route_success_count", occurrence.route_success_count),
                ("runtime_business_result_byte_count", occurrence.runtime_business_result_byte_count),
                ("runtime_business_result_id", occurrence.runtime_business_result_id),
                ("runtime_business_result_sha256", occurrence.runtime_business_result_sha256),
                ("schedule_id", occurrence.schedule_id),
                ("scientific_occurrence_id", occurrence.scientific_occurrence_id),
                ("source_archive_byte_count", occurrence.source_archive_byte_count),
                ("source_archive_sha256", occurrence.source_archive_sha256),
                ("source_snapshot_id", occurrence.source_snapshot_id),
                ("source_v3_envelope_id", occurrence.source_v3_envelope_id),
                ("stage_profile_id", occurrence.stage_profile_id),
                ("structural_cutoff_attestation_id", cutoff.structural_cutoff_attestation_id),
                ("structural_identity_join_id", occurrence.structural_identity_join_id),
                ("terminal_closure_observation_id", occurrence.terminal_closure_observation_id),
                ("terminal_kind", occurrence.terminal_kind),
                ("terminal_status", occurrence.terminal_status),
                ("transcript_document_sha256", occurrence.transcript_document_sha256),
                ("verified_nine_envelope_id", verified_nine.verified_envelope_id),
            )
        )
    )
    return K7RouteTerminalSemanticDependencyV2(
        _ROUTE_DEPENDENCY_ISSUER,
        occurrence.counter_registry_id,
        occurrence.stage_profile_id,
        occurrence.logical_occurrence_id,
        verified_nine.verified_envelope_id,
        authority_id,
        facts,
        (
            ("root_terminal.route_failures", occurrence.route_failure_count),
            ("root_terminal.route_successes", occurrence.route_success_count),
        ),
        tuple(
            sorted(
                (
                    "full_owner_transcript_chain_replayed",
                    "occurrence_cutoff_authority_independently_replayed",
                    "route_counts_explicit_and_conserved",
                    "runtime_business_result_actual_bytes_publicly_replayed",
                    "runtime_business_result_id_sha_extent_bound",
                    "status_only_evidence_rejected",
                )
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class K7ExactRouteDerivedPathProofV2:
    _issuer: InitVar[object]
    path: str
    value: int
    formula_id: str
    route_dependency_id: str | None
    derived_dependency_proof_ids: tuple[str, ...]
    verified_nine_envelope_id: str
    production_runtime_envelope_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    terminal_closure_observation_id: str
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.formula_id, "route formula"),
            (self.verified_nine_envelope_id, "route proof verified-nine"),
            (self.production_runtime_envelope_id, "route proof runtime"),
            (self.logical_occurrence_id, "route proof occurrence"),
            (self.route_attempt_id, "route proof attempt"),
            (self.decision_point_id, "route proof decision"),
            (self.measurement_window_id, "route proof window"),
            (self.terminal_closure_observation_id, "route proof terminal closure"),
            *((value, "route proof dependency") for value in self.derived_dependency_proof_ids),
        ):
            _cid(value, label)
        if self.route_dependency_id is not None:
            _cid(self.route_dependency_id, "route proof semantic dependency")
        _nonnegative(self.value, "route proof value")
        formula = {
            row.path: row for row in v1.official_k7_reconciliation_formulas_v1()
        }.get(self.path)
        if (
            _issuer is not _ROUTE_PROOF_ISSUER
            or self.path not in ROUTE_PATHS
            or formula is None
            or self.formula_id != formula.formula_id
            or type(self.derived_dependency_proof_ids) is not tuple
            or len(set(self.derived_dependency_proof_ids))
            != len(self.derived_dependency_proof_ids)
        ):
            _fail("route path proof is caller-minted or crossed")
        if self.path == "route.attempts":
            if (
                self.route_dependency_id is not None
                or len(self.derived_dependency_proof_ids) != 2
            ):
                _fail("route attempt proof lacks its two outcome proofs")
        elif (
            self.route_dependency_id is None
            or self.derived_dependency_proof_ids
        ):
            _fail("route outcome proof lacks its exact semantic dependency")
        object.__setattr__(
            self,
            "_proof_id",
            _local_id(ROUTE_PATH_PROOF_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_exact_route_path_proof.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "value": self.value,
            "formula_id": self.formula_id,
            "route_semantic_dependency_id": self.route_dependency_id,
            "derived_dependency_proof_ids": list(
                self.derived_dependency_proof_ids
            ),
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "terminal_closure_observation_id": self.terminal_closure_observation_id,
            "counter_record_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def proof_id(self) -> str:
        current = _local_id(ROUTE_PATH_PROOF_V2_DOMAIN, self._payload())
        if current != self._proof_id:
            _fail("route path proof changed after issuance")
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_path_proof_id": self.proof_id}


def _route_proofs_v2(
    *,
    verified_nine: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    dependency: K7RouteTerminalSemanticDependencyV2,
) -> tuple[K7ExactRouteDerivedPathProofV2, ...]:
    formulas = {
        row.path: row for row in v1.official_k7_reconciliation_formulas_v1()
    }
    source = verified_nine.source_envelope
    common = (
        verified_nine.verified_envelope_id,
        source.production_runtime_envelope_id,
        source.occurrence_id,
        source.route_attempt_id,
        source.decision_point_id,
        source.measurement_window_id,
        source.terminal_closure_observation_id,
    )
    failures = K7ExactRouteDerivedPathProofV2(
        _ROUTE_PROOF_ISSUER,
        "route.failures",
        dependency.by_external_key["root_terminal.route_failures"],
        formulas["route.failures"].formula_id,
        dependency.dependency_id,
        (),
        *common,
    )
    successes = K7ExactRouteDerivedPathProofV2(
        _ROUTE_PROOF_ISSUER,
        "route.successes",
        dependency.by_external_key["root_terminal.route_successes"],
        formulas["route.successes"].formula_id,
        dependency.dependency_id,
        (),
        *common,
    )
    attempts = K7ExactRouteDerivedPathProofV2(
        _ROUTE_PROOF_ISSUER,
        "route.attempts",
        failures.value + successes.value,
        formulas["route.attempts"].formula_id,
        None,
        (failures.proof_id, successes.proof_id),
        *common,
    )
    return attempts, failures, successes


@dataclass(frozen=True, slots=True)
class K7ExactProofRowV2:
    """Stable public bridge from mixed V1/V2 proofs to semantic closure."""

    path: str
    value: int
    proof_id: str
    formula_id: str
    closure_dependency_paths: tuple[str, ...]
    proof_version: str

    def __post_init__(self) -> None:
        _nonnegative(self.value, "proof-row value")
        _cid(self.proof_id, "proof-row proof")
        _cid(self.formula_id, "proof-row formula")
        formula = {
            row.path: row for row in v1.official_k7_reconciliation_formulas_v1()
        }.get(self.path)
        if (
            self.path not in v1.DERIVED_PATHS
            or formula is None
            or self.formula_id != formula.formula_id
            or self.closure_dependency_paths != formula.closure_dependency_paths
            or self.proof_version not in {"V1", "V2_ROUTE"}
            or (self.path in ROUTE_PATHS) != (self.proof_version == "V2_ROUTE")
        ):
            _fail("public proof row differs from its exact formula/proof version")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "value": self.value,
            "proof_id": self.proof_id,
            "formula_id": self.formula_id,
            "closure_dependency_paths": list(self.closure_dependency_paths),
            "proof_version": self.proof_version,
        }


@dataclass(frozen=True, slots=True)
class K7CompleteDerivedReconciliationReadinessV2:
    """All eight paths, with five frozen V1 and three strong-route V2 proofs."""

    _issuer: InitVar[object]
    base_v1_readiness: v1.K7DerivedReconciliationReadinessV1 = field(repr=False)
    process_dependency_v1: v1.K7ExactReconciliationSemanticDependencyV1 = field(
        repr=False
    )
    solver_dependency_v1: v1.K7ExactReconciliationSemanticDependencyV1 = field(
        repr=False
    )
    route_dependency_v2: K7RouteTerminalSemanticDependencyV2 = field(repr=False)
    route_proofs_v2: tuple[K7ExactRouteDerivedPathProofV2, ...] = field(
        repr=False
    )
    exact_values: tuple[tuple[str, int], ...]
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _READINESS_ISSUER
            or type(self.base_v1_readiness)
            is not v1.K7DerivedReconciliationReadinessV1
            or type(self.process_dependency_v1)
            is not v1.K7ExactReconciliationSemanticDependencyV1
            or type(self.solver_dependency_v1)
            is not v1.K7ExactReconciliationSemanticDependencyV1
            or type(self.route_dependency_v2)
            is not K7RouteTerminalSemanticDependencyV2
            or type(self.route_proofs_v2) is not tuple
            or tuple(row.path for row in self.route_proofs_v2) != ROUTE_PATHS
            or any(
                type(row) is not K7ExactRouteDerivedPathProofV2
                for row in self.route_proofs_v2
            )
            or tuple(path for path, _value in self.exact_values)
            != v1.DERIVED_PATHS
            or any(type(value) is not int or value < 0 for _path, value in self.exact_values)
        ):
            _fail("complete reconciliation readiness is caller-minted or malformed")
        base = self.base_v1_readiness
        if (
            base.status is not v1.ReconciliationReadinessStatusV1.INCOMPLETE_TYPED
            or base.resolved_paths != V1_BASE_PATHS
            or base.unresolved_paths != ROUTE_PATHS
            or tuple(row.code for row in base.blockers)
            != (
                v1.ReconciliationBlockerCodeV1
                .ROUTE_TERMINAL_SEMANTIC_AUTHORITY_UNAVAILABLE,
            )
            or base.verified_nine_envelope_id
            != self.route_dependency_v2.verified_nine_envelope_id
            or self.process_dependency_v1.kind
            is not v1.SemanticDependencyKindV1.PROCESS_DIRECT_PIDFD_REAPS
            or self.solver_dependency_v1.kind
            is not v1.SemanticDependencyKindV1.ROOT_CAP_STAGE_EXCLUSION
        ):
            _fail("V1 base readiness is not its exact five-path predecessor")
        dependencies = (self.process_dependency_v1, self.solver_dependency_v1)
        if any(
            row.counter_registry_id != self.route_dependency_v2.counter_registry_id
            or row.stage_profile_id != self.route_dependency_v2.stage_profile_id
            or row.occurrence_id != self.route_dependency_v2.logical_occurrence_id
            for row in dependencies
        ):
            _fail("V1 and V2 semantic dependencies crossed occurrence context")
        base_by_path = {row.path: row for row in base.proofs}
        process_id = self.process_dependency_v1.dependency_id
        solver_id = self.solver_dependency_v1.dependency_id
        for path in ("process.exit_failures", "process.exit_successes"):
            if base_by_path[path].semantic_dependency_ids != (process_id,):
                _fail("V1 process proof crossed its semantic dependency")
        for path in ("solver.failures", "solver.successes"):
            if base_by_path[path].semantic_dependency_ids != (solver_id,):
                _fail("V1 solver proof crossed its semantic dependency")
        if base_by_path["solver.attempts"].derived_dependency_proof_ids != (
            base_by_path["solver.failures"].proof_id,
            base_by_path["solver.successes"].proof_id,
        ):
            _fail("V1 solver total proof crossed its outcome proofs")
        route_by_path = {row.path: row for row in self.route_proofs_v2}
        dependency_id = self.route_dependency_v2.dependency_id
        if (
            route_by_path["route.failures"].route_dependency_id != dependency_id
            or route_by_path["route.successes"].route_dependency_id != dependency_id
            or route_by_path["route.failures"].value
            != self.route_dependency_v2.by_external_key[
                "root_terminal.route_failures"
            ]
            or route_by_path["route.successes"].value
            != self.route_dependency_v2.by_external_key[
                "root_terminal.route_successes"
            ]
            or route_by_path["route.attempts"].derived_dependency_proof_ids
            != (
                route_by_path["route.failures"].proof_id,
                route_by_path["route.successes"].proof_id,
            )
            or route_by_path["route.attempts"].value
            != route_by_path["route.failures"].value
            + route_by_path["route.successes"].value
        ):
            _fail("V2 route proof DAG is incomplete or crossed")
        combined = {
            **{row.path: row.value for row in base.proofs},
            **{row.path: row.value for row in self.route_proofs_v2},
        }
        if dict(self.exact_values) != combined or combined != {
            "process.exit_failures": 0,
            "process.exit_successes": 2,
            "route.attempts": 1,
            "route.failures": 1,
            "route.successes": 0,
            "solver.attempts": 0,
            "solver.failures": 0,
            "solver.successes": 0,
        }:
            _fail("complete reconciliation values differ from exact K7 evidence")
        object.__setattr__(
            self,
            "_readiness_id",
            _local_id(COMPLETE_READINESS_V2_DOMAIN, self._payload()),
        )

    @property
    def proof_rows(self) -> tuple[K7ExactProofRowV2, ...]:
        """Eight ordered exact rows; no private predecessor API is required."""

        base = {row.path: row for row in self.base_v1_readiness.proofs}
        route = {row.path: row for row in self.route_proofs_v2}
        formulas = {
            row.path: row for row in v1.official_k7_reconciliation_formulas_v1()
        }
        rows: list[K7ExactProofRowV2] = []
        for path in v1.DERIVED_PATHS:
            proof = route[path] if path in route else base[path]
            rows.append(
                K7ExactProofRowV2(
                    path,
                    proof.value,
                    proof.proof_id,
                    formulas[path].formula_id,
                    formulas[path].closure_dependency_paths,
                    "V2_ROUTE" if path in route else "V1",
                )
            )
        return tuple(rows)

    @property
    def exact_proofs_by_path(self) -> dict[str, K7ExactProofRowV2]:
        """Fresh mapping view; mutating it cannot alter the readiness artifact."""

        return {row.path: row for row in self.proof_rows}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_complete_derived_reconciliation_readiness.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "formula_ids_v1": [
                row.formula_id
                for row in v1.official_k7_reconciliation_formulas_v1()
            ],
            "base_v1_readiness": self.base_v1_readiness.to_document(),
            "process_dependency_v1": self.process_dependency_v1.to_document(),
            "solver_dependency_v1": self.solver_dependency_v1.to_document(),
            "route_dependency_v2": self.route_dependency_v2.to_document(),
            "route_proofs_v2": [
                row.to_document() for row in self.route_proofs_v2
            ],
            "proof_rows": [row.to_document() for row in self.proof_rows],
            "exact_values": [
                {"path": path, "value": value}
                for path, value in self.exact_values
            ],
            "resolved_paths": list(v1.DERIVED_PATHS),
            "unresolved_paths": [],
            "all_eight_exact": True,
            "counter_record_materialization_eligible": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "v1_payloads_or_ids_changed": False,
        }

    @property
    def readiness_id(self) -> str:
        current = _local_id(COMPLETE_READINESS_V2_DOMAIN, self._payload())
        if current != self._readiness_id:
            _fail("complete reconciliation readiness changed after issuance")
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "complete_derived_reconciliation_readiness_id": self.readiness_id,
        }


def derive_k7_complete_eight_path_reconciliation_v2(
    *,
    verified_nine: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    authority_bundle: occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2,
    route_replay_inputs: Mapping[str, Any],
    owner_transcript: partial_v1.PartialNativeOccurrenceTranscriptV1 | None = None,
) -> K7CompleteDerivedReconciliationReadinessV2:
    route_dependency = derive_route_terminal_semantic_dependency_v2(
        verified_nine=verified_nine,
        authority_bundle=authority_bundle,
        replay_inputs=route_replay_inputs,
    )
    replay_owned = route_replay_inputs.get("owned_result")
    replay_transcript = getattr(replay_owned, "transcript", None)
    if type(replay_transcript) is not partial_v1.PartialNativeOccurrenceTranscriptV1:
        _fail("replayed route authority lacks its exact owner transcript")
    if owner_transcript is None:
        owner_transcript = replay_transcript
    elif (
        type(owner_transcript) is not partial_v1.PartialNativeOccurrenceTranscriptV1
        or owner_transcript.transcript_id != replay_transcript.transcript_id
        or owner_transcript.to_document() != replay_transcript.to_document()
    ):
        _fail("solver transcript was transplanted across route authority")
    base = v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=verified_nine,
        owner_transcript=owner_transcript,
    )
    process_dependency = v1.derive_process_reap_dependency_v1(verified_nine)
    solver_dependency = v1.derive_solver_stage_exclusion_dependency_v1(
        verified=verified_nine,
        transcript=owner_transcript,
    )
    route_proofs = _route_proofs_v2(
        verified_nine=verified_nine,
        dependency=route_dependency,
    )
    values = {
        **{row.path: row.value for row in base.proofs},
        **{row.path: row.value for row in route_proofs},
    }
    return K7CompleteDerivedReconciliationReadinessV2(
        _READINESS_ISSUER,
        base,
        process_dependency,
        solver_dependency,
        route_dependency,
        route_proofs,
        tuple((path, values[path]) for path in v1.DERIVED_PATHS),
    )


def replay_k7_complete_eight_path_reconciliation_v2(
    claimed: K7CompleteDerivedReconciliationReadinessV2,
    **kwargs: Any,
) -> K7CompleteDerivedReconciliationReadinessV2:
    if type(claimed) is not K7CompleteDerivedReconciliationReadinessV2:
        _fail("complete reconciliation replay requires one exact V2 readiness")
    expected = derive_k7_complete_eight_path_reconciliation_v2(**kwargs)
    if (
        claimed.readiness_id != expected.readiness_id
        or claimed.to_document() != expected.to_document()
    ):
        _fail("complete reconciliation differs from independent replay")
    return expected


__all__ = (
    "COMPLETE_READINESS_V2_DOMAIN",
    "ConstructionK7DerivedReconciliationV2Error",
    "K7CompleteDerivedReconciliationReadinessV2",
    "K7ExactRouteDerivedPathProofV2",
    "K7ExactProofRowV2",
    "K7RouteTerminalSemanticDependencyV2",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "ROUTE_AUTHORITY_REPLAY_INPUT_KEYS",
    "ROUTE_BOUND_FACT_KEYS",
    "ROUTE_DEPENDENCY_V2_DOMAIN",
    "ROUTE_PATHS",
    "ROUTE_PATH_PROOF_V2_DOMAIN",
    "SCHEMA_VERSION",
    "V1_BASE_PATHS",
    "derive_k7_complete_eight_path_reconciliation_v2",
    "derive_route_terminal_semantic_dependency_v2",
    "replay_k7_complete_eight_path_reconciliation_v2",
)
