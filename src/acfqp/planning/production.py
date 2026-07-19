"""Sound production prechecks for cached exact J0 conclusions.

The Phase 0.5 G2048 regression deliberately continues after J0 has proved the
query infeasible so that the construction/split/fallback path is exercised.
Production is different: it may return ``INFEASIBLE_QUERY`` immediately, but
only when the exact proof is bound to the same structural model, build,
transition kernel, and query.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProductionPrecheckStatus(str, Enum):
    """The only terminal status produced by the production precheck."""

    INFEASIBLE_QUERY = "INFEASIBLE_QUERY"


@dataclass(frozen=True, slots=True)
class PlanningIdentity:
    """Content identities that make an exact planning claim reusable."""

    structural_id: str
    build_id: str
    kernel_hash: str
    query_hash: str

    def __post_init__(self) -> None:
        for field_name in ("structural_id", "build_id", "kernel_hash", "query_hash"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a nonempty string")


@dataclass(frozen=True, slots=True)
class ExactJ0InfeasibilityProof:
    """A cached oracle-truth claim with auditable establishment accounting."""

    proof_id: str
    identity: PlanningIdentity
    frontier_hash: str
    establishment_candidate_count: int
    establishment_elapsed_ns: int
    evidence: str = "oracle_truth"
    exact: bool = True
    infeasible: bool = True

    def __post_init__(self) -> None:
        if not self.proof_id or not self.frontier_hash:
            raise ValueError("proof_id and frontier_hash must be nonempty")
        if self.establishment_candidate_count < 0 or self.establishment_elapsed_ns < 0:
            raise ValueError("proof establishment costs must be nonnegative")
        if self.evidence != "oracle_truth" or not self.exact or not self.infeasible:
            raise ValueError("production shortcut requires exact oracle-truth infeasibility")


@dataclass(frozen=True, slots=True)
class ProductionPrecheckResult:
    """A resolved shortcut, including both historical and current-run costs."""

    status: ProductionPrecheckStatus
    proof_id: str
    identity: PlanningIdentity
    establishment_candidate_count: int
    establishment_elapsed_ns: int
    validation_elapsed_ns: int

    def __post_init__(self) -> None:
        if self.validation_elapsed_ns < 0:
            raise ValueError("proof validation cost must be nonnegative")


def resolve_known_infeasibility(
    current: PlanningIdentity,
    proof: ExactJ0InfeasibilityProof | None,
    *,
    validation_elapsed_ns: int = 0,
) -> ProductionPrecheckResult | None:
    """Return the production shortcut only for an identity-exact J0 proof.

    A mismatch is not an error: it means normal audit/refinement/fallback must
    continue.  No identity component is optional or wildcardable.
    """

    if validation_elapsed_ns < 0:
        raise ValueError("proof validation cost must be nonnegative")
    if proof is None or proof.identity != current:
        return None
    return ProductionPrecheckResult(
        ProductionPrecheckStatus.INFEASIBLE_QUERY,
        proof.proof_id,
        current,
        proof.establishment_candidate_count,
        proof.establishment_elapsed_ns,
        validation_elapsed_ns,
    )
