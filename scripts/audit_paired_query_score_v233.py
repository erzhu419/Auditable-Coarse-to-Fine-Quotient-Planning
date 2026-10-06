"""Independent chronological tape and bounded-score audit of V233.

The V233 producers are not imported.  Sources and paid target observations are
replayed from their frozen seeds, and route scores use independent arithmetic.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from itertools import product
import gzip
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_joint_gap_v230 import ALPHABETS, COSTS, OPERATORS, POLICIES, WEIGHTS, utility, vectors
from scripts.analyze_scoped_lifecycle_v229 import world

INPUT = ROOT/'reports/oracle_gap_lifecycle_v231'
OUTPUT = ROOT/'reports/paired_query_score_v233'
THRESHOLD, EVENT_THRESHOLD = F(1, 20), 4320
ARMS = ('ORACLE_BALANCED', 'ORACLE_GAP')
S, DETOUR, R = OPERATORS


def load(path):
    return json.loads(path.read_text())


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def empty():
    return {operator: [] for operator in OPERATORS}


def atom_score(policy, outcome, query, retry_cost):
    """Utility with only the deterministic operating cost removed."""
    _, failure, goal = WEIGHTS[query]
    if policy == 'WAIT':
        return F(0)
    if policy == 'SHORT':
        return F(goal*(outcome[S] == 'DELIVERY')-failure*(outcome[S] == 'LOST'))
    score = F(goal*(outcome[DETOUR] == 'DELIVERY')-failure*(outcome[DETOUR] == 'LOST'))
    if policy == 'DETOUR_RETRY' and outcome[DETOUR] == 'RECOVERY':
        score += goal*(outcome[R] == 'DELIVERY')-failure*(outcome[R] == 'LOST')-F(retry_cost)
    return score


def required(chosen, other):
    if chosen == other:
        return ()
    policies = {chosen, other}
    return tuple(operator for operator in OPERATORS if (
        operator == S and 'SHORT' in policies or
        operator == DETOUR and policies & {'DETOUR_RETURN', 'DETOUR_RETRY'} or
        operator == R and 'DETOUR_RETRY' in policies))


def specification(query, chosen, other, retry_cost):
    needed = required(chosen, other)
    values = {}
    for categories in product(*(ALPHABETS[operator] for operator in needed)):
        atom = dict(zip(needed, categories))
        value = (F(0) if chosen == other else
                 atom_score(other, atom, query, retry_cost)-atom_score(chosen, atom, query, retry_cost))
        values[categories] = value
    return needed, values, min(values.values()), max(values.values())


def operating_constant(case, chosen, other):
    short, detour = COSTS[case['operating']]
    costs = dict(WAIT=F(0), SHORT=short, DETOUR_RETURN=detour, DETOUR_RETRY=detour)
    return costs[chosen]-costs[other]


def predictable_bets(scores, lower, upper):
    width, total, squares = upper-lower, F(0), F(0)
    if not width:
        return [F(0)]*len(scores)
    result = []
    for index, score in enumerate(scores, 1):
        past = index-1
        mean = total/past if past else F(0)
        variance = squares/past-mean*mean if past else F(0)
        deviation = THRESHOLD-mean
        bet = min(1/width, max(F(0), deviation/(variance+deviation**2+width**2/index)))
        result.append(bet)
        total += score
        squares += score*score
    return result


def independent_logs(scores, bets, theta):
    """Recompute complete-prefix logarithms independently at 100 digits."""
    with localcontext() as context:
        context.prec = 100
        total, result = D(0), []
        for score, bet in zip(scores, bets):
            factor = 1+bet*(theta-score)
            if factor < 0:
                raise ValueError('negative betting factor cannot be evidence')
            if factor == 0:
                total = D('-Infinity')
            elif total.is_finite():
                total += (D(factor.numerator)/D(factor.denominator)).ln()
            result.append(total)
        return result


def scores_from_queues(queues, query, chosen, other, retry_cost):
    needed, table, lower, upper = specification(query, chosen, other, retry_cost)
    n = min((len(queues[operator]) for operator in needed), default=0)
    scores = [table[tuple(queues[operator][index] for operator in needed)] for index in range(n)]
    return needed, scores, lower, upper


def expectation(query, chosen, other, retry_cost, kernel):
    needed, table, _, _ = specification(query, chosen, other, retry_cost)
    result = F(0)
    for categories, score in table.items():
        probability = F(1)
        for operator, category in zip(needed, categories):
            probability *= kernel[operator][category]
        result += probability*score
    return result


def audit_comparison(queues, case, query, chosen, other, saved, statistics, kernel, check):
    """Check observable evidence and legal outward bounds before true scoring."""
    needed, scores, lower, upper = scores_from_queues(queues, query, chosen, other, case['retry_cost'])
    bets = predictable_bets(scores, lower, upper)
    units = [int(score*20) for score in scores]
    retry = F(case['retry_cost']) if 'DETOUR_RETRY' in (chosen, other) else None
    check('fixed_comparison_statistics', statistics['query'] == query and statistics['chosen'] == chosen
          and statistics['other'] == other and (F(statistics['retry_cost']) if statistics['retry_cost'] is not None else None) == retry)
    check('only_necessary_actual_rows', statistics['required_rows'] == list(needed)
          and saved['required_rows'] == list(needed))
    check('exact_complete_score_support', list(map(F, statistics['score_bounds'])) == [lower, upper]
          and list(map(F, saved['score_bounds'])) == [lower, upper])
    check('actual_complete_pair_count', statistics['n'] == saved['n'] == len(scores))
    check('exact_score_histogram', {int(key): value for key, value in statistics['score_histogram'].items()} == dict(Counter(units)))
    check('exact_score_moments', statistics['score_sum_units'] == sum(units)
          and statistics['score_square_sum_units'] == sum(value*value for value in units))
    check('predictable_zero_bets', statistics['zero_bets'] == sum(bet == 0 for bet in bets))
    check('legal_predictable_bet_domain', all(F(0) <= bet <= 1/(upper-lower) for bet in bets)
          if upper != lower else all(bet == 0 for bet in bets))
    cost, theta = operating_constant(case, chosen, other), THRESHOLD-operating_constant(case, chosen, other)
    check('operating_cost_changes_only_null', F(saved['constant_gap']) == cost and F(saved['theta']) == theta)
    check('frozen_event_threshold', saved['threshold'] == EVENT_THRESHOLD)
    true_mean = expectation(query, chosen, other, case['retry_cost'], kernel)
    pure = vectors(case, kernel)
    true_gap = utility(pure[other], WEIGHTS[query])-utility(pure[chosen], WEIGHTS[query])
    check('paired_score_is_unbiased_complete_gap', true_mean+cost == true_gap)
    if theta >= upper:
        expected, kind = True, 'score_range'
    elif theta < lower:
        expected, kind = False, 'below_score_range'
    else:
        kind = 'bounded_mean_bet'
        logs = independent_logs(scores, bets, theta)
        value = logs[-1] if logs else D(0)
        saved_log, saved_product = D(saved['log_e_lower']), D(saved['e_lower'])
        with localcontext() as context:
            context.prec = 100
            threshold_log = D(EVENT_THRESHOLD).ln()
            check('outward_lower_e_log', saved_log <= value+D('1e-85'))
            check('outward_lower_e_product', saved_product >= 0 and (
                saved_product == 0 if not value.is_finite() else saved_product.ln() <= value+D('1e-85')))
            check('outward_threshold_log', D(saved['log_threshold_upper']) >= threshold_log-D('1e-85'))
            expected = saved_log > D(saved['log_threshold_upper'])
            check('no_false_true_gap_certificate', not expected or true_gap <= THRESHOLD)
        # This is a retained-stream diagnostic, not a guarantee checked by
        # post-hoc selection: the all-m event is established mathematically.
        true_logs = independent_logs(scores, bets, true_mean)
        with localcontext() as context:
            context.prec = 100
            true_event_ok = max([D(0)]+true_logs) < D(EVENT_THRESHOLD).ln()
    if kind != 'bounded_mean_bet':
        check('analytic_support_uses_no_evidence_product', saved['log_e_lower'] is None
              and saved['e_lower'] is None and saved['log_threshold_upper'] is None)
        check('no_false_true_gap_certificate', not expected or true_gap <= THRESHOLD)
        true_logs = independent_logs(scores, bets, true_mean) if scores else []
        with localcontext() as context:
            context.prec = 100
            true_event_ok = max([D(0)]+true_logs) < D(EVENT_THRESHOLD).ln()
    check('exact_certification_status', saved['kind'] == kind and saved['certified'] == expected)
    return dict(certified=expected, true_gap=true_gap, true_mean_event_ok=true_event_ok, pairs=len(scores))


def _draw(generator, kernel, operator, amount):
    result = []
    for _ in range(amount):
        value, cumulative = generator.random(), F(0)
        for category in ALPHABETS[operator]:
            cumulative += kernel[operator][category]
            if value < float(cumulative):
                result.append(category)
                break
    return result


def reconstruct(selected, check):
    """Reconstruct all actual prefixes before inspecting V233 certificates."""
    source_records = load(INPUT/'source_records.json')
    wanted = {(row['life'], row['index'], row['arm']) for row in selected}
    snapshots, total_target_samples = {}, 0
    for life in (0, 1, 2):
        cases, laws, identities, metadata = world(life)
        sources = {context: [empty() for _ in range(3)] for context in ('A', 'B')}
        generators = {}
        for batch in (row for row in source_records if row['life'] == life):
            operator, index, slot = batch['operator'], batch['index'], batch['slot']
            seed = 262000+(life*6+slot)*3+OPERATORS.index(operator)
            key = batch['context'], index, operator
            generator = generators.setdefault(key, random.Random(seed))
            queue = sources[batch['context']][identities[index]][operator]
            check('source_seed_and_cursor', batch['seed'] == seed and batch['draw_start'] == len(queue))
            values = _draw(generator, laws[index], operator, 16)
            check('source_actual_increment', dict(Counter(values)) == {
                category: count for category, count in batch['increments'].items() if count})
            queue.extend(values)
            check('source_terminal_cursor', batch['draw_end'] == len(queue))
        check('fixed_source_actual_lengths', all(len(group[operator]) == (384 if context == 'A' else 128)
              for context, groups in sources.items() for group in groups for operator in OPERATORS))
        rows = read_rows(INPUT/f'records_life_{life:02d}.jsonl.gz')
        for arm in ARMS:
            a = deepcopy(sources['A'])
            b = None
            history_paid = 0
            for row in sorted((item for item in rows if item['arm'] == arm), key=lambda item: item['index']):
                index, identity = row['index'], row['identity']
                check('target_fixed_roster', row['case'] == cases[index] and identity == identities[index])
                if cases[index]['context'] == 'B' and b is None:
                    b = deepcopy(sources['B'])
                    for group in range(3):
                        for operator in OPERATORS:
                            if operator != metadata['changed_operator']:
                                b[group][operator] = a[metadata['b_to_a'][group]][operator]+b[group][operator]
                group = (a if cases[index]['context'] == 'A' else b)[identity]
                generators = {operator: random.Random(263000+(life*78+index)*3+j)
                              for j, operator in enumerate(OPERATORS)}
                cursors = dict.fromkeys(OPERATORS, 0)
                member = {operator: Counter() for operator in OPERATORS}
                for batch in row['batches']:
                    operator = batch['operator']
                    seed = 263000+(life*78+index)*3+OPERATORS.index(operator)
                    check('target_seed_and_cursor', row['seeds'][operator] == seed
                          and batch['draw_start'] == cursors[operator])
                    values = _draw(generators[operator], laws[index], operator, 16)
                    check('target_actual_increment', Counter(values) == Counter(batch['increments']))
                    group[operator].extend(values)
                    member[operator].update(values)
                    cursors[operator] += 16
                    check('target_terminal_cursor', batch['draw_end'] == cursors[operator])
                check('target_actual_fee', sum(cursors.values()) == row['spent'])
                check('target_actual_member', all(member[operator] == Counter(row['member'][operator])
                                                for operator in OPERATORS))
                total_target_samples += row['spent']
                source_paid = 3456 if index < 30 else 4608
                fees = dict(source_paid_samples=source_paid, history_paid_samples=history_paid,
                            current_paid_samples=row['spent'],
                            total_reference_paid_samples=source_paid+history_paid+row['spent'])
                check('retained_cumulative_reference_fees', all(row[key] == value for key, value in fees.items())
                      and row['new_paid_samples'] == row['spent'])
                history_paid += row['spent']
                key = life, index, arm
                if key in wanted:
                    fees['evidence_samples'] = sum(map(len, group.values()))
                    snapshots[key] = dict(queues=deepcopy(group), case=cases[index],
                                          identity=identity, law=laws[index], fees=fees,
                                          member={operator: dict(member[operator]) for operator in OPERATORS},
                                          changed_operator=metadata['changed_operator'])
    check('all_fixed_snapshots_reconstructed', set(snapshots) == wanted)
    return snapshots, total_target_samples


def audit_provenance(tape, check):
    context, changed = tape['case']['context'], tape['changed_operator']
    for operator, segments in tape['provenance'].items():
        cursor, previous_order, seen_b = 0, -1, False
        for segment in segments:
            amount = segment['draw_end']-segment['draw_start']
            check('provenance_actual_queue_interval', segment['queue_start'] == cursor
                  and segment['queue_end'] == cursor+amount and amount == 16)
            check('provenance_availability_order', segment['availability_order'] > previous_order)
            previous_order, cursor = segment['availability_order'], cursor+amount
            check('provenance_operator_and_life', segment['operator'] == operator and segment['life'] == tape['life'])
            if segment['kind'] == 'source':
                index = segment['index']
                slot = index if segment['context'] == 'A' else index-24
                seed = 262000+(tape['life']*6+slot)*3+OPERATORS.index(operator)
            else:
                seed = 263000+(tape['life']*78+segment['index'])*3+OPERATORS.index(operator)
                check('provenance_own_arm_only', segment['arm'] == tape['arm'])
                check('provenance_no_future_target', segment['index'] <= tape['index'])
            check('provenance_frozen_seed', segment['seed'] == seed)
            if context == 'A':
                check('return_uses_only_a_event', segment['context'] == 'A')
            elif operator == changed:
                check('changed_operator_excludes_a', segment['context'] == 'B')
            else:
                check('unchanged_operator_splice_order', not seen_b or segment['context'] == 'B')
                seen_b |= segment['context'] == 'B'
                check('inherited_a_stops_before_switch', segment['context'] != 'A' or segment['index'] < 27)
        check('provenance_covers_complete_queue', cursor == len(tape['operators'][operator]))


def run():
    begun, counts, failures = perf_counter(), Counter(), []
    def check(name, valid):
        counts[name] += 1
        if not valid:
            failures.append(dict(check=name, location=location.copy()))
    location = {}
    protocol = load(OUTPUT/'run.json')
    previous = read_rows(ROOT/'reports/kernel_query_profile_v232/inputs.jsonl.gz')
    key = lambda row: (row['life'], row['index'], row['arm'])
    old = {key(row): row for row in previous}
    tapes, records = read_rows(OUTPUT/'tapes.jsonl.gz'), read_rows(OUTPUT/'records.jsonl.gz')
    check('frozen_24_terminal_roster', [key(row) for row in tapes] == [key(row) for row in previous]
          == [key(row) for row in records] and len(records) == 24)
    check('frozen_protocol_budget_and_order', protocol['stream_count'] == 216 and protocol['threshold'] == 4320
          and protocol['delta_per_life_arm'] == '1/20' and protocol['bet_anchor'] == '1/20'
          and protocol['phases'] == ['protocol_frozen', 'tapes_frozen', 'certificates_frozen', 'oracle_evaluated', 'complete']
          and protocol['complete'] and not protocol['scientific_gate_changed']
          and protocol['new_observations'] == protocol['new_paid_samples'] == 0)
    expected, target_samples = reconstruct(previous, check)
    scored = {key(row): row for row in load(OUTPUT/'scores.json')}
    false_certificates, tested_true_mean_failures, paired_counts, unpaired_counts = 0, 0, [], []
    cache_keys, unique_streams, cache_hits = set(), 0, 0
    for tape, row in zip(tapes, records):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'])
        rebuilt = expected[key(row)]
        check('exact_actual_operator_queue_order', tape['operators'] == rebuilt['queues'])
        check('exact_snapshot_scope_and_fees', tape['case'] == row['case'] == rebuilt['case']
              and tape['identity'] == row['identity'] == rebuilt['identity']
              and tape['fees'] == row['fees'] == rebuilt['fees']
              and tape['changed_operator'] == rebuilt['changed_operator'])
        check('snapshot_has_no_new_acquisition', tape['new_observations'] == tape['new_paid_samples']
              == row['new_observations'] == row['new_paid_samples'] == 0)
        check('retained_actual_member_order_counts', all(Counter(tape['member'][operator]) ==
              Counter(rebuilt['member'][operator]) for operator in OPERATORS))
        check('exact_effective_operator_lengths', row['row_lengths'] == {
            operator: len(values) for operator, values in rebuilt['queues'].items()})
        audit_provenance(tape, check)
        chosen = old[key(row)]['terminal_plan']['queries']
        check('old_status_not_rejudged', row['old_query_ready'] == old[key(row)]['terminal_plan']['query_ready'])
        check('unchanged_selected_policies', all(row['queries'][query]['policy'] == decision['policy']
                                               for query, decision in chosen.items()))
        reward = row['queries']['reward']
        check('analytic_reward_cost_certificate', reward == dict(policy='WAIT', certified=True,
              kind='known_nonnegative_cost') and chosen['reward']['policy'] == 'WAIT')
        row_unique, row_hits = 0, 0
        for query in ('goal', 'risk'):
            decision = row['queries'][query]
            comparisons = decision['comparisons']
            check('complete_ordered_alternative_roster', [item['other'] for item in comparisons]
                  == [policy for policy in POLICIES if policy != decision['policy']])
            statuses = []
            for comparison in comparisons:
                location['query'], location['other'] = query, comparison['other']
                outcome = audit_comparison(rebuilt['queues'], row['case'], query, decision['policy'],
                    comparison['other'], comparison, comparison, rebuilt['law'], check)
                statuses.append(outcome['certified'])
                tested_true_mean_failures += not outcome['true_mean_event_ok']
                paired_counts.append(outcome['pairs'])
                unpaired_counts.append(sum(len(rebuilt['queues'][operator])-outcome['pairs']
                                           for operator in comparison['required_rows']))
                stream_key = (query, decision['policy'], comparison['other'], comparison['retry_cost'],
                              tuple((operator, tuple(rebuilt['queues'][operator]))
                                    for operator in comparison['required_rows']))
                if stream_key in cache_keys:
                    row_hits += 1
                else:
                    row_unique += 1
                    cache_keys.add(stream_key)
            check('single_query_all_comparisons_and', decision['certified'] == all(statuses))
        check('all_three_queries_and', row['query_ready'] == all(d['certified'] for d in row['queries'].values()))
        check('reported_cache_cost', row['unique_score_streams'] == row_unique and row['score_cache_hits'] == row_hits)
        unique_streams += row_unique
        cache_hits += row_hits
        pure = vectors(row['case'], rebuilt['law'])
        regrets = {query: max(utility(vector, WEIGHTS[query]) for vector in pure.values())
                   -utility(pure[decision['policy']], WEIGHTS[query]) for query, decision in row['queries'].items()}
        false = sum(row['queries'][query]['certified'] and value > THRESHOLD for query, value in regrets.items())
        false_certificates += false
        check('exact_postfreeze_truth_scores', {query: F(value) for query, value in scored[key(row)]['regrets'].items()}
              == regrets and scored[key(row)]['false_certificates'] == false)
        print(f'audited life={row["life"]} index={row["index"]} arm={row["arm"]}', flush=True)
    location = {}
    summary, replay = load(OUTPUT/'summary.json'), load(OUTPUT/'replay_summary.json')
    check('exact_global_zero_draw_and_false_certificates', summary['new_observations'] == summary['new_paid_samples'] == 0
          and summary['false_certificates'] == false_certificates == 0 and summary['records'] == 24)
    check('exact_replayed_paid_sample_totals', replay['replayed_target_samples'] == target_samples
          and replay['replayed_physical_source_samples'] == 13824)
    check('exact_global_cache_cost', summary['unique_score_streams'] == unique_streams
          and summary['score_cache_hits'] == cache_hits)
    for kind in ('failure', 'positive'):
        group, relevant = summary['groups'][kind], [row for row in records if row['kind'] == kind]
        check('exact_group_status_summary', group['targets'] == len(relevant)
              and group['old_query_ready'] == sum(row['old_query_ready'] for row in relevant)
              and group['v232_query_ready'] == sum(row['v232_query_ready'] for row in relevant)
              and group['query_ready'] == sum(row['query_ready'] for row in relevant)
              and group['queries'] == {query: sum(row['queries'][query]['certified'] for row in relevant)
                                      for query in WEIGHTS})
        for arm in ARMS:
            ar = [row for row in relevant if row['arm'] == arm]
            check('exact_method_status_summary', group['arms'][arm] == dict(targets=len(ar), query_ready=sum(row['query_ready'] for row in ar)))
    result = dict(valid=not failures, records=len(records), comparisons=len(paired_counts),
                  checks=dict(counts), failures=failures, false_certificates=false_certificates,
                  retained_tested_true_mean_event_failures=tested_true_mean_failures,
                  paired_n_range=[min(paired_counts), max(paired_counts)],
                  paired_n_total=sum(paired_counts), unpaired_relevant_total=sum(unpaired_counts),
                  replayed_target_samples=target_samples, replayed_physical_source_samples=13824,
                  new_observations=0, new_paid_samples=0, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    run()
