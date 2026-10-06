"""Independent exact interval and action-gap audit of the frozen V234 run.

No V234 producer is imported. V233's audited ordered tapes are the unchanged
input evidence; the beta mixture below uses a sequential predictive recurrence
rather than the producer's combinatorial formula.
"""
from collections import Counter
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_paired_query_score_v233 as prior

OUTPUT = ROOT/'reports/shared_prefix_score_v234'
PREVIOUS = ROOT/'reports/paired_query_score_v233'
EVENT_THRESHOLD, BISECTIONS = 3600, 40
REGRET = F(1, 20)


@lru_cache(maxsize=None)
def mixture_weight(n, k):
    """Jeffreys mixture probability of any one ordered binary sample."""
    successes, failures, weight = 0, 0, F(1)
    for index in range(n):
        if index < k:
            weight *= F(2*successes+1, 2*(index+1))
            successes += 1
        else:
            weight *= F(2*failures+1, 2*(index+1))
            failures += 1
    return weight


def mixture_value(n, k, probability):
    probability = F(probability)
    likelihood = probability**k*(1-probability)**(n-k)
    return mixture_weight(n, k)/likelihood if likelihood else None


@lru_cache(maxsize=None)
def region(n, k):
    """Outward closed region with exact outside/inside root brackets."""
    if not n:
        return dict(lower=F(0), upper=F(1), lower_bracket=None, upper_bracket=None)
    center = F(k, n)
    if k:
        lower, inside = F(0), center
        for _ in range(BISECTIONS):
            middle = (lower+inside)/2
            if mixture_value(n, k, middle) > EVENT_THRESHOLD:
                lower = middle
            else:
                inside = middle
        lower_bracket = [lower, inside]
    else:
        lower, lower_bracket = F(0), None
    if k < n:
        inside, upper = center, F(1)
        for _ in range(BISECTIONS):
            middle = (inside+upper)/2
            if mixture_value(n, k, middle) > EVENT_THRESHOLD:
                upper = middle
            else:
                inside = middle
        upper_bracket = [inside, upper]
    else:
        upper, upper_bracket = F(1), None
    return dict(lower=lower, upper=upper, lower_bracket=lower_bracket,
                upper_bracket=upper_bracket)


def conditional_bounds(query, chosen, other, retry_cost, p_region, q_region):
    """Derive the four vertices directly from query utility coefficients."""
    _, loss, delivery = prior.WEIGHTS[query]
    sign = 1 if chosen == 'DETOUR_RETURN' else -1
    continuation = sorted(sign*((delivery+loss)*q-loss-F(retry_cost))
                          for q in (q_region['lower'], q_region['upper']))
    vertices = [p*h for p in (p_region['lower'], p_region['upper'])
                for h in continuation]
    return continuation, [min(vertices), max(vertices)]


def audit_region(queues, operator, success, saved, check):
    n, k = len(queues[operator]), queues[operator].count(success)
    expected = region(n, k)
    check('full_paid_bernoulli_row', saved['operator'] == operator
          and saved['success'] == success and saved['n'] == n and saved['k'] == k)
    check('fixed_exact_mixture_protocol', saved['threshold'] == EVENT_THRESHOLD
          and saved['bisections'] == BISECTIONS and saved['kind'] == 'exact_rational_bisection')
    check('exact_outward_interval', F(saved['lower']) == expected['lower']
          and F(saved['upper']) == expected['upper'])
    for side in ('lower', 'upper'):
        bracket = saved[f'{side}_bracket']
        calculated = expected[f'{side}_bracket']
        if calculated is None:
            proof_ok = bracket['outside'] is None and F(bracket['inside']) == expected[side]
        else:
            outside, inside = calculated if side == 'lower' else calculated[::-1]
            proof_ok = (F(bracket['outside']) == outside and F(bracket['inside']) == inside
                        and abs(outside-inside) <= F(1, 2**BISECTIONS)
                        and mixture_value(n, k, outside) > EVENT_THRESHOLD
                        and mixture_value(n, k, inside) <= EVENT_THRESHOLD)
        check('exact_inside_outside_root_bracket', proof_ok)
    return expected


