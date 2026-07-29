"""Independent verifier for the V0-072 incremental post-build bridge."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import exact_lazy_h2_independent_verifier_v1 as lazy_independent
from . import partial_support_robust_planner_v1 as robust
from . import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from . import v072_incremental_materializer_v1 as materializer
from . import (
    v072_incremental_materializer_independent_verifier_v1
    as materializer_independent,
)
from . import (
    v072_confidence_row_projection_independent_verifier_v1
    as confidence_projection_independent,
)
from . import v072_incremental_postbuild_bridge_v1 as bridge_types


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_incremental_postbuild_independent_verifier_v1"
)

DOMAINS = {
    "physical": "acfqp:v072-incremental-postbuild-physical-evidence:v1",
    "lineage": "acfqp:v072-incremental-postbuild-row-lineage:v1",
    "selected_policy": (
        "acfqp:v072-incremental-postbuild-selected-policy:v1"
    ),
    "result": "acfqp:v072-incremental-postbuild-result:v1",
    "confidence_authority": (
        "acfqp:v072-incremental-postbuild-confidence-row-authority:v1"
    ),
    "attestation": (
        "acfqp:v072-incremental-postbuild-independent-attestation:v1"
    ),
}


class IndependentIncrementalPostbuildVerificationFailure(ValueError):
    """The claimed standard model/audit differs from independent replay."""


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise IndependentIncrementalPostbuildVerificationFailure(
            f"independent content replay failed: {error}"
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentIncrementalPostbuildVerificationFailure(
            f"{field_name} is not a content ID"
        ) from error


def _lineage_id(
    lineage: bridge_types.HandoffRowProjectionLineageV1,
    *,
    physical_evidence_id: str,
) -> str:
    return _hash(
        "lineage",
        {
            "schema": "acfqp.v072_incremental_postbuild_row_lineage.v1",
            "schema_version": SCHEMA_VERSION,
            "semantic_physical_row_id":
                lineage.semantic_physical_row_id,
            "cold_row_evidence_id": lineage.cold_row_evidence_id,
            "cold_physical_evidence_id": physical_evidence_id,
            "discovery_transcript_id":
                lineage.discovery_transcript_id,
            "validation_transcript_id":
                lineage.validation_transcript_id,
            "validation_prefix_id": lineage.validation_prefix_id,
            "projection_binding_id": lineage.projection_binding_id,
            "source_stream_ids": list(lineage.source_stream_ids),
            "selected_checkpoint_draw_count":
                lineage.selected_checkpoint_draw_count,
            "same_handoff_physical_lineage": True,
        },
    )


def _confidence_authority_id(
    authority: bridge_types.ProductionConfidenceRowAuthorityV1,
) -> str:
    return _hash(
        "confidence_authority",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_"
                "confidence_row_authority.v1"
            ),
            "row_binding_id": authority.row_binding.row_binding_id,
            "support_epoch_id":
                authority.support_epoch.support_epoch_id,
            "confidence_snapshot_id": authority.snapshot.snapshot_id,
            "confidence_verification_id":
                authority.confidence_verification.verification_id,
            "source_projection_id":
                authority.source_projection.projection_id,
            "projection_verification_id":
                authority.projection_verification.verification_id,
            "discovery_transcript_id":
                authority.discovery_transcript_id,
            "validation_transcript_id":
                authority.validation_transcript_id,
            "row_replay_verification_id":
                authority.row_replay_verification_id,
            "support_descriptor_record_ids": [
                value.descriptor_record_id
                for value in authority.support_descriptors
            ],
            "validation_novel_descriptor_record_ids": [
                value.descriptor_record_id
                for value in authority.validation_novel
            ],
            "bucket_descriptor_ids": [
                [bucket, descriptor_id]
                for bucket, descriptor_id
                in authority.bucket_descriptor_ids
            ],
            "promotion_parent_snapshot_id": (
                None
                if authority.promotion_parent_snapshot is None
                else authority.promotion_parent_snapshot.snapshot_id
            ),
        },
    )


@dataclass(frozen=True, slots=True)
class IndependentIncrementalPostbuildAttestationV1:
    postbuild_result_id: str
    handoff_id: str
    closure_id: str
    model_pair_id: str
    planner_model_id: str
    model_verification_id: str
    planner_verification_id: str
    audit_id: str
    failed_frontier_id: str | None
    audit_status: str
    row_lineage_count: int
    round_index: int = 1
    materializer_attestation_id: str | None = None
    prior_postbuild_result_id: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.postbuild_result_id,
            self.handoff_id,
            self.closure_id,
            self.model_pair_id,
            self.planner_model_id,
            self.model_verification_id,
            self.planner_verification_id,
            self.audit_id,
        ):
            _cid(value, "postbuild attestation identity")
        if self.failed_frontier_id is not None:
            _cid(self.failed_frontier_id, "attested failed frontier")
        if self.materializer_attestation_id is not None:
            _cid(
                self.materializer_attestation_id,
                "attested materializer replay",
            )
        if self.prior_postbuild_result_id is not None:
            _cid(
                self.prior_postbuild_result_id,
                "attested prior postbuild",
            )
        if (
            self.audit_status not in (
                "CERTIFIED",
                "FAILED_PROOF_FRONTIER",
            )
            or (self.audit_status == "CERTIFIED")
            != (self.failed_frontier_id is None)
            or self.round_index not in (1, 2)
            or (self.round_index == 1)
            != (self.prior_postbuild_result_id is None)
            or not 1 <= self.row_lineage_count <= 8
            or self.materializer_attestation_id is None
        ):
            raise IndependentIncrementalPostbuildVerificationFailure(
                "postbuild attestation is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_incremental_postbuild_independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification_profile": VERIFICATION_PROFILE,
            "postbuild_result_id": self.postbuild_result_id,
            "handoff_id": self.handoff_id,
            "closure_id": self.closure_id,
            "model_pair_id": self.model_pair_id,
            "planner_model_id": self.planner_model_id,
            "model_verification_id": self.model_verification_id,
            "planner_verification_id": self.planner_verification_id,
            "audit_id": self.audit_id,
            "failed_frontier_id": self.failed_frontier_id,
            "audit_status": self.audit_status,
            "row_lineage_count": self.row_lineage_count,
            "round_index": self.round_index,
            "materializer_attestation_id":
                self.materializer_attestation_id,
            "prior_postbuild_result_id":
                self.prior_postbuild_result_id,
            "production_bridge_called": False,
            "production_model_builder_called": False,
            "production_planner_called": False,
        }

    @property
    def attestation_id(self) -> str:
        return _hash("attestation", self._payload())


def verify_incremental_postbuild_result_v1(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    claimed: bridge_types.IncrementalPostbuildResultV1,
    prior_handoff: (
        materializer.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    prior_postbuild: (
        bridge_types.IncrementalPostbuildResultV1 | None
    ) = None,
) -> IndependentIncrementalPostbuildAttestationV1:
    """Replay lineage, model proof, exact-lazy proof, and audit identity."""

    if (
        type(handoff)
        is not materializer.IncrementalModelRebuildHandoffV1
        or type(claimed)
        is not bridge_types.IncrementalPostbuildResultV1
        or (
            handoff.request.parent_epoch.round_index == 1
            and (prior_handoff is not None or prior_postbuild is not None)
        )
        or (
            handoff.request.parent_epoch.round_index == 2
            and (
                type(prior_handoff)
                is not materializer.IncrementalModelRebuildHandoffV1
                or type(prior_postbuild)
                is not bridge_types.IncrementalPostbuildResultV1
                or prior_postbuild.audit_status
                is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            )
        )
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild claim is not bound to one exact handoff"
        )
    materializer_attestation = (
        materializer_independent
        .verify_incremental_materializer_handoff_v1(
            handoff,
            previous_handoff=prior_handoff,
        )
    )
    prior_materializer_attestation = (
        None
        if prior_handoff is None
        else materializer_independent
        .verify_incremental_materializer_handoff_v1(prior_handoff)
    )
    if (
        claimed.handoff_id != materializer_attestation.handoff_id
        or (
            prior_materializer_attestation is not None
            and (
                handoff.request.previous_handoff_id
                != prior_materializer_attestation.handoff_id
                or prior_postbuild is None
                or prior_postbuild.handoff_id
                != prior_materializer_attestation.handoff_id
            )
        )
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild claim differs from independently replayed handoff identities"
        )
    if prior_postbuild is not None:
        assert prior_handoff is not None
        verify_incremental_postbuild_result_v1(
            handoff=prior_handoff,
            claimed=prior_postbuild,
        )
    expected_semantic_rows = set(handoff.resulting_physical_row_ids)
    lineages = claimed.row_lineage
    if (
        type(lineages) is not tuple
        or len(lineages) != len(expected_semantic_rows)
        or {
            item.semantic_physical_row_id for item in lineages
        }
        != expected_semantic_rows
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild lineage is not one-to-one with handoff rows"
        )
    rows_by_id = {
        item.row_evidence_id: item
        for item in claimed.closure_bundle.all_rows
    }
    projections_by_id = {
        item.projection_binding_id: item
        for item in claimed.row_projections
    }
    source_handoffs = (
        *(() if prior_handoff is None else (prior_handoff,)),
        handoff,
    )
    execution_stream_ids = {
        stream.stream_id
        for source_handoff in source_handoffs
        for stream in (
            source_handoff.parent_validation_stream,
            *(
                stream
                for child in source_handoff.child_rows
                for stream in (
                    child.discovery_stream,
                    child.validation_stream,
                )
            ),
        )
    }
    all_ranges = {
        item.stream_id: item
        for item in (
            *handoff.prior_cold_raw_commitment_ranges,
            *(
                item
                for source_handoff in source_handoffs
                for item in source_handoff.raw_commitment_ranges
            ),
        )
    }
    allowed_source_ids = set(all_ranges)
    stream_by_id = {
        stream.stream_id: stream
        for source_handoff in source_handoffs
        for stream in (
            source_handoff.parent_validation_stream,
            *(
                stream
                for child in source_handoff.child_rows
                for stream in (
                    child.discovery_stream,
                    child.validation_stream,
                )
            ),
        )
    }
    upstream_by_stream: dict[str, tuple[Any, str]] = {}
    for transcript in handoff.request.parent_evidence.upstream_root_rows:
        for lane, draws, seed_id, digest in (
            (
                "UPSTREAM_DISCOVERY",
                64,
                transcript.discovery_seed_id,
                transcript.discovery_raw_digest,
            ),
            (
                "UPSTREAM_VALIDATION",
                2_048,
                transcript.validation_seed_id,
                transcript.validation_raw_digest,
            ),
        ):
            stream_id = materializer_independent._upstream_stream_id(
                transcript,
                lane=lane,
                draws=draws,
                seed_id=seed_id,
                raw_digest=digest,
            )
            upstream_by_stream[stream_id] = (transcript, lane)

    def expected_sample_ids(
        stream_id: str,
        draw_count: int,
    ) -> tuple[str, ...]:
        stream = stream_by_id.get(stream_id)
        if stream is not None:
            return tuple(
                materializer_independent._raw_commitment_id(
                    stream,
                    index,
                )
                for index in range(draw_count)
            )
        upstream = upstream_by_stream.get(stream_id)
        if upstream is None:
            raise IndependentIncrementalPostbuildVerificationFailure(
                "confidence transcript is absent from verified raw ledgers"
            )
        transcript, lane = upstream
        return tuple(
            materializer_independent._upstream_commitment_id(
                transcript,
                lane=lane,
                stream_id=stream_id,
                index=index,
            )
            for index in range(draw_count)
        )
    physical_ids: set[str] = set()
    lineage_ids: list[str] = []
    for lineage in lineages:
        row = rows_by_id.get(lineage.cold_row_evidence_id)
        projection = projections_by_id.get(lineage.projection_binding_id)
        discovery_range = all_ranges.get(
            lineage.discovery_transcript_id
        )
        validation_range = all_ranges.get(
            lineage.validation_transcript_id
        )
        if discovery_range is None or validation_range is None:
            raise IndependentIncrementalPostbuildVerificationFailure(
                "row lineage references an unverified raw range"
            )
        expected_physical = _hash(
            "physical",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_physical_evidence.v1"
                ),
                "semantic_physical_row_id":
                    lineage.semantic_physical_row_id,
                "source_stream_ids": list(lineage.source_stream_ids),
                "discovery_raw_commitment_range_proof_id":
                    discovery_range.range_proof_id,
                "validation_raw_commitment_range_proof_id":
                    validation_range.range_proof_id,
                "selected_checkpoint_draw_count":
                    lineage.selected_checkpoint_draw_count,
            },
        )
        replayed_lineage_id = _lineage_id(
            lineage,
            physical_evidence_id=expected_physical,
        )
        if (
            row is None
            or projection is None
            or not set(lineage.source_stream_ids).issubset(
                allowed_source_ids
            )
            or set(lineage.source_stream_ids)
            != {
                lineage.discovery_transcript_id,
                lineage.validation_transcript_id,
            }
            or lineage.cold_physical_evidence_id != expected_physical
            or row.physical_evidence_id != expected_physical
            or projection.physical_evidence_id != expected_physical
            or projection.row_evidence_id != row.row_evidence_id
            or projection.discovery_transcript_id
            != lineage.discovery_transcript_id
            or projection.validation_transcript_id
            != lineage.validation_transcript_id
            or projection.validation_prefix_id
            != lineage.validation_prefix_id
            or projection.selected_checkpoint_draw_count
            != lineage.selected_checkpoint_draw_count
        ):
            raise IndependentIncrementalPostbuildVerificationFailure(
                "one row projection is not derived from handoff transcript lineage"
            )
        physical_ids.add(expected_physical)
        lineage_ids.append(replayed_lineage_id)
    if tuple(lineage_ids) != tuple(sorted(set(lineage_ids))):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild lineage identities are not canonical and unique"
        )
    if physical_ids != set(claimed.model_pair.shared_physical_row_ids):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "standard model physical inventory differs from handoff lineage"
        )
    lineage_by_semantic = {
        item.semantic_physical_row_id: item for item in lineages
    }
    confidence_authority_ids = tuple(
        _confidence_authority_id(item)
        for item in claimed.confidence_authorities
    )
    if (
        len(claimed.confidence_authorities) != len(lineages)
        or confidence_authority_ids
        != tuple(sorted(set(confidence_authority_ids)))
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "confidence authority inventory is incomplete"
        )
    for authority in claimed.confidence_authorities:
        semantic_row_id = authority.row_binding.physical_row_id
        lineage = lineage_by_semantic.get(semantic_row_id)
        if lineage is None:
            raise IndependentIncrementalPostbuildVerificationFailure(
                "confidence authority is transplanted across a row"
            )
        replayed_projection = (
            confidence_projection_independent
            .verify_v072_confidence_row_projection_v1(
                authority.source_projection
            )
        )
        actual_validation_samples = tuple(
            item.sample_id
            for item in (
                authority.snapshot.validation_prefix.observations
            )
        )
        expected_validation_samples = expected_sample_ids(
            authority.validation_transcript_id,
            authority.snapshot.selected_checkpoint_draw_count,
        )
        if (
            replayed_projection
            != authority.projection_verification
            or replayed_projection.verification_id
            != authority.projection_verification.verification_id
            or actual_validation_samples
            != expected_validation_samples
            or authority.discovery_transcript_id
            != lineage.discovery_transcript_id
            or authority.validation_transcript_id
            != lineage.validation_transcript_id
            or authority.snapshot.snapshot_id
            != next(
                row.confidence_snapshot_id
                for row in claimed.closure_bundle.all_rows
                if row.row_evidence_id
                == lineage.cold_row_evidence_id
            )
        ):
            raise IndependentIncrementalPostbuildVerificationFailure(
                "production confidence authority differs from raw/projection replay"
            )
        epoch = authority.support_epoch
        if hasattr(epoch, "discovery_evidence"):
            discovery = epoch.discovery_evidence
            actual_discovery_samples = tuple(
                item.sample_id for item in discovery.observations
            )
            if actual_discovery_samples != expected_sample_ids(
                authority.discovery_transcript_id,
                len(actual_discovery_samples),
            ):
                raise IndependentIncrementalPostbuildVerificationFailure(
                    "discovery support samples differ from the raw ledger"
                )
    replayed_model = (
        model_independent.verify_v072_cold_h2_model_pair_independently_v1(
            claimed.model_pair
        )
    )
    if (
        replayed_model != claimed.model_independent_attestation
        or replayed_model.verification_id
        != claimed.model_independent_attestation.verification_id
        or claimed.model_pair.closure_bundle != claimed.closure_bundle
        or tuple(
            item.projection_binding_id
            for item in claimed.model_pair.row_projections
        )
        != tuple(
            item.projection_binding_id
            for item in claimed.row_projections
        )
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "model pair or independent model attestation differs"
        )
    planner_projection = (
        claimed.model_pair.quotient_planner_projection
    )
    replayed_planner = lazy_independent.verify_exact_lazy_h2_solve_result_v1(
        planner_projection.planner_model,
        claimed.model_pair.threshold_profile,
        claimed.planner_result.solve_result,
    )
    if (
        claimed.planner_result.independent_verification is None
        or replayed_planner.to_document()
        != claimed.planner_result.independent_verification.to_document()
        or replayed_planner.model_id
        != planner_projection.planner_model.model_id
        or replayed_planner.threshold_profile_id
        != claimed.model_pair.threshold_profile.threshold_profile_id
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "exact-lazy independent proof replay differs"
        )
    audit = claimed.planner_result.solve_result.audit
    if audit is None:
        raise IndependentIncrementalPostbuildVerificationFailure(
            "resource exhaustion cannot close postbuild verification"
        )
    frontier_id = (
        None
        if audit.failed_frontier is None
        else audit.failed_frontier.frontier_id
    )
    selected_policy_id = _hash(
        "selected_policy",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_selected_policy.v1"
            ),
            "planner_model_id": claimed.planner_result.model_id,
            "audit_id": audit.audit_id,
            "assignment_ids": [
                item.assignment_id for item in audit.assignments
            ],
            "independent_verification_id":
                replayed_planner.verification_id,
        },
    )
    if (
        claimed.audit_id != audit.audit_id
        or claimed.audit_status is not audit.status
        or claimed.failed_frontier_id != frontier_id
        or claimed.selected_policy_id != selected_policy_id
        or (audit.status is robust.RobustAuditStatus.CERTIFIED)
        != (frontier_id is None)
    ):
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild status/frontier was not mechanically audit-derived"
        )
    payload = {
        "schema": "acfqp.v072_incremental_postbuild_result.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "1.36.0",
        "profile_key": "v072_incremental_postbuild_bridge_v1",
        "handoff_id": materializer_attestation.handoff_id,
        "closure_id": claimed.closure_bundle.closure_id,
        "row_projection_binding_ids": [
            item.projection_binding_id
            for item in claimed.row_projections
        ],
        "row_lineage_ids": [
            *lineage_ids,
        ],
        "confidence_authority_ids": [
            *confidence_authority_ids,
        ],
        "model_pair_id": claimed.model_pair.model_pair_id,
        "direct_model_id": claimed.model_pair.direct_model.model_id,
        "quotient_model_id": claimed.model_pair.quotient_model.model_id,
        "quotient_planner_model_id":
            planner_projection.planner_model.model_id,
        "quotient_other_collapse_proof_id":
            planner_projection.collapse_proof.proof_id,
        "model_independent_attestation_id":
            replayed_model.verification_id,
        "planner_component_result_id":
            claimed.planner_result.component_result_id,
        "planner_independent_verification_id":
            replayed_planner.verification_id,
        "selected_policy_id": selected_policy_id,
        "audit_id": audit.audit_id,
        "audit_status": audit.status.value,
        "failed_frontier_id": frontier_id,
        "caller_supplied_model": False,
        "caller_supplied_audit": False,
        "certificate_authority": (
            audit.status is robust.RobustAuditStatus.CERTIFIED
        ),
        "registered_target_evidence": False,
    }
    result_id = _hash("result", payload)
    if result_id != claimed.result_id:
        raise IndependentIncrementalPostbuildVerificationFailure(
            "postbuild result content identity differs"
        )
    return IndependentIncrementalPostbuildAttestationV1(
        result_id,
        materializer_attestation.handoff_id,
        claimed.closure_bundle.closure_id,
        claimed.model_pair.model_pair_id,
        planner_projection.planner_model.model_id,
        replayed_model.verification_id,
        replayed_planner.verification_id,
        audit.audit_id,
        frontier_id,
        audit.status.value,
        len(lineages),
        handoff.request.parent_epoch.round_index,
        materializer_attestation.attestation_id,
        (
            None
            if prior_postbuild is None
            else prior_postbuild.result_id
        ),
    )


__all__ = [
    "IndependentIncrementalPostbuildAttestationV1",
    "IndependentIncrementalPostbuildVerificationFailure",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "verify_incremental_postbuild_result_v1",
]
