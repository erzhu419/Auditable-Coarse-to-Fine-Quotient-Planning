"""Law-free private environment generation profile for V0-075.

Only the public candidate grid and deterministic selection protocol are
serialized.  A high-entropy generation seed is supplied as in-memory
``bytes`` and is never retained by the generated environment.  The selected
laws have no public identity and expose no serialization method.

Selection is domain-separated by the frozen public family, profile, context
identity, context ordinal, and selection round.  It samples without
replacement from a public exact-rational grid, so the three contexts receive
distinct laws while preserving the registered context order.

The grid requires positive ranks ``{1, 2, 3}``, keeps rank-1 mass in a
high-probability range comparable to the retired construction fixture, and
uses a rank-2 numerator congruence class disjoint from every exposed
construction law.  Callers cannot supply a law.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_public_campaign_authority_v1 as public


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_private_environment_generation_profile_v1"

MINIMUM_SECRET_GENERATION_SEED_BYTES = 32
MINIMUM_SECRET_GENERATION_SEED_DISTINCT_BYTES = 16
RANK_SUPPORT = (1, 2, 3)
PROBABILITY_DENOMINATOR = 10_000

# This is the public preregistered candidate grid, not a selected production
# law.  Every rank-2 numerator is 1 modulo 20; the exposed construction laws
# lie outside this congruence class.  Positive rank 3 additionally excludes
# the exposed two-rank construction law.
RANK_2_NUMERATOR_GRID = (61, 81, 101, 121, 141, 161)
RANK_3_NUMERATOR_GRID = (11, 21, 31, 41, 51)
CANDIDATE_COUNT = len(RANK_2_NUMERATOR_GRID) * len(RANK_3_NUMERATOR_GRID)

SELECTION_DOMAIN = (
    b"acfqp:v075-private-environment-generation-selection:v1"
)
PROFILE_DOMAIN = "acfqp:v075-private-environment-generation-profile:v1"

PRODUCTION_LAW_SERIALIZED = False
PRODUCTION_ENVIRONMENT_ID_SERIALIZED = False
OBSERVER_OPENED = False
TARGET_OBSERVATIONS_GENERATED = 0
TARGET_EXECUTION_ALLOWED = False


class V075PrivateEnvironmentGenerationInvariantViolation(ValueError):
    """The public profile or private generation boundary was violated."""


def _fail(message: str) -> None:
    raise V075PrivateEnvironmentGenerationInvariantViolation(message)


def _hash(payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            PROFILE_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075PrivateEnvironmentGenerationInvariantViolation(
            str(error)
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("profile probability bounds must use exact Fraction")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _candidate_laws() -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    laws = tuple(
        (
            (
                1,
                Fraction(
                    PROBABILITY_DENOMINATOR - rank_2 - rank_3,
                    PROBABILITY_DENOMINATOR,
                ),
            ),
            (2, Fraction(rank_2, PROBABILITY_DENOMINATOR)),
            (3, Fraction(rank_3, PROBABILITY_DENOMINATOR)),
        )
        for rank_2 in RANK_2_NUMERATOR_GRID
        for rank_3 in RANK_3_NUMERATOR_GRID
    )
    if (
        len(laws) != CANDIDATE_COUNT
        or len(set(laws)) != CANDIDATE_COUNT
        or any(
            tuple(rank for rank, _probability in law) != RANK_SUPPORT
            or any(
                type(probability) is not Fraction or probability <= 0
                for _rank, probability in law
            )
            or sum(
                (probability for _rank, probability in law),
                Fraction(0),
            )
            != 1
            for law in laws
        )
    ):  # pragma: no cover - frozen module-level grid invariant
        raise RuntimeError("V0-075 private environment grid is malformed")
    return laws


def _minimum_rank_1_probability() -> Fraction:
    return min(dict(law)[1] for law in _candidate_laws())


def _maximum_rank_1_probability() -> Fraction:
    return max(dict(law)[1] for law in _candidate_laws())


_PROFILE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PrivateEnvironmentGenerationProfileV1:
    """Public preregistration object; contains no selected private value."""

    _issuer: object
    family: public.V075PublicFamilyGenerationV1
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected_family = public.freeze_v075_public_family_generation_v1()
        if (
            self._issuer is not _PROFILE_ISSUER
            or type(self.family) is not public.V075PublicFamilyGenerationV1
            or self.family != expected_family
            or len(self.family.replicate_contexts) != 3
            or tuple(
                context.replicate_ordinal
                for context in self.family.replicate_contexts
            )
            != (0, 1, 2)
        ):
            _fail("private environment profile targets a stale public family")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(self._payload()),
        )

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def candidate_laws(
        self,
    ) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
        """Return the public candidate set, never the private selection."""

        return _candidate_laws()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_environment_generation_profile.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation_id": self.family.generation_id,
            "context_ids_in_generation_order": [
                context.context_id
                for context in self.family.replicate_contexts
            ],
            "context_ordinals": [0, 1, 2],
            "rank_support": list(RANK_SUPPORT),
            "probability_denominator": PROBABILITY_DENOMINATOR,
            "rank_2_numerator_grid": list(RANK_2_NUMERATOR_GRID),
            "rank_3_numerator_grid": list(RANK_3_NUMERATOR_GRID),
            "rank_2_numerator_congruence": {
                "modulus": 20,
                "residue": 1,
            },
            "minimum_rank_1_probability": _fdoc(
                _minimum_rank_1_probability()
            ),
            "maximum_rank_1_probability": _fdoc(
                _maximum_rank_1_probability()
            ),
            "candidate_count": CANDIDATE_COUNT,
            "selection_hash": "SHA256",
            "selection_domain": SELECTION_DOMAIN.decode("ascii"),
            "selection_sampling": (
                "EXACT_REJECTION_SAMPLED_UNIFORM_WITHOUT_REPLACEMENT_V1"
            ),
            "context_domain_separation_fields": [
                "profile_id",
                "family_generation_id",
                "context_id",
                "context_ordinal",
                "selection_round",
                "remaining_candidate_indices",
            ],
            "minimum_secret_generation_seed_bytes": (
                MINIMUM_SECRET_GENERATION_SEED_BYTES
            ),
            "minimum_secret_generation_seed_distinct_bytes": (
                MINIMUM_SECRET_GENERATION_SEED_DISTINCT_BYTES
            ),
            "caller_selected_law_allowed": False,
            "exposed_construction_law_allowed": False,
            "exposed_construction_exclusion_rule": (
                "FULL_POSITIVE_RANK_123_AND_RANK2_NUMERATOR_1_MOD_20_V1"
            ),
            "selected_law_serialized": False,
            "secret_generation_seed_serialized": False,
            "secret_generation_seed_digest_serialized": False,
            "secret_salt_serialized": False,
            "production_environment_id_serialized": False,
            "observer_opened": False,
            "target_observations_generated": 0,
            "target_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def freeze_v075_private_environment_generation_profile_v1(
) -> V075PrivateEnvironmentGenerationProfileV1:
    return V075PrivateEnvironmentGenerationProfileV1(
        _PROFILE_ISSUER,
        public.freeze_v075_public_family_generation_v1(),
    )


def _validated_secret_seed(value: Any) -> bytes:
    if (
        type(value) is not bytes
        or len(value) < MINIMUM_SECRET_GENERATION_SEED_BYTES
        or len(set(value)) < MINIMUM_SECRET_GENERATION_SEED_DISTINCT_BYTES
    ):
        _fail(
            "secret generation seed must be exact bytes, contain at least "
            "32 bytes, and pass the preregistered diversity floor"
        )
    return value


def _uniform_remaining_offset(
    *,
    secret_seed: bytes,
    profile: V075PrivateEnvironmentGenerationProfileV1,
    context: public.V075PublicReplicateContextV1,
    selection_round: int,
    remaining_candidate_indices: tuple[int, ...],
) -> int:
    if (
        type(context) is not public.V075PublicReplicateContextV1
        or type(selection_round) is not int
        or selection_round != context.replicate_ordinal
        or type(remaining_candidate_indices) is not tuple
        or not remaining_candidate_indices
        or tuple(sorted(set(remaining_candidate_indices)))
        != remaining_candidate_indices
    ):
        _fail("private selection context/order is malformed")
    modulus = len(remaining_candidate_indices)
    ceiling = 1 << 256
    acceptance_limit = ceiling - ceiling % modulus
    binding = canonical_json_bytes(
        {
            "schema": (
                "acfqp.v075_private_environment_generation_selection_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_id": profile.profile_id,
            "family_generation_id": profile.family.generation_id,
            "context_id": context.context_id,
            "context_ordinal": context.replicate_ordinal,
            "selection_round": selection_round,
            "remaining_candidate_indices": list(
                remaining_candidate_indices
            ),
        }
    )
    for counter in range(1 << 32):
        token = int.from_bytes(
            hashlib.sha256(
                SELECTION_DOMAIN
                + b"\x00"
                + secret_seed
                + b"\x00"
                + binding
                + b"\x00"
                + counter.to_bytes(4, "big")
            ).digest(),
            "big",
        )
        if token < acceptance_limit:
            return token % modulus
    raise RuntimeError("private environment rejection sampler exhausted")


_PRIVATE_GENERATOR_ISSUER = object()


@dataclass(frozen=True, slots=True, repr=False)
class V075PrivateGeneratedSpawnLawV1:
    """In-memory selected law; intentionally has no public serialization."""

    _issuer: object = field(repr=False)
    profile: V075PrivateEnvironmentGenerationProfileV1 = field(repr=False)
    context: public.V075PublicReplicateContextV1 = field(repr=False)
    rank_probabilities: tuple[tuple[int, Fraction], ...] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _PRIVATE_GENERATOR_ISSUER
            or type(self.profile)
            is not V075PrivateEnvironmentGenerationProfileV1
            or type(self.context) is not public.V075PublicReplicateContextV1
            or self.context
            != self.profile.family.replicate_contexts[
                self.context.replicate_ordinal
            ]
            or type(self.rank_probabilities) is not tuple
            or self.rank_probabilities not in self.profile.candidate_laws
            or tuple(rank for rank, _ in self.rank_probabilities)
            != RANK_SUPPORT
            or any(
                type(probability) is not Fraction or probability <= 0
                for _rank, probability in self.rank_probabilities
            )
            or sum(
                (
                    probability
                    for _rank, probability in self.rank_probabilities
                ),
                Fraction(0),
            )
            != 1
        ):
            _fail("private spawn law was caller-picked, stale, or malformed")

    @property
    def context_id(self) -> str:
        return self.context.context_id

    @property
    def replicate_ordinal(self) -> int:
        return self.context.replicate_ordinal

    def as_secret_law(self) -> tuple[tuple[int, Fraction], ...]:
        return self.rank_probabilities

    def __repr__(self) -> str:
        return (
            "<V075PrivateGeneratedSpawnLawV1 "
            f"context_ordinal={self.replicate_ordinal} redacted>"
        )

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("private generated spawn laws are not serializable")


@dataclass(frozen=True, slots=True, repr=False)
class V075PrivateGeneratedEnvironmentV1:
    """Ordered in-memory environment; no seed, salt, ID, or serializer."""

    _issuer: object = field(repr=False)
    profile: V075PrivateEnvironmentGenerationProfileV1 = field(repr=False)
    laws: tuple[V075PrivateGeneratedSpawnLawV1, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _PRIVATE_GENERATOR_ISSUER
            or type(self.profile)
            is not V075PrivateEnvironmentGenerationProfileV1
            or type(self.laws) is not tuple
            or len(self.laws) != len(self.profile.family.replicate_contexts)
            or any(
                type(law) is not V075PrivateGeneratedSpawnLawV1
                or law.profile != self.profile
                for law in self.laws
            )
            or tuple(law.context for law in self.laws)
            != self.profile.family.replicate_contexts
            or tuple(law.replicate_ordinal for law in self.laws) != (0, 1, 2)
            or len({law.rank_probabilities for law in self.laws}) != 3
        ):
            _fail("private environment context/order binding is invalid")

    @property
    def family(self) -> public.V075PublicFamilyGenerationV1:
        return self.profile.family

    def secret_laws_for_commitment(
        self,
    ) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
        return tuple(law.as_secret_law() for law in self.laws)

    def __repr__(self) -> str:
        return (
            "<V075PrivateGeneratedEnvironmentV1 "
            "context_count=3 selected_laws=redacted>"
        )

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("private generated environments are not serializable")


def generate_v075_private_environment_v1(
    *,
    profile: V075PrivateEnvironmentGenerationProfileV1,
    secret_generation_seed: bytes,
) -> V075PrivateGeneratedEnvironmentV1:
    """Deterministically select three exact laws without retaining the seed."""

    if type(profile) is not V075PrivateEnvironmentGenerationProfileV1:
        _fail("private generator requires the exact frozen profile type")
    expected = freeze_v075_private_environment_generation_profile_v1()
    if profile != expected:
        _fail("private generator profile is stale or caller-modified")
    seed = _validated_secret_seed(secret_generation_seed)
    candidates = profile.candidate_laws
    remaining = tuple(range(len(candidates)))
    selected: list[V075PrivateGeneratedSpawnLawV1] = []
    for context in profile.family.replicate_contexts:
        offset = _uniform_remaining_offset(
            secret_seed=seed,
            profile=profile,
            context=context,
            selection_round=context.replicate_ordinal,
            remaining_candidate_indices=remaining,
        )
        candidate_index = remaining[offset]
        selected.append(
            V075PrivateGeneratedSpawnLawV1(
                _PRIVATE_GENERATOR_ISSUER,
                profile,
                context,
                candidates[candidate_index],
            )
        )
        remaining = (
            remaining[:offset] + remaining[offset + 1 :]
        )
    return V075PrivateGeneratedEnvironmentV1(
        _PRIVATE_GENERATOR_ISSUER,
        profile,
        tuple(selected),
    )


def seal_v075_generated_private_environment_commitment_v1(
    *,
    generated_environment: V075PrivateGeneratedEnvironmentV1,
    secret_salt: bytes,
) -> public.V075OpaqueEnvironmentCommitmentV1:
    """Feed only an exact generated environment into the public opaque seal."""

    if (
        type(generated_environment)
        is not V075PrivateGeneratedEnvironmentV1
    ):
        _fail(
            "opaque commitment wrapper rejects caller-picked laws and "
            "duck-typed environments"
        )
    return public.seal_opaque_environment_commitment_v1(
        family=generated_environment.family,
        secret_salt=secret_salt,
        secret_laws=generated_environment.secret_laws_for_commitment(),
    )


__all__ = [
    "CANDIDATE_COUNT",
    "MINIMUM_SECRET_GENERATION_SEED_BYTES",
    "PROFILE_KEY",
    "RANK_SUPPORT",
    "V075PrivateEnvironmentGenerationInvariantViolation",
    "V075PrivateEnvironmentGenerationProfileV1",
    "V075PrivateGeneratedEnvironmentV1",
    "V075PrivateGeneratedSpawnLawV1",
    "freeze_v075_private_environment_generation_profile_v1",
    "generate_v075_private_environment_v1",
    "seal_v075_generated_private_environment_commitment_v1",
]
