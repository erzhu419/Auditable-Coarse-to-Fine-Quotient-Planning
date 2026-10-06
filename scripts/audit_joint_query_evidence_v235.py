"""Independent exact likelihood arithmetic for the frozen V235 diagnostic.

No V235 producer is imported.  Predictive recurrences reconstruct the ordered
Jeffreys/Dirichlet mixture; comparisons and route gaps remain exact rationals.
"""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from decimal import Decimal as Decimal, localcontext
import gzip
import json
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/joint_query_evidence_v235'
S, D, R = 'SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY'
ALPHABETS = {S: ('DELIVERY', 'LOST'),
             D: ('DELIVERY', 'LOST', 'RECOVERY'),
             R: ('DELIVERY', 'LOST')}
FAMILY_ROWS = {
    'S': ((S, 'DELIVERY'),),
    'D_DEL': ((D, 'DELIVERY'),),
    'D_FULL': ((D, None),),
    'D_FULL_R': ((D, None), (R, 'DELIVERY')),
    'S_D_DEL': ((S, 'DELIVERY'), (D, 'DELIVERY')),
    'S_D_FULL': ((S, 'DELIVERY'), (D, None)),
    'S_D_FULL_R': ((S, 'DELIVERY'), (D, None), (R, 'DELIVERY')),
    'D_REC_R': ((D, 'RECOVERY'), (R, 'DELIVERY')),
}
ROW_NAMES = {(S, 'DELIVERY'): 'S', (D, 'DELIVERY'): 'D_DEL',
             (D, None): 'D_FULL', (R, 'DELIVERY'): 'R',
             (D, 'RECOVERY'): 'D_REC'}
THRESHOLD, REGRET = 960, F(1, 20)


@lru_cache(maxsize=None)
def predictive_weight(counts):
    """Probability of one ordered categorical sample under Dirichlet(.5)."""
    weight, total = F(1), 0
    dimension = len(counts)
    for count in counts:
        for previously_seen in range(count):
            weight *= F(2*previously_seen+1, 2*total+dimension)
            total += 1
    return weight


def likelihood_ratio(counts, probabilities):
    counts, probabilities = tuple(counts), tuple(map(F, probabilities))
    if len(counts) != len(probabilities) or sum(probabilities) != 1:
        raise ValueError('categorical probabilities must form the same simplex')
    denominator = F(1)
    for count, probability in zip(counts, probabilities):
        if count < 0 or probability < 0:
            raise ValueError('counts and probabilities must be nonnegative')
        denominator *= probability**count
    return predictive_weight(counts)/denominator if denominator else None


def projected_row(raw_counts, raw_probabilities, operator, success):
    if success is None:
        alphabet = ALPHABETS[operator]
        return (tuple(raw_counts.get(category, 0) for category in alphabet),
                tuple(F(raw_probabilities[category]) for category in alphabet))
    k, n = raw_counts.get(success, 0), sum(raw_counts.values())
    probability = F(raw_probabilities[success])
    return (k, n-k), (probability, 1-probability)


def family_value(family, counts, kernel):
    result = F(1)
    for operator, success in FAMILY_ROWS[family]:
        projected_counts, probabilities = projected_row(
            counts[operator], kernel[operator], operator, success)
        value = likelihood_ratio(projected_counts, probabilities)
        if value is None:
            return None
        result *= value
    return result


def named_projection(family, counts, kernel):
    """Return named sufficient counts/parameters for record comparison."""
    projected_counts, projected_parameters = {}, {}
    for operator, success in FAMILY_ROWS[family]:
        name = ROW_NAMES[operator, success]
        row_counts, probabilities = projected_row(counts[operator], kernel[operator], operator, success)
        categories = ALPHABETS[operator] if success is None else (
            success, 'OTHER' if operator == D else 'LOST')
        projected_counts[name] = dict(zip(categories, row_counts))
        projected_parameters[name] = dict(zip(categories, probabilities))
    return projected_counts, projected_parameters


