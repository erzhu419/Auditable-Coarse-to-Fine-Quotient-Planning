"""Query evidence from complete actually observed conditional continuations.

Native rows also receive standalone S tails; complete-trajectory statistics do
not. V233's score support, predictable bets and outward evaluation are reused.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from . import paired_query_score_v233 as direct

OPERATORS, ALPHABETS = direct.OPERATORS, direct.ALPHABETS
S, D, R = OPERATORS
OUTCOMES = tuple((short, detour, retry) for short in ALPHABETS[S]
    for detour, retry in (('DELIVERY', None), ('LOST', None), ('RECOVERY', 'DELIVERY'), ('RECOVERY', 'LOST')))
OUTCOME_KEYS = tuple('|'.join(value if value is not None else 'NONE' for value in outcomes) for outcomes in OUTCOMES)
POLICIES = direct.POLICIES


def new_type_state():
    return dict(native_counts={op: dict.fromkeys(ALPHABETS[op], 0) for op in OPERATORS},
        rounds=[], joint_outcome_counts=dict.fromkeys(OUTCOME_KEYS, 0), tail_s_samples=0, round_prefix_last_id=None)


def observe_round(state, outcomes, round_id):
    values = tuple(outcomes[op] for op in OPERATORS)
    if values not in OUTCOMES:
        raise ValueError('a complete round requires R exactly when D reaches RECOVERY')
    for op, outcome in outcomes.items():
        if outcome is not None:
            state['native_counts'][op][outcome] += 1
    state['rounds'].append(deepcopy(outcomes))
    state['joint_outcome_counts']['|'.join(value if value is not None else 'NONE' for value in values)] += 1
    state['round_prefix_last_id'] = round_id


def observe_tail_s(state, outcome):
    state['native_counts'][S][outcome] += 1
    state['tail_s_samples'] += 1


def round_vectors(case, outcomes):
    sc, dc = direct.COST_PRIOR[case['operating']]
    short, detour, retry = (outcomes[op] for op in OPERATORS)
    recovery = detour == 'RECOVERY'
    return dict(WAIT=[F(0)]*3,
        SHORT=[-sc, F(short == 'LOST'), F(short == 'DELIVERY')],
        DETOUR_RETURN=[-dc, F(detour == 'LOST'), F(detour == 'DELIVERY')],
        DETOUR_RETRY=[-dc-F(case['retry_cost'])*recovery,
            F(detour == 'LOST' or recovery and retry == 'LOST'),
            F(detour == 'DELIVERY' or recovery and retry == 'DELIVERY')])


def pure_vectors(state, case):
    n = len(state['rounds'])
    result = {policy: [F(0)]*3 for policy in POLICIES}
    for values, key in zip(OUTCOMES, OUTCOME_KEYS):
        count = state['joint_outcome_counts'][key]
        if count:
            vectors = round_vectors(case, dict(zip(OPERATORS, values)))
            for policy in POLICIES:
                for position in range(3):
                    result[policy][position] += F(count, n)*vectors[policy][position]
    return result


def point_queries(vectors):
    weights = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
    result = {}
    for query, (reward, failure, delivery) in weights.items():
        utility = lambda policy: vectors[policy][0]*reward-vectors[policy][1]*failure+vectors[policy][2]*delivery
        result[query] = dict(policy=min(POLICIES, key=lambda policy: (-utility(policy), policy)))
    return result


def actual_statistics(rounds, query, chosen, other, retry_cost, cache, work=None):
    spec = direct.score_spec(query, chosen, other, retry_cost)
    prefix = tuple(tuple(outcomes[op] for op in OPERATORS) for outcomes in rounds)
    key = spec, prefix
    if key in cache:
        if work is not None:
            work['trajectory_score_cache_hits'] += 1
        return cache[key]
    units = []
    for outcomes in rounds:
        score = (direct._random_utility(other, query, spec.retry_cost, outcomes)
                 -direct._random_utility(chosen, query, spec.retry_cost, outcomes))
        value = score*direct.SCORE_SCALE
        units.append(value.numerator)
    scores = tuple(units)
    statistics = direct.StreamStatistics(spec, scores, direct.predictable_bets(spec, scores),
        sum(scores), sum(value*value for value in scores))
    cache[key] = statistics
    if work is not None:
        work['trajectory_unique_score_prefixes'] += 1
        work['trajectory_complete_score_evaluations'] += len(scores)
    return statistics


def trajectory_certificates(rounds, case, queries, cache, work=None):
    result = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    records = []
    for query in direct.QUERIES:
        chosen, comparisons = queries[query]['policy'], []
        for other in POLICIES:
            if other == chosen:
                continue
            statistics = actual_statistics(rounds, query, chosen, other, case['retry_cost'], cache, work)
            comparison = dict(direct.statistics_record(statistics), **direct.evaluate(statistics, case),
                score_source='actual_complete_conditional_rounds')
            comparisons.append(comparison)
            records.append(comparison)
            if work is not None:
                work['trajectory_certificate_evaluations'] += 1
        result[query] = dict(policy=chosen, certified=all(row['certified'] for row in comparisons), comparisons=comparisons)
    return dict(queries=result, all_ready=all(row['certified'] for row in result.values()),
        comparison_records=records, threshold=direct.STREAM_THRESHOLD)
