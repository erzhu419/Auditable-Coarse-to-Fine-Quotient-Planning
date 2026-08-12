"""Preregistered learn-once/reuse-many structural world-model campaign.

The campaign starts from an empty immutable model catalogue.  It constructs a
W5 model only after that constructor's abstract certificate fails, immediately
reuses the promoted model for a fresh W5 occurrence, repeats the same sequence
for K6, and finally routes the nearby K6-minus-edge negative control to a typed
no-access closure.  Every occurrence is preregistered before either constructor
runs and every catalogue epoch is immutable.

This remains a bounded construction fixture.  The registered constructor
grammar is human supplied; coordinate-language invention, broad domain
generalization, scalar economics, and official execution are not claimed.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_catalogue_query_router_v1 as router_v1
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v1 as synthesis_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.141"
PROFILE_KEY = "construction_k7_observation_driven_world_model_campaign_v1"

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
OCCURRENCE_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN
CLOSURE_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREREGISTRATION_DOMAIN, OCCURRENCE_DOMAIN, CLOSURE_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-driven campaign domains are not central")

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

_PREREGISTRATION_ISSUER = object()
_ROW_ISSUER = object()
_CLOSURE_ISSUER = object()
_RESULT_ISSUER = object()

_EXPECTED_SEQUENCE = (
    (
        1,
        "W5_CONSTRUCT",
        "opaque_graph_w5_v0",
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        0,
        1,
        4_096,
        "PLAN_CERTIFICATE",
        "MODEL_SYNTHESIZED_AND_ABSTRACT_CERTIFIED",
    ),
    (
        2,
        "W5_REUSE",
        "opaque_graph_w5_v0",
        "EXISTING_MODEL_REUSED",
        1,
        1,
        0,
        "PLAN_CERTIFICATE",
        "ABSTRACT_CERTIFIED",
    ),
    (
        3,
        "K6_CONSTRUCT",
        "opaque_graph_k6_v0",
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        1,
        2,
        8_192,
        "PLAN_CERTIFICATE",
        "MODEL_SYNTHESIZED_AND_ABSTRACT_CERTIFIED",
    ),
    (
        4,
        "K6_REUSE",
        "opaque_graph_k6_v0",
        "EXISTING_MODEL_REUSED",
        2,
        2,
        0,
        "PLAN_CERTIFICATE",
        "ABSTRACT_CERTIFIED",
    ),
    (
        5,
        "K6_MINUS_EDGE_UNSUPPORTED",
        "opaque_graph_k6_minus_edge_v0",
        "NO_CERTIFIABLE_CONSTRUCTOR",
        2,
        2,
        0,
        "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "NO_CERTIFIABLE_CONSTRUCTOR_REGISTERED",
    ),
)


class ConstructionK7ObservationDrivenWorldModelCampaignV1Error(RuntimeError):
    """The preregistered sequence, catalogue lineage, or artifact bytes changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDrivenWorldModelCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenWorldModelCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _logical(role: str, parent: str) -> str:
    return hashlib.sha256(f"{PROFILE_KEY}:{role}:{parent}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignOccurrenceSpecV1:
    occurrence_index: int
    occurrence_role: str
    context_key: str
    context_id: str
    topology_id: str
    expected_result_outcome: str
    expected_model_count_before: int
    expected_model_count_after: int
    max_incremental_local_ground_draw_count: int
    expected_terminal_class: str
    expected_terminal_code: str

    def __post_init__(self) -> None:
        expected = _EXPECTED_SEQUENCE[self.occurrence_index - 1] if type(self.occurrence_index) is int and 1 <= self.occurrence_index <= len(_EXPECTED_SEQUENCE) else None
        context = observer_v1.public_context_by_key_v1(self.context_key)
        if (
            expected is None
            or (
                self.occurrence_index,
                self.occurrence_role,
                self.context_key,
                self.expected_result_outcome,
                self.expected_model_count_before,
                self.expected_model_count_after,
                self.max_incremental_local_ground_draw_count,
                self.expected_terminal_class,
                self.expected_terminal_code,
            )
            != expected
            or self.context_id != context.context_id
            or self.topology_id != context.topology.topology_id
        ):
            _fail("campaign occurrence spec changed")
        _cid(self.context_id, "campaign context")
        _cid(self.topology_id, "campaign topology")

    def to_document(self) -> dict[str, Any]:
        return {
            "occurrence_index": self.occurrence_index,
            "occurrence_role": self.occurrence_role,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "expected_result_outcome": self.expected_result_outcome,
            "expected_model_count_before": self.expected_model_count_before,
            "expected_model_count_after": self.expected_model_count_after,
            "max_incremental_local_ground_draw_count": (
                self.max_incremental_local_ground_draw_count
            ),
            "expected_terminal_class": self.expected_terminal_class,
            "expected_terminal_code": self.expected_terminal_code,
        }


def _registered_specs() -> tuple[ObservationDrivenCampaignOccurrenceSpecV1, ...]:
    rows = []
    for row in _EXPECTED_SEQUENCE:
        context = observer_v1.public_context_by_key_v1(row[2])
        rows.append(
            ObservationDrivenCampaignOccurrenceSpecV1(
                row[0],
                row[1],
                row[2],
                context.context_id,
                context.topology.topology_id,
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignPreregistrationV1:
    _issuer: InitVar[object]
    initial_catalogue_id: str
    specs: tuple[ObservationDrivenCampaignOccurrenceSpecV1, ...]
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREREGISTRATION_ISSUER
            or type(self.specs) is not tuple
            or self.specs != _registered_specs()
        ):
            _fail("campaign preregistration changed")
        _cid(self.initial_catalogue_id, "initial empty catalogue")
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "initial_model_catalogue_id": self.initial_catalogue_id,
            "initial_registered_model_count": 0,
            "ordered_occurrence_specs": [item.to_document() for item in self.specs],
            "registered_logical_occurrence_count": len(self.specs),
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

    @property
    def preregistration_id(self) -> str:
        current = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if current != self._preregistration_id:
            _fail("campaign preregistration identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_preregistration_id": self.preregistration_id,
        }


def _terminal_facts(
    spec: ObservationDrivenCampaignOccurrenceSpecV1,
    result: synthesis_v1.ObservationDrivenWorldModelSynthesisResultV1,
) -> tuple[str, str, int]:
    if result.promotion is not None:
        ground = result.promotion.incremental_ground_draw_count
    else:
        ground = 0
    return spec.expected_terminal_class, spec.expected_terminal_code, ground


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignOccurrenceV1:
    _issuer: InitVar[object]
    preregistration_id: str
    spec: ObservationDrivenCampaignOccurrenceSpecV1
    input_catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1 = field(
        repr=False, compare=False
    )
    result: synthesis_v1.ObservationDrivenWorldModelSynthesisResultV1 = field(
        repr=False, compare=False
    )
    _occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ROW_ISSUER
            or type(self.spec) is not ObservationDrivenCampaignOccurrenceSpecV1
            or type(self.input_catalogue)
            is not catalogue_v1.HeldoutReusableModelCatalogueV1
            or type(self.result)
            is not synthesis_v1.ObservationDrivenWorldModelSynthesisResultV1
        ):
            _fail("campaign occurrence is caller-minted")
        _cid(self.preregistration_id, "occurrence preregistration")
        terminal_class, terminal_code, ground = _terminal_facts(self.spec, self.result)
        document = self.result.to_document()
        if (
            self.result.initial_route.selection.catalogue_id
            != self.input_catalogue.catalogue_id
            or len(self.input_catalogue.entries)
            != self.spec.expected_model_count_before
            or self.result.dispatch.context_key != self.spec.context_key
            or self.result.dispatch.context_id != self.spec.context_id
            or document["result_outcome"] != self.spec.expected_result_outcome
            or len(self.result.final_catalogue.entries)
            != self.spec.expected_model_count_after
            or ground != self.spec.max_incremental_local_ground_draw_count
            or terminal_class != self.spec.expected_terminal_class
            or terminal_code != self.spec.expected_terminal_code
        ):
            _fail("campaign occurrence crossed its preregistered route")
        if self.spec.expected_result_outcome == "EXISTING_MODEL_REUSED" and (
            self.result.promotion is not None
            or self.result.unsupported is not None
            or self.result.initial_route.plan is None
        ):
            _fail("exact reuse occurrence executed construction")
        if self.spec.expected_result_outcome == "NO_CERTIFIABLE_CONSTRUCTOR" and (
            self.result.unsupported is None
            or self.result.final_route is not None
            or self.result.final_catalogue.catalogue_id
            != self.input_catalogue.catalogue_id
        ):
            _fail("negative control was not one no-access closure")
        object.__setattr__(
            self, "_occurrence_id", content_id(OCCURRENCE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        terminal_class, terminal_code, ground = _terminal_facts(self.spec, self.result)
        return {
            "schema": "acfqp.construction_k7_observation_driven_campaign_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "occurrence_spec": self.spec.to_document(),
            "input_model_catalogue_id": self.input_catalogue.catalogue_id,
            "world_model_synthesis_result_id": self.result.result_id,
            "output_model_catalogue_id": self.result.final_catalogue.catalogue_id,
            "result_outcome": self.result.to_document()["result_outcome"],
            "terminal_class": terminal_class,
            "terminal_code": terminal_code,
            "incremental_local_ground_draw_count": ground,
            "postconstruction_ground_draw_count": 0,
            "multi_step_plan_mainly_completed_in_abstract_model": (
                self.result.final_route is not None
            ),
            "closure_denominator_contribution": 1,
            "certificate_coverage_denominator_contribution": 1,
            "future_economics_denominator_contribution": 1,
            "world_model_synthesis_result": self.result.to_document(),
            "official_execution_allowed": False,
        }

    @property
    def occurrence_id(self) -> str:
        current = content_id(OCCURRENCE_DOMAIN, self._payload())
        if current != self._occurrence_id:
            _fail("campaign occurrence identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignFileCommitV1:
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.filename) is not str
            or self.filename not in EXPECTED_FILENAMES
            or type(self.byte_count) is not int
            or self.byte_count <= 0
            or type(self.bytes_sha256) is not str
            or len(self.bytes_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.bytes_sha256)
        ):
            _fail("campaign file commit changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
        }


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignClosureV1:
    _issuer: InitVar[object]
    preregistration: ObservationDrivenCampaignPreregistrationV1
    rows: tuple[ObservationDrivenCampaignOccurrenceV1, ...]
    prefix_commits: tuple[ObservationDrivenCampaignFileCommitV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        rows = tuple(self.rows)
        commits = tuple(self.prefix_commits)
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.preregistration) is not ObservationDrivenCampaignPreregistrationV1
            or len(rows) != 5
            or tuple(row.spec for row in rows) != self.preregistration.specs
            or any(row.preregistration_id != self.preregistration.preregistration_id for row in rows)
            or rows[0].input_catalogue.catalogue_id
            != self.preregistration.initial_catalogue_id
            or any(
                rows[index].result.final_catalogue.catalogue_id
                != rows[index + 1].input_catalogue.catalogue_id
                for index in range(4)
            )
            or tuple(item.filename for item in commits)
            != (PREREGISTRATION_FILENAME, *OCCURRENCE_FILENAMES)
            or tuple(item.family_key for item in rows[-1].result.final_catalogue.entries)
            != ("W5", "K6")
        ):
            _fail("campaign closure graph changed")
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "prefix_commits", commits)
        object.__setattr__(
            self, "_closure_id", content_id(CLOSURE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        ground = sum(
            _terminal_facts(row.spec, row.result)[2] for row in self.rows
        )
        return {
            "schema": "acfqp.construction_k7_observation_driven_campaign_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "ordered_campaign_occurrence_ids": [row.occurrence_id for row in self.rows],
            "ordered_result_outcomes": [
                row.result.to_document()["result_outcome"] for row in self.rows
            ],
            "ordered_catalogue_epoch_ids": [
                self.preregistration.initial_catalogue_id,
                *[row.result.final_catalogue.catalogue_id for row in self.rows],
            ],
            "ordered_prefix_file_commits": [
                item.to_document() for item in self.prefix_commits
            ],
            "registered_logical_occurrence_count": 5,
            "closed_logical_occurrence_count": 5,
            "plan_certificate_count": 4,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 1,
            "model_construction_count": 2,
            "exact_model_reuse_count": 2,
            "unsupported_no_access_count": 1,
            "final_registered_model_count": 2,
            "cumulative_incremental_local_ground_draw_count": ground,
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

    @property
    def closure_id(self) -> str:
        current = content_id(CLOSURE_DOMAIN, self._payload())
        if current != self._closure_id:
            _fail("campaign closure identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class ObservationDrivenCampaignResultV1:
    _issuer: InitVar[object]
    preregistration: ObservationDrivenCampaignPreregistrationV1
    rows: tuple[ObservationDrivenCampaignOccurrenceV1, ...]
    closure: ObservationDrivenCampaignClosureV1
    file_commits: tuple[ObservationDrivenCampaignFileCommitV1, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.preregistration) is not ObservationDrivenCampaignPreregistrationV1
            or tuple(self.rows) != self.closure.rows
            or self.closure.preregistration != self.preregistration
            or tuple(self.file_commits[:-1]) != self.closure.prefix_commits
            or tuple(item.filename for item in self.file_commits) != EXPECTED_FILENAMES
        ):
            _fail("campaign result graph changed")
        object.__setattr__(
            self, "_result_id", content_id(RESULT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_driven_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "ordered_campaign_occurrence_ids": [row.occurrence_id for row in self.rows],
            "campaign_closure_id": self.closure.closure_id,
            "ordered_file_commits": [item.to_document() for item in self.file_commits],
            "durable_campaign_graph_complete": True,
            "independent_campaign_verification_present": False,
            "automatic_coordinate_primitive_invention_claimed": False,
            "broad_cross_domain_generalization_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("campaign result identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_result_id": self.result_id}


def _prepare_directory(path: Path) -> None:
    if path.exists():
        _fail("campaign directory must not already exist")
    path.mkdir(mode=0o700, parents=False)
    if (
        path.is_symlink()
        or not path.is_dir()
        or stat.S_IMODE(path.stat().st_mode) != 0o700
    ):
        _fail("campaign directory is not one private directory")


def _write_commit(
    directory: Path,
    filename: str,
    document: dict[str, Any],
) -> ObservationDrivenCampaignFileCommitV1:
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
    return ObservationDrivenCampaignFileCommitV1(
        filename, len(raw), hashlib.sha256(raw).hexdigest()
    )


def run_observation_driven_world_model_campaign_v1(
    *, campaign_directory: str | os.PathLike[str]
) -> ObservationDrivenCampaignResultV1:
    """Run the preregistered five-occurrence adaptive model campaign."""

    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())
    preregistration = ObservationDrivenCampaignPreregistrationV1(
        _PREREGISTRATION_ISSUER, catalogue.catalogue_id, _registered_specs()
    )
    directory = Path(campaign_directory)
    _prepare_directory(directory)
    commits = [
        _write_commit(directory, PREREGISTRATION_FILENAME, preregistration.to_document())
    ]
    rows: list[ObservationDrivenCampaignOccurrenceV1] = []
    reuse_bytes_by_family: dict[str, bytes] = {}
    for spec, filename in zip(preregistration.specs, OCCURRENCE_FILENAMES, strict=True):
        family = "W5" if spec.context_key == "opaque_graph_w5_v0" else "K6"
        selected_bytes = (
            reuse_bytes_by_family.get(family)
            if spec.expected_result_outcome == "EXISTING_MODEL_REUSED"
            else None
        )
        result = synthesis_v1.run_observation_driven_world_model_synthesis_v1(
            catalogue,
            observer_v1.public_context_by_key_v1(spec.context_key),
            logical_occurrence_id=_logical(
                f"occurrence-{spec.occurrence_index}", preregistration.preregistration_id
            ),
            occurrence_ordinal=spec.occurrence_index,
            selected_reuse_result_bytes=selected_bytes,
        )
        if result.promotion is not None:
            if result.reuse_result_document is None:
                _fail("constructed occurrence omitted reusable model bytes")
            reuse_bytes_by_family[family] = canonical_json_bytes(
                result.reuse_result_document
            )
        row = ObservationDrivenCampaignOccurrenceV1(
            _ROW_ISSUER, preregistration.preregistration_id, spec, catalogue, result
        )
        rows.append(row)
        commits.append(_write_commit(directory, filename, row.to_document()))
        catalogue = result.final_catalogue
    closure = ObservationDrivenCampaignClosureV1(
        _CLOSURE_ISSUER, preregistration, tuple(rows), tuple(commits)
    )
    commits.append(_write_commit(directory, CLOSURE_FILENAME, closure.to_document()))
    return ObservationDrivenCampaignResultV1(
        _RESULT_ISSUER, preregistration, tuple(rows), closure, tuple(commits)
    )


def verify_observation_driven_world_model_campaign_v1(
    result: ObservationDrivenCampaignResultV1,
    *,
    campaign_directory: str | os.PathLike[str],
) -> ObservationDrivenCampaignResultV1:
    """Replay the in-memory identities and all seven durable artifact bytes."""

    if type(result) is not ObservationDrivenCampaignResultV1:
        _fail("campaign verifier rejects foreign values")
    result.__post_init__(_RESULT_ISSUER)
    reuse_bytes_by_family: dict[str, bytes] = {}
    for row in result.rows:
        synthesis_v1.verify_observation_driven_world_model_synthesis_v1(row.result)
        family = "W5" if row.spec.context_key == "opaque_graph_w5_v0" else "K6"
        if row.result.promotion is not None:
            assert row.result.reuse_result_document is not None
            reuse_bytes_by_family[family] = canonical_json_bytes(
                row.result.reuse_result_document
            )
        elif row.result.dispatch.dispatch_outcome == "REUSE_EXACT_MODEL":
            router_v1.verify_heldout_catalogue_query_result_v1(
                row.result.initial_route,
                selected_reuse_result_bytes=reuse_bytes_by_family[family],
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
    "ConstructionK7ObservationDrivenWorldModelCampaignV1Error",
    "EXPECTED_FILENAMES",
    "LOCAL_DOMAINS",
    "ObservationDrivenCampaignClosureV1",
    "ObservationDrivenCampaignFileCommitV1",
    "ObservationDrivenCampaignOccurrenceSpecV1",
    "ObservationDrivenCampaignOccurrenceV1",
    "ObservationDrivenCampaignPreregistrationV1",
    "ObservationDrivenCampaignResultV1",
    "run_observation_driven_world_model_campaign_v1",
    "verify_observation_driven_world_model_campaign_v1",
)
