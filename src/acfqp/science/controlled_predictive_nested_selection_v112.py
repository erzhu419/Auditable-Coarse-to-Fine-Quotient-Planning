"""Source-only inner history validation and its inherited acquisition cost."""
from collections import Counter
from itertools import combinations
from math import fsum, isfinite
from time import perf_counter
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS
from scripts.analyze_controlled_predictive_crossed_ranking_v106 import event_metrics
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values

LIVES = (11, 12, 13, 14)
WIDTHS = (4, 16)
QUERIES = ('reward', 'risk_goal')
STAGES = ('HALF', 'FULL')
REPLICAS = 32


def _root_index(roots, lives, roots_per_query):
    if tuple(lives) != LIVES:
        raise ValueError('nested selection requires the four frozen histories')
    index = {root['root_id']: root for root in roots}
    expected = {(life, query, episode) for life in lives for query in QUERIES
        for episode in range(roots_per_query)}
    if (len(index) != len(roots) or len(roots) != len(expected)
            or {(r['life'], r['query'], r['episode']) for r in roots} != expected):
        raise ValueError('complete frozen root cohort is required')
    for root in roots:
        log = root['reference_log']
        if (not root['reference_complete'] or log['censored_root']
                or log['trajectories'] != REPLICAS * len(OPTIONS)
                or any(len(log['pair_deltas'].get(option, [])) != REPLICAS
                    or any(len(row) != 3 or not all(isfinite(value) for value in row)
                        for row in log['pair_deltas'][option]) for option in OPTIONS[1:])):
            raise ValueError('every root requires all 32 complete paired reference replicas')
    return index


def select_updates(inner_decisions, roots, lives, widths, roots_per_query=8):
    """Select FULL only for a positive equal-history source validation mean."""
    start = perf_counter()
    if tuple(widths) != WIDTHS:
        raise ValueError('nested selection retains both frozen widths')
    roots_by_id = _root_index(roots, lives, roots_per_query)
    pairs = {'_'.join(map(str, pair)): pair for pair in combinations(lives, 2)}
    methods = [f'POOLED_H{hidden}_{stage}' for hidden in widths for stage in STAGES]
    expected = {(pair_id, root['root_id'], method) for pair_id, pair in pairs.items()
        for root in roots if root['life'] not in pair for method in methods}
    decisions = {}
    for row in inner_decisions:
        key = (row['pair_id'], row['root_id'], row['method'])
        if (key not in expected or key in decisions
                or row['validation_life'] != roots_by_id[row['root_id']]['life']
                or row['event'] is None):
            raise ValueError('inner decisions must match the unique two-train one-validation roster')
        decisions[key] = row['event']
    if set(decisions) != expected:
        raise ValueError('complete inner decision roster is required')
    utilities = {root['root_id']: reference_values(root['reference_log'], root['query'], REPLICAS)['pooled']
        for root in roots}
    selections = []
    for outer in lives:
        sources = [life for life in lives if life != outer]
        for hidden in widths:
            half_method, full_method = [f'POOLED_H{hidden}_{stage}' for stage in STAGES]
            for query in QUERIES:
                folds = []
                for validation in sources:
                    training = [life for life in sources if life != validation]
                    pair_id = '_'.join(map(str, training))
                    selected = sorted((root for root in roots if root['life'] == validation
                        and root['query'] == query), key=lambda root: root['episode'])
                    deltas = []
                    for root in selected:
                        root_id = root['root_id']
                        values = utilities[root_id]
                        half = event_metrics(decisions[(pair_id, root_id, half_method)], values)
                        full = event_metrics(decisions[(pair_id, root_id, full_method)], values)
                        delta = full['selected_reference_utility'] - half['selected_reference_utility']
                        if not isfinite(delta):
                            raise ValueError('selection utility must be finite for every fixed root')
                        deltas.append(delta)
                    folds.append(dict(validation_life=validation, pair_id=pair_id, source_lives=training,
                        root_ids=[root['root_id'] for root in selected],
                        mean_utility_delta=fsum(deltas) / roots_per_query))
                average = fsum(fold['mean_utility_delta'] for fold in folds) / len(sources)
                stage = 'FULL' if average > 0 else 'HALF'
                selections.append(dict(heldout_life=outer, hidden=hidden, query=query, source_lives=sources,
                    validation_folds=folds, mean_utility_delta=average,
                    chosen_stage=stage, chosen_method=f'POOLED_H{hidden}_{stage}'))
    comparisons = len(selections) * (len(lives) - 1) * roots_per_query
    return selections, dict(counts=dict(selections=len(selections), validation_folds=len(selections) * 3,
        root_comparisons=comparisons, cached_decision_lookups=2 * comparisons,
        neural_candidate_predictions=0, neural_model_fits=0, new_environment_transitions=0,
        new_synthetic_transitions=0), checks=dict(complete_root_roster=True, complete_inner_decision_roster=True,
        complete_reference_replicas=True, outer_history_excluded=True, two_source_training_one_validation=True,
        equal_root_history_weight=True, strict_positive_full_else_half=True, pooled_reference_only=True),
        seconds=perf_counter() - start)


