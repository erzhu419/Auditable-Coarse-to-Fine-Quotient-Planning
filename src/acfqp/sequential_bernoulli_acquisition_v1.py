"""Bounded target-local sequential Bernoulli row acquisition for V0-067.

The confidence sequence is obtained by inverting the uniform-beta
beta-binomial likelihood-mixture e-process.  For a Bernoulli sequence with
``s`` successes after ``n`` draws, the mixture likelihood of the *observed
sequence* is

    m_n(s) = B(s + 1, n - s + 1)
           = 1 / ((n + 1) * binom(n, s)).

For every fixed candidate probability ``p``,

    E_n(p) = m_n(s) / (p**s * (1-p)**(n-s))

is a nonnegative likelihood-ratio martingale under Bernoulli(p).  Ville's
inequality therefore makes

    C_n = {p: E_n(p) < 1 / alpha}

a time-uniform confidence sequence.  A single ``alpha`` covers every
checkpoint and every data-dependent stopping time; this is not repeated use
of a fixed-time interval.

The likelihood-mixture boundary follows the observed Bernoulli likelihood,
so its width adapts to the observed variance.  The fixed uniform-beta
reference measure is a mathematical e-process mixture, not a learned,
source, or meta prior.  Only target-local row draws enter the interval.

Interval endpoints lie on a preregistered dyadic grid.  Floating-point logs
are used only to locate likely boundary cells.  Every returned outer endpoint
and both adjacent grid relations are checked with exact integer arithmetic;
the log approximation can affect runtime but cannot make the interval
anti-conservative.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import lru_cache
import hashlib
import math
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "target_local_sequential_bernoulli_row_v0"
METHOD_ID = "uniform_beta_binomial_likelihood_mixture_ville_cs_v1"
STATISTICAL_CLAIM_SCOPE = (
    "CONDITIONAL_ON_TARGET_LOCAL_BERNOULLI_IID_SIMULATOR_ASSUMPTION"
)
INTERVAL_EVIDENCE_SCOPE = "TARGET_ROW_DRAWS_ONLY"

DOMAIN_TAGS = {
    "binding": "acfqp:target-local-bernoulli-row-binding:v1",
    "profile": "acfqp:sequential-bernoulli-profile:v1",
    "result": "acfqp:sequential-bernoulli-acquisition:v1",
    "verification": "acfqp:sequential-bernoulli-verification:v1",
}


class SequentialBernoulliInvariantViolation(ValueError):
    """A profile, transcript, confidence sequence, or binding is invalid."""


class _GMPInteger(ctypes.Structure):
    _fields_ = (
        ("_mp_alloc", ctypes.c_int),
        ("_mp_size", ctypes.c_int),
        ("_mp_d", ctypes.c_void_p),
    )


def _load_gmp_exact_backend() -> Any | None:
    library_name = ctypes.util.find_library("gmp")
    if library_name is None:
        return None
    try:
        library = ctypes.CDLL(library_name)
    except OSError:
        return None
    pointer = ctypes.POINTER(_GMPInteger)
    signatures = {
        "__gmpz_init": ([pointer], None),
        "__gmpz_clear": ([pointer], None),
        "__gmpz_ui_pow_ui": (
            [pointer, ctypes.c_ulong, ctypes.c_ulong],
            None,
        ),
        "__gmpz_mul": ([pointer, pointer, pointer], None),
        "__gmpz_set_str": (
            [pointer, ctypes.c_char_p, ctypes.c_int],
            ctypes.c_int,
        ),
        "__gmpz_set_ui": ([pointer, ctypes.c_ulong], None),
        "__gmpz_mul_2exp": (
            [pointer, pointer, ctypes.c_ulong],
            None,
        ),
        "__gmpz_cmp": ([pointer, pointer], ctypes.c_int),
    }
    try:
        for name, (arguments, result) in signatures.items():
            function = getattr(library, name)
            function.argtypes = arguments
            function.restype = result
    except AttributeError:
        return None
    return library


_GMP_EXACT_BACKEND = _load_gmp_exact_backend()


def _gmp_exact_likelihood_rejects(
    *,
    grid_index: int,
    success_count: int,
    draw_count: int,
    denominator: int,
    left_coefficient_hex: bytes,
    confidence_alpha_numerator: int,
) -> bool | None:
    """Evaluate the same integer inequality with GMP, or request fallback."""

    library = _GMP_EXACT_BACKEND
    if (
        library is None
        or denominator <= 0
        or denominator & (denominator - 1)
        or any(
            item < 0
            for item in (
                grid_index,
                success_count,
                draw_count,
                confidence_alpha_numerator,
            )
        )
    ):
        return None
    values = [_GMPInteger() for _ in range(4)]
    for value in values:
        library.__gmpz_init(ctypes.byref(value))
    try:
        library.__gmpz_ui_pow_ui(
            ctypes.byref(values[0]),
            grid_index,
            success_count,
        )
        library.__gmpz_ui_pow_ui(
            ctypes.byref(values[1]),
            denominator - grid_index,
            draw_count - success_count,
        )
        library.__gmpz_mul(
            ctypes.byref(values[0]),
            ctypes.byref(values[0]),
            ctypes.byref(values[1]),
        )
        if (
            library.__gmpz_set_str(
                ctypes.byref(values[2]),
                left_coefficient_hex,
                16,
            )
            != 0
        ):
            return None
        library.__gmpz_mul(
            ctypes.byref(values[0]),
            ctypes.byref(values[0]),
            ctypes.byref(values[2]),
        )
        library.__gmpz_set_ui(
            ctypes.byref(values[3]),
            confidence_alpha_numerator,
        )
        library.__gmpz_mul_2exp(
            ctypes.byref(values[3]),
            ctypes.byref(values[3]),
            (denominator.bit_length() - 1) * draw_count,
        )
        return (
            library.__gmpz_cmp(
                ctypes.byref(values[0]),
                ctypes.byref(values[3]),
            )
            <= 0
        )
    finally:
        for value in values:
            library.__gmpz_clear(ctypes.byref(value))


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw_suffix: bytes = b"",
) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise SequentialBernoulliInvariantViolation(str(error)) from error
    body = tag + b"\x00" + encoded
    if raw_suffix:
        body += b"\x00" + raw_suffix
    return hashlib.sha256(body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SequentialBernoulliInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _strict_fraction(
    value: Any,
    field: str,
    *,
    lower: Fraction,
    upper: Fraction,
) -> Fraction:
    if (
        type(value) is not Fraction
        or not lower < value < upper
    ):
        raise SequentialBernoulliInvariantViolation(
            f"{field} must be an exact Fraction in ({lower}, {upper})"
        )
    return value


@dataclass(frozen=True, slots=True)
class TargetLocalBernoulliRowBindingV1:
    """Identity chain for one target-local Bernoulli proof obligation."""

    structural_id: str
    target_context_id: str
    target_row_id: str
    draw_source_id: str
    outcome_semantics_id: str
    row_key: str
    source_observation_rows_used: int = 0
    offline_draws_used_for_interval: int = 0
    cross_target_rows_used: int = 0
    target_local_interval: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.structural_id, "structural"),
            (self.target_context_id, "target context"),
            (self.target_row_id, "target row"),
            (self.draw_source_id, "draw source"),
            (self.outcome_semantics_id, "outcome semantics"),
        ):
            _cid(value, field)
        if (
            type(self.row_key) is not str
            or not self.row_key
            or len(self.row_key) > 512
            or self.source_observation_rows_used != 0
            or self.offline_draws_used_for_interval != 0
            or self.cross_target_rows_used != 0
            or self.target_local_interval is not True
        ):
            raise SequentialBernoulliInvariantViolation(
                "Bernoulli row binding is not target-local"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_local_bernoulli_row_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "target_context_id": self.target_context_id,
            "target_row_id": self.target_row_id,
            "draw_source_id": self.draw_source_id,
            "outcome_semantics_id": self.outcome_semantics_id,
            "row_key": self.row_key,
            "source_observation_rows_used": 0,
            "offline_draws_used_for_interval": 0,
            "cross_target_rows_used": 0,
            "target_local_interval": True,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class SequentialBernoulliProfileV1:
    """Preregistered stopping, confidence, resolution, and hard-cap profile."""

    confidence_alpha: Fraction
    target_half_width: Fraction
    checkpoints: tuple[int, ...]
    boundary_grid_bits: int
    method_id: str = METHOD_ID
    confidence_accounting: str = (
        "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
    )
    reference_mixture: str = (
        "FIXED_UNIFORM_BETA_REFERENCE_NOT_SOURCE_OR_META_PRIOR"
    )
    interval_evidence_scope: str = INTERVAL_EVIDENCE_SCOPE
    cap_fail_closed: bool = True

    def __post_init__(self) -> None:
        _strict_fraction(
            self.confidence_alpha,
            "confidence alpha",
            lower=Fraction(0),
            upper=Fraction(1),
        )
        _strict_fraction(
            self.target_half_width,
            "target half width",
            lower=Fraction(0),
            upper=Fraction(1, 2),
        )
        if (
            type(self.checkpoints) is not tuple
            or not self.checkpoints
            or any(
                type(item) is not int or item <= 0
                for item in self.checkpoints
            )
            or self.checkpoints
            != tuple(sorted(set(self.checkpoints)))
            or type(self.boundary_grid_bits) is not int
            or not 8 <= self.boundary_grid_bits <= 48
            or Fraction(1, 1 << self.boundary_grid_bits)
            > self.target_half_width / 8
            or self.method_id != METHOD_ID
            or self.confidence_accounting
            != "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
            or self.reference_mixture
            != "FIXED_UNIFORM_BETA_REFERENCE_NOT_SOURCE_OR_META_PRIOR"
            or self.interval_evidence_scope != INTERVAL_EVIDENCE_SCOPE
            or self.cap_fail_closed is not True
        ):
            raise SequentialBernoulliInvariantViolation(
                "sequential Bernoulli profile is not preregistered or sound"
            )

    @property
    def min_draws(self) -> int:
        return self.checkpoints[0]

    @property
    def max_draws(self) -> int:
        return self.checkpoints[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_bernoulli_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "confidence_alpha": _fdoc(self.confidence_alpha),
            "target_half_width": _fdoc(self.target_half_width),
            "checkpoints": list(self.checkpoints),
            "min_draws": self.min_draws,
            "max_draws": self.max_draws,
            "boundary_grid_bits": self.boundary_grid_bits,
            "method_id": self.method_id,
            "confidence_accounting": self.confidence_accounting,
            "reference_mixture": self.reference_mixture,
            "interval_evidence_scope": self.interval_evidence_scope,
            "cap_fail_closed": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def v0067_default_sequential_profile_v1() -> SequentialBernoulliProfileV1:
    """Return the bounded profile matched to the V0-066 per-row radius/cap."""

    return SequentialBernoulliProfileV1(
        confidence_alpha=Fraction(1, 250_000),
        target_half_width=Fraction(1, 140),
        checkpoints=tuple(1 << power for power in range(8, 18)),
        boundary_grid_bits=24,
    )


@lru_cache(maxsize=32_768)
def beta_binomial_sequence_mass_v1(
    draw_count: int,
    success_count: int,
) -> Fraction:
    """Exact uniform-beta mixture likelihood of one Bernoulli sequence."""

    if (
        type(draw_count) is not int
        or draw_count <= 0
        or type(success_count) is not int
        or not 0 <= success_count <= draw_count
    ):
        raise SequentialBernoulliInvariantViolation(
            "beta-binomial sequence counts are invalid"
        )
    return Fraction(
        1,
        (draw_count + 1) * math.comb(draw_count, success_count),
    )


def bernoulli_likelihood_v1(
    draw_count: int,
    success_count: int,
    probability: Fraction,
) -> Fraction:
    """Return the exact likelihood of one ordered Bernoulli sequence."""

    if (
        type(probability) is not Fraction
        or not 0 <= probability <= 1
    ):
        raise SequentialBernoulliInvariantViolation(
            "candidate probability must be an exact Fraction in [0,1]"
        )
    beta_binomial_sequence_mass_v1(draw_count, success_count)
    return (
        probability ** success_count
        * (1 - probability) ** (draw_count - success_count)
    )


def bernoulli_mixture_rejects_v1(
    draw_count: int,
    success_count: int,
    probability: Fraction,
    confidence_alpha: Fraction,
) -> bool:
    """Exact e-process rejection predicate at one arbitrary stopping time."""

    _strict_fraction(
        confidence_alpha,
        "confidence alpha",
        lower=Fraction(0),
        upper=Fraction(1),
    )
    mixture_mass = beta_binomial_sequence_mass_v1(
        draw_count,
        success_count,
    )
    likelihood = bernoulli_likelihood_v1(
        draw_count,
        success_count,
        probability,
    )
    return likelihood <= confidence_alpha * mixture_mass


def _log_rejects(
    draw_count: int,
    success_count: int,
    grid_index: int,
    grid_denominator: int,
    log_threshold: float,
) -> bool:
    """Approximate search predicate; never used as final proof evidence."""

    if grid_index <= 0:
        log_likelihood = (
            0.0 if success_count == 0 else -math.inf
        )
    elif grid_index >= grid_denominator:
        log_likelihood = (
            0.0 if success_count == draw_count else -math.inf
        )
    else:
        probability = grid_index / grid_denominator
        log_likelihood = (
            success_count * math.log(probability)
            + (draw_count - success_count)
            * math.log1p(-probability)
        )
    return log_likelihood <= log_threshold


class _ExactGridRejectionV1:
    """Cached integer comparison for dyadic likelihood boundaries."""

    __slots__ = (
        "draw_count",
        "success_count",
        "denominator",
        "left_coefficient",
        "left_coefficient_hex",
        "confidence_alpha_numerator",
        "right_hand_side",
        "comparison_count",
    )

    def __init__(
        self,
        draw_count: int,
        success_count: int,
        confidence_alpha: Fraction,
        denominator: int,
    ) -> None:
        self.draw_count = draw_count
        self.success_count = success_count
        self.denominator = denominator
        self.left_coefficient = (
            confidence_alpha.denominator
            * (draw_count + 1)
            * math.comb(draw_count, success_count)
        )
        self.left_coefficient_hex = format(
            self.left_coefficient,
            "x",
        ).encode("ascii")
        self.confidence_alpha_numerator = confidence_alpha.numerator
        self.right_hand_side = (
            None
            if _GMP_EXACT_BACKEND is not None
            else confidence_alpha.numerator * denominator ** draw_count
        )
        self.comparison_count = 0

    def rejects(self, grid_index: int) -> bool:
        self.comparison_count += 1
        native_result = _gmp_exact_likelihood_rejects(
            grid_index=grid_index,
            success_count=self.success_count,
            draw_count=self.draw_count,
            denominator=self.denominator,
            left_coefficient_hex=self.left_coefficient_hex,
            confidence_alpha_numerator=(
                self.confidence_alpha_numerator
            ),
        )
        if native_result is not None:
            return native_result
        if self.right_hand_side is None:
            self.right_hand_side = (
                self.confidence_alpha_numerator
                * self.denominator ** self.draw_count
            )
        likelihood_numerator = (
            grid_index ** self.success_count
            * (self.denominator - grid_index)
            ** (self.draw_count - self.success_count)
        )
        return (
            likelihood_numerator * self.left_coefficient
            <= self.right_hand_side
        )


def _last_rejected_lower_grid_index(
    draw_count: int,
    success_count: int,
    denominator: int,
    log_threshold: float,
    exact: _ExactGridRejectionV1,
) -> tuple[int, int]:
    if success_count == 0:
        return 0, 0
    upper = (success_count * denominator) // draw_count
    if upper <= 0:
        return 0, 0
    log_evaluations = 0
    low = 0
    high = upper
    while high - low > 1:
        middle = (low + high) // 2
        log_evaluations += 1
        if _log_rejects(
            draw_count,
            success_count,
            middle,
            denominator,
            log_threshold,
        ):
            low = middle
        else:
            high = middle

    candidate = low
    while candidate > 0 and not exact.rejects(candidate):
        candidate -= 1
    while (
        candidate + 1 <= upper
        and exact.rejects(candidate + 1)
    ):
        candidate += 1
    if not exact.rejects(candidate):
        raise SequentialBernoulliInvariantViolation(
            "exact lower boundary correction failed"
        )
    if (
        candidate < upper
        and exact.rejects(candidate + 1)
    ):
        raise SequentialBernoulliInvariantViolation(
            "lower confidence boundary is not an outer bracket"
        )
    return candidate, log_evaluations


def _first_rejected_upper_grid_index(
    draw_count: int,
    success_count: int,
    denominator: int,
    log_threshold: float,
    exact: _ExactGridRejectionV1,
) -> tuple[int, int]:
    if success_count == draw_count:
        return denominator, 0
    lower = (
        success_count * denominator + draw_count - 1
    ) // draw_count
    if lower >= denominator:
        return denominator, 0
    log_evaluations = 0
    low = lower
    high = denominator
    while high - low > 1:
        middle = (low + high) // 2
        log_evaluations += 1
        if _log_rejects(
            draw_count,
            success_count,
            middle,
            denominator,
            log_threshold,
        ):
            high = middle
        else:
            low = middle

    candidate = high
    while (
        candidate < denominator
        and not exact.rejects(candidate)
    ):
        candidate += 1
    while (
        candidate - 1 >= lower
        and exact.rejects(candidate - 1)
    ):
        candidate -= 1
    if not exact.rejects(candidate):
        raise SequentialBernoulliInvariantViolation(
            "exact upper boundary correction failed"
        )
    if (
        candidate > lower
        and exact.rejects(candidate - 1)
    ):
        raise SequentialBernoulliInvariantViolation(
            "upper confidence boundary is not an outer bracket"
        )
    return candidate, log_evaluations


@lru_cache(maxsize=32_768)
def _outer_confidence_bounds(
    draw_count: int,
    success_count: int,
    confidence_alpha: Fraction,
    boundary_grid_bits: int,
) -> tuple[Fraction, Fraction, int, int]:
    mixture_mass = beta_binomial_sequence_mass_v1(
        draw_count,
        success_count,
    )
    threshold = confidence_alpha * mixture_mass
    log_threshold = (
        math.log(threshold.numerator)
        - math.log(threshold.denominator)
    )
    denominator = 1 << boundary_grid_bits
    exact = _ExactGridRejectionV1(
        draw_count,
        success_count,
        confidence_alpha,
        denominator,
    )
    lower_index, lower_log_evaluations = (
        _last_rejected_lower_grid_index(
            draw_count,
            success_count,
            denominator,
            log_threshold,
            exact,
        )
    )
    upper_index, upper_log_evaluations = (
        _first_rejected_upper_grid_index(
            draw_count,
            success_count,
            denominator,
            log_threshold,
            exact,
        )
    )
    lower = Fraction(lower_index, denominator)
    upper = Fraction(upper_index, denominator)
    if lower > upper:
        raise SequentialBernoulliInvariantViolation(
            "confidence sequence boundaries crossed"
        )
    return (
        lower,
        upper,
        exact.comparison_count,
        lower_log_evaluations + upper_log_evaluations,
    )


def clear_exact_bernoulli_math_cache_v1() -> None:
    """Clear pure exact-math memoization used only for execution speed.

    Both cached functions are deterministic functions of their complete
    arguments.  Clearing these caches therefore changes neither artifact
    bytes nor any statistical or numerical conclusion; it only supports
    fresh-computation regression lanes.
    """

    beta_binomial_sequence_mass_v1.cache_clear()
    _outer_confidence_bounds.cache_clear()


@dataclass(frozen=True, slots=True)
class AnytimeBernoulliCheckpointV1:
    draw_count: int
    success_count: int
    empirical_probability: Fraction
    mixture_sequence_mass: Fraction
    rejection_likelihood_threshold: Fraction
    lower_probability: Fraction
    upper_probability: Fraction
    interval_width: Fraction
    exact_likelihood_comparisons: int
    log_search_evaluations: int
    method_id: str = METHOD_ID

    def __post_init__(self) -> None:
        expected_mass = beta_binomial_sequence_mass_v1(
            self.draw_count,
            self.success_count,
        )
        values = (
            self.empirical_probability,
            self.mixture_sequence_mass,
            self.rejection_likelihood_threshold,
            self.lower_probability,
            self.upper_probability,
            self.interval_width,
        )
        if (
            any(type(item) is not Fraction for item in values)
            or self.empirical_probability
            != Fraction(self.success_count, self.draw_count)
            or self.mixture_sequence_mass != expected_mass
            or not 0
            <= self.lower_probability
            <= self.empirical_probability
            <= self.upper_probability
            <= 1
            or self.interval_width
            != self.upper_probability - self.lower_probability
            or type(self.exact_likelihood_comparisons) is not int
            or self.exact_likelihood_comparisons < 0
            or type(self.log_search_evaluations) is not int
            or self.log_search_evaluations < 0
            or self.method_id != METHOD_ID
        ):
            raise SequentialBernoulliInvariantViolation(
                "anytime Bernoulli checkpoint is inconsistent"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "draw_count": self.draw_count,
            "success_count": self.success_count,
            "empirical_probability": _fdoc(self.empirical_probability),
            "mixture_sequence_mass": _fdoc(self.mixture_sequence_mass),
            "rejection_likelihood_threshold": _fdoc(
                self.rejection_likelihood_threshold
            ),
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
            "interval_width": _fdoc(self.interval_width),
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "method_id": self.method_id,
        }


def build_anytime_bernoulli_checkpoint_v1(
    draw_count: int,
    success_count: int,
    profile: SequentialBernoulliProfileV1,
) -> AnytimeBernoulliCheckpointV1:
    """Build an exact-grid CS checkpoint from counts only.

    A multinomial row owner can retain one authoritative ordinal transcript
    and call this function with the count of each preregistered aggregate
    event.  The Bernoulli layer therefore does not require or authorize one
    duplicated boolean transcript per event.  This function only constructs
    a confidence-sequence checkpoint; the caller remains responsible for
    binding counts to the authoritative ordinal transcript and for applying
    its plan-level proof/stopping rule.
    """

    if type(profile) is not SequentialBernoulliProfileV1:
        raise SequentialBernoulliInvariantViolation(
            "count-only checkpoint requires an exact profile type"
        )
    mass = beta_binomial_sequence_mass_v1(draw_count, success_count)
    lower, upper, exact_comparisons, log_evaluations = (
        _outer_confidence_bounds(
            draw_count,
            success_count,
            profile.confidence_alpha,
            profile.boundary_grid_bits,
        )
    )
    return AnytimeBernoulliCheckpointV1(
        draw_count=draw_count,
        success_count=success_count,
        empirical_probability=Fraction(success_count, draw_count),
        mixture_sequence_mass=mass,
        rejection_likelihood_threshold=profile.confidence_alpha * mass,
        lower_probability=lower,
        upper_probability=upper,
        interval_width=upper - lower,
        exact_likelihood_comparisons=exact_comparisons,
        log_search_evaluations=log_evaluations,
    )


def _pack_draws(draws: Iterable[bool]) -> bytes:
    output = bytearray()
    byte = 0
    width = 0
    for draw in draws:
        if type(draw) is not bool:
            raise SequentialBernoulliInvariantViolation(
                "target transcript contains a non-boolean draw"
            )
        if draw:
            byte |= 1 << width
        width += 1
        if width == 8:
            output.append(byte)
            byte = 0
            width = 0
    if width:
        output.append(byte)
    return bytes(output)


def _unpack_draws(packed: bytes, draw_count: int) -> tuple[bool, ...]:
    if (
        type(packed) is not bytes
        or type(draw_count) is not int
        or draw_count < 0
        or len(packed) != math.ceil(draw_count / 8)
    ):
        raise SequentialBernoulliInvariantViolation(
            "packed Bernoulli transcript shape is invalid"
        )
    draws = tuple(
        bool((packed[index // 8] >> (index % 8)) & 1)
        for index in range(draw_count)
    )
    trailing = draw_count % 8
    if trailing and packed[-1] >> trailing:
        raise SequentialBernoulliInvariantViolation(
            "packed Bernoulli transcript has nonzero trailing bits"
        )
    return draws


class SequentialBernoulliOutcome(str, Enum):
    CERTIFIED_TARGET_LOCAL_INTERVAL = "CERTIFIED_TARGET_LOCAL_INTERVAL"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    SOURCE_EXHAUSTED = "SOURCE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class SequentialBernoulliCountersV1:
    target_draw_calls: int
    source_poll_calls: int
    checkpoint_evaluations: int
    exact_likelihood_comparisons: int
    log_search_evaluations: int
    cap_checks: int
    transcript_bits_recorded: int
    packed_transcript_bytes: int
    source_observation_rows_imported: int = 0
    offline_draws_used_for_interval: int = 0
    cross_target_rows_imported: int = 0

    def __post_init__(self) -> None:
        nonnegative = (
            self.target_draw_calls,
            self.source_poll_calls,
            self.checkpoint_evaluations,
            self.exact_likelihood_comparisons,
            self.log_search_evaluations,
            self.cap_checks,
            self.transcript_bits_recorded,
            self.packed_transcript_bytes,
        )
        if (
            any(type(item) is not int or item < 0 for item in nonnegative)
            or self.source_poll_calls < self.target_draw_calls
            or self.checkpoint_evaluations != self.cap_checks
            or self.transcript_bits_recorded != self.target_draw_calls
            or self.packed_transcript_bytes
            != math.ceil(self.target_draw_calls / 8)
            or self.source_observation_rows_imported != 0
            or self.offline_draws_used_for_interval != 0
            or self.cross_target_rows_imported != 0
        ):
            raise SequentialBernoulliInvariantViolation(
                "sequential Bernoulli counters do not reconcile"
            )

    def to_document(self) -> dict[str, int]:
        return {
            "target_draw_calls": self.target_draw_calls,
            "source_poll_calls": self.source_poll_calls,
            "checkpoint_evaluations": self.checkpoint_evaluations,
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "cap_checks": self.cap_checks,
            "transcript_bits_recorded": self.transcript_bits_recorded,
            "packed_transcript_bytes": self.packed_transcript_bytes,
            "source_observation_rows_imported": 0,
            "offline_draws_used_for_interval": 0,
            "cross_target_rows_imported": 0,
        }


def _expected_checkpoint_draw_counts(
    draw_count: int,
    profile: SequentialBernoulliProfileV1,
) -> tuple[int, ...]:
    scheduled = tuple(
        item for item in profile.checkpoints if item <= draw_count
    )
    if draw_count == 0 or (
        scheduled and scheduled[-1] == draw_count
    ):
        return scheduled
    return scheduled + (draw_count,)


@dataclass(frozen=True, slots=True)
class SequentialBernoulliAcquisitionV1:
    binding: TargetLocalBernoulliRowBindingV1
    profile: SequentialBernoulliProfileV1
    outcome: SequentialBernoulliOutcome
    draw_count: int
    success_count: int
    packed_draws: bytes
    checkpoints: tuple[AnytimeBernoulliCheckpointV1, ...]
    counters: SequentialBernoulliCountersV1
    target_draws_only: bool = True
    time_uniform_confidence_sequence: bool = True
    source_or_meta_prior_used_for_interval: bool = False
    unconditional_iid_claimed: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not TargetLocalBernoulliRowBindingV1
            or type(self.profile) is not SequentialBernoulliProfileV1
            or type(self.outcome) is not SequentialBernoulliOutcome
            or type(self.draw_count) is not int
            or not 0 <= self.draw_count <= self.profile.max_draws
            or type(self.success_count) is not int
            or not 0 <= self.success_count <= self.draw_count
            or type(self.packed_draws) is not bytes
            or type(self.checkpoints) is not tuple
            or any(
                type(item) is not AnytimeBernoulliCheckpointV1
                for item in self.checkpoints
            )
            or tuple(item.draw_count for item in self.checkpoints)
            != _expected_checkpoint_draw_counts(
                self.draw_count,
                self.profile,
            )
            or type(self.counters) is not SequentialBernoulliCountersV1
            or self.counters.target_draw_calls != self.draw_count
            or self.counters.checkpoint_evaluations
            != len(self.checkpoints)
            or self.counters.exact_likelihood_comparisons
            != sum(
                item.exact_likelihood_comparisons
                for item in self.checkpoints
            )
            or self.counters.log_search_evaluations
            != sum(
                item.log_search_evaluations
                for item in self.checkpoints
            )
            or self.target_draws_only is not True
            or self.time_uniform_confidence_sequence is not True
            or self.source_or_meta_prior_used_for_interval is not False
            or self.unconditional_iid_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
        ):
            raise SequentialBernoulliInvariantViolation(
                "sequential acquisition structure or claim scope changed"
            )
        draws = _unpack_draws(self.packed_draws, self.draw_count)
        if sum(draws) != self.success_count:
            raise SequentialBernoulliInvariantViolation(
                "transcript successes do not match result counts"
            )
        target_width = 2 * self.profile.target_half_width
        prior_checkpoints = self.checkpoints[:-1]
        if any(
            item.interval_width <= target_width
            for item in prior_checkpoints
            if item.draw_count in self.profile.checkpoints
        ):
            raise SequentialBernoulliInvariantViolation(
                "acquisition continued after its first certified checkpoint"
            )
        final = self.checkpoints[-1] if self.checkpoints else None
        if self.outcome is SequentialBernoulliOutcome.CERTIFIED_TARGET_LOCAL_INTERVAL:
            if (
                final is None
                or self.draw_count not in self.profile.checkpoints
                or final.interval_width > target_width
                or self.counters.source_poll_calls != self.draw_count
            ):
                raise SequentialBernoulliInvariantViolation(
                    "certified acquisition did not meet the stopping rule"
                )
        elif self.outcome is SequentialBernoulliOutcome.CAP_EXHAUSTED:
            if (
                final is None
                or self.draw_count != self.profile.max_draws
                or final.interval_width <= target_width
                or self.counters.source_poll_calls != self.draw_count
            ):
                raise SequentialBernoulliInvariantViolation(
                    "cap exhaustion is not fail-closed"
                )
        elif (
            self.draw_count >= self.profile.max_draws
            or self.counters.source_poll_calls != self.draw_count + 1
        ):
            raise SequentialBernoulliInvariantViolation(
                "source exhaustion chronology is invalid"
            )

    @property
    def certified(self) -> bool:
        return (
            self.outcome
            is SequentialBernoulliOutcome.CERTIFIED_TARGET_LOCAL_INTERVAL
        )

    @property
    def final_checkpoint(self) -> AnytimeBernoulliCheckpointV1 | None:
        return self.checkpoints[-1] if self.checkpoints else None

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_bernoulli_acquisition.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "binding_id": self.binding.binding_id,
            "profile_id": self.profile.profile_id,
            "outcome": self.outcome.value,
            "draw_count": self.draw_count,
            "success_count": self.success_count,
            "packed_draws_sha256": hashlib.sha256(
                self.packed_draws
            ).hexdigest(),
            "packed_draws_byte_count": len(self.packed_draws),
            "checkpoints": [
                item.to_document() for item in self.checkpoints
            ],
            "counters": self.counters.to_document(),
            "target_draws_only": True,
            "time_uniform_confidence_sequence": True,
            "source_or_meta_prior_used_for_interval": False,
            "unconditional_iid_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
        }

    @property
    def acquisition_id(self) -> str:
        return _content_id(
            "result",
            self._identity_payload(),
            self.packed_draws,
        )

    def to_document(
        self,
        *,
        include_packed_draws: bool = True,
    ) -> dict[str, Any]:
        document = {
            **self._identity_payload(),
            "acquisition_id": self.acquisition_id,
        }
        if include_packed_draws:
            document["packed_draws_hex"] = self.packed_draws.hex()
        return document


def _counters(
    draw_count: int,
    source_poll_calls: int,
    checkpoints: tuple[AnytimeBernoulliCheckpointV1, ...],
) -> SequentialBernoulliCountersV1:
    return SequentialBernoulliCountersV1(
        target_draw_calls=draw_count,
        source_poll_calls=source_poll_calls,
        checkpoint_evaluations=len(checkpoints),
        exact_likelihood_comparisons=sum(
            item.exact_likelihood_comparisons for item in checkpoints
        ),
        log_search_evaluations=sum(
            item.log_search_evaluations for item in checkpoints
        ),
        cap_checks=len(checkpoints),
        transcript_bits_recorded=draw_count,
        packed_transcript_bytes=math.ceil(draw_count / 8),
    )


def _result(
    binding: TargetLocalBernoulliRowBindingV1,
    profile: SequentialBernoulliProfileV1,
    outcome: SequentialBernoulliOutcome,
    draws: tuple[bool, ...],
    checkpoints: tuple[AnytimeBernoulliCheckpointV1, ...],
    source_poll_calls: int,
) -> SequentialBernoulliAcquisitionV1:
    packed = _pack_draws(draws)
    return SequentialBernoulliAcquisitionV1(
        binding=binding,
        profile=profile,
        outcome=outcome,
        draw_count=len(draws),
        success_count=sum(draws),
        packed_draws=packed,
        checkpoints=checkpoints,
        counters=_counters(
            len(draws),
            source_poll_calls,
            checkpoints,
        ),
    )


def acquire_sequential_bernoulli_row_v1(
    binding: TargetLocalBernoulliRowBindingV1,
    profile: SequentialBernoulliProfileV1,
    draws: Iterable[bool],
) -> SequentialBernoulliAcquisitionV1:
    """Acquire until the anytime width target, hard cap, or source exhaustion."""

    if (
        type(binding) is not TargetLocalBernoulliRowBindingV1
        or type(profile) is not SequentialBernoulliProfileV1
    ):
        raise SequentialBernoulliInvariantViolation(
            "acquisition requires exact binding and profile types"
        )
    try:
        iterator = iter(draws)
    except TypeError as error:
        raise SequentialBernoulliInvariantViolation(
            "target draw source is not iterable"
        ) from error

    observed: list[bool] = []
    checkpoints: list[AnytimeBernoulliCheckpointV1] = []
    success_count = 0
    source_poll_calls = 0
    target_width = 2 * profile.target_half_width

    for scheduled_draw_count in profile.checkpoints:
        while len(observed) < scheduled_draw_count:
            source_poll_calls += 1
            try:
                draw = next(iterator)
            except StopIteration:
                if observed and (
                    not checkpoints
                    or checkpoints[-1].draw_count != len(observed)
                ):
                    checkpoints.append(
                        build_anytime_bernoulli_checkpoint_v1(
                            len(observed),
                            success_count,
                            profile,
                        )
                    )
                return _result(
                    binding,
                    profile,
                    SequentialBernoulliOutcome.SOURCE_EXHAUSTED,
                    tuple(observed),
                    tuple(checkpoints),
                    source_poll_calls,
                )
            if type(draw) is not bool:
                raise SequentialBernoulliInvariantViolation(
                    "target draw source emitted a non-boolean value"
                )
            observed.append(draw)
            success_count += int(draw)

        current = build_anytime_bernoulli_checkpoint_v1(
            len(observed),
            success_count,
            profile,
        )
        checkpoints.append(current)
        if current.interval_width <= target_width:
            return _result(
                binding,
                profile,
                SequentialBernoulliOutcome.CERTIFIED_TARGET_LOCAL_INTERVAL,
                tuple(observed),
                tuple(checkpoints),
                source_poll_calls,
            )

    return _result(
        binding,
        profile,
        SequentialBernoulliOutcome.CAP_EXHAUSTED,
        tuple(observed),
        tuple(checkpoints),
        source_poll_calls,
    )


@dataclass(frozen=True, slots=True)
class SequentialBernoulliVerificationV1:
    acquisition_id: str
    binding_id: str
    profile_id: str
    outcome: SequentialBernoulliOutcome
    replayed_draws: int
    replayed_checkpoints: int
    exact_transcript_replay_passed: bool
    exact_boundary_replay_passed: bool
    target_local_scope_passed: bool
    cap_and_stopping_rule_passed: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.acquisition_id, "acquisition"),
            (self.binding_id, "binding"),
            (self.profile_id, "profile"),
        ):
            _cid(value, field)
        if (
            type(self.outcome) is not SequentialBernoulliOutcome
            or type(self.replayed_draws) is not int
            or self.replayed_draws < 0
            or type(self.replayed_checkpoints) is not int
            or self.replayed_checkpoints < 0
            or self.exact_transcript_replay_passed is not True
            or self.exact_boundary_replay_passed is not True
            or self.target_local_scope_passed is not True
            or self.cap_and_stopping_rule_passed is not True
        ):
            raise SequentialBernoulliInvariantViolation(
                "sequential verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_bernoulli_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "acquisition_id": self.acquisition_id,
            "binding_id": self.binding_id,
            "profile_id": self.profile_id,
            "outcome": self.outcome.value,
            "replayed_draws": self.replayed_draws,
            "replayed_checkpoints": self.replayed_checkpoints,
            "exact_transcript_replay_passed": True,
            "exact_boundary_replay_passed": True,
            "target_local_scope_passed": True,
            "cap_and_stopping_rule_passed": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_sequential_bernoulli_acquisition_v1(
    result: SequentialBernoulliAcquisitionV1,
) -> SequentialBernoulliVerificationV1:
    """Rebuild every checkpoint exactly from the serialized target transcript."""

    if type(result) is not SequentialBernoulliAcquisitionV1:
        raise SequentialBernoulliInvariantViolation(
            "verifier requires an exact sequential acquisition type"
        )
    draws = _unpack_draws(result.packed_draws, result.draw_count)
    if sum(draws) != result.success_count:
        raise SequentialBernoulliInvariantViolation(
            "verification transcript count mismatch"
        )
    replayed: list[AnytimeBernoulliCheckpointV1] = []
    running_successes = 0
    cursor = 0
    for checkpoint_draw_count in _expected_checkpoint_draw_counts(
        result.draw_count,
        result.profile,
    ):
        running_successes += sum(
            draws[cursor:checkpoint_draw_count]
        )
        cursor = checkpoint_draw_count
        replayed.append(
            build_anytime_bernoulli_checkpoint_v1(
                checkpoint_draw_count,
                running_successes,
                result.profile,
            )
        )
    if tuple(replayed) != result.checkpoints:
        raise SequentialBernoulliInvariantViolation(
            "confidence boundaries failed exact transcript replay"
        )
    expected_counters = _counters(
        result.draw_count,
        result.counters.source_poll_calls,
        tuple(replayed),
    )
    if expected_counters != result.counters:
        raise SequentialBernoulliInvariantViolation(
            "acquisition counters failed replay"
        )
    # Reconstructing the frozen dataclass re-runs the outcome, cap, chronology,
    # target-local, and earliest-stopping invariants.
    replay_result = SequentialBernoulliAcquisitionV1(
        binding=result.binding,
        profile=result.profile,
        outcome=result.outcome,
        draw_count=result.draw_count,
        success_count=result.success_count,
        packed_draws=result.packed_draws,
        checkpoints=tuple(replayed),
        counters=expected_counters,
    )
    if replay_result.acquisition_id != result.acquisition_id:
        raise SequentialBernoulliInvariantViolation(
            "acquisition identity failed deterministic replay"
        )
    return SequentialBernoulliVerificationV1(
        acquisition_id=result.acquisition_id,
        binding_id=result.binding.binding_id,
        profile_id=result.profile.profile_id,
        outcome=result.outcome,
        replayed_draws=result.draw_count,
        replayed_checkpoints=len(replayed),
        exact_transcript_replay_passed=True,
        exact_boundary_replay_passed=True,
        target_local_scope_passed=True,
        cap_and_stopping_rule_passed=True,
    )


__all__ = [
    "AnytimeBernoulliCheckpointV1",
    "CONTRACT_VERSION",
    "INTERVAL_EVIDENCE_SCOPE",
    "METHOD_ID",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "STATISTICAL_CLAIM_SCOPE",
    "SequentialBernoulliAcquisitionV1",
    "SequentialBernoulliCountersV1",
    "SequentialBernoulliInvariantViolation",
    "SequentialBernoulliOutcome",
    "SequentialBernoulliProfileV1",
    "SequentialBernoulliVerificationV1",
    "TargetLocalBernoulliRowBindingV1",
    "acquire_sequential_bernoulli_row_v1",
    "bernoulli_likelihood_v1",
    "bernoulli_mixture_rejects_v1",
    "beta_binomial_sequence_mass_v1",
    "build_anytime_bernoulli_checkpoint_v1",
    "clear_exact_bernoulli_math_cache_v1",
    "v0067_default_sequential_profile_v1",
    "verify_sequential_bernoulli_acquisition_v1",
]
