"""Producer-free replay of the adaptive world-model campaign directory.

The verifier imports no campaign, synthesis, router, catalogue, or constructor
producer.  It composes the existing producer-free W5/K6 model verifiers with
an independent reconstruction of catalogue entries, exact structural routing,
the five synthesis branches, immutable catalogue epochs, seven physical files,
and all campaign denominators.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn

from acfqp import (
    construction_k7_heldout_catalogue_miss_recovery_promotion_independent_verifier_v1
    as catalogue_replay_v1,
)
from acfqp import (
    construction_k7_heldout_k6_overlay_abstract_reuse_independent_verifier_v1
    as k6_verifier_v1,
)
from acfqp import (
    construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1
    as w5_verifier_v1,
)
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.142"
PROFILE_KEY = (
    "construction_k7_observation_driven_world_model_campaign_"
    "independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-driven campaign verification domain is not central")

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
OCCURRENCE_FILENAMES = tuple(
    f"{index + 1:04d}_OCCURRENCE_{index:04d}.json" for index in range(1, 6)
)
CLOSURE_FILENAME = "0007_CAMPAIGN_CLOSURE.json"
EXPECTED_FILENAMES = (
    PREREGISTRATION_FILENAME,
    *OCCURRENCE_FILENAMES,
    CLOSURE_FILENAME,
)

_CAMPAIGN_CONTRACT = "2.0.141"
_CAMPAIGN_PROFILE = "construction_k7_observation_driven_world_model_campaign_v1"
_SYNTHESIS_CONTRACT = "2.0.140"
_SYNTHESIS_PROFILE = "construction_k7_observation_driven_world_model_synthesis_v1"
_RESULT_ISSUER = object()

_SEQUENCE = (
    (1, "W5_CONSTRUCT", "opaque_graph_w5_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED", 0, 1, 4_096, "PLAN_CERTIFICATE", "MODEL_SYNTHESIZED_AND_ABSTRACT_CERTIFIED"),
    (2, "W5_REUSE", "opaque_graph_w5_v0", "EXISTING_MODEL_REUSED", 1, 1, 0, "PLAN_CERTIFICATE", "ABSTRACT_CERTIFIED"),
    (3, "K6_CONSTRUCT", "opaque_graph_k6_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED", 1, 2, 8_192, "PLAN_CERTIFICATE", "MODEL_SYNTHESIZED_AND_ABSTRACT_CERTIFIED"),
    (4, "K6_REUSE", "opaque_graph_k6_v0", "EXISTING_MODEL_REUSED", 2, 2, 0, "PLAN_CERTIFICATE", "ABSTRACT_CERTIFIED"),
    (5, "K6_MINUS_EDGE_UNSUPPORTED", "opaque_graph_k6_minus_edge_v0", "NO_CERTIFIABLE_CONSTRUCTOR", 2, 2, 0, "ATTEMPT_CLOSURE_NONCERTIFICATE", "NO_CERTIFIABLE_CONSTRUCTOR_REGISTERED"),
)


class ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error(
    ValueError
):
    """The portable adaptive-campaign graph does not replay exactly."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{label} must be one object")
    return value


def _read_canonical(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        info = path.stat()
        raw = path.read_bytes()
    except OSError as error:
        raise ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error(
            f"{label} is unreadable"
        ) from error
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or not raw
    ):
        _fail(f"{label} is not one private regular file")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _expected_domain_document(
    document: dict[str, Any],
    *,
    expected_payload: dict[str, Any],
    id_key: str,
    domain: str,
    nested: Mapping[str, Any] | None = None,
    label: str,
) -> str:
    expected = dict(expected_payload)
    if nested:
        expected.update(nested)
    expected_id = content_id(domain, expected_payload)
    expected[id_key] = expected_id
    if canonical_json_bytes(document) != canonical_json_bytes(expected):
        _fail(f"{label} differs from independent reconstruction")
    return _cid(document[id_key], f"{label} ID")


