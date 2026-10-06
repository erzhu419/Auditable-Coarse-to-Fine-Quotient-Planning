"""Anytime direct policy-gap tests from paired, actually paid row prefixes.

Each fixed query/policy/retry-cost stream pairs the i-th observation of only
the rows on which that gap depends.  Its score omits the known additive
operating-cost difference.  Under the declared stationary true-type scope,
independent row stacks make these scores iid even when the revealed prefix
length was chosen using other observations.  The fixed predictable bets
therefore give an all-prefix Ville event, rather than a product of separately
tested prefix e-values.  The 216 streams per life/arm use threshold 4320.

Operating costs change the tested mean, but never the score or betting rule.
All evidence below is immutable and depends only on supplied observations;
this module neither samples nor imports the simulator's probabilities.
"""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from functools import lru_cache
from itertools import product

from .continual_route_kernels_v202 import ALPHABETS, COST_PRIOR, OPERATORS

POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
QUERIES = ('goal', 'risk')
WEIGHTS = {'goal': (0, 4), 'risk': (4, 4)}  # failure, delivery
REGRET = F(1, 20)
STREAM_THRESHOLD = 4320
SCORE_SCALE = 20


@dataclass(frozen=True)
class ScoreSpec:
    query: str
    chosen: str
    other: str
    retry_cost: F | None
    required_rows: tuple[str, ...]
    lower: F
    upper: F
    score_table: tuple[tuple[tuple[str, ...], int], ...]


@dataclass(frozen=True)
class StreamStatistics:
    spec: ScoreSpec
    score_units: tuple[int, ...]
    bets: tuple[tuple[int, int], ...]
    score_sum_units: int
    score_square_sum_units: int

    @property
    def n(self):
        return len(self.score_units)


def _random_utility(policy, query, retry_cost, observations):
    failure, delivery = WEIGHTS[query]
    if policy == 'WAIT':
        return F(0)
    operator = OPERATORS[0] if policy == 'SHORT' else OPERATORS[1]
    outcome = observations[operator]
    result = F(delivery * (outcome == 'DELIVERY') - failure * (outcome == 'LOST'))
    if policy == 'DETOUR_RETRY' and outcome == 'RECOVERY':
        retry = observations[OPERATORS[2]]
        result += delivery * (retry == 'DELIVERY') - failure * (retry == 'LOST')
        result -= retry_cost
    return result


def score_spec(query, chosen, other, retry_cost='19/20'):
    """Describe one fixed score stream; nonretry pairs share retry-cost keys."""
    if query not in QUERIES or chosen not in POLICIES or other not in POLICIES:
        raise ValueError('V233 tests goal/risk comparisons of the four pure policies')
    retry = F(retry_cost) if 'DETOUR_RETRY' in (chosen, other) else None
    if retry is not None and retry not in (F(17, 20), F(19, 20)):
        raise ValueError('V233 has two declared retry-cost streams')
    return _score_spec(query, chosen, other, retry)


@lru_cache(maxsize=80)
def _score_spec(query, chosen, other, retry_cost):
    dependencies = {'WAIT': (), 'SHORT': (OPERATORS[0],),
                    'DETOUR_RETURN': (OPERATORS[1],),
                    'DETOUR_RETRY': (OPERATORS[1], OPERATORS[2])}
    required = tuple(op for op in OPERATORS
                     if op in dependencies[chosen] or op in dependencies[other])
    if chosen == other:
        required = ()
    table = []
    for values in product(*(ALPHABETS[op] for op in required)):
        observations = dict(zip(required, values))
        score = (F(0) if chosen == other else
                 _random_utility(other, query, retry_cost, observations)
                 - _random_utility(chosen, query, retry_cost, observations))
        units = score * SCORE_SCALE
        if units.denominator != 1:
            raise ValueError('declared score must use the fixed twentieth-unit grid')
        table.append((values, units.numerator))
    lower = F(min(units for _, units in table), SCORE_SCALE)
    upper = F(max(units for _, units in table), SCORE_SCALE)
    return ScoreSpec(query, chosen, other, retry_cost, required, lower, upper, tuple(table))


def predictable_bets(spec, score_units):
    """Fixed nonnegative bets from past complete scores, never current scores."""
    width = spec.upper - spec.lower
    if not width:
        return tuple((0, 1) for _ in score_units)
    total, square_total, result = 0, 0, []
    for past_n, units in enumerate(score_units):
        mean = F(total, SCORE_SCALE * past_n) if past_n else F(0)
        variance = (F(square_total, SCORE_SCALE**2 * past_n) - mean**2
                    if past_n else F(0))
        difference = REGRET - mean
        denominator = variance + difference**2 + width**2 / (past_n + 1)
        bet = min(1 / width, max(F(0), difference / denominator))
        result.append((bet.numerator, bet.denominator))
        total += units
        square_total += units * units
    return tuple(result)


