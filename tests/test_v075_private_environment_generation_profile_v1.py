from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp import v075_fresh_campaign_authority_v1 as construction
from acfqp import v075_private_environment_generation_profile_v1 as generation
from acfqp import v075_public_campaign_authority_v1 as public


def _seed(label: str) -> bytes:
    return hashlib.sha512(
        b"acfqp:v075-private-generation-test-seed:v1\x00"
        + label.encode("utf-8")
    ).digest()


def _salt(label: str) -> bytes:
    return hashlib.sha512(
        b"acfqp:v075-private-generation-test-salt:v1\x00"
        + label.encode("utf-8")
    ).digest()


def _profile() -> generation.V075PrivateEnvironmentGenerationProfileV1:
    return generation.freeze_v075_private_environment_generation_profile_v1()


def _environment(
    label: str = "one",
) -> generation.V075PrivateGeneratedEnvironmentV1:
    return generation.generate_v075_private_environment_v1(
        profile=_profile(),
        secret_generation_seed=_seed(label),
    )


def _exposed_construction_laws():
    return tuple(
        law.rank_probabilities
        for law in construction.freeze_v075_environment_manifest_v1().laws
    )


def test_public_profile_freezes_only_grid_and_selection_protocol() -> None:
    profile = _profile()
    repeated = _profile()
    document = profile.to_document()
    assert profile == repeated
    assert profile.profile_id == repeated.profile_id
    assert document["rank_support"] == [1, 2, 3]
    assert document["candidate_count"] == generation.CANDIDATE_COUNT == 30
    assert document["context_ordinals"] == [0, 1, 2]
    assert document["context_ids_in_generation_order"] == [
        context.context_id
        for context in public.freeze_v075_public_family_generation_v1()
        .replicate_contexts
    ]
    assert document["caller_selected_law_allowed"] is False
    assert document["exposed_construction_law_allowed"] is False
    assert document["selected_law_serialized"] is False
    assert document["secret_generation_seed_serialized"] is False
    assert document["secret_generation_seed_digest_serialized"] is False
    assert document["secret_salt_serialized"] is False
    assert document["production_environment_id_serialized"] is False
    assert document["observer_opened"] is False
    assert document["target_observations_generated"] == 0
    assert document["target_execution_allowed"] is False
    assert "rank_probabilities" not in document
    assert "laws" not in document


def test_candidate_grid_is_exact_positive_high_rank1_and_excludes_exposed_laws() -> None:
    candidates = _profile().candidate_laws
    exposed = set(_exposed_construction_laws())
    assert len(candidates) == len(set(candidates)) == 30
    assert set(candidates).isdisjoint(exposed)
    for law in candidates:
        assert tuple(rank for rank, _probability in law) == (1, 2, 3)
        assert all(
            type(probability) is Fraction and probability > 0
            for _rank, probability in law
        )
        assert sum(
            (probability for _rank, probability in law),
            Fraction(0),
        ) == 1
        assert Fraction(97, 100) < dict(law)[1] < Fraction(1)
        assert (
            dict(law)[2].numerator
            * (
                generation.PROBABILITY_DENOMINATOR
                // dict(law)[2].denominator
            )
        ) % 20 == 1


def test_secret_seed_generation_is_deterministic_and_not_retained() -> None:
    seed = _seed("deterministic")
    first = generation.generate_v075_private_environment_v1(
        profile=_profile(),
        secret_generation_seed=seed,
    )
    repeated = generation.generate_v075_private_environment_v1(
        profile=_profile(),
        secret_generation_seed=seed,
    )
    changed = _environment("changed")
    assert first == repeated
    assert first.secret_laws_for_commitment() == (
        repeated.secret_laws_for_commitment()
    )
    assert first != changed
    assert not hasattr(first, "secret_generation_seed")
    assert not hasattr(first, "generation_seed_digest")
    assert seed.hex() not in repr(first)
    assert seed.hex() not in repr(_profile().to_document())
    assert "redacted" in repr(first)
    assert all("redacted" in repr(law) for law in first.laws)
    assert not hasattr(first, "to_document")
    assert all(not hasattr(law, "to_document") for law in first.laws)
    with pytest.raises(TypeError):
        pickle.dumps(first)
    with pytest.raises(TypeError):
        pickle.dumps(first.laws[0])


def test_context_selection_is_order_bound_domain_separated_and_distinct() -> None:
    environment = _environment("context-separation")
    family = public.freeze_v075_public_family_generation_v1()
    assert tuple(law.context for law in environment.laws) == (
        family.replicate_contexts
    )
    assert tuple(law.replicate_ordinal for law in environment.laws) == (
        0,
        1,
        2,
    )
    assert len(
        {law.rank_probabilities for law in environment.laws}
    ) == 3
    assert all(
        law.rank_probabilities in _profile().candidate_laws
        for law in environment.laws
    )


