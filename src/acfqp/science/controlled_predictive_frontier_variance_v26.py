"""Combine the frozen frontier selector with the frozen variance repeat rule."""

from .controlled_predictive_frontier_v24 import FrontierGapPlannerState
from .controlled_predictive_variance_v20 import VarianceGapPlannerState


class FrontierVarianceGapPlannerState(FrontierGapPlannerState, VarianceGapPlannerState):
    """FRONTIER selects new rows; VARIANCE selects repeats or falls back to BALANCED.

    The inherited frontier_to_balanced_fallbacks counter records an empty
    structural selection here. Actual balanced fallback uses the unchanged
    variance_fallback_calls counter.
    """