def stream_statistics(sequences, query, chosen, other, retry_cost='19/20', cache=None):
    """Pair required paid prefixes, with an optional exact immutable-key cache.

    Cache keys contain only the required prefixes, so extra retry observations
    cannot change a comparison which does not use retry.  No aggregate-count
    ordering is synthesized: sequential outcomes are required evidence.
    """
    spec = score_spec(query, chosen, other, retry_cost)
    prefix = tuple((op, tuple(sequences[op])) for op in spec.required_rows)
    key = (spec, prefix)
    if cache is not None and key in cache:
        return cache[key]
    n = min((len(values) for _, values in prefix), default=0)
    table = dict(spec.score_table)
    scores = tuple(table[tuple(values[index] for _, values in prefix)] for index in range(n))
    result = StreamStatistics(spec, scores, predictable_bets(spec, scores),
                              sum(scores), sum(value * value for value in scores))
    if cache is not None:
        cache[key] = result
    return result


def constant_gap(spec, case):
    """Known additive utility(other)-utility(chosen) operating-cost term."""
    short, detour = COST_PRIOR[case['operating']]
    costs = {'WAIT': F(0), 'SHORT': short,
             'DETOUR_RETURN': detour, 'DETOUR_RETRY': detour}
    return costs[spec.chosen] - costs[spec.other]


def evaluate(statistics, case, threshold=STREAM_THRESHOLD):
    """Certify mean(score)+known_cost <= .05, with an outward e-log proof."""
    spec = statistics.spec
    if spec.retry_cost is not None and F(case['retry_cost']) != spec.retry_cost:
        raise ValueError('retry-cost case must match its fixed score stream')
    cost = constant_gap(spec, case)
    theta = REGRET - cost
    result = dict(n=statistics.n, required_rows=list(spec.required_rows),
                  score_bounds=[spec.lower, spec.upper], constant_gap=cost,
                  theta=theta, threshold=int(threshold), log_e_lower=None,
                  log_threshold_upper=None, e_lower=None)
    if theta >= spec.upper:
        return dict(result, certified=True, kind='score_range')
    if theta < spec.lower:
        return dict(result, certified=False, kind='below_score_range')
    with localcontext() as context:
        context.prec, context.rounding = 80, ROUND_FLOOR
        lower_product = Decimal(1)
        for units, (numerator, denominator) in zip(statistics.score_units, statistics.bets):
            factor = 1 + F(numerator, denominator) * (theta - F(units, SCORE_SCALE))
            # theta within the score range and lambda <= 1/range make this
            # factor nonnegative; each downward operation preserves a bound.
            lower_factor = Decimal(factor.numerator) / Decimal(factor.denominator)
            lower_product *= lower_factor
        lower_log = lower_product.ln().next_minus() if lower_product else Decimal('-Infinity')
        upper_threshold = Decimal(threshold).ln().next_plus()
    return dict(result, certified=lower_log > upper_threshold, kind='bounded_mean_bet',
                log_e_lower=str(lower_log), log_threshold_upper=str(upper_threshold),
                e_lower=str(lower_product))


def statistics_record(statistics):
    """Small retained summary; paid tapes permit independent sequential replay."""
    spec = statistics.spec
    return dict(query=spec.query, chosen=spec.chosen, other=spec.other,
                retry_cost=spec.retry_cost, required_rows=list(spec.required_rows),
                score_bounds=[spec.lower, spec.upper], n=statistics.n,
                score_histogram=dict(sorted(Counter(statistics.score_units).items())),
                score_sum_units=statistics.score_sum_units,
                score_square_sum_units=statistics.score_square_sum_units,
                zero_bets=sum(numerator == 0 for numerator, _ in statistics.bets))


def certificates(sequences, case, point_queries, cache=None):
    """AND all ordered alternative comparisons for each selected pure policy."""
    if point_queries['reward']['policy'] != 'WAIT':
        raise ValueError('declared reward query chooses the known cost-optimal WAIT')
    result = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    records = []
    for query in QUERIES:
        chosen = point_queries[query]['policy']
        comparisons = []
        for other in POLICIES:
            if other == chosen:
                continue
            statistics = stream_statistics(sequences, query, chosen, other,
                                           case['retry_cost'], cache)
            comparison = dict(statistics_record(statistics), **evaluate(statistics, case))
            comparisons.append(comparison)
            records.append(comparison)
        result[query] = dict(policy=chosen, certified=all(row['certified'] for row in comparisons),
                             comparisons=comparisons)
    return dict(queries=result, all_ready=all(row['certified'] for row in result.values()),
                comparison_records=records, threshold=STREAM_THRESHOLD)
