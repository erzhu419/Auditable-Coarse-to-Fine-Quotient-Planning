"""Promote a newly constructed K6 model after an exact catalogue miss.

The campaign starts from an immutable W5-only catalogue.  A K6 query first
produces a no-access ``MODEL_MISS`` and is preregistered before construction.
The existing K6 held-out authority then builds a base partial model, observes
its failed certificate, extends exactly one registered frontier row, freezes
an immutable certified overlay, and promotes that query-neutral model into a
new catalogue snapshot.  A second K6 query is planned entirely in the promoted
abstract model with zero fresh ground access.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_catalogue_query_router_v1 as router_v1
from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as reuse_v1
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.138"
PROFILE_KEY = "construction_k7_heldout_catalogue_miss_recovery_promotion_v1"

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN
)
PROMOTION_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN
CLOSURE_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREREGISTRATION_DOMAIN, PROMOTION_DOMAIN, CLOSURE_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("catalogue-promotion domains are not central")

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
K6_REUSE_FILENAME = "0002_K6_REUSE_RESULT.json"
PROMOTION_FILENAME = "0003_MODEL_PROMOTION.json"
FINAL_ROUTE_FILENAME = "0004_FINAL_ABSTRACT_ROUTE.json"
CLOSURE_FILENAME = "0005_CAMPAIGN_CLOSURE.json"
EXPECTED_FILENAMES = (
    PREREGISTRATION_FILENAME,
    K6_REUSE_FILENAME,
    PROMOTION_FILENAME,
    FINAL_ROUTE_FILENAME,
    CLOSURE_FILENAME,
)

_PREREG_ISSUER = object()
_PROMOTION_ISSUER = object()
_CLOSURE_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error(RuntimeError):
    """The miss, recovery, promotion, route, or durable chronology changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _logical_identity(role: str, parent_id: str) -> str:
    return hashlib.sha256(f"{PROFILE_KEY}:{role}:{parent_id}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CataloguePromotionPreregistrationV1:
    _issuer: InitVar[object]
    initial_catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1
    initial_miss: router_v1.HeldoutCatalogueQueryResultV1
    target_context_id: str
    target_topology_id: str
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREREG_ISSUER
            or type(self.initial_catalogue)
            is not catalogue_v1.HeldoutReusableModelCatalogueV1
            or tuple(item.family_key for item in self.initial_catalogue.entries)
            != ("W5",)
            or type(self.initial_miss) is not router_v1.HeldoutCatalogueQueryResultV1
            or self.initial_miss.to_document()["routing_outcome"]
            != "CONSTRUCTION_REQUIRED"
            or self.initial_miss.construction_request is None
            or self.initial_miss.query.context_key != source_v1.TARGET_CONTEXT_KEY
            or self.initial_miss.query.context_id != self.target_context_id
            or self.initial_miss.query.topology_id != self.target_topology_id
        ):
            _fail("catalogue promotion preregistration is not the exact K6 miss")
        _cid(self.target_context_id, "promotion target context")
        _cid(self.target_topology_id, "promotion target topology")
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        request = self.initial_miss.construction_request
        assert request is not None
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_promotion_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "initial_model_catalogue_id": self.initial_catalogue.catalogue_id,
            "initial_model_count": 1,
            "initial_model_selection_id": self.initial_miss.selection.selection_id,
            "initial_catalogue_query_id": self.initial_miss.query.query_id,
            "initial_construction_request_id": request.request_id,
            "target_context_key": source_v1.TARGET_CONTEXT_KEY,
            "target_context_id": self.target_context_id,
            "target_topology_id": self.target_topology_id,
            "registered_validation_checkpoint_ladder": [8_192, 16_384],
            "max_local_transactions": 1,
            "construction_must_follow_preregistration_commit": True,
            "local_ground_only_after_failed_abstract_certificate": True,
            "promoted_entry_requires_independent_reuse_verification": True,
            "nearby_model_transfer_allowed": False,
            "full_target_closure_authorized": False,
            "exact_evaluation_or_ground_solver_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        current = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if current != self._preregistration_id:
            _fail("catalogue promotion preregistration changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "initial_catalogue": self.initial_catalogue.to_document(),
            "initial_miss": self.initial_miss.to_document(),
            "promotion_preregistration_id": self.preregistration_id,
        }


