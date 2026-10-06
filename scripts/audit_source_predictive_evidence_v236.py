"""Independent chronological split and posterior prediction for V236.

The V236 producer is never imported. Predictive likelihood is reconstructed
by sequential normalized updates initialized with the fixed source counts.
"""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence
from scripts import audit_kernel_query_profile_v232 as arithmetic

OUTPUT = ROOT/'reports/source_predictive_evidence_v236'
OPERATORS = tuple(evidence.ALPHABETS)
MAIN = ((0, 58, 'ORACLE_BALANCED'), (0, 58, 'ORACLE_GAP'),
        (1, 56, 'ORACLE_BALANCED'), (1, 56, 'ORACLE_GAP'),
        (2, 55, 'ORACLE_BALANCED'), (2, 55, 'ORACLE_GAP'))


def key(row):
    return row['life'], row['index'], row['arm']


def split_tape(tape):
    """Assign every original row segment using context and physical order."""
    training, validation = {}, {}
    training_segments, validation_segments = {}, {}
    for operator in OPERATORS:
        train_context = 'B' if (tape['case']['context'] == 'B'
                                  and operator == tape['changed_operator']) else 'A'
        training[operator], validation[operator] = [], []
        training_segments[operator], validation_segments[operator] = [], []
        cursor, last_order, validation_started = 0, -1, False
        queue = tape['operators'][operator]
        for segment in tape['provenance'][operator]:
            lo, hi = segment['queue_start'], segment['queue_end']
            if lo != cursor or hi-lo != segment['draw_end']-segment['draw_start']:
                raise ValueError('paid provenance must cover each queue contiguously')
            if not (lo <= hi <= len(queue)) or segment['availability_order'] <= last_order:
                raise ValueError('row provenance must preserve physical reveal order')
            is_training = segment['kind'] == 'source' and segment['context'] == train_context
            if is_training:
                if validation_started:
                    raise ValueError('the fixed source training block must precede validation')
                training[operator].extend(queue[lo:hi])
                training_segments[operator].append(segment)
            else:
                if segment['kind'] == 'target':
                    if segment['arm'] != tape['arm']:
                        raise ValueError('validation cannot include the coupled other arm')
                elif not (segment['kind'] == 'source' and segment['context'] == 'B'
                          and tape['case']['context'] == 'B' and operator != tape['changed_operator']):
                    raise ValueError('unexpected source block in validation')
                validation_started = True
                validation[operator].extend(queue[lo:hi])
                validation_segments[operator].append(segment)
            cursor, last_order = hi, segment['availability_order']
        if cursor != len(queue) or not training_segments[operator]:
            raise ValueError('the complete original queue must have its fixed source block')
    return dict(training=training, validation=validation,
                training_segments=training_segments, validation_segments=validation_segments)


@lru_cache(maxsize=512)
def posterior_predictive(training, validation):
    """Direct ordered prediction with alpha initialized to source+one-half."""
    if len(training) != len(validation) or min(training+validation) < 0:
        raise ValueError('same categorical nonnegative training and validation rows required')
    dimension, total, weight = len(training), sum(training), F(1)
    for category, count in enumerate(validation):
        for previously_seen in range(count):
            weight *= F(2*(training[category]+previously_seen)+1, 2*total+dimension)
            total += 1
    return weight


def predictive_values(training, validation, parameters):
    predictive, validation_likelihood, source_mixture, source_likelihood, joint_mixture = (F(1),)*5
    validation_mle = F(1)
    if set(training) != set(validation) or set(training) != set(parameters):
        raise ValueError('the same required rows must be used throughout')
    for name, row in validation.items():
        if set(training[name]) != set(row) or set(parameters[name]) != set(row):
            raise ValueError('projected categorical coordinates must match')
        categories = tuple(row)
        probabilities = {cat: F(parameters[name][cat]) for cat in categories}
        if min(probabilities.values()) < 0 or sum(probabilities.values()) != 1:
            raise ValueError('projected probabilities must form a simplex')
        a, k = tuple(training[name][cat] for cat in categories), tuple(row[cat] for cat in categories)
        predictive *= posterior_predictive(a, k)
        source_mixture *= evidence.predictive_weight(a)
        joint_mixture *= evidence.predictive_weight(tuple(x+y for x, y in zip(a, k)))
        for cat in categories:
            validation_likelihood *= probabilities[cat]**row[cat]
            source_likelihood *= probabilities[cat]**training[name][cat]
            if row[cat]:
                validation_mle *= F(row[cat], sum(row.values()))**row[cat]
    conditional = predictive/validation_likelihood if validation_likelihood else None
    joint = joint_mixture/(source_likelihood*validation_likelihood) if source_likelihood*validation_likelihood else None
    source = source_mixture/source_likelihood if source_likelihood else None
    return dict(predictive=predictive, validation_likelihood=validation_likelihood,
        joint_mixture=joint_mixture, source_mixture=source_mixture,
        source_likelihood=source_likelihood, conditional_ratio=conditional,
        joint_ratio=joint, source_ratio=source, validation_mle=validation_mle,
        prior_independent_mixture_obstruction=validation_mle <= evidence.THRESHOLD*validation_likelihood)


