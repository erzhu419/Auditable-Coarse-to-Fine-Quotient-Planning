"""Run the unchanged V91 and V92 learners on one newly acquired history."""
from collections import Counter
from time import perf_counter

from acfqp.science.controlled_predictive_continuation_value_v91 import fit_decomposed
from acfqp.science.controlled_predictive_paired_continuation_value_v92 import fit_models
from acfqp.science.controlled_predictive_paired_correction_v92 import fit_selectors


def assert_shared_roots(unary_roots, paired_roots):
    """Compare the two already-loaded cohorts without another trajectory read."""
    if unary_roots != paired_roots:
        raise ValueError("V91 and V92 loaders produced different roots, prefixes or original MC labels")
    return dict(root_cohorts_identical=True, roots=len(unary_roots),
                mc_rows=sum(len(root["mc_rows"]) for root in unary_roots))


def learn(roots, unary_rows, paired_rows, prefix_pools, checkpoint):
    """Fit the fixed algorithms, retaining every model and each component's cost.

    Return selectors, paired models, unary models, labels by method, and log.
    Each row collection comes from the corresponding unchanged historical
    extractor; the V91 trajectory weights and final-active-state rows persist.
    """
    started = perf_counter()
    roots, unary_rows, paired_rows = list(roots), list(unary_rows), list(paired_rows)
    paired_models, paired_fit = fit_models(paired_rows, checkpoint)
    selectors, labels, selector_fit = fit_selectors(roots, prefix_pools, paired_models, checkpoint)
    unary_selector, unary_models, unary_labels, unary_fit = fit_decomposed(roots, unary_rows, checkpoint)
    selectors["V91_DECOMPOSED"] = unary_selector
    labels["V91_DECOMPOSED"] = unary_labels
    counts = Counter()
    for component in (paired_fit, selector_fit, unary_fit):
        counts.update(component["counts"])
    return selectors, paired_models, unary_models, labels, dict(checkpoint=checkpoint,
        input_roots=len(roots), input_unary_rows=len(unary_rows), input_paired_rows=len(paired_rows),
        paired_models=paired_fit, paired_selectors=selector_fit, v91_decomposed=unary_fit,
        counts=dict(counts), new_environment_transitions=0, seconds=perf_counter() - started)