def _spec_document(row: tuple[Any, ...]) -> dict[str, Any]:
    context = observer_v1.public_context_by_key_v1(row[2])
    return {
        "occurrence_index": row[0],
        "occurrence_role": row[1],
        "context_key": row[2],
        "context_id": context.context_id,
        "topology_id": context.topology.topology_id,
        "expected_result_outcome": row[3],
        "expected_model_count_before": row[4],
        "expected_model_count_after": row[5],
        "max_incremental_local_ground_draw_count": row[6],
        "expected_terminal_class": row[7],
        "expected_terminal_code": row[8],
    }


def _empty_catalogue() -> dict[str, Any]:
    return catalogue_replay_v1._catalogue_document([])


def _verify_preregistration(document: dict[str, Any]) -> str:
    initial_catalogue = _empty_catalogue()
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_campaign_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _CAMPAIGN_CONTRACT,
        "profile_key": _CAMPAIGN_PROFILE,
        "initial_model_catalogue_id": initial_catalogue["model_catalogue_id"],
        "initial_registered_model_count": 0,
        "ordered_occurrence_specs": [_spec_document(row) for row in _SEQUENCE],
        "registered_logical_occurrence_count": 5,
        "registered_positive_structural_family_count": 2,
        "registered_negative_control_count": 1,
        "construction_occurrences_preregistered_before_observation": True,
        "local_ground_requires_prior_failed_certificate": True,
        "nearby_model_transfer_allowed": False,
        "full_target_closure_authorized": False,
        "fixed_human_constructor_registry": True,
        "automatic_coordinate_primitive_invention_claimed": False,
        "denominator_row_deletion_allowed": False,
        "official_execution_allowed": False,
    }
    return _expected_domain_document(
        document,
        expected_payload=payload,
        id_key="campaign_preregistration_id",
        domain=CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
        label="campaign preregistration",
    )


def _entry_for_context(
    entries: list[dict[str, Any]], context_key: str
) -> dict[str, Any] | None:
    matches = [item for item in entries if item["target_context_key"] == context_key]
    if len(matches) > 1:
        _fail("catalogue contains duplicate structural entries")
    return matches[0] if matches else None


def _model_and_threshold(
    reuse_document: dict[str, Any],
) -> tuple[robust.PartialSupportIntervalModelV1, robust.RobustThresholdProfileV1]:
    return (
        robust.replay_partial_support_interval_model_bytes_v1(
            canonical_json_bytes(
                _mapping(reuse_document["final_quotient_model"], "reused model")
            )
        ),
        robust.replay_robust_threshold_profile_bytes_v1(
            canonical_json_bytes(
                _mapping(reuse_document["threshold"], "reused threshold")
            )
        ),
    )


def _verify_route(
    document: dict[str, Any],
    *,
    catalogue: dict[str, Any],
    entries: list[dict[str, Any]],
    reuse_by_family: dict[str, dict[str, Any]],
    context_key: str,
) -> None:
    context = observer_v1.public_context_by_key_v1(context_key)
    entry = _entry_for_context(entries, context_key)
    model = threshold = None
    if entry is not None:
        reuse = reuse_by_family[entry["family_key"]]
        model, threshold = _model_and_threshold(reuse)
    catalogue_replay_v1._verify_route(
        document,
        catalogue=catalogue,
        context=context,
        entry=entry,
        model=model,
        threshold=threshold,
    )


def _dispatch_document(
    *,
    catalogue_id: str,
    route_id: str,
    context_key: str,
    selection_outcome: str,
    result_outcome: str,
) -> dict[str, Any]:
    context = observer_v1.public_context_by_key_v1(context_key)
    constructor = {
        "opaque_graph_w5_v0": "W5_CHECKPOINT_OVERLAY_V1",
        "opaque_graph_k6_v0": "K6_CHECKPOINT_OVERLAY_V1",
    }.get(context_key)
    dispatch_outcome = (
        "REUSE_EXACT_MODEL"
        if result_outcome == "EXISTING_MODEL_REUSED"
        else "CONSTRUCT_REGISTERED_MODEL"
        if result_outcome == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"
        else "NO_CERTIFIABLE_CONSTRUCTOR"
    )
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_synthesis_dispatch.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _SYNTHESIS_CONTRACT,
        "profile_key": _SYNTHESIS_PROFILE,
        "initial_model_catalogue_id": catalogue_id,
        "initial_catalogue_query_result_id": route_id,
        "context_key": context_key,
        "context_id": context.context_id,
        "topology_id": context.topology.topology_id,
        "selection_outcome": selection_outcome,
        "dispatch_outcome": dispatch_outcome,
        "constructor_key": constructor if dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL" else None,
        "dispatch_uses_only_public_structural_identity": True,
        "nearby_model_transfer_allowed": False,
        "ground_access_authorized_by_dispatch": False,
        "constructor_must_observe_failed_certificate_before_local_recovery": True,
        "fixed_human_constructor_registry": True,
        "automatic_coordinate_primitive_invention_claimed": False,
    }
    return {
        **payload,
        "synthesis_dispatch_id": content_id(
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN,
            payload,
        ),
    }


