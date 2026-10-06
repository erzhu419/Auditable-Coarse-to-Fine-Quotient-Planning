"""Source-trained predictive evidence on the fixed V236 paid chronology.

Each row starts validation after its own source block.  For B, the unchanged
rows can already be validating when the changed row's training block arrives;
the joint process therefore uses row activation in the arm's chronology.
Training outcomes set a Jeffreys posterior and never enter the validation
likelihood.  This module neither acquires observations nor evaluates truth.
"""
from fractions import Fraction as F

from .joint_query_evidence_v235 import (
    ALPHABETS, FAMILIES, OPERATORS, POLICIES, REGRET, ROWS, THRESHOLD,
    canonical_family, embedded_counts, gap, log_bounds, mixture_normalizer,
    project_counts, project_parameters,
)


def split_tape(tape):
    """Partition every retained row outcome using its paid provenance.

    A and A_RETURN train on A sources.  Changed B rows train on B sources;
    unchanged B rows train on mapped A sources and validate the inherited A
    targets, B sources and B targets.  The already-audited B tape excludes
    A_RETURN.  Keeping the segments records each row's training activation.
    """
    training = {operator: [] for operator in OPERATORS}
    validation = {operator: [] for operator in OPERATORS}
    training_segments = {operator: [] for operator in OPERATORS}
    validation_segments = {operator: [] for operator in OPERATORS}
    for operator in OPERATORS:
        source_context = ('B' if tape['case']['context'] == 'B'
                          and operator == tape['changed_operator'] else 'A')
        for segment in tape['provenance'][operator]:
            is_training = segment['kind'] == 'source' and segment['context'] == source_context
            observations = tape['operators'][operator][segment['queue_start']:segment['queue_end']]
            (training if is_training else validation)[operator].extend(observations)
            (training_segments if is_training else validation_segments)[operator].append(segment)
    return dict(training=training, validation=validation,
                training_segments=training_segments, validation_segments=validation_segments)


def predictive_normalizer(training, validation):
    """Exact posterior predictive sequence likelihood M(s+t)/M(s)."""
    combined = tuple(s+t for s, t in zip(training, validation))
    return mixture_normalizer(combined)/mixture_normalizer(tuple(training))


def _likelihood(counts, parameters):
    result = F(1)
    for name, row in counts.items():
        for category, count in row.items():
            result *= F(parameters[name][category])**count
    return result


def _predictive(training_counts, validation_counts):
    result = F(1)
    for name, row in validation_counts.items():
        result *= predictive_normalizer(tuple(training_counts[name][category] for category in row),
                                        tuple(row.values()))
    return result


def membership(training_counts, validation_counts, parameters, threshold=THRESHOLD):
    """Keep exactly Q <= T L(validation), including the equality boundary."""
    for name, row in validation_counts.items():
        probabilities = [F(parameters[name][category]) for category in row]
        if sum(probabilities) != 1 or any(p < 0 for p in probabilities):
            raise ValueError('each projected parameter row must be a simplex')
    predictive = _predictive(training_counts, validation_counts)
    likelihood = _likelihood(validation_counts, parameters)
    threshold = F(threshold)
    inside = predictive <= threshold*likelihood
    lower, upper = log_bounds(predictive/likelihood) if likelihood else ('Infinity', 'Infinity')
    threshold_lower, threshold_upper = log_bounds(threshold)
    return dict(exact_inside=inside, excluded=not inside, threshold=int(threshold),
                log_lr_lower=lower, log_lr_upper=upper,
                log_threshold_lower=threshold_lower, log_threshold_upper=threshold_upper)


def _bounds(value):
    lower, upper = log_bounds(value)
    return dict(lower=lower, upper=upper)


def observed_geometry(training_counts, validation_counts, parameters):
    """Observed likelihood geometry for the fixed positive-probability witnesses.

    The source likelihood ratio explains the algebraic change from joint to
    conditional evidence.  Empirical validation KL describes these observations,
    without asserting a true-law KL or a guaranteed additional sample budget.
    """
    predictive, training_mixture, joint_mixture, neutral_mixture = F(1), F(1), F(1), F(1)
    validation_mle, per_row = F(1), {}
    for name, row in validation_counts.items():
        trained = tuple(training_counts[name][category] for category in row)
        validated = tuple(row.values())
        joined = tuple(s+t for s, t in zip(trained, validated))
        q = predictive_normalizer(trained, validated)
        predictive *= q
        training_mixture *= mixture_normalizer(trained)
        joint_mixture *= mixture_normalizer(joined)
        neutral_mixture *= mixture_normalizer(validated)
        n, row_maximum = sum(row.values()), F(1)
        row_likelihood = F(1)
        for category, count in row.items():
            if count:
                row_maximum *= F(count, n)**count
                row_likelihood *= F(parameters[name][category])**count
        validation_mle *= row_maximum
        loss = _bounds(row_maximum/row_likelihood)
        per_row[name] = dict(n=n, log_mle_minus_log_bad=loss,
            kl_lower=str(F(loss['lower'])/n) if n else '0',
            kl_upper=str(F(loss['upper'])/n) if n else '0')
    train_likelihood = _likelihood(training_counts, parameters)
    validation_likelihood = _likelihood(validation_counts, parameters)
    return dict(
        log_validation_mle_minus_log_bad=_bounds(validation_mle/validation_likelihood),
        log_validation_mle_minus_log_predictive=_bounds(validation_mle/predictive),
        log_validation_mle_minus_log_neutral_mixture=_bounds(validation_mle/neutral_mixture),
        log_predictive_minus_log_neutral_mixture=_bounds(predictive/neutral_mixture),
        log_lr_training=_bounds(training_mixture/train_likelihood),
        log_lr_joint=_bounds(joint_mixture/(train_likelihood*validation_likelihood)),
        log_lr_conditional=_bounds(predictive/validation_likelihood),
        exact_joint_equals_training_times_conditional=(predictive*training_mixture == joint_mixture),
        per_row_kl_validation_to_bad=per_row,
        scope='observed_validation_geometry_not_true_KL_or_new_sample_guarantee')
