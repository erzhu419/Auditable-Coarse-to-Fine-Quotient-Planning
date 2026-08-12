"""Durable structural catalogue for independently verified world models.

W5 and K6 each contribute one independently replayed, query-neutral quotient
model.  Selection is an exact public-context identity match.  A different
topology -- including the registered K6-minus-edge control -- produces a typed
``MODEL_MISS`` and cannot receive either model.  The miss is the boundary at
which a later observation-driven construction/recovery pipeline may begin; it
is not a plan certificate or fallback result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import (
    construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1
    as w5_verifier_v1,
)
from acfqp import (
    construction_k7_heldout_k6_overlay_abstract_reuse_independent_verifier_v1
    as k6_verifier_v1,
)
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.136"
PROFILE_KEY = "construction_k7_heldout_reusable_model_catalogue_v1"
ENTRY_DOMAIN = CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN
CATALOGUE_DOMAIN = CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN
SELECTION_DOMAIN = CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN
LOCAL_DOMAINS = frozenset({ENTRY_DOMAIN, CATALOGUE_DOMAIN, SELECTION_DOMAIN})
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out model-catalogue domains are not central")

_FAMILY_SPECS: Mapping[str, tuple[str, int, str, str]] = {
    "W5": (
        "opaque_graph_w5_v0",
        5,
        "acfqp.construction_k7_heldout_abstract_reuse_result.v1",
        "acfqp.construction_k7_heldout_checkpoint_recertification_result.v1",
    ),
    "K6": (
        "opaque_graph_k6_v0",
        6,
        "acfqp.construction_k7_heldout_k6_abstract_reuse_result.v1",
        "acfqp.construction_k7_heldout_k6_recertification_result.v1",
    ),
}

_ENTRY_ISSUER = object()
_CATALOGUE_ISSUER = object()
_SELECTION_ISSUER = object()


class ConstructionK7HeldoutReusableModelCatalogueV1Error(ValueError):
    """The verified model entry, catalogue, or exact selector changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutReusableModelCatalogueV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutReusableModelCatalogueV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} must be canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutReusableModelCatalogueV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _structural_entry_facts(
    family_key: str,
    reuse: Mapping[str, Any],
) -> dict[str, Any]:
    context_key, vertex_count, reuse_schema, source_schema = _FAMILY_SPECS[family_key]
    source = reuse.get("source_result")
    query = reuse.get("query")
    plan = reuse.get("plan")
    model = reuse.get("final_quotient_model")
    threshold = reuse.get("threshold")
    if (
        reuse.get("schema") != reuse_schema
        or not all(type(item) is dict for item in (source, query, plan, model, threshold))
    ):
        _fail(f"{family_key} model entry evidence is incomplete")
    preregistration = source.get("preregistration")
    if type(preregistration) is not dict:
        _fail(f"{family_key} source preregistration is absent")
    source_id = _cid(reuse.get("source_result_id"), f"{family_key} source")
    overlay_id = _cid(reuse.get("source_overlay_id"), f"{family_key} overlay")
    context_id = _cid(source.get("target_context_id"), f"{family_key} context")
    model_id = _cid(query.get("quotient_model_id"), f"{family_key} model")
    threshold_id = _cid(
        query.get("threshold_profile_id"), f"{family_key} threshold"
    )
    audit_id = _cid(
        reuse.get("replanned_audit_id"), f"{family_key} certified audit"
    )
    if (
        source.get("schema") != source_schema
        or source.get("result_id") != source_id
        or source.get("source_vertex_counts") != [4]
        or source.get("target_vertex_count") != vertex_count
        or preregistration.get("target_context_key") != context_key
        or query.get("context_id") != context_id
        or source.get("final_overlay_id") != overlay_id
        or query.get("source_overlay_id") != overlay_id
        or source.get("final_quotient_model_id") != model_id
        or model.get("model_id") != model_id
        or threshold.get("threshold_profile_id") != threshold_id
        or plan.get("replanned_audit_id") != audit_id
        or plan.get("audit_status") != "CERTIFIED"
        or source.get("query_neutral_overlay_reusable") is not True
        or source.get("local_ground_restoration_only_after_certificate_failure")
        is not True
        or reuse.get("fresh_occurrence_directly_abstract_certified") is not True
        or reuse.get("source_local_recovery_reused_as_query_neutral_overlay")
        is not True
    ):
        _fail(f"{family_key} model entry structural chain changed")
    topology = observer_v1.public_context_by_key_v1(context_key).topology
    return {
        "source_result_id": source_id,
        "source_overlay_id": overlay_id,
        "context_id": context_id,
        "topology_id": topology.topology_id,
        "model_id": model_id,
        "threshold_profile_id": threshold_id,
        "certified_audit_id": audit_id,
    }