def data_equivalence(family, projected_counts, prefixes):
    full_mask = all(success is None or operator != D
                    for operator, success in FAMILY_ROWS[family])
    required = [operator for operator, _ in FAMILY_ROWS[family]]
    comparisons = []
    for prefix in prefixes:
        counts = prefix['counts']
        relevant = {}
        for operator, success in FAMILY_ROWS[family]:
            raw = counts.get(operator, dict.fromkeys(ALPHABETS[operator], 0))
            name = ROW_NAMES[operator, success]
            if success is None:
                relevant[name] = {category: raw.get(category, 0) for category in ALPHABETS[operator]}
            else:
                category = 'OTHER' if operator == D else 'LOST'
                relevant[name] = {success: raw.get(success, 0),
                                  category: sum(raw.values())-raw.get(success, 0)}
        same_mask = full_mask and set(prefix['operators']) == set(required)
        same_counts = relevant == projected_counts
        comparisons.append(dict(prefix=prefix['name'], threshold=prefix['threshold'],
            operators=prefix['operators'], relevant_projected_counts=relevant,
            same_projection_mask=same_mask, same_projected_counts=same_counts,
            equivalent_evidence=same_mask and same_counts,
            same_region=same_mask and same_counts and prefix['threshold'] == THRESHOLD))
    return comparisons


def audit_membership(value, saved, check):
    """The decision uses exact fractions; logarithms are only compact output."""
    inside = value is not None and value <= THRESHOLD
    check('exact_joint_ratio_decision', saved['threshold'] == THRESHOLD
          and saved['exact_inside'] == inside and saved['excluded'] == (not inside))
    if value is None:
        logs_ok = saved['log_lr_lower'] == saved['log_lr_upper'] == 'Infinity'
    else:
        with localcontext() as context:
            context.prec = 120
            exact_log = (Decimal(value.numerator)/Decimal(value.denominator)).ln()
            logs_ok = (Decimal(saved['log_lr_lower']) <= exact_log+Decimal('1e-110')
                       and Decimal(saved['log_lr_upper']) >= exact_log-Decimal('1e-110'))
    with localcontext() as context:
        context.prec = 120
        exact_threshold = Decimal(THRESHOLD).ln()
        logs_ok &= (Decimal(saved['log_threshold_lower']) <= exact_threshold
                    and Decimal(saved['log_threshold_upper']) >= exact_threshold)
    check('compact_outward_log_intervals', logs_ok)
    return inside


def relevant_family(query, chosen, alternative):
    pair = {chosen, alternative}
    if pair == {'DETOUR_RETURN', 'DETOUR_RETRY'}:
        return 'D_REC_R'
    has_short = 'SHORT' in pair
    if 'DETOUR_RETRY' in pair:
        return 'S_D_FULL_R' if has_short else 'D_FULL_R'
    has_detour = 'DETOUR_RETURN' in pair
    if has_detour:
        return ('S_D_DEL' if has_short else 'D_DEL') if query == 'goal' else (
            'S_D_FULL' if has_short else 'D_FULL')
    return 'S'


def utility(case, query, policy, kernel):
    short_cost, detour_cost = ((F(1, 10), F(1, 20)) if case['operating'] == 'low'
                               else (F(3, 25), F(7, 100)))
    loss_weight, delivery_weight = {'reward': (0, 0), 'goal': (0, 4), 'risk': (4, 4)}[query]
    if policy == 'WAIT':
        return F(0)
    if policy == 'SHORT':
        delivery = F(kernel[S]['DELIVERY'])
        return -short_cost+delivery_weight*delivery-loss_weight*(1-delivery)
    row = {category: F(value) for category, value in kernel[D].items()}
    value = -detour_cost+delivery_weight*row['DELIVERY']-loss_weight*row['LOST']
    if policy == 'DETOUR_RETRY':
        retry = F(kernel[R]['DELIVERY'])
        value += row['RECOVERY']*(delivery_weight*retry-loss_weight*(1-retry)-F(case['retry_cost']))
    return value


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def load(path):
    return json.loads(path.read_text())


