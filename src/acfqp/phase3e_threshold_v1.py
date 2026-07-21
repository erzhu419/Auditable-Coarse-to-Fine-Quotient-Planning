"""Neutral canonical threshold identity shared by model-only and local paths."""

from __future__ import annotations

from fractions import Fraction
import hashlib

from acfqp.phase3e_ids import canonical_json, parse_content_id


PORTABLE_THRESHOLD_PROFILE_DOMAIN = "acfqp:portable-threshold-profile:v1"


def portable_threshold_profile_id_v1(
    query_id: str,
    regret_tolerance: Fraction | int,
    risk_tolerance: Fraction | int,
) -> str:
    """Return the sole V1 identity for one query's regret/risk thresholds."""

    parse_content_id(query_id)
    regret = Fraction(regret_tolerance)
    risk = Fraction(risk_tolerance)
    if regret < 0 or not 0 <= risk <= 1:
        raise ValueError("threshold tolerances are outside the V1 domain")
    payload = {
        "schema": "acfqp.portable_threshold_profile.v1",
        "query_id": query_id,
        "delta": {
            "numerator": risk.numerator,
            "denominator": risk.denominator,
        },
        "regret_tolerance": {
            "numerator": regret.numerator,
            "denominator": regret.denominator,
        },
    }
    return hashlib.sha256(
        PORTABLE_THRESHOLD_PROFILE_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json(payload).encode("utf-8")
    ).hexdigest()


__all__ = [
    "PORTABLE_THRESHOLD_PROFILE_DOMAIN",
    "portable_threshold_profile_id_v1",
]
