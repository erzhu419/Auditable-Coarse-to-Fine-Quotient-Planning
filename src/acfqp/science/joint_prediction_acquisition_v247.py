"""Acquire against all live query bounds with fixed retained proof parameters.

The three deterministic empirical batch predictions are acquisition proxies.
They neither call proof optimizers nor certify hypothetical observations. The
original engine alone certifies and stops after an actual paid observation.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import joint_query_evidence_v235 as joint
from . import kernel_query_profile_v232 as dual
from . import oracle_gap_acquisition_v231 as original

OPERATORS, ALPHABETS = original.OPERATORS, original.ALPHABETS
BATCH, TARGET_CAP = original.BATCH, original.TARGET_CAP


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0)+amount


def _log(value):
    return (F(0), F(0)) if F(value) == 1 else tuple(map(F, joint.log_bounds(value)))


def expected_increment(row):
    """Largest-remainder rounding of 16 times the paid full-row frequencies."""
    total = sum(row.values())
    expected = {category: F(BATCH*count, total) for category, count in row.items()}
    result = {category: value.numerator//value.denominator for category, value in expected.items()}
    order = sorted(row, key=lambda category: (-(expected[category]-result[category]),
                                               tuple(row).index(category)))
    for category in order[:BATCH-sum(result.values())]:
        result[category] += 1
    return result


def _mle_upper(counts):
    return sum((count*_log(F(count, sum(row.values())))[1]
                for row in counts.values() for count in row.values() if count), F(0))


def _mixture_lower(counts):
    # Lookup the active function each time: the runner installs per-arm caches.
    return sum((_log(joint.mixture_normalizer(tuple(row.values())))[0]
                for row in counts.values()), F(0))


def _leaf_bounds(proof, projected, work):
    counts = joint.embedded_counts(projected, proof['family'])
    leaves = []
    for index, leaf in enumerate(proof['leaves']):
        _add(work, 'joint_prediction_cell_evaluations')
        item = dict(index=index, kind=leaf['kind'], log_bad_likelihood_upper=None,
                    row_nus={}, retry_probability=None)
        if leaf['log_bad_likelihood_upper'] is None:
            leaves.append(item)
            continue
        multiplier = F(leaf['multiplier'])
        row_bounds = []
        for operator, coefficients in leaf['gap_coefficients'].items():
            retained = leaf['row_witnesses'][operator]
            row = counts[operator]
            _add(work, 'joint_prediction_row_bound_evaluations')
            if retained['kind'] == 'free_simplex':
                if sum(row.values()):
                    raise ValueError('a retained free simplex cannot predict an observed row')
                row_bounds.append(max(multiplier*F(value) for value in coefficients.values()))
                item['row_nus'][operator] = None
            else:
                delta = sum(row.values())-sum(proof['embedded_counts'][operator].values())
                nu = F(retained['nu'])+delta
                item['row_nus'][operator] = nu
                row_bounds.append(dual._row_dual_upper(row, coefficients, multiplier, nu))
        retry_row = counts[OPERATORS[2]]
        size = sum(retry_row.values())
        probability = F(retry_row['DELIVERY'], size) if size else F(1, 2)
        low, high = map(F, leaf['retry_interval'])
        probability = min(high, max(low, probability))
        retry = {'DELIVERY': probability, 'LOST': 1-probability}
        retry_upper = sum((count*_log(retry[category])[1]
                           for category, count in retry_row.items() if count), F(0))
        item['retry_probability'] = probability
        item['log_bad_likelihood_upper'] = (multiplier*(F(leaf['gap_constant'])-F(proof['regret_threshold']))
                                            +retry_upper+sum(row_bounds, F(0)))
        leaves.append(item)
    return leaves


def _tangent_upper(proof, projected, work):
    """Reevaluate concave f_k+lambda*h on its entire original domain."""
    retained = proof['result']['global_tangent']
    point, multiplier = retained['point'], F(retained['multiplier'])
    likelihood = sum((count*_log(F(point[name][category]))[1]
                      for name, row in projected.items() for category, count in row.items() if count), F(0))
    if proof['family'] == 'S_D_FULL':
        residual = {name: {category: F(count)/F(point[name][category])
                          +multiplier*F(retained['gradient_h'][name][category])
                          for category, count in row.items()} for name, row in projected.items()}
        support = sum((max(row.values())-sum(value*F(point[name][category])
                       for category, value in row.items()) for name, row in residual.items()), F(0))
    else:
        residual = {}
        for name, category in (('D_REC', 'RECOVERY'), ('R', 'DELIVERY')):
            probability = F(point[name][category])
            other = 'OTHER' if name == 'D_REC' else 'LOST'
            gradient = F(projected[name][category])/probability-F(projected[name][other])/(1-probability)
            residual[name] = gradient+multiplier*F(retained['gradient_h'][name])
        support = sum((max(F(0), value)-value*F(point[name]['RECOVERY' if name == 'D_REC' else 'DELIVERY'])
                       for name, value in residual.items()), F(0))
    _add(work, 'joint_prediction_tangent_evaluations')
    return likelihood+multiplier*F(retained['h_point'])+support


def predict(proof, case, raw_counts, work=None):
    """Bound a hypothetical histogram without producing a certificate."""
    projected = joint.project_counts(raw_counts, proof['family'])
    fallback, leaves = None, []
    engine = proof.get('engine', 'V235')
    if engine == 'convex_tangent':
        if proof['result']['global_tangent'] is not None:
            upper = _tangent_upper(proof, projected, work)
        else:
            fallback, upper = 'missing_retained_tangent', _mle_upper(projected)
    elif proof['witness_kind'] == 'global_likelihood_dual' and proof['leaves']:
        leaves = _leaf_bounds(proof, projected, work)
        finite = [row['log_bad_likelihood_upper'] for row in leaves
                  if row['log_bad_likelihood_upper'] is not None]
        if not finite:
            fallback, upper = 'missing_retained_partition', _mle_upper(projected)
        else:
            upper = max(finite)
    else:
        fallback, upper = ('bad_null_mle' if proof['witness_kind'] == 'bad_null_mle'
                           else 'missing_retained_partition'), _mle_upper(projected)
    if fallback is not None:
        _add(work, 'joint_prediction_mle_fallbacks')
    lower, threshold = _mixture_lower(projected), _log(F(proof['threshold']))[1]
    log_e = lower-upper
    return dict(query=proof['query'], chosen=proof['chosen'], other=proof['other'],
        family=proof['family'], engine=engine, fallback=fallback, projected_counts=projected,
        log_mixture_lower=lower, log_bad_likelihood_upper=upper, log_e_lower=log_e,
        log_threshold_upper=threshold, deficit=max(F(0), threshold-log_e), leaf_bounds=leaves)


def choose(member, plan, spent, work):
    """Minimize the largest predicted deficit over all live alternatives."""
    if spent >= TARGET_CAP or original._ready(plan):
        return None
    if not (plan['utility_lower'] >= 2 or plan['goal_impossible']) or plan['query_ready']:
        return original.choose(member, plan, spent, work)
    proofs = [proof for query in ('goal', 'risk')
              for proof in plan['query_evidence']['queries'][query]['comparisons']
              if not proof['certified']]
    if not proofs:
        return original.choose(member, plan, spent, work)
    counts = plan['evidence_counts']
    current = [predict(proof, plan['case'], counts, work) for proof in proofs]
    _add(work, 'joint_prediction_current_comparison_evaluations', len(proofs))
    increments, candidates = {}, {}
    for operator in OPERATORS:
        # Fixed full alphabet order also fixes largest-remainder ties.
        row = {category: counts[operator][category] for category in ALPHABETS[operator]}
        increments[operator] = expected_increment(row)
        hypothetical = deepcopy(counts)
        for category, number in increments[operator].items():
            hypothetical[operator][category] += number
        predictions = [predict(proof, plan['case'], hypothetical, work) for proof in proofs]
        _add(work, 'joint_prediction_candidate_comparison_evaluations', len(proofs))
        candidates[operator] = dict(comparisons=predictions,
                                    worst_deficit=max(row['deficit'] for row in predictions))
    operator = min(OPERATORS, key=lambda op: (candidates[op]['worst_deficit'],
                    sum(member[op].values()), OPERATORS.index(op)))
    _add(work, 'joint_prediction_choices')
    return dict(operator=operator, reason='joint_retained_proof_prediction', prediction_only=True,
        joint_prediction_reason='active', joint_prediction_expected_increments=increments,
        joint_prediction_current=current, joint_prediction_candidates=candidates,
        effective_n=dict(plan['effective_n']), initial_deficits=original.deficits(plan))