def audit_shared(queues, case, query, chosen, other, saved, check):
    detour, retry = prior.DETOUR, prior.R
    check('shared_prefix_policy_pair', {chosen, other} == {'DETOUR_RETURN', 'DETOUR_RETRY'}
          and saved['method'] == 'shared_prefix_rectangle' and saved['kind'] == 'exact_rectangle')
    check('known_shared_operating_cancellation', F(saved['constant_gap']) == 0
          and F(saved['retry_cost']) == F(case['retry_cost']))
    check('complete_shared_row_roster', saved['required_rows'] == [detour, retry]
          and set(saved['row_intervals']) == {detour, retry})
    p = audit_region(queues, detour, 'RECOVERY', saved['row_intervals'][detour], check)
    q = audit_region(queues, retry, 'DELIVERY', saved['row_intervals'][retry], check)
    check('full_paid_row_counts_not_paired_minimum', saved['n_by_row'] == {
        operator: len(queues[operator]) for operator in (detour, retry)}
        and saved['k_by_row'] == {detour: queues[detour].count('RECOVERY'),
                                 retry: queues[retry].count('DELIVERY')})
    continuation, gap = conditional_bounds(query, chosen, other, case['retry_cost'], p, q)
    check('exact_directional_continuation', saved['direction'] == (1 if chosen == 'DETOUR_RETURN' else -1)
          and list(map(F, saved['continuation_bounds'])) == continuation)
    check('exact_four_vertex_product', list(map(F, saved['gap_bounds'])) == gap)
    expected = gap[1] <= REGRET
    check('exact_shared_certificate', saved['threshold'] == EVENT_THRESHOLD
          and saved['certified'] == expected)
    return expected


def audit_direct(queues, case, query, chosen, other, saved, check):
    needed, scores, lower, upper = prior.scores_from_queues(
        queues, query, chosen, other, case['retry_cost'])
    bets = prior.predictable_bets(scores, lower, upper)
    units = [int(score*20) for score in scores]
    retry = F(case['retry_cost']) if 'DETOUR_RETRY' in (chosen, other) else None
    check('unchanged_direct_score_object', saved['method'] == 'paired_direct'
          and saved['required_rows'] == list(needed) and saved['n'] == len(scores)
          and list(map(F, saved['score_bounds'])) == [lower, upper]
          and (F(saved['retry_cost']) if saved['retry_cost'] is not None else None) == retry)
    check('exact_direct_score_statistics', {int(key): value for key, value in saved['score_histogram'].items()}
          == dict(Counter(units)) and saved['score_sum_units'] == sum(units)
          and saved['score_square_sum_units'] == sum(value*value for value in units)
          and saved['zero_bets'] == sum(bet == 0 for bet in bets))
    cost = prior.operating_constant(case, chosen, other)
    theta = REGRET-cost
    check('known_direct_operating_shift', F(saved['constant_gap']) == cost and F(saved['theta']) == theta)
    if theta >= upper:
        expected, kind = True, 'score_range'
    elif theta < lower:
        expected, kind = False, 'below_score_range'
    else:
        kind = 'bounded_mean_bet'
        logs = prior.independent_logs(scores, bets, theta)
        actual_log = logs[-1] if logs else D(0)
        saved_log, saved_product = D(saved['log_e_lower']), D(saved['e_lower'])
        with localcontext() as context:
            context.prec = 100
            proof_ok = (saved_log <= actual_log+D('1e-85') and saved_product >= 0
                        and (saved_product == 0 if not actual_log.is_finite()
                             else saved_product.ln() <= actual_log+D('1e-85'))
                        and D(saved['log_threshold_upper']) >= D(EVENT_THRESHOLD).ln()-D('1e-85'))
        check('outward_direct_terminal_e_bounds', proof_ok)
        expected = saved_log > D(saved['log_threshold_upper'])
    if kind != 'bounded_mean_bet':
        check('analytic_direct_support_branch', saved['log_e_lower'] is None
              and saved['e_lower'] is None and saved['log_threshold_upper'] is None)
    check('exact_direct_certificate', saved['threshold'] == EVENT_THRESHOLD
          and saved['kind'] == kind and saved['certified'] == expected)
    return expected