def _promotion_document(
    *,
    dispatch: dict[str, Any],
    family: str,
    reuse_document: dict[str, Any],
    entry: dict[str, Any],
    initial_catalogue: dict[str, Any],
    promoted_catalogue: dict[str, Any],
) -> dict[str, Any]:
    source = _mapping(reuse_document["source_result"], f"{family} source")
    changed, preserved, draws = (2, 6, 4_096) if family == "W5" else (1, 19, 8_192)
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_synthesis_promotion.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _SYNTHESIS_CONTRACT,
        "profile_key": _SYNTHESIS_PROFILE,
        "synthesis_dispatch_id": dispatch["synthesis_dispatch_id"],
        "family_key": family,
        "source_recertification_result_id": source["result_id"],
        "source_base_audit_id": source["base_audit_id"],
        "source_base_audit_status": "FAILED_PROOF_FRONTIER",
        "source_final_overlay_id": source["final_overlay_id"],
        "source_final_audit_id": source["final_audit_id"],
        "source_final_audit_status": "CERTIFIED",
        "changed_row_count": changed,
        "preserved_row_count": preserved,
        "incremental_local_ground_draw_count": draws,
        "source_reuse_result_id": reuse_document["result_id"],
        "promoted_model_catalogue_entry_id": entry["model_catalogue_entry_id"],
        "initial_model_catalogue_id": initial_catalogue["model_catalogue_id"],
        "promoted_model_catalogue_id": promoted_catalogue["model_catalogue_id"],
        "local_ground_triggered_only_after_failed_certificate": True,
        "only_failed_frontier_distinctions_restored": True,
        "immutable_query_neutral_model_promoted": True,
        "full_target_checkpoint_closure_built": False,
        "evaluation_exact_kernel_calls": 0,
        "ground_solver_invocations": 0,
    }
    return {
        **payload,
        "promoted_entry": entry,
        "promoted_catalogue": promoted_catalogue,
        "synthesis_promotion_id": content_id(
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN,
            payload,
        ),
    }


def _unsupported_document(dispatch: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_synthesis_unsupported.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _SYNTHESIS_CONTRACT,
        "profile_key": _SYNTHESIS_PROFILE,
        "synthesis_dispatch_id": dispatch["synthesis_dispatch_id"],
        "context_id": dispatch["context_id"],
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "NO_CERTIFIABLE_CONSTRUCTOR_REGISTERED",
        "ground_access_count": 0,
        "observer_call_count": 0,
        "abstract_planner_invocations": 0,
        "nearby_model_transfer_attempted": False,
        "fallback_executed_here": False,
        "infeasibility_certified": False,
    }
    return {
        **payload,
        "unsupported_synthesis_id": content_id(
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN,
            payload,
        ),
    }