def run():
    started, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    previous, shared = ROOT/'reports/kernel_query_profile_v232', ROOT/'reports/shared_prefix_score_v234'
    protocol, saved, summary = (load(OUTPUT/name) for name in (
        'protocol.json', 'records.json', 'summary.json'))
    old_audit, tape_audit = load(previous/'countermodel_analysis.json'), load(shared/'analysis.json')
    check('previous_accepted_evidence_valid', old_audit['valid'] and tape_audit['valid']
          and old_audit['verified_countermodels'] == 12)
    key = lambda row: (row['life'], row['index'], row['arm'])
    tapes = {key(row): row for row in read_rows(shared/'tapes.jsonl.gz')}
    old_records = {key(row): row for row in read_rows(previous/'records.jsonl.gz')}
    countermodels = [row for row in load(previous/'countermodels.json') if row['found']]
    diagnosis = load(shared/'diagnosis.json')
    rectangles = diagnosis['terminal_rectangle_witnesses']
    selected = [(row, 'V232_countermodel') for row in countermodels]+[
        (row, 'V234_rectangle') for row in rectangles]
    roster = [dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')}, origin=origin)
              for row, origin in selected]
    check('fixed_fifteen_relevant_witnesses', len(tapes) == 24 and len(saved) == len(selected) == 15
          and len(countermodels) == 12 and len(rectangles) == 3
          and protocol['selected'] == roster
          and [(key(row), row['origin']) for row in saved] == [(key(row), origin) for row, origin in selected])
    expected_families = {name: [ROW_NAMES[row] for row in rows] for name, rows in FAMILY_ROWS.items()}
    check('fixed_shared_event_budget', protocol['families'] == expected_families
          and protocol['family_count'] == 8 and protocol['event_count_per_life_arm'] == 48
          and protocol['delta_per_life_arm'] == '1/20' and protocol['threshold'] == THRESHOLD)
    check('fixed_diagnostic_stage_and_claim_scope', protocol['complete']
          and protocol['phases'] == ['protocol_frozen', 'evidence_frozen', 'witnesses_checked', 'complete']
          and protocol['witness_feasibility_only'] and protocol['qualification_only']
          and protocol['new_observations'] == protocol['new_paid_samples'] == 0
          and not protocol['scientific_gate_changed'] and not protocol['query_certificates_obtained'])
    admitted, results, matches, mask_matches, comparisons = 0, {}, 0, 0, 0
    group_rows = {'V232_countermodel': [], 'V234_rectangle': []}
    for (witness, origin), row in zip(selected, saved):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'], origin=origin)
        tape = tapes[key(witness)]
        chosen = witness['chosen_policy'] if origin == 'V232_countermodel' else witness['chosen']
        other = witness['alternative_policy'] if origin == 'V232_countermodel' else witness['other']
        family = relevant_family(witness['query'], chosen, other)
        raw_counts = {operator: dict(Counter(values)) for operator, values in tape['operators'].items()}
        if origin == 'V232_countermodel':
            kernel, old_gap = witness['kernel'], F(witness['regret'])
            gap = utility(tape['case'], witness['query'], other, kernel)-utility(
                tape['case'], witness['query'], chosen, kernel)
        else:
            p, q = F(witness['p']), F(witness['q'])
            kernel, old_gap = {D: {'RECOVERY': p}, R: {'DELIVERY': q}}, F(witness['gap'])
            sign = 1 if other == 'DETOUR_RETRY' else -1
            continuation = (4*q if witness['query'] == 'goal' else 8*q-4)-F(tape['case']['retry_cost'])
            gap = sign*p*continuation
        counts, parameters = named_projection(family, raw_counts, kernel)
        check('original_snapshot_policy_fees_unchanged', all(row[field] == tape[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees'))
            and row['origin'] == origin and row['query'] == witness['query']
            and row['chosen'] == chosen and row['other'] == other)
        check('canonical_needed_projection_full_paid_counts', row['family'] == family
              and row['projected_counts'] == counts and {
                  name: {cat: F(value) for cat, value in parameter_row.items()}
                  for name, parameter_row in row['parameters'].items()} == parameters)
        check('exact_retained_bad_gap', gap == old_gap == F(row['previously_reported_gap']) == F(row['gap'])
              and gap > REGRET and row['gap_above_regret'])
        expected_comparison = data_equivalence(family, counts, old_records[key(witness)]['prefixes'])
        check('literal_prior_mask_counts_and_prior_comparison', row['data_comparison'] == expected_comparison)
        value = family_value(family, raw_counts, kernel)
        inside = audit_membership(value, row['membership'], check)
        if origin == 'V234_rectangle':
            check('original_terminal_rectangle_witness_valid', family == 'D_REC_R'
                  and all(likelihood_ratio(tuple(counts[name].values()), tuple(parameters[name].values())) <= 3600
                          for name in ('D_REC', 'R')))
        check('witness_only_interpretation', row['interpretation'] == (
            'admitted_bad_witness_prevents_this_query_certificate' if inside else 'excluded_fixed_witness_only')
            and row['new_observations'] == row['new_paid_samples'] == 0)
        group_rows[origin].append((row['kind'], inside))
        if origin == 'V232_countermodel':
            results[key(row)] = inside
        admitted += inside
        matches += sum(item['equivalent_evidence'] for item in expected_comparison)
        mask_matches += sum(item['same_projection_mask'] for item in expected_comparison)
        comparisons += len(expected_comparison)
    groups = {origin: dict(witnesses=len(rows), admitted=sum(inside for _, inside in rows),
        excluded=sum(not inside for _, inside in rows), by_kind={kind: dict(
            witnesses=sum(k == kind for k, _ in rows),
            admitted=sum(k == kind and inside for k, inside in rows),
            excluded=sum(k == kind and not inside for k, inside in rows)) for kind in ('failure', 'positive')})
        for origin, rows in group_rows.items()}
    check('exact_diagnostic_summary', summary['complete'] and summary['records'] == 15
          and summary['groups'] == groups and summary['admitted'] == admitted
          and summary['excluded'] == 15-admitted and summary['exact_prior_mask_and_count_matches'] == matches
          and summary['exact_prior_mask_matches'] == mask_matches and summary['prior_comparisons'] == comparisons
          and summary['new_observations'] == summary['new_paid_samples'] == 0
          and not summary['query_certificates_obtained'] and not summary['scientific_gate_changed'])
    main_blockers = [row for row in diagnosis['original_seven_short_return_risk_blockers']
                    if not row['v234_certified']]
    retained_main = [row for row in main_blockers if key(row) in results]
    allowed = len(retained_main) == 5 and all(not results[key(row)] for row in retained_main)
    check('fixed_main_bottleneck_continuation_rule', len(main_blockers) == 6 and len(retained_main) == 5)
    main_admitted = sum(results[key(row)] for row in retained_main)
    missing = [dict(life=life, index=index, arm=arm) for life, index, arm in sorted(
        {key(row) for row in main_blockers}-{key(row) for row in retained_main})]
    check('primary_roster_and_eligibility_summary', summary['primary_risk_blockers'] == dict(
        cases=6, retained_witnesses=5, admitted=main_admitted, excluded=5-main_admitted,
        without_retained_witness=missing) and summary['full_qualification_eligible'] == allowed
        and summary['qualification_status'] == ('eligible_not_run' if allowed
            else 'skipped_primary_bad_witness_still_admitted')
        and not summary['full_bad_null_solver_implemented'])
    result = dict(valid=not failures, complete=True, records=15, exact_joint_membership_checks=15,
        admitted=admitted, excluded=15-admitted, groups=groups,
        original_terminal_rectangle_witness_checks=3,
        exact_prior_mask_and_count_matches=matches, prior_comparisons=comparisons,
        main_risk_blockers=6, main_risk_retained_witnesses=5,
        main_risk_admitted=main_admitted,
        full_qualification_allowed=allowed, new_observations=0, new_paid_samples=0,
        query_certificates_obtained=False, checks=dict(checks), failures=failures,
        seconds=perf_counter()-started)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
