"""Candidate-specific, multibatch forecasts for certificate acquisition.

The callback evaluates hypothetical member counts with the real planner.  Every
forecast is discarded; only the returned operator is used for the next paid
batch.  Forecasts neither certify a query nor update the persistent library.
"""
from copy import deepcopy
from fractions import Fraction as F

from .scoped_union_v228 import OPERATORS, ALPHABETS
from .scoped_queries_v228 import THRESHOLD

BATCH, TARGET_CAP = 16, 384


def _add(work, name, amount=1):
    work[name] = work.get(name, 0) + amount


def _deficit(plan):
    goal = F(0) if plan['goal_impossible'] else max(F(0), F(2)-plan['utility_lower'])
    gap = max(row['regret_upper'] for row in plan['query_certificates'].values())
    return goal + max(F(0), gap-THRESHOLD)


def increments(kernel, operator, samples):
    """Round one candidate's expected categorical counts to a paid-batch size."""
    expected = {cat: samples*F(kernel[operator][cat]) for cat in ALPHABETS[operator]}
    result = {cat: int(value) for cat, value in expected.items()}
    order = sorted(ALPHABETS[operator], key=lambda cat: (
        -(expected[cat]-result[cat]), ALPHABETS[operator].index(cat)))
    for cat in order[:samples-sum(result.values())]:
        result[cat] += 1
    return result


def _counts_key(member):
    return tuple(member[op][cat] for op in OPERATORS for cat in ALPHABETS[op])


def choose(member, plan, spent, work, forecast):
    """Choose one batch using up to three future horizons per source type.

    ``plan['candidate_posteriors']`` supplies one feasible forecast kernel per
    distinct source index, or ``{'member': posterior}`` in member-only mode.
    A source index has one vote regardless of how many repair branches retain
    it.  ``forecast(member_counts, work)`` must return a plan without committing
    evidence.  It receives a fresh count dictionary on every computed forecast.

    Mean certificate-deficit reduction per batch determines acquisition.  Mean
    eliminated source types breaks forecast ties; remaining ties use observed
    row counts and the fixed operator order.  Uniform scenario weights are an
    acquisition heuristic, not probabilities used by the confidence bound.
    """
    if spent >= TARGET_CAP or ((plan['utility_lower'] >= 2 or plan['goal_impossible'])
                               and plan['query_ready']):
        return None
    remaining = TARGET_CAP-spent
    horizons = sorted({min(BATCH, remaining), min(4*BATCH, remaining), remaining})
    kernels = list(plan['candidate_posteriors'].values())
    initial_types = len({row['index'] for row in plan['candidate_labels'].values()})
    before = _deficit(plan)
    cache, diagnostics, best = {}, {}, {}
    for operator in OPERATORS:
        rows = []
        for horizon in horizons:
            gain, eliminated, ready = F(0), F(0), 0
            for kernel in kernels:
                hypothetical = deepcopy(member)
                future = increments(kernel, operator, horizon)
                for category, count in future.items():
                    hypothetical[operator][category] += count
                key = _counts_key(hypothetical)
                if key in cache:
                    predicted = cache[key]
                    _add(work, 'gap_acquisition_forecast_cache_hits')
                else:
                    predicted = forecast(hypothetical, work)
                    cache[key] = predicted
                    _add(work, 'gap_acquisition_computed_forecasts')
                _add(work, 'gap_acquisition_candidate_scenarios')
                gain += before-_deficit(predicted)
                # Losing every library hypothesis is not source discrimination.
                if predicted['mode'] == 'library':
                    types = {row['index'] for row in predicted['candidate_labels'].values()}
                    eliminated += initial_types-len(types)
                ready += int((predicted['utility_lower'] >= 2 or predicted['goal_impossible'])
                             and predicted['query_ready'])
            mean_gain, mean_eliminated = gain/len(kernels), eliminated/len(kernels)
            batches = F(horizon, BATCH)
            rows.append(dict(horizon=horizon, mean_gain=mean_gain,
                             gain_per_batch=mean_gain/batches,
                             mean_eliminated_types=mean_eliminated,
                             elimination_per_batch=mean_eliminated/batches,
                             ready_scenarios=ready, scenarios=len(kernels)))
        diagnostics[operator] = rows
        best[operator] = max(rows, key=lambda row: (
            max(F(0), row['gain_per_batch']),
            max(F(0), row['elimination_per_batch']), -row['horizon']))
    operator = min(OPERATORS, key=lambda op: (
        -max(F(0), best[op]['gain_per_batch']),
        -max(F(0), best[op]['elimination_per_batch']),
        sum(member[op].values()), OPERATORS.index(op)))
    return dict(operator=operator, reason='candidate_multibatch_certificate_gap',
                scores={op: max(F(0), best[op]['gain_per_batch']) for op in OPERATORS},
                selected_horizon=best[operator]['horizon'], horizons=horizons,
                candidate_scenarios=len(kernels), forecasts=diagnostics)
