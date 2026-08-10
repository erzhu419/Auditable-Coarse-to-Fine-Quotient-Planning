"""One-shot production accounting pipeline for the exact K7 occurrence.

The individual K7 authorities intentionally remain small and independently
replayable.  This module is the orchestration boundary that prevents a caller
from treating any proper prefix of that chain as a completed accounting run.
It accepts the exact production roots, replays all nine shared-resource
sources, closes all 202 required paths, materializes the formal vectors,
derives the typed attempt terminal, independently verifies the complete
bundle, and finally closes the logical occurrence.

The result is a process-local aggregate, not a new artifact role.  Every
portable artifact it exposes is issued by its existing role-specific authority
and can still be verified without trusting this orchestrator.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, Mapping, NoReturn

from acfqp import campaign_v1
from acfqp import construction_k7_derived_reconciliation_v2 as derived_v2
from acfqp import construction_k7_formal_accounting_materializer_v1 as materializer_v1
from acfqp import construction_k7_logical_occurrence_closure_v1 as occurrence_closure_v1
from acfqp import (
    construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_v1,
)
from acfqp import construction_k7_root_cap_terminal_authority_v1 as terminal_v1
from acfqp import construction_k7_semantic_evidence_closure_v1 as semantic_v1
from acfqp import (
    construction_occurrence_identity_cutoff_semantic_authority_v2
    as occurrence_v2,
)
from acfqp import construction_profile_native_zero_semantic_authority_v1 as zero_v1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_production_accounting_pipeline_v1"

EXPECTED_SHARED_RESOURCE_PATH_COUNT = 9
EXPECTED_COUNTER_RECORD_COUNT = 202
EXPECTED_PROJECTION_TERM_COUNT = 182
EXPECTED_COMPARISON_AXIS_COUNT = 8

_ROOT_KEYS = frozenset(
    {
        "identity_join",
        "cutoff_attestation",
        "owned_result",
        "evidence_closure",
        "receipt_set",
        "runtime_envelope",
        "request_replay",
        "source_envelope",
        "verified_envelope",
        "output_bundle",
        "operational_output_bytes",
        "owner_event_candidates",
        "role_manifest",
    }
)
_CLOSURE_INPUT_KEYS = frozenset(
    {
        "replay_roots",
        "occurrence_authority",
        "verified_nine",
        "owner_candidates",
        "profile_native_zeros",
        "derived_reconciliation",
    }
)
_RESULT_ISSUER = object()


class ConstructionK7ProductionAccountingPipelineV1Error(ValueError):
    """The K7 roots or one mandatory accounting layer failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProductionAccountingPipelineV1Error(message)


def _exact_roots(replay_roots: Any) -> dict[str, Any]:
    if type(replay_roots) is not dict or set(replay_roots) != _ROOT_KEYS:
        _fail("production accounting requires the exact replay-root field set")
    return dict(replay_roots)


def _source_archive(raw: Any) -> bytes:
    if type(raw) is not bytes or not raw:
        _fail("production accounting requires nonempty frozen source-archive bytes")
    return raw