def _reference_work(roots):
    ground, planning, outcomes = Counter(), Counter(), Counter()
    trajectories = 0
    for root in roots:
        log = root['reference_log']
        ground.update(log['ground_work']); planning.update(log['planning_counts'])
        outcomes.update(log['outcomes']); trajectories += log['trajectories']
    return dict(roots=len(roots), trajectories=trajectories,
        sampled_transitions=ground['sampled_transitions'], ground_work=dict(ground),
        planning_counts=dict(planning), outcomes=dict(outcomes))


def selection_acquisition_accounting(roots, acquisition_accounting, lives):
    """Charge all source full acquisition and source reference validation once per outer use."""
    _root_index(roots, lives, 8)
    histories = {row['life']: row for row in acquisition_accounting['per_history']}
    if (len(histories) != len(acquisition_accounting['per_history']) or set(histories) != set(lives)
            or any(row['half_transitions'] != 256000 or row['full_transitions'] != 512000
                for row in histories.values())):
        raise ValueError('acquisition must contain the four frozen half/full history budgets')
    per_history = [dict(life=life, half_transitions=histories[life]['half_transitions'],
        full_transitions=histories[life]['full_transitions'],
        reference_work=_reference_work([root for root in roots if root['life'] == life])) for life in lives]
    per_fold = []
    for outer in lives:
        sources = [life for life in lives if life != outer]
        validation = _reference_work([root for root in roots if root['life'] in sources])
        evaluation = _reference_work([root for root in roots if root['life'] == outer])
        training = sum(histories[life]['full_transitions'] for life in sources)
        per_fold.append(dict(heldout_life=outer, source_lives=sources,
            source_training_transitions=training,
            half_baseline_training_transitions=sum(histories[life]['half_transitions'] for life in sources),
            full_baseline_training_transitions=training,
            selection_validation_work=validation, outer_evaluation_work=evaluation,
            learning_validation_environment_transitions=training + validation['sampled_transitions'],
            outer_evaluation_environment_transitions=evaluation['sampled_transitions']))
    reference = _reference_work(roots)
    training = sum(row['full_transitions'] for row in histories.values())
    return dict(per_history=per_history, per_fold=per_fold,
        unique_physical=dict(source_lives=list(lives), training_environment_transitions=training,
            reference_work=reference,
            training_plus_reference_environment_transitions=training + reference['sampled_transitions']),
        newly_sampled_environment_transitions=0,
        checks=dict(full_source_acquisition_charged=True, source_validation_separate_from_outer_evaluation=True,
            unique_physical_references_counted_once=True, no_width_query_or_fold_multiplication=True),
        scope='Inherited source training and reference acquisition. Each outer selection uses full source data '
            'and source validation regardless of its chosen stage. Overlapping folds reuse the unique physical '
            'reference bank; natural-root extraction, model fitting and feature work remain separately accounted.')