def subtract(left, right):
    return left[0]-right[1], left[1]-right[0]


def add(left, right):
    return left[0]+right[0], left[1]+right[1]


def row_log_likelihood(counts, probabilities):
    bounds = (F(0), F(0))
    for category, count in counts.items():
        if count:
            lo, hi = arithmetic.logarithm(F(probabilities[category]))
            bounds = add(bounds, (count*lo, count*hi))
    return bounds


def likelihood_geometry(training, validation, parameters, values=None):
    """Observed coding and likelihood losses, with independent outer logs."""
    values = values or predictive_values(training, validation, parameters)
    mle, bad, source_bad, per_row_kl, per_row_loss = (F(0), F(0)), (F(0), F(0)), (F(0), F(0)), {}, {}
    neutral = F(1)
    for name, row in validation.items():
        total = sum(row.values())
        empirical = {cat: F(n, total) for cat, n in row.items()} if total else dict.fromkeys(row, F(0))
        mle_row = row_log_likelihood(row, empirical)
        bad_row = row_log_likelihood(row, parameters[name])
        mle, bad = add(mle, mle_row), add(bad, bad_row)
        source_bad = add(source_bad, row_log_likelihood(training[name], parameters[name]))
        difference = subtract(mle_row, bad_row)
        per_row_loss[name] = difference
        per_row_kl[name] = ((difference[0]/total, difference[1]/total) if total else (F(0), F(0)))
        neutral *= evidence.predictive_weight(tuple(row.values()))
    prediction_log = arithmetic.logarithm(values['predictive'])
    source_mixture_log = arithmetic.logarithm(values['source_mixture'])
    neutral_log = arithmetic.logarithm(neutral)
    return dict(log_validation_mle_minus_log_bad=subtract(mle, bad),
        log_validation_mle_minus_log_predictive=subtract(mle, prediction_log),
        log_validation_mle_minus_log_neutral_mixture=subtract(mle, neutral_log),
        log_predictive_minus_log_neutral_mixture=subtract(prediction_log, neutral_log),
        log_lr_training=arithmetic.logarithm(values['source_ratio']),
        log_lr_joint=arithmetic.logarithm(values['joint_ratio']),
        log_lr_conditional=arithmetic.logarithm(values['conditional_ratio']),
        source_coding_advantage=subtract(source_bad, source_mixture_log),
        per_row_kl=per_row_kl, per_row_loss=per_row_loss)


def contains_bounds(saved, bounds):
    return F(saved['lower']) <= bounds[0] and F(saved['upper']) >= bounds[1]


def named_counts(family, queues):
    raw = {op: dict(Counter(values)) for op, values in queues.items()}
    # named_projection constructs required categorical counts independently.
    kernel = {op: {cat: F(1, len(alphabet)) for cat in alphabet}
              for op, alphabet in evidence.ALPHABETS.items()}
    return evidence.named_projection(family, raw, kernel)[0]


def projected_gap(case, query, chosen, other, parameters):
    if set(parameters) == {'D_REC', 'R'}:
        p, q = F(parameters['D_REC']['RECOVERY']), F(parameters['R']['DELIVERY'])
        return (1 if other == 'DETOUR_RETRY' else -1)*p*((4*q if query == 'goal' else 8*q-4)-F(case['retry_cost']))
    kernel = {evidence.S: parameters['S'], evidence.D: parameters['D_FULL']}
    return evidence.utility(case, query, other, kernel)-evidence.utility(case, query, chosen, kernel)


