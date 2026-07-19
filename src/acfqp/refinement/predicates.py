"""Canonical deterministic predicates for hard quotient refinement."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Hashable, Any


Feature = Callable[[Hashable], Any]


def canonical_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


@dataclass(frozen=True)
class Predicate:
    feature_name: str
    operator: str
    threshold: Fraction
    feature: Feature = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        if not self.feature_name:
            raise ValueError("predicate feature name must not be empty")
        if self.operator not in {"<=", ">"}:
            raise ValueError("V0 predicates support only '<=' and '>'")
        object.__setattr__(self, "threshold", canonical_fraction(self.threshold))

    @property
    def canonical_id(self) -> str:
        threshold = f"{self.threshold.numerator}/{self.threshold.denominator}"
        return f"{self.feature_name}|{self.operator}|{threshold}"

    def __call__(self, state: Hashable) -> bool:
        value = canonical_fraction(self.feature(state))
        if self.operator == "<=":
            return value <= self.threshold
        return value > self.threshold
