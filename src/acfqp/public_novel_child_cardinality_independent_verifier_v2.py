"""Independent replay for the V0-072 public novel-child authority.

The verifier deliberately does not call the production authorization
function or its row-derivation helpers.  Starting from the registered public
context, the complete public catalogues, and the frozen parent descriptors,
it reconstructs the current closure, induced H1 rows, absent-row partition,
round union, exact cardinalities, and both draw bounds.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import public_novel_child_cardinality_authority_v2 as authority
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_independent_public_novel_child_cardinality_replay_v0"
)
_ATTESTATION_DOMAIN = (
    "acfqp:v072-independent-novel-child-cardinality-attestation:v2"
)


class IndependentNovelChildCardinalityV2VerificationFailure(ValueError):
    """The claimed authority does not independently replay."""


def _content_id(payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(
        _ATTESTATION_DOMAIN.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            f"{field} is not a full content ID"
        ) from error


def _registered_context(
    context: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "independent replay requires the exact registered context"
        )
    return context


def _public_catalogue(
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: observer.HeldoutLegalActionCatalogueV2,
    remaining_horizon: int,
) -> observer.HeldoutLegalActionCatalogueV2:
    if (
        type(claimed) is not observer.HeldoutLegalActionCatalogueV2
        or claimed.context_id != context.context_id
        or claimed.remaining_horizon != remaining_horizon
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "catalogue context/horizon binding changed"
        )
    replayed = observer.legal_action_catalogue_v2(
        context,
        claimed.state,
        remaining_horizon,
    )
    if replayed.to_document() != claimed.to_document():
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "catalogue completeness replay failed"
        )
    return replayed


def _physical_rows(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogues: tuple[observer.HeldoutLegalActionCatalogueV2, ...],
) -> tuple[authority.PublicH1PhysicalRowV2, ...]:
    by_id: dict[str, authority.PublicH1PhysicalRowV2] = {}
    for catalogue in catalogues:
        canonical = _public_catalogue(context, catalogue, 1)
        for action in canonical.actions:
            row = authority.PublicH1PhysicalRowV2(
                context.context_id,
                canonical.state.state_id,
                canonical.catalogue_id,
                action,
            )
            by_id[row.physical_row_id] = row
    return tuple(by_id[key] for key in sorted(by_id))


def _replay_parent(
    context: prereg.HeldoutPublicGraphContextV2,
    parent: authority.VerifiedParentObservationValidationArtifactV2,
) -> authority.VerifiedParentObservationValidationArtifactV2:
    if (
        type(parent)
        is not authority.VerifiedParentObservationValidationArtifactV2
        or parent.context_id != context.context_id
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "parent observation authority has a foreign context"
        )
    _public_catalogue(
        context,
        parent.parent_catalogue,
        prereg.HORIZON,
    )
    try:
        replayed_chain = observer.verify_heldout_support_epoch_chain_v2(
            context,
            parent.parent_row_binding,
            parent.arm,
            parent.support_epoch_chain,
        )
        replayed = (
            authority.VerifiedParentObservationValidationArtifactV2(
                parent.logical_occurrence_id,
                parent.model_id,
                parent.audit_id,
                parent.frontier_id,
                parent.threshold_profile_id,
                parent.selected_candidate_id,
                parent.selected_planner_row_id,
                parent.upstream_verification_attestation_id,
                parent.evidence_role,
                parent.parent_catalogue,
                parent.parent_row_binding,
                replayed_chain,
                parent.old_support_evidence,
                parent.novel_evidence,
                parent.all_recorded_novel_descriptors_complete,
                parent.environment_law_queries,
                parent.outcome_enumeration_calls,
                parent.new_draw_calls,
            )
        )
    except (
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
    ) as error:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "parent observation/validation replay failed"
        ) from error
    if replayed.to_document() != parent.to_document():
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "parent observation/validation bytes changed on replay"
        )
    return replayed


def _replay_closure(
    context: prereg.HeldoutPublicGraphContextV2,
    closure: authority.CurrentPublicH1RowClosureV2,
) -> authority.CurrentPublicH1RowClosureV2:
    if (
        type(closure) is not authority.CurrentPublicH1RowClosureV2
        or closure.context_id != context.context_id
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "current H1 closure has a foreign context"
        )
    canonical_catalogues = tuple(
        _public_catalogue(context, item, 1)
        for item in closure.catalogues
    )
    if (
        tuple(item.catalogue_id for item in canonical_catalogues)
        != tuple(
            sorted({item.catalogue_id for item in canonical_catalogues})
        )
        or len({item.state.state_id for item in canonical_catalogues})
        != len(canonical_catalogues)
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "current H1 catalogue registry is duplicated or unsorted"
        )
    expected_rows = _physical_rows(context, canonical_catalogues)
    try:
        replayed = authority.CurrentPublicH1RowClosureV2(
            context.context_id,
            closure.model_id,
            canonical_catalogues,
            expected_rows,
        )
    except authority.PublicNovelChildCardinalityV2InvariantViolation as error:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "current H1 closure reconstruction failed"
        ) from error
    if replayed.to_document() != closure.to_document():
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "current H1 closure omitted, added, or duplicated a public row"
        )
    return replayed


def _induced_catalogues(
    context: prereg.HeldoutPublicGraphContextV2,
    parent: authority.VerifiedParentObservationValidationArtifactV2,
) -> tuple[observer.HeldoutLegalActionCatalogueV2, ...]:
    by_id: dict[str, observer.HeldoutLegalActionCatalogueV2] = {}
    for evidence in parent.novel_evidence:
        descriptor = evidence.descriptor
        if descriptor.failure:
            continue
        catalogue = observer.legal_action_catalogue_v2(
            context,
            descriptor.next_state,
            1,
        )
        by_id[catalogue.catalogue_id] = catalogue
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class IndependentNovelChildCardinalityAttestationV2:
    authority_id: str
    parent_artifact_id: str
    closure_id: str
    selector_counterfactual_id: str
    context_id: str
    round_index: int
    exact_new_child_row_count: int
    exact_cumulative_child_row_count: int
    exact_round_draw_upper: int
    exact_cumulative_draw_upper: int
    verification_result: str = "VALID"

    def __post_init__(self) -> None:
        for value, field in (
            (self.authority_id, "verified authority"),
            (self.parent_artifact_id, "verified parent"),
            (self.closure_id, "verified closure"),
            (
                self.selector_counterfactual_id,
                "verified selector counterfactual",
            ),
            (self.context_id, "verified context"),
        ):
            _cid(value, field)
        if (
            type(self.round_index) is not int
            or not 1 <= self.round_index <= authority.MAX_ROUNDS
            or type(self.exact_new_child_row_count) is not int
            or self.exact_new_child_row_count < 0
            or type(self.exact_cumulative_child_row_count) is not int
            or not 0
            <= self.exact_cumulative_child_row_count
            <= authority.MAX_CUMULATIVE_CHILD_ROWS
            or type(self.exact_round_draw_upper) is not int
            or type(self.exact_cumulative_draw_upper) is not int
            or self.exact_cumulative_draw_upper
            > authority.MAX_CUMULATIVE_DRAW_UPPER
            or self.verification_result != "VALID"
        ):
            raise IndependentNovelChildCardinalityV2VerificationFailure(
                "independent verification attestation is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_novel_child_cardinality_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification_profile": VERIFICATION_PROFILE,
            "authority_id": self.authority_id,
            "parent_artifact_id": self.parent_artifact_id,
            "closure_id": self.closure_id,
            "selector_counterfactual_id": (
                self.selector_counterfactual_id
            ),
            "context_id": self.context_id,
            "round_index": self.round_index,
            "exact_new_child_row_count": (
                self.exact_new_child_row_count
            ),
            "exact_cumulative_child_row_count": (
                self.exact_cumulative_child_row_count
            ),
            "exact_round_draw_upper": self.exact_round_draw_upper,
            "exact_cumulative_draw_upper": (
                self.exact_cumulative_draw_upper
            ),
            "verification_result": "VALID",
            "production_authorization_builder_called": False,
            "claimed_ids_or_counts_trusted": False,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def attestation_id(self) -> str:
        return _content_id(self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestation_id": self.attestation_id,
        }


def verify_public_novel_child_cardinality_authority_v2(
    *,
    claimed: authority.PublicNovelChildCardinalityAuthorityV2,
    context: prereg.HeldoutPublicGraphContextV2,
    parent: authority.VerifiedParentObservationValidationArtifactV2,
    current_h1_closure: authority.CurrentPublicH1RowClosureV2,
    selector_gain: selector.OneRowCounterfactualGainV2,
    previous_evidence: (
        authority.PublicNovelChildCardinalityEvidenceV2 | None
    ) = None,
) -> IndependentNovelChildCardinalityAttestationV2:
    """Replay the authority without calling its production builder."""

    registered = _registered_context(context)
    replayed_parent = _replay_parent(registered, parent)
    replayed_closure = _replay_closure(
        registered,
        current_h1_closure,
    )
    if (
        type(claimed)
        is not authority.PublicNovelChildCardinalityAuthorityV2
        or type(selector_gain)
        is not selector.OneRowCounterfactualGainV2
        or replayed_closure.model_id != replayed_parent.model_id
        or not replayed_parent.novel_evidence
        or not selector_gain.eligible
        or selector_gain.gain <= 0
        or selector_gain.model_id != replayed_parent.model_id
        or selector_gain.audit_id != replayed_parent.audit_id
        or selector_gain.frontier_id != replayed_parent.frontier_id
        or selector_gain.threshold_profile_id
        != replayed_parent.threshold_profile_id
        or selector_gain.support_epoch_id
        != replayed_parent.support_epoch_id
        or selector_gain.candidate_id
        != replayed_parent.selected_candidate_id
        or selector_gain.planner_row_id
        != replayed_parent.selected_planner_row_id
        or selector_gain.cardinality_evidence_id
        != claimed.cardinality_evidence.evidence_id
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "selector gain does not bind the verified current parent"
        )

    catalogues = _induced_catalogues(registered, replayed_parent)
    induced_rows = _physical_rows(registered, catalogues)
    current_ids = set(replayed_closure.physical_row_ids)
    present = tuple(
        row for row in induced_rows if row.physical_row_id in current_ids
    )
    acquire = tuple(
        row
        for row in induced_rows
        if row.physical_row_id not in current_ids
    )
    exact_round_upper = (
        authority.PROMOTED_PARENT_DRAWS_PER_ROUND
        + authority.CHILD_ROW_DRAWS * len(acquire)
    )
    if previous_evidence is None:
        round_index = 1
        previous_id = None
        cumulative = acquire
    else:
        if (
            type(previous_evidence)
            is not authority.PublicNovelChildCardinalityEvidenceV2
            or previous_evidence.round_index != 1
            or previous_evidence.logical_occurrence_id
            != replayed_parent.logical_occurrence_id
            or previous_evidence.context_id != registered.context_id
            or previous_evidence.arm != replayed_parent.arm
            or previous_evidence.model_id == replayed_parent.model_id
            or previous_evidence.parent_row_binding_id
            == replayed_parent.parent_row_binding.row_binding_id
            or previous_evidence.parent_support_epoch_id
            == replayed_parent.support_epoch_id
            or previous_evidence.selected_candidate_id
            == replayed_parent.selected_candidate_id
            or not set(previous_evidence.cumulative_row_ids).issubset(
                current_ids
            )
        ):
            raise IndependentNovelChildCardinalityV2VerificationFailure(
                "round-two predecessor/model/closure did not advance"
            )
        prior_by_id = {
            row.physical_row_id: row
            for row in previous_evidence.cumulative_rows
        }
        if set(prior_by_id) & {
            row.physical_row_id for row in acquire
        }:
            raise IndependentNovelChildCardinalityV2VerificationFailure(
                "round two attempted to reuse a prior acquisition row"
            )
        cumulative_by_id = {
            **prior_by_id,
            **{row.physical_row_id: row for row in acquire},
        }
        cumulative = tuple(
            cumulative_by_id[key] for key in sorted(cumulative_by_id)
        )
        round_index = 2
        previous_id = previous_evidence.evidence_id

    if (
        len(cumulative) > authority.MAX_CUMULATIVE_CHILD_ROWS
        or round_index not in (1, 2)
    ):
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "independent cumulative row/round cap replay failed"
        )
    cumulative_upper = (
        authority.PROMOTED_PARENT_DRAWS_PER_ROUND * round_index
        + authority.CHILD_ROW_DRAWS * len(cumulative)
    )
    if cumulative_upper > authority.MAX_CUMULATIVE_DRAW_UPPER:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "independent cumulative draw cap replay failed"
        )
    try:
        expected_evidence = authority.PublicNovelChildCardinalityEvidenceV2(
            replayed_parent.logical_occurrence_id,
            registered.context_id,
            replayed_parent.arm,
            replayed_parent.model_id,
            replayed_parent.audit_id,
            replayed_parent.frontier_id,
            replayed_parent.threshold_profile_id,
            replayed_parent.parent_artifact_id,
            replayed_parent.parent_row_binding.row_binding_id,
            replayed_parent.support_epoch_id,
            replayed_closure.closure_id,
            replayed_parent.selected_candidate_id,
            replayed_parent.selected_planner_row_id,
            round_index,
            previous_id,
            replayed_parent.old_support_descriptor_ids,
            replayed_parent.novel_descriptor_ids,
            replayed_parent.promoted_support_descriptor_ids,
            catalogues,
            induced_rows,
            present,
            acquire,
            cumulative,
            len(acquire),
            len(cumulative),
            exact_round_upper,
            cumulative_upper,
            len(catalogues),
        )
        if (
            expected_evidence.to_document()
            != claimed.cardinality_evidence.to_document()
        ):
            raise IndependentNovelChildCardinalityV2VerificationFailure(
                "claimed cardinality evidence differs from independent "
                "public row/count replay"
            )
        if (
            selector_gain.exact_draw_upper != exact_round_upper
            or selector_gain.cardinality_evidence_id
            != expected_evidence.evidence_id
        ):
            raise IndependentNovelChildCardinalityV2VerificationFailure(
                "selector gain does not consume the independently replayed "
                "full row-list cost evidence"
            )
        expected = authority.PublicNovelChildCardinalityAuthorityV2(
            expected_evidence,
            selector_gain,
        )
    except authority.PublicNovelChildCardinalityV2InvariantViolation as error:
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "independent authority reconstruction failed"
        ) from error
    if expected.to_document() != claimed.to_document():
        raise IndependentNovelChildCardinalityV2VerificationFailure(
            "claimed authority differs from independent row/count replay"
        )
    return IndependentNovelChildCardinalityAttestationV2(
        expected.authority_id,
        replayed_parent.parent_artifact_id,
        replayed_closure.closure_id,
        selector_gain.counterfactual_id,
        registered.context_id,
        round_index,
        len(acquire),
        len(cumulative),
        exact_round_upper,
        cumulative_upper,
    )


__all__ = [
    "IndependentNovelChildCardinalityAttestationV2",
    "IndependentNovelChildCardinalityV2VerificationFailure",
    "VERIFICATION_PROFILE",
    "verify_public_novel_child_cardinality_authority_v2",
]
