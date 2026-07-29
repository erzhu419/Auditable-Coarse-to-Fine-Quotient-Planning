"""Construction fixture for the pre-anchor V0-075 authority design.

The exact laws in this module were exposed during construction.  Consequently
this module is permanently ineligible as production held-out evidence.  It is
retained only for deterministic regression, schema development, and negative
controls.  Production public code must instead depend on
``v075_public_campaign_authority_v1``, whose dependency graph contains no law.

The phase-one objects are:

* a typed disposition registry for historical target identities;
* one fresh family generation containing three structural replicates;
* fresh hidden-law and environment identities;
* a five-arm, fifteen-occurrence preregistration draft;
* a nonfinal execution-manifest draft; and
* an anchor-derived, but still nonauthorizing, target-tape namespace identity.

All objects remain nonexecuting.  No ID produced here may authorize a
production target observer or a confirmatory scientific claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import combinations
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_fresh_total_lift_parallel_confirmatory_campaign_v0"
TARGET_FAMILY_GENERATION_KEY = (
    "v075_fresh_confirmatory_family_generation_1"
)
AUTHORITY_ROLE = "CONSTRUCTION_FIXTURE_ONLY"
PRODUCTION_HELDOUT_EVIDENCE_ALLOWED = False

HORIZON = 2
RANK_CAP = 6
ROOT_RANKS = (1, 1, 2, 0, 0, 0, 0)
RISK_TOLERANCE = Fraction(1, 20)
REWARD_CEILING = Fraction(3, 64)
NORMALIZED_REGRET_TOLERANCE = Fraction(1, 20)

ARM_ORDER = (
    "SOURCE_CONSENSUS_PRIOR",
    "NO_PRIOR",
    "WRONG_CONSENSUS_PRIOR",
    "OOD_ABSTENTION",
    "MATCHED_DIRECT_GROUND",
)
DIRECT_VALIDATION_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
MAX_ROUNDS = 2
INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW = 64
INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW = 2_048
PROMOTION_VALIDATION_DRAWS_PER_ROUND = 2_048
NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW = 64
NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW = 8_192
MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS = 19
MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM = 160_960
ROW_EPOCH_BETA = Fraction(1, 300_000)
CAMPAIGN_JOINT_TAIL_UPPER = Fraction(1, 125)
CAMPAIGN_CONFIDENCE_LOWER = Fraction(124, 125)
EXPECTED_OCCURRENCE_COUNT = 15

TERMINAL_CODES = (
    "CONDITIONAL_PLAN_CERTIFICATE",
    "EXACT_FEASIBLE_FALLBACK",
    "EXACT_INFEASIBILITY_CERTIFICATE",
    "NO_POSITIVE_GAIN_NONCERTIFICATE",
    "INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE",
    "DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE",
    "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE",
    "TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE",
    "STATISTICAL_ENVELOPE_MISS_NONCERTIFICATE",
    "PROTOCOL_FAILURE",
    "INTEGRITY_FAILURE",
)

DOMAIN_TAGS = {
    "historical_disposition": (
        "acfqp:v075-historical-identity-disposition-registry:v1"
    ),
    "family_seed": "acfqp:v075-target-family-generation-seed:v1",
    "replicate_context": "acfqp:v075-heldout-replicate-context:v1",
    "family_generation": "acfqp:v075-target-family-generation:v1",
    "hidden_law": "acfqp:v075-hidden-spawn-law:v1",
    "environment": "acfqp:v075-heldout-environment-manifest:v1",
    "occurrence_template": (
        "acfqp:v075-registered-occurrence-template:v1"
    ),
    "tape_derivation_rule": (
        "acfqp:v075-target-tape-derivation-rule:v1"
    ),
    "preregistration_draft": (
        "acfqp:v075-fresh-campaign-preregistration-draft:v1"
    ),
    "manifest_draft": (
        "acfqp:v075-confirmatory-execution-manifest-draft:v1"
    ),
    "target_tape_namespace": (
        "acfqp:v075-target-tape-namespace:v1"
    ),
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 authority domains must be unique and v075-only")


class V075FreshCampaignAuthorityInvariantViolation(ValueError):
    """A V0-075 pre-anchor authority or identity invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075FreshCampaignAuthorityInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075FreshCampaignAuthorityInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V075FreshCampaignAuthorityInvariantViolation(
            f"{field} must be one nonempty canonical string"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V075FreshCampaignAuthorityInvariantViolation(
            "registered arithmetic must use exact Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


HISTORICAL_FAILURE_RECORD_IDS = (
    "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f",
    "cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e",
)

# These are historical target or execution-authority identities.  They are
# retained only to reject cross-family substitution.  Source-only evidence has
# a separate allowlist below.
FORBIDDEN_V072_TARGET_IDENTITY_IDS = tuple(
    sorted(
        {
            # Public target contexts, hidden laws, and environment.
            "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a",
            "48a6f36af9ef5ff1ba9920d783d2435cedd9458c8383f48ccf40412ff55f0dda",
            "52363b3d6e6508e6734418103be98da18cd7aafe6657d24de16c2547c630ba7a",
            "434f67074a8be498fd8cc532fe780f4227f6f8233bc90a62fab6e8cb595a5f71",
            "801683343ef1973337e534f2d36ac6c8493717d240ef05677abd3a2abb72559c",
            "b0803f306f3d5ac79abd6e87fc713caedcceae3411f3172f88d103cb7b540347",
            "f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da",
            # Draft and retired development preregistration identities.
            "7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2",
            "8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29",
            "e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4",
            "0f8061ac58630cced8f01bce01191ab0d02aff5cf64b4cc106f579ad53d02312",
            "1f240bb0305012a9144b4039d9f2f9b13a0be18b23c0cc7c70dc2909f09ccc29",
            "a5775190ea336702a7f4e1f06bdd93ec0bd0609f03f69ad7a72c2262e6645976",
            "ad7dca2b9db96d98d0c8bd6608315264995d3dcb0b6457a4b2b5d073db494ab0",
            "571d4cb2a7b2b55fc85012b2b417f397b57226df7ae4b00c47d0bb5f35639441",
            "e8cb7a070c7d6bbdb93683367a8026f422a8ef397877b87d07a3c6c549820cde",
            "f0d8db6165c3d0a125945b43b4b0d8e221b13ea7870021e96f18b91e218ed00e",
            "495927b2c72c847086008b2b2c6e8f65ea4a2b5a45ce409c8c7ec3d4be915500",
            # Attempt-1 authority chain.
            "acbec3e259e9df0e5b56c172ae2261f6d072f29b3a669b1eaafbcbdcae28b1c6",
            "b6a543a0e30214338214bf025bbf543994f6afc3251608f522d11f5c20e236f2",
            "41c9aa9509717915777ba91a7d6015071ddb1f55187505f8ab376be2fd122d4f",
            "4316c8a441db0eee80847c9060b25d9eae454d14895c4e137e1e9c092ff0fe6f",
            "157f6c512b912d4e100e76a30fdb4ae43c051cef6ac073778a303dd523e6d88e",
            "d836f0b0c7f3b302541ce81dc5372c077d336add5f28a973ebd6ae611ccbd8b9",
            # Attempt-2 authority chain, plan, occurrence, and journal.
            "2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865",
            "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26",
            "022ced158d19aea8293a8c8c75e70aa93f93e1913380a76ad11f729f54057076",
            "408e76d3350bc4fc7a6e2a625d7a42b7949672e98615d51870b156aafc8924c0",
            "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474",
            "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1",
            "10921e80f0f529c972351eb55c2d6912df9cb76ef1045401996606b0ddca2c42",
            "32f53516c83c75017284eb3f371a097c6fb216b0b0bed0197aacdb7924b7733d",
            "e34222b33e065429a0fa188882e178c14458680b07bdc384ce25f5f470a41f06",
            "a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a",
        }
    )
)

ALLOWED_SOURCE_ONLY_UPSTREAM_IDS = (
    "16b383ff8fd9ce3ec52737c9e68c079f2e908be4f9abd07ac4c4b41c16a9c7be",
    "f1892c934776d5601146b4b1fddbdcebb9dd4bb146f164ad3538c704633a6c34",
)

ALLOWED_STRUCTURAL_TOPOLOGY_IDS = (
    "c4ad4934340b4fe0854a7f85d778a6ebec9a52337da6577426d5585a155a7b21",
    "1e8b9ee52ed801d75d3ad6e5038b3abf6e4e6e639312b4eb57b45d4bd060a19e",
    "4504dbc17e530161ca185d58efeae68e571a58190dca579f987a57700267a428",
)


@dataclass(frozen=True, slots=True)
class HistoricalIdentityDispositionRegistryV1:
    historical_failure_record_ids: tuple[str, ...] = (
        HISTORICAL_FAILURE_RECORD_IDS
    )
    forbidden_v072_target_identity_ids: tuple[str, ...] = (
        FORBIDDEN_V072_TARGET_IDENTITY_IDS
    )
    allowed_source_only_upstream_ids: tuple[str, ...] = (
        ALLOWED_SOURCE_ONLY_UPSTREAM_IDS
    )
    allowed_structural_topology_ids: tuple[str, ...] = (
        ALLOWED_STRUCTURAL_TOPOLOGY_IDS
    )

    def __post_init__(self) -> None:
        if (
            self.historical_failure_record_ids
            != HISTORICAL_FAILURE_RECORD_IDS
            or self.forbidden_v072_target_identity_ids
            != FORBIDDEN_V072_TARGET_IDENTITY_IDS
            or self.allowed_source_only_upstream_ids
            != ALLOWED_SOURCE_ONLY_UPSTREAM_IDS
            or self.allowed_structural_topology_ids
            != ALLOWED_STRUCTURAL_TOPOLOGY_IDS
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "historical identity disposition changed"
            )
        groups = (
            self.historical_failure_record_ids,
            self.forbidden_v072_target_identity_ids,
            self.allowed_source_only_upstream_ids,
            self.allowed_structural_topology_ids,
        )
        for group in groups:
            if len(group) != len(set(group)):
                raise V075FreshCampaignAuthorityInvariantViolation(
                    "historical disposition contains a duplicate identity"
                )
            for value in group:
                _cid(value, "historical disposition identity")
        if (
            set(self.historical_failure_record_ids)
            & set(self.forbidden_v072_target_identity_ids)
            or set(self.allowed_source_only_upstream_ids)
            & set(self.forbidden_v072_target_identity_ids)
            or set(self.allowed_structural_topology_ids)
            & set(self.forbidden_v072_target_identity_ids)
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "historical identity roles overlap"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_historical_identity_disposition_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "historical_failure_records": [
                {
                    "record_id": value,
                    "role": "PROVENANCE_AND_REGRESSION_ONLY",
                    "scientific_input_allowed": False,
                }
                for value in self.historical_failure_record_ids
            ],
            "forbidden_v072_target_identity_ids": list(
                self.forbidden_v072_target_identity_ids
            ),
            "allowed_source_only_upstream_ids": list(
                self.allowed_source_only_upstream_ids
            ),
            "allowed_structural_topology_ids": list(
                self.allowed_structural_topology_ids
            ),
            "v072_target_evidence_reuse_allowed": False,
            "v072_attempt_resume_or_retry_allowed": False,
            "source_only_evidence_requires_fresh_v075_semantic_wrapper": True,
            "structural_fingerprint_is_not_target_evidence": True,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("historical_disposition", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}

    def assert_fresh_target_identity(self, value: Any, *, field: str) -> str:
        canonical = _cid(value, field)
        rejected = (
            set(self.historical_failure_record_ids)
            | set(self.forbidden_v072_target_identity_ids)
            | set(self.allowed_source_only_upstream_ids)
            | set(self.allowed_structural_topology_ids)
        )
        if canonical in rejected:
            raise V075FreshCampaignAuthorityInvariantViolation(
                f"{field} reuses a non-target or historical V0-072 identity"
            )
        return canonical


def freeze_historical_identity_disposition_registry_v1(
) -> HistoricalIdentityDispositionRegistryV1:
    return HistoricalIdentityDispositionRegistryV1()


def assert_no_v072_target_identity_material_v1(
    value: Any,
    *,
    allow_source_only_upstream_ids: bool = False,
) -> None:
    """Recursively reject historical target roles from a future input.

    The disposition registry itself is the sole document allowed to enumerate
    forbidden target IDs.  A future production source wrapper may explicitly
    allow the two source-only upstream IDs, but no target authority field may.
    """

    registry = freeze_historical_identity_disposition_registry_v1()
    forbidden = (
        set(registry.historical_failure_record_ids)
        | set(registry.forbidden_v072_target_identity_ids)
    )
    source_only = set(registry.allowed_source_only_upstream_ids)

    def visit(item: Any) -> None:
        if type(item) is str:
            if item in forbidden:
                raise V075FreshCampaignAuthorityInvariantViolation(
                    "future input contains a historical V0-072 target identity"
                )
            if item in source_only and not allow_source_only_upstream_ids:
                raise V075FreshCampaignAuthorityInvariantViolation(
                    "target input contains a source-only upstream identity"
                )
            if item.startswith(("acfqp:v072-", "acfqp.v072_")):
                raise V075FreshCampaignAuthorityInvariantViolation(
                    "future input contains a V0-072 target schema/domain"
                )
            return
        if type(item) in (tuple, list):
            for nested in item:
                visit(nested)
            return
        if type(item) is dict:
            for key, nested in item.items():
                normalized = key.lower().replace("-", "_")
                if "v072_target" in normalized or "old_target" in normalized:
                    allowed_negative_declaration = (
                        normalized
                        in {
                            "old_target_tape_reuse_allowed",
                            "old_target_tape_or_evidence_reuse_allowed",
                        }
                        and nested is False
                    )
                    if not allowed_negative_declaration:
                        raise V075FreshCampaignAuthorityInvariantViolation(
                            "future input declares a historical target channel"
                        )
                visit(key)
                visit(nested)
            return
        if item is None or type(item) in (bool, int):
            return
        raise V075FreshCampaignAuthorityInvariantViolation(
            "future identity material is not canonical JSON"
        )

    visit(value)


def _canonical_edges(
    edges: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({tuple(sorted(edge)) for edge in edges}))


K7_TOPOLOGY = GraphTopologyV1(
    7,
    tuple(combinations(range(7), 2)),
)
W7_TOPOLOGY = GraphTopologyV1(
    7,
    _canonical_edges(
        tuple((index, (index + 1) % 6) for index in range(6))
        + tuple((6, index) for index in range(6))
    ),
)
K7_MINUS_TWO_TOPOLOGY = GraphTopologyV1(
    7,
    tuple(
        edge
        for edge in combinations(range(7), 2)
        if edge not in {(4, 6), (5, 6)}
    ),
)

if (
    K7_TOPOLOGY.topology_id,
    W7_TOPOLOGY.topology_id,
    K7_MINUS_TWO_TOPOLOGY.topology_id,
) != ALLOWED_STRUCTURAL_TOPOLOGY_IDS:
    raise RuntimeError("registered V0-075 structural topology changed")

_CONTEXT_SPECS = (
    (
        "heldout_graph_k7_fresh_replication_v075_1",
        K7_TOPOLOGY,
        96,
    ),
    (
        "heldout_graph_w7_fresh_replication_v075_1",
        W7_TOPOLOGY,
        48,
    ),
    (
        "heldout_graph_k7_minus_two_fresh_replication_v075_1",
        K7_MINUS_TWO_TOPOLOGY,
        96,
    ),
)

_HIDDEN_LAW_SPECS = (
    (
        (1, Fraction(991, 1_000)),
        (2, Fraction(7, 1_000)),
        (3, Fraction(2, 1_000)),
    ),
    (
        (1, Fraction(197, 200)),
        (2, Fraction(3, 200)),
    ),
    (
        (1, Fraction(393, 400)),
        (2, Fraction(3, 200)),
        (3, Fraction(1, 400)),
    ),
)


def _generation_seed_payload(registry_id: str) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_target_family_generation_seed.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "generation_key": TARGET_FAMILY_GENERATION_KEY,
        "fresh_replication_ordinal": 1,
        "historical_disposition_registry_id": registry_id,
        "scientific_parameters_copied_before_target_access": True,
        "historical_target_evidence_used": False,
        "target_tapes_opened": False,
        "target_observations_generated": 0,
    }


def _canonical_generation_seed_id() -> str:
    registry = freeze_historical_identity_disposition_registry_v1()
    return _content_id(
        "family_seed",
        _generation_seed_payload(registry.registry_id),
    )


@dataclass(frozen=True, slots=True)
class V075ReplicateContextV1:
    generation_seed_id: str
    replicate_ordinal: int
    context_key: str
    topology: GraphTopologyV1
    maximum_physical_rows_per_confidence_epoch: int
    root_ranks: tuple[int, ...] = ROOT_RANKS
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE
    rank_cap: int = RANK_CAP
    reward_ceiling: Fraction = REWARD_CEILING
    normalized_regret_tolerance: Fraction = NORMALIZED_REGRET_TOLERANCE
    hidden_law_serialized: bool = False
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.replicate_ordinal) is not int
            or self.replicate_ordinal not in range(3)
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "replicate context ordinal is invalid"
            )
        key, topology, row_cap = _CONTEXT_SPECS[self.replicate_ordinal]
        if (
            self.generation_seed_id != _canonical_generation_seed_id()
            or self.context_key != key
            or self.topology != topology
            or self.maximum_physical_rows_per_confidence_epoch != row_cap
            or self.root_ranks != ROOT_RANKS
            or self.horizon != HORIZON
            or self.risk_tolerance != RISK_TOLERANCE
            or self.rank_cap != RANK_CAP
            or self.reward_ceiling != REWARD_CEILING
            or self.normalized_regret_tolerance
            != NORMALIZED_REGRET_TOLERANCE
            or self.hidden_law_serialized is not False
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "fresh replicate context changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_replicate_context.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "generation_seed_id": self.generation_seed_id,
            "replicate_ordinal": self.replicate_ordinal,
            "context_key": self.context_key,
            "base_topology": self.topology.to_document(),
            "base_topology_id": self.topology.topology_id,
            "root_ranks": list(self.root_ranks),
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "rank_cap": self.rank_cap,
            "reward_ceiling": _fdoc(self.reward_ceiling),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "maximum_physical_rows_per_confidence_epoch": (
                self.maximum_physical_rows_per_confidence_epoch
            ),
            "fresh_statistical_replicate": True,
            "new_structural_generality_claimed": False,
            "hidden_law_serialized": False,
            "target_execution_allowed": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("replicate_context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class V075TargetFamilyGenerationV1:
    historical_disposition_registry_id: str
    generation_key: str = TARGET_FAMILY_GENERATION_KEY
    fresh_replication_ordinal: int = 1
    historical_target_evidence_used: bool = False
    target_tapes_opened: bool = False
    target_observations_generated: int = 0
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        registry = freeze_historical_identity_disposition_registry_v1()
        if (
            self.historical_disposition_registry_id != registry.registry_id
            or self.generation_key != TARGET_FAMILY_GENERATION_KEY
            or self.fresh_replication_ordinal != 1
            or self.historical_target_evidence_used is not False
            or self.target_tapes_opened is not False
            or self.target_observations_generated != 0
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "target family generation changed or became executable"
            )

    @property
    def generation_seed_id(self) -> str:
        return _content_id(
            "family_seed",
            _generation_seed_payload(
                self.historical_disposition_registry_id
            ),
        )

    @property
    def replicate_contexts(self) -> tuple[V075ReplicateContextV1, ...]:
        return tuple(
            V075ReplicateContextV1(
                self.generation_seed_id,
                ordinal,
                key,
                topology,
                row_cap,
            )
            for ordinal, (key, topology, row_cap) in enumerate(
                _CONTEXT_SPECS
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_generation_seed_payload(
                self.historical_disposition_registry_id
            ),
            "schema": "acfqp.v075_target_family_generation.v1",
            "generation_seed_id": self.generation_seed_id,
            "replicate_contexts": [
                context.to_document()
                for context in self.replicate_contexts
            ],
            "replicate_context_ids": [
                context.context_id
                for context in self.replicate_contexts
            ],
            "context_count": 3,
            "fresh_identity_not_new_structural_generality": True,
            "target_execution_allowed": False,
        }

    @property
    def generation_id(self) -> str:
        return _content_id("family_generation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "generation_id": self.generation_id}


def freeze_v075_target_family_generation_v1(
) -> V075TargetFamilyGenerationV1:
    registry = freeze_historical_identity_disposition_registry_v1()
    return V075TargetFamilyGenerationV1(registry.registry_id)


@dataclass(frozen=True, slots=True)
class V075HiddenSpawnLawV1:
    family_generation_id: str
    context_id: str
    replicate_ordinal: int
    rank_probabilities: tuple[tuple[int, Fraction], ...]
    role: str = AUTHORITY_ROLE
    target_tapes_opened: bool = False
    target_observations_generated: int = 0
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        family = freeze_v075_target_family_generation_v1()
        if (
            type(self.replicate_ordinal) is not int
            or self.replicate_ordinal not in range(3)
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "hidden-law replicate ordinal is invalid"
            )
        context = family.replicate_contexts[self.replicate_ordinal]
        expected = _HIDDEN_LAW_SPECS[self.replicate_ordinal]
        if (
            self.family_generation_id != family.generation_id
            or self.context_id != context.context_id
            or self.rank_probabilities != expected
            or sum(
                (probability for _, probability in self.rank_probabilities),
                Fraction(0),
            )
            != 1
            or self.role != AUTHORITY_ROLE
            or self.target_tapes_opened is not False
            or self.target_observations_generated != 0
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "fresh hidden-law authority changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_hidden_spawn_law.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation_id": self.family_generation_id,
            "context_id": self.context_id,
            "replicate_ordinal": self.replicate_ordinal,
            "rank_probabilities": [
                {"rank": rank, "probability": _fdoc(probability)}
                for rank, probability in self.rank_probabilities
            ],
            "role": self.role,
            "construction_fixture_only": True,
            "production_heldout_evidence_allowed": False,
            "law_was_exposed_during_construction": True,
            "frozen_before_target_access": True,
            "target_tapes_opened": False,
            "target_observations_generated": 0,
            "target_execution_allowed": False,
        }

    @property
    def law_id(self) -> str:
        return _content_id("hidden_law", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "law_id": self.law_id}


@dataclass(frozen=True, slots=True)
class V075EnvironmentManifestV1:
    family_generation_id: str
    laws: tuple[V075HiddenSpawnLawV1, ...]
    target_tapes_opened: bool = False
    target_observations_generated: int = 0
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        family = freeze_v075_target_family_generation_v1()
        expected = tuple(
            V075HiddenSpawnLawV1(
                family.generation_id,
                context.context_id,
                ordinal,
                _HIDDEN_LAW_SPECS[ordinal],
            )
            for ordinal, context in enumerate(family.replicate_contexts)
        )
        if (
            self.family_generation_id != family.generation_id
            or self.laws != expected
            or self.target_tapes_opened is not False
            or self.target_observations_generated != 0
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "fresh environment manifest changed or became executable"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_environment_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation_id": self.family_generation_id,
            "laws": [law.to_document() for law in self.laws],
            "law_ids": [law.law_id for law in self.laws],
            "authority_role": AUTHORITY_ROLE,
            "construction_fixture_only": True,
            "production_heldout_evidence_allowed": False,
            "law_was_exposed_during_construction": True,
            "target_tapes_opened": False,
            "target_observations_generated": 0,
            "frozen_before_target_access": True,
            "target_execution_allowed": False,
        }

    @property
    def environment_manifest_id(self) -> str:
        return _content_id("environment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "environment_manifest_id": self.environment_manifest_id,
        }


def freeze_v075_environment_manifest_v1(
) -> V075EnvironmentManifestV1:
    family = freeze_v075_target_family_generation_v1()
    return V075EnvironmentManifestV1(
        family.generation_id,
        tuple(
            V075HiddenSpawnLawV1(
                family.generation_id,
                context.context_id,
                ordinal,
                _HIDDEN_LAW_SPECS[ordinal],
            )
            for ordinal, context in enumerate(family.replicate_contexts)
        ),
    )


@dataclass(frozen=True, slots=True)
class V075OccurrenceTemplateV1:
    family_generation_id: str
    context_id: str
    context_ordinal: int
    arm: str
    occurrence_ordinal: int
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        family = freeze_v075_target_family_generation_v1()
        if (
            type(self.context_ordinal) is not int
            or self.context_ordinal not in range(3)
            or self.context_id
            != family.replicate_contexts[self.context_ordinal].context_id
            or self.family_generation_id != family.generation_id
            or self.arm not in ARM_ORDER
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal
            != self.context_ordinal * len(ARM_ORDER)
            + ARM_ORDER.index(self.arm)
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "registered occurrence template is not context-major"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_registered_occurrence_template.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation_id": self.family_generation_id,
            "context_id": self.context_id,
            "context_ordinal": self.context_ordinal,
            "arm": self.arm,
            "occurrence_ordinal": self.occurrence_ordinal,
            "fresh_target_identity_required": True,
            "old_target_tape_reuse_allowed": False,
            "replacement_allowed": False,
            "target_execution_allowed": False,
        }

    @property
    def template_id(self) -> str:
        return _content_id("occurrence_template", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "template_id": self.template_id}


def registered_v075_occurrence_templates_v1(
) -> tuple[V075OccurrenceTemplateV1, ...]:
    family = freeze_v075_target_family_generation_v1()
    return tuple(
        V075OccurrenceTemplateV1(
            family.generation_id,
            context.context_id,
            context_ordinal,
            arm,
            context_ordinal * len(ARM_ORDER) + arm_ordinal,
        )
        for context_ordinal, context in enumerate(family.replicate_contexts)
        for arm_ordinal, arm in enumerate(ARM_ORDER)
    )


@dataclass(frozen=True, slots=True)
class V075TapeDerivationRuleV1:
    historical_disposition_registry_id: str
    rule_key: str = "V075_ANCHOR_DERIVED_ARM_FREE_TARGET_TAPE_NAMESPACE"
    anchor_identity_enters_namespace: bool = True
    final_preregistration_identity_enters_namespace: bool = True
    worker_count_enters_namespace: bool = False
    worker_pid_enters_namespace: bool = False
    launch_order_enters_namespace: bool = False
    completion_order_enters_namespace: bool = False
    caller_nonce_allowed: bool = False
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        registry = freeze_historical_identity_disposition_registry_v1()
        if (
            self.historical_disposition_registry_id != registry.registry_id
            or self.rule_key
            != "V075_ANCHOR_DERIVED_ARM_FREE_TARGET_TAPE_NAMESPACE"
            or self.anchor_identity_enters_namespace is not True
            or self.final_preregistration_identity_enters_namespace is not True
            or self.worker_count_enters_namespace is not False
            or self.worker_pid_enters_namespace is not False
            or self.launch_order_enters_namespace is not False
            or self.completion_order_enters_namespace is not False
            or self.caller_nonce_allowed is not False
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "target-tape derivation rule changed or became executable"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_target_tape_derivation_rule.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "historical_disposition_registry_id": (
                self.historical_disposition_registry_id
            ),
            "rule_key": self.rule_key,
            "namespace_inputs": [
                "final_preregistration_id",
                "remote_main_anchor_id",
                "target_family_generation_id",
                "environment_manifest_id",
                "observer_profile_id",
            ],
            "arm_free_pairing_inputs": [
                "target_tape_namespace_id",
                "replicate_context_id",
                "row_binding_id",
                "support_lineage_id",
                "lane",
            ],
            "arm_enters_pairing_group": False,
            "anchor_identity_enters_namespace": True,
            "final_preregistration_identity_enters_namespace": True,
            "worker_count_enters_namespace": False,
            "worker_pid_enters_namespace": False,
            "launch_order_enters_namespace": False,
            "completion_order_enters_namespace": False,
            "caller_nonce_allowed": False,
            "observer_open_authority": False,
            "target_execution_allowed": False,
        }

    @property
    def rule_id(self) -> str:
        return _content_id("tape_derivation_rule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "rule_id": self.rule_id}


def freeze_v075_tape_derivation_rule_v1() -> V075TapeDerivationRuleV1:
    registry = freeze_historical_identity_disposition_registry_v1()
    return V075TapeDerivationRuleV1(registry.registry_id)


@dataclass(frozen=True, slots=True)
class V075PreregistrationDraftV1:
    historical_disposition_registry_id: str
    family_generation_id: str
    context_ids: tuple[str, ...]
    environment_manifest_id: str
    law_ids: tuple[str, ...]
    occurrence_templates: tuple[V075OccurrenceTemplateV1, ...]
    tape_derivation_rule_id: str
    confirmatory_execution_manifest_id: None = None
    anchor_commit_id: None = None
    target_execution_allowed: bool = False
    official_execution_allowed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"
    counter_completeness_gate_status: str = "NOT_RUN"
    workload_economics_gate_status: str = "NOT_RUN"
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        registry = freeze_historical_identity_disposition_registry_v1()
        family = freeze_v075_target_family_generation_v1()
        environment = freeze_v075_environment_manifest_v1()
        rule = freeze_v075_tape_derivation_rule_v1()
        templates = registered_v075_occurrence_templates_v1()
        if (
            self.historical_disposition_registry_id != registry.registry_id
            or self.family_generation_id != family.generation_id
            or self.context_ids
            != tuple(context.context_id for context in family.replicate_contexts)
            or self.environment_manifest_id
            != environment.environment_manifest_id
            or self.law_ids != tuple(law.law_id for law in environment.laws)
            or self.occurrence_templates != templates
            or self.tape_derivation_rule_id != rule.rule_id
            or self.confirmatory_execution_manifest_id is not None
            or self.anchor_commit_id is not None
            or self.target_execution_allowed is not False
            or self.official_execution_allowed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
            or self.counter_completeness_gate_status != "NOT_RUN"
            or self.workload_economics_gate_status != "NOT_RUN"
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "fresh campaign preregistration draft changed or unlocked"
            )
        if (
            len(self.occurrence_templates) != EXPECTED_OCCURRENCE_COUNT
            or len(
                {template.template_id for template in self.occurrence_templates}
            )
            != EXPECTED_OCCURRENCE_COUNT
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "preregistration must contain fifteen distinct occurrences"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_fresh_campaign_preregistration_draft.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_role": AUTHORITY_ROLE,
            "construction_fixture_only": True,
            "production_heldout_evidence_allowed": False,
            "historical_disposition_registry_id": (
                self.historical_disposition_registry_id
            ),
            "family_generation_id": self.family_generation_id,
            "context_ids": list(self.context_ids),
            "environment_manifest_id": self.environment_manifest_id,
            "law_ids": list(self.law_ids),
            "arm_order": list(ARM_ORDER),
            "occurrence_templates": [
                template.to_document()
                for template in self.occurrence_templates
            ],
            "occurrence_count": EXPECTED_OCCURRENCE_COUNT,
            "order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
            "campaign_early_stop_allowed": False,
            "replacement_allowed": False,
            "maximum_attempts_for_future_authority_chain": 1,
            "old_target_tape_or_evidence_reuse_allowed": False,
            "fresh_target_tape_namespace_required": True,
            "tape_derivation_rule_id": self.tape_derivation_rule_id,
            "maximum_rounds": MAX_ROUNDS,
            "initial_schedule": {
                "discovery_draws_per_physical_row": (
                    INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                ),
                "validation_draws_per_physical_row": (
                    INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
                ),
                "starts_cold": True,
                "same_for_all_arms": True,
            },
            "incremental_schedule": {
                "promotion_validation_draws_per_round": (
                    PROMOTION_VALIDATION_DRAWS_PER_ROUND
                ),
                "new_child_discovery_draws_per_physical_row": (
                    NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                ),
                "new_child_validation_draws_per_physical_row": (
                    NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
                ),
                "maximum_new_child_action_rows_across_rounds": (
                    MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS
                ),
                "maximum_two_round_incremental_draw_cap_per_arm": (
                    MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
                ),
            },
            "direct_validation_checkpoints": list(
                DIRECT_VALIDATION_CHECKPOINTS
            ),
            "confidence_allocation": {
                "row_epoch_beta": _fdoc(ROW_EPOCH_BETA),
                "campaign_joint_tail_upper": _fdoc(
                    CAMPAIGN_JOINT_TAIL_UPPER
                ),
                "campaign_confidence_lower": _fdoc(
                    CAMPAIGN_CONFIDENCE_LOWER
                ),
            },
            "terminal_codes": list(TERMINAL_CODES),
            "primary_endpoint": (
                "SOURCE_ONLINE_DRAWS_STRICTLY_LESS_THAN_NO_PRIOR"
            ),
            "matched_sample_tax_endpoint": (
                "SOURCE_ONLINE_DRAWS_LE_MATCHED_DIRECT_GROUND"
            ),
            "formal_exact_iid_implementation_claimed": False,
            "confirmatory_execution_manifest_id": None,
            "confirmatory_profile_finalized": False,
            "anchor_commit_id": None,
            "target_execution_allowed": False,
            "official_execution_allowed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def preregistration_draft_id(self) -> str:
        return _content_id("preregistration_draft", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration_draft_id": self.preregistration_draft_id,
        }


def freeze_v075_preregistration_draft_v1(
) -> V075PreregistrationDraftV1:
    registry = freeze_historical_identity_disposition_registry_v1()
    family = freeze_v075_target_family_generation_v1()
    environment = freeze_v075_environment_manifest_v1()
    rule = freeze_v075_tape_derivation_rule_v1()
    return V075PreregistrationDraftV1(
        registry.registry_id,
        family.generation_id,
        tuple(context.context_id for context in family.replicate_contexts),
        environment.environment_manifest_id,
        tuple(law.law_id for law in environment.laws),
        registered_v075_occurrence_templates_v1(),
        rule.rule_id,
    )


REQUIRED_PRODUCTION_COMPONENT_ROLES = (
    "v075 production semantic source-proposal compiler",
    "v075 production source-proposal independent verifier",
    "v075 anchor-gated target observer adapter",
    "v075 registered adaptive and matched-direct occurrence worker",
    "v075 occurrence-parallel child journal and canonical merge",
    "v074 total partial-support exact lift",
    "v075 independent exact-envelope evaluator",
    "v075 complete-bundle and endpoint verifier",
    "v075 runtime dependency lock and exact test command",
)

MANIFEST_DRAFT_BLOCKERS = (
    "PRODUCTION_SOURCE_PROPOSAL_ARCHIVE_NOT_BOUND",
    "PRODUCTION_OCCURRENCE_WORKER_NOT_BOUND",
    "COMPONENT_TREE_NOT_FROZEN",
    "TEST_COMMAND_NOT_FROZEN",
    "RUNTIME_DEPENDENCY_LOCK_NOT_FROZEN",
    "REMOTE_MAIN_ANCHOR_NOT_MINTED",
)


@dataclass(frozen=True, slots=True)
class V075ManifestDraftV1:
    historical_disposition_registry_id: str
    family_generation_id: str
    environment_manifest_id: str
    preregistration_draft_id: str
    tape_derivation_rule_id: str
    required_component_roles: tuple[str, ...] = (
        REQUIRED_PRODUCTION_COMPONENT_ROLES
    )
    blockers: tuple[str, ...] = MANIFEST_DRAFT_BLOCKERS
    final_preregistration_id_embedded: bool = False
    finalization_ready: bool = False
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        registry = freeze_historical_identity_disposition_registry_v1()
        family = freeze_v075_target_family_generation_v1()
        environment = freeze_v075_environment_manifest_v1()
        preregistration = freeze_v075_preregistration_draft_v1()
        rule = freeze_v075_tape_derivation_rule_v1()
        if (
            self.historical_disposition_registry_id != registry.registry_id
            or self.family_generation_id != family.generation_id
            or self.environment_manifest_id
            != environment.environment_manifest_id
            or self.preregistration_draft_id
            != preregistration.preregistration_draft_id
            or self.tape_derivation_rule_id != rule.rule_id
            or self.required_component_roles
            != REQUIRED_PRODUCTION_COMPONENT_ROLES
            or self.blockers != MANIFEST_DRAFT_BLOCKERS
            or self.final_preregistration_id_embedded is not False
            or self.finalization_ready is not False
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "execution-manifest draft changed or became authorizing"
            )
        for role in self.required_component_roles:
            _token(role, "required production component role")
        for blocker in self.blockers:
            _token(blocker, "manifest blocker")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_confirmatory_execution_manifest_draft.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "historical_disposition_registry_id": (
                self.historical_disposition_registry_id
            ),
            "family_generation_id": self.family_generation_id,
            "environment_manifest_id": self.environment_manifest_id,
            "preregistration_draft_id": self.preregistration_draft_id,
            "tape_derivation_rule_id": self.tape_derivation_rule_id,
            "required_component_roles": list(
                self.required_component_roles
            ),
            "blockers": list(self.blockers),
            "component_registry_id": None,
            "production_source_proposal_archive_id": None,
            "test_command_manifest_id": None,
            "runtime_dependency_lock_id": None,
            "final_preregistration_id_embedded": False,
            "future_binding_direction": (
                "FINAL_PREREGISTRATION_BINDS_FINAL_MANIFEST_ID_ONE_WAY"
            ),
            "finalization_ready": False,
            "remote_main_anchor_id": None,
            "target_execution_allowed": False,
        }

    @property
    def manifest_draft_id(self) -> str:
        return _content_id("manifest_draft", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_draft_id": self.manifest_draft_id}


def freeze_v075_manifest_draft_v1() -> V075ManifestDraftV1:
    registry = freeze_historical_identity_disposition_registry_v1()
    family = freeze_v075_target_family_generation_v1()
    environment = freeze_v075_environment_manifest_v1()
    preregistration = freeze_v075_preregistration_draft_v1()
    rule = freeze_v075_tape_derivation_rule_v1()
    return V075ManifestDraftV1(
        registry.registry_id,
        family.generation_id,
        environment.environment_manifest_id,
        preregistration.preregistration_draft_id,
        rule.rule_id,
    )


@dataclass(frozen=True, slots=True)
class V075TargetTapeNamespaceV1:
    remote_main_anchor_id: str
    final_preregistration_id: str
    family_generation_id: str
    environment_manifest_id: str
    observer_profile_id: str
    tape_derivation_rule_id: str
    historical_disposition_registry_id: str
    remote_main_anchor_semantically_verified: bool = False
    observer_open_authority: bool = False
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        registry = freeze_historical_identity_disposition_registry_v1()
        family = freeze_v075_target_family_generation_v1()
        environment = freeze_v075_environment_manifest_v1()
        rule = freeze_v075_tape_derivation_rule_v1()
        preregistration = freeze_v075_preregistration_draft_v1()
        anchor = registry.assert_fresh_target_identity(
            self.remote_main_anchor_id,
            field="claimed future remote-main anchor",
        )
        final_preregistration = registry.assert_fresh_target_identity(
            self.final_preregistration_id,
            field="claimed future final preregistration",
        )
        observer_profile = registry.assert_fresh_target_identity(
            self.observer_profile_id,
            field="future V0-075 observer profile",
        )
        if (
            len({anchor, final_preregistration, observer_profile}) != 3
            or final_preregistration
            == preregistration.preregistration_draft_id
            or self.family_generation_id != family.generation_id
            or self.environment_manifest_id
            != environment.environment_manifest_id
            or self.tape_derivation_rule_id != rule.rule_id
            or self.historical_disposition_registry_id != registry.registry_id
            or self.remote_main_anchor_semantically_verified is not False
            or self.observer_open_authority is not False
            or self.target_execution_allowed is not False
        ):
            raise V075FreshCampaignAuthorityInvariantViolation(
                "target-tape namespace is stale, historical, or authorizing"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_target_tape_namespace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_role": AUTHORITY_ROLE,
            "construction_fixture_only": True,
            "production_heldout_evidence_allowed": False,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "family_generation_id": self.family_generation_id,
            "environment_manifest_id": self.environment_manifest_id,
            "observer_profile_id": self.observer_profile_id,
            "tape_derivation_rule_id": self.tape_derivation_rule_id,
            "historical_disposition_registry_id": (
                self.historical_disposition_registry_id
            ),
            "anchor_identity_used_as_namespace_input": True,
            "final_preregistration_identity_used_as_namespace_input": True,
            "worker_count_used_as_namespace_input": False,
            "worker_pid_used_as_namespace_input": False,
            "launch_order_used_as_namespace_input": False,
            "completion_order_used_as_namespace_input": False,
            "caller_nonce_used": False,
            "remote_main_anchor_semantically_verified": False,
            "observer_open_authority": False,
            "target_execution_allowed": False,
        }

    @property
    def target_tape_namespace_id(self) -> str:
        return _content_id("target_tape_namespace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "target_tape_namespace_id": self.target_tape_namespace_id,
        }


def derive_v075_target_tape_namespace_identity_v1(
    *,
    remote_main_anchor_id: str,
    final_preregistration_id: str,
    observer_profile_id: str,
) -> V075TargetTapeNamespaceV1:
    """Derive a fresh namespace identity without granting observer access.

    The arguments are identities only.  Phase one has no Git semantic anchor
    verifier or private capability, so the returned object deliberately keeps
    all execution booleans false.
    """

    registry = freeze_historical_identity_disposition_registry_v1()
    family = freeze_v075_target_family_generation_v1()
    environment = freeze_v075_environment_manifest_v1()
    rule = freeze_v075_tape_derivation_rule_v1()
    return V075TargetTapeNamespaceV1(
        remote_main_anchor_id=remote_main_anchor_id,
        final_preregistration_id=final_preregistration_id,
        family_generation_id=family.generation_id,
        environment_manifest_id=environment.environment_manifest_id,
        observer_profile_id=observer_profile_id,
        tape_derivation_rule_id=rule.rule_id,
        historical_disposition_registry_id=registry.registry_id,
    )


__all__ = [
    "ALLOWED_SOURCE_ONLY_UPSTREAM_IDS",
    "ALLOWED_STRUCTURAL_TOPOLOGY_IDS",
    "AUTHORITY_ROLE",
    "ARM_ORDER",
    "DOMAIN_TAGS",
    "EXPECTED_OCCURRENCE_COUNT",
    "FORBIDDEN_V072_TARGET_IDENTITY_IDS",
    "HISTORICAL_FAILURE_RECORD_IDS",
    "HistoricalIdentityDispositionRegistryV1",
    "PROFILE_KEY",
    "PRODUCTION_HELDOUT_EVIDENCE_ALLOWED",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_FAMILY_GENERATION_KEY",
    "V075EnvironmentManifestV1",
    "V075FreshCampaignAuthorityInvariantViolation",
    "V075HiddenSpawnLawV1",
    "V075ManifestDraftV1",
    "V075OccurrenceTemplateV1",
    "V075PreregistrationDraftV1",
    "V075ReplicateContextV1",
    "V075TapeDerivationRuleV1",
    "V075TargetFamilyGenerationV1",
    "V075TargetTapeNamespaceV1",
    "assert_no_v072_target_identity_material_v1",
    "derive_v075_target_tape_namespace_identity_v1",
    "freeze_historical_identity_disposition_registry_v1",
    "freeze_v075_environment_manifest_v1",
    "freeze_v075_manifest_draft_v1",
    "freeze_v075_preregistration_draft_v1",
    "freeze_v075_tape_derivation_rule_v1",
    "freeze_v075_target_family_generation_v1",
    "registered_v075_occurrence_templates_v1",
]
