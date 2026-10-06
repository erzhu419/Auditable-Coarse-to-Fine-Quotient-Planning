"""Independent paid-prefix and exact joint-region audit for frozen V244.

Only retained observations and public costs are read. No V244 producer, route
world, optimizer, saved outcome score, or true probability is imported.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import gzip
import json
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports/bidirectional_lifecycle_v243'
OUTPUT = ROOT / 'reports/goal_joint_region_v244'
S, D, R = 'SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY'
OPERATORS = (S, D, R)
ALPHABETS = {S: ('DELIVERY', 'LOST'),
             D: ('DELIVERY', 'LOST', 'RECOVERY'),
             R: ('DELIVERY', 'LOST')}
FAMILIES = {
    'S': ((S, 'DELIVERY'),), 'D_DEL': ((D, 'DELIVERY'),),
    'D_FULL': ((D, None),), 'D_FULL_R': ((D, None), (R, 'DELIVERY')),
    'S_D_DEL': ((S, 'DELIVERY'), (D, 'DELIVERY')),
    'S_D_FULL': ((S, 'DELIVERY'), (D, None)),
    'S_D_FULL_R': ((S, 'DELIVERY'), (D, None), (R, 'DELIVERY')),
    'D_REC_R': ((D, 'RECOVERY'), (R, 'DELIVERY')),
}
ROW_NAMES = {(S, 'DELIVERY'): 'S', (D, 'DELIVERY'): 'D_DEL',
             (D, None): 'D_FULL', (R, 'DELIVERY'): 'R',
             (D, 'RECOVERY'): 'D_REC'}
REGRET, STRICT_GAP, QUERY_THRESHOLD = F(1, 20), F(50001, 1000000), 960
STATUSES = ('unknown', 'paid_constraints_reject_candidate', 'full_region_bad_witness')


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def exact(value):
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [exact(item) for item in value]
    if isinstance(value, str):
        try:
            return F(value)
        except ValueError:
            return value
    return value


def empty():
    return {operator: dict.fromkeys(categories, 0) for operator, categories in ALPHABETS.items()}


@lru_cache(maxsize=None)
def normalizer(counts):
    """Rising half factors as integer odd products, independent of factorial code."""
    numerator = denominator = 1
    for count in counts:
        for position in range(count):
            numerator *= 2 * position + 1
    for position in range(sum(counts)):
        denominator *= len(counts) + 2 * position
    return F(numerator, denominator)


def membership(projected_counts, projected_parameters, threshold):
    mixture = likelihood = F(1)
    for name, counts in projected_counts.items():
        mixture *= normalizer(tuple(counts.values()))
        for category, count in counts.items():
            likelihood *= F(projected_parameters[name][category]) ** count
    inside = mixture <= F(threshold) * likelihood
    return dict(exact_inside=inside, excluded=not inside, threshold=int(threshold)), (
        mixture / likelihood if likelihood else None)


def projection(family, counts, kernel):
    projected_counts, parameters = {}, {}
    for operator, category in FAMILIES[family]:
        name = ROW_NAMES[operator, category]
        if category is None:
            projected_counts[name] = {item: counts[operator][item] for item in ALPHABETS[operator]}
            parameters[name] = {item: F(kernel[operator][item]) for item in ALPHABETS[operator]}
        else:
            other = 'OTHER' if operator == D else 'LOST'
            count, probability = counts[operator][category], F(kernel[operator][category])
            projected_counts[name] = {category: count, other: sum(counts[operator].values()) - count}
            parameters[name] = {category: probability, other: 1 - probability}
    return projected_counts, parameters


def family_memberships(counts, kernel):
    return {family: membership(*projection(family, counts, kernel), QUERY_THRESHOLD)
            for family in FAMILIES}


def execution_memberships(constraints, kernel):
    result = []
    for operator in OPERATORS:
        for position, constraint in enumerate(constraints[operator]):
            decision, ratio = membership({operator: constraint['counts']},
                                         {operator: kernel[operator]}, constraint['threshold'])
            result.append((dict(operator=operator, position=position, **deepcopy(constraint),
                                membership=decision), ratio))
    return result


def costs(case):
    return (F(1, 10), F(1, 20)) if case['operating'] == 'low' else (F(3, 25), F(7, 100))


def goal_gap(case, kernel):
    short_cost, detour_cost = costs(case)
    return (short_cost - detour_cost + 4 * F(kernel[D]['DELIVERY'])
            + F(kernel[D]['RECOVERY']) * (4 * F(kernel[R]['DELIVERY']) - F(case['retry_cost']))
            - 4 * F(kernel[S]['DELIVERY']))


def simplex(kernel):
    return (kernel is not None and set(kernel) == set(OPERATORS)
            and all(set(kernel[operator]) == set(categories)
                    and all(F(value) >= 0 for value in kernel[operator].values())
                    and sum(map(F, kernel[operator].values())) == 1
                    for operator, categories in ALPHABETS.items()))


def restored_coefficients(case, endpoint):
    return {S: dict(DELIVERY=F(-4), LOST=F(0)),
            D: dict(DELIVERY=F(4), LOST=F(0), RECOVERY=4 * F(endpoint) - F(case['retry_cost']))}


def reconstruct_candidate(certificate, case):
    certificate = exact(certificate)
    kind = certificate['witness_kind']
    result = dict(kind=kind, leaf_index=None, recovered_kernel=None,
                  short_delivery_unclipped=None, repair_applied=False,
                  kernel=None, gap=None, reason=None)

    def unavailable(reason):
        result['reason'] = reason
        return result

    if kind == 'bad_null_mle':
        recovered = deepcopy(certificate['bad_null_kernel'])
    elif kind == 'global_likelihood_dual':
        finite = [(index, leaf) for index, leaf in enumerate(certificate['leaves'])
                  if leaf['log_bad_likelihood_upper'] is not None]
        if not finite:
            return unavailable('no_finite_leaf')
        index, leaf = max(finite, key=lambda item: F(item[1]['log_bad_likelihood_upper']))
        result['leaf_index'] = index
        multiplier = F(leaf['multiplier'])
        coefficients = restored_coefficients(case, leaf['gap_endpoint'])
        counts, recovered = certificate['embedded_counts'], {}
        for operator in (S, D):
            witness, row = leaf['row_witnesses'][operator], counts[operator]
            if witness['kind'] == 'free_simplex':
                return unavailable(f'free_simplex:{operator}')
            if not sum(row.values()):
                return unavailable(f'zero_row:{operator}')
            nu, recovered_row = F(witness['nu']), {}
            for category in ALPHABETS[operator]:
                denominator = nu - multiplier * coefficients[operator][category]
                if denominator <= 0:
                    return unavailable(f'nonpositive_denominator:{operator}:{category}')
                recovered_row[category] = F(row[category]) / denominator
            total = sum(recovered_row.values())
            if total <= 0:
                return unavailable(f'zero_reconstructed_row:{operator}')
            recovered[operator] = {category: value / total for category, value in recovered_row.items()}
        retry_counts = counts[R]
        retry_total = sum(retry_counts.values())
        retry = F(retry_counts['DELIVERY'], retry_total) if retry_total else F(1, 2)
        lo, hi = map(F, leaf['retry_interval'])
        retry = min(hi, max(lo, retry))
        recovered[R] = dict(DELIVERY=retry, LOST=1 - retry)
    else:
        return unavailable('unsupported_witness_kind')
    result['recovered_kernel'] = recovered
    if not simplex(recovered):
        return unavailable('recovered_kernel_not_simplex')
    short_cost, detour_cost = costs(case)
    short = (short_cost - detour_cost + 4 * recovered[D]['DELIVERY']
             + recovered[D]['RECOVERY'] * (4 * recovered[R]['DELIVERY'] - F(case['retry_cost']))
             - STRICT_GAP) / 4
    result.update(short_delivery_unclipped=short, repair_applied=True)
    if not 0 <= short <= 1:
        return unavailable('short_delivery_outside_simplex')
    kernel = deepcopy(recovered)
    kernel[S] = dict(DELIVERY=short, LOST=1 - short)
    gap = goal_gap(case, kernel)
    if not simplex(kernel) or gap <= REGRET:
        result['gap'] = gap
        return unavailable('repair_not_strict_bad_kernel')
    result.update(kernel=kernel, gap=gap)
    return result


def original_constraints(life, index, identity, sources, pool, member):
    result = {}
    for operator in OPERATORS:
        event = f'l{life}/A/pool{identity}/{operator}'
        result[operator] = [
            dict(counts=deepcopy(sources['a'][identity][operator]), threshold=720, event=event),
            dict(counts=deepcopy(pool[operator]), threshold=720, event=event),
            dict(counts=deepcopy(member[operator]), threshold=8640,
                 event=f'l{life}/member{index}/{operator}'),
        ]
    return result


def source_banks(source_records, check):
    banks = {life: {context: [empty() for _ in range(3)] for context in ('a', 'b')}
             for life in range(3)}
    cursors = Counter()
    for row in source_records:
        life, context, slot, operator = row['life'], row['context'], row['slot'], row['operator']
        identity = slot if context == 'A' else slot - 3
        size = 384 if context == 'A' else 128
        key = life, context, identity, operator
        increments = row['increments']
        expected_index = identity if context == 'A' else identity + 27
        check('source_record_literal_batch_and_prefix', 0 <= identity < 3
              and row['index'] == expected_index and set(increments) == set(ALPHABETS[operator])
              and all(isinstance(value, int) and value >= 0 for value in increments.values())
              and sum(increments.values()) == 16 and row['draw_start'] == cursors[key]
              and row['draw_end'] == cursors[key] + 16 <= size)
        cursors[key] += 16
        destination = banks[life][context.lower()][identity][operator]
        for category, count in increments.items():
            destination[category] += count
    check('all_source_prefixes_reconstructed', len(source_records) == 864 and len(cursors) == 54
          and all(cursors[life, context, identity, operator] == (384 if context == 'A' else 128)
                  for life in range(3) for context in ('A', 'B')
                  for identity in range(3) for operator in OPERATORS))
    return banks


def replay_native_pools(life, sources, interface, raw_rows, check):
    """Yield immutable own-arm terminal snapshots before later targets are read."""
    pools = deepcopy(sources)
    identities, previous_index = interface['identities'], -1
    for row in raw_rows:
        if row['arm'] != 'ONE_WAY':
            continue
        index, identity, case = row['index'], row['identity'], row['case']
        check('one_way_chronological_public_identity', row['life'] == life
              and index > previous_index and identity == identities[index])
        previous_index = index
        pool = pools[case['context'].lower()][identity]
        check('own_native_pool_before_target', row['pooled_before'] == pool)
        member, spent = empty(), 0
        for batch in row['batches']:
            operator, increments = batch['operator'], batch['increments']
            start = sum(member[operator].values())
            check('own_paid_batch_offsets', set(increments) == set(ALPHABETS[operator])
                  and all(isinstance(value, int) and value >= 0 for value in increments.values())
                  and sum(increments.values()) == 16 and batch['draw_start'] == start
                  and batch['draw_end'] == start + 16 and batch['spent'] == spent + 16)
            for category, count in increments.items():
                member[operator][category] += count
                pool[operator][category] += count
            spent += 16
        check('own_native_pool_and_member_after_target', row['pooled_after'] == pool
              and row['member'] == member and row['spent'] == spent)
        constraints = (original_constraints(life, index, identity, sources, pool, member)
                       if case['stage'] == 'A_RETURN' else None)
        yield dict(record=row, evidence_counts=deepcopy(pool), member=deepcopy(member),
                   joint_constraints=constraints)


def status(candidate, canonical_inside, all_query_inside, all_execution_inside):
    if not simplex(candidate['kernel']) or candidate['gap'] is None or F(candidate['gap']) <= REGRET:
        return 'unknown'
    if not canonical_inside:
        return 'unknown'
    return ('full_region_bad_witness' if all_query_inside and all_execution_inside
            else 'paid_constraints_reject_candidate')


def log_encloses(value, lower, upper):
    if value is None:
        return lower == upper == 'Infinity'
    if value == 1:
        return Decimal(lower) <= 0 <= Decimal(upper)
    with localcontext() as context:
        context.prec, context.rounding = 120, ROUND_FLOOR
        lo = Decimal(value.numerator) / Decimal(value.denominator)
        context.rounding = ROUND_CEILING
        hi = Decimal(value.numerator) / Decimal(value.denominator)
        lo, hi = lo.ln().next_minus(), hi.ln().next_plus()
    return Decimal(lower) <= lo and Decimal(upper) >= hi


def audit_membership(saved, expected, ratio, check):
    check('exact_joint_mixture_membership', all(saved[field] == expected[field]
          for field in ('exact_inside', 'excluded', 'threshold')))
    check('compact_outward_membership_log', log_encloses(ratio, saved['log_lr_lower'], saved['log_lr_upper'])
          and log_encloses(F(expected['threshold']), saved['log_threshold_lower'], saved['log_threshold_upper']))


def summarize(records):
    def counts(subset):
        counter = Counter(row['status'] for row in subset)
        return {label: counter[label] for label in STATUSES}

    query_rejections, execution_rejections = Counter(), Counter()
    for row in records:
        query_rejections.update(family for family, member in row['query_regions'].items()
                                if member['exact_inside'] is False)
        execution_rejections.update(
            f'{("source", "pool", "member")[event["position"]]}:{event["operator"]}'
            for event in row['execution_regions'] if event['membership']['exact_inside'] is False)
    return dict(complete=True, records=len(records), arm='ONE_WAY',
        comparison=dict(query='goal', chosen='SHORT', other='DETOUR_RETRY'),
        status_counts=counts(records),
        life_summaries=[dict(life=life, records=sum(row['life'] == life for row in records),
            status_counts=counts([row for row in records if row['life'] == life])) for life in range(3)],
        canonical_admitted=sum(row['canonical_inside'] is True for row in records),
        all_query_admitted=sum(row['all_query_inside'] is True for row in records),
        all_execution_admitted=sum(row['all_execution_inside'] is True for row in records),
        query_rejection_counts=dict(sorted(query_rejections.items())),
        execution_rejection_counts=dict(sorted(execution_rejections.items())),
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0,
        posthoc_scoring_calls=0, scientific_gate_changed=False, diagnostic_only=True)


def run():
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    protocol, saved_summary, records = (load(OUTPUT / name) for name in ('run.json', 'summary.json', 'records.json'))
    baseline_run, baseline_audit = load(SOURCE / 'run.json'), load(SOURCE / 'analysis.json')
    check('complete_and_audited_paid_baseline', baseline_run['complete'] and baseline_audit['valid'])
    check('frozen_diagnostic_protocol', protocol['complete'] and protocol['arm'] == 'ONE_WAY'
          and protocol['baseline'] == 'reports/bidirectional_lifecycle_v243'
          and protocol['comparison'] == dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')
          and protocol['query_threshold'] == QUERY_THRESHOLD and F(protocol['strict_gap']) == STRICT_GAP
          and protocol['execution_thresholds'] == 'retained_source720_pool720_member8640'
          and protocol['candidate_rule'] == 'maximum_finite_dual_leaf_first_tie_or_retained_bad_null_mle'
          and protocol['repair'] == 'one_algebraic_SHORT_DELIVERY_update_without_clipping'
          and protocol['data_access'] == 'retained_records_profiles_source_records_interfaces_only'
          and protocol['phases'] == ['protocol_frozen', 'all_endpoints_diagnosed', 'complete'])
    check('no_observation_optimizer_score_or_certificate_added', all(protocol[field] == 0 for field in
          ('new_observations', 'new_optimizer_calls', 'new_query_certificates', 'posthoc_scoring_calls'))
          and protocol['scientific_gate_changed'] is False and protocol['diagnostic_only'] is True)
    check('retained_source_before_execution', all((OUTPUT / 'source_code' / relative).read_bytes()
          == (ROOT / relative).read_bytes() for relative in (
              'scripts/audit_goal_joint_region_v244.py', 'tests/test_goal_joint_region_v244_audit.py',
              'specs/GOAL_JOINT_REGION_V244.md')))
    banks = source_banks(load(SOURCE / 'source_records.json'), check)
    interfaces = {row['life']: row for row in load(SOURCE / 'interfaces.json')}
    selected = []
    for life in range(3):
        location = dict(life=life)
        own_indexes = []
        for snapshot in replay_native_pools(life, banks[life], interfaces[life],
                                           rows(SOURCE / f'records_life_{life:02d}.jsonl.gz'), check):
            row = snapshot['record']
            own_indexes.append(row['index'])
            stage = 'A' if row['index'] < 30 else 'B' if row['index'] < 54 else 'A_RETURN'
            check('public_stage_from_original_paid_record', row['case']['stage'] == stage
                  and row['case']['context'] == ('B' if stage == 'B' else 'A'))
            if row['case']['stage'] != 'A_RETURN':
                continue
            goal = row['terminal_plan']['query_evidence']['queries']['goal']
            if goal['policy'] != 'SHORT':
                continue
            reference = next(item for item in goal['comparisons'] if item['other'] == 'DETOUR_RETRY')
            if reference['certified']:
                continue
            snapshot['reference'] = reference
            selected.append(snapshot)
        check('all_own_native_targets_once', own_indexes == list(range(3, 27)) + list(range(30, 78)))
    selected.sort(key=lambda item: (item['record']['life'], item['record']['index']))
    roster = [dict(life=item['record']['life'], index=item['record']['index'],
                   profile_id=item['reference']['profile_id']) for item in selected]
    check('frozen_complete_twenty_four_roster', len(selected) == len(records) == 24
          and Counter(item['life'] for item in roster) == {0: 8, 1: 8, 2: 8}
          and protocol['roster'] == roster
          and [{field: row[field] for field in ('life', 'index', 'profile_id')} for row in records] == roster)
    profiles = {}
    for life in range(3):
        needed = {item['profile_id'] for item in roster if item['life'] == life}
        profiles[life] = {item['profile_id']: item for item in rows(SOURCE / f'profiles_life_{life:02d}.jsonl.gz')
                          if item['profile_id'] in needed}
        check('retained_profiles_complete', set(profiles[life]) == needed)
    recomputed_records = []
    for snapshot, saved in zip(selected, records):
        row, reference = snapshot['record'], snapshot['reference']
        life, index, case = row['life'], row['index'], row['case']
        location = dict(life=life, index=index, profile_id=reference['profile_id'])
        counts, constraints = snapshot['evidence_counts'], snapshot['joint_constraints']
        plan = row['terminal_plan']
        check('original_frozen_native_terminal', plan['evidence_counts'] == saved['evidence_counts'] == counts
              and plan['joint_constraints'] == saved['joint_constraints'] == constraints
              and saved['case'] == case and saved['identity'] == row['identity']
              and row['member'] == snapshot['member'] and plan['return_transfer'] is None)
        profile = profiles[life][reference['profile_id']]
        certificate = exact(profile['certificate'])
        projected, _ = projection('S_D_FULL_R', counts, {operator: dict.fromkeys(categories, F(1, len(categories)))
                                      for operator, categories in ALPHABETS.items()})
        check('canonical_source_profile_paid_counts_and_direction',
              (certificate['query'], certificate['chosen'], certificate['other'], certificate['family'])
              == ('goal', 'SHORT', 'DETOUR_RETRY', 'S_D_FULL_R')
              and certificate['threshold'] == QUERY_THRESHOLD and certificate['regret_threshold'] == REGRET
              and certificate['projected_counts'] == projected and certificate['embedded_counts'] == counts
              and certificate['certified'] is False
              and profile['case']['operating'] == case['operating']
              and F(profile['case']['retry_cost']) == F(case['retry_cost']))
        candidate = reconstruct_candidate(certificate, case)
        check('one_retained_recovery_and_one_exact_short_repair', exact(saved['candidate']) == candidate)
        if candidate['leaf_index'] is not None:
            leaf = certificate['leaves'][candidate['leaf_index']]
            retry_row = counts[R]
            retry = F(retry_row['DELIVERY'], sum(retry_row.values())) if sum(retry_row.values()) else F(1, 2)
            lo, hi = leaf['retry_interval']
            check('selected_leaf_uses_actual_retry_and_original_goal_coefficients',
                  leaf['retry_likelihood']['probability'] == min(hi, max(lo, retry))
                  and leaf['gap_coefficients'] == restored_coefficients(case, leaf['gap_endpoint']))
        expected = dict(saved, candidate=candidate)
        if candidate['kernel'] is None:
            check('unavailable_candidate_keeps_unknown_and_no_membership', saved['status'] == 'unknown'
                  and all(saved[field] is None for field in ('canonical_inside', 'all_query_inside', 'all_execution_inside'))
                  and saved['query_regions'] == {} and saved['execution_regions'] == [])
            expected.update(canonical_inside=None, all_query_inside=None, all_execution_inside=None,
                            query_regions={}, execution_regions=[], status='unknown')
        else:
            kernel = candidate['kernel']
            check('strict_bad_kernel_at_actual_retry_probability', simplex(kernel)
                  and candidate['gap'] == goal_gap(case, kernel) == STRICT_GAP > REGRET)
            queries = family_memberships(counts, kernel)
            check('all_eight_compatible_query_families_once', set(saved['query_regions']) == set(FAMILIES))
            for family, (decision, ratio) in queries.items():
                audit_membership(saved['query_regions'][family], decision, ratio, check)
            execution = execution_memberships(constraints, kernel)
            check('all_nine_original_full_execution_events_once', len(saved['execution_regions']) == len(execution) == 9)
            for retained, (event, ratio) in zip(saved['execution_regions'], execution):
                check('original_execution_event_counts_position_and_threshold',
                      all(retained[field] == event[field] for field in
                          ('operator', 'position', 'event', 'counts', 'threshold')))
                audit_membership(retained['membership'], event['membership'], ratio, check)
            canonical = queries['S_D_FULL_R'][0]['exact_inside']
            all_query = all(item[0]['exact_inside'] for item in queries.values())
            all_execution = all(item[0]['membership']['exact_inside'] for item in execution)
            label = status(candidate, canonical, all_query, all_execution)
            check('candidate_exclusion_is_not_a_query_certificate',
                  saved['canonical_inside'] is canonical and saved['all_query_inside'] is all_query
                  and saved['all_execution_inside'] is all_execution and saved['status'] == label
                  and 'query_certified' not in saved and 'certificate' not in saved)
            expected.update(canonical_inside=canonical, all_query_inside=all_query,
                all_execution_inside=all_execution, status=label,
                query_regions={family: value[0] for family, value in queries.items()},
                execution_regions=[event for event, _ in execution])
        recomputed_records.append(expected)
    independently_summarized = summarize(recomputed_records)
    check('independently_recomputed_status_and_rejection_summary', all(saved_summary[field] == value
          for field, value in independently_summarized.items()) and saved_summary['elapsed_seconds'] >= 0)
    analysis = dict(valid=not failures, records=len(recomputed_records), checks=dict(checks),
                    failures=failures, elapsed_seconds=perf_counter() - begun,
                    **{field: independently_summarized[field] for field in (
                        'status_counts', 'life_summaries', 'canonical_admitted', 'all_query_admitted',
                        'all_execution_admitted', 'query_rejection_counts', 'execution_rejection_counts')},
                    new_observations=0, new_optimizer_calls=0, new_query_certificates=0,
                    posthoc_scoring_calls=0, scientific_gate_changed=False, diagnostic_only=True)
    (OUTPUT / 'analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
    print(json.dumps(analysis), flush=True)
    return analysis


if __name__ == '__main__':
    if not run()['valid']:
        raise SystemExit(1)
