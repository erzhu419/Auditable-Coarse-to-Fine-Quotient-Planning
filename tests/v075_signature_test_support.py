"""Test-only RSA signing support.

Unit-test key pairs are derived in memory from fixed, explicitly nonproduction
labels.  No private key material is checked into the repository.  Production
modules contain verification code only; production keys are supplied by a
frozen preregistration and its private signers remain outside the repository.
"""

from __future__ import annotations

import hashlib
import math

from acfqp import v075_public_campaign_authority_v1 as authority


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
                hashlib.sha256(
                    label + index.to_bytes(4, "big")
                ).digest(),
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


def _derive_test_prime(label: bytes) -> int:
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
    raise RuntimeError("deterministic unit-test RSA prime search exhausted")


def _derive_test_key_pair(
    first_label: bytes,
    second_label: bytes,
) -> tuple[int, int]:
    first = _derive_test_prime(first_label)
    second = _derive_test_prime(second_label)
    if first == second:
        raise RuntimeError("unit-test RSA primes unexpectedly coincide")
    totient = (first - 1) * (second - 1)
    if math.gcd(_PUBLIC_EXPONENT, totient) != 1:
        raise RuntimeError("unit-test RSA exponent is not invertible")
    modulus = first * second
    if modulus.bit_length() < 2_048:
        raise RuntimeError("unit-test RSA modulus is undersized")
    return modulus, pow(_PUBLIC_EXPONENT, -1, totient)


RSA_MODULUS, _RSA_SIGNING_EXPONENT = _derive_test_key_pair(
    b"acfqp-unit-rsa-62",
    b"acfqp-unit-rsa-68",
)
OBSERVER_RSA_MODULUS, _OBSERVER_RSA_SIGNING_EXPONENT = (
    _derive_test_key_pair(
        b"acfqp-unit-rsa-95",
        b"acfqp-unit-rsa-97",
    )
)

_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


def make_public_key(
    key_role: str,
) -> authority.V075RSAPublicVerificationKeyV1:
    return authority.V075RSAPublicVerificationKeyV1(
        key_role,
        (
            RSA_MODULUS
            if key_role == "CAMPAIGN_AUTHORITY"
            else OBSERVER_RSA_MODULUS
        ),
    )


def sign_test_message(
    message: bytes,
    *,
    key_role: str = "CAMPAIGN_AUTHORITY",
) -> str:
    modulus, signing_exponent = (
        (RSA_MODULUS, _RSA_SIGNING_EXPONENT)
        if key_role == "CAMPAIGN_AUTHORITY"
        else (
            OBSERVER_RSA_MODULUS,
            _OBSERVER_RSA_SIGNING_EXPONENT,
        )
    )
    width = (modulus.bit_length() + 7) // 8
    digest_info = _DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
    padding_size = width - len(digest_info) - 3
    encoded = (
        b"\x00\x01"
        + b"\xff" * padding_size
        + b"\x00"
        + digest_info
    )
    signature = pow(
        int.from_bytes(encoded, "big"),
        signing_exponent,
        modulus,
    )
    return signature.to_bytes(width, "big").hex()