def test_private_selection_rejects_reordered_or_duplicate_candidate_sets() -> None:
    profile = _profile()
    context = profile.family.replicate_contexts[0]
    for malformed in ((1, 0, 2), (0, 1, 1)):
        with pytest.raises(
            generation.V075PrivateEnvironmentGenerationInvariantViolation,
            match="context/order",
        ):
            generation._uniform_remaining_offset(  # type: ignore[attr-defined]
                secret_seed=_seed("malformed-candidate-set"),
                profile=profile,
                context=context,
                selection_round=0,
                remaining_candidate_indices=malformed,
            )


def test_generated_environment_feeds_only_opaque_public_commitment() -> None:
    environment = _environment("commitment")
    salt = _salt("commitment")
    wrapped = (
        generation.seal_v075_generated_private_environment_commitment_v1(
            generated_environment=environment,
            secret_salt=salt,
        )
    )
    direct = public.seal_opaque_environment_commitment_v1(
        family=environment.family,
        secret_salt=salt,
        secret_laws=environment.secret_laws_for_commitment(),
    )
    changed_salt = (
        generation.seal_v075_generated_private_environment_commitment_v1(
            generated_environment=environment,
            secret_salt=_salt("changed"),
        )
    )
    assert wrapped == direct
    assert wrapped.commitment_id == direct.commitment_id
    assert wrapped.commitment_digest != changed_salt.commitment_digest
    document = wrapped.to_document()
    assert document["secret_salt_serialized"] is False
    assert document["secret_environment_serialized"] is False
    assert document["production_law_serialized"] is False
    assert salt.hex() not in repr(document)
    assert "rank_probabilities" not in repr(document)


@pytest.mark.parametrize(
    "seed",
    (
        b"short",
        b"\x00" * 32,
        bytearray(range(32)),
        "not-bytes",
    ),
)
def test_short_low_diversity_and_duck_typed_seeds_are_rejected(
    seed,
) -> None:
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.generate_v075_private_environment_v1(
            profile=_profile(),
            secret_generation_seed=seed,
        )


def test_duck_typed_profile_and_environment_are_rejected() -> None:
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.generate_v075_private_environment_v1(
            profile=SimpleNamespace(
                profile_id=_profile().profile_id,
                family=_profile().family,
            ),
            secret_generation_seed=_seed("duck-profile"),
        )
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.seal_v075_generated_private_environment_commitment_v1(
            generated_environment=SimpleNamespace(
                family=_profile().family,
                secret_laws_for_commitment=lambda: (),
            ),
            secret_salt=_salt("duck-environment"),
        )


def test_caller_cannot_supply_or_transplant_laws() -> None:
    environment = _environment("caller-law")
    exposed = _exposed_construction_laws()[0]
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.V075PrivateGeneratedSpawnLawV1(
            generation._PRIVATE_GENERATOR_ISSUER,
            _profile(),
            _profile().family.replicate_contexts[0],
            exposed,
        )
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.V075PrivateGeneratedSpawnLawV1(
            object(),
            _profile(),
            _profile().family.replicate_contexts[0],
            _profile().candidate_laws[0],
        )
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        generation.seal_v075_generated_private_environment_commitment_v1(
            generated_environment=environment.secret_laws_for_commitment(),
            secret_salt=_salt("caller-picked"),
        )
    with pytest.raises(
        generation.V075PrivateEnvironmentGenerationInvariantViolation
    ):
        replace(environment, laws=tuple(reversed(environment.laws)))


def test_public_generation_apis_have_no_caller_law_parameter() -> None:
    parameters = inspect.signature(
        generation.generate_v075_private_environment_v1
    ).parameters
    assert tuple(parameters) == ("profile", "secret_generation_seed")
    seal_parameters = inspect.signature(
        generation.seal_v075_generated_private_environment_commitment_v1
    ).parameters
    assert tuple(seal_parameters) == ("generated_environment", "secret_salt")
    assert "secret_laws" not in parameters
    assert "rank_probabilities" not in parameters
    assert "secret_laws" not in seal_parameters


def test_module_contains_no_selected_private_environment_constant() -> None:
    forbidden_suffixes = (
        "PRODUCTION_LAW_ID",
        "PRODUCTION_ENVIRONMENT_ID",
        "GENERATION_SEED",
        "SECRET_SALT",
    )
    assert not any(
        name.endswith(forbidden_suffixes)
        and not name.startswith("MINIMUM_")
        for name in vars(generation)
    )
    assert not any(
        isinstance(value, generation.V075PrivateGeneratedEnvironmentV1)
        for value in vars(generation).values()
    )
