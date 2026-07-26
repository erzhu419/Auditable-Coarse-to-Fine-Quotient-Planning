"""Registered two-domain observed/statistical held-out planning campaign.

V0-059 composes two deliberately different reusable-model authorities:

* LMB uses the V0-058 observation-only typed program closure, an honest
  partial RAPM, and certificate-triggered exact target-row recovery.
* G2048 uses the already-known exact D4 structural quotient as a registered
  human prior, but learns its six binary transition rows only from an
  aggregated offline sample ledger.  A finite, exact-rational Hoeffding union
  proof turns those rows into a simultaneous statistical envelope.

The production campaign receives no G2048 kernel.  It plans a preregistered
family of point and orbit-uniform H2 queries in the statistical quotient.
The G2048 kernel is accepted only by the standalone verifier.  Consequently
this module does not claim automatic symmetry discovery, unknown primitive
invention, raw symbolization, exact-sound statistical certificates, sample
savings, or cross-domain shared coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
import math
from itertools import product
from typing import Any, Mapping

from acfqp.domains.g2048 import (
    D4_ELEMENTS,
    G2048SafeChainKernel,
    G2048State,
    G2048Status,
    SAFE_CHAIN_BASE_STATE,
    inverse_d4,
    orbit,
    safe_chain_query,
    transform_action,
    transform_state,
)
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.domains.semantic import (
    G2048RelativeSurvivorAdapter,
    G2048RelativeSurvivorLabel,
)
from acfqp.observation_partial_rapm_v1 import (
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PreregisteredObservationAuthorityV1,
)
from acfqp.observed_program_closure_heldout_h2_v1 import (
    ProgramClosureHeldOutH2PreregistrationV1,
    ProgramClosureHeldOutH2ResultV1,
    ProgramClosureHeldOutPlanProposalV1,
    ProgramClosureHeldOutSelectedAuditV1,
    preregister_lmb_program_closure_heldout_h2_v1,
    run_lmb_program_closure_heldout_h2_v1,
    verify_lmb_program_closure_heldout_h2_v1,
)
import acfqp.observed_program_closure_heldout_h2_v1 as lmb_heldout
from acfqp.observed_program_closure_synthesis_v1 import (
    ObservedProgramClosureResultV1,
    synthesize_observed_lmb_program_closure_partial_rapm_v1,
    verify_observed_lmb_program_closure_partial_rapm_v1,
)
from acfqp.partial_sound_audit_v1 import PartialAuditOutcome
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.symmetry import (
    FiniteGroupAction,
    OrbitCellKind,
    build_validate_solve_d4,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.23.0"
PROFILE_KEY = "multidomain_observed_statistical_heldout_campaign_v0"
G2048_PROFILE_KEY = "g2048_d4_empirical_hoeffding_partial_rapm_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_MULTIDOMAIN_OBSERVED_STATISTICAL_HELDOUT_CAMPAIGN"
)
STATISTICAL_CERTIFIED = "CERTIFIED_STATISTICAL_H2_PLAN"
EXACT_CERTIFIED = "CERTIFIED_EXACT_H2_PLAN"

G2048_SAMPLE_COUNT_PER_ROW = 65_536
G2048_STATISTICAL_ROW_COUNT = 6
G2048_TOTAL_OFFLINE_SAMPLES = (
    G2048_SAMPLE_COUNT_PER_ROW * G2048_STATISTICAL_ROW_COUNT
)
HOEFFDING_RADIUS = Fraction(1, 128)
HOEFFDING_ALPHA = Fraction(1, 100)
HOEFFDING_COORDINATE_OBLIGATIONS = 12
HOEFFDING_PER_COORDINATE_TAIL_UPPER = Fraction(1, 1400)
HOEFFDING_FAMILY_TAIL_UPPER = Fraction(3, 350)
HOEFFDING_CONFIDENCE_LOWER = Fraction(347, 350)

IMPLEMENTATION_SHA256 = (
    "fe229af2d937dec412d28c3e9f7cefd949038714a9ca3bf46d0dda1ffe9bfdff"
)

DOMAIN_TAGS = {
    "primitive_schema": "acfqp:multidomain-primitive-schema:v1",
    "statistical_cell": "acfqp:g2048-statistical-cell:v1",
    "statistical_row_catalogue": "acfqp:g2048-statistical-row-catalogue:v1",
    "statistical_catalogue": "acfqp:g2048-statistical-catalogue:v1",
    "sample_count_row": "acfqp:g2048-aggregated-sample-count-row:v1",
    "sample_ledger": "acfqp:g2048-aggregated-sample-ledger:v1",
    "calibration": "acfqp:g2048-hoeffding-calibration:v1",
    "probability_interval": "acfqp:g2048-probability-interval:v1",
    "statistical_transition": "acfqp:g2048-statistical-transition:v1",
    "statistical_model": "acfqp:g2048-statistical-rapm:v1",
    "occurrence_spec": "acfqp:multidomain-occurrence-spec:v1",
    "preregistration": "acfqp:multidomain-campaign-preregistration:v1",
    "g2048_policy": "acfqp:g2048-statistical-policy:v1",
    "g2048_certificate": "acfqp:g2048-statistical-certificate:v1",
    "occurrence_result": "acfqp:multidomain-occurrence-result:v1",
    "work": "acfqp:multidomain-campaign-work:v1",
    "result": "acfqp:multidomain-campaign-result:v1",
    "verification": "acfqp:multidomain-campaign-verification:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-059 content domains must be unique")


class MultiDomainStatisticalCampaignInvariantViolation(ValueError):
    """One registered source, envelope, campaign or replay is inconsistent."""


class CampaignDomain(str, Enum):
    LMB = "layered_matching_buffer"
    G2048 = "g2048_safe_chain"


class StatisticalCellKind(str, Enum):
    ACTIVE = "ACTIVE"
    FAILURE = "FAILURE"
    TERMINAL = "TERMINAL"


class EvidenceLevel(str, Enum):
    EXACT_SOUND = "exact_sound"
    STATISTICAL_HIGH_PROBABILITY = "statistical_high_probability"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise MultiDomainStatisticalCampaignInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            f"{field} must be exact"
        )
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _exact_tuple(value: Any, item_type: type, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            f"{field} rejects nested runtime-type substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            f"{path} contains a nested runtime-type substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                f"{path} tuple length differs"
            )
        for index, (left, right) in enumerate(zip(claimed, expected)):
            _runtime_shape(left, right, f"{path}[{index}]")
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


@dataclass(frozen=True, slots=True)
class PrimitiveSchemaBindingV1:
    domain: CampaignDomain
    structural_key: str
    primitive_names: tuple[str, ...]
    operator_names: tuple[str, ...]
    abstraction_prior: str
    automatically_selected_within_schema: bool

    def __post_init__(self) -> None:
        if (
            type(self.domain) is not CampaignDomain
            or type(self.structural_key) is not str
            or not self.structural_key
            or type(self.primitive_names) is not tuple
            or not self.primitive_names
            or any(type(item) is not str or not item for item in self.primitive_names)
            or self.primitive_names != tuple(sorted(set(self.primitive_names)))
            or type(self.operator_names) is not tuple
            or not self.operator_names
            or any(type(item) is not str or not item for item in self.operator_names)
            or self.operator_names != tuple(sorted(set(self.operator_names)))
            or type(self.abstraction_prior) is not str
            or not self.abstraction_prior
            or type(self.automatically_selected_within_schema) is not bool
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "primitive schema registration is noncanonical"
            )
        if (
            self.domain is CampaignDomain.LMB
            and self.automatically_selected_within_schema is not True
        ) or (
            self.domain is CampaignDomain.G2048
            and self.automatically_selected_within_schema is not False
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "domain abstraction-prior claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_primitive_schema.v1",
            "schema_version": SCHEMA_VERSION,
            "domain": self.domain.value,
            "structural_key": self.structural_key,
            "primitive_names": list(self.primitive_names),
            "operator_names": list(self.operator_names),
            "abstraction_prior": self.abstraction_prior,
            "automatically_selected_within_schema": (
                self.automatically_selected_within_schema
            ),
        }

    @property
    def schema_id(self) -> str:
        return _content_id("primitive_schema", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "schema_id": self.schema_id}


def registered_primitive_schemas_v1() -> tuple[PrimitiveSchemaBindingV1, ...]:
    """Return both frozen human schema registrations, in domain order."""

    lmb = PrimitiveSchemaBindingV1(
        CampaignDomain.LMB,
        "lmb_generated_n6_t2_k3_d2_seed0_v0",
        tuple(
            sorted(
                (
                    "buffer_capacity",
                    "buffer_counts",
                    "integer_literal",
                    "legal_actions",
                    "remaining_tiles",
                    "selected_tile_type",
                )
            )
        ),
        tuple(
            sorted(
                (
                    "buffer_at_type",
                    "cardinality",
                    "cardinality_tiles",
                    "count_equal",
                    "equals",
                    "max_vector",
                    "subtract",
                    "sum_vector",
                )
            )
        ),
        "observation_driven_complete_depth2_program_closure",
        True,
    )
    g2048 = PrimitiveSchemaBindingV1(
        CampaignDomain.G2048,
        "g2048_select_safe_chain_2x2_v0",
        tuple(
            sorted(
                (
                    "absorbing_failure_status",
                    "d4_state_orbit",
                    "remaining_horizon",
                    "relative_survivor_geometry",
                )
            )
        ),
        tuple(
            sorted(
                (
                    "binary_successor_projection",
                    "d4_canonicalization",
                    "stabilizer_action_orbit",
                )
            )
        ),
        "known_exact_d4_automorphism_not_automatically_discovered",
        False,
    )
    return (lmb, g2048)


@dataclass(frozen=True, slots=True)
class StatisticalCellV1:
    key: str
    remaining_horizon: int
    kind: StatisticalCellKind
    representative_board: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.key) is not str
            or not self.key
            or type(self.remaining_horizon) is not int
            or not 0 <= self.remaining_horizon <= 2
            or type(self.kind) is not StatisticalCellKind
            or type(self.representative_board) is not tuple
            or any(type(item) is not int for item in self.representative_board)
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical cell is noncanonical"
            )
        if (
            self.kind is StatisticalCellKind.ACTIVE
            and (not self.representative_board or self.remaining_horizon == 0)
        ) or (
            self.kind is StatisticalCellKind.FAILURE
            and self.representative_board
        ) or (
            self.kind is StatisticalCellKind.TERMINAL
            and (not self.representative_board or self.remaining_horizon != 0)
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical cell kind/horizon semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_cell.v1",
            "schema_version": SCHEMA_VERSION,
            "key": self.key,
            "remaining_horizon": self.remaining_horizon,
            "kind": self.kind.value,
            "representative_board": list(self.representative_board),
        }

    @property
    def cell_id(self) -> str:
        return _content_id("statistical_cell", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cell_id": self.cell_id}


@dataclass(frozen=True, slots=True)
class StatisticalRowCatalogueV1:
    key: str
    source_cell_id: str
    action_label: str
    normalized_reward: Fraction
    destination_cell_ids: tuple[str, str]

    def __post_init__(self) -> None:
        _cid(self.source_cell_id, "statistical row source")
        for item in self.destination_cell_ids:
            _cid(item, "statistical row destination")
        if (
            type(self.key) is not str
            or not self.key
            or self.action_label
            not in (
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.TOWARD.value,
            )
            or type(self.normalized_reward) is not Fraction
            or self.normalized_reward not in (Fraction(1, 64), Fraction(1, 32))
            or type(self.destination_cell_ids) is not tuple
            or len(self.destination_cell_ids) != 2
            or self.destination_cell_ids[0] == self.destination_cell_ids[1]
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical row catalogue entry changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_row_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "key": self.key,
            "source_cell_id": self.source_cell_id,
            "action_label": self.action_label,
            "normalized_reward": _fraction_document(self.normalized_reward),
            "destination_cell_ids": list(self.destination_cell_ids),
        }

    @property
    def row_id(self) -> str:
        return _content_id("statistical_row_catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class G2048StatisticalCatalogueV1:
    primitive_schema: PrimitiveSchemaBindingV1
    cells: tuple[StatisticalCellV1, ...]
    rows: tuple[StatisticalRowCatalogueV1, ...]
    horizon: int = 2
    support_complete_by_registered_spawn_and_d4_schema: bool = True
    probabilities_absent: bool = True
    query_inputs_absent: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.primitive_schema) is not PrimitiveSchemaBindingV1
            or self.primitive_schema.domain is not CampaignDomain.G2048
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "G2048 catalogue requires its exact primitive schema"
            )
        _exact_tuple(self.cells, StatisticalCellV1, "statistical catalogue cells")
        _exact_tuple(self.rows, StatisticalRowCatalogueV1, "statistical catalogue rows")
        cell_ids = tuple(item.cell_id for item in self.cells)
        row_keys = tuple(item.key for item in self.rows)
        row_ids = tuple(item.row_id for item in self.rows)
        if (
            len(self.cells) != 7
            or len(set(cell_ids)) != 7
            or len(self.rows) != G2048_STATISTICAL_ROW_COUNT
            or len(set(row_keys)) != G2048_STATISTICAL_ROW_COUNT
            or len(set(row_ids)) != G2048_STATISTICAL_ROW_COUNT
            or any(
                row.source_cell_id not in cell_ids
                or any(dest not in cell_ids for dest in row.destination_cell_ids)
                for row in self.rows
            )
            or self.horizon != 2
            or self.support_complete_by_registered_spawn_and_d4_schema is not True
            or self.probabilities_absent is not True
            or self.query_inputs_absent is not True
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "G2048 structural catalogue shape or claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": G2048_PROFILE_KEY,
            "primitive_schema": self.primitive_schema.to_document(),
            "cells": [item.to_document() for item in self.cells],
            "rows": [item.to_document() for item in self.rows],
            "horizon": self.horizon,
            "support_complete_by_registered_spawn_and_d4_schema": (
                self.support_complete_by_registered_spawn_and_d4_schema
            ),
            "probabilities_absent": self.probabilities_absent,
            "query_inputs_absent": self.query_inputs_absent,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("statistical_catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


def registered_g2048_d4_statistical_catalogue_v1() -> G2048StatisticalCatalogueV1:
    """Return the probability-free H2 D4 structural support catalogue."""

    schema = registered_primitive_schemas_v1()[1]
    cells_by_key = {
        "ROOT_H2": StatisticalCellV1(
            "ROOT_H2", 2, StatisticalCellKind.ACTIVE, (0, 1, 2, 1)
        ),
        "FAILURE_H1": StatisticalCellV1(
            "FAILURE_H1", 1, StatisticalCellKind.FAILURE, ()
        ),
        "CHAIN_A_H1": StatisticalCellV1(
            "CHAIN_A_H1", 1, StatisticalCellKind.ACTIVE, (0, 1, 2, 2)
        ),
        "CHAIN_B_H1": StatisticalCellV1(
            "CHAIN_B_H1", 1, StatisticalCellKind.ACTIVE, (0, 2, 2, 2)
        ),
        "FAILURE_H0": StatisticalCellV1(
            "FAILURE_H0", 0, StatisticalCellKind.FAILURE, ()
        ),
        "TERMINAL_A_H0": StatisticalCellV1(
            "TERMINAL_A_H0", 0, StatisticalCellKind.TERMINAL, (0, 1, 3, 1)
        ),
        "TERMINAL_B_H0": StatisticalCellV1(
            "TERMINAL_B_H0", 0, StatisticalCellKind.TERMINAL, (0, 2, 3, 2)
        ),
    }
    away = G2048RelativeSurvivorLabel.AWAY.value
    toward = G2048RelativeSurvivorLabel.TOWARD.value

    def row(
        key: str,
        source: str,
        label: str,
        reward: Fraction,
        first: str,
        second: str,
    ) -> StatisticalRowCatalogueV1:
        return StatisticalRowCatalogueV1(
            key,
            cells_by_key[source].cell_id,
            label,
            reward,
            (cells_by_key[first].cell_id, cells_by_key[second].cell_id),
        )

    rows = (
        row(
            "ROOT_AWAY",
            "ROOT_H2",
            away,
            Fraction(1, 64),
            "FAILURE_H1",
            "CHAIN_B_H1",
        ),
        row(
            "ROOT_TOWARD",
            "ROOT_H2",
            toward,
            Fraction(1, 64),
            "CHAIN_A_H1",
            "CHAIN_B_H1",
        ),
        row(
            "CHAIN_A_AWAY",
            "CHAIN_A_H1",
            away,
            Fraction(1, 32),
            "FAILURE_H0",
            "TERMINAL_A_H0",
        ),
        row(
            "CHAIN_A_TOWARD",
            "CHAIN_A_H1",
            toward,
            Fraction(1, 32),
            "FAILURE_H0",
            "TERMINAL_A_H0",
        ),
        row(
            "CHAIN_B_AWAY",
            "CHAIN_B_H1",
            away,
            Fraction(1, 32),
            "FAILURE_H0",
            "TERMINAL_B_H0",
        ),
        row(
            "CHAIN_B_TOWARD",
            "CHAIN_B_H1",
            toward,
            Fraction(1, 32),
            "FAILURE_H0",
            "TERMINAL_B_H0",
        ),
    )
    return G2048StatisticalCatalogueV1(
        schema,
        tuple(cells_by_key.values()),
        rows,
    )


@dataclass(frozen=True, slots=True)
class AggregatedSampleCountRowV1:
    catalogue_row_id: str
    destination_counts: tuple[int, int]
    sample_count: int = G2048_SAMPLE_COUNT_PER_ROW

    def __post_init__(self) -> None:
        _cid(self.catalogue_row_id, "sample count catalogue row")
        if (
            type(self.destination_counts) is not tuple
            or len(self.destination_counts) != 2
            or any(type(item) is not int or item <= 0 for item in self.destination_counts)
            or type(self.sample_count) is not int
            or self.sample_count != G2048_SAMPLE_COUNT_PER_ROW
            or sum(self.destination_counts) != self.sample_count
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "aggregated sample-count row is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_aggregated_sample_count_row.v1",
            "schema_version": SCHEMA_VERSION,
            "catalogue_row_id": self.catalogue_row_id,
            "destination_counts": list(self.destination_counts),
            "sample_count": self.sample_count,
        }

    @property
    def count_row_id(self) -> str:
        return _content_id("sample_count_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "count_row_id": self.count_row_id}


@dataclass(frozen=True, slots=True)
class AggregatedSampleLedgerV1:
    catalogue_id: str
    count_rows: tuple[AggregatedSampleCountRowV1, ...]
    evidence_class: str = "OFFLINE_LOGGED_OBSERVATION"
    evidence_lane: str = "offline_source"
    source_frozen_before_query_release: bool = True
    trusted_sufficient_statistic_authority: bool = True
    individual_sample_trace_embedded: bool = False

    def __post_init__(self) -> None:
        _cid(self.catalogue_id, "sample ledger catalogue")
        _exact_tuple(self.count_rows, AggregatedSampleCountRowV1, "sample count rows")
        row_ids = tuple(item.catalogue_row_id for item in self.count_rows)
        if (
            len(self.count_rows) != G2048_STATISTICAL_ROW_COUNT
            or row_ids != tuple(sorted(set(row_ids)))
            or sum(item.sample_count for item in self.count_rows)
            != G2048_TOTAL_OFFLINE_SAMPLES
            or self.evidence_class != "OFFLINE_LOGGED_OBSERVATION"
            or self.evidence_lane != "offline_source"
            or self.source_frozen_before_query_release is not True
            or self.trusted_sufficient_statistic_authority is not True
            or self.individual_sample_trace_embedded is not False
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "aggregated sample ledger authority or count changed"
            )

    @property
    def total_sample_count(self) -> int:
        return sum(item.sample_count for item in self.count_rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_aggregated_sample_ledger.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": G2048_PROFILE_KEY,
            "catalogue_id": self.catalogue_id,
            "count_rows": [item.to_document() for item in self.count_rows],
            "total_sample_count": self.total_sample_count,
            "evidence_class": self.evidence_class,
            "evidence_lane": self.evidence_lane,
            "source_frozen_before_query_release": (
                self.source_frozen_before_query_release
            ),
            "trusted_sufficient_statistic_authority": (
                self.trusted_sufficient_statistic_authority
            ),
            "individual_sample_trace_embedded": (
                self.individual_sample_trace_embedded
            ),
        }

    @property
    def ledger_id(self) -> str:
        return _content_id("sample_ledger", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "ledger_id": self.ledger_id}


def registered_g2048_aggregated_sample_ledger_v1(
    catalogue: G2048StatisticalCatalogueV1,
) -> AggregatedSampleLedgerV1:
    """Return the frozen aggregate counts without consulting a query/kernel."""

    if type(catalogue) is not G2048StatisticalCatalogueV1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "sample-ledger constructor rejects substituted catalogues"
        )
    counts = {
        "ROOT_AWAY": (64881, 655),
        "ROOT_TOWARD": (64881, 655),
        "CHAIN_A_AWAY": (655, 64881),
        "CHAIN_A_TOWARD": (33096, 32440),
        "CHAIN_B_AWAY": (64881, 655),
        "CHAIN_B_TOWARD": (65208, 328),
    }
    rows = tuple(
        sorted(
            (
                AggregatedSampleCountRowV1(row.row_id, counts[row.key])
                for row in catalogue.rows
            ),
            key=lambda item: item.catalogue_row_id,
        )
    )
    return AggregatedSampleLedgerV1(catalogue.catalogue_id, rows)


@dataclass(frozen=True, slots=True)
class HoeffdingCalibrationCertificateV1:
    sample_count_per_row: int
    radius: Fraction
    coordinate_obligation_count: int
    alpha: Fraction
    exponent: Fraction
    taylor_degree: int
    taylor_lower: Fraction
    exponential_denominator_lower: int
    per_coordinate_tail_upper: Fraction
    family_tail_upper: Fraction
    confidence_lower: Fraction
    theorem_id: str = (
        "two_sided_hoeffding_plus_exact_taylor_lower_plus_finite_union_v1"
    )

    def __post_init__(self) -> None:
        expected_taylor = sum(
            (Fraction(8**index, math.factorial(index)) for index in range(14)),
            Fraction(0),
        )
        if (
            self.sample_count_per_row != G2048_SAMPLE_COUNT_PER_ROW
            or self.radius != HOEFFDING_RADIUS
            or self.coordinate_obligation_count
            != HOEFFDING_COORDINATE_OBLIGATIONS
            or self.alpha != HOEFFDING_ALPHA
            or self.exponent != 2 * self.sample_count_per_row * self.radius**2
            or self.exponent != 8
            or self.taylor_degree != 13
            or self.taylor_lower != expected_taylor
            or self.taylor_lower <= self.exponential_denominator_lower
            or self.exponential_denominator_lower != 2800
            or self.per_coordinate_tail_upper
            != HOEFFDING_PER_COORDINATE_TAIL_UPPER
            or self.per_coordinate_tail_upper != Fraction(2, 2800)
            or self.family_tail_upper
            != self.coordinate_obligation_count * self.per_coordinate_tail_upper
            or self.family_tail_upper != HOEFFDING_FAMILY_TAIL_UPPER
            or self.family_tail_upper >= self.alpha
            or self.confidence_lower != 1 - self.family_tail_upper
            or self.confidence_lower != HOEFFDING_CONFIDENCE_LOWER
            or self.theorem_id
            != "two_sided_hoeffding_plus_exact_taylor_lower_plus_finite_union_v1"
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "Hoeffding calibration proof changed or is not exact"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_hoeffding_calibration.v1",
            "schema_version": SCHEMA_VERSION,
            "sample_count_per_row": self.sample_count_per_row,
            "radius": _fraction_document(self.radius),
            "coordinate_obligation_count": self.coordinate_obligation_count,
            "alpha": _fraction_document(self.alpha),
            "exponent": _fraction_document(self.exponent),
            "taylor_degree": self.taylor_degree,
            "taylor_lower": _fraction_document(self.taylor_lower),
            "exponential_denominator_lower": self.exponential_denominator_lower,
            "per_coordinate_tail_upper": _fraction_document(
                self.per_coordinate_tail_upper
            ),
            "family_tail_upper": _fraction_document(self.family_tail_upper),
            "confidence_lower": _fraction_document(self.confidence_lower),
            "theorem_id": self.theorem_id,
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "calibration_id": self.calibration_id}


def _calibration_v1() -> HoeffdingCalibrationCertificateV1:
    taylor = sum(
        (Fraction(8**index, math.factorial(index)) for index in range(14)),
        Fraction(0),
    )
    return HoeffdingCalibrationCertificateV1(
        G2048_SAMPLE_COUNT_PER_ROW,
        HOEFFDING_RADIUS,
        HOEFFDING_COORDINATE_OBLIGATIONS,
        HOEFFDING_ALPHA,
        Fraction(8),
        13,
        taylor,
        2800,
        HOEFFDING_PER_COORDINATE_TAIL_UPPER,
        HOEFFDING_FAMILY_TAIL_UPPER,
        HOEFFDING_CONFIDENCE_LOWER,
    )


@dataclass(frozen=True, slots=True)
class StatisticalProbabilityIntervalV1:
    destination_cell_id: str
    empirical_probability: Fraction
    lower: Fraction
    upper: Fraction
    sample_count: int
    radius: Fraction

    def __post_init__(self) -> None:
        _cid(self.destination_cell_id, "statistical interval destination")
        if (
            type(self.empirical_probability) is not Fraction
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.empirical_probability <= self.upper <= 1
            or type(self.sample_count) is not int
            or self.sample_count != G2048_SAMPLE_COUNT_PER_ROW
            or self.radius != HOEFFDING_RADIUS
            or self.lower != max(Fraction(0), self.empirical_probability - self.radius)
            or self.upper != min(Fraction(1), self.empirical_probability + self.radius)
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical probability interval is not the registered bound"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_probability_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "destination_cell_id": self.destination_cell_id,
            "empirical_probability": _fraction_document(
                self.empirical_probability
            ),
            "lower": _fraction_document(self.lower),
            "upper": _fraction_document(self.upper),
            "sample_count": self.sample_count,
            "radius": _fraction_document(self.radius),
        }

    @property
    def interval_id(self) -> str:
        return _content_id("probability_interval", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


@dataclass(frozen=True, slots=True)
class StatisticalTransitionRowV1:
    catalogue_row: StatisticalRowCatalogueV1
    sample_count_row_id: str
    intervals: tuple[StatisticalProbabilityIntervalV1, ...]
    calibration_id: str
    evidence_level: EvidenceLevel = EvidenceLevel.STATISTICAL_HIGH_PROBABILITY

    def __post_init__(self) -> None:
        if type(self.catalogue_row) is not StatisticalRowCatalogueV1:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical transition rejects substituted catalogue rows"
            )
        _cid(self.sample_count_row_id, "statistical transition count row")
        _cid(self.calibration_id, "statistical transition calibration")
        _exact_tuple(
            self.intervals,
            StatisticalProbabilityIntervalV1,
            "statistical transition intervals",
        )
        if (
            len(self.intervals) != 2
            or tuple(item.destination_cell_id for item in self.intervals)
            != self.catalogue_row.destination_cell_ids
            or sum((item.lower for item in self.intervals), Fraction(0)) > 1
            or sum((item.upper for item in self.intervals), Fraction(0)) < 1
            or self.evidence_level is not EvidenceLevel.STATISTICAL_HIGH_PROBABILITY
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical transition simplex or evidence level changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_transition.v1",
            "schema_version": SCHEMA_VERSION,
            "catalogue_row": self.catalogue_row.to_document(),
            "sample_count_row_id": self.sample_count_row_id,
            "intervals": [item.to_document() for item in self.intervals],
            "calibration_id": self.calibration_id,
            "evidence_level": self.evidence_level.value,
            "joint_simplex_enforced": True,
        }

    @property
    def transition_id(self) -> str:
        return _content_id("statistical_transition", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "transition_id": self.transition_id}


@dataclass(frozen=True, slots=True)
class G2048StatisticalRAPMV1:
    catalogue: G2048StatisticalCatalogueV1
    sample_ledger_id: str
    calibration: HoeffdingCalibrationCertificateV1
    transitions: tuple[StatisticalTransitionRowV1, ...]
    query_neutral: bool = True
    exact_quotient_claimed: bool = False
    exact_sound_claimed: bool = False
    learned_probability_rows: int = G2048_STATISTICAL_ROW_COUNT

    def __post_init__(self) -> None:
        if (
            type(self.catalogue) is not G2048StatisticalCatalogueV1
            or type(self.calibration) is not HoeffdingCalibrationCertificateV1
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical RAPM rejects substituted authorities"
            )
        _cid(self.sample_ledger_id, "statistical RAPM sample ledger")
        _exact_tuple(
            self.transitions,
            StatisticalTransitionRowV1,
            "statistical RAPM transitions",
        )
        if (
            len(self.transitions) != G2048_STATISTICAL_ROW_COUNT
            or tuple(item.catalogue_row.row_id for item in self.transitions)
            != tuple(sorted(row.row_id for row in self.catalogue.rows))
            or any(
                item.calibration_id != self.calibration.calibration_id
                for item in self.transitions
            )
            or self.query_neutral is not True
            or self.exact_quotient_claimed is not False
            or self.exact_sound_claimed is not False
            or self.learned_probability_rows != G2048_STATISTICAL_ROW_COUNT
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical RAPM authority or overclaim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_rapm.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": G2048_PROFILE_KEY,
            "catalogue": self.catalogue.to_document(),
            "sample_ledger_id": self.sample_ledger_id,
            "calibration": self.calibration.to_document(),
            "transitions": [item.to_document() for item in self.transitions],
            "query_neutral": self.query_neutral,
            "exact_quotient_claimed": self.exact_quotient_claimed,
            "exact_sound_claimed": self.exact_sound_claimed,
            "learned_probability_rows": self.learned_probability_rows,
        }

    @property
    def model_id(self) -> str:
        return _content_id("statistical_model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def build_g2048_statistical_rapm_v1(
    catalogue: G2048StatisticalCatalogueV1,
    sample_ledger: AggregatedSampleLedgerV1,
) -> G2048StatisticalRAPMV1:
    """Build the probability envelope from two source artifacts only."""

    if type(catalogue) is not G2048StatisticalCatalogueV1 or type(
        sample_ledger
    ) is not AggregatedSampleLedgerV1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "statistical builder rejects substituted source artifacts"
        )
    if sample_ledger.catalogue_id != catalogue.catalogue_id:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "sample ledger is stale for this catalogue"
        )
    count_by_row = {
        item.catalogue_row_id: item for item in sample_ledger.count_rows
    }
    if set(count_by_row) != {item.row_id for item in catalogue.rows}:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "sample ledger does not cover every structural row exactly once"
        )
    calibration = _calibration_v1()
    transitions = []
    for row in sorted(catalogue.rows, key=lambda item: item.row_id):
        counts = count_by_row[row.row_id]
        intervals = tuple(
            StatisticalProbabilityIntervalV1(
                destination,
                Fraction(count, counts.sample_count),
                max(
                    Fraction(0),
                    Fraction(count, counts.sample_count) - calibration.radius,
                ),
                min(
                    Fraction(1),
                    Fraction(count, counts.sample_count) + calibration.radius,
                ),
                counts.sample_count,
                calibration.radius,
            )
            for destination, count in zip(
                row.destination_cell_ids, counts.destination_counts
            )
        )
        transitions.append(
            StatisticalTransitionRowV1(
                row,
                counts.count_row_id,
                intervals,
                calibration.calibration_id,
            )
        )
    return G2048StatisticalRAPMV1(
        catalogue,
        sample_ledger.ledger_id,
        calibration,
        tuple(transitions),
    )


def verify_g2048_statistical_rapm_v1(
    catalogue: G2048StatisticalCatalogueV1,
    sample_ledger: AggregatedSampleLedgerV1,
    claimed_model: G2048StatisticalRAPMV1,
) -> tuple[str, ...]:
    if type(claimed_model) is not G2048StatisticalRAPMV1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "statistical model verifier rejects substituted results"
        )
    expected = build_g2048_statistical_rapm_v1(catalogue, sample_ledger)
    _runtime_shape(claimed_model, expected, "claimed statistical RAPM")
    return (
        ()
        if claimed_model.to_document() == expected.to_document()
        else ("STATISTICAL_MODEL_RECONSTRUCTION_MISMATCH",)
    )


def _binary_probability_bounds(
    row: StatisticalTransitionRowV1,
) -> tuple[Fraction, Fraction]:
    first, second = row.intervals
    lower = max(first.lower, 1 - second.upper)
    upper = min(first.upper, 1 - second.lower)
    if not 0 <= lower <= upper <= 1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "binary statistical row has an empty simplex intersection"
        )
    return lower, upper


def _expectation_extreme(
    probability_bounds: tuple[Fraction, Fraction],
    first_value: Fraction,
    second_value: Fraction,
    *,
    maximize: bool,
) -> Fraction:
    lower, upper = probability_bounds
    values = (
        lower * first_value + (1 - lower) * second_value,
        upper * first_value + (1 - upper) * second_value,
    )
    return max(values) if maximize else min(values)


@dataclass(frozen=True, slots=True)
class G2048StatisticalPolicyV1:
    model_id: str
    root_action: str
    chain_a_action: str
    chain_b_action: str
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.model_id, "statistical policy model")
        labels = (
            G2048RelativeSurvivorLabel.AWAY.value,
            G2048RelativeSurvivorLabel.TOWARD.value,
        )
        if (
            any(
                item not in labels
                for item in (
                    self.root_action,
                    self.chain_a_action,
                    self.chain_b_action,
                )
            )
            or any(
                type(item) is not Fraction
                for item in (
                    self.reward_lower,
                    self.reward_upper,
                    self.failure_lower,
                    self.failure_upper,
                )
            )
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical policy bounds or schedule are invalid"
            )

    @property
    def schedule(self) -> tuple[str, str, str]:
        return (self.root_action, self.chain_a_action, self.chain_b_action)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "schedule": list(self.schedule),
            "reward_lower": _fraction_document(self.reward_lower),
            "reward_upper": _fraction_document(self.reward_upper),
            "failure_lower": _fraction_document(self.failure_lower),
            "failure_upper": _fraction_document(self.failure_upper),
        }

    @property
    def policy_id(self) -> str:
        return _content_id("g2048_policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_id": self.policy_id}


def _policy_bounds_v1(
    model: G2048StatisticalRAPMV1,
    schedule: tuple[str, str, str],
) -> G2048StatisticalPolicyV1:
    row_by_key = {item.catalogue_row.key: item for item in model.transitions}
    cell_by_id = {item.cell_id: item for item in model.catalogue.cells}
    root_action, chain_a_action, chain_b_action = schedule
    a_row = row_by_key[
        "CHAIN_A_AWAY"
        if chain_a_action == G2048RelativeSurvivorLabel.AWAY.value
        else "CHAIN_A_TOWARD"
    ]
    b_row = row_by_key[
        "CHAIN_B_AWAY"
        if chain_b_action == G2048RelativeSurvivorLabel.AWAY.value
        else "CHAIN_B_TOWARD"
    ]

    def terminal_risk(cell_id: str) -> Fraction:
        return Fraction(
            cell_by_id[cell_id].kind is StatisticalCellKind.FAILURE
        )

    def last_stage(
        row: StatisticalTransitionRowV1,
    ) -> tuple[Fraction, Fraction, Fraction, Fraction]:
        probability = _binary_probability_bounds(row)
        first, second = row.catalogue_row.destination_cell_ids
        risk_first = terminal_risk(first)
        risk_second = terminal_risk(second)
        return (
            row.catalogue_row.normalized_reward,
            row.catalogue_row.normalized_reward,
            _expectation_extreme(
                probability, risk_first, risk_second, maximize=False
            ),
            _expectation_extreme(
                probability, risk_first, risk_second, maximize=True
            ),
        )

    a_reward_lower, a_reward_upper, a_risk_lower, a_risk_upper = last_stage(a_row)
    b_reward_lower, b_reward_upper, b_risk_lower, b_risk_upper = last_stage(b_row)
    root_row = row_by_key[
        "ROOT_AWAY"
        if root_action == G2048RelativeSurvivorLabel.AWAY.value
        else "ROOT_TOWARD"
    ]
    probability = _binary_probability_bounds(root_row)
    root_destinations = root_row.catalogue_row.destination_cell_ids

    if root_action == G2048RelativeSurvivorLabel.AWAY.value:
        first_reward_lower = first_reward_upper = Fraction(0)
        first_risk_lower = first_risk_upper = Fraction(1)
        second_reward_lower, second_reward_upper = (
            b_reward_lower,
            b_reward_upper,
        )
        second_risk_lower, second_risk_upper = b_risk_lower, b_risk_upper
    else:
        first_reward_lower, first_reward_upper = (
            a_reward_lower,
            a_reward_upper,
        )
        first_risk_lower, first_risk_upper = a_risk_lower, a_risk_upper
        second_reward_lower, second_reward_upper = (
            b_reward_lower,
            b_reward_upper,
        )
        second_risk_lower, second_risk_upper = b_risk_lower, b_risk_upper
    if len(root_destinations) != 2:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "root row is not binary"
        )
    immediate = root_row.catalogue_row.normalized_reward
    return G2048StatisticalPolicyV1(
        model.model_id,
        root_action,
        chain_a_action,
        chain_b_action,
        immediate
        + _expectation_extreme(
            probability,
            first_reward_lower,
            second_reward_lower,
            maximize=False,
        ),
        immediate
        + _expectation_extreme(
            probability,
            first_reward_upper,
            second_reward_upper,
            maximize=True,
        ),
        _expectation_extreme(
            probability,
            first_risk_lower,
            second_risk_lower,
            maximize=False,
        ),
        _expectation_extreme(
            probability,
            first_risk_upper,
            second_risk_upper,
            maximize=True,
        ),
    )


@dataclass(frozen=True, slots=True)
class G2048StatisticalCertificateV1:
    model_id: str
    occurrence_id: str
    candidate_policies: tuple[G2048StatisticalPolicyV1, ...]
    selected_policy: G2048StatisticalPolicyV1
    delta: Fraction
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    calibration_id: str
    confidence_lower: Fraction
    evidence_level: EvidenceLevel = EvidenceLevel.STATISTICAL_HIGH_PROBABILITY
    status: str = STATISTICAL_CERTIFIED
    exact_sound_claimed: bool = False
    online_sample_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.model_id, "statistical certificate model"),
            (self.occurrence_id, "statistical certificate occurrence"),
            (self.calibration_id, "statistical certificate calibration"),
        ):
            _cid(value, field)
        _exact_tuple(
            self.candidate_policies,
            G2048StatisticalPolicyV1,
            "statistical candidate policies",
        )
        if type(self.selected_policy) is not G2048StatisticalPolicyV1:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical certificate rejects substituted policies"
            )
        ids = tuple(item.policy_id for item in self.candidate_policies)
        if (
            len(self.candidate_policies) != 8
            or ids != tuple(sorted(set(ids)))
            or self.selected_policy.policy_id not in ids
            or self.selected_policy.schedule
            != (
                G2048RelativeSurvivorLabel.TOWARD.value,
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.AWAY.value,
            )
            or self.delta != Fraction(1, 20)
            or self.selected_policy.failure_upper > self.delta
            or self.unrestricted_reward_upper != Fraction(3, 64)
            or self.normalized_regret_upper
            != self.unrestricted_reward_upper - self.selected_policy.reward_lower
            or self.normalized_regret_upper != 0
            or self.confidence_lower != HOEFFDING_CONFIDENCE_LOWER
            or self.evidence_level
            is not EvidenceLevel.STATISTICAL_HIGH_PROBABILITY
            or self.status != STATISTICAL_CERTIFIED
            or self.exact_sound_claimed is not False
            or self.online_sample_count != 0
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "statistical certificate selection, bounds, or claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.g2048_statistical_certificate.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": G2048_PROFILE_KEY,
            "model_id": self.model_id,
            "occurrence_id": self.occurrence_id,
            "candidate_policies": [
                item.to_document() for item in self.candidate_policies
            ],
            "selected_policy": self.selected_policy.to_document(),
            "delta": _fraction_document(self.delta),
            "unrestricted_reward_upper": _fraction_document(
                self.unrestricted_reward_upper
            ),
            "normalized_regret_upper": _fraction_document(
                self.normalized_regret_upper
            ),
            "calibration_id": self.calibration_id,
            "confidence_lower": _fraction_document(self.confidence_lower),
            "evidence_level": self.evidence_level.value,
            "status": self.status,
            "exact_sound_claimed": self.exact_sound_claimed,
            "online_sample_count": self.online_sample_count,
        }

    @property
    def certificate_id(self) -> str:
        return _content_id("g2048_certificate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


def solve_g2048_statistical_h2_v1(
    model: G2048StatisticalRAPMV1,
    occurrence_id: str,
) -> G2048StatisticalCertificateV1:
    """Enumerate all eight deterministic policies and certify one robustly."""

    if type(model) is not G2048StatisticalRAPMV1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "statistical solver rejects substituted models"
        )
    _cid(occurrence_id, "statistical solver occurrence")
    labels = (
        G2048RelativeSurvivorLabel.AWAY.value,
        G2048RelativeSurvivorLabel.TOWARD.value,
    )
    candidates = tuple(
        sorted(
            (
                _policy_bounds_v1(model, schedule)
                for schedule in product(labels, repeat=3)
            ),
            key=lambda item: item.policy_id,
        )
    )
    feasible = tuple(
        item for item in candidates if item.failure_upper <= Fraction(1, 20)
    )
    if not feasible:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "registered statistical query unexpectedly has no certified policy"
        )
    selected = min(
        feasible,
        key=lambda item: (
            -item.reward_lower,
            item.failure_upper,
            item.schedule,
            item.policy_id,
        ),
    )
    unrestricted = max(item.reward_upper for item in candidates)
    return G2048StatisticalCertificateV1(
        model.model_id,
        occurrence_id,
        candidates,
        selected,
        Fraction(1, 20),
        unrestricted,
        unrestricted - selected.reward_lower,
        model.calibration.calibration_id,
        model.calibration.confidence_lower,
    )


@dataclass(frozen=True, slots=True)
class CampaignOccurrenceSpecV1:
    ordinal: int
    domain: CampaignDomain
    query_key: str
    initial_mode: str
    initial_boards: tuple[tuple[int, ...], ...]
    horizon: int = 2
    delta: Fraction = Fraction(1, 20)
    reward_profile: str = "canonical_normalized_merge_or_match_plus_clear_v1"
    held_out_from_model_construction: bool = True

    def __post_init__(self) -> None:
        _integer(self.ordinal, "campaign occurrence ordinal")
        if (
            type(self.domain) is not CampaignDomain
            or type(self.query_key) is not str
            or not self.query_key
            or type(self.initial_mode) is not str
            or self.initial_mode
            not in (
                "LMB_TARGET_POINT",
                "G2048_D4_POINT",
                "G2048_D4_UNIFORM",
            )
            or type(self.initial_boards) is not tuple
            or any(
                type(board) is not tuple
                or len(board) != 4
                or any(type(rank) is not int for rank in board)
                for board in self.initial_boards
            )
            or self.horizon != 2
            or self.reward_profile
            != "canonical_normalized_merge_or_match_plus_clear_v1"
            or self.held_out_from_model_construction is not True
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign occurrence specification changed"
            )
        if self.domain is CampaignDomain.LMB:
            if (
                self.initial_mode != "LMB_TARGET_POINT"
                or self.initial_boards
                or self.delta != 0
            ):
                raise MultiDomainStatisticalCampaignInvariantViolation(
                    "LMB occurrence initial support changed"
                )
        elif self.delta != Fraction(1, 20):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "G2048 occurrence risk threshold changed"
            )
        elif self.initial_mode == "G2048_D4_POINT":
            if len(self.initial_boards) != 1:
                raise MultiDomainStatisticalCampaignInvariantViolation(
                    "G2048 point occurrence must contain one board"
                )
        elif (
            self.initial_mode != "G2048_D4_UNIFORM"
            or len(self.initial_boards) != 8
            or self.initial_boards != tuple(sorted(set(self.initial_boards)))
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "G2048 uniform occurrence must contain the complete D4 orbit"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_occurrence_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "domain": self.domain.value,
            "query_key": self.query_key,
            "initial_mode": self.initial_mode,
            "initial_boards": [list(board) for board in self.initial_boards],
            "horizon": self.horizon,
            "delta": _fraction_document(self.delta),
            "reward_profile": self.reward_profile,
            "held_out_from_model_construction": (
                self.held_out_from_model_construction
            ),
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence_spec", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def _campaign_occurrences_v1() -> tuple[CampaignOccurrenceSpecV1, ...]:
    boards = tuple(state.board for state in orbit(SAFE_CHAIN_BASE_STATE))
    rows: list[CampaignOccurrenceSpecV1] = [
        CampaignOccurrenceSpecV1(
            0,
            CampaignDomain.LMB,
            "lmb.program_closure.target.strict_h2.acquire",
            "LMB_TARGET_POINT",
            (),
            delta=Fraction(0),
        )
    ]
    for index, board in enumerate(boards[:4]):
        rows.append(
            CampaignOccurrenceSpecV1(
                len(rows),
                CampaignDomain.G2048,
                f"g2048.safe_chain.d4_point_{index}.h2",
                "G2048_D4_POINT",
                (board,),
            )
        )
    rows.append(
        CampaignOccurrenceSpecV1(
            len(rows),
            CampaignDomain.LMB,
            "lmb.program_closure.target.strict_h2.reuse_1",
            "LMB_TARGET_POINT",
            (),
            delta=Fraction(0),
        )
    )
    for index, board in enumerate(boards[4:], start=4):
        rows.append(
            CampaignOccurrenceSpecV1(
                len(rows),
                CampaignDomain.G2048,
                f"g2048.safe_chain.d4_point_{index}.h2",
                "G2048_D4_POINT",
                (board,),
            )
        )
    rows.append(
        CampaignOccurrenceSpecV1(
            len(rows),
            CampaignDomain.G2048,
            "g2048.safe_chain.d4_uniform.h2",
            "G2048_D4_UNIFORM",
            boards,
        )
    )
    rows.append(
        CampaignOccurrenceSpecV1(
            len(rows),
            CampaignDomain.LMB,
            "lmb.program_closure.target.strict_h2.reuse_2",
            "LMB_TARGET_POINT",
            (),
            delta=Fraction(0),
        )
    )
    result = tuple(rows)
    if (
        len(result) != 12
        or sum(item.domain is CampaignDomain.LMB for item in result) != 3
        or sum(item.domain is CampaignDomain.G2048 for item in result) != 9
        or tuple(item.ordinal for item in result) != tuple(range(12))
    ):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "registered campaign occurrence family changed"
        )
    return result


@dataclass(frozen=True, slots=True)
class MultiDomainCampaignPreregistrationV1:
    observation_log_id: str
    observation_semantics_id: str
    observation_authority_id: str
    g2048_catalogue_id: str
    g2048_sample_ledger_id: str
    primitive_schemas: tuple[PrimitiveSchemaBindingV1, ...]
    lmb_preregistration: ProgramClosureHeldOutH2PreregistrationV1
    occurrences: tuple[CampaignOccurrenceSpecV1, ...]
    prospective_model_ids_absent: bool = True
    prospective_plan_ids_absent: bool = True
    query_family_not_passed_to_model_builders: bool = True
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.observation_log_id, "campaign observation log"),
            (self.observation_semantics_id, "campaign observation semantics"),
            (self.observation_authority_id, "campaign observation authority"),
            (self.g2048_catalogue_id, "campaign G2048 catalogue"),
            (self.g2048_sample_ledger_id, "campaign G2048 sample ledger"),
        ):
            _cid(value, field)
        _exact_tuple(
            self.primitive_schemas,
            PrimitiveSchemaBindingV1,
            "campaign primitive schemas",
        )
        if type(self.lmb_preregistration) is not ProgramClosureHeldOutH2PreregistrationV1:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign preregistration rejects substituted LMB preregistration"
            )
        _exact_tuple(
            self.occurrences,
            CampaignOccurrenceSpecV1,
            "campaign occurrences",
        )
        if (
            self.primitive_schemas != registered_primitive_schemas_v1()
            or len(self.occurrences) != 12
            or tuple(item.ordinal for item in self.occurrences) != tuple(range(12))
            or tuple(item.occurrence_id for item in self.occurrences)
            != tuple(item.occurrence_id for item in _campaign_occurrences_v1())
            or self.lmb_preregistration.query.observation_log_id
            != self.observation_log_id
            or self.lmb_preregistration.query.semantics_profile_id
            != self.observation_semantics_id
            or self.lmb_preregistration.query.observation_authority_id
            != self.observation_authority_id
            or self.prospective_model_ids_absent is not True
            or self.prospective_plan_ids_absent is not True
            or self.query_family_not_passed_to_model_builders is not True
            or self.official_execution_allowed is not False
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign preregistration chronology or source binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observation_log_id": self.observation_log_id,
            "observation_semantics_id": self.observation_semantics_id,
            "observation_authority_id": self.observation_authority_id,
            "g2048_catalogue_id": self.g2048_catalogue_id,
            "g2048_sample_ledger_id": self.g2048_sample_ledger_id,
            "primitive_schemas": [
                item.to_document() for item in self.primitive_schemas
            ],
            "lmb_preregistration": self.lmb_preregistration.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "prospective_model_ids_absent": self.prospective_model_ids_absent,
            "prospective_plan_ids_absent": self.prospective_plan_ids_absent,
            "query_family_not_passed_to_model_builders": (
                self.query_family_not_passed_to_model_builders
            ),
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


def preregister_multidomain_statistical_campaign_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    g2048_catalogue: G2048StatisticalCatalogueV1,
    g2048_sample_ledger: AggregatedSampleLedgerV1,
) -> MultiDomainCampaignPreregistrationV1:
    """Freeze both sources and the held-out family before model construction."""

    if (
        type(observation_log) is not ObservationLogManifestV1
        or type(semantics_profile) is not DeterministicObservationProfileV1
        or type(observation_authority) is not PreregisteredObservationAuthorityV1
        or type(g2048_catalogue) is not G2048StatisticalCatalogueV1
        or type(g2048_sample_ledger) is not AggregatedSampleLedgerV1
    ):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "campaign preregistration rejects substituted source artifacts"
        )
    if g2048_sample_ledger.catalogue_id != g2048_catalogue.catalogue_id:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "campaign sample ledger is stale"
        )
    lmb_preregistration = preregister_lmb_program_closure_heldout_h2_v1(
        observation_log, semantics_profile, observation_authority
    )
    return MultiDomainCampaignPreregistrationV1(
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_authority.authority_id,
        g2048_catalogue.catalogue_id,
        g2048_sample_ledger.ledger_id,
        registered_primitive_schemas_v1(),
        lmb_preregistration,
        _campaign_occurrences_v1(),
    )


@dataclass(frozen=True, slots=True)
class MultiDomainOccurrenceResultV1:
    preregistration_id: str
    occurrence: CampaignOccurrenceSpecV1
    model_authority_id: str
    plan_id: str
    certificate_id: str
    evidence_level: EvidenceLevel
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    normalized_regret_upper: Fraction
    candidate_plan_count: int
    independent_audit_count: int
    exact_target_transition_calls: int
    online_statistical_samples: int
    reused_frozen_model: bool
    status: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.preregistration_id, "occurrence result preregistration"),
            (self.model_authority_id, "occurrence result model"),
            (self.plan_id, "occurrence result plan"),
            (self.certificate_id, "occurrence result certificate"),
        ):
            _cid(value, field)
        if type(self.occurrence) is not CampaignOccurrenceSpecV1:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "occurrence result rejects substituted specifications"
            )
        if any(
            type(item) is not Fraction
            for item in (
                self.reward_lower,
                self.reward_upper,
                self.failure_lower,
                self.failure_upper,
                self.normalized_regret_upper,
            )
        ) or not (
            0 <= self.reward_lower <= self.reward_upper <= 1
            and 0 <= self.failure_lower <= self.failure_upper <= 1
            and self.normalized_regret_upper == 0
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "occurrence result bounds changed"
            )
        if self.occurrence.domain is CampaignDomain.LMB:
            expected = (
                EvidenceLevel.EXACT_SOUND,
                4,
                1,
                3 if self.occurrence.ordinal == 0 else 0,
                0,
                self.occurrence.ordinal != 0,
                EXACT_CERTIFIED,
            )
        else:
            expected = (
                EvidenceLevel.STATISTICAL_HIGH_PROBABILITY,
                8,
                1,
                0,
                0,
                self.occurrence.ordinal != 1,
                STATISTICAL_CERTIFIED,
            )
        observed = (
            self.evidence_level,
            self.candidate_plan_count,
            self.independent_audit_count,
            self.exact_target_transition_calls,
            self.online_statistical_samples,
            self.reused_frozen_model,
            self.status,
        )
        if observed != expected:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "occurrence work, reuse, evidence, or status changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "occurrence": self.occurrence.to_document(),
            "model_authority_id": self.model_authority_id,
            "plan_id": self.plan_id,
            "certificate_id": self.certificate_id,
            "evidence_level": self.evidence_level.value,
            "reward_lower": _fraction_document(self.reward_lower),
            "reward_upper": _fraction_document(self.reward_upper),
            "failure_lower": _fraction_document(self.failure_lower),
            "failure_upper": _fraction_document(self.failure_upper),
            "normalized_regret_upper": _fraction_document(
                self.normalized_regret_upper
            ),
            "candidate_plan_count": self.candidate_plan_count,
            "independent_audit_count": self.independent_audit_count,
            "exact_target_transition_calls": self.exact_target_transition_calls,
            "online_statistical_samples": self.online_statistical_samples,
            "reused_frozen_model": self.reused_frozen_model,
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("occurrence_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MultiDomainCampaignWorkV1:
    logical_occurrences: int
    lmb_program_candidates: int
    lmb_plan_candidates: int
    lmb_exact_target_transition_calls: int
    g2048_offline_logged_samples: int
    g2048_statistical_policy_candidates: int
    g2048_online_samples: int
    exact_sound_certificates: int
    statistical_high_probability_certificates: int
    sample_efficiency_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        expected = (
            12,
            6650,
            16,
            3,
            G2048_TOTAL_OFFLINE_SAMPLES,
            72,
            0,
            3,
            9,
            False,
            None,
            None,
        )
        observed = (
            self.logical_occurrences,
            self.lmb_program_candidates,
            self.lmb_plan_candidates,
            self.lmb_exact_target_transition_calls,
            self.g2048_offline_logged_samples,
            self.g2048_statistical_policy_candidates,
            self.g2048_online_samples,
            self.exact_sound_certificates,
            self.statistical_high_probability_certificates,
            self.sample_efficiency_claimed,
            self.official_scalar_cost,
            self.official_n_break_even,
        )
        if observed != expected:
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign native work or locked economics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_campaign_work.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrences": self.logical_occurrences,
            "lmb_program_candidates": self.lmb_program_candidates,
            "lmb_plan_candidates": self.lmb_plan_candidates,
            "lmb_exact_target_transition_calls": (
                self.lmb_exact_target_transition_calls
            ),
            "g2048_offline_logged_samples": self.g2048_offline_logged_samples,
            "g2048_statistical_policy_candidates": (
                self.g2048_statistical_policy_candidates
            ),
            "g2048_online_samples": self.g2048_online_samples,
            "exact_sound_certificates": self.exact_sound_certificates,
            "statistical_high_probability_certificates": (
                self.statistical_high_probability_certificates
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_n_break_even": self.official_n_break_even,
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class MultiDomainStatisticalCampaignResultV1:
    preregistration: MultiDomainCampaignPreregistrationV1
    lmb_synthesis_result_id: str
    lmb_heldout_result: ProgramClosureHeldOutH2ResultV1
    g2048_model: G2048StatisticalRAPMV1
    occurrences: tuple[MultiDomainOccurrenceResultV1, ...]
    work: MultiDomainCampaignWorkV1
    status: str = SUCCESS_STATUS
    domain_count: int = 2
    cross_domain_shared_coordinate_claimed: bool = False
    automatic_g2048_symmetry_discovery_claimed: bool = False
    statistical_exact_sound_claimed: bool = False
    sample_efficiency_claimed: bool = False
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.preregistration) is not MultiDomainCampaignPreregistrationV1
            or type(self.lmb_heldout_result) is not ProgramClosureHeldOutH2ResultV1
            or type(self.g2048_model) is not G2048StatisticalRAPMV1
            or type(self.work) is not MultiDomainCampaignWorkV1
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign result rejects substituted nested authorities"
            )
        _cid(self.lmb_synthesis_result_id, "campaign LMB synthesis")
        _exact_tuple(
            self.occurrences,
            MultiDomainOccurrenceResultV1,
            "campaign occurrence results",
        )
        preregistration_id = self.preregistration.preregistration_id
        if (
            len(self.occurrences) != 12
            or tuple(item.occurrence.occurrence_id for item in self.occurrences)
            != tuple(
                item.occurrence_id for item in self.preregistration.occurrences
            )
            or any(
                item.preregistration_id != preregistration_id
                for item in self.occurrences
            )
            or self.lmb_heldout_result.preregistration.preregistration_id
            != self.preregistration.lmb_preregistration.preregistration_id
            or self.lmb_heldout_result.synthesis_result_id
            != self.lmb_synthesis_result_id
            or self.g2048_model.catalogue.catalogue_id
            != self.preregistration.g2048_catalogue_id
            or self.g2048_model.sample_ledger_id
            != self.preregistration.g2048_sample_ledger_id
            or self.status != SUCCESS_STATUS
            or self.domain_count != 2
            or self.cross_domain_shared_coordinate_claimed is not False
            or self.automatic_g2048_symmetry_discovery_claimed is not False
            or self.statistical_exact_sound_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.official_execution_allowed is not False
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign result identity chain or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_statistical_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "lmb_synthesis_result_id": self.lmb_synthesis_result_id,
            "lmb_heldout_result": self.lmb_heldout_result.to_document(),
            "g2048_model": self.g2048_model.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "work": self.work.to_document(),
            "status": self.status,
            "domain_count": self.domain_count,
            "cross_domain_shared_coordinate_claimed": (
                self.cross_domain_shared_coordinate_claimed
            ),
            "automatic_g2048_symmetry_discovery_claimed": (
                self.automatic_g2048_symmetry_discovery_claimed
            ),
            "statistical_exact_sound_claimed": (
                self.statistical_exact_sound_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _lmb_occurrence_result_v1(
    preregistration: MultiDomainCampaignPreregistrationV1,
    spec: CampaignOccurrenceSpecV1,
    heldout: ProgramClosureHeldOutH2ResultV1,
    proposal: ProgramClosureHeldOutPlanProposalV1,
    audit: ProgramClosureHeldOutSelectedAuditV1,
) -> MultiDomainOccurrenceResultV1:
    if audit.audit_result.outcome is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "LMB reuse occurrence did not independently certify"
        )
    bounds = audit.audit_result.robust_bounds
    return MultiDomainOccurrenceResultV1(
        preregistration.preregistration_id,
        spec,
        heldout.final_epoch.epoch_id,
        proposal.selected_plan.plan_id,
        audit.audit_id,
        EvidenceLevel.EXACT_SOUND,
        bounds.policy_reward_lower,
        bounds.policy_reward_upper,
        bounds.policy_failure_lower,
        bounds.policy_failure_upper,
        bounds.normalized_distribution_regret,
        4,
        1,
        3 if spec.ordinal == 0 else 0,
        0,
        spec.ordinal != 0,
        EXACT_CERTIFIED,
    )


def _g2048_occurrence_result_v1(
    preregistration: MultiDomainCampaignPreregistrationV1,
    spec: CampaignOccurrenceSpecV1,
    model: G2048StatisticalRAPMV1,
) -> MultiDomainOccurrenceResultV1:
    certificate = solve_g2048_statistical_h2_v1(model, spec.occurrence_id)
    selected = certificate.selected_policy
    return MultiDomainOccurrenceResultV1(
        preregistration.preregistration_id,
        spec,
        model.model_id,
        selected.policy_id,
        certificate.certificate_id,
        EvidenceLevel.STATISTICAL_HIGH_PROBABILITY,
        selected.reward_lower,
        selected.reward_upper,
        selected.failure_lower,
        selected.failure_upper,
        certificate.normalized_regret_upper,
        8,
        1,
        0,
        0,
        spec.ordinal != 1,
        STATISTICAL_CERTIFIED,
    )


def _implementation_functions() -> tuple[Any, ...]:
    return (
        registered_primitive_schemas_v1,
        registered_g2048_d4_statistical_catalogue_v1,
        registered_g2048_aggregated_sample_ledger_v1,
        build_g2048_statistical_rapm_v1,
        _binary_probability_bounds,
        _expectation_extreme,
        _policy_bounds_v1,
        solve_g2048_statistical_h2_v1,
        _campaign_occurrences_v1,
        preregister_multidomain_statistical_campaign_v1,
        _lmb_occurrence_result_v1,
        _g2048_occurrence_result_v1,
    )


def _observed_implementation_sha256() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _implementation_functions()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority() -> None:
    if _observed_implementation_sha256() != IMPLEMENTATION_SHA256:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "V0-059 implementation differs from its frozen authority"
        )


def run_multidomain_statistical_campaign_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    g2048_catalogue: G2048StatisticalCatalogueV1,
    g2048_sample_ledger: AggregatedSampleLedgerV1,
    preregistration: MultiDomainCampaignPreregistrationV1,
    lmb_kernel: LMBKernel,
) -> MultiDomainStatisticalCampaignResultV1:
    """Construct both models, then execute only the preregistered family."""

    if (
        type(observation_log) is not ObservationLogManifestV1
        or type(semantics_profile) is not DeterministicObservationProfileV1
        or type(observation_authority) is not PreregisteredObservationAuthorityV1
        or type(g2048_catalogue) is not G2048StatisticalCatalogueV1
        or type(g2048_sample_ledger) is not AggregatedSampleLedgerV1
        or type(preregistration) is not MultiDomainCampaignPreregistrationV1
        or type(lmb_kernel) is not LMBKernel
    ):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "campaign runner rejects substituted inputs"
        )
    _validate_implementation_authority()
    expected_preregistration = preregister_multidomain_statistical_campaign_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        g2048_catalogue,
        g2048_sample_ledger,
    )
    _runtime_shape(
        preregistration,
        expected_preregistration,
        "campaign preregistration",
    )
    if preregistration.to_document() != expected_preregistration.to_document():
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "campaign preregistration reconstruction mismatch"
        )

    synthesis = synthesize_observed_lmb_program_closure_partial_rapm_v1(
        observation_log, semantics_profile, observation_authority
    )
    if verify_observed_lmb_program_closure_partial_rapm_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        synthesis,
    ):
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "LMB program closure failed retained replay"
        )
    lmb_result = run_lmb_program_closure_heldout_h2_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration.lmb_preregistration,
        synthesis,
        lmb_kernel,
    )
    g2048_model = build_g2048_statistical_rapm_v1(
        g2048_catalogue, g2048_sample_ledger
    )

    lmb_replay_count = 0
    occurrence_results: list[MultiDomainOccurrenceResultV1] = []
    for spec in preregistration.occurrences:
        if spec.domain is CampaignDomain.G2048:
            occurrence_results.append(
                _g2048_occurrence_result_v1(
                    preregistration, spec, g2048_model
                )
            )
            continue
        if lmb_replay_count == 0:
            proposal = lmb_result.final_proposal
            audit = lmb_result.final_selected_audit
        else:
            proposal = lmb_heldout._propose(
                observation_log,
                semantics_profile,
                observation_authority,
                preregistration.lmb_preregistration,
                lmb_result.final_epoch,
            )
            audit = lmb_heldout._independent_selected_audit(
                observation_log,
                semantics_profile,
                observation_authority,
                lmb_result.final_epoch,
                proposal,
            )
        occurrence_results.append(
            _lmb_occurrence_result_v1(
                preregistration, spec, lmb_result, proposal, audit
            )
        )
        lmb_replay_count += 1

    work = MultiDomainCampaignWorkV1(
        12,
        6650,
        16,
        3,
        G2048_TOTAL_OFFLINE_SAMPLES,
        72,
        0,
        3,
        9,
    )
    return MultiDomainStatisticalCampaignResultV1(
        preregistration,
        synthesis.result_id,
        lmb_result,
        g2048_model,
        tuple(occurrence_results),
        work,
    )


def _simple_cell_key_from_exact_v1(cell_id: Any) -> str:
    if cell_id.kind is OrbitCellKind.FAILURE:
        return f"FAILURE_H{cell_id.remaining}"
    if cell_id.remaining == 2:
        return "ROOT_H2"
    if cell_id.remaining == 1:
        if "(0, 1, 2, 2)" in cell_id.representative_key:
            return "CHAIN_A_H1"
        if "(0, 2, 2, 2)" in cell_id.representative_key:
            return "CHAIN_B_H1"
    if cell_id.remaining == 0:
        if "(0, 1, 3, 1)" in cell_id.representative_key:
            return "TERMINAL_A_H0"
        if "(0, 2, 3, 2)" in cell_id.representative_key:
            return "TERMINAL_B_H0"
    raise MultiDomainStatisticalCampaignInvariantViolation(
        "standalone exact quotient contains an unregistered cell"
    )


def _verify_g2048_against_exact_kernel_v1(
    model: G2048StatisticalRAPMV1,
    kernel: G2048SafeChainKernel,
) -> tuple[tuple[str, ...], Fraction, Fraction]:
    if type(kernel) is not G2048SafeChainKernel:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "standalone G2048 verification requires the exact safe-chain kernel"
        )
    query = safe_chain_query(kernel)
    group = FiniteGroupAction(
        elements=D4_ELEMENTS,
        transform_state=lambda element, state: transform_state(
            state, element, kernel.size
        ),
        transform_action=lambda element, action: transform_action(
            action, element, kernel.size
        ),
        inverse=inverse_d4,
        state_key=lambda state: repr((state.board, state.status.value)),
        action_key=repr,
    )
    exact = build_validate_solve_d4(
        kernel,
        query,
        group,
        is_failure=lambda state: state.status is G2048Status.FAILURE,
    )
    failures: list[str] = []
    if not exact.validation.exact or not exact.validation.automorphism_exact:
        failures.append("EXACT_D4_STRUCTURAL_VERIFICATION_FAILED")
    catalogue_cells = {
        item.key: item for item in model.catalogue.cells
    }
    if set(catalogue_cells) != {
        _simple_cell_key_from_exact_v1(item.cell_id)
        for item in exact.state_time_orbits
    }:
        failures.append("STATISTICAL_CELL_CATALOGUE_MISMATCH")
    action_orbits = {
        (item.cell_id, item.label): item for item in exact.action_orbits
    }
    adapter = G2048RelativeSurvivorAdapter()
    transition_by_key = {
        item.catalogue_row.key: item for item in model.transitions
    }
    for transition in exact.quotient.transitions:
        action_orbit = action_orbits[(transition.cell_id, transition.label)]
        action_label = adapter.label(
            kernel,
            action_orbit.representative_state,
            action_orbit.canonical_action,
        )
        source_key = _simple_cell_key_from_exact_v1(transition.cell_id)
        row_key = {
            ("ROOT_H2", G2048RelativeSurvivorLabel.AWAY): "ROOT_AWAY",
            ("ROOT_H2", G2048RelativeSurvivorLabel.TOWARD): "ROOT_TOWARD",
            ("CHAIN_A_H1", G2048RelativeSurvivorLabel.AWAY): "CHAIN_A_AWAY",
            ("CHAIN_A_H1", G2048RelativeSurvivorLabel.TOWARD): "CHAIN_A_TOWARD",
            ("CHAIN_B_H1", G2048RelativeSurvivorLabel.AWAY): "CHAIN_B_AWAY",
            ("CHAIN_B_H1", G2048RelativeSurvivorLabel.TOWARD): "CHAIN_B_TOWARD",
        }[(source_key, action_label)]
        statistical = transition_by_key[row_key]
        exact_probabilities = {
            catalogue_cells[
                _simple_cell_key_from_exact_v1(destination)
            ].cell_id: probability
            for destination, probability in transition.successor_probabilities
        }
        for interval in statistical.intervals:
            probability = exact_probabilities.get(interval.destination_cell_id)
            if probability is None or not interval.lower <= probability <= interval.upper:
                failures.append(
                    f"EXACT_PROBABILITY_OUTSIDE_INTERVAL:{row_key}"
                )
        exact_reward = dict(transition.reward_features)["merge"] / 2
        if exact_reward != statistical.catalogue_row.normalized_reward:
            failures.append(f"EXACT_REWARD_MISMATCH:{row_key}")
    if exact.ground_value != Fraction(3, 64):
        failures.append("EXACT_GROUND_VALUE_CHANGED")
    if exact.ground_risk != Fraction(99, 5000):
        failures.append("EXACT_GROUND_RISK_CHANGED")
    first_certificate = solve_g2048_statistical_h2_v1(
        model, _campaign_occurrences_v1()[1].occurrence_id
    )
    selected = first_certificate.selected_policy
    if not (
        selected.reward_lower
        <= exact.ground_value
        <= selected.reward_upper
        and selected.failure_lower
        <= exact.ground_risk
        <= selected.failure_upper
    ):
        failures.append("EXACT_OPTIMUM_OUTSIDE_STATISTICAL_CERTIFICATE")
    return tuple(sorted(set(failures))), exact.ground_value, exact.ground_risk


@dataclass(frozen=True, slots=True)
class MultiDomainCampaignVerificationV1:
    claimed_result_id: str
    replay_result_id: str
    failures: tuple[str, ...]
    exact_g2048_value: Fraction
    exact_g2048_failure: Fraction
    verification_lane: str = "standalone_evaluation"
    production_g2048_kernel_access: int = 0
    exact_sound_statistical_promotion_authorized: bool = False

    def __post_init__(self) -> None:
        _cid(self.claimed_result_id, "campaign verification claimed result")
        _cid(self.replay_result_id, "campaign verification replay result")
        if (
            type(self.failures) is not tuple
            or any(type(item) is not str for item in self.failures)
            or self.failures != tuple(sorted(set(self.failures)))
            or self.exact_g2048_value != Fraction(3, 64)
            or self.exact_g2048_failure != Fraction(99, 5000)
            or self.verification_lane != "standalone_evaluation"
            or self.production_g2048_kernel_access != 0
            or self.exact_sound_statistical_promotion_authorized is not False
        ):
            raise MultiDomainStatisticalCampaignInvariantViolation(
                "campaign verification result or lane changed"
            )

    @property
    def verified(self) -> bool:
        return not self.failures and self.claimed_result_id == self.replay_result_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multidomain_campaign_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "claimed_result_id": self.claimed_result_id,
            "replay_result_id": self.replay_result_id,
            "failures": list(self.failures),
            "verified": self.verified,
            "exact_g2048_value": _fraction_document(self.exact_g2048_value),
            "exact_g2048_failure": _fraction_document(
                self.exact_g2048_failure
            ),
            "verification_lane": self.verification_lane,
            "production_g2048_kernel_access": self.production_g2048_kernel_access,
            "exact_sound_statistical_promotion_authorized": (
                self.exact_sound_statistical_promotion_authorized
            ),
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_multidomain_statistical_campaign_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    g2048_catalogue: G2048StatisticalCatalogueV1,
    g2048_sample_ledger: AggregatedSampleLedgerV1,
    preregistration: MultiDomainCampaignPreregistrationV1,
    lmb_kernel: LMBKernel,
    g2048_kernel: G2048SafeChainKernel,
    claimed_result: MultiDomainStatisticalCampaignResultV1,
) -> MultiDomainCampaignVerificationV1:
    """Replay both production paths, then evaluate G2048 with the exact kernel."""

    if type(claimed_result) is not MultiDomainStatisticalCampaignResultV1:
        raise MultiDomainStatisticalCampaignInvariantViolation(
            "campaign verifier rejects substituted results"
        )
    expected = run_multidomain_statistical_campaign_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        g2048_catalogue,
        g2048_sample_ledger,
        preregistration,
        lmb_kernel,
    )
    _runtime_shape(claimed_result, expected, "claimed campaign result")
    failures: list[str] = []
    if verify_lmb_program_closure_heldout_h2_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration.lmb_preregistration,
        synthesize_observed_lmb_program_closure_partial_rapm_v1(
            observation_log, semantics_profile, observation_authority
        ),
        lmb_kernel,
        claimed_result.lmb_heldout_result,
    ):
        failures.append("LMB_HELDOUT_REPLAY_MISMATCH")
    g2048_failures, exact_value, exact_failure = (
        _verify_g2048_against_exact_kernel_v1(
            claimed_result.g2048_model, g2048_kernel
        )
    )
    failures.extend(g2048_failures)
    if claimed_result.to_document() != expected.to_document():
        failures.append("CAMPAIGN_RESULT_RECONSTRUCTION_MISMATCH")
    return MultiDomainCampaignVerificationV1(
        claimed_result.result_id,
        expected.result_id,
        tuple(sorted(set(failures))),
        exact_value,
        exact_failure,
    )


__all__ = [
    "AggregatedSampleCountRowV1",
    "AggregatedSampleLedgerV1",
    "CONTRACT_VERSION",
    "CampaignDomain",
    "CampaignOccurrenceSpecV1",
    "EvidenceLevel",
    "G2048StatisticalCatalogueV1",
    "G2048StatisticalCertificateV1",
    "G2048StatisticalPolicyV1",
    "G2048StatisticalRAPMV1",
    "HOEFFDING_CONFIDENCE_LOWER",
    "HOEFFDING_FAMILY_TAIL_UPPER",
    "HOEFFDING_RADIUS",
    "IMPLEMENTATION_SHA256",
    "MultiDomainCampaignPreregistrationV1",
    "MultiDomainCampaignVerificationV1",
    "MultiDomainCampaignWorkV1",
    "MultiDomainOccurrenceResultV1",
    "MultiDomainStatisticalCampaignInvariantViolation",
    "MultiDomainStatisticalCampaignResultV1",
    "PrimitiveSchemaBindingV1",
    "PROFILE_KEY",
    "STATISTICAL_CERTIFIED",
    "SUCCESS_STATUS",
    "StatisticalCellKind",
    "StatisticalCellV1",
    "StatisticalProbabilityIntervalV1",
    "StatisticalRowCatalogueV1",
    "StatisticalTransitionRowV1",
    "build_g2048_statistical_rapm_v1",
    "preregister_multidomain_statistical_campaign_v1",
    "registered_g2048_aggregated_sample_ledger_v1",
    "registered_g2048_d4_statistical_catalogue_v1",
    "registered_primitive_schemas_v1",
    "run_multidomain_statistical_campaign_v1",
    "solve_g2048_statistical_h2_v1",
    "verify_g2048_statistical_rapm_v1",
    "verify_multidomain_statistical_campaign_v1",
]