@dataclass(frozen=True, slots=True)
class CatalogueModelPromotionEventV1:
    _issuer: InitVar[object]
    preregistration: CataloguePromotionPreregistrationV1
    source: source_v1.K6CheckpointRecertificationResultV1 = field(repr=False)
    reuse: reuse_v1.K6OverlayAbstractReuseResultV1 = field(repr=False)
    promoted_entry: catalogue_v1.HeldoutReusableModelCatalogueEntryV1
    promoted_catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1
    _promotion_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROMOTION_ISSUER
            or type(self.preregistration) is not CataloguePromotionPreregistrationV1
            or type(self.source) is not source_v1.K6CheckpointRecertificationResultV1
            or type(self.reuse) is not reuse_v1.K6OverlayAbstractReuseResultV1
            or type(self.promoted_entry)
            is not catalogue_v1.HeldoutReusableModelCatalogueEntryV1
            or type(self.promoted_catalogue)
            is not catalogue_v1.HeldoutReusableModelCatalogueV1
            or self.promoted_entry.family_key != "K6"
            or tuple(item.family_key for item in self.promoted_catalogue.entries)
            != ("W5", "K6")
            or self.promoted_catalogue.entries[0]
            != self.preregistration.initial_catalogue.entries[0]
            or self.promoted_catalogue.entries[1] != self.promoted_entry
            or self.source.base_audit.status
            is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            or self.source.overlay.audit.status is not robust.RobustAuditStatus.CERTIFIED
            or self.source.overlay.changed_row_binding_ids
            != (self.source.request.row_binding_id,)
            or len(self.source.overlay.preserved_row_binding_ids) != 19
            or self.reuse.source != self.source
            or self.reuse.plan.audit.status is not robust.RobustAuditStatus.CERTIFIED
            or self.reuse.result_id != self.promoted_entry.source_reuse_result_id
            or self.source.result_id != self.promoted_entry.source_result_id
            or self.source.overlay.overlay_id != self.promoted_entry.source_overlay_id
            or self.source.overlay.bridge.quotient_model.model_id
            != self.promoted_entry.quotient_model_id
        ):
            _fail("catalogue promotion event crossed its recovery/model chain")
        object.__setattr__(
            self, "_promotion_id", content_id(PROMOTION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_promotion_event.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_preregistration_id": self.preregistration.preregistration_id,
            "initial_model_catalogue_id": self.preregistration.initial_catalogue.catalogue_id,
            "source_recertification_result_id": self.source.result_id,
            "source_base_audit_id": self.source.base_audit.audit_id,
            "source_base_audit_status": self.source.base_audit.status.value,
            "source_recovery_request_id": self.source.request.request_id,
            "source_overlay_id": self.source.overlay.overlay_id,
            "source_final_audit_id": self.source.overlay.audit.audit_id,
            "source_final_audit_status": self.source.overlay.audit.status.value,
            "source_changed_row_binding_ids": list(
                self.source.overlay.changed_row_binding_ids
            ),
            "source_changed_row_count": 1,
            "source_preserved_row_count": 19,
            "source_incremental_local_ground_draw_count": 8_192,
            "source_full_16384_row_closure_built": False,
            "source_exact_evaluation_calls": 0,
            "source_ground_solver_invocations": 0,
            "source_reuse_result_id": self.reuse.result_id,
            "promoted_model_catalogue_entry_id": self.promoted_entry.entry_id,
            "promoted_quotient_model_id": self.promoted_entry.quotient_model_id,
            "promoted_model_catalogue_id": self.promoted_catalogue.catalogue_id,
            "promoted_model_count": 2,
            "request_frozen_before_local_observation": True,
            "local_ground_triggered_only_by_failed_certificate": True,
            "immutable_query_neutral_overlay_promoted": True,
            "independent_reuse_verification_required_before_promotion": True,
            "automatic_coordinate_primitive_invention_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def promotion_id(self) -> str:
        current = content_id(PROMOTION_DOMAIN, self._payload())
        if current != self._promotion_id:
            _fail("catalogue promotion event changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_entry": self.promoted_entry.to_document(),
            "promoted_catalogue": self.promoted_catalogue.to_document(),
            "model_promotion_id": self.promotion_id,
        }


@dataclass(frozen=True, slots=True)
class CataloguePromotionFileCommitV1:
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            self.filename not in EXPECTED_FILENAMES
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("catalogue promotion file commit changed")
        _cid(self.bytes_sha256, "campaign file digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
        }


@dataclass(frozen=True, slots=True)
class CataloguePromotionCampaignClosureV1:
    _issuer: InitVar[object]
    preregistration: CataloguePromotionPreregistrationV1
    promotion: CatalogueModelPromotionEventV1
    final_route: router_v1.HeldoutCatalogueQueryResultV1
    predecessor_commits: tuple[CataloguePromotionFileCommitV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        commits = tuple(self.predecessor_commits)
        object.__setattr__(self, "predecessor_commits", commits)
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.preregistration) is not CataloguePromotionPreregistrationV1
            or type(self.promotion) is not CatalogueModelPromotionEventV1
            or type(self.final_route) is not router_v1.HeldoutCatalogueQueryResultV1
            or self.promotion.preregistration != self.preregistration
            or tuple(item.filename for item in commits) != EXPECTED_FILENAMES[:4]
            or self.final_route.selection.catalogue_id
            != self.promotion.promoted_catalogue.catalogue_id
            or self.final_route.query.context_key != source_v1.TARGET_CONTEXT_KEY
            or self.final_route.plan is None
            or self.final_route.to_document()["routing_outcome"]
            != "ABSTRACT_PLAN_CERTIFIED"
            or self.final_route.plan.entry != self.promotion.promoted_entry
        ):
            _fail("catalogue promotion campaign closure changed")
        object.__setattr__(
            self, "_closure_id", content_id(CLOSURE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_promotion_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_preregistration_id": self.preregistration.preregistration_id,
            "model_promotion_id": self.promotion.promotion_id,
            "final_catalogue_query_result_id": self.final_route.result_id,
            "initial_model_catalogue_id": self.preregistration.initial_catalogue.catalogue_id,
            "promoted_model_catalogue_id": self.promotion.promoted_catalogue.catalogue_id,
            "ordered_predecessor_file_commits": [
                item.to_document() for item in self.predecessor_commits
            ],
            "logical_occurrence_denominator": 1,
            "certificate_coverage_denominator": 1,
            "future_economics_cost_denominator": 1,
            "plan_certificate_count": 1,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 0,
            "initial_catalogue_miss_count": 1,
            "local_recovery_transaction_count": 1,
            "historical_local_ground_draw_count": 8_192,
            "fresh_postpromotion_ground_draw_count": 0,
            "fresh_postpromotion_observer_call_count": 0,
            "fresh_postpromotion_abstract_planner_invocations": 1,
            "multi_step_plan_mainly_completed_in_reusable_abstract_model": True,
            "ground_distinctions_restored_only_after_certificate_failure": True,
            "promoted_model_reusable_for_later_queries": True,
            "broad_cross_domain_generalization_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
        }

    @property
    def closure_id(self) -> str:
        current = content_id(CLOSURE_DOMAIN, self._payload())
        if current != self._closure_id:
            _fail("catalogue promotion closure changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class CataloguePromotionCampaignResultV1:
    _issuer: InitVar[object]
    preregistration: CataloguePromotionPreregistrationV1
    source: source_v1.K6CheckpointRecertificationResultV1 = field(repr=False)
    reuse: reuse_v1.K6OverlayAbstractReuseResultV1 = field(repr=False)
    promotion: CatalogueModelPromotionEventV1
    final_route: router_v1.HeldoutCatalogueQueryResultV1
    closure: CataloguePromotionCampaignClosureV1
    file_commits: tuple[CataloguePromotionFileCommitV1, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        commits = tuple(self.file_commits)
        object.__setattr__(self, "file_commits", commits)
        if (
            _issuer is not _RESULT_ISSUER
            or self.promotion.preregistration != self.preregistration
            or self.promotion.source != self.source
            or self.promotion.reuse != self.reuse
            or self.closure.preregistration != self.preregistration
            or self.closure.promotion != self.promotion
            or self.closure.final_route != self.final_route
            or tuple(item.filename for item in commits) != EXPECTED_FILENAMES
            or commits[:4] != self.closure.predecessor_commits
        ):
            _fail("catalogue promotion result graph changed")
        object.__setattr__(
            self, "_result_id", content_id(RESULT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_promotion_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_preregistration_id": self.preregistration.preregistration_id,
            "source_recertification_result_id": self.source.result_id,
            "source_reuse_result_id": self.reuse.result_id,
            "model_promotion_id": self.promotion.promotion_id,
            "final_catalogue_query_result_id": self.final_route.result_id,
            "campaign_closure_id": self.closure.closure_id,
            "ordered_file_commits": [item.to_document() for item in self.file_commits],
            "durable_campaign_graph_complete": True,
            "independent_campaign_verification_present": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("catalogue promotion result changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "promotion_campaign_result_id": self.result_id}


def _prepare_directory(path: Path) -> None:
    if path.exists():
        _fail("campaign directory must not already exist")
    path.mkdir(mode=0o700, parents=False)
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.is_symlink() or not path.is_dir() or mode != 0o700:
        _fail("campaign directory is not one private directory")


def _write_commit(
    directory: Path,
    filename: str,
    document: dict[str, Any],
) -> CataloguePromotionFileCommitV1:
    raw = canonical_json_bytes(document)
    target = directory / filename
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                _fail("campaign artifact write made no progress")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return CataloguePromotionFileCommitV1(
        filename, len(raw), hashlib.sha256(raw).hexdigest()
    )


def run_catalogue_miss_recovery_promotion_v1(
    *,
    w5_reuse_result_bytes: bytes,
    campaign_directory: str | os.PathLike[str],
) -> CataloguePromotionCampaignResultV1:
    """Run one preregistered miss→local recovery→promotion→reuse campaign."""

    w5_entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
        "W5", w5_reuse_result_bytes
    )
    initial_catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(
        (w5_entry,)
    )
    context = observer_v1.public_context_by_key_v1(source_v1.TARGET_CONTEXT_KEY)
    initial_miss = router_v1.run_heldout_catalogue_query_v1(
        initial_catalogue,
        context,
        logical_occurrence_id=_logical_identity("initial-miss", initial_catalogue.catalogue_id),
        occurrence_ordinal=1,
        selected_reuse_result_bytes=None,
    )
    preregistration = CataloguePromotionPreregistrationV1(
        _PREREG_ISSUER,
        initial_catalogue,
        initial_miss,
        context.context_id,
        context.topology.topology_id,
    )
    directory = Path(campaign_directory)
    _prepare_directory(directory)
    commits = [
        _write_commit(
            directory, PREREGISTRATION_FILENAME, preregistration.to_document()
        )
    ]

    source = source_v1.run_heldout_k6_checkpoint_recertification_v1()
    reuse = reuse_v1.run_heldout_k6_overlay_abstract_reuse_v1(
        source,
        logical_occurrence_id=_logical_identity(
            "construction-reuse", preregistration.preregistration_id
        ),
        occurrence_ordinal=2,
    )
    reuse_bytes = canonical_json_bytes(reuse.to_document())
    commits.append(_write_commit(directory, K6_REUSE_FILENAME, reuse.to_document()))
    k6_entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1(
        "K6", reuse_bytes
    )
    promoted_catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(
        (w5_entry, k6_entry)
    )
    promotion = CatalogueModelPromotionEventV1(
        _PROMOTION_ISSUER,
        preregistration,
        source,
        reuse,
        k6_entry,
        promoted_catalogue,
    )
    commits.append(_write_commit(directory, PROMOTION_FILENAME, promotion.to_document()))

    final_route = router_v1.run_heldout_catalogue_query_v1(
        promoted_catalogue,
        context,
        logical_occurrence_id=_logical_identity(
            "postpromotion-query", promotion.promotion_id
        ),
        occurrence_ordinal=3,
        selected_reuse_result_bytes=reuse_bytes,
    )
    commits.append(
        _write_commit(directory, FINAL_ROUTE_FILENAME, final_route.to_document())
    )
    closure = CataloguePromotionCampaignClosureV1(
        _CLOSURE_ISSUER,
        preregistration,
        promotion,
        final_route,
        tuple(commits),
    )
    commits.append(_write_commit(directory, CLOSURE_FILENAME, closure.to_document()))
    return CataloguePromotionCampaignResultV1(
        _RESULT_ISSUER,
        preregistration,
        source,
        reuse,
        promotion,
        final_route,
        closure,
        tuple(commits),
    )


def verify_catalogue_miss_recovery_promotion_v1(
    result: CataloguePromotionCampaignResultV1,
    *,
    campaign_directory: str | os.PathLike[str],
) -> CataloguePromotionCampaignResultV1:
    """Revalidate the owner-bound graph and its five physical artifacts."""

    if type(result) is not CataloguePromotionCampaignResultV1:
        _fail("catalogue promotion verifier rejects foreign values")
    result.__post_init__(_RESULT_ISSUER)
    source_v1.verify_heldout_k6_checkpoint_recertification_v1(result.source)
    reuse_v1.verify_heldout_k6_overlay_abstract_reuse_v1(result.reuse)
    router_v1.verify_heldout_catalogue_query_result_v1(
        result.final_route,
        selected_reuse_result_bytes=canonical_json_bytes(result.reuse.to_document()),
    )
    directory = Path(campaign_directory)
    for commit in result.file_commits:
        target = directory / commit.filename
        if target.is_symlink() or not target.is_file():
            _fail("campaign artifact is absent or non-regular")
        raw = target.read_bytes()
        if (
            len(raw) != commit.byte_count
            or hashlib.sha256(raw).hexdigest() != commit.bytes_sha256
        ):
            _fail("campaign artifact bytes changed")
    return result


__all__ = (
    "CatalogueModelPromotionEventV1",
    "CataloguePromotionCampaignClosureV1",
    "CataloguePromotionCampaignResultV1",
    "CataloguePromotionFileCommitV1",
    "CataloguePromotionPreregistrationV1",
    "ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error",
    "EXPECTED_FILENAMES",
    "LOCAL_DOMAINS",
    "run_catalogue_miss_recovery_promotion_v1",
    "verify_catalogue_miss_recovery_promotion_v1",
)
