"""Fixed-partition route evidence and condition-directed acquisition.

The learner receives observed categorical outcomes.  Supplied operator
supports, graph, costs and terminal semantics remain prior knowledge.  New
task laws are isolated in a separate module, which this learner never imports.
"""
from collections import Counter
from copy import deepcopy

from . import continual_route_kernels_v202 as learning
from . import target_risk_acquisition_v204 as acquisition
from .structured_route_task_v201 import QUERIES, plan

OPERATORS = learning.OPERATORS
ALPHABETS = learning.ALPHABETS
FIELDS = learning.FEATURE_FIELDS
PURE_POLICIES = acquisition.PURE_POLICIES
BATCH = acquisition.BATCH
BUDGET = acquisition.BUDGET
BETA = acquisition.BETA
GRID = acquisition.GRID
fit = learning.fit
probabilities = learning.probabilities
predicted_graph = learning.predicted_graph
make_plan = acquisition.make_plan
update = acquisition.update


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0)+amount


def fixed_model(source, full, work=None):
    """Keep SOURCE conditions while estimating them from all prefix counts.

    ``full`` is an already fitted FULL_CONTEXT model, not new observations.
    Only the selected SOURCE subset is scored; no partition re-selection or
    frozen SOURCE parameter table is used.
    """
    counts = Counter() if work is None else work
    _add(counts, "fixed_model_calls")
    model = deepcopy(full)
    _add(counts, "fixed_model_copies")
    _add(counts, "fixed_model_copied_contexts", sum(len(table) for table in full["tables"].values()))
    model["arm"] = "FIXED"
    model["selected_fields"] = deepcopy(source["selected_fields"])
    model["scores"] = {}
    for operator in OPERATORS:
        fields = tuple(model["selected_fields"][operator])
        score = learning._score(model["tables"][operator], operator, fields, counts)
        model["scores"][operator] = [dict(fields=list(fields), score=score)]
        _add(counts, "fixed_model_selected_subsets")
    model["fit_counts"] = dict(counts)
    return model


def projection_counts(model, case, work=None):
    """Experience at each entry operator's currently selected projection."""
    result = {}
    _add(work, "acquisition_projection_calls")
    for operator in OPERATORS[:2]:
        fields = model["selected_fields"][operator]
        wanted = tuple(case[field] for field in fields)
        _add(work, "acquisition_context_projections")
        n = 0
        for record in model["tables"][operator]:
            _add(work, "acquisition_context_scans")
            _add(work, "acquisition_context_projections")
            if tuple(record["context"][field] for field in fields) == wanted:
                n += sum(record["counts"].values())
                _add(work, "acquisition_count_summands", len(ALPHABETS[operator]))
                _add(work, "acquisition_projection_accumulations")
        result[operator] = n
    return result


def choose(model, case, current, work=None):
    """Pilot each unseen entry projection, then follow point goal/risk ratio.

    Pilot order is SHORT_PASS then DETOUR_PASS.  Inherited projection counts
    can remove either pilot; parameters still update on every real batch.
    """
    _add(work, "acquisition_choice_calls")
    observed = projection_counts(model, case, work)
    for operator in OPERATORS[:2]:
        _add(work, "acquisition_pilot_checks")
        if observed[operator] == 0:
            _add(work, "acquisition_pilot_choices")
            return dict(operator=operator, pilot=True, policy=None,
                        forecast_scores=None, policy_scores=None, projection_counts=observed)
    choice = acquisition.cold_policy(model, case, current, work)
    _add(work, "acquisition_ratio_choices")
    return dict(**choice, pilot=False, projection_counts=observed)


def query_decisions(model, case, work=None):
    """Own H4 joint policy for each supplied reward, goal and risk query.

    Returns the generic DP dictionaries, including tuple-keyed values,
    policies and action vectors.  A caller may retain only root/recovery
    decisions and their own joint vectors for later independent evaluation.
    """
    _add(work, "query_decision_sets")
    graph = predicted_graph(model, case, work)
    return {query: plan(graph, 4, query, work) for query in QUERIES}