@dataclass(frozen=True, slots=True)
class K7ProductionAccountingPipelineResultV1:
    """All role-specific outputs from one all-or-nothing K7 replay."""

    _issuer: InitVar[object]
    closure_replay_inputs: Mapping[str, Any] = field(
        repr=False,
        compare=False,
    )
    semantic_closure: semantic_v1.K7SemanticEvidenceClosureV1
    formal_materialization: materializer_v1.K7FormalAccountingMaterializationBundleV1
    terminal_accounting: terminal_v1.K7RootCapTerminalAccountingBundleV1
    complete_verification: complete_v1.K7ProductionCompleteBundleVerificationV1
    logical_occurrence_closure: occurrence_closure_v1.K7LogicalOccurrenceClosureBundleV1
    logical_occurrence_verification: (
        occurrence_closure_v1.K7LogicalOccurrenceClosureVerificationV1
    )

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("production accounting pipeline result is caller-minted")
        if (
            type(self.closure_replay_inputs) is not dict
            or set(self.closure_replay_inputs) != _CLOSURE_INPUT_KEYS
            or type(self.semantic_closure)
            is not semantic_v1.K7SemanticEvidenceClosureV1
            or type(self.formal_materialization)
            is not materializer_v1.K7FormalAccountingMaterializationBundleV1
            or type(self.terminal_accounting)
            is not terminal_v1.K7RootCapTerminalAccountingBundleV1
            or type(self.complete_verification)
            is not complete_v1.K7ProductionCompleteBundleVerificationV1
            or type(self.logical_occurrence_closure)
            is not occurrence_closure_v1.K7LogicalOccurrenceClosureBundleV1
            or type(self.logical_occurrence_verification)
            is not occurrence_closure_v1.K7LogicalOccurrenceClosureVerificationV1
        ):
            _fail("production accounting pipeline contains a foreign authority")

        work = self.formal_materialization.work_vector
        comparison = self.formal_materialization.comparison_vector
        proof = self.formal_materialization.actual_projection_proof
        verified_closure = self.logical_occurrence_verification.verified_bundle
        if (
            self.formal_materialization.semantic_evidence_closure_id
            != self.semantic_closure.closure_id
            or self.terminal_accounting.formal_materialization.bundle_id
            != self.formal_materialization.bundle_id
            or self.complete_verification.semantic_evidence_closure_id
            != self.semantic_closure.closure_id
            or self.complete_verification.formal_materialization_bundle_id
            != self.formal_materialization.bundle_id
            or self.complete_verification.terminal_accounting_bundle_id
            != self.terminal_accounting.bundle_id
            or self.logical_occurrence_closure.complete_verification.verification_id
            != self.complete_verification.verification_id
            or verified_closure.bundle_id != self.logical_occurrence_closure.bundle_id
            or len(work.records) != EXPECTED_COUNTER_RECORD_COUNT
            or len({row.path for row in work.records}) != EXPECTED_COUNTER_RECORD_COUNT
            or proof.projection_term_count != EXPECTED_PROJECTION_TERM_COUNT
            or len(comparison.values) != EXPECTED_COMPARISON_AXIS_COUNT
        ):
            _fail("production accounting layers crossed identities or cardinalities")

    def to_document(self) -> dict[str, Any]:
        work = self.formal_materialization.work_vector
        comparison = self.formal_materialization.comparison_vector
        terminal = self.terminal_accounting.to_document()
        occurrence = self.logical_occurrence_closure.to_document()[
            "logical_occurrence_closure"
        ]
        return {
            "schema": "acfqp.construction_k7_production_accounting_pipeline_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_cutoff_authority_bundle_id": (
                self.semantic_closure.context.occurrence_authority_bundle_id
            ),
            "profile_native_zero_envelope_id": (
                self.semantic_closure.context.profile_native_zero_envelope_id
            ),
            "derived_reconciliation_readiness_id": (
                self.semantic_closure.context.derived_reconciliation_readiness_id
            ),
            "semantic_evidence_closure_id": self.semantic_closure.closure_id,
            "formal_accounting_materialization_bundle_id": (
                self.formal_materialization.bundle_id
            ),
            "work_vector_id": work.work_vector_id,
            "comparison_vector_id": comparison.comparison_vector_id,
            "actual_projection_proof_id": (
                self.formal_materialization.actual_projection_proof.proof_id
            ),
            "terminal_accounting_bundle_id": self.terminal_accounting.bundle_id,
            "complete_bundle_verification_id": (
                self.complete_verification.verification_id
            ),
            "logical_occurrence_closure_bundle_id": (
                self.logical_occurrence_closure.bundle_id
            ),
            "logical_occurrence_closure_verification_id": (
                self.logical_occurrence_verification.verification_id
            ),
            "shared_resource_path_count": EXPECTED_SHARED_RESOURCE_PATH_COUNT,
            "counter_record_count": len(work.records),
            "projection_term_count": (
                self.formal_materialization.actual_projection_proof
                .projection_term_count
            ),
            "comparison_axis_count": len(comparison.values),
            "terminal_scope": terminal["terminal_scope"],
            "terminal_class": terminal["terminal_class"],
            "terminal_code": terminal["terminal_code"],
            "specific_cause": terminal["specific_cause"],
            "logical_occurrence_closed": occurrence["logical_occurrence_closed"],
            "noncertificate_count": occurrence["noncertificate_count"],
            "all_nine_shared_resources_replayed": True,
            "all_202_required_paths_materialized": True,
            "counter_record_to_work_vector_to_comparison_vector_complete": True,
            "independent_complete_bundle_replay_passed": True,
            "logical_occurrence_replay_passed": True,
            "complete_replay_inputs_retained_for_campaign": True,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }


def run_k7_production_accounting_pipeline_v1(
    *,
    replay_roots: dict[str, Any],
    source_archive_raw: bytes,
) -> K7ProductionAccountingPipelineResultV1:
    """Replay every mandatory K7 accounting layer or return no result."""

    roots = _exact_roots(replay_roots)
    archive = _source_archive(source_archive_raw)
    try:
        occurrence = occurrence_v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(
            **roots
        )
        zeros = zero_v1.issue_k7_profile_native_zero_semantic_authority_v1(
            occurrence_cutoff_authority=occurrence,
            owner_candidate_set=roots["owner_event_candidates"],
            verified_nine_envelope=roots["verified_envelope"],
            runtime_envelope=roots["runtime_envelope"],
            request_replay=roots["request_replay"],
            role_manifest=roots["role_manifest"],
            operational_output_bytes=roots["operational_output_bytes"],
            source_archive_raw=archive,
        )
        derived = derived_v2.derive_k7_complete_eight_path_reconciliation_v2(
            verified_nine=roots["verified_envelope"],
            authority_bundle=occurrence,
            route_replay_inputs=roots,
        )
        closure_inputs: dict[str, Any] = {
            "replay_roots": roots,
            "occurrence_authority": occurrence,
            "verified_nine": roots["verified_envelope"],
            "owner_candidates": roots["owner_event_candidates"],
            "profile_native_zeros": zeros,
            "derived_reconciliation": derived,
        }
        semantic = semantic_v1.issue_k7_semantic_evidence_closure_v1(
            **closure_inputs
        )
        formal = materializer_v1.materialize_k7_formal_accounting_v1(
            semantic_closure_raw=semantic.canonical_bytes,
            closure_replay_inputs=closure_inputs,
        )
        terminal = terminal_v1.issue_k7_root_cap_terminal_accounting_bundle_v1(
            formal_materialization_raw=formal.canonical_bytes,
            semantic_closure_raw=semantic.canonical_bytes,
            closure_replay_inputs=closure_inputs,
        )
        complete = complete_v1.verify_k7_production_complete_bundle_independently_v1(
            semantic_closure_raw=semantic.canonical_bytes,
            formal_materialization_raw=formal.canonical_bytes,
            terminal_accounting_bundle_raw=terminal.canonical_bytes,
            closure_replay_inputs=closure_inputs,
        )
        route = roots["request_replay"].request.route_identity
        logical = occurrence_closure_v1.issue_k7_logical_occurrence_closure_bundle_v1(
            complete_bundle_verification=complete,
            terminal_accounting_bundle_raw=terminal.canonical_bytes,
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1(),
        )
        logical_verification = (
            occurrence_closure_v1.verify_k7_logical_occurrence_closure_bundle_bytes_v1(
                raw=logical.canonical_bytes,
                complete_bundle_verification_raw=complete.canonical_bytes,
                semantic_closure_raw=semantic.canonical_bytes,
                formal_materialization_raw=formal.canonical_bytes,
                terminal_accounting_bundle_raw=terminal.canonical_bytes,
                closure_replay_inputs=closure_inputs,
            )
        )
    except Exception as error:
        raise ConstructionK7ProductionAccountingPipelineV1Error(
            "production accounting pipeline failed full-root replay"
        ) from error
    return K7ProductionAccountingPipelineResultV1(
        _RESULT_ISSUER,
        closure_inputs,
        semantic,
        formal,
        terminal,
        complete,
        logical,
        logical_verification,
    )


def replay_k7_production_accounting_pipeline_v1(
    claimed: Any,
    *,
    replay_roots: dict[str, Any],
    source_archive_raw: bytes,
) -> K7ProductionAccountingPipelineResultV1:
    """Recompute the complete pipeline and compare every role-specific output."""

    if type(claimed) is not K7ProductionAccountingPipelineResultV1:
        _fail("pipeline replay requires one exact issued result")
    expected = run_k7_production_accounting_pipeline_v1(
        replay_roots=replay_roots,
        source_archive_raw=source_archive_raw,
    )
    if claimed.to_document() != expected.to_document():
        _fail("production accounting pipeline result differs from full-root replay")
    return expected


__all__ = (
    "ConstructionK7ProductionAccountingPipelineV1Error",
    "EXPECTED_COMPARISON_AXIS_COUNT",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "EXPECTED_PROJECTION_TERM_COUNT",
    "EXPECTED_SHARED_RESOURCE_PATH_COUNT",
    "K7ProductionAccountingPipelineResultV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "replay_k7_production_accounting_pipeline_v1",
    "run_k7_production_accounting_pipeline_v1",
)