@dataclass(frozen=True, slots=True)
class HeldoutReusableModelCatalogueEntryV1:
    _issuer: Any = field(repr=False, compare=False)
    family_key: str = ""
    target_context_key: str = ""
    target_vertex_count: int = 0
    context_id: str = ""
    topology_id: str = ""
    source_result_id: str = ""
    source_overlay_id: str = ""
    quotient_model_id: str = ""
    threshold_profile_id: str = ""
    certified_audit_id: str = ""
    source_reuse_result_id: str = ""
    source_reuse_bytes_sha256: str = ""
    source_independent_verification_id: str = ""
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = _FAMILY_SPECS.get(self.family_key)
        if (
            self._issuer is not _ENTRY_ISSUER
            or expected is None
            or (self.target_context_key, self.target_vertex_count) != expected[:2]
        ):
            _fail("reusable model entry is caller-minted or unregistered")
        for value, label in (
            (self.context_id, "entry context"),
            (self.topology_id, "entry topology"),
            (self.source_result_id, "entry source"),
            (self.source_overlay_id, "entry overlay"),
            (self.quotient_model_id, "entry model"),
            (self.threshold_profile_id, "entry threshold"),
            (self.certified_audit_id, "entry audit"),
            (self.source_reuse_result_id, "entry reuse result"),
            (self.source_reuse_bytes_sha256, "entry reuse digest"),
            (self.source_independent_verification_id, "entry verification"),
        ):
            _cid(value, label)
        object.__setattr__(self, "_entry_id", content_id(ENTRY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_model_catalogue_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_key": self.family_key,
            "source_vertex_counts": [4],
            "target_context_key": self.target_context_key,
            "target_vertex_count": self.target_vertex_count,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "source_result_id": self.source_result_id,
            "source_overlay_id": self.source_overlay_id,
            "quotient_model_id": self.quotient_model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "certified_audit_id": self.certified_audit_id,
            "source_reuse_result_id": self.source_reuse_result_id,
            "source_reuse_bytes_sha256": self.source_reuse_bytes_sha256,
            "source_independent_verification_id": (
                self.source_independent_verification_id
            ),
            "query_neutral_model": True,
            "source_certificate_failure_recovery_present": True,
            "fresh_zero_ground_abstract_reuse_verified": True,
            "selection_requires_exact_context_and_topology_identity": True,
            "cross_structural_model_transfer_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def entry_id(self) -> str:
        current = content_id(ENTRY_DOMAIN, self._payload())
        if current != self._entry_id:
            _fail("reusable model entry changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_catalogue_entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class HeldoutReusableModelCatalogueV1:
    _issuer: Any = field(repr=False, compare=False)
    entries: tuple[HeldoutReusableModelCatalogueEntryV1, ...] = ()
    _catalogue_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        object.__setattr__(self, "entries", entries)
        family_keys = tuple(item.family_key for item in entries)
        if (
            self._issuer is not _CATALOGUE_ISSUER
            or len(entries) > len(_FAMILY_SPECS)
            or family_keys
            != tuple(key for key in _FAMILY_SPECS if key in family_keys)
            or len(set(family_keys)) != len(family_keys)
            or any(type(item) is not HeldoutReusableModelCatalogueEntryV1 for item in entries)
            or len({item.context_id for item in entries}) != len(entries)
            or len({item.topology_id for item in entries}) != len(entries)
            or len({item.quotient_model_id for item in entries}) != len(entries)
        ):
            _fail("reusable model catalogue inventory changed")
        object.__setattr__(
            self, "_catalogue_id", content_id(CATALOGUE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_model_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ordered_entry_ids": [item.entry_id for item in self.entries],
            "registered_structural_context_keys": [
                item.target_context_key for item in self.entries
            ],
            "registered_target_vertex_counts": [
                item.target_vertex_count for item in self.entries
            ],
            "registered_model_count": len(self.entries),
            "selector_kind": "EXACT_CONTEXT_AND_TOPOLOGY_IDENTITY",
            "nearby_structure_transfer_allowed": False,
            "model_miss_requires_new_construction_or_fallback": True,
            "persistent_storage_implemented": False,
            "official_execution_allowed": False,
        }

    @property
    def catalogue_id(self) -> str:
        current = content_id(CATALOGUE_DOMAIN, self._payload())
        if current != self._catalogue_id:
            _fail("reusable model catalogue changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_catalogue_id": self.catalogue_id}


@dataclass(frozen=True, slots=True)
class HeldoutReusableModelSelectionV1:
    _issuer: Any = field(repr=False, compare=False)
    catalogue_id: str = ""
    requested_context_key: str = ""
    requested_context_id: str = ""
    requested_topology_id: str = ""
    requested_vertex_count: int = 0
    outcome: str = ""
    selected_entry_id: str | None = None
    selected_model_id: str | None = None
    selected_overlay_id: str | None = None
    _selection_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _SELECTION_ISSUER:
            _fail("model selection is caller-minted")
        for value, label in (
            (self.catalogue_id, "selection catalogue"),
            (self.requested_context_id, "selection context"),
            (self.requested_topology_id, "selection topology"),
        ):
            _cid(value, label)
        hit = self.outcome == "EXACT_MODEL_MATCH"
        miss = self.outcome == "MODEL_MISS"
        if (
            type(self.requested_context_key) is not str
            or not self.requested_context_key
            or type(self.requested_vertex_count) is not int
            or self.requested_vertex_count <= 0
            or not (hit or miss)
            or (
                hit
                and any(
                    value is None
                    for value in (
                        self.selected_entry_id,
                        self.selected_model_id,
                        self.selected_overlay_id,
                    )
                )
            )
            or (
                miss
                and any(
                    value is not None
                    for value in (
                        self.selected_entry_id,
                        self.selected_model_id,
                        self.selected_overlay_id,
                    )
                )
            )
        ):
            _fail("model selection outcome changed")
        for value, label in (
            (self.selected_entry_id, "selected entry"),
            (self.selected_model_id, "selected model"),
            (self.selected_overlay_id, "selected overlay"),
        ):
            if value is not None:
                _cid(value, label)
        object.__setattr__(
            self, "_selection_id", content_id(SELECTION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_model_selection.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_catalogue_id": self.catalogue_id,
            "requested_context_key": self.requested_context_key,
            "requested_context_id": self.requested_context_id,
            "requested_topology_id": self.requested_topology_id,
            "requested_vertex_count": self.requested_vertex_count,
            "selection_outcome": self.outcome,
            "selected_model_catalogue_entry_id": self.selected_entry_id,
            "selected_quotient_model_id": self.selected_model_id,
            "selected_source_overlay_id": self.selected_overlay_id,
            "exact_identity_match_required": True,
            "cross_structural_model_transfer_attempted": False,
            "fresh_ground_or_observer_event_count": 0,
            "plan_certificate_issued": False,
            "local_ground_recovery_authorized_here": False,
            "direct_fallback_executed_here": False,
            "official_execution_allowed": False,
        }

    @property
    def selection_id(self) -> str:
        current = content_id(SELECTION_DOMAIN, self._payload())
        if current != self._selection_id:
            _fail("model selection changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_selection_id": self.selection_id}


def build_heldout_reusable_model_catalogue_entry_v1(
    family_key: str,
    reuse_result_bytes: bytes,
) -> HeldoutReusableModelCatalogueEntryV1:
    if family_key not in _FAMILY_SPECS:
        _fail("model entry family is not registered")
    document = _canonical(reuse_result_bytes, f"{family_key} reuse result")
    if family_key == "W5":
        verification = w5_verifier_v1.verify_heldout_overlay_abstract_reuse_bytes_v1(
            reuse_result_bytes
        )
    else:
        verification = k6_verifier_v1.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
            reuse_result_bytes
        )
    facts = _structural_entry_facts(family_key, document)
    context_key, vertex_count, _reuse_schema, _source_schema = _FAMILY_SPECS[family_key]
    return HeldoutReusableModelCatalogueEntryV1(
        _ENTRY_ISSUER,
        family_key,
        context_key,
        vertex_count,
        facts["context_id"],
        facts["topology_id"],
        facts["source_result_id"],
        facts["source_overlay_id"],
        facts["model_id"],
        facts["threshold_profile_id"],
        facts["certified_audit_id"],
        _cid(document.get("result_id"), f"{family_key} reuse result"),
        hashlib.sha256(reuse_result_bytes).hexdigest(),
        verification.verification_id,
    )


def build_heldout_reusable_model_catalogue_snapshot_v1(
    entries: tuple[HeldoutReusableModelCatalogueEntryV1, ...],
) -> HeldoutReusableModelCatalogueV1:
    """Freeze one exact subset, including the empty bootstrap inventory."""

    if type(entries) is not tuple:
        _fail("model catalogue snapshot entries must be one exact tuple")
    return HeldoutReusableModelCatalogueV1(_CATALOGUE_ISSUER, entries)


def build_heldout_reusable_model_catalogue_v1(
    *,
    w5_reuse_result_bytes: bytes,
    k6_reuse_result_bytes: bytes,
) -> HeldoutReusableModelCatalogueV1:
    """Replay and catalogue the two registered query-neutral models."""

    return HeldoutReusableModelCatalogueV1(
        _CATALOGUE_ISSUER,
        (
            build_heldout_reusable_model_catalogue_entry_v1(
                "W5", w5_reuse_result_bytes
            ),
            build_heldout_reusable_model_catalogue_entry_v1(
                "K6", k6_reuse_result_bytes
            ),
        ),
    )


def select_heldout_reusable_model_v1(
    catalogue: HeldoutReusableModelCatalogueV1,
    context: observer_v1.PublicGraphContextV1,
) -> HeldoutReusableModelSelectionV1:
    """Select only an exact structural identity; otherwise return MODEL_MISS."""

    if (
        type(catalogue) is not HeldoutReusableModelCatalogueV1
        or type(context) is not observer_v1.PublicGraphContextV1
    ):
        _fail("model selector requires exact catalogue and public context types")
    catalogue.catalogue_id
    accounting_runtime.emit_owned_operation_v1(
        "adaptive-world-model.catalogue-selection"
    )
    registered = observer_v1.public_context_by_key_v1(context.context_key)
    if registered != context:
        _fail("model selector context differs from the registered public identity")
    matches = tuple(
        entry
        for entry in catalogue.entries
        if (
            entry.target_context_key == context.context_key
            and entry.context_id == context.context_id
            and entry.topology_id == context.topology.topology_id
            and entry.target_vertex_count == context.topology.vertex_count
        )
    )
    if len(matches) > 1:
        _fail("model selector found ambiguous exact identities")
    entry = matches[0] if matches else None
    return HeldoutReusableModelSelectionV1(
        _SELECTION_ISSUER,
        catalogue.catalogue_id,
        context.context_key,
        context.context_id,
        context.topology.topology_id,
        context.topology.vertex_count,
        "EXACT_MODEL_MATCH" if entry is not None else "MODEL_MISS",
        None if entry is None else entry.entry_id,
        None if entry is None else entry.quotient_model_id,
        None if entry is None else entry.source_overlay_id,
    )


def verify_heldout_reusable_model_catalogue_v1(
    catalogue: HeldoutReusableModelCatalogueV1,
) -> HeldoutReusableModelCatalogueV1:
    if type(catalogue) is not HeldoutReusableModelCatalogueV1:
        _fail("model-catalogue verifier rejects foreign values")
    expected = HeldoutReusableModelCatalogueV1(
        _CATALOGUE_ISSUER,
        tuple(
            HeldoutReusableModelCatalogueEntryV1(
                _ENTRY_ISSUER,
                entry.family_key,
                entry.target_context_key,
                entry.target_vertex_count,
                entry.context_id,
                entry.topology_id,
                entry.source_result_id,
                entry.source_overlay_id,
                entry.quotient_model_id,
                entry.threshold_profile_id,
                entry.certified_audit_id,
                entry.source_reuse_result_id,
                entry.source_reuse_bytes_sha256,
                entry.source_independent_verification_id,
            )
            for entry in catalogue.entries
        ),
    )
    if expected != catalogue or expected.catalogue_id != catalogue.catalogue_id:
        _fail("model catalogue differs from exact typed replay")
    return catalogue


__all__ = (
    "ConstructionK7HeldoutReusableModelCatalogueV1Error",
    "HeldoutReusableModelCatalogueEntryV1",
    "HeldoutReusableModelCatalogueV1",
    "HeldoutReusableModelSelectionV1",
    "LOCAL_DOMAINS",
    "build_heldout_reusable_model_catalogue_v1",
    "build_heldout_reusable_model_catalogue_entry_v1",
    "build_heldout_reusable_model_catalogue_snapshot_v1",
    "select_heldout_reusable_model_v1",
    "verify_heldout_reusable_model_catalogue_v1",
)