def run():
    begun, counts, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, valid):
        counts[name] += 1
        if not valid:
            failures.append(dict(check=name, location=location.copy()))

    key = lambda row: (row['life'], row['index'], row['arm'])
    protocol, summary = prior.load(OUTPUT/'run.json'), prior.load(OUTPUT/'summary.json')
    previous_audit = prior.load(PREVIOUS/'analysis.json')
    check('prior_paid_tape_audit_passed', previous_audit['valid']
          and previous_audit['new_observations'] == previous_audit['new_paid_samples'] == 0)
    check('exact_unchanged_paid_tape_copy', (OUTPUT/'tapes.jsonl.gz').read_bytes()
          == (PREVIOUS/'tapes.jsonl.gz').read_bytes())
    originals = prior.read_rows(ROOT/'reports/kernel_query_profile_v232/inputs.jsonl.gz')
    tapes, records = prior.read_rows(OUTPUT/'tapes.jsonl.gz'), prior.read_rows(OUTPUT/'records.jsonl.gz')
    old = {key(row): row for row in originals}
    v232 = {key(row): row for row in prior.read_rows(ROOT/'reports/kernel_query_profile_v232/records.jsonl.gz')}
    v233 = {key(row): row for row in prior.read_rows(PREVIOUS/'records.jsonl.gz')}
    truth = {key(row): row for row in prior.load(PREVIOUS/'scores.json')}
    scored = {key(row): row for row in prior.load(OUTPUT/'scores.json')}
    check('fixed_24_terminal_roster', len(records) == 24 and [key(row) for row in records]
          == [key(row) for row in tapes] == [key(row) for row in originals])
    check('frozen_joint_event_budget', protocol['stream_count'] == 180
          and protocol['direct_stream_count'] == 168 and protocol['bernoulli_stream_count'] == 12
          and protocol['threshold'] == EVENT_THRESHOLD and protocol['delta_per_life_arm'] == '1/20')
    check('frozen_stage_order_and_scope', protocol['phases'] == ['protocol_frozen', 'tapes_frozen',
          'certificates_frozen', 'saved_truth_evaluated', 'complete'] and protocol['complete']
          and protocol['qualification_only'] and not protocol['scientific_gate_changed']
          and protocol['new_observations'] == protocol['new_paid_samples'] == 0)
    check('frozen_selected_manifest', protocol['selected'] == [
        {field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')} for row in originals])
    direct_cache, row_cache, method_counts = set(), set(), Counter()
    false_certificates = 0
    for tape, row in zip(tapes, records):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        queues, snapshot_key = tape['operators'], key(row)
        check('unchanged_paid_snapshot_and_fees', all(row[field] == tape[field]
              for field in ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees'))
              and row['row_lengths'] == {operator: len(values) for operator, values in queues.items()})
        check('no_new_acquisition_per_snapshot', row['new_observations'] == row['new_paid_samples'] == 0)
        check('prior_statuses_not_rejudged', row['old_query_ready'] == old[snapshot_key]['terminal_plan']['query_ready']
              and row['v232_query_ready'] == v232[snapshot_key]['query_ready']
              and row['v233_query_ready'] == v233[snapshot_key]['query_ready'])
        chosen = old[snapshot_key]['terminal_plan']['queries']
        check('original_selected_policies', all(row['queries'][query]['policy'] == decision['policy']
              == v233[snapshot_key]['queries'][query]['policy'] for query, decision in chosen.items()))
        check('analytic_reward_wait', row['queries']['reward'] == dict(policy='WAIT', certified=True,
              kind='known_nonnegative_cost') and chosen['reward']['policy'] == 'WAIT')
        direct_calls = new_direct = new_rows = 0
        evidence = {}
        for query in ('goal', 'risk'):
            decision = row['queries'][query]
            comparisons, statuses = decision['comparisons'], []
            check('complete_three_alternative_roster', [item['other'] for item in comparisons]
                  == [policy for policy in prior.POLICIES if policy != decision['policy']])
            for comparison in comparisons:
                other = comparison['other']
                location['query'], location['other'] = query, other
                check('original_comparison_identity', comparison['query'] == query
                      and comparison['chosen'] == decision['policy'])
                shared = {decision['policy'], other} == {'DETOUR_RETURN', 'DETOUR_RETRY'}
                if shared:
                    expected = audit_shared(queues, row['case'], query, decision['policy'], other, comparison, check)
                    evidence.update(comparison['row_intervals'])
                    for operator in comparison['required_rows']:
                        cache_key = operator, tuple(queues[operator])
                        if cache_key not in row_cache:
                            row_cache.add(cache_key)
                            new_rows += 1
                else:
                    expected = audit_direct(queues, row['case'], query, decision['policy'], other, comparison, check)
                    direct_calls += 1
                    cache_key = (query, decision['policy'], other, comparison['retry_cost'],
                                 tuple((operator, tuple(queues[operator])) for operator in comparison['required_rows']))
                    if cache_key not in direct_cache:
                        direct_cache.add(cache_key)
                        new_direct += 1
                method_counts[comparison['method']] += 1
                statuses.append(expected)
            check('query_is_and_of_all_alternatives', decision['certified'] == all(statuses))
        expected_evidence = [evidence[operator] for operator in prior.OPERATORS if operator in evidence]
        check('deduplicated_full_row_evidence_records', row['evidence_records'] == expected_evidence)
        check('query_ready_is_three_query_and', row['query_ready'] == all(d['certified'] for d in row['queries'].values()))
        check('exact_direct_cache_work', row['direct_score_calls'] == direct_calls
              and row['unique_direct_score_streams'] == new_direct
              and row['direct_score_cache_hits'] == direct_calls-new_direct)
        check('exact_row_interval_reference_work', row['row_interval_calls'] == len(expected_evidence)
              and row['unique_row_intervals'] == new_rows
              and row['row_interval_cache_hits'] == len(expected_evidence)-new_rows)
        check('unchanged_postfreeze_truth_scores', scored[snapshot_key]['regrets'] == truth[snapshot_key]['regrets'])
        false = sum(row['queries'][query]['certified'] and F(regret) > REGRET
                    for query, regret in truth[snapshot_key]['regrets'].items())
        false_certificates += false
        check('reported_false_certificates', scored[snapshot_key]['false_certificates'] == false)
        check('no_false_retained_query_certificate', false == 0)
        print(f'audited life={row["life"]} index={row["index"]} arm={row["arm"]}', flush=True)
    location = {}
    check('exact_global_qualification_scope', summary['complete'] and summary['records'] == 24
          and summary['qualification_only'] and not summary['scientific_gate_changed']
          and summary['new_observations'] == summary['new_paid_samples'] == 0
          and summary['false_certificates'] == false_certificates)
    check('exact_unique_cache_work', summary['unique_direct_score_streams'] == len(direct_cache)
          and summary['unique_row_intervals'] == len(row_cache))
    for field in ('direct_score_calls', 'direct_score_cache_hits', 'row_interval_calls', 'row_interval_cache_hits'):
        check('exact_global_reference_work', summary[field] == sum(row[field] for row in records))
    for kind in ('failure', 'positive'):
        group, relevant = summary['groups'][kind], [row for row in records if row['kind'] == kind]
        check('exact_group_query_statuses', group['targets'] == len(relevant)
              and all(group[field] == sum(row[field] for row in relevant)
                      for field in ('old_query_ready', 'v232_query_ready', 'v233_query_ready', 'query_ready'))
              and group['queries'] == {query: sum(row['queries'][query]['certified'] for row in relevant)
                                       for query in prior.WEIGHTS})
        for arm in prior.ARMS:
            selected = [row for row in relevant if row['arm'] == arm]
            check('exact_group_arm_statuses', group['arms'][arm] == dict(targets=len(selected),
                  query_ready=sum(row['query_ready'] for row in selected)))
        methods, blockers = Counter(), Counter()
        for row in relevant:
            for query in ('goal', 'risk'):
                for comparison in row['queries'][query]['comparisons']:
                    method = comparison['method']
                    methods[method, 'certified' if comparison['certified'] else 'unknown'] += 1
                    if not comparison['certified']:
                        blockers[method] += 1
        check('exact_group_method_statuses', group['methods'] == {method: {status: methods[method, status]
              for status in ('certified', 'unknown')} for method in ('paired_direct', 'shared_prefix_rectangle')}
              and group['blockers_by_method'] == dict(blockers))
    result = dict(valid=not failures, records=len(records), comparisons=sum(method_counts.values()),
                  methods=dict(method_counts), checks=dict(counts), failures=failures,
                  false_certificates=false_certificates, prior_paid_tape_audit_valid=previous_audit['valid'],
                  new_observations=0, new_paid_samples=0, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    run()