def saved_split_matches(row, split):
    return (row['training_segments'] == split['training_segments']
        and row['validation_segments'] == split['validation_segments']
        and row['training_lengths'] == {op: len(values) for op, values in split['training'].items()}
        and row['validation_lengths'] == {op: len(values) for op, values in split['validation'].items()})


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    protocol, rows, summary = (evidence.load(OUTPUT/name) for name in (
        'protocol.json', 'records.json', 'summary.json'))
    prior = ROOT/'reports/joint_query_qualification_v235'
    old_shared = ROOT/'reports/shared_prefix_score_v234'
    check('prior_evidence_independently_valid', all(evidence.load(path)['valid'] for path in (
        prior/'analysis.json', prior/'countermodel_analysis.json', old_shared/'analysis.json')))
    tapes = {key(row): row for row in evidence.read_rows(prior/'tapes.jsonl.gz')}
    countermodels = [row for row in evidence.load(prior/'countermodels.json') if row['found']]
    rectangles = evidence.load(old_shared/'diagnosis.json')['terminal_rectangle_witnesses']
    selected = [(row, 'V235_countermodel') for row in countermodels]+[
        (row, 'V234_rectangle') for row in rectangles]
    roster = [dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')}, origin=origin)
              for row, origin in selected]
    check('nine_fixed_witnesses_and_six_main_blockers', len(tapes) == 24 and len(rows) == len(selected) == 9
        and len(countermodels) == 6 and tuple(map(key, countermodels)) == MAIN and len(rectangles) == 3
        and protocol['selected'] == roster and [(key(row), row['origin']) for row in rows]
        == [(key(row), origin) for row, origin in selected])
    check('fixed_eight_family_event_budget', protocol['families'] == {
        family: [evidence.ROW_NAMES[row] for row in family_rows]
        for family, family_rows in evidence.FAMILY_ROWS.items()}
        and protocol['family_count'] == 8 and protocol['event_count_per_life_arm'] == 48
        and protocol['delta_per_life_arm'] == '1/20' and protocol['threshold'] == evidence.THRESHOLD)
    check('fixed_source_training_validation_rule', protocol['training_rule'] ==
        'A_source_for_A_and_unchanged_B_rows__B_source_for_changed_B_row'
        and protocol['denominator'] == 'validation_only'
        and protocol['numerator'] == 'M_training_plus_validation_divided_by_M_training')
    check('frozen_phase1_scope', protocol['complete'] and protocol['phases'] == [
        'protocol_frozen', 'evidence_frozen', 'witnesses_checked', 'complete']
        and protocol['qualification_only'] and protocol['witness_feasibility_only']
        and not protocol['query_certificates_obtained'] and not protocol['scientific_gate_changed']
        and protocol['new_observations'] == protocol['new_paid_samples'] == 0)
    groups, main_admitted = {'V235_countermodel': [], 'V234_rectangle': []}, 0
    mixture_obstructions, mixture_obstructions_by_origin = [], Counter()
    for row, (witness, origin) in zip(rows, selected):
        location = dict(life=row['life'], index=row['index'], arm=row['arm'], origin=origin)
        tape = tapes[key(witness)]
        check('original_identity_case_fee_and_observation_scope', all(row[field] == tape[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'changed_operator'))
            and row['new_observations'] == row['new_paid_samples'] == 0)
        split = split_tape(tape)
        family = evidence.relevant_family(witness['query'], witness['chosen'], witness['other'])
        training, validation = named_counts(family, split['training']), named_counts(family, split['validation'])
        if origin == 'V235_countermodel':
            parameters = {name: {cat: F(value) for cat, value in values.items()}
                          for name, values in witness['parameters'].items()}
        else:
            p, q = F(witness['p']), F(witness['q'])
            parameters = {'D_REC': {'RECOVERY': p, 'OTHER': 1-p},
                          'R': {'DELIVERY': q, 'LOST': 1-q}}
        check('original_comparison_and_necessary_projection', row['origin'] == origin
            and row['query'] == witness['query'] and row['chosen'] == witness['chosen']
            and row['other'] == witness['other'] and row['family'] == family
            and row['training_counts'] == training and row['validation_counts'] == validation
            and {name: {cat: F(value) for cat, value in values.items()}
                 for name, values in row['parameters'].items()} == parameters)
        check('independent_training_activation_and_complete_validation_split',
            saved_split_matches(row, split)
            and row['row_lengths'] == {op: len(values) for op, values in tape['operators'].items()})
        expected_training = {op: 128 if tape['case']['context'] == 'B' and op == tape['changed_operator'] else 384
                             for op in OPERATORS}
        check('source_training_paid_counts_and_cumulative_fees', row['training_lengths'] == expected_training
            and tape['fees']['source_paid_samples'] == (3456 if tape['index'] < 30 else 4608)
            and all(row['training_lengths'][op]+row['validation_lengths'][op] == row['row_lengths'][op]
                    for op in OPERATORS))
        gap = projected_gap(tape['case'], witness['query'], witness['chosen'], witness['other'], parameters)
        check('exact_original_bad_gap', F(row['gap']) == F(row['previously_reported_gap']) == F(witness['gap']) == gap
            and gap > evidence.REGRET)
        values = predictive_values(training, validation, parameters)
        check('exact_sequential_prediction_and_joint_tradeoff', values['predictive']*values['source_mixture']
            == values['joint_mixture'] and values['joint_ratio'] == values['source_ratio']*values['conditional_ratio'])
        check('prediction_is_bounded_by_validation_mle', values['predictive'] <= values['validation_mle'])
        if values['prior_independent_mixture_obstruction']:
            mixture_obstructions.append(dict(location))
            mixture_obstructions_by_origin[origin] += 1
        inside = evidence.audit_membership(values['conditional_ratio'], row['membership'], check)
        geometry = likelihood_geometry(training, validation, parameters, values)
        saved_geometry = row['geometry']
        check('observed_validation_geometry_and_exact_tradeoff', all(contains_bounds(saved_geometry[field], geometry[field])
            for field in ('log_validation_mle_minus_log_bad', 'log_validation_mle_minus_log_predictive',
                          'log_validation_mle_minus_log_neutral_mixture', 'log_predictive_minus_log_neutral_mixture',
                          'log_lr_training', 'log_lr_joint', 'log_lr_conditional'))
            and saved_geometry['exact_joint_equals_training_times_conditional']
            and saved_geometry['scope'] == 'observed_validation_geometry_not_true_KL_or_new_sample_guarantee')
        per_row = saved_geometry['per_row_kl_validation_to_bad']
        check('per_row_validation_kl_bounds', set(per_row) == set(validation) and all(
            per_row[name]['n'] == sum(validation[name].values())
            and contains_bounds(per_row[name]['log_mle_minus_log_bad'], geometry['per_row_loss'][name])
            and F(per_row[name]['kl_lower']) <= geometry['per_row_kl'][name][0]
            and F(per_row[name]['kl_upper']) >= geometry['per_row_kl'][name][1] for name in validation))
        check('fixed_witness_only_interpretation', row['interpretation'] == (
            'admitted_bad_witness_prevents_this_query_certificate' if inside else 'excluded_fixed_witness_only'))
        groups[origin].append((row['kind'], inside))
        if origin == 'V235_countermodel':
            main_admitted += inside
    expected_groups = {origin: dict(witnesses=len(values), admitted=sum(inside for _, inside in values),
        excluded=sum(not inside for _, inside in values), by_kind={kind: dict(
            witnesses=sum(saved_kind == kind for saved_kind, _ in values),
            admitted=sum(saved_kind == kind and inside for saved_kind, inside in values),
            excluded=sum(saved_kind == kind and not inside for saved_kind, inside in values))
            for kind in ('failure', 'positive')}) for origin, values in groups.items()}
    eligible = main_admitted == 0
    check('frozen_continuation_and_summary', summary['complete'] and summary['records'] == 9
        and summary['groups'] == expected_groups and summary['primary_risk_blockers'] == dict(
            cases=6, admitted=main_admitted, excluded=6-main_admitted)
        and summary['full_qualification_eligible'] == eligible and summary['qualification_status'] == (
            'eligible_not_run' if eligible else 'skipped_primary_bad_witness_still_admitted')
        and summary['qualification_only'] and not summary['query_certificates_obtained']
        and not summary['scientific_gate_changed'] and summary['new_observations'] == summary['new_paid_samples'] == 0)
    result = dict(valid=not failures, complete=True, records=9, exact_predictive_membership_checks=9,
        groups=expected_groups, primary_risk_admitted=main_admitted, full_qualification_allowed=eligible,
        prior_independent_mixture_obstructions=len(mixture_obstructions),
        prior_independent_mixture_obstructions_by_origin={origin: mixture_obstructions_by_origin[origin]
                                                        for origin in groups},
        prior_independent_mixture_obstruction_identities=mixture_obstructions,
        prior_independent_scope='normalized_mixtures_of_this_fixed_validation_likelihood_only',
        query_certificates_obtained=False, new_observations=0, new_paid_samples=0,
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
