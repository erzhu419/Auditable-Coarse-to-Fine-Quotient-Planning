"""Unified exact-hit or observation-driven world-model synthesis router.

The router starts from any immutable catalogue snapshot, including an empty
bootstrap.  Exact structural hits execute only one fresh H=2 abstract plan.
Misses for the two registered positive held-out families invoke their existing
observation-driven constructors, permit local checkpoint restoration only
after an abstract proof failure, promote the resulting query-neutral model to
a new catalogue epoch, and then execute one fresh abstract plan.  The nearby
K6-minus-edge negative control has no certifiable constructor and remains a
typed no-access result; no neighbouring model is transferred.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_catalogue_query_router_v1 as router_v1
from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as w5_source_v1
from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as k6_source_v1
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as k6_reuse_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as w5_reuse_v1
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp import construction_k7_adaptive_accounting_phase_v1 as accounting_phase
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.140"
PROFILE_KEY = "construction_k7_observation_driven_world_model_synthesis_v1"

DISPATCH_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN
PROMOTION_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN
UNSUPPORTED_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {DISPATCH_DOMAIN, PROMOTION_DOMAIN, UNSUPPORTED_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-driven synthesis domains are not central")

_CONSTRUCTOR_BY_CONTEXT = {
    "opaque_graph_w5_v0": "W5_CHECKPOINT_OVERLAY_V1",
    "opaque_graph_k6_v0": "K6_CHECKPOINT_OVERLAY_V1",
}
_FAMILY_ORDER = {"W5": 0, "K6": 1}

_DISPATCH_ISSUER = object()
_PROMOTION_ISSUER = object()
_UNSUPPORTED_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7ObservationDrivenWorldModelSynthesisV1Error(ValueError):
    """The structural dispatch, construction, promotion, or reuse changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDrivenWorldModelSynthesisV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenWorldModelSynthesisV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _logical(role: str, parent: str) -> str:
    return hashlib.sha256(f"{PROFILE_KEY}:{role}:{parent}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ObservationDrivenSynthesisDispatchV1:
    _issuer: InitVar[object]
    initial_catalogue_id: str
    initial_route_result_id: str
    context_key: str
    context_id: str
    topology_id: str
    selection_outcome: str
    dispatch_outcome: str
    constructor_key: str | None
    _dispatch_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DISPATCH_ISSUER:
            _fail("synthesis dispatch is caller-minted")
        for value, label in (
            (self.initial_catalogue_id, "initial catalogue"),
            (self.initial_route_result_id, "initial route"),
            (self.context_id, "dispatch context"),
            (self.topology_id, "dispatch topology"),
        ):
            _cid(value, label)
        expected_constructor = _CONSTRUCTOR_BY_CONTEXT.get(self.context_key)
        exact = self.selection_outcome == "EXACT_MODEL_MATCH"
        construct = self.dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL"
        unsupported = self.dispatch_outcome == "NO_CERTIFIABLE_CONSTRUCTOR"
        reuse = self.dispatch_outcome == "REUSE_EXACT_MODEL"
        if (
            type(self.context_key) is not str
            or not self.context_key
            or not (construct or unsupported or reuse)
            or (exact != reuse)
            or (construct != (not exact and expected_constructor is not None))
            or (unsupported != (not exact and expected_constructor is None))
            or self.constructor_key != (expected_constructor if construct else None)
        ):
            _fail("synthesis dispatch semantics changed")
        object.__setattr__(
            self, "_dispatch_id", content_id(DISPATCH_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_dispatch.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "initial_model_catalogue_id": self.initial_catalogue_id,
            "initial_catalogue_query_result_id": self.initial_route_result_id,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "selection_outcome": self.selection_outcome,
            "dispatch_outcome": self.dispatch_outcome,
            "constructor_key": self.constructor_key,
            "dispatch_uses_only_public_structural_identity": True,
            "nearby_model_transfer_allowed": False,
            "ground_access_authorized_by_dispatch": False,
            "constructor_must_observe_failed_certificate_before_local_recovery": True,
            "fixed_human_constructor_registry": True,
            "automatic_coordinate_primitive_invention_claimed": False,
        }

    @property
    def dispatch_id(self) -> str:
        current = content_id(DISPATCH_DOMAIN, self._payload())
        if current != self._dispatch_id:
            _fail("synthesis dispatch changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "synthesis_dispatch_id": self.dispatch_id}


@dataclass(frozen=True, slots=True)
class ObservationDrivenModelPromotionV1:
    _issuer: InitVar[object]
    dispatch: ObservationDrivenSynthesisDispatchV1
    family_key: str
    source_result_id: str
    base_audit_id: str
    final_overlay_id: str
    final_audit_id: str
    changed_row_count: int
    preserved_row_count: int
    incremental_ground_draw_count: int
    reuse_result_id: str
    entry: catalogue_v1.HeldoutReusableModelCatalogueEntryV1
    initial_catalogue_id: str
    promoted_catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1
    _promotion_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        expected = {
            "W5": (2, 6, 4_096),
            "K6": (1, 19, 8_192),
        }.get(self.family_key)
        if (
            _issuer is not _PROMOTION_ISSUER
            or type(self.dispatch) is not ObservationDrivenSynthesisDispatchV1
            or self.dispatch.dispatch_outcome != "CONSTRUCT_REGISTERED_MODEL"
            or expected is None
            or (
                self.changed_row_count,
                self.preserved_row_count,
                self.incremental_ground_draw_count,
            )
            != expected
            or type(self.entry)
            is not catalogue_v1.HeldoutReusableModelCatalogueEntryV1
            or self.entry.family_key != self.family_key
            or self.entry.source_result_id != self.source_result_id
            or self.entry.source_overlay_id != self.final_overlay_id
            or self.entry.certified_audit_id != self.final_audit_id
            or self.entry.source_reuse_result_id != self.reuse_result_id
            or type(self.promoted_catalogue)
            is not catalogue_v1.HeldoutReusableModelCatalogueV1
            or self.promoted_catalogue.catalogue_id == self.initial_catalogue_id
            or self.entry not in self.promoted_catalogue.entries
        ):
            _fail("world-model promotion crossed its constructor result")
        for value, label in (
            (self.source_result_id, "constructed source"),
            (self.base_audit_id, "failed base audit"),
            (self.final_overlay_id, "promoted overlay"),
            (self.final_audit_id, "certified final audit"),
            (self.reuse_result_id, "verified reuse result"),
            (self.initial_catalogue_id, "promotion predecessor catalogue"),
        ):
            _cid(value, label)
        object.__setattr__(
            self, "_promotion_id", content_id(PROMOTION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_promotion.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "synthesis_dispatch_id": self.dispatch.dispatch_id,
            "family_key": self.family_key,
            "source_recertification_result_id": self.source_result_id,
            "source_base_audit_id": self.base_audit_id,
            "source_base_audit_status": "FAILED_PROOF_FRONTIER",
            "source_final_overlay_id": self.final_overlay_id,
            "source_final_audit_id": self.final_audit_id,
            "source_final_audit_status": "CERTIFIED",
            "changed_row_count": self.changed_row_count,
            "preserved_row_count": self.preserved_row_count,
            "incremental_local_ground_draw_count": self.incremental_ground_draw_count,
            "source_reuse_result_id": self.reuse_result_id,
            "promoted_model_catalogue_entry_id": self.entry.entry_id,
            "initial_model_catalogue_id": self.initial_catalogue_id,
            "promoted_model_catalogue_id": self.promoted_catalogue.catalogue_id,
            "local_ground_triggered_only_after_failed_certificate": True,
            "only_failed_frontier_distinctions_restored": True,
            "immutable_query_neutral_model_promoted": True,
            "full_target_checkpoint_closure_built": False,
            "evaluation_exact_kernel_calls": 0,
            "ground_solver_invocations": 0,
        }

    @property
    def promotion_id(self) -> str:
        current = content_id(PROMOTION_DOMAIN, self._payload())
        if current != self._promotion_id:
            _fail("world-model promotion changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_entry": self.entry.to_document(),
            "promoted_catalogue": self.promoted_catalogue.to_document(),
            "synthesis_promotion_id": self.promotion_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationDrivenSynthesisUnsupportedV1:
    _issuer: InitVar[object]
    dispatch: ObservationDrivenSynthesisDispatchV1
    _unsupported_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _UNSUPPORTED_ISSUER
            or type(self.dispatch) is not ObservationDrivenSynthesisDispatchV1
            or self.dispatch.dispatch_outcome != "NO_CERTIFIABLE_CONSTRUCTOR"
        ):
            _fail("unsupported synthesis closure is invalid")
        object.__setattr__(
            self,
            "_unsupported_id",
            content_id(UNSUPPORTED_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_unsupported.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "synthesis_dispatch_id": self.dispatch.dispatch_id,
            "context_id": self.dispatch.context_id,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "NO_CERTIFIABLE_CONSTRUCTOR_REGISTERED",
            "ground_access_count": 0,
            "observer_call_count": 0,
            "abstract_planner_invocations": 0,
            "nearby_model_transfer_attempted": False,
            "fallback_executed_here": False,
            "infeasibility_certified": False,
        }

    @property
    def unsupported_id(self) -> str:
        current = content_id(UNSUPPORTED_DOMAIN, self._payload())
        if current != self._unsupported_id:
            _fail("unsupported synthesis closure changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "unsupported_synthesis_id": self.unsupported_id}


@dataclass(frozen=True, slots=True)
class ObservationDrivenWorldModelSynthesisResultV1:
    _issuer: InitVar[object]
    initial_route: router_v1.HeldoutCatalogueQueryResultV1
    dispatch: ObservationDrivenSynthesisDispatchV1
    promotion: ObservationDrivenModelPromotionV1 | None
    unsupported: ObservationDrivenSynthesisUnsupportedV1 | None
    final_catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1
    final_route: router_v1.HeldoutCatalogueQueryResultV1 | None
    reuse_result_document: dict[str, Any] | None = field(repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        reused = self.dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
        constructed = self.dispatch.dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL"
        unsupported = self.dispatch.dispatch_outcome == "NO_CERTIFIABLE_CONSTRUCTOR"
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.initial_route) is not router_v1.HeldoutCatalogueQueryResultV1
            or type(self.dispatch) is not ObservationDrivenSynthesisDispatchV1
            or self.initial_route.result_id != self.dispatch.initial_route_result_id
            or type(self.final_catalogue)
            is not catalogue_v1.HeldoutReusableModelCatalogueV1
            or (reused and (self.promotion is not None or self.unsupported is not None or self.final_route != self.initial_route or self.reuse_result_document is not None))
            or (constructed and (type(self.promotion) is not ObservationDrivenModelPromotionV1 or self.unsupported is not None or type(self.final_route) is not router_v1.HeldoutCatalogueQueryResultV1 or type(self.reuse_result_document) is not dict))
            or (unsupported and (self.promotion is not None or type(self.unsupported) is not ObservationDrivenSynthesisUnsupportedV1 or self.final_route is not None or self.reuse_result_document is not None))
        ):
            _fail("world-model synthesis result branches changed")
        if constructed:
            assert self.promotion is not None and self.final_route is not None
            if (
                self.promotion.promoted_catalogue != self.final_catalogue
                or self.final_route.selection.catalogue_id
                != self.final_catalogue.catalogue_id
                or self.final_route.plan is None
            ):
                _fail("constructed model was not reused by the final route")
        object.__setattr__(
            self, "_result_id", content_id(RESULT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        constructed = self.promotion is not None
        reused = self.dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "initial_catalogue_query_result_id": self.initial_route.result_id,
            "synthesis_dispatch_id": self.dispatch.dispatch_id,
            "synthesis_promotion_id": None if self.promotion is None else self.promotion.promotion_id,
            "unsupported_synthesis_id": None if self.unsupported is None else self.unsupported.unsupported_id,
            "final_model_catalogue_id": self.final_catalogue.catalogue_id,
            "final_catalogue_query_result_id": None if self.final_route is None else self.final_route.result_id,
            "result_outcome": (
                "EXISTING_MODEL_REUSED"
                if reused
                else "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"
                if constructed
                else "NO_CERTIFIABLE_CONSTRUCTOR"
            ),
            "model_construction_executed": constructed,
            "fresh_postconstruction_ground_draw_count": 0,
            "fresh_postconstruction_observer_call_count": 0,
            "fresh_postconstruction_abstract_planner_invocations": (
                1 if self.final_route is not None else 0
            ),
            "multi_step_plan_mainly_completed_in_abstract_model": self.final_route is not None,
            "ground_distinctions_restored_only_after_certificate_failure": constructed,
            "fixed_human_constructor_registry": True,
            "automatic_coordinate_primitive_invention_claimed": False,
            "broad_cross_domain_generalization_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("world-model synthesis result changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "initial_route": self.initial_route.to_document(),
            "dispatch": self.dispatch.to_document(),
            "promotion": None if self.promotion is None else self.promotion.to_document(),
            "unsupported": None if self.unsupported is None else self.unsupported.to_document(),
            "final_catalogue": self.final_catalogue.to_document(),
            "final_route": None if self.final_route is None else self.final_route.to_document(),
            "reuse_result": self.reuse_result_document,
            "world_model_synthesis_result_id": self.result_id,
        }


def _promoted_snapshot(
    initial: catalogue_v1.HeldoutReusableModelCatalogueV1,
    entry: catalogue_v1.HeldoutReusableModelCatalogueEntryV1,
) -> catalogue_v1.HeldoutReusableModelCatalogueV1:
    entries = tuple(
        sorted((*initial.entries, entry), key=lambda item: _FAMILY_ORDER[item.family_key])
    )
    if len({item.family_key for item in entries}) != len(entries):
        _fail("synthesis attempted duplicate family promotion")
    return catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(entries)


def run_observation_driven_world_model_synthesis_v1(
    catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1,
    context: observer_v1.PublicGraphContextV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
    selected_reuse_result_bytes: bytes | None,
) -> ObservationDrivenWorldModelSynthesisResultV1:
    """Reuse, synthesize, or safely reject one registered structural query."""

    catalogue_v1.verify_heldout_reusable_model_catalogue_v1(catalogue)
    with accounting_phase.adaptive_accounting_phase_v1(
        accounting_phase.AdaptiveAccountingPhaseV1.COMMON_PREFIX
    ):
        initial_route = router_v1.run_heldout_catalogue_query_v1(
            catalogue,
            context,
            logical_occurrence_id=_cid(logical_occurrence_id, "logical occurrence"),
            occurrence_ordinal=occurrence_ordinal,
            selected_reuse_result_bytes=selected_reuse_result_bytes,
        )
    constructor = _CONSTRUCTOR_BY_CONTEXT.get(context.context_key)
    dispatch_outcome = (
        "REUSE_EXACT_MODEL"
        if initial_route.selection.outcome == "EXACT_MODEL_MATCH"
        else "CONSTRUCT_REGISTERED_MODEL"
        if constructor is not None
        else "NO_CERTIFIABLE_CONSTRUCTOR"
    )
    dispatch = ObservationDrivenSynthesisDispatchV1(
        _DISPATCH_ISSUER,
        catalogue.catalogue_id,
        initial_route.result_id,
        context.context_key,
        context.context_id,
        context.topology.topology_id,
        initial_route.selection.outcome,
        dispatch_outcome,
        constructor if dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL" else None,
    )
    if dispatch_outcome == "REUSE_EXACT_MODEL":
        return ObservationDrivenWorldModelSynthesisResultV1(
            _RESULT_ISSUER,
            initial_route,
            dispatch,
            None,
            None,
            catalogue,
            initial_route,
            None,
        )
    if dispatch_outcome == "NO_CERTIFIABLE_CONSTRUCTOR":
        closure = ObservationDrivenSynthesisUnsupportedV1(
            _UNSUPPORTED_ISSUER, dispatch
        )
        return ObservationDrivenWorldModelSynthesisResultV1(
            _RESULT_ISSUER,
            initial_route,
            dispatch,
            None,
            closure,
            catalogue,
            None,
            None,
        )
    if selected_reuse_result_bytes is not None:
        _fail("model construction miss cannot accept a prebuilt model")

    if context.context_key == "opaque_graph_w5_v0":
        source = w5_source_v1.run_heldout_checkpoint_recertification_v1()
        with accounting_phase.adaptive_accounting_phase_v1(
            accounting_phase.AdaptiveAccountingPhaseV1.ABSTRACT_CERTIFICATE
        ):
            reuse = w5_reuse_v1.run_heldout_overlay_abstract_reuse_v1(
                source,
                logical_occurrence_id=_logical("w5-reuse", dispatch.dispatch_id),
                occurrence_ordinal=occurrence_ordinal + 1,
            )
        family = "W5"
        source_document = source.to_document()
        base_audit = source.base_audit
        overlay = source.final_overlay
        changed_count, preserved_count, draws = 2, 6, 4_096
    else:
        source = k6_source_v1.run_heldout_k6_checkpoint_recertification_v1()
        with accounting_phase.adaptive_accounting_phase_v1(
            accounting_phase.AdaptiveAccountingPhaseV1.ABSTRACT_CERTIFICATE
        ):
            reuse = k6_reuse_v1.run_heldout_k6_overlay_abstract_reuse_v1(
                source,
                logical_occurrence_id=_logical("k6-reuse", dispatch.dispatch_id),
                occurrence_ordinal=occurrence_ordinal + 1,
            )
        family = "K6"
        source_document = source.to_document()
        base_audit = source.base_audit
        overlay = source.overlay
        changed_count, preserved_count, draws = 1, 19, 8_192
    if (
        base_audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or overlay.audit.status is not robust.RobustAuditStatus.CERTIFIED
        or source_document["changed_row_count"] != changed_count
        or source_document["preserved_row_count"] != preserved_count
        or source_document["incremental_local_ground_draw_count"] != draws
    ):
        _fail("registered constructor did not form its minimal certified overlay")

    with accounting_phase.adaptive_accounting_phase_v1(
        accounting_phase.AdaptiveAccountingPhaseV1.LOCAL_RECOVERY
    ):
        reuse_document = reuse.to_document()
        reuse_bytes = canonical_json_bytes(reuse_document)
        entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
            family, reuse_bytes
        )
        promoted_catalogue = _promoted_snapshot(catalogue, entry)
        promotion = ObservationDrivenModelPromotionV1(
            _PROMOTION_ISSUER,
            dispatch,
            family,
            source.result_id,
            base_audit.audit_id,
            overlay.overlay_id,
            overlay.audit.audit_id,
            changed_count,
            preserved_count,
            draws,
            reuse.result_id,
            entry,
            catalogue.catalogue_id,
            promoted_catalogue,
        )
        accounting_runtime.emit_owned_operation_v1(
            "adaptive-world-model.catalogue-promotion"
        )
    with accounting_phase.adaptive_accounting_phase_v1(
        accounting_phase.AdaptiveAccountingPhaseV1.ABSTRACT_CERTIFICATE
    ):
        final_route = router_v1.run_heldout_catalogue_query_v1(
            promoted_catalogue,
            context,
            logical_occurrence_id=_logical("fresh-postpromotion", promotion.promotion_id),
            occurrence_ordinal=occurrence_ordinal + 2,
            selected_reuse_result_bytes=reuse_bytes,
        )
    return ObservationDrivenWorldModelSynthesisResultV1(
        _RESULT_ISSUER,
        initial_route,
        dispatch,
        promotion,
        None,
        promoted_catalogue,
        final_route,
        reuse_document,
    )


def verify_observation_driven_world_model_synthesis_v1(
    result: ObservationDrivenWorldModelSynthesisResultV1,
) -> ObservationDrivenWorldModelSynthesisResultV1:
    if type(result) is not ObservationDrivenWorldModelSynthesisResultV1:
        _fail("world-model synthesis verifier rejects foreign values")
    result.__post_init__(_RESULT_ISSUER)
    catalogue_v1.verify_heldout_reusable_model_catalogue_v1(result.final_catalogue)
    if result.final_route is not None and result.promotion is not None:
        assert result.reuse_result_document is not None
        router_v1.verify_heldout_catalogue_query_result_v1(
            result.final_route,
            selected_reuse_result_bytes=canonical_json_bytes(
                result.reuse_result_document
            ),
        )
    return result


__all__ = (
    "ConstructionK7ObservationDrivenWorldModelSynthesisV1Error",
    "LOCAL_DOMAINS",
    "ObservationDrivenModelPromotionV1",
    "ObservationDrivenSynthesisDispatchV1",
    "ObservationDrivenSynthesisUnsupportedV1",
    "ObservationDrivenWorldModelSynthesisResultV1",
    "run_observation_driven_world_model_synthesis_v1",
    "verify_observation_driven_world_model_synthesis_v1",
)