def _verify_synthesis_result(
    document: dict[str, Any],
    *,
    expected: tuple[Any, ...],
    entries: list[dict[str, Any]],
    reuse_by_family: dict[str, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], str | None]:
    context_key = expected[2]
    result_outcome = expected[3]
    initial_catalogue = catalogue_replay_v1._catalogue_document(entries)
    initial_route = _mapping(document.get("initial_route"), "initial route")
    _verify_route(
        initial_route,
        catalogue=initial_catalogue,
        entries=entries,
        reuse_by_family=reuse_by_family,
        context_key=context_key,
    )
    selection_outcome = initial_route["selection"]["selection_outcome"]
    dispatch = _dispatch_document(
        catalogue_id=initial_catalogue["model_catalogue_id"],
        route_id=initial_route["catalogue_query_result_id"],
        context_key=context_key,
        selection_outcome=selection_outcome,
        result_outcome=result_outcome,
    )
    if canonical_json_bytes(document.get("dispatch")) != canonical_json_bytes(dispatch):
        _fail("synthesis dispatch differs from independent reconstruction")

    promotion: dict[str, Any] | None = None
    unsupported: dict[str, Any] | None = None
    final_route: dict[str, Any] | None = None
    reuse_document: dict[str, Any] | None = None
    final_entries = list(entries)
    new_verification_id: str | None = None
    if result_outcome == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED":
        family = "W5" if context_key == "opaque_graph_w5_v0" else "K6"
        reuse_document = _mapping(document.get("reuse_result"), f"{family} reuse result")
        reuse_bytes = canonical_json_bytes(reuse_document)
        verification = (
            w5_verifier_v1.verify_heldout_overlay_abstract_reuse_bytes_v1(reuse_bytes)
            if family == "W5"
            else k6_verifier_v1.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
                reuse_bytes
            )
        )
        new_verification_id = verification.verification_id
        entry = catalogue_replay_v1._entry_document(
            family, reuse_bytes, verification.verification_id
        )
        final_entries.append(entry)
        final_entries.sort(key=lambda item: (0 if item["family_key"] == "W5" else 1))
        promoted_catalogue = catalogue_replay_v1._catalogue_document(final_entries)
        promotion = _promotion_document(
            dispatch=dispatch,
            family=family,
            reuse_document=reuse_document,
            entry=entry,
            initial_catalogue=initial_catalogue,
            promoted_catalogue=promoted_catalogue,
        )
        if canonical_json_bytes(document.get("promotion")) != canonical_json_bytes(promotion):
            _fail("synthesis promotion differs from independently verified model")
        reuse_by_family[family] = reuse_document
        final_route = _mapping(document.get("final_route"), "postpromotion route")
        _verify_route(
            final_route,
            catalogue=promoted_catalogue,
            entries=final_entries,
            reuse_by_family=reuse_by_family,
            context_key=context_key,
        )
        final_catalogue = promoted_catalogue
    elif result_outcome == "EXISTING_MODEL_REUSED":
        if document.get("promotion") is not None or document.get("unsupported") is not None or document.get("reuse_result") is not None:
            _fail("exact reuse branch contains construction evidence")
        final_route = _mapping(document.get("final_route"), "exact reuse final route")
        if canonical_json_bytes(final_route) != canonical_json_bytes(initial_route):
            _fail("exact reuse branch changed its one routed plan")
        final_catalogue = initial_catalogue
    else:
        if document.get("promotion") is not None or document.get("reuse_result") is not None or document.get("final_route") is not None:
            _fail("unsupported branch contains execution evidence")
        unsupported = _unsupported_document(dispatch)
        if canonical_json_bytes(document.get("unsupported")) != canonical_json_bytes(unsupported):
            _fail("unsupported closure differs from no-access reconstruction")
        final_catalogue = initial_catalogue

    if canonical_json_bytes(document.get("final_catalogue")) != canonical_json_bytes(final_catalogue):
        _fail("synthesis final catalogue differs from immutable replay")
    constructed = promotion is not None
    reused = result_outcome == "EXISTING_MODEL_REUSED"
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_synthesis_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _SYNTHESIS_CONTRACT,
        "profile_key": _SYNTHESIS_PROFILE,
        "initial_catalogue_query_result_id": initial_route["catalogue_query_result_id"],
        "synthesis_dispatch_id": dispatch["synthesis_dispatch_id"],
        "synthesis_promotion_id": None if promotion is None else promotion["synthesis_promotion_id"],
        "unsupported_synthesis_id": None if unsupported is None else unsupported["unsupported_synthesis_id"],
        "final_model_catalogue_id": final_catalogue["model_catalogue_id"],
        "final_catalogue_query_result_id": None if final_route is None else final_route["catalogue_query_result_id"],
        "result_outcome": result_outcome,
        "model_construction_executed": constructed,
        "fresh_postconstruction_ground_draw_count": 0,
        "fresh_postconstruction_observer_call_count": 0,
        "fresh_postconstruction_abstract_planner_invocations": 0 if final_route is None else 1,
        "multi_step_plan_mainly_completed_in_abstract_model": final_route is not None,
        "ground_distinctions_restored_only_after_certificate_failure": constructed,
        "fixed_human_constructor_registry": True,
        "automatic_coordinate_primitive_invention_claimed": False,
        "broad_cross_domain_generalization_claimed": False,
        "official_execution_allowed": False,
    }
    nested = {
        "initial_route": initial_route,
        "dispatch": dispatch,
        "promotion": promotion,
        "unsupported": unsupported,
        "final_catalogue": final_catalogue,
        "final_route": final_route,
        "reuse_result": reuse_document if constructed else None,
    }
    result_id = _expected_domain_document(
        document,
        expected_payload=payload,
        id_key="world_model_synthesis_result_id",
        domain=CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN,
        nested=nested,
        label="world-model synthesis result",
    )
    return result_id, final_entries, new_verification_id


