"""Deterministic non-fresh K7 causal-promotion construction occurrence.

This module replaces the historical test-module fixture at the execution
boundary.  It builds the same registered NO_PRIOR K7 occurrence using
deterministically derived, explicitly nonproduction RSA keys, then executes
the owner-accounted twelve-stage causal-promotion path through
``ATTEMPT_BUDGET_EXHAUSTED``.

The fixture is construction-only.  It is not a fresh campaign, production
signer, certificate, or official-execution authority.  Keeping it in ``src``
allows a sealed runtime closure to execute and hash the exact fixture source
without importing pytest or any repository test module.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_batched_causal_accounted_occurrence_v1 as occurrence
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from acfqp import v075_reveal_verifying_attestation_authority_v2 as reveal
from acfqp.phase3e_ids import canonical_json_bytes


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_causal_promotion_construction_fixture_v1"
CONSTRUCTION_ONLY = True
FRESH_HELDOUT_ACCESSED = False
OFFICIAL_EXECUTION_ALLOWED = False

_PUBLIC_EXPONENT = 65_537
_SMALL_PRIMES = (
    3,
    5,
    7,
    11,
    13,
    17,
    19,
    23,
    29,
    31,
    37,
    41,
    43,
    47,
    53,
    59,
    61,
    67,
    71,
    73,
    79,
    83,
    89,
    97,
)
_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


class V075K7CausalPromotionConstructionFixtureV1Error(RuntimeError):
    """The deterministic construction fixture or its identity replay failed."""


def _fail(message: str) -> None:
    raise V075K7CausalPromotionConstructionFixtureV1Error(message)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-causal-promotion-construction-fixture:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _oid(label: str) -> str:
    return hashlib.sha1(
        b"acfqp:v075-k7-causal-promotion-construction-fixture-git:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _probable_prime(candidate: int, label: bytes) -> bool:
    if any(candidate % prime == 0 for prime in _SMALL_PRIMES):
        return False
    odd_part = candidate - 1
    power_of_two = 0
    while odd_part % 2 == 0:
        power_of_two += 1
        odd_part //= 2
    for index in range(32):
        base = 2 + (
            int.from_bytes(
                hashlib.sha256(label + index.to_bytes(4, "big")).digest(),
                "big",
            )
            % (candidate - 3)
        )
        witness = pow(base, odd_part, candidate)
        if witness in (1, candidate - 1):
            continue
        for _ in range(power_of_two - 1):
            witness = pow(witness, 2, candidate)
            if witness == candidate - 1:
                break
        else:
            return False
    return True


def _derive_prime(label: bytes) -> int:
    for counter in range(10_000):
        counter_bytes = counter.to_bytes(8, "big")
        raw = b"".join(
            hashlib.sha512(
                label + counter_bytes + block.to_bytes(4, "big")
            ).digest()
            for block in range(2)
        )
        candidate = int.from_bytes(raw, "big") | (3 << 1022) | 1
        if _probable_prime(candidate, label + counter_bytes):
            return candidate
    _fail("deterministic construction RSA prime search exhausted")


def _derive_key(
    first_label: bytes,
    second_label: bytes,
) -> tuple[int, int, int, int, int]:
    first = _derive_prime(first_label)
    second = _derive_prime(second_label)
    if first == second:
        _fail("construction RSA primes unexpectedly coincide")
    totient = (first - 1) * (second - 1)
    if math.gcd(_PUBLIC_EXPONENT, totient) != 1:
        _fail("construction RSA exponent is not invertible")
    modulus = first * second
    if modulus.bit_length() < 2_048:
        _fail("construction RSA modulus is undersized")
    signing_exponent = pow(_PUBLIC_EXPONENT, -1, totient)
    return (
        modulus,
        first,
        second,
        signing_exponent % (first - 1),
        signing_exponent % (second - 1),
    )


class _ConstructionSigner:
    def __init__(
        self,
        *,
        key_role: str,
        key: tuple[int, int, int, int, int],
    ) -> None:
        self.key_role = key_role
        self._key = key
        self.messages: list[bytes] = []

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        return public.V075RSAPublicVerificationKeyV1(
            self.key_role,
            self._key[0],
        )

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        if type(message) is not bytes or not message:
            _fail("construction signer received an empty or non-byte message")
        self.messages.append(message)
        modulus, first, second, first_exponent, second_exponent = self._key
        width = (modulus.bit_length() + 7) // 8
        digest_info = _DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
        padding_size = width - len(digest_info) - 3
        if padding_size < 8:
            _fail("construction signature padding is undersized")
        encoded = (
            b"\x00\x01"
            + b"\xff" * padding_size
            + b"\x00"
            + digest_info
        )
        encoded_integer = int.from_bytes(encoded, "big")
        first_residue = pow(encoded_integer, first_exponent, first)
        second_residue = pow(encoded_integer, second_exponent, second)
        q_inverse = pow(second, -1, first)
        signature = second_residue + second * (
            (first_residue - second_residue) * q_inverse % first
        )
        return signature.to_bytes(width, "big").hex()


def _fixture(
    marker: str,
) -> tuple[
    Any,
    bytes,
    namespace_v2.V075PublicTargetTapeNamespaceV2,
    preopen.V075ObserverOpenAuthorizationV2,
    _ConstructionSigner,
]:
    if type(marker) is not str or not marker or len(marker.encode("utf-8")) > 128:
        _fail("construction fixture marker is invalid")
    generated = private_env.generate_v075_private_environment_v1(
        profile=private_env.freeze_v075_private_environment_generation_profile_v1(),
        secret_generation_seed=hashlib.sha256(
            ("generated-" + marker).encode("utf-8")
        ).digest(),
    )
    salt = hashlib.sha512(("salt-" + marker).encode("utf-8")).digest()
    commitment = private_env.seal_v075_generated_private_environment_commitment_v1(
        generated_environment=generated,
        secret_salt=salt,
    )
    campaign_key = _derive_key(
        b"acfqp-construction-campaign-rsa-62",
        b"acfqp-construction-campaign-rsa-68",
    )
    observer_key = _derive_key(
        b"acfqp-construction-observer-rsa-95",
        b"acfqp-construction-observer-rsa-97",
    )
    signer = _ConstructionSigner(
        key_role="OBSERVER_EVIDENCE",
        key=observer_key,
    )
    registry = public.V075TrustedSignerRegistryV1(
        public.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY",
            campaign_key[0],
        ),
        signer.public_verification_key_v1(),
    )
    workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    runner_profile = campaign_profile.freeze_v075_production_campaign_profile_v2()
    anchor = remote.V075RemoteMainAnchorAttestationV2(
        remote._ANCHOR_ISSUER,  # noqa: SLF001
        _oid(marker + "-commit"),
        _oid(marker + "-tree"),
        (_oid(marker + "-parent"),),
        _oid(marker + "-manifest-blob"),
        _oid(marker + "-final-blob"),
        _id(marker + "-manifest"),
        _id(marker + "-final"),
        _id(marker + "-component-registry"),
        _id(marker + "-semantic-registry-binding"),
        _id(marker + "-semantic-artifact-replay"),
        workload.workload_id,
        runner_profile.profile_id,
        commitment.family.generation_id,
        commitment.commitment_id,
        registry,
    )
    namespace = namespace_v2.V075PublicTargetTapeNamespaceV2(
        namespace_v2._NAMESPACE_ISSUER,  # noqa: SLF001
        anchor,
        workload,
        commitment.family,
        runner_profile,
        commitment,
        registry,
    )
    attestation = reveal.issue_v075_reveal_verified_private_attestation_v2(
        anchor=anchor,
        commitment=commitment,
        generated_environment=generated,
        secret_salt=salt,
        signer_registry=registry,
        observer_signer=signer,
    )
    tracked = preopen.V075TrackedPreopenBlobClosureV2(
        preopen._BLOB_CLOSURE_ISSUER,  # noqa: SLF001
        anchor,
        _id(marker + "-manifest-bytes"),
        _id(marker + "-final-bytes"),
    )
    authorization = preopen.V075ObserverOpenAuthorizationV2(
        preopen._AUTHORIZATION_ISSUER,  # noqa: SLF001
        anchor,
        tracked,
        registry,
        commitment,
        attestation,
    )
    return generated, salt, namespace, authorization, signer


def run_v075_k7_causal_promotion_construction_fixture_v1(
    *,
    repository_root: str | Path,
    marker: str = "nonfresh-k7-causal-promotion",
) -> occurrence.V075LiveBatchedCausalAccountedOccurrenceV1:
    """Execute one exact construction-only NO_PRIOR causal-promotion run."""

    root = Path(repository_root).resolve(strict=True)
    generated, salt, namespace, authorization, signer = _fixture(marker)
    arm = worker.V075WorkerArmV1.NO_PRIOR
    context = namespace.family.replicate_contexts[0]
    occurrence_identity = (
        backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=acquisition.ARM_ORDER.index(arm),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    schedule = acquisition.freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=root,
        namespace=namespace,
        occurrence=occurrence_identity,
    )
    slot = schedule.profile.occurrence_slot_for(
        context_id=context.context_id,
        arm=arm,
    )
    replayed, schedule_verification = (
        acquisition.verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
            repository_root=root,
            namespace=namespace,
            expected_slot=slot,
            occurrence_identity_bytes=canonical_json_bytes(
                occurrence_identity.to_document()
            ),
            raw=schedule.canonical_bytes,
        )
    )
    if replayed.schedule_id != schedule.schedule_id:
        _fail("construction schedule replay changed its identity")
    result = occurrence.run_v075_live_batched_causal_accounted_occurrence_v1(
        namespace=namespace,
        schedule=schedule,
        schedule_verification=schedule_verification,
        authority=authorization,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id(marker + "-session"),
    )
    document = result.to_document()
    if (
        document["terminal_target_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
        or document["observer_closed_and_exactly_reconciled"] is not True
        or document["stage_instance_count"] != 12
        or document["stage_local_counter_record_count"] != 2_424
        or document["official_execution_allowed"] is not False
    ):
        _fail("construction occurrence terminal or stage facts changed")
    return result


__all__ = (
    "CONSTRUCTION_ONLY",
    "FRESH_HELDOUT_ACCESSED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "V075K7CausalPromotionConstructionFixtureV1Error",
    "run_v075_k7_causal_promotion_construction_fixture_v1",
)
