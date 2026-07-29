"""Public, result-blind novel-child row authority for V0-072.

The authority consumes one already-frozen parent observation/validation
artifact.  It never opens an observer stream, reads an environment law, or
enumerates transition outcomes.  The only successor states it may inspect
are the novel descriptors already recorded in that parent artifact.

For every distinct nonterminal successor, a preselection evidence authority
reconstructs the complete public H1 legal-action catalogue and derives every
physical ``(state, action, h=1)`` row that is absent from the current model
closure.  Counts and draw bounds are properties of those content-addressed
rows; there is no caller-supplied row mapping or cardinality argument.  Only
after the selector has consumed that evidence to derive gain/base/rank may a
separate postselection authorization bind the chosen positive gain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_public_novel_child_cardinality_authority_v0"

MAX_ROUNDS = 2
PROMOTED_PARENT_DRAWS_PER_ROUND = 2_048
CHILD_DISCOVERY_DRAWS = 64
CHILD_VALIDATION_DRAWS = 8_192
CHILD_ROW_DRAWS = CHILD_DISCOVERY_DRAWS + CHILD_VALIDATION_DRAWS
MAX_CUMULATIVE_CHILD_ROWS = 19
MAX_CUMULATIVE_DRAW_UPPER = (
    MAX_ROUNDS * PROMOTED_PARENT_DRAWS_PER_ROUND
    + MAX_CUMULATIVE_CHILD_ROWS * CHILD_ROW_DRAWS
)

if (
    selector.PROMOTED_ROW_DRAWS != PROMOTED_PARENT_DRAWS_PER_ROUND
    or selector.CHILD_DISCOVERY_DRAWS != CHILD_DISCOVERY_DRAWS
    or selector.CHILD_VALIDATION_DRAWS != CHILD_VALIDATION_DRAWS
    or selector.MAX_NEW_CHILD_ACTIONS_TOTAL
    != MAX_CUMULATIVE_CHILD_ROWS
    or selector.MAX_TWO_ROUND_DRAW_UPPER
    != MAX_CUMULATIVE_DRAW_UPPER
):  # pragma: no cover - import-time contract drift guard
    raise RuntimeError("V0-072 selector/cardinality constants diverged")


DOMAIN_TAGS = {
    "descriptor": "acfqp:v072-recorded-transition-descriptor:v2",
    "descriptor_evidence": (
        "acfqp:v072-recorded-transition-descriptor-evidence:v2"
    ),
    "parent": (
        "acfqp:v072-verified-parent-observation-validation-artifact:v2"
    ),
    "physical_row": "acfqp:v072-public-h1-physical-row:v2",
    "closure": "acfqp:v072-current-public-h1-row-closure:v2",
    "evidence": (
        "acfqp:v072-public-novel-child-cardinality-evidence:v2"
    ),
    "authority": "acfqp:v072-public-novel-child-cardinality-authority:v2",
}


class PublicNovelChildCardinalityV2InvariantViolation(ValueError):
    """A public input, row derivation, lineage, or cap is invalid."""


class ParentEvidenceRoleV2(str, Enum):
    REGISTERED_TARGET_VERIFIED = "REGISTERED_TARGET_VERIFIED"
    SYNTHETIC_NONCONFIRMATORY_CONTROL = (
        "SYNTHETIC_NONCONFIRMATORY_CONTROL"
    )


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(tag + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "novel-child authority arithmetic must remain exact"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _action(value: Any) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "public physical action must be an integer triple"
        )
    return value


def _registered_context(
    context: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "novel-child authority requires an exact registered context"
        )
    return context


def _context_by_id(
    context_id: str,
) -> prereg.HeldoutPublicGraphContextV2:
    canonical = _cid(context_id, "public context")
    for context in prereg.registered_heldout_public_contexts_v2():
        if context.context_id == canonical:
            return context
    raise PublicNovelChildCardinalityV2InvariantViolation(
        "public context is outside the registered held-out family"
    )


def _canonical_public_catalogue(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: Any,
    *,
    remaining_horizon: int,
) -> observer.HeldoutLegalActionCatalogueV2:
    if (
        type(catalogue) is not observer.HeldoutLegalActionCatalogueV2
        or catalogue.context_id != context.context_id
        or catalogue.remaining_horizon != remaining_horizon
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "public legal-action catalogue has a foreign binding"
        )
    expected = observer.legal_action_catalogue_v2(
        context,
        catalogue.state,
        remaining_horizon,
    )
    if catalogue.to_document() != expected.to_document():
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "public legal-action catalogue is incomplete or noncanonical"
        )
    return expected


def _canonical_catalogues(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogues: tuple[observer.HeldoutLegalActionCatalogueV2, ...],
) -> tuple[observer.HeldoutLegalActionCatalogueV2, ...]:
    if type(catalogues) is not tuple:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "public H1 catalogues must be an immutable tuple"
        )
    canonical = tuple(
        _canonical_public_catalogue(
            context,
            item,
            remaining_horizon=1,
        )
        for item in catalogues
    )
    if (
        tuple(item.catalogue_id for item in canonical)
        != tuple(sorted({item.catalogue_id for item in canonical}))
        or len({item.state.state_id for item in canonical})
        != len(canonical)
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "public H1 catalogues must be state-distinct and ID-sorted"
        )
    return canonical


def _expected_parent_reward(
    catalogue: observer.HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
) -> Fraction:
    first, second, _survivor = action
    ranks = catalogue.state.ranks
    if (
        first < 0
        or second < 0
        or first >= len(ranks)
        or second >= len(ranks)
        or ranks[first] <= 0
        or ranks[first] != ranks[second]
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "parent action does not encode a legal equal-rank merge"
        )
    return (
        Fraction(
            2 ** (ranks[first] + 1),
            2 ** (prereg.RANK_CAP + 1),
        )
        / prereg.HORIZON
    )


@dataclass(frozen=True, slots=True)
class RecordedTransitionDescriptorV2:
    """One successor tuple already present in upstream observation evidence."""

    next_state: observer.HeldoutSymbolicGraphStateV2
    realized_row_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.next_state)
            is not observer.HeldoutSymbolicGraphStateV2
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "recorded transition descriptor is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_recorded_transition_descriptor.v2",
            "schema_version": SCHEMA_VERSION,
            "next_state": self.next_state.to_document(),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def descriptor_id(self) -> str:
        return _content_id("descriptor", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "descriptor_id": self.descriptor_id}


@dataclass(frozen=True, slots=True)
class RecordedDescriptorEvidenceV2:
    """All observation identities recording one exact successor descriptor."""

    descriptor: RecordedTransitionDescriptorV2
    observation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.descriptor) is not RecordedTransitionDescriptorV2
            or type(self.observation_ids) is not tuple
            or not self.observation_ids
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "descriptor evidence requires a descriptor and observations"
            )
        canonical = tuple(
            _cid(item, "recorded observation")
            for item in self.observation_ids
        )
        if canonical != tuple(sorted(set(canonical))):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "recorded observation IDs must be distinct and sorted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_recorded_transition_descriptor_evidence.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "descriptor_id": self.descriptor.descriptor_id,
            "observation_ids": list(self.observation_ids),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("descriptor_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "descriptor": self.descriptor.to_document(),
            "evidence_id": self.evidence_id,
        }


def _canonical_evidence(
    values: tuple[RecordedDescriptorEvidenceV2, ...],
    field: str,
    *,
    allow_empty: bool,
) -> tuple[RecordedDescriptorEvidenceV2, ...]:
    if (
        type(values) is not tuple
        or (not allow_empty and not values)
        or any(type(item) is not RecordedDescriptorEvidenceV2 for item in values)
        or tuple(item.evidence_id for item in values)
        != tuple(sorted({item.evidence_id for item in values}))
        or len({item.descriptor.descriptor_id for item in values})
        != len(values)
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            f"{field} must contain canonical descriptor evidence"
        )
    return values


@dataclass(frozen=True, slots=True)
class VerifiedParentObservationValidationArtifactV2:
    """Current, complete parent support/novel descriptor authority.

    ``upstream_verification_attestation_id`` is only an identity-binding slot.
    Its presence does not establish raw-tape authenticity.  A registered
    confirmatory runner and its independent verifier must exact-type bind the
    forthcoming row/confidence verification authority before this artifact
    may carry confirmatory evidence.  Tests use only the explicitly
    nonconfirmatory role.

    An authorized parent is always confidence/support epoch 1.  Epoch 2 is a
    materializer output, not a promotable parent: accepting it here would
    require a forbidden epoch 3.
    """

    logical_occurrence_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    upstream_verification_attestation_id: str
    evidence_role: ParentEvidenceRoleV2
    parent_catalogue: observer.HeldoutLegalActionCatalogueV2
    parent_row_binding: observer.HeldoutObservationRowBindingV2
    support_epoch_chain: observer.HeldoutSupportEpochChainV2
    old_support_evidence: tuple[RecordedDescriptorEvidenceV2, ...]
    novel_evidence: tuple[RecordedDescriptorEvidenceV2, ...]
    all_recorded_novel_descriptors_complete: bool = True
    environment_law_queries: int = 0
    outcome_enumeration_calls: int = 0
    new_draw_calls: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.model_id, "parent model"),
            (self.audit_id, "parent audit"),
            (self.frontier_id, "parent frontier"),
            (self.threshold_profile_id, "parent threshold"),
            (self.selected_candidate_id, "selected candidate"),
            (self.selected_planner_row_id, "selected planner row"),
            (
                self.upstream_verification_attestation_id,
                "upstream observation/validation verification",
            ),
        ):
            _cid(value, field)
        if type(self.evidence_role) is not ParentEvidenceRoleV2:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "parent evidence role is unregistered"
            )
        context = _context_by_id(self.parent_catalogue.context_id)
        catalogue = _canonical_public_catalogue(
            context,
            self.parent_catalogue,
            remaining_horizon=prereg.HORIZON,
        )
        if (
            type(self.parent_row_binding)
            is not observer.HeldoutObservationRowBindingV2
            or self.parent_row_binding
            != observer.observation_row_binding_v2(
                context,
                catalogue,
                self.parent_row_binding.action,
            )
            or type(self.support_epoch_chain)
            is not observer.HeldoutSupportEpochChainV2
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "parent row/catalogue binding is not canonical"
            )
        try:
            canonical_chain = (
                observer.verify_heldout_support_epoch_chain_v2(
                    context,
                    self.parent_row_binding,
                    self.support_epoch_chain.arm,
                    self.support_epoch_chain,
                )
            )
        except observer.HeldoutGraphTransitionObserverV2InvariantViolation as error:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "parent support epoch chain is invalid"
            ) from error
        old = _canonical_evidence(
            self.old_support_evidence,
            "old support evidence",
            allow_empty=False,
        )
        novel = _canonical_evidence(
            self.novel_evidence,
            "novel evidence",
            allow_empty=True,
        )
        old_descriptor_ids = tuple(
            sorted(item.descriptor.descriptor_id for item in old)
        )
        novel_descriptor_ids = tuple(
            sorted(item.descriptor.descriptor_id for item in novel)
        )
        all_observation_ids = tuple(
            observation_id
            for evidence in (*old, *novel)
            for observation_id in evidence.observation_ids
        )
        expected_reward = _expected_parent_reward(
            catalogue,
            self.parent_row_binding.action,
        )
        descriptors = tuple(
            evidence.descriptor for evidence in (*old, *novel)
        )
        if (
            canonical_chain.leaf.epoch_index != 1
            or canonical_chain.leaf.frozen_support_member_ids
            != old_descriptor_ids
            or set(old_descriptor_ids) & set(novel_descriptor_ids)
            or len(all_observation_ids) != len(set(all_observation_ids))
            or any(
                descriptor.realized_row_reward != expected_reward
                or descriptor.terminal != descriptor.failure
                for descriptor in descriptors
            )
            or self.all_recorded_novel_descriptors_complete is not True
            or self.environment_law_queries != 0
            or self.outcome_enumeration_calls != 0
            or self.new_draw_calls != 0
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "parent observation/validation evidence is incomplete or stale"
            )
        promoted = set(old_descriptor_ids) | set(novel_descriptor_ids)
        if len(promoted) > observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "promoted support exceeds the registered per-row support cap"
            )
        for descriptor in descriptors:
            try:
                observer.legal_action_catalogue_v2(
                    context,
                    descriptor.next_state,
                    1,
                )
            except (
                observer.HeldoutGraphTransitionObserverV2InvariantViolation
            ) as error:
                raise PublicNovelChildCardinalityV2InvariantViolation(
                    "recorded successor is incompatible with public topology"
                ) from error

    @property
    def context_id(self) -> str:
        return self.parent_catalogue.context_id

    @property
    def arm(self) -> str:
        return self.support_epoch_chain.arm

    @property
    def support_epoch_id(self) -> str:
        return self.support_epoch_chain.leaf.epoch_id

    @property
    def old_support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.descriptor.descriptor_id
                for item in self.old_support_evidence
            )
        )

    @property
    def novel_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.descriptor.descriptor_id for item in self.novel_evidence
            )
        )

    @property
    def promoted_support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    *self.old_support_descriptor_ids,
                    *self.novel_descriptor_ids,
                }
            )
        )

    @property
    def recorded_observation_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                observation_id
                for evidence in (
                    *self.old_support_evidence,
                    *self.novel_evidence,
                )
                for observation_id in evidence.observation_ids
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_verified_parent_observation_validation_artifact.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "upstream_verification_attestation_id": (
                self.upstream_verification_attestation_id
            ),
            "upstream_verification_attestation_semantics": (
                "IDENTITY_BINDING_SLOT_NOT_RAW_AUTHENTICITY"
            ),
            "registered_confirmatory_requirement": (
                "EXACT_TYPED_ROW_AND_CONFIDENCE_VERIFICATION_AUTHORITY"
            ),
            "evidence_role": self.evidence_role.value,
            "context_id": self.context_id,
            "parent_catalogue_id": self.parent_catalogue.catalogue_id,
            "parent_row_binding_id": (
                self.parent_row_binding.row_binding_id
            ),
            "support_epoch_chain_id": self.support_epoch_chain.chain_id,
            "support_epoch_id": self.support_epoch_id,
            "arm": self.arm,
            "old_support_evidence_ids": [
                item.evidence_id for item in self.old_support_evidence
            ],
            "novel_evidence_ids": [
                item.evidence_id for item in self.novel_evidence
            ],
            "old_support_descriptor_ids": list(
                self.old_support_descriptor_ids
            ),
            "novel_descriptor_ids": list(self.novel_descriptor_ids),
            "promoted_support_descriptor_ids": list(
                self.promoted_support_descriptor_ids
            ),
            "recorded_observation_ids": list(
                self.recorded_observation_ids
            ),
            "all_recorded_novel_descriptors_complete": True,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def parent_artifact_id(self) -> str:
        return _content_id("parent", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "parent_catalogue": self.parent_catalogue.to_document(),
            "parent_row_binding": self.parent_row_binding.to_document(),
            "support_epoch_chain": self.support_epoch_chain.to_document(),
            "old_support_evidence": [
                item.to_document() for item in self.old_support_evidence
            ],
            "novel_evidence": [
                item.to_document() for item in self.novel_evidence
            ],
            "parent_artifact_id": self.parent_artifact_id,
        }


@dataclass(frozen=True, slots=True)
class PublicH1PhysicalRowV2:
    context_id: str
    state_id: str
    catalogue_id: str
    action: tuple[int, int, int]
    remaining_horizon: int = 1

    def __post_init__(self) -> None:
        _context_by_id(self.context_id)
        _cid(self.state_id, "public H1 row state")
        _cid(self.catalogue_id, "public H1 row catalogue")
        _action(self.action)
        if self.remaining_horizon != 1:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "novel-child physical rows must be H1 rows"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_public_h1_physical_row.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state_id,
            "catalogue_id": self.catalogue_id,
            "remaining_horizon": 1,
            "action": list(self.action),
        }

    @property
    def physical_row_id(self) -> str:
        return _content_id("physical_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "physical_row_id": self.physical_row_id,
        }


def _rows_for_catalogues(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogues: Iterable[observer.HeldoutLegalActionCatalogueV2],
) -> tuple[PublicH1PhysicalRowV2, ...]:
    rows = {
        PublicH1PhysicalRowV2(
            context.context_id,
            catalogue.state.state_id,
            catalogue.catalogue_id,
            action,
        )
        for catalogue in catalogues
        for action in catalogue.actions
    }
    return tuple(sorted(rows, key=lambda item: item.physical_row_id))


def _canonical_rows(
    rows: tuple[PublicH1PhysicalRowV2, ...],
    field: str,
    *,
    allow_empty: bool = True,
) -> tuple[PublicH1PhysicalRowV2, ...]:
    if (
        type(rows) is not tuple
        or (not allow_empty and not rows)
        or any(type(item) is not PublicH1PhysicalRowV2 for item in rows)
        or tuple(item.physical_row_id for item in rows)
        != tuple(sorted({item.physical_row_id for item in rows}))
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            f"{field} must be physical-row-ID sorted and distinct"
        )
    return rows


@dataclass(frozen=True, slots=True)
class CurrentPublicH1RowClosureV2:
    """All currently materialized H1 rows for complete public catalogues."""

    context_id: str
    model_id: str
    catalogues: tuple[observer.HeldoutLegalActionCatalogueV2, ...]
    rows: tuple[PublicH1PhysicalRowV2, ...]
    complete_for_registered_states: bool = True

    def __post_init__(self) -> None:
        context = _context_by_id(self.context_id)
        _cid(self.model_id, "current closure model")
        catalogues = _canonical_catalogues(context, self.catalogues)
        rows = _canonical_rows(self.rows, "current H1 closure rows")
        expected = _rows_for_catalogues(context, catalogues)
        if (
            rows != expected
            or self.complete_for_registered_states is not True
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "current H1 closure omits or invents a public legal row"
            )

    @property
    def physical_row_ids(self) -> tuple[str, ...]:
        return tuple(item.physical_row_id for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_current_public_h1_row_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "catalogue_ids": [
                item.catalogue_id for item in self.catalogues
            ],
            "physical_row_ids": list(self.physical_row_ids),
            "complete_for_registered_states": True,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogues": [
                item.to_document() for item in self.catalogues
            ],
            "rows": [item.to_document() for item in self.rows],
            "closure_id": self.closure_id,
        }


def freeze_current_public_h1_row_closure_v2(
    *,
    context: prereg.HeldoutPublicGraphContextV2,
    model_id: str,
    catalogues: tuple[observer.HeldoutLegalActionCatalogueV2, ...],
) -> CurrentPublicH1RowClosureV2:
    """Freeze a row-complete public closure without accepting a row mapping."""

    registered = _registered_context(context)
    _cid(model_id, "current closure model")
    canonical = _canonical_catalogues(registered, catalogues)
    return CurrentPublicH1RowClosureV2(
        registered.context_id,
        model_id,
        canonical,
        _rows_for_catalogues(registered, canonical),
    )


def cumulative_round_draw_upper_v2(
    round_index: int,
    cumulative_rows: tuple[PublicH1PhysicalRowV2, ...],
) -> int:
    """Exact cumulative formula ``2048*r + 8256*|union rows|``."""

    if (
        type(round_index) is not int
        or not 1 <= round_index <= MAX_ROUNDS
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "cumulative draw formula requires round one or two"
        )
    rows = _canonical_rows(
        cumulative_rows,
        "cumulative acquired rows",
    )
    if len(rows) > MAX_CUMULATIVE_CHILD_ROWS:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "cumulative child-row union exceeds nineteen"
        )
    result = (
        PROMOTED_PARENT_DRAWS_PER_ROUND * round_index
        + CHILD_ROW_DRAWS * len(rows)
    )
    if result > MAX_CUMULATIVE_DRAW_UPPER:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "cumulative draw formula exceeds the registered hard cap"
        )
    return result


@dataclass(frozen=True, slots=True)
class PublicNovelChildCardinalityEvidenceV2:
    """Preselection full-row-list cost evidence with no gain dependency."""

    logical_occurrence_id: str
    context_id: str
    arm: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    parent_artifact_id: str
    parent_row_binding_id: str
    parent_support_epoch_id: str
    current_closure_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    round_index: int
    previous_evidence_id: str | None
    old_support_descriptor_ids: tuple[str, ...]
    novel_descriptor_ids: tuple[str, ...]
    promoted_support_descriptor_ids: tuple[str, ...]
    induced_child_catalogues: tuple[
        observer.HeldoutLegalActionCatalogueV2, ...
    ]
    induced_rows: tuple[PublicH1PhysicalRowV2, ...]
    already_present_rows: tuple[PublicH1PhysicalRowV2, ...]
    rows_to_acquire: tuple[PublicH1PhysicalRowV2, ...]
    cumulative_rows: tuple[PublicH1PhysicalRowV2, ...]
    new_child_row_count: int
    cumulative_child_row_count: int
    exact_round_draw_upper: int
    cumulative_draw_upper: int
    public_catalogue_queries: int
    environment_law_queries: int = 0
    outcome_enumeration_calls: int = 0
    new_draw_calls: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_occurrence_id, "authority logical occurrence"),
            (self.context_id, "authority context"),
            (self.model_id, "authority model"),
            (self.audit_id, "authority audit"),
            (self.frontier_id, "authority frontier"),
            (self.threshold_profile_id, "authority threshold"),
            (self.parent_artifact_id, "authority parent artifact"),
            (
                self.parent_row_binding_id,
                "authority parent row binding",
            ),
            (
                self.parent_support_epoch_id,
                "authority parent support epoch",
            ),
            (self.current_closure_id, "authority current closure"),
            (self.selected_candidate_id, "authority selected candidate"),
            (self.selected_planner_row_id, "authority planner row"),
        ):
            _cid(value, field)
        _context_by_id(self.context_id)
        if type(self.arm) is not str or self.arm not in prereg.ARM_ORDER:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "authority arm is unregistered"
            )
        if self.round_index == 1:
            if self.previous_evidence_id is not None:
                raise PublicNovelChildCardinalityV2InvariantViolation(
                    "round one cannot inherit prior cardinality evidence"
                )
        elif self.round_index == 2:
            _cid(self.previous_evidence_id, "previous cardinality evidence")
        else:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "authority round must be one or two"
            )
        old = tuple(
            _cid(item, "old support descriptor")
            for item in self.old_support_descriptor_ids
        )
        novel = tuple(
            _cid(item, "novel descriptor")
            for item in self.novel_descriptor_ids
        )
        promoted = tuple(
            _cid(item, "promoted support descriptor")
            for item in self.promoted_support_descriptor_ids
        )
        if (
            not old
            or not novel
            or old != tuple(sorted(set(old)))
            or novel != tuple(sorted(set(novel)))
            or set(old) & set(novel)
            or promoted != tuple(sorted({*old, *novel}))
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "promotion support is not old support union all novel descriptors"
            )
        context = _context_by_id(self.context_id)
        catalogues = _canonical_catalogues(
            context,
            self.induced_child_catalogues,
        )
        induced = _canonical_rows(
            self.induced_rows,
            "induced child rows",
        )
        present = _canonical_rows(
            self.already_present_rows,
            "already-present child rows",
        )
        acquire = _canonical_rows(
            self.rows_to_acquire,
            "rows to acquire",
        )
        cumulative = _canonical_rows(
            self.cumulative_rows,
            "cumulative acquired rows",
        )
        expected_induced = _rows_for_catalogues(context, catalogues)
        if (
            induced != expected_induced
            or set(item.physical_row_id for item in present)
            & set(item.physical_row_id for item in acquire)
            or tuple(
                sorted(
                    {
                        *(
                            item.physical_row_id for item in present
                        ),
                        *(
                            item.physical_row_id for item in acquire
                        ),
                    }
                )
            )
            != tuple(item.physical_row_id for item in induced)
            or type(self.new_child_row_count) is not int
            or self.new_child_row_count != len(acquire)
            or type(self.cumulative_child_row_count) is not int
            or self.cumulative_child_row_count != len(cumulative)
            or self.cumulative_child_row_count
            > MAX_CUMULATIVE_CHILD_ROWS
            or type(self.exact_round_draw_upper) is not int
            or self.exact_round_draw_upper
            != (
                PROMOTED_PARENT_DRAWS_PER_ROUND
                + CHILD_ROW_DRAWS * len(acquire)
            )
            or self.cumulative_draw_upper
            != cumulative_round_draw_upper_v2(
                self.round_index,
                cumulative,
            )
            or type(self.public_catalogue_queries) is not int
            or self.public_catalogue_queries
            != len(self.induced_child_catalogues)
            or self.environment_law_queries != 0
            or self.outcome_enumeration_calls != 0
            or self.new_draw_calls != 0
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "derived row partition, exact count, or draw upper is invalid"
            )

    @property
    def cumulative_row_ids(self) -> tuple[str, ...]:
        return tuple(item.physical_row_id for item in self.cumulative_rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_public_novel_child_cardinality_evidence.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "parent_artifact_id": self.parent_artifact_id,
            "parent_row_binding_id": self.parent_row_binding_id,
            "parent_support_epoch_id": self.parent_support_epoch_id,
            "current_closure_id": self.current_closure_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "round_index": self.round_index,
            "previous_evidence": (
                {"kind": "ROOT"}
                if self.previous_evidence_id is None
                else {
                    "kind": "PREVIOUS_ROUND",
                    "evidence_id": self.previous_evidence_id,
                }
            ),
            "old_support_descriptor_ids": list(
                self.old_support_descriptor_ids
            ),
            "novel_descriptor_ids": list(self.novel_descriptor_ids),
            "promoted_support_descriptor_ids": list(
                self.promoted_support_descriptor_ids
            ),
            "induced_child_catalogue_ids": [
                item.catalogue_id for item in self.induced_child_catalogues
            ],
            "induced_row_ids": [
                item.physical_row_id for item in self.induced_rows
            ],
            "already_present_row_ids": [
                item.physical_row_id for item in self.already_present_rows
            ],
            "rows_to_acquire_ids": [
                item.physical_row_id for item in self.rows_to_acquire
            ],
            "cumulative_row_ids": list(self.cumulative_row_ids),
            "new_child_row_count": self.new_child_row_count,
            "cumulative_child_row_count": (
                self.cumulative_child_row_count
            ),
            "round_draw_formula": "2048+8256*new_child_row_count",
            "exact_round_draw_upper": self.exact_round_draw_upper,
            "cumulative_draw_formula": (
                "2048*round_index+8256*cardinality(union_child_rows)"
            ),
            "cumulative_draw_upper": self.cumulative_draw_upper,
            "maximum_rounds": MAX_ROUNDS,
            "maximum_cumulative_child_rows": (
                MAX_CUMULATIVE_CHILD_ROWS
            ),
            "maximum_cumulative_draw_upper": (
                MAX_CUMULATIVE_DRAW_UPPER
            ),
            "public_catalogue_queries": self.public_catalogue_queries,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
            "caller_supplied_mapping": False,
            "caller_supplied_count": False,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "induced_child_catalogues": [
                item.to_document()
                for item in self.induced_child_catalogues
            ],
            "induced_rows": [
                item.to_document() for item in self.induced_rows
            ],
            "already_present_rows": [
                item.to_document() for item in self.already_present_rows
            ],
            "rows_to_acquire": [
                item.to_document() for item in self.rows_to_acquire
            ],
            "cumulative_rows": [
                item.to_document() for item in self.cumulative_rows
            ],
            "evidence_id": self.evidence_id,
        }


@dataclass(frozen=True, slots=True)
class PublicNovelChildCardinalityAuthorityV2:
    """Postselection binding of one positive gain to preselection evidence."""

    cardinality_evidence: PublicNovelChildCardinalityEvidenceV2
    selector_gain: selector.OneRowCounterfactualGainV2

    def __post_init__(self) -> None:
        if (
            type(self.cardinality_evidence)
            is not PublicNovelChildCardinalityEvidenceV2
            or type(self.selector_gain)
            is not selector.OneRowCounterfactualGainV2
            or not self.selector_gain.eligible
            or self.selector_gain.gain <= 0
            or self.selector_gain.cardinality_evidence_id
            != self.cardinality_evidence.evidence_id
            or self.selector_gain.model_id
            != self.cardinality_evidence.model_id
            or self.selector_gain.audit_id
            != self.cardinality_evidence.audit_id
            or self.selector_gain.frontier_id
            != self.cardinality_evidence.frontier_id
            or self.selector_gain.threshold_profile_id
            != self.cardinality_evidence.threshold_profile_id
            or self.selector_gain.support_epoch_id
            != self.cardinality_evidence.parent_support_epoch_id
            or self.selector_gain.candidate_id
            != self.cardinality_evidence.selected_candidate_id
            or self.selector_gain.planner_row_id
            != self.cardinality_evidence.selected_planner_row_id
            or self.selector_gain.exact_draw_upper
            != self.cardinality_evidence.exact_round_draw_upper
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "postselection authority does not bind one positive gain to "
                "the complete preselection row-list evidence"
            )

    @property
    def selector_counterfactual_id(self) -> str:
        return self.selector_gain.counterfactual_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_public_novel_child_cardinality_authority.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cardinality_evidence_id": (
                self.cardinality_evidence.evidence_id
            ),
            "selector_counterfactual_id": (
                self.selector_gain.counterfactual_id
            ),
            "round_index": self.cardinality_evidence.round_index,
            "previous_evidence_id": (
                self.cardinality_evidence.previous_evidence_id
            ),
            "parent_row_binding_id": (
                self.cardinality_evidence.parent_row_binding_id
            ),
            "parent_support_epoch_id": (
                self.cardinality_evidence.parent_support_epoch_id
            ),
            "selected_candidate_id": (
                self.cardinality_evidence.selected_candidate_id
            ),
            "positive_gain_required": True,
            "full_row_list_bound_before_selection": True,
        }

    @property
    def authority_id(self) -> str:
        return _content_id("authority", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cardinality_evidence": (
                self.cardinality_evidence.to_document()
            ),
            "selector_gain": self.selector_gain.to_document(),
            "authority_id": self.authority_id,
        }

    @property
    def logical_occurrence_id(self) -> str:
        return self.cardinality_evidence.logical_occurrence_id

    @property
    def context_id(self) -> str:
        return self.cardinality_evidence.context_id

    @property
    def arm(self) -> str:
        return self.cardinality_evidence.arm

    @property
    def model_id(self) -> str:
        return self.cardinality_evidence.model_id

    @property
    def parent_artifact_id(self) -> str:
        return self.cardinality_evidence.parent_artifact_id

    @property
    def parent_row_binding_id(self) -> str:
        return self.cardinality_evidence.parent_row_binding_id

    @property
    def parent_support_epoch_id(self) -> str:
        return self.cardinality_evidence.parent_support_epoch_id

    @property
    def current_closure_id(self) -> str:
        return self.cardinality_evidence.current_closure_id

    @property
    def selected_candidate_id(self) -> str:
        return self.cardinality_evidence.selected_candidate_id

    @property
    def selected_planner_row_id(self) -> str:
        return self.cardinality_evidence.selected_planner_row_id

    @property
    def round_index(self) -> int:
        return self.cardinality_evidence.round_index

    @property
    def previous_evidence_id(self) -> str | None:
        return self.cardinality_evidence.previous_evidence_id

    @property
    def old_support_descriptor_ids(self) -> tuple[str, ...]:
        return self.cardinality_evidence.old_support_descriptor_ids

    @property
    def novel_descriptor_ids(self) -> tuple[str, ...]:
        return self.cardinality_evidence.novel_descriptor_ids

    @property
    def promoted_support_descriptor_ids(self) -> tuple[str, ...]:
        return self.cardinality_evidence.promoted_support_descriptor_ids

    @property
    def induced_child_catalogues(
        self,
    ) -> tuple[observer.HeldoutLegalActionCatalogueV2, ...]:
        return self.cardinality_evidence.induced_child_catalogues

    @property
    def induced_rows(self) -> tuple[PublicH1PhysicalRowV2, ...]:
        return self.cardinality_evidence.induced_rows

    @property
    def already_present_rows(self) -> tuple[PublicH1PhysicalRowV2, ...]:
        return self.cardinality_evidence.already_present_rows

    @property
    def rows_to_acquire(self) -> tuple[PublicH1PhysicalRowV2, ...]:
        return self.cardinality_evidence.rows_to_acquire

    @property
    def cumulative_rows(self) -> tuple[PublicH1PhysicalRowV2, ...]:
        return self.cardinality_evidence.cumulative_rows

    @property
    def cumulative_row_ids(self) -> tuple[str, ...]:
        return self.cardinality_evidence.cumulative_row_ids

    @property
    def new_child_row_count(self) -> int:
        return self.cardinality_evidence.new_child_row_count

    @property
    def cumulative_child_row_count(self) -> int:
        return self.cardinality_evidence.cumulative_child_row_count

    @property
    def exact_round_draw_upper(self) -> int:
        return self.cardinality_evidence.exact_round_draw_upper

    @property
    def cumulative_draw_upper(self) -> int:
        return self.cardinality_evidence.cumulative_draw_upper

    @property
    def public_catalogue_queries(self) -> int:
        return self.cardinality_evidence.public_catalogue_queries

    @property
    def environment_law_queries(self) -> int:
        return self.cardinality_evidence.environment_law_queries

    @property
    def outcome_enumeration_calls(self) -> int:
        return self.cardinality_evidence.outcome_enumeration_calls

    @property
    def new_draw_calls(self) -> int:
        return self.cardinality_evidence.new_draw_calls


def _induced_catalogues_from_parent(
    context: prereg.HeldoutPublicGraphContextV2,
    parent: VerifiedParentObservationValidationArtifactV2,
) -> tuple[observer.HeldoutLegalActionCatalogueV2, ...]:
    catalogues = {
        catalogue.catalogue_id: catalogue
        for evidence in parent.novel_evidence
        if not evidence.descriptor.failure
        for catalogue in (
            observer.legal_action_catalogue_v2(
                context,
                evidence.descriptor.next_state,
                1,
            ),
        )
    }
    return tuple(catalogues[key] for key in sorted(catalogues))


def derive_public_novel_child_cardinality_evidence_v2(
    *,
    context: prereg.HeldoutPublicGraphContextV2,
    parent: VerifiedParentObservationValidationArtifactV2,
    current_h1_closure: CurrentPublicH1RowClosureV2,
    previous_evidence: PublicNovelChildCardinalityEvidenceV2 | None = None,
) -> PublicNovelChildCardinalityEvidenceV2:
    """Precompute exact rows/cost before gain, base, score, or rank exists."""

    registered = _registered_context(context)
    if (
        type(parent)
        is not VerifiedParentObservationValidationArtifactV2
        or parent.context_id != registered.context_id
        or type(current_h1_closure) is not CurrentPublicH1RowClosureV2
        or current_h1_closure.context_id != registered.context_id
        or current_h1_closure.model_id != parent.model_id
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "cardinality inputs do not bind one current parent/model/context"
        )
    if not parent.novel_evidence:
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "preselection cardinality requires nonempty novel evidence"
        )
    induced_catalogues = _induced_catalogues_from_parent(
        registered,
        parent,
    )
    induced_rows = _rows_for_catalogues(
        registered,
        induced_catalogues,
    )
    present_ids = set(current_h1_closure.physical_row_ids)
    already_present = tuple(
        item
        for item in induced_rows
        if item.physical_row_id in present_ids
    )
    rows_to_acquire = tuple(
        item
        for item in induced_rows
        if item.physical_row_id not in present_ids
    )
    round_draw_upper = (
        PROMOTED_PARENT_DRAWS_PER_ROUND
        + CHILD_ROW_DRAWS * len(rows_to_acquire)
    )
    if previous_evidence is None:
        round_index = 1
        previous_id = None
        cumulative_rows = rows_to_acquire
    else:
        if (
            type(previous_evidence)
            is not PublicNovelChildCardinalityEvidenceV2
            or previous_evidence.round_index != 1
            or previous_evidence.logical_occurrence_id
            != parent.logical_occurrence_id
            or previous_evidence.context_id != registered.context_id
            or previous_evidence.arm != parent.arm
            or previous_evidence.model_id == parent.model_id
            or previous_evidence.parent_row_binding_id
            == parent.parent_row_binding.row_binding_id
            or previous_evidence.parent_support_epoch_id
            == parent.support_epoch_id
            or previous_evidence.selected_candidate_id
            == parent.selected_candidate_id
            or not set(previous_evidence.cumulative_row_ids).issubset(
                present_ids
            )
        ):
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "round two did not advance one occurrence/model/closure"
            )
        prior_by_id = {
            item.physical_row_id: item
            for item in previous_evidence.cumulative_rows
        }
        if set(prior_by_id) & {
            item.physical_row_id for item in rows_to_acquire
        }:
            raise PublicNovelChildCardinalityV2InvariantViolation(
                "round two attempted to reacquire a prior child row"
            )
        cumulative_by_id = {
            **prior_by_id,
            **{
                item.physical_row_id: item
                for item in rows_to_acquire
            },
        }
        cumulative_rows = tuple(
            cumulative_by_id[key] for key in sorted(cumulative_by_id)
        )
        round_index = 2
        previous_id = previous_evidence.evidence_id
    cumulative_upper = cumulative_round_draw_upper_v2(
        round_index,
        cumulative_rows,
    )
    return PublicNovelChildCardinalityEvidenceV2(
        parent.logical_occurrence_id,
        registered.context_id,
        parent.arm,
        parent.model_id,
        parent.audit_id,
        parent.frontier_id,
        parent.threshold_profile_id,
        parent.parent_artifact_id,
        parent.parent_row_binding.row_binding_id,
        parent.support_epoch_id,
        current_h1_closure.closure_id,
        parent.selected_candidate_id,
        parent.selected_planner_row_id,
        round_index,
        previous_id,
        parent.old_support_descriptor_ids,
        parent.novel_descriptor_ids,
        parent.promoted_support_descriptor_ids,
        induced_catalogues,
        induced_rows,
        already_present,
        rows_to_acquire,
        cumulative_rows,
        len(rows_to_acquire),
        len(cumulative_rows),
        round_draw_upper,
        cumulative_upper,
        len(induced_catalogues),
    )


def authorize_public_novel_child_rows_v2(
    *,
    parent: VerifiedParentObservationValidationArtifactV2,
    cardinality_evidence: PublicNovelChildCardinalityEvidenceV2,
    selector_gain: selector.OneRowCounterfactualGainV2,
) -> PublicNovelChildCardinalityAuthorityV2:
    """Freeze postselection authorization after evidence-first ranking."""

    if (
        type(parent)
        is not VerifiedParentObservationValidationArtifactV2
        or type(cardinality_evidence)
        is not PublicNovelChildCardinalityEvidenceV2
        or parent.parent_artifact_id
        != cardinality_evidence.parent_artifact_id
        or parent.parent_row_binding.row_binding_id
        != cardinality_evidence.parent_row_binding_id
        or parent.support_epoch_id
        != cardinality_evidence.parent_support_epoch_id
        or parent.selected_candidate_id
        != cardinality_evidence.selected_candidate_id
        or parent.selected_planner_row_id
        != cardinality_evidence.selected_planner_row_id
        or not parent.novel_evidence
    ):
        raise PublicNovelChildCardinalityV2InvariantViolation(
            "postselection authorization uses stale parent/cardinality evidence"
        )
    return PublicNovelChildCardinalityAuthorityV2(
        cardinality_evidence,
        selector_gain,
    )


__all__ = [
    "CHILD_DISCOVERY_DRAWS",
    "CHILD_ROW_DRAWS",
    "CHILD_VALIDATION_DRAWS",
    "CurrentPublicH1RowClosureV2",
    "MAX_CUMULATIVE_CHILD_ROWS",
    "MAX_CUMULATIVE_DRAW_UPPER",
    "MAX_ROUNDS",
    "PROFILE_KEY",
    "PROMOTED_PARENT_DRAWS_PER_ROUND",
    "ParentEvidenceRoleV2",
    "PublicH1PhysicalRowV2",
    "PublicNovelChildCardinalityAuthorityV2",
    "PublicNovelChildCardinalityEvidenceV2",
    "PublicNovelChildCardinalityV2InvariantViolation",
    "RecordedDescriptorEvidenceV2",
    "RecordedTransitionDescriptorV2",
    "VerifiedParentObservationValidationArtifactV2",
    "authorize_public_novel_child_rows_v2",
    "cumulative_round_draw_upper_v2",
    "derive_public_novel_child_cardinality_evidence_v2",
    "freeze_current_public_h1_row_closure_v2",
]
