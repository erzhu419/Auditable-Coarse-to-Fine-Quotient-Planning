"""Hard partitions, nominal quotients, and optional behavioural controls.

The direct-homomorphism construction depends only on ``partition`` and
``quotient``.  Behavioural-oracle exports are therefore loaded lazily: this
preserves the public ``acfqp.abstraction`` API without making every quotient
consumer transitively import the oracle target implementation.
"""

from importlib import import_module

from .partition import Partition
from .quotient import (
    ExactRealizationEnvelope,
    GroundRealization,
    NominalActionModel,
    NominalQuotient,
    QuotientModels,
    RAPM,
    ReusableAbstractPlanningModel,
    build_exact_realization_envelope,
    build_nominal_quotient,
    build_quotient_models,
    identity_action_label,
)


_BEHAVIORAL_EXPORTS = frozenset(
    {
        "BehavioralActionAssignment",
        "BehavioralActionSignature",
        "BehavioralCellId",
        "BehavioralRefinementStep",
        "BehavioralSemanticAdapter",
        "ExactBehavioralQuotient",
        "build_exact_behavioral_quotient",
    }
)


def __getattr__(name: str):
    if name not in _BEHAVIORAL_EXPORTS:
        raise AttributeError(name)
    module = import_module(".behavioral", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value

__all__ = [
    "BehavioralActionAssignment",
    "BehavioralActionSignature",
    "BehavioralCellId",
    "BehavioralRefinementStep",
    "BehavioralSemanticAdapter",
    "ExactBehavioralQuotient",
    "ExactRealizationEnvelope",
    "GroundRealization",
    "NominalActionModel",
    "NominalQuotient",
    "Partition",
    "QuotientModels",
    "RAPM",
    "ReusableAbstractPlanningModel",
    "build_exact_realization_envelope",
    "build_exact_behavioral_quotient",
    "build_nominal_quotient",
    "build_quotient_models",
    "identity_action_label",
]
