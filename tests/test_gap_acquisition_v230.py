from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import gap_acquisition_v230 as acquisition


def empty():
    return {op: dict.fromkeys(categories, 0) for op, categories in acquisition.ALPHABETS.items()}


def kernel(delivery):
    result = {}
    for op, categories in acquisition.ALPHABETS.items():
        result[op] = dict.fromkeys(categories, F(0))
        result[op]['DELIVERY'] = F(delivery)
        result[op]['LOST'] = 1-F(delivery)
    return result


def plan(gap=F(1), labels=(0, 1)):
    return dict(utility_lower=F(2), goal_impossible=False, query_ready=gap <= F(1, 20),
                query_certificates={'goal': {'regret_upper': gap}}, mode='library',
                candidate_labels={str(i): {'index': i} for i in labels},
                candidate_posteriors={0: kernel(1), 1: kernel(0)})


def test_forecasts_keep_candidate_outcomes_distinct_and_do_not_commit_counts():
    member, initial, work = empty(), plan(), Counter()
    before = deepcopy((member, initial))
    seen = []

    def forecast(counts, counter):
        seen.append(deepcopy(counts))
        count = counts['SHORT_PASS']
        informative = count['DELIVERY'] >= 16 or count['LOST'] >= 16
        return plan(F(0) if informative else F(1))

    result = acquisition.choose(member, initial, 0, work, forecast)
    assert result['operator'] == 'SHORT_PASS'
    assert (member, initial) == before
    assert result['candidate_scenarios'] == 2
    assert result['horizons'] == [16, 64, 384]
    assert work['gap_acquisition_candidate_scenarios'] == 18
    assert work['gap_acquisition_computed_forecasts'] == len(seen)
    assert all(not (row[op]['DELIVERY'] and row[op]['LOST'])
               for row in seen for op in acquisition.OPERATORS)
    assert all(sum(sum(row.values()) for row in counts.values()) in (16, 64, 384)
               for counts in seen)
    assert 'environment_random_draws' not in work and 'controlled_samples' not in work


def test_multibatch_lookahead_crosses_a_single_batch_plateau():
    member, initial, work = empty(), plan(), Counter()

    def forecast(counts, counter):
        informative = sum(counts['DETOUR_PASS'].values()) >= 64
        return plan(F(0) if informative else F(1))

    result = acquisition.choose(member, initial, 0, work, forecast)
    assert result['operator'] == 'DETOUR_PASS'
    assert result['selected_horizon'] == 64
    assert all(rows[0]['mean_gain'] == 0 for rows in result['forecasts'].values())
    assert result['scores']['DETOUR_PASS'] > 0


def test_plateau_uses_source_discrimination_without_rewarding_library_loss():
    def forecast(counts, counter):
        if sum(counts['SHORT_PASS'].values()):
            predicted = plan(labels=())
            predicted['mode'] = 'member'
            return predicted
        if sum(counts['DETOUR_PASS'].values()):
            return plan(labels=(0,))
        return plan()

    result = acquisition.choose(empty(), plan(), 0, Counter(), forecast)
    assert not any(result['scores'].values())
    assert result['operator'] == 'DETOUR_PASS'
    assert result['forecasts']['SHORT_PASS'][0]['mean_eliminated_types'] == 0
    assert result['forecasts']['DETOUR_PASS'][0]['mean_eliminated_types'] == 1


def test_certified_stop_and_budget_stop_perform_no_forecasts():
    def unexpected_forecast(counts, counter):
        raise AssertionError('a stopped target must not be forecast')

    assert acquisition.choose(empty(), plan(F(0)), 0, Counter(), unexpected_forecast) is None
    assert acquisition.choose(empty(), plan(), 384, Counter(), unexpected_forecast) is None


def test_horizon_respects_remaining_budget_and_rounding_preserves_batch_size():
    work, seen = Counter(), []

    def forecast(counts, counter):
        seen.append(sum(sum(row.values()) for row in counts.values()))
        return plan()

    result = acquisition.choose(empty(), plan(), 368, work, forecast)
    assert result['horizons'] == [16] and set(seen) == {16}
    value = kernel(F(1, 3))
    value['DETOUR_PASS'] = dict(DELIVERY=F(1, 3), LOST=F(1, 3), RECOVERY=F(1, 3))
    assert acquisition.increments(value, 'DETOUR_PASS', 16) == dict(DELIVERY=6, LOST=5, RECOVERY=5)