def _verify_occurrence(
    document: dict[str, Any],
    *,
    preregistration_id: str,
    expected: tuple[Any, ...],
    entries: list[dict[str, Any]],
    reuse_by_family: dict[str, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], str | None]:
    result_document = _mapping(
        document.get("world_model_synthesis_result"), "embedded synthesis result"
    )
    result_id, final_entries, verification_id = _verify_synthesis_result(
        result_document,
        expected=expected,
        entries=entries,
        reuse_by_family=reuse_by_family,
    )
    input_catalogue = catalogue_replay_v1._catalogue_document(entries)
    output_catalogue = catalogue_replay_v1._catalogue_document(final_entries)
    spec = _spec_document(expected)
    payload = {
        "schema": "acfqp.construction_k7_observation_driven_campaign_occurrence.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _CAMPAIGN_CONTRACT,
        "profile_key": _CAMPAIGN_PROFILE,
        "campaign_preregistration_id": preregistration_id,
        "occurrence_spec": spec,
        "input_model_catalogue_id": input_catalogue["model_catalogue_id"],
        "world_model_synthesis_result_id": result_id,
        "output_model_catalogue_id": output_catalogue["model_catalogue_id"],
        "result_outcome": expected[3],
        "terminal_class": expected[7],
        "terminal_code": expected[8],
        "incremental_local_ground_draw_count": expected[6],
        "postconstruction_ground_draw_count": 0,
        "multi_step_plan_mainly_completed_in_abstract_model": expected[7] == "PLAN_CERTIFICATE",
        "closure_denominator_contribution": 1,
        "certificate_coverage_denominator_contribution": 1,
        "future_economics_denominator_contribution": 1,
        "world_model_synthesis_result": result_document,
        "official_execution_allowed": False,
    }
    occurrence_id = _expected_domain_document(
        document,
        expected_payload=payload,
        id_key="campaign_occurrence_id",
        domain=CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN,
        label=f"campaign occurrence {expected[0]}",
    )
    return occurrence_id, final_entries, verification_id


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignIndependentVerificationV1:
    _issuer: InitVar[object]
    preregistration_id: str
    occurrence_ids: tuple[str, ...]
    closure_id: str
    w5_reuse_verification_id: str
    k6_reuse_verification_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER or len(self.occurrence_ids) != 5:
            _fail("independent campaign verification is caller-minted")
        for value, label in (
            (self.preregistration_id, "verified preregistration"),
            (self.closure_id, "verified closure"),
            (self.w5_reuse_verification_id, "W5 reuse verification"),
            (self.k6_reuse_verification_id, "K6 reuse verification"),
            *((value, "verified occurrence") for value in self.occurrence_ids),
        ):
            _cid(value, label)
        object.__setattr__(
            self, "_verification_id", content_id(VERIFICATION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_campaign_occurrence_ids": list(self.occurrence_ids),
            "campaign_closure_id": self.closure_id,
            "w5_reuse_independent_verification_id": self.w5_reuse_verification_id,
            "k6_reuse_independent_verification_id": self.k6_reuse_verification_id,
            "producer_import_count": 0,
            "physical_campaign_bytes_verified": True,
            "both_local_recovery_chains_independently_replayed": True,
            "two_exact_model_reuses_independently_replanned": True,
            "negative_control_no_access_independently_replayed": True,
            "catalogue_epoch_lineage_independently_replayed": True,
            "all_five_denominator_rows_retained": True,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("independent verification identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_observation_driven_campaign_directory_bytes_v1(
    campaign_directory: str | Path,
) -> ObservationDrivenCampaignIndependentVerificationV1:
    """Replay one seven-file campaign without importing any producer."""

    directory = Path(campaign_directory)
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or stat.S_IMODE(directory.stat().st_mode) & 0o077
        or tuple(path.name for path in sorted(directory.iterdir())) != EXPECTED_FILENAMES
    ):
        _fail("campaign directory inventory or privacy changed")
    raws: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    for filename in EXPECTED_FILENAMES:
        raw, document = _read_canonical(directory / filename, filename)
        raws[filename] = raw
        documents[filename] = document
    preregistration_id = _verify_preregistration(documents[PREREGISTRATION_FILENAME])
    entries: list[dict[str, Any]] = []
    reuse_by_family: dict[str, dict[str, Any]] = {}
    verification_ids: dict[str, str] = {}
    occurrence_ids: list[str] = []
    catalogue_epochs = [_empty_catalogue()["model_catalogue_id"]]
    for filename, expected in zip(OCCURRENCE_FILENAMES, _SEQUENCE, strict=True):
        occurrence_id, entries, verification_id = _verify_occurrence(
            documents[filename],
            preregistration_id=preregistration_id,
            expected=expected,
            entries=entries,
            reuse_by_family=reuse_by_family,
        )
        occurrence_ids.append(occurrence_id)
        catalogue_epochs.append(
            catalogue_replay_v1._catalogue_document(entries)["model_catalogue_id"]
        )
        if verification_id is not None:
            verification_ids["W5" if expected[2] == "opaque_graph_w5_v0" else "K6"] = verification_id
    if set(verification_ids) != {"W5", "K6"}:
        _fail("campaign did not independently verify both model constructions")
    prefix_commits = [
        {
            "filename": filename,
            "byte_count": len(raws[filename]),
            "bytes_sha256": hashlib.sha256(raws[filename]).hexdigest(),
        }
        for filename in (PREREGISTRATION_FILENAME, *OCCURRENCE_FILENAMES)
    ]
    closure_payload = {
        "schema": "acfqp.construction_k7_observation_driven_campaign_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": _CAMPAIGN_CONTRACT,
        "profile_key": _CAMPAIGN_PROFILE,
        "campaign_preregistration_id": preregistration_id,
        "ordered_campaign_occurrence_ids": occurrence_ids,
        "ordered_result_outcomes": [row[3] for row in _SEQUENCE],
        "ordered_catalogue_epoch_ids": catalogue_epochs,
        "ordered_prefix_file_commits": prefix_commits,
        "registered_logical_occurrence_count": 5,
        "closed_logical_occurrence_count": 5,
        "plan_certificate_count": 4,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": 1,
        "model_construction_count": 2,
        "exact_model_reuse_count": 2,
        "unsupported_no_access_count": 1,
        "final_registered_model_count": 2,
        "cumulative_incremental_local_ground_draw_count": 12_288,
        "expected_cumulative_incremental_local_ground_draw_count": 12_288,
        "postconstruction_ground_draw_count": 0,
        "nearby_model_transfer_attempt_count": 0,
        "all_positive_plans_multi_step_and_abstract_first": True,
        "catalogue_epochs_immutable": True,
        "denominator_row_deletion_detected": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": "NOT_RUN",
        "counter_completeness_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
    }
    closure_id = _expected_domain_document(
        documents[CLOSURE_FILENAME],
        expected_payload=closure_payload,
        id_key="campaign_closure_id",
        domain=CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN,
        label="campaign closure",
    )
    return ObservationDrivenCampaignIndependentVerificationV1(
        _RESULT_ISSUER,
        preregistration_id,
        tuple(occurrence_ids),
        closure_id,
        verification_ids["W5"],
        verification_ids["K6"],
    )


__all__ = (
    "ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error",
    "EXPECTED_FILENAMES",
    "LOCAL_DOMAINS",
    "ObservationDrivenCampaignIndependentVerificationV1",
    "verify_observation_driven_campaign_directory_bytes_v1",
)
